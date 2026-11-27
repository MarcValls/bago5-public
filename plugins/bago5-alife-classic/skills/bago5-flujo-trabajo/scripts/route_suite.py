#!/usr/bin/env python3
"""Select permitted BAGO workflow modules and emit a route receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = SKILL_ROOT / "references" / "route-policy.json"


def select(intent: str, includes: list[str], reason: str, request_id: str) -> dict[str, object]:
    if not reason.strip() or not request_id.strip():
        raise ValueError("reason and request-id must be non-empty")
    policy_bytes = POLICY_PATH.read_bytes()
    policy = json.loads(policy_bytes)
    routes = policy["routes"]
    if intent not in routes:
        raise ValueError(f"unknown intent: {intent}")
    route = routes[intent]
    required = list(route["required"])
    optional = set(route["optional"])
    # Keep the historical module IDs in v1 receipts while accepting public skill names.
    names = {Path(target).parent.name: name for name, target in policy["targets"].items()}
    names.update(policy.get("module_aliases", {}))
    includes = [names.get(name.removeprefix("$"), name.removeprefix("$")) for name in includes]
    if len(set(includes)) != len(includes):
        raise ValueError("duplicate --include module")
    rejected = sorted(set(includes) - optional)
    if rejected:
        raise ValueError(f"modules not permitted for {intent}: {', '.join(rejected)}")
    if intent == "question" and includes:
        raise ValueError("question route cannot load specialist modules")
    selected = required + [name for name in includes if name not in required]
    order = policy["module_order"]
    if set(required + list(optional)) - set(order):
        raise ValueError("route policy references a module absent from module_order")
    selected.sort(key=order.index)
    targets = {name: policy["targets"][name] for name in selected}
    for target in targets.values():
        resolved = (SKILL_ROOT.parent.parent / target).resolve()
        resolved.relative_to(SKILL_ROOT.parent.parent.resolve())
        if not resolved.is_file():
            raise ValueError(f"missing packaged target: {target}")
    return {
        "schema": "bago.skills_suite.route_receipt.v1",
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy_version": policy["version"],
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest(),
        "intent": intent,
        "reason": reason,
        "selected_modules": selected,
        "selected_targets": targets,
        "selected_skills": ["$" + Path(target).parent.name for target in targets.values()],
        "excluded_modules": [name for name in order if name not in selected],
        "governance_scope": "suite_internal_advisory",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intent", required=True, choices=("question", "repository", "goal", "phased", "app_game", "repair", "ui"))
    parser.add_argument("--reason", required=True, help="short evidence-based reason for the route")
    parser.add_argument("--request-id", required=True)
    parser.add_argument("--include", action="append", default=[], help="permitted cross-cutting module; repeatable")
    parser.add_argument("--receipt", type=Path, help="optional persistent receipt path")
    args = parser.parse_args()
    try:
        receipt = select(args.intent, args.include, args.reason, args.request_id)
        rendered = json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        if args.receipt:
            destination = args.receipt.expanduser().resolve()
            if destination.exists():
                raise FileExistsError(f"refusing to overwrite route receipt: {destination}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        print(rendered, end="")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
