"""BAGO5-CCR-001: read-only terminal-action replacement eligibility assessment.

This helper cannot grant permission or execute an effect. Original record stays intact.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys

try:
    import turn_decision
except ImportError:
    from . import turn_decision

TERMINAL = {"EXPIRED", "OBSOLETE"}
BOUND = ("project_id", "mission_id", "goal_id", "goal_revision")

def assess(previous: dict, receipt: dict) -> dict:
    result = {"schema": "bago5.objective-continuation.v1", "decision": "BLOCKED", "reasons": [], "prior_action_state": None,
              "old_action_retained": True, "new_action_id": None, "effect_executed": False, "permissions_granted": False}
    if not isinstance(previous, dict) or not isinstance(receipt, dict):
        result["reasons"] = ["Invalid record or receipt"]
        return result
    # STOP must win even against invalid receipt; no external read or side effect.
    control = receipt.get("control")
    if isinstance(control, dict) and control.get("state") in ("STOP", "REVOKED"):
        result.update(decision="STOP", reasons=["STOP or mission revocation"])
        return result
    try:
        assert previous.get("schema") == "bago5.behavior-recovery.record.v1", "Unsupported previous correction"
        assert previous.get("state") in TERMINAL, "Prior correction is not terminal"
        result["prior_action_state"] = previous["state"]
        # A terminal action cannot be used to circumvent an unlifted prohibition
        # or to repeat an effect that has not been reconciled.
        assert previous.get("cause_kind") != "PROHIBITION", "Prior prohibition requires independent authoritative lifting before selecting another route"
        assert previous.get("prior_execution") != "UNCERTAIN", "Uncertain previous execution requires reconciliation before replacement"
        assert not any(e.get("observation", {}).get("prior_result") == "UNCERTAIN" for e in previous.get("events", [])), "Uncertain effect history requires reconciliation"
        oldbinding, newbinding = previous["binding"], receipt["binding"]
        assert all(oldbinding[k] == newbinding[k] for k in BOUND), "Mission/goal binding changed"
        assert previous["goal"] == {k:receipt["goal"][k] for k in ("baseline", "current")}, "Original objective changed"
        assert previous["baseline_criteria"] == receipt["baseline_criteria"], "Acceptance criteria changed"
        assert receipt["control"]["state"] == "RUNNING" and receipt["control"]["current"] is True, "Control not established"
        old_ids = {previous["action_id"], previous["target_action_id"]}
        old_ids.update(e["result_action_id"] for e in previous.get("events", []))
        actions = receipt["actions"]
        assert not any(a["id"] in old_ids for a in actions), "Terminal action still present in current executable actions"
        needed = set(previous["criterion_ids"])
        replacements = [a for a in actions if a["id"] not in old_ids and needed.issubset(set(a["criterion_ids"]))]
        assert len(replacements) == 1, "Exactly one distinct action preserving affected criteria is required"
        action = replacements[0]
        result["new_action_id"] = action["id"]
        # Only the existing evaluator recognizes current permission/eligibility.
        policy_result = turn_decision.assess(receipt)
        result["turn_result"] = policy_result
        eligible = policy_result.get("eligible_actions", [])
        eligible_ids = set(eligible) if all(isinstance(e,str) for e in eligible) else {e.get("id") for e in eligible if isinstance(e,dict)}
        # If admission is to a different host, it is HANDOFF, not local execution.
        if policy_result["decision"] == "CLOSE":
            result.update(decision="CLOSE", reasons=["Objective already satisfied; no replacement needed"])
        elif policy_result["decision"] == "CONTINUE" and action["id"] in eligible_ids:
            result.update(decision="REASSESS", reasons=["New action eligible according to current turn policy; effect gateway still required"])
        elif policy_result["decision"] == "HANDOFF":
            result.update(decision="HANDOFF", reasons=["Current authorized action requires a different host; recipient revalidates"])
        else:
            result["reasons"] = ["Current replacement not yet eligible: " + policy_result["decision"]]
        return result
    except (AssertionError, KeyError, TypeError, ValueError, IndexError) as e:
        result["reasons"] = [str(e) or "Invalid correction record"]
        return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("previous")
    p.add_argument("receipt")
    args=p.parse_args()
    previous=json.loads(Path(args.previous).read_text(encoding="utf-8"))
    receipt=json.loads(Path(args.receipt).read_text(encoding="utf-8"))
    print(json.dumps(assess(previous,receipt),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
