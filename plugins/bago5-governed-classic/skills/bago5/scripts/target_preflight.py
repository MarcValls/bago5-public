#!/usr/bin/env python3
"""Classify declared preflight evidence; does not probe or enforce tool calls."""
import datetime as dt
import json
import sys

ALLOWED_SOURCES = {"target_probe", "authenticated_panel", "authenticated_connector", "user_observed_target"}
MAX_AGE_SECONDS = 3600

def assess(data, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    problems = []
    if not isinstance(data, dict):
        return {"decision": "BLOCKED", "reasons": ["invalid_document"]}
    action = data.get("action_id")
    target = data.get("target")
    required = data.get("required_facts")
    observations = data.get("observations")
    if not isinstance(action, str) or not action.strip():
        problems.append("missing_action_id")
    if not isinstance(target, dict) or any(not isinstance(target.get(k), str) or not target[k].strip() for k in ("id", "environment")):
        problems.append("missing_target")
        target = {}
    if not isinstance(required, list) or not required or any(not isinstance(x, str) or not x.strip() for x in required) or len(set(required)) != len(required):
        problems.append("invalid_required_facts")
        required = []
    if not isinstance(observations, list):
        problems.append("invalid_observations")
        observations = []
    try:
        max_age = data.get("max_age_seconds", 900)
        if not isinstance(max_age, int) or isinstance(max_age, bool) or not 1 <= max_age <= MAX_AGE_SECONDS:
            raise ValueError()
    except ValueError:
        problems.append("invalid_max_age")
        max_age = 0
    for name in required:
        matches = [x for x in observations if isinstance(x, dict) and x.get("fact") == name]
        if len(matches) != 1:
            problems.append(name + ":missing_or_duplicate")
            continue
        x = matches[0]
        if x.get("action_id") != action:
            problems.append(name + ":wrong_action")
        if x.get("target_id") != target.get("id") or x.get("environment") != target.get("environment"):
            problems.append(name + ":wrong_target_or_environment")
        if x.get("source_type") not in ALLOWED_SOURCES:
            problems.append(name + ":source_not_target_observation")
        if not isinstance(x.get("source_ref"), str) or not x["source_ref"].strip():
            problems.append(name + ":missing_source")
        if x.get("observed") is None or (isinstance(x.get("observed"), str) and not x["observed"].strip()):
            problems.append(name + ":missing_observed")
        if "expected" in x and x.get("expected") != x.get("observed"):
            problems.append(name + ":expected_observed_conflict")
        if x.get("conflict") is True:
            problems.append(name + ":unresolved_conflict")
        try:
            raw = x.get("captured_at")
            if not isinstance(raw, str):
                raise ValueError()
            stamp = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError()
            age = (now - stamp.astimezone(dt.timezone.utc)).total_seconds()
            if age < -60 or age > max_age:
                problems.append(name + ":stale_or_future")
        except (ValueError, TypeError):
            problems.append(name + ":invalid_timestamp")
    return {"decision": "BLOCKED" if problems else "READY_FOR_DEPENDENT_WORK",
            "reasons": problems, "limit": "metadata only; no target probe or tool enforcement"}

def main():
    if len(sys.argv) != 2:
        print("usage: target_preflight.py receipt.json", file=sys.stderr)
        return 1
    try:
        with open(sys.argv[1], encoding="utf-8") as handle:
            data = json.load(handle)
        result = assess(data)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"decision": "BLOCKED", "reasons": [type(error).__name__]}))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["decision"] == "READY_FOR_DEPENDENT_WORK" else 2

if __name__ == "__main__":
    sys.exit(main())
