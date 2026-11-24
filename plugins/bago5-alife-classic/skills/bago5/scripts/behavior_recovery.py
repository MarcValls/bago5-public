"""BAGO5-CCR-001: preserve a valid route while correcting a scoped action.

Pure, bounded metadata adapter around turn_decision.assess. It does not observe
the world, grant permission, resume STOP, execute tools, or persist anything.
The caller must authenticate observations and enforce real host/controller gates.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path


_spec = importlib.util.spec_from_file_location(
    "bago5_recovery_policy", Path(__file__).with_name("turn_decision.py"))
policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(policy)

SCHEMA = "bago5.behavior-recovery.record.v1"
MAX_EVENTS = 64
MAX_RECORDS = 32
STATES = {"WAITING_CONDITIONS", "PROHIBITED", "RECONCILE", "RESOLVED", "EXPIRED", "OBSOLETE"}
KINDS = {"CONDITION", "AUTHORITY", "PROHIBITION", "UNCERTAIN_RESULT"}
SPEC_KEYS = {"id", "action_id", "cause_kind", "reason", "source_ref", "correct_behavior",
             "activation_condition", "conditions", "expires_at", "prior_execution"}
SPEC_OPTIONAL_KEYS = {"restriction_source_type"}
OBS_KEYS = {"id", "correction_id", "binding", "action_id", "observed_at", "valid_until",
            "current", "source_ref", "conditions", "relevance", "prior_result", "restriction_resolution"}
RECORD_KEYS = SPEC_KEYS | {"schema", "binding", "goal", "baseline_criteria", "criterion_ids",
                          "initial_blocker", "initial_authorization", "registered_at", "state",
                          "target_action_id", "events", "invalidations", "invalidated_authority_refs", "resolution"}
GUARD_PREFIX = "bago5:correction:"
GUARD_INTERVENTION = "Reevaluar esta corrección con observaciones actuales; conservar las autorizaciones y controles del host."


class RecoveryError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RecoveryError(message)


def _object(value, keys, label):
    require(isinstance(value, dict) and set(value) == set(keys), label + ": unexpected or missing fields")


def _text(value, label):
    try:
        return policy._text(value, label)
    except ValueError as exc:
        raise RecoveryError(str(exc)) from exc


def _enum(value, choices, label):
    require(isinstance(value, str) and value in choices, label + ": invalid value")
    return value


def _time(value, label):
    require(isinstance(value, str) and 0 < len(value) <= 100, label + ": timezone-aware timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise RecoveryError(label + ": invalid timestamp") from exc
    require(parsed.tzinfo is not None, label + ": timezone required")
    try:
        return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise RecoveryError(label + ": timestamp outside supported UTC range") from exc


def _now(value):
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        require(value.tzinfo is not None, "now: timezone required")
        return value.astimezone(timezone.utc)
    return _time(value, "now")


def _digest(value):
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
        raise RecoveryError("Bounded JSON metadata required") from exc
    require(len(raw) <= 2_000_000, "Recovery metadata exceeds input limit")
    return hashlib.sha256(raw).hexdigest()


def _binding(value, expected=None):
    try:
        policy._binding(value, "recovery.binding", expected)
    except ValueError as exc:
        raise RecoveryError(str(exc)) from exc


def _stopped(receipt):
    return (isinstance(receipt, dict) and isinstance(receipt.get("control"), dict)
            and isinstance(receipt["control"].get("state"), str)
            and receipt["control"].get("state") in {"STOP", "REVOKED"})


def _receipt(receipt, record=None):
    require(isinstance(receipt, dict), "Current turn receipt required")
    # assess short-circuits UNKNOWN/STOP control. Structural validation uses a
    # throwaway copy only; it neither changes nor authorizes the supplied state.
    structural = deepcopy(receipt)
    _binding(structural.get("binding"), record["binding"] if record else None)
    control = structural.get("control")
    require(isinstance(control, dict), "Current control required")
    if (isinstance(control.get("state"), str) and control["state"] in {"UNKNOWN", "STOP", "REVOKED"}
            or control.get("current") is False):
        structural["control"] = {**control, "state": "RUNNING", "current": True}
    result = policy.assess(structural)
    require(result.get("validation") != "INVALID", "Invalid current receipt: " + "; ".join(result["reasons"]))
    _digest(receipt)
    if record:
        require({k: receipt["goal"][k] for k in ("baseline", "current")} == record["goal"],
                "Correction cannot change the objective")
        require(receipt["baseline_criteria"] == record["baseline_criteria"],
                "Correction cannot discard or change acceptance criteria")
    return receipt


def _conditions(values, observed=False):
    require(isinstance(values, list) and 1 <= len(values) <= 32, "One to 32 recovery conditions required")
    seen = set()
    keys = {"id", "state", "source_ref"} if observed else {"id", "description"}
    for item in values:
        _object(item, keys, "condition")
        for name in keys:
            _text(item[name], "condition." + name)
        require(item["id"] not in seen, "Duplicate condition ID")
        seen.add(item["id"])
        if observed:
            _enum(item["state"], {"SATISFIED", "UNSATISFIED", "UNKNOWN"}, "condition.state")
    return seen


def _validate_spec(spec):
    require(isinstance(spec, dict) and SPEC_KEYS <= set(spec)
            and set(spec) <= SPEC_KEYS | SPEC_OPTIONAL_KEYS,
            "correction specification: unexpected or missing fields")
    for name in ("id", "action_id", "reason", "source_ref", "correct_behavior", "activation_condition"):
        _text(spec[name], "correction." + name)
    _enum(spec["cause_kind"], KINDS, "cause_kind")
    _enum(spec["prior_execution"], {"NOT_RUN", "UNCERTAIN"}, "prior_execution")
    if spec["cause_kind"] == "PROHIBITION":
        require("restriction_source_type" in spec, "Prohibition requires its own restriction source type")
    if "restriction_source_type" in spec:
        _enum(spec["restriction_source_type"], {"USER_INSTRUCTION", "HOST_PERMISSION", "EXPLICIT_APPROVAL"},
              "restriction_source_type")
    _conditions(spec["conditions"])
    if spec["expires_at"] is not None:
        _time(spec["expires_at"], "expires_at")


def _guard(record):
    source_ref = GUARD_PREFIX + record["id"]
    if len(source_ref) > 10000:
        source_ref = GUARD_PREFIX + "sha256:" + _digest(record["id"])
    return {"reason": ("BAGO5-CCR-001: " + record["reason"])[:10000],
            "source_ref": source_ref, "intervention": GUARD_INTERVENTION,
            "basis": "INSTRUCTION", "current": True}


def _is_guard(blocker, record=None):
    if not isinstance(blocker, dict):
        return False
    if record is not None:
        return blocker == _guard(record)
    return (set(blocker) == {"reason", "source_ref", "intervention", "basis", "current"}
            and isinstance(blocker["source_ref"], str) and blocker["source_ref"].startswith(GUARD_PREFIX)
            and isinstance(blocker["reason"], str) and blocker["reason"].startswith("BAGO5-CCR-001: ")
            and blocker["intervention"] == GUARD_INTERVENTION
            and blocker["basis"] == "INSTRUCTION" and blocker["current"] is True)


def _receipt_digest(receipt):
    # Guards are projections of the independent correction registry. Normalize
    # only that exact shape, so applying guard_receipt twice is idempotent.
    value = deepcopy(receipt)
    for action in value.get("actions", []):
        if _is_guard(action.get("blocker")):
            action["blocker"] = None
    return _digest(value)


def _release_owned_blocker(receipt, record, action_id):
    result = deepcopy(receipt)
    chosen = next((a for a in result["actions"] if a["id"] == action_id), None)
    if chosen is not None and (chosen["blocker"] == record["initial_blocker"]
                               or _is_guard(chosen["blocker"], record)):
        chosen["blocker"] = None
    return result


def validate_record(record):
    require(isinstance(record, dict) and RECORD_KEYS <= set(record)
            and set(record) <= RECORD_KEYS | SPEC_OPTIONAL_KEYS,
            "correction record: unexpected or missing fields")
    require(record["schema"] == SCHEMA, "Unsupported correction record schema")
    _validate_spec({k: record[k] for k in SPEC_KEYS | SPEC_OPTIONAL_KEYS if k in record})
    _binding(record["binding"])
    _object(record["goal"], {"baseline", "current"}, "record.goal")
    for value in record["goal"].values():
        _text(value, "record.goal")
    require(isinstance(record["baseline_criteria"], list) and 1 <= len(record["baseline_criteria"]) <= 256,
            "Baseline criteria required")
    ids = []
    for item in record["baseline_criteria"]:
        try:
            policy._object(item, policy.DEFINITION_KEYS, "baseline criterion")
            policy._definition(item, "baseline criterion")
        except ValueError as exc:
            raise RecoveryError(str(exc)) from exc
        ids.append(item["id"])
    require(len(ids) == len(set(ids)), "Duplicate baseline criterion")
    require(isinstance(record["criterion_ids"], list) and record["criterion_ids"]
            and all(isinstance(x, str) for x in record["criterion_ids"])
            and len(record["criterion_ids"]) == len(set(record["criterion_ids"]))
            and set(record["criterion_ids"]) <= set(ids), "Invalid preserved criterion IDs")
    blocker = record["initial_blocker"]
    if blocker is not None:
        require(isinstance(blocker, dict)
                and {"reason", "source_ref", "intervention"} <= set(blocker)
                and set(blocker) <= {"reason", "source_ref", "intervention", "basis", "current"},
                "Invalid historical blocker")
        for key in ("reason", "source_ref", "intervention"):
            _text(blocker[key], "historical blocker." + key)
        if "basis" in blocker:
            _enum(blocker["basis"], policy.BLOCKER_BASES, "historical blocker.basis")
        if "current" in blocker:
            require(type(blocker["current"]) is bool, "historical blocker.current must be boolean")
    _historical_authority(record["initial_authorization"])
    require(isinstance(record["invalidated_authority_refs"], list)
            and len(record["invalidated_authority_refs"]) <= 256, "Bounded invalidated authority references required")
    for ref in record["invalidated_authority_refs"]:
        _text(ref, "invalidated_authority_ref")
    require(len(record["invalidated_authority_refs"]) == len(set(record["invalidated_authority_refs"])),
            "Duplicate invalidated authority reference")
    _time(record["registered_at"], "registered_at")
    _enum(record["state"], STATES, "record.state")
    _text(record["target_action_id"], "target_action_id")
    require(isinstance(record["events"], list) and len(record["events"]) <= MAX_EVENTS, "Recovery history limit exceeded")
    event_ids = set()
    sequences = []
    for event in record["events"]:
        _object(event, {"id", "sequence", "assessed_at", "fingerprint", "observation", "authority_snapshot",
                        "result_state", "result_action_id"}, "recovery event")
        _text(event["id"], "event.id")
        require(event["id"] not in event_ids, "Duplicate recovery event")
        event_ids.add(event["id"])
        _hash(event["fingerprint"])
        require(type(event["sequence"]) is int and event["sequence"] > 0, "Positive event sequence required")
        sequences.append(event["sequence"])
        _time(event["assessed_at"], "event.assessed_at")
        _observation(event["observation"], record)
        _historical_authority(event["authority_snapshot"])
        require(event["id"] == event["observation"]["id"], "Event ID differs from observation")
        _enum(event["result_state"], STATES, "event.result_state")
        _text(event["result_action_id"], "event.result_action_id")
    require(isinstance(record["invalidations"], list) and len(record["invalidations"]) <= MAX_EVENTS,
            "Invalidation history limit exceeded")
    for invalidation in record["invalidations"]:
        _object(invalidation, {"source_ref", "observed_at", "sequence", "authority_snapshots"}, "invalidation")
        _text(invalidation["source_ref"], "invalidation.source_ref")
        _time(invalidation["observed_at"], "invalidation.observed_at")
        require(type(invalidation["sequence"]) is int and invalidation["sequence"] > 0,
                "Positive invalidation sequence required")
        sequences.append(invalidation["sequence"])
        require(isinstance(invalidation["authority_snapshots"], list)
                and len(invalidation["authority_snapshots"]) <= 256, "Bounded historical authorizations required")
        for snapshot in invalidation["authority_snapshots"]:
            _historical_authority(snapshot)
    require(sorted(sequences) == list(range(1, len(sequences) + 1)), "Recovery history sequence must be contiguous")
    resolution = record["resolution"]
    require((record["state"] == "RESOLVED") == (resolution is not None), "Resolution/state mismatch")
    if resolution is not None:
        _object(resolution, {"receipt_sha256", "valid_until", "event_id", "action_id"}, "resolution")
        _hash(resolution["receipt_sha256"])
        _time(resolution["valid_until"], "resolution.valid_until")
        require(resolution["event_id"] in event_ids, "Resolution event missing")
        require(resolution["action_id"] == record["target_action_id"], "Resolution action mismatch")
        event = next(e for e in record["events"] if e["id"] == resolution["event_id"])
        require(event["result_state"] == "RESOLVED" and event["result_action_id"] == resolution["action_id"],
                "Resolution does not match its observation result")
        require(_time(resolution["valid_until"], "resolution.valid_until")
                <= _time(event["observation"]["valid_until"], "observation.valid_until"),
                "Resolution cannot extend observation validity")
    _digest(record)
    return record


def _hash(value):
    require(isinstance(value, str) and len(value) == 64
            and all(char in "0123456789abcdef" for char in value), "SHA-256 required")


def _historical_authority(value):
    _object(value, {"state", "source_type", "source_ref"}, "historical authorization")
    _enum(value["state"], {"ALLOWED", "DENIED", "UNKNOWN", "REVOKED"}, "historical authorization state")
    _enum(value["source_type"], {"USER_INSTRUCTION", "HOST_PERMISSION", "EXPLICIT_APPROVAL"}, "historical authorization source")
    _text(value["source_ref"], "historical authorization reference")


def _authority_family(source_type):
    return "HOST" if source_type == "HOST_PERMISSION" else "USER"


def _invalidated_authority_refs(record):
    """A revocation invalidates references observed before it, not later grants."""
    snapshots = [record["initial_authorization"]]
    for item in sorted(record["events"] + record["invalidations"], key=lambda item: item["sequence"]):
        snapshots.extend([item["authority_snapshot"]] if "authority_snapshot" in item
                         else item["authority_snapshots"])
    invalidated = set(record["invalidated_authority_refs"])
    seen = set(invalidated)
    for snapshot in snapshots:
        seen.add(snapshot["source_ref"])
        if snapshot["state"] in {"DENIED", "REVOKED"}:
            invalidated.update(seen)
    return invalidated


def _current_history(record):
    """Only observations current at assessment establish a freshness watermark."""
    return [event["observation"] for event in record["events"]
            if event["observation"]["current"] is True
            and _time(event["observation"]["observed_at"], "observed_at")
            >= _time(record["registered_at"], "registered_at")
            and _time(event["observation"]["observed_at"], "observed_at")
            <= _time(event["assessed_at"], "assessed_at")
            < _time(event["observation"]["valid_until"], "valid_until")]


def _effect_history(record):
    uncertainty = record["prior_execution"] == "UNCERTAIN" or record["cause_kind"] == "UNCERTAIN_RESULT"
    completed = False
    for previous in sorted(_current_history(record), key=lambda item: _time(item["observed_at"], "observed_at")):
        if previous["prior_result"] == "UNCERTAIN":
            uncertainty = True
        elif previous["prior_result"] == "RECONCILED_NOT_EXECUTED":
            uncertainty = False
        elif previous["prior_result"] == "VERIFIED_COMPLETE":
            completed = True
    return uncertainty, completed


def _observation(value, record):
    _object(value, OBS_KEYS, "recovery observation")
    for name in ("id", "correction_id", "action_id", "source_ref"):
        _text(value[name], "observation." + name)
    require(value["correction_id"] == record["id"], "Observation belongs to another correction")
    _binding(value["binding"], record["binding"])
    require(type(value["current"]) is bool, "Observation currentness must be boolean")
    start = _time(value["observed_at"], "observed_at")
    end = _time(value["valid_until"], "valid_until")
    require(start < end, "Observation validity interval must be positive")
    require(_conditions(value["conditions"], True) == {c["id"] for c in record["conditions"]},
            "All original recovery conditions must be retained")
    _enum(value["relevance"], {"NEEDED", "OBSOLETE", "UNKNOWN"}, "relevance")
    _enum(value["prior_result"], {"NOT_RUN", "RECONCILED_NOT_EXECUTED", "VERIFIED_COMPLETE", "UNCERTAIN"}, "prior_result")
    lifting = value["restriction_resolution"]
    if lifting is not None:
        _object(lifting, {"restriction_ref", "authority"}, "restriction resolution")
        _text(lifting["restriction_ref"], "restriction_ref")
        try:
            policy._authority(lifting["authority"], "restriction resolution authority", record["binding"])
        except ValueError as exc:
            raise RecoveryError(str(exc)) from exc
    return value


def register(receipt, spec, now=None):
    """Describe an observed correction; preserve obligations, not permission."""
    require(not _stopped(receipt), "STOP forbids registering a new correction")
    _receipt(receipt)
    require(receipt["control"]["state"] == "RUNNING" and receipt["control"]["current"] is True,
            "Current RUNNING control required")
    _validate_spec(spec)
    action = next((a for a in receipt["actions"] if a["id"] == spec["action_id"]), None)
    require(action is not None, "Correction action missing from current receipt")
    at = _now(now)
    state = ("PROHIBITED" if spec["cause_kind"] == "PROHIBITION" else "RECONCILE"
             if spec["prior_execution"] == "UNCERTAIN" or spec["cause_kind"] == "UNCERTAIN_RESULT"
             else "WAITING_CONDITIONS")
    if spec["expires_at"] is not None and at >= _time(spec["expires_at"], "expires_at"):
        state = "EXPIRED"
    record = {**deepcopy(spec), "schema": SCHEMA, "binding": deepcopy(receipt["binding"]),
              "goal": {k: receipt["goal"][k] for k in ("baseline", "current")},
              "baseline_criteria": deepcopy(receipt["baseline_criteria"]),
              "criterion_ids": deepcopy(action["criterion_ids"]),
              "initial_blocker": deepcopy(action["blocker"]),
              "initial_authorization": {k: action["authorization"][k] for k in ("state", "source_type", "source_ref")},
              "registered_at": at.isoformat(), "state": state, "target_action_id": action["id"],
              "events": [], "invalidations": [], "invalidated_authority_refs": [], "resolution": None}
    validate_record(record)
    return record


def _resolved(record, receipt, at):
    resolution = record["resolution"]
    return (record["state"] == "RESOLVED" and resolution is not None
            and at < _time(resolution["valid_until"], "resolution.valid_until")
            and (record["expires_at"] is None or at < _time(record["expires_at"], "expires_at"))
            and resolution["receipt_sha256"] == _receipt_digest(receipt))


def guard_receipt(receipt, records, now=None):
    """Project unresolved corrections into existing v1 action blockers.

    This is idempotent and leaves independent branches and proved completion
    available. Actual blockers are never overwritten by a projection.
    """
    if _stopped(receipt):
        return deepcopy(receipt)
    _receipt(receipt)
    require(isinstance(records, list) and len(records) <= MAX_RECORDS, "Bounded correction list required")
    result = deepcopy(receipt)
    at = _now(now)
    seen = set()
    unresolved = []
    for record in records:
        validate_record(record)
        require(record["id"] not in seen, "Duplicate correction ID")
        seen.add(record["id"])
        _receipt(receipt, record)
        if _resolved(record, receipt, at):
            # Only a generated guard for this exact record may be removed.
            for action in result["actions"]:
                if _is_guard(action["blocker"], record):
                    action["blocker"] = None
        else:
            unresolved.append(record)
    # Remove resolved projections before adding unresolved ones. Otherwise an
    # existing guard can hide a second correction and be removed later in the
    # same pass, accidentally enabling the action depending on registry order.
    for record in unresolved:
        for action in result["actions"]:
            if set(action["criterion_ids"]) & set(record["criterion_ids"]):
                if action["blocker"] is None:
                    action["blocker"] = _guard(record)
    return result


def invalidate(record, source_ref, now=None, *, receipt=None):
    """Remember a material change and observed revocations without granting power."""
    validate_record(record)
    _text(source_ref, "invalidation.source_ref")
    result = deepcopy(record)
    if result["state"] in {"EXPIRED", "OBSOLETE"}:
        return result
    at = _now(now).isoformat()
    snapshots = []
    if receipt is not None:
        _receipt(receipt, record)
        for action in receipt["actions"]:
            if set(action["criterion_ids"]) & set(record["criterion_ids"]):
                snapshot = {k: action["authorization"][k] for k in ("state", "source_type", "source_ref")}
                if snapshot not in snapshots:
                    snapshots.append(snapshot)
    if any(item["source_ref"] == source_ref and item["observed_at"] == at
           and item["authority_snapshots"] == snapshots for item in record["invalidations"]):
        return result
    require(len(result["invalidations"]) < MAX_EVENTS, "Invalidation history full; preserve before starting a new scope")
    result["invalidations"].append({"source_ref": source_ref, "observed_at": at,
                                    "sequence": len(result["events"]) + len(result["invalidations"]) + 1,
                                    "authority_snapshots": snapshots})
    result["resolution"] = None
    if result["state"] == "RESOLVED":
        result["state"] = ("PROHIBITED" if result["cause_kind"] == "PROHIBITION" else "RECONCILE"
                           if result["prior_execution"] == "UNCERTAIN" or result["cause_kind"] == "UNCERTAIN_RESULT"
                           else "WAITING_CONDITIONS")
    validate_record(result)
    return result


def rebind(record, new_receipt, now=None):
    """Carry restrictions across a candidate/scope/session change of one goal.

    The session must archive the previous record. No authorization or resolved
    proof is transferred; current receipt authority remains the sole input.
    """
    require(not _stopped(new_receipt), "STOP forbids rebinding a correction")
    validate_record(record)
    _receipt(new_receipt)
    for key in ("project_id", "mission_id", "goal_id", "goal_revision"):
        require(new_receipt["binding"][key] == record["binding"][key],
                "Rebind cannot cross project, mission, goal, or goal revision")
    require({k: new_receipt["goal"][k] for k in ("baseline", "current")} == record["goal"],
            "Rebind cannot change the objective")
    require(new_receipt["baseline_criteria"] == record["baseline_criteria"],
            "Rebind cannot discard or change acceptance criteria")
    at = _now(now)
    if new_receipt["binding"] == record["binding"]:
        return invalidate(record, "bago5:rebind:unchanged-binding", at, receipt=new_receipt)
    result = deepcopy(record)
    result["binding"] = deepcopy(new_receipt["binding"])
    result["registered_at"] = at.isoformat()
    result["events"] = []
    result["invalidations"] = []
    result["resolution"] = None
    result["invalidated_authority_refs"] = sorted(_invalidated_authority_refs(record))
    uncertainty, completed = _effect_history(record)
    if uncertainty or completed:
        result["prior_execution"] = "UNCERTAIN"
    candidates = [action for action in new_receipt["actions"]
                  if set(record["criterion_ids"]) <= set(action["criterion_ids"])]
    action = next((a for a in candidates if a["id"] == record["target_action_id"]), None)
    action = action or next((a for a in candidates if a["id"] == record["action_id"]), None)
    action = action or (candidates[0] if candidates else None)
    result["target_action_id"] = action["id"] if action else record["target_action_id"]
    # A candidate change never transfers ownership of a different restriction.
    result["initial_blocker"] = deepcopy(record["initial_blocker"])
    result["initial_authorization"] = ({k: action["authorization"][k] for k in ("state", "source_type", "source_ref")}
                                       if action else {"state": "UNKNOWN",
                                                       "source_type": record["initial_authorization"]["source_type"],
                                                       "source_ref": "bago5:rebind:unobserved-authority"})
    result["state"] = ("PROHIBITED" if result["cause_kind"] == "PROHIBITION" else "RECONCILE"
                       if result["prior_execution"] == "UNCERTAIN" or result["cause_kind"] == "UNCERTAIN_RESULT"
                       else "WAITING_CONDITIONS")
    if record["state"] in {"EXPIRED", "OBSOLETE"}:
        result["state"] = record["state"]
    elif record["expires_at"] is not None and at >= _time(record["expires_at"], "expires_at"):
        result["state"] = "EXPIRED"
    validate_record(result)
    return result


def reassess(record, receipt, observation, now=None):
    """Use a fresh observation and current receipt, then delegate to assess.

    RESOLVED means that this cause was addressed. Other blockers, permissions,
    dependencies and the host/controller still decide whether work may proceed.
    """
    if _stopped(receipt):
        return {"record": deepcopy(record), "receipt": deepcopy(receipt),
                "policy_result": policy.assess(receipt), "changed": False}
    validate_record(record)
    _receipt(receipt, record)
    _observation(observation, record)
    at = _now(now)
    # The owned historical blocker and its resolved projection are equivalent
    # inputs for event deduplication; all other receipt facts remain bound.
    fingerprint = _digest({"observation": observation,
                           "receipt_sha256": _receipt_digest(_release_owned_blocker(
                               receipt, record, observation["action_id"]))})
    prior = next((e for e in record["events"] if e["id"] == observation["id"]), None)
    if prior:
        require(prior["fingerprint"] == fingerprint, "Recovery event ID reused with different content")
        current = (_release_owned_blocker(receipt, record, observation["action_id"])
                   if record["resolution"] is not None
                   and record["resolution"]["event_id"] == observation["id"] else receipt)
        result_receipt = guard_receipt(current, [record], at)
        return {"record": deepcopy(record), "receipt": result_receipt,
                "policy_result": policy.assess(result_receipt), "changed": False}
    require(len(record["events"]) < MAX_EVENTS, "Recovery history full; preserve before starting a new scope")
    action = next((a for a in receipt["actions"] if a["id"] == observation["action_id"]), None)
    require(action is not None, "Reassessed action is missing")
    require(set(record["criterion_ids"]) <= set(action["criterion_ids"]), "Replacement loses original obligations")
    previous_actions = {record["action_id"], record["target_action_id"]}
    previous_actions.update(event["result_action_id"] for event in record["events"])
    require(all(a["id"] not in previous_actions - {observation["action_id"]} for a in receipt["actions"]),
            "Replacement must not leave an earlier corrected action executable")
    result_record = deepcopy(record)
    result_record["target_action_id"] = action["id"]
    result_record["resolution"] = None
    valid_time = (_time(observation["observed_at"], "observed_at") <= at
                  < _time(observation["valid_until"], "valid_until"))
    history = _current_history(record)
    latest_change = max([_time(record["registered_at"], "registered_at")]
                        + [_time(item["observed_at"], "invalidation.observed_at")
                           for item in record["invalidations"]]
                        + [_time(item["observed_at"], "history.observed_at") for item in history])
    valid_time = valid_time and _time(observation["observed_at"], "observed_at") >= latest_change
    current = (valid_time and observation["current"] is True
               and receipt["control"]["state"] == "RUNNING" and receipt["control"]["current"] is True)
    conditions_met = all(c["state"] == "SATISFIED" for c in observation["conditions"])
    denied_refs = _invalidated_authority_refs(record)
    historical_denial = bool(denied_refs)
    authority = action["authorization"]
    renewed_authority = (authority["state"] == "ALLOWED" and authority["current"] is True
                         and authority["source_ref"] not in denied_refs)
    lifting = observation["restriction_resolution"]
    lifted = (isinstance(lifting, dict) and lifting["restriction_ref"] == record["source_ref"]
              and lifting["authority"]["state"] == "ALLOWED" and lifting["authority"]["current"] is True
              and lifting["authority"]["source_ref"] != record["source_ref"]
              and _authority_family(lifting["authority"]["source_type"])
              == _authority_family(record.get("restriction_source_type", "USER_INSTRUCTION")))
    uncertainty, completed_effect = _effect_history(record)
    unresolved_effect = (observation["prior_result"] == "UNCERTAIN"
                         or uncertainty and not (current and observation["prior_result"]
                                                 in {"RECONCILED_NOT_EXECUTED", "VERIFIED_COMPLETE"}))
    current_policy = policy.assess(receipt)
    if completed_effect or observation["prior_result"] == "VERIFIED_COMPLETE":
        # A verified completed effect cannot be sent again. Until the ordinary
        # receipt proves each affected criterion, reconcile instead of retrying.
        pending = set(current_policy.get("pending_criteria", [])) | set(current_policy.get("supporting_criteria", []))
        unresolved_effect = bool(pending & set(record["criterion_ids"]))
    state = "WAITING_CONDITIONS"
    if record["state"] in {"OBSOLETE", "EXPIRED"}:
        state = record["state"]
    elif record["expires_at"] is not None and at >= _time(record["expires_at"], "expires_at"):
        state = "EXPIRED"
    elif current and observation["relevance"] == "OBSOLETE":
        state = "OBSOLETE"
    elif record["cause_kind"] == "PROHIBITION" and not (current and lifted and renewed_authority):
        state = "PROHIBITED"
    elif unresolved_effect:
        state = "RECONCILE"
    elif (current and conditions_met and observation["relevance"] == "NEEDED"
          and observation["source_ref"] != record["source_ref"]
          and (record["cause_kind"] != "AUTHORITY" and not historical_denial or renewed_authority)):
        state = "RESOLVED"
    result_record["state"] = state
    result_receipt = deepcopy(receipt)
    if state == "RESOLVED":
        result_receipt = _release_owned_blocker(result_receipt, record, action["id"])
        until = _time(observation["valid_until"], "valid_until")
        if record["expires_at"] is not None:
            until = min(until, _time(record["expires_at"], "expires_at"))
        result_record["resolution"] = {"receipt_sha256": _receipt_digest(result_receipt),
                                       "valid_until": until.isoformat(), "event_id": observation["id"],
                                       "action_id": action["id"]}
    result_record["events"].append({"id": observation["id"], "fingerprint": fingerprint,
                                     "sequence": len(record["events"]) + len(record["invalidations"]) + 1,
                                     "assessed_at": at.isoformat(),
                                     "observation": deepcopy(observation),
                                     "authority_snapshot": {k: authority[k] for k in ("state", "source_type", "source_ref")},
                                     "result_state": state,
                                     "result_action_id": action["id"]})
    result_receipt = guard_receipt(result_receipt, [result_record], at)
    return {"record": result_record, "receipt": result_receipt,
            "policy_result": policy.assess(result_receipt), "changed": True}
