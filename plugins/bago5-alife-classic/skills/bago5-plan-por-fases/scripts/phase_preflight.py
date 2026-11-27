#!/usr/bin/env python3
"""Classify declared phase evidence. Never probe, grant permission or run work."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unicodedata

try:
    from jsonschema import Draft202012Validator, FormatChecker
except ImportError:
    Draft202012Validator = None
    FormatChecker = None

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = SKILL_ROOT / "schemas" / "phase-preflight.schema.json"
AREAS = {"tools", "access", "authorization", "execution", "verification", "delivery", "dependencies"}
AUTHORIZATION_SOURCES = {"USER_INSTRUCTION", "EXPLICIT_APPROVAL"}
CAPABILITY_SOURCES = {"HOST_TOOL", "AUTHENTICATED_ACCESS", "SOURCE_READ", "TARGET_PROBE"}
LIMIT = "declared evidence only; no host probe, authorization or tool interception"


def context_key(context):
    """Bind observations to this exact context; a hash is not execution evidence."""
    return hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def result(decision, reasons, **details):
    return {"decision": decision, "can_start": decision == "GO", "reasons": reasons,
            "can_prepare": False, "preparation_steps": [], "limit": LIMIT, **details}


def _action_key(text):
    """Detect explicit duplicate actions, without interpreting their semantics."""
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split()).strip(" .,:;!?¡¿")


def _timestamp(raw):
    try:
        stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        return stamp.astimezone(dt.timezone.utc)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return None


def _fresh(raw, now, max_age):
    stamp = _timestamp(raw)
    return stamp is not None and -60 <= (now - stamp).total_seconds() <= max_age


def _unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate_json_key:" + key)
        obj[key] = value
    return obj


def _reject_constant(value):
    raise ValueError("nonfinite_json_number:" + value)


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                      parse_constant=_reject_constant)


def _target_assessor():
    path = SKILL_ROOT.parent / "bago5" / "scripts" / "target_preflight.py"
    spec = importlib.util.spec_from_file_location("bago5_target_preflight_for_phase", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.assess


def assess(receipt, current_context, now=None):
    """Evaluate the receipt against separately observed current context."""
    if isinstance(receipt, dict) and receipt.get("stop") is True:
        return result("BLOQUEADO", ["STOP"])
    if Draft202012Validator is None:
        return result("NO_COMPROBADO", ["validator_dependency_unavailable:jsonschema"])
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = list(validator.iter_errors(receipt))
        context_validator = Draft202012Validator(
            {"$ref": "#/$defs/context", "$defs": schema["$defs"]})
        errors.extend(context_validator.iter_errors(current_context))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        return result("BLOQUEADO", ["invalid_contract:" + type(exc).__name__])
    if errors:
        return result("BLOQUEADO", ["invalid_input:" + ".".join(map(str, e.path)) + ":" + e.message for e in errors])
    if receipt["context"] != current_context:
        return result("NO_COMPROBADO", ["context_changed:repeat_preflight"])
    now = now or dt.datetime.now(dt.timezone.utc)
    if not isinstance(now, dt.datetime) or now.tzinfo is None:
        return result("BLOQUEADO", ["invalid_clock"])
    timestamps = [receipt["captured_at"]] + [item["captured_at"] for item in receipt["observations"]]
    timestamps += [item[field] for item in receipt["user_interventions"] if item["status"] == "COMPLETED" for field in ("captured_at", "completed_at")]
    if any(_timestamp(stamp) is None for stamp in timestamps):
        return result("BLOQUEADO", ["invalid_timestamp"])
    freshness = receipt["max_age_seconds"]
    if not _fresh(receipt["captured_at"], now, freshness):
        return result("NO_COMPROBADO", ["stale_or_future_preflight"])

    requirements = receipt["requirements"]
    by_id = {item["id"]: item for item in requirements}
    malformed = []
    if len(by_id) != len(requirements):
        malformed.append("duplicate_requirements")
    if {item["area"] for item in requirements} != AREAS:
        malformed.append("incomplete_area_coverage")
    observations = receipt["observations"]
    if any(item["requirement_id"] not in by_id for item in observations):
        malformed.append("observation_without_requirement")
    human = receipt["user_interventions"]
    if len({item["id"] for item in human}) != len(human):
        malformed.append("duplicate_intervention")
    change = receipt["environment_change"]
    if change["required"] and change["destination"] == current_context["host"]:
        malformed.append("handoff_to_same_host")
    target_receipts = receipt["target_preflights"]
    actions = receipt["required_target_actions"]
    action_ids = [item["action_id"] for item in actions]
    if len(set(action_ids)) != len(action_ids):
        malformed.append("duplicate_target_action")
    if any(item.get("action_id") not in action_ids for item in target_receipts):
        malformed.append("unrequested_target_receipt")
    if malformed:
        return result("BLOQUEADO", malformed)

    key = context_key(current_context)
    unknown, failed, denied = [], [], []
    for identifier, requirement in by_id.items():
        matches = [item for item in observations if item["requirement_id"] == identifier]
        if requirement["area"] == "authorization" and any(item["status"] == "FAIL" and item["context_key"] == key and _fresh(item["captured_at"], now, freshness) for item in matches):
            denied.append(identifier + ":authorization_denied")
        if len(matches) != 1:
            unknown.append(identifier + ":missing_or_conflicting_observation")
            continue
        observation = matches[0]
        sources = AUTHORIZATION_SOURCES if requirement["area"] == "authorization" else CAPABILITY_SOURCES
        if observation["source_type"] not in sources:
            unknown.append(identifier + ":source_type_not_admissible_for_area")
            continue
        if observation["context_key"] != key or not _fresh(observation["captured_at"], now, freshness):
            unknown.append(identifier + ":wrong_context_or_stale")
            continue
        if observation["status"] == "FAIL":
            failed.append(identifier + ":" + observation["detail"])
        elif observation["status"] == "NO_COMPROBADO":
            unknown.append(identifier + ":not_verified")
    for item in human:
        if item["status"] == "COMPLETED":
            if item["context_key"] != key or not _fresh(item["captured_at"], now, freshness):
                unknown.append(item["id"] + ":intervention_evidence_stale_or_wrong_context")
            if (_timestamp(item["completed_at"]) - now).total_seconds() > 60:
                unknown.append(item["id"] + ":intervention_not_completed_yet")

    if actions:
        try:
            target_assess = _target_assessor()
            for action in actions:
                identifier = action["action_id"]
                matches = [item for item in target_receipts if item.get("action_id") == identifier]
                if len(matches) != 1:
                    unknown.append(identifier + ":target_preflight_missing_or_duplicate")
                    continue
                target_context = matches[0].get("target")
                if not isinstance(target_context, dict) or target_context.get("id") != action["target_id"] or target_context.get("environment") != action["environment"]:
                    unknown.append(identifier + ":wrong_expected_target_or_environment")
                    continue
                target = target_assess(matches[0], now=now)
                if target["decision"] != "READY_FOR_DEPENDENT_WORK":
                    unknown.append(identifier + ":target_preflight_not_ready")
        except (ImportError, OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            unknown.append("target_validator_unavailable:" + type(exc).__name__)

    pending = [item for item in human if item["status"] == "PENDING"]
    detail = {"context_key": key, "environment_change": change,
              "pending_interventions": pending, "unverified": unknown, "failed": failed}
    if denied:
        return result("BLOQUEADO", denied, **detail)
    if pending:
        preparation = receipt.get("preparation")
        can_prepare = False
        preparation_reasons = []
        if preparation:
            pending_actions = {_action_key(item["action"]) for item in pending}
            if any(_action_key(step) in pending_actions for step in preparation["steps"]):
                preparation_reasons.append("preparation_contains_pending_intervention")
            if any(item["stage"] != "BEFORE_COMPLETION" for item in pending):
                preparation_reasons.append("intervention_required_before_start")
            if unknown or failed or change["required"]:
                preparation_reasons.append("phase_conditions_not_ready_for_preparation")
            if preparation["context_key"] != key:
                preparation_reasons.append("preparation_wrong_context")
            grants = [item for item in observations if by_id[item["requirement_id"]]["area"] == "authorization"
                      and item["status"] == "PASS" and item["source_ref"] == preparation["authorization_ref"]
                      and item["source_type"] == preparation["authorization_source_type"]]
            if not grants:
                preparation_reasons.append("preparation_authorization_not_checked")
            can_prepare = not preparation_reasons
        else:
            preparation_reasons.append("no_explicit_preparation_scope_and_notice")
        return result("REQUIERE_USUARIO", [item["id"] + ":" + item["action"] for item in pending],
                      can_prepare=can_prepare, preparation_steps=preparation["steps"] if can_prepare else [],
                      preparation_reasons=preparation_reasons, **detail)
    if change["required"]:
        return result("CAMBIO_ENTORNO", [change["reason"], "destination_requires_own_preflight"], **detail)
    if failed:
        return result("BLOQUEADO", failed, **detail)
    if unknown:
        return result("NO_COMPROBADO", unknown, **detail)
    return result("GO", [], **detail)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--context", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        receipt = load_json(args.receipt)
        current = load_json(args.context)
        outcome = assess(receipt, current)
    except (OSError, ValueError, TypeError, RecursionError, UnicodeError) as exc:
        outcome = result("BLOQUEADO", ["input_unreadable:" + type(exc).__name__])
    print(json.dumps(outcome, ensure_ascii=False))
    return 0 if outcome["decision"] == "GO" else 2


if __name__ == "__main__":
    sys.exit(main())
