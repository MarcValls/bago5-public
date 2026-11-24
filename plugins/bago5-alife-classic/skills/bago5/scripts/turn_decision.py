#!/usr/bin/env python3
"""Assess a scoped turn receipt. No tools, persistence, authentication or effects.

Inputs are claims made by the caller, not authority minted by this evaluator.
The host must observe and enforce actual permissions before every effect.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "bago5.turn-decision.v1"
RESULT_SCHEMA = "bago5.turn-decision.result.v1"
HOSTS = {"CHAT", "WORK", "CODEX", "COPILOT"}
BINDING_KEYS = {"project_id", "mission_id", "goal_id", "goal_revision", "candidate_id", "scope_id", "session_id"}
DEFINITION_KEYS = {"id", "description", "required", "expected_basis", "expected_outcome", "min_independent_origins"}
BLOCKER_BASES = {"OBSERVATION", "CAPABILITY", "AUTHORITY", "INSTRUCTION", "REQUIRED_INPUT"}
LIMIT = "Declared metadata only; does not authenticate evidence, grant permission, execute tools or intercept the host."


class InvalidReceipt(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise InvalidReceipt(message)


def _object(value, keys, label, optional=()):
    _require(isinstance(value, dict), label + ": expected object")
    _require(set(value) >= set(keys) and set(value) <= set(keys) | set(optional), label + ": missing or unexpected fields")
    return value


def _text(value, label):
    _require(isinstance(value, str) and 0 < len(value) <= 10000 and bool(value.strip()), label + ": expected nonempty bounded text")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise InvalidReceipt(label + ": invalid Unicode text") from exc
    return value


def _enum(value, options, label):
    _require(isinstance(value, str) and value in options, label + ": invalid enum")
    return value


def _bool(value, label):
    _require(type(value) is bool, label + ": expected boolean")
    return value


def _list(value, label, nonempty=False, maximum=1024):
    _require(isinstance(value, list) and int(nonempty) <= len(value) <= maximum, label + ": invalid bounded list")
    return value


def _ids(value, label, nonempty=False):
    _list(value, label, nonempty)
    for item in value:
        _text(item, label)
    _require(len(set(value)) == len(value), label + ": duplicate IDs")
    return value


def _binding(value, label, expected=None):
    _object(value, BINDING_KEYS, label)
    for key in BINDING_KEYS - {"goal_revision"}:
        _text(value[key], label + "." + key)
    _require(type(value["goal_revision"]) is int and value["goal_revision"] >= 1, label + ": invalid goal_revision")
    _require(expected is None or value == expected, label + ": wrong project, mission, goal, revision, candidate, scope or session")
    return value


def _authority(value, label, binding):
    _object(value, {"state", "source_type", "source_ref", "current", "binding"}, label)
    _enum(value["state"], {"ALLOWED", "DENIED", "UNKNOWN", "REVOKED"}, label + ".state")
    _enum(value["source_type"], {"USER_INSTRUCTION", "HOST_PERMISSION", "EXPLICIT_APPROVAL"}, label + ".source_type")
    _text(value["source_ref"], label + ".source_ref")
    _bool(value["current"], label + ".current")
    _binding(value["binding"], label + ".binding", binding)
    return value["state"] == "ALLOWED" and value["current"] is True


def _definition(value, label):
    for key in ("id", "description"):
        _text(value[key], label + "." + key)
    _bool(value["required"], label + ".required")
    _enum(value["expected_basis"], {"OBSERVATION", "DECLARATION", "ARTIFACT"}, label + ".expected_basis")
    _enum(value["expected_outcome"], {"PASS", "FAIL"}, label + ".expected_outcome")
    _require(type(value["min_independent_origins"]) is int and 1 <= value["min_independent_origins"] <= 32, label + ": invalid minimum origins")
    return {key: value[key] for key in DEFINITION_KEYS}


def _result(decision, reasons, **details):
    # Readiness to report a pause is distinct from completion of the task.
    # An incomplete receipt never creates permission to execute any operation.
    closure = {"report_ready": decision in {"CLOSE", "HANDOFF", "STOP"},
               "review_required": decision == "BLOCKED",
               "basis": {"CLOSE": "SATISFIED_CRITERIA", "HANDOFF": "REAL_HANDOFF",
                         "STOP": "STOP_OR_REVOCATION", "CONTINUE": "LOCAL_WORK_AVAILABLE",
                         "BLOCKED": "INCOMPLETE_RECEIPT"}[decision]}
    return {"schema": RESULT_SCHEMA, "decision": decision, "reasons": reasons,
            "pending_criteria": [], "eligible_actions": [], "blockers": [],
            "independent_origins": {}, "closure": closure, "limit": LIMIT, **details}


def _status_only(value):
    """Recognize bare result labels, not the semantics of arbitrary prose."""
    normalized = "".join(char for char in value.upper() if char.isalnum())
    return normalized in {"NOTRUN", "NOCOMPROBADO", "NOCOMPROBADA", "NOCOMPROBADOS",
                          "NOCOMPROBADAS", "PENDING", "PENDIENTE", "PENDIENTES",
                          "BLOCKED", "BLOQUEADO", "BLOQUEADA", "FAIL", "UNKNOWN",
                          "NORECUPERADO", "NOVERIFICADO"}


def _blocker_gaps(blocker):
    if blocker is None:
        return ["Identify the impeded operation's current cause, source and minimum intervention."]
    gaps = []
    if blocker.get("basis") not in BLOCKER_BASES:
        gaps.append("Identify whether the cause is an observation, capability, authority, instruction or required input.")
    if blocker.get("current") is not True:
        gaps.append("Establish that the cited cause still applies after the latest result or human intervention.")
    for key in ("reason", "source_ref", "intervention"):
        if _status_only(blocker[key]):
            gaps.append(key + ": a result/status label does not substantiate an impediment.")
    return gaps


def _blocked_closure(actions, needed, satisfied):
    """Check declared reasons for pausing, without authenticating their sources.

    Existing v1 blockers remain readable. New final reports need their cause
    type and currentness; missing metadata asks for bounded review, never a
    dangerous attempt, secret, new permission or automatic retry.
    """
    relevant = [a for a in actions if set(a["criterion_ids"]) & needed]
    direct = {a["id"] for a in relevant if not _blocker_gaps(a["blocker"])}
    explained = {cid for a in relevant if a["id"] in direct
                 for cid in a["criterion_ids"] if cid in needed}
    dependent = set()
    while True:
        previous = set(explained)
        for action in relevant:
            # A concrete upstream blocker can explain the downstream pause.
            # Do not invent an independent blocker for every dependent step.
            if action["blocker"] is None and any(
                    cid in explained and not satisfied[cid] for cid in action["depends_on"]):
                dependent.add(action["id"])
                explained.update(set(action["criterion_ids"]) & needed)
        if previous == explained:
            break
    incomplete = [{"action_id": a["id"], "missing": _blocker_gaps(a["blocker"])}
                  for a in relevant if a["id"] not in direct | dependent]
    mapped = {cid for a in relevant for cid in a["criterion_ids"]}
    unmapped = sorted(needed - mapped)
    review = bool(incomplete or unmapped or not relevant)
    return {"report_ready": not review, "review_required": review,
            "basis": "INCOMPLETE_BLOCKER" if review else "DOCUMENTED_BLOCKER",
            "unmapped_criteria": unmapped, "incomplete_actions": incomplete,
            "documented_action_ids": sorted(direct),
            "dependent_action_ids": sorted(dependent)}


def _assess(data):
    _object(data, {"schema", "binding", "current_host", "goal", "control", "baseline_criteria", "criteria", "evidence", "actions"}, "receipt")
    _require(data["schema"] == SCHEMA, "receipt: unsupported schema")
    binding = _binding(data["binding"], "binding")
    current_host = _enum(data["current_host"], HOSTS, "current_host")
    control = _object(data["control"], {"state", "source_ref", "current", "binding"}, "control")
    _enum(control["state"], {"RUNNING", "STOP", "REVOKED", "UNKNOWN"}, "control.state")
    _text(control["source_ref"], "control.source_ref")
    _bool(control["current"], "control.current")
    _binding(control["binding"], "control.binding", binding)
    if control["state"] == "UNKNOWN" or not control["current"]:
        return _result("BLOCKED", ["Current STOP/revocation state has not been established."],
                       closure={"report_ready": True, "review_required": False,
                                "basis": "CONTROL_NOT_ESTABLISHED"})

    goal = _object(data["goal"], {"baseline", "current", "change_authority"}, "goal")
    _text(goal["baseline"], "goal.baseline")
    _text(goal["current"], "goal.current")
    change_allowed = False
    if goal["change_authority"] is not None:
        change_allowed = _authority(goal["change_authority"], "goal.change_authority", binding)
        change_allowed = change_allowed and goal["change_authority"]["source_type"] in {"USER_INSTRUCTION", "EXPLICIT_APPROVAL"}
    _require(goal["baseline"] == goal["current"] or change_allowed, "Goal changed without a current explicit authorization reference.")

    baseline = {}
    for item in _list(data["baseline_criteria"], "baseline_criteria", True, 256):
        _object(item, DEFINITION_KEYS, "baseline criterion")
        definition = _definition(item, "baseline criterion")
        _require(item["id"] not in baseline, "baseline_criteria: duplicate ID")
        baseline[item["id"]] = definition
    criteria = {}
    for item in _list(data["criteria"], "criteria", True, 256):
        _object(item, DEFINITION_KEYS | {"status", "evidence_ids", "waiver"}, "criterion")
        definition = _definition(item, "criterion")
        _require(item["id"] not in criteria, "criteria: duplicate ID")
        _require(definition == baseline.get(item["id"]), "criterion " + item["id"] + ": definition differs from baseline")
        _enum(item["status"], {"PASS", "PENDING", "BLOCKED", "FAIL", "NOT_RUN", "WAIVED"}, "criterion.status")
        _ids(item["evidence_ids"], "criterion.evidence_ids")
        if item["status"] == "WAIVED":
            waiver = _object(item["waiver"], {"reason", "authority"}, "waiver")
            _text(waiver["reason"], "waiver.reason")
            _require(_authority(waiver["authority"], "waiver.authority", binding) and waiver["authority"]["source_type"] in {"USER_INSTRUCTION", "EXPLICIT_APPROVAL"}, "waiver: explicit current scope decision required")
        else:
            _require(item["waiver"] is None, "waiver only applies to WAIVED criteria")
        criteria[item["id"]] = item
    _require(set(criteria) == set(baseline), "A baseline criterion is missing; summaries cannot discard obligations.")

    evidence = {}
    origins = {}
    precise_sources = {}
    for item in _list(data["evidence"], "evidence"):
        _object(item, {"id", "criterion_id", "binding", "kind", "outcome", "source_ref", "origin_id", "derived_from"}, "evidence")
        _text(item["id"], "evidence.id")
        _require(item["id"] not in evidence, "evidence: duplicate ID")
        _require(isinstance(item["criterion_id"], str) and item["criterion_id"] in criteria, "evidence: unknown criterion")
        _binding(item["binding"], "evidence.binding", binding)
        _enum(item["kind"], {"OBSERVATION", "DECLARATION", "ARTIFACT", "DERIVED"}, "evidence.kind")
        _enum(item["outcome"], {"PASS", "FAIL", "UNKNOWN"}, "evidence.outcome")
        _text(item["source_ref"], "evidence.source_ref")
        _ids(item["derived_from"], "evidence.derived_from", item["kind"] == "DERIVED")
        if item["kind"] == "DERIVED":
            _require(item["origin_id"] is None, "derived evidence cannot invent a primary origin")
        else:
            _text(item["origin_id"], "evidence.origin_id")
            _require(not item["derived_from"], "primary evidence must not have parents")
            # One observed event can legitimately support several criteria.
            # Independence is counted per criterion, never per copied record.
            origin_key = (item["criterion_id"], item["origin_id"])
            signature = (item["kind"], item["outcome"], item["source_ref"])
            _require(origin_key not in origins or origins[origin_key] == signature, "One origin has conflicting primary observations.")
            origins[origin_key] = signature
            # source_ref must identify the concrete primary event/check, not a
            # generic document or service. Renaming its origin is not new proof.
            source_key = (item["criterion_id"], item["source_ref"])
            _require(source_key not in precise_sources or precise_sources[source_key] == item["origin_id"], "Different origin IDs alias the same precise primary source.")
            precise_sources[source_key] = item["origin_id"]
        evidence[item["id"]] = item

    root_cache = {}
    depth_cache = {}
    def roots(eid, trail=()):
        _require(eid in evidence, "Evidence lineage refers to a missing record.")
        _require(eid not in trail and len(trail) < 128, "Evidence lineage is cyclic or exceeds the depth limit.")
        if eid in root_cache:
            _require(len(trail) + depth_cache[eid] <= 128, "Evidence lineage exceeds the depth limit.")
            return root_cache[eid]
        item = evidence[eid]
        if item["kind"] != "DERIVED":
            value = {item["origin_id"]}
            depth = 1
        else:
            value = set()
            depth = 1
            for parent in item["derived_from"]:
                _require(parent in evidence, "Evidence lineage refers to a missing record.")
                prior = evidence[parent]
                _require(prior["criterion_id"] == item["criterion_id"] and prior["outcome"] == item["outcome"], "Derived evidence changes the criterion or outcome of its source.")
                value |= roots(parent, trail + (eid,))
                depth = max(depth, 1 + depth_cache[parent])
        _require(len(trail) + depth <= 128, "Evidence lineage exceeds the depth limit.")
        root_cache[eid] = value
        depth_cache[eid] = depth
        return value

    for eid in evidence:
        roots(eid)
    satisfied = {}
    independent = {}
    issues = []
    conflicted = set()
    for cid, criterion in criteria.items():
        selected = set()
        for eid in criterion["evidence_ids"]:
            _require(eid in evidence and evidence[eid]["criterion_id"] == cid, "Criterion refers to missing or unrelated evidence.")
            selected |= roots(eid)
        active_outcomes = {item["outcome"] for item in evidence.values() if item["criterion_id"] == cid and item["outcome"] != "UNKNOWN"}
        if len(active_outcomes) > 1:
            conflicted.add(cid)
            issues.append(cid + ": conflicting current evidence; reconcile this criterion before dependent work")
        relevant = {oid for oid in selected if origins[(cid, oid)][:2] == (criterion["expected_basis"], criterion["expected_outcome"])}
        independent[cid] = sorted(relevant)
        proof_sufficient = len(relevant) >= criterion["min_independent_origins"]
        satisfied[cid] = criterion["status"] == "WAIVED" or (cid not in conflicted and criterion["status"] == "PASS" and proof_sufficient)
        if criterion["status"] == "PASS" and not proof_sufficient:
            issues.append(cid + ": claimed PASS lacks the required basis/outcome/independent origins")

    actions = []
    action_ids = set()
    for action in _list(data["actions"], "actions", maximum=256):
        _object(action, {"id", "binding", "criterion_ids", "depends_on", "target_host", "capability", "authorization", "preconditions", "blocker", "handoff"}, "action")
        _text(action["id"], "action.id")
        _require(action["id"] not in action_ids, "actions: duplicate ID")
        action_ids.add(action["id"])
        _binding(action["binding"], "action.binding", binding)
        for key in ("criterion_ids", "depends_on"):
            _ids(action[key], "action." + key, key == "criterion_ids")
            _require(set(action[key]) <= set(criteria), "action references an unknown criterion")
        _require(not set(action["criterion_ids"]) & set(action["depends_on"]), "action depends on the criterion it must establish")
        _enum(action["target_host"], HOSTS, "action.target_host")
        capability = _object(action["capability"], {"state", "source_ref", "current", "binding"}, "capability")
        _enum(capability["state"], {"AVAILABLE", "UNAVAILABLE", "UNKNOWN"}, "capability.state")
        _text(capability["source_ref"], "capability.source_ref")
        _bool(capability["current"], "capability.current")
        _binding(capability["binding"], "capability.binding", binding)
        _authority(action["authorization"], "action.authorization", binding)
        _enum(action["preconditions"], {"SATISFIED", "UNSATISFIED", "UNKNOWN"}, "action.preconditions")
        if action["blocker"] is not None:
            _object(action["blocker"], {"reason", "source_ref", "intervention"}, "blocker",
                    optional={"basis", "current"})
            for key in ("reason", "source_ref", "intervention"):
                _text(action["blocker"][key], "blocker." + key)
            if "basis" in action["blocker"]:
                _enum(action["blocker"]["basis"], BLOCKER_BASES, "blocker.basis")
            if "current" in action["blocker"]:
                _bool(action["blocker"]["current"], "blocker.current")
        if action["target_host"] == current_host:
            _require(action["handoff"] is None, "No handoff to the current host; an explicit prompt is its own deliverable.")
        else:
            handoff = _object(action["handoff"], {"reason", "source_ref", "current"}, "handoff")
            _enum(handoff["reason"], {"CAPABILITY_UNAVAILABLE_HERE", "USER_REQUESTED_HOST"}, "handoff.reason")
            _text(handoff["source_ref"], "handoff.source_ref")
            _bool(handoff["current"], "handoff.current")
        actions.append(action)

    pending = [cid for cid, c in criteria.items() if c["required"] and not satisfied[cid]]
    details = {"binding": binding, "pending_criteria": pending, "independent_origins": independent, "criterion_issues": issues,
               "conflicted_criteria": [cid for cid in criteria if cid in conflicted]}
    if not pending:
        return _result("CLOSE", ["Every mandatory criterion is satisfied or explicitly waived for this scope."], **details)

    # Optional criteria can be necessary prerequisites for a mandatory result.
    # Follow only declared dependencies of actions that establish still-needed
    # criteria; unrelated optional work cannot extend the user's scope.
    needed = set(pending)
    while True:
        prerequisites = {cid for action in actions if set(action["criterion_ids"]) & needed
                         for cid in action["depends_on"] if not satisfied[cid]}
        expanded = needed | prerequisites
        if expanded == needed:
            break
        needed = expanded
    details["supporting_criteria"] = [cid for cid in criteria if cid in needed and cid not in pending]

    eligible_local, eligible_remote, blockers = [], [], []
    for action in actions:
        if not set(action["criterion_ids"]) & needed:
            continue
        failures = []
        if set(action["criterion_ids"]) & conflicted:
            failures.append("Action addresses a criterion with conflicting current evidence; reconcile its observations first.")
        if not all(satisfied[cid] for cid in action["depends_on"]):
            failures.append("Dependencies are not yet satisfied.")
        if action["preconditions"] != "SATISFIED":
            failures.append("Preconditions are " + action["preconditions"] + ".")
        if action["capability"]["state"] != "AVAILABLE" or not action["capability"]["current"]:
            failures.append("Current capability is not established as available.")
        if action["authorization"]["state"] != "ALLOWED" or not action["authorization"]["current"]:
            failures.append("Current authorization is not established as allowed.")
        if action["blocker"] is not None:
            failures.append(action["blocker"]["reason"])
        if action["handoff"] is not None and not action["handoff"]["current"]:
            failures.append("Reason for changing host has not been established as current.")
        if failures:
            blockers.append({"action_id": action["id"], "reasons": failures, "observed_blocker": action["blocker"]})
        elif action["target_host"] == current_host:
            eligible_local.append(action["id"])
        else:
            eligible_remote.append({"action_id": action["id"], "target_host": action["target_host"], "reason": action["handoff"]["reason"], "source_ref": action["handoff"]["source_ref"], "recipient_must_revalidate": True})
    details["blockers"] = blockers
    if eligible_local:
        return _result("CONTINUE", ["Authorized work remains executable in this session."], eligible_actions=eligible_local, **details)
    if eligible_remote:
        return _result("HANDOFF", ["Remaining executable work requires the documented other host; receiving execution is NOT_RUN."], handoffs=eligible_remote, **details)
    closure = _blocked_closure(actions, needed, satisfied)
    reasons = ["Mandatory work remains, with no currently established executable action."]
    if closure["review_required"]:
        reasons.append("The pause is not fully substantiated: review omitted actions or blocker details before reporting. NOT_RUN alone is not a cause; this review grants no operation permission.")
    return _result("BLOCKED", reasons, closure=closure, **details)


def assess(data):
    """Return one decision; malformed/unknown inputs never authorize progress.

    A declared STOP/revocation takes precedence even over an otherwise malformed
    receipt. This is conservative refusal, not validation of that declaration.
    """
    if isinstance(data, dict) and isinstance(data.get("control"), dict) and isinstance(data["control"].get("state"), str) and data["control"]["state"] in {"STOP", "REVOKED"}:
        return _result("STOP", ["STOP or revocation is declared; no new action or closing write is evaluated."])
    try:
        return _assess(data)
    except InvalidReceipt as exc:
        return _result("BLOCKED", [str(exc)], validation="INVALID")
    except (KeyError, TypeError, ValueError, RecursionError):
        return _result("BLOCKED", ["Malformed receipt."], validation="INVALID")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidReceipt("Duplicate JSON key.")
        result[key] = value
    return result


def parse_receipt(raw):
    if len(raw) > 2_000_000:
        raise InvalidReceipt("Receipt exceeds input limit.")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw, object_pairs_hook=_unique_object,
                      parse_constant=lambda value: (_ for _ in ()).throw(InvalidReceipt("Non-finite JSON value.")))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", help="JSON receipt path, or - for standard input")
    args = parser.parse_args(argv)
    try:
        if args.receipt == "-":
            raw = sys.stdin.buffer.read(2_000_001)
        else:
            with Path(args.receipt).open("rb") as handle:
                raw = handle.read(2_000_001)
        result = assess(parse_receipt(raw))
    except (OSError, ValueError, UnicodeError, RecursionError):
        result = _result("BLOCKED", ["Receipt could not be read as bounded, unique-key UTF-8 JSON."], validation="INVALID")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 2 if result["decision"] in {"BLOCKED", "STOP"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
