import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPT = SKILL / "scripts" / "turn_decision.py"
FIXTURES = Path(__file__).parent / "fixtures" / "turn-decision"
spec = importlib.util.spec_from_file_location("turn_decision", SCRIPT)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


def fixture(name="continue-work"):
    return json.loads((FIXTURES / (name + ".json")).read_text())


def observation(data, eid="obs-1", origin="origin-1", kind="OBSERVATION", outcome="PASS", cid="verify-db"):
    return {"id": eid, "criterion_id": cid, "binding": copy.deepcopy(data["binding"]),
            "kind": kind, "outcome": outcome, "source_ref": "fixture:" + origin,
            "origin_id": origin, "derived_from": []}


def complete(data, kind="OBSERVATION", outcome="PASS"):
    data["criteria"][0]["status"] = "PASS"
    data["criteria"][0]["evidence_ids"] = ["obs-1"]
    data["evidence"] = [observation(data, kind=kind, outcome=outcome)]
    return data


def derived(data, eid, parents, outcome="PASS", cid="verify-db"):
    return {"id": eid, "criterion_id": cid, "binding": copy.deepcopy(data["binding"]),
            "kind": "DERIVED", "outcome": outcome, "source_ref": "fixture:" + eid,
            "origin_id": None, "derived_from": parents}


class TurnDecisionTests(unittest.TestCase):
    def decision(self, data):
        return policy.assess(data)["decision"]

    def test_work_executes_available_second_step(self):
        result = policy.assess(fixture())
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["eligible_actions"], ["inspect-application-db"])

    def test_observed_panel_block_identifies_intervention(self):
        result = policy.assess(fixture("blocked-panel"))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["blockers"][0]["observed_blocker"]["intervention"],
                         "Complete sign-in to the selected panel session.")

    def test_identification_only_closes_on_declared_acceptance(self):
        self.assertEqual(self.decision(fixture("close-identification")), "CLOSE")

    def test_stop_prevents_second_step(self):
        result = policy.assess(fixture("stop-before-second-step"))
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["eligible_actions"], [])

    def test_all_four_cases_through_real_cli(self):
        cases = {"continue-work": "CONTINUE", "blocked-panel": "BLOCKED",
                 "close-identification": "CLOSE", "stop-before-second-step": "STOP"}
        for name, expected in cases.items():
            with self.subTest(name=name):
                run = subprocess.run([sys.executable, "-B", str(SCRIPT), str(FIXTURES / (name + ".json"))], capture_output=True, text=True)
                result = json.loads(run.stdout)
                self.assertEqual(result["decision"], expected)
                self.assertEqual(run.returncode, 2 if expected in {"BLOCKED", "STOP"} else 0)
                self.assertEqual(run.stderr, "")

    def test_receipt_driven_local_two_step_execution(self):
        # Exercises the policy with actual file effects performed by this test
        # harness. This is not evidence of an LLM host following the skill.
        data = fixture()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / "inspected.txt"
            self.assertEqual(self.decision(data), "CONTINUE")
            out.write_text("synthetic-db", encoding="utf-8")
            self.assertEqual(out.read_text(), "synthetic-db")
            complete(data)
            data["evidence"][0]["source_ref"] = "test-harness:read-inspected-file"
            self.assertEqual(self.decision(data), "CLOSE")
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_complete_task_does_not_invent_more_work(self):
        result = policy.assess(complete(fixture()))
        self.assertEqual(result["decision"], "CLOSE")
        self.assertEqual(result["eligible_actions"], [])

    def test_not_run_cannot_close_even_with_evidence_attached(self):
        data = complete(fixture())
        data["criteria"][0]["status"] = "NOT_RUN"
        self.assertEqual(self.decision(data), "CONTINUE")
        data["actions"] = []
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_pass_without_evidence_requires_verification(self):
        data = fixture()
        data["criteria"][0]["status"] = "PASS"
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertIn("verify-db", result["pending_criteria"])
        self.assertTrue(result["criterion_issues"])

    def test_summary_cannot_drop_one_of_five_migration_hashes(self):
        data = fixture()
        baseline = data["baseline_criteria"][0]
        criterion = data["criteria"][0]
        data["baseline_criteria"] = [{**copy.deepcopy(baseline), "id": "migration-" + str(i)} for i in range(1, 6)]
        data["criteria"] = [{**copy.deepcopy(criterion), "id": "migration-" + str(i)} for i in range(1, 5)]
        data["actions"] = []
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("missing", result["reasons"][0])

    def test_current_criterion_cannot_weaken_its_baseline(self):
        data = fixture()
        data["criteria"][0]["required"] = False
        self.assertEqual(self.decision(data), "BLOCKED")
        data = fixture()
        data["criteria"][0]["expected_basis"] = "DECLARATION"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_declaration_does_not_prove_application_observation(self):
        data = complete(fixture(), kind="DECLARATION")
        data["actions"] = []
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_two_derived_copies_still_have_one_origin(self):
        data = complete(fixture())
        data["baseline_criteria"][0]["min_independent_origins"] = 2
        data["criteria"][0]["min_independent_origins"] = 2
        data["evidence"] += [derived(data, "agent-summary", ["obs-1"]), derived(data, "memory-copy", ["agent-summary"])]
        data["criteria"][0]["evidence_ids"] = ["obs-1", "agent-summary", "memory-copy"]
        data["actions"] = []
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["independent_origins"]["verify-db"], ["origin-1"])

    def test_duplicate_primary_ids_with_same_origin_are_not_independent(self):
        data = complete(fixture())
        data["baseline_criteria"][0]["min_independent_origins"] = 2
        data["criteria"][0]["min_independent_origins"] = 2
        data["evidence"].append(observation(data, eid="obs-copy"))
        data["criteria"][0]["evidence_ids"].append("obs-copy")
        data["actions"] = []
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_origin_aliases_for_one_precise_source_do_not_corroborate(self):
        data = complete(fixture())
        data["baseline_criteria"][0]["min_independent_origins"] = 2
        data["criteria"][0]["min_independent_origins"] = 2
        alias = observation(data, eid="obs-renamed", origin="renamed-origin")
        alias["source_ref"] = data["evidence"][0]["source_ref"]
        data["evidence"].append(alias)
        data["criteria"][0]["evidence_ids"].append("obs-renamed")
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_two_distinct_declared_origins_satisfy_requested_count(self):
        data = complete(fixture())
        data["baseline_criteria"][0]["min_independent_origins"] = 2
        data["criteria"][0]["min_independent_origins"] = 2
        data["evidence"].append(observation(data, eid="obs-2", origin="origin-2"))
        data["criteria"][0]["evidence_ids"].append("obs-2")
        self.assertEqual(self.decision(data), "CLOSE")

    def test_one_event_can_support_two_different_criteria(self):
        data = complete(fixture())
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "verify-isolation"}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PASS", "evidence_ids": ["same-event-second-claim"], "waiver": None})
        data["evidence"].append(observation(data, eid="same-event-second-claim", cid="verify-isolation"))
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CLOSE")
        self.assertEqual(result["independent_origins"], {"verify-db": ["origin-1"], "verify-isolation": ["origin-1"]})

    def test_derivation_cannot_upgrade_declaration_to_observation(self):
        data = complete(fixture(), kind="DECLARATION")
        data["evidence"].append(derived(data, "repeated-conclusion", ["obs-1"]))
        data["criteria"][0]["evidence_ids"] = ["repeated-conclusion"]
        data["actions"] = []
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_lineage_cycles_and_missing_parent_fail_closed(self):
        for parents in (["loop"], ["not-recovered"]):
            data = complete(fixture())
            data["evidence"].append(derived(data, "loop", parents))
            self.assertEqual(self.decision(data), "BLOCKED")

    def test_lineage_depth_limit_does_not_depend_on_record_order(self):
        for links, expected in ((127, "CLOSE"), (130, "BLOCKED")):
            data = complete(fixture())
            parent = "obs-1"
            for number in range(links):
                eid = "derived-" + str(number)
                data["evidence"].append(derived(data, eid, [parent]))
                parent = eid
            data["criteria"][0]["evidence_ids"] = [parent]
            forward = self.decision(data)
            data["evidence"].reverse()
            backward = self.decision(data)
            with self.subTest(links=links):
                self.assertEqual((forward, backward), (expected, expected))

    def test_derivation_cannot_change_outcome(self):
        data = complete(fixture(), outcome="FAIL")
        data["evidence"].append(derived(data, "laundered-pass", ["obs-1"]))
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_conflicting_current_evidence_blocks_even_if_one_is_ignored(self):
        data = complete(fixture())
        data["evidence"].append(observation(data, "negative", "origin-negative", outcome="FAIL"))
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_conflict_blocks_its_branch_but_not_independent_work(self):
        data = complete(fixture())
        data["evidence"].append(observation(data, "negative", "origin-negative", outcome="FAIL"))
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "independent-review"}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PENDING", "evidence_ids": [], "waiver": None})
        independent_action = copy.deepcopy(data["actions"][0])
        independent_action.update(id="perform-independent-review", criterion_ids=["independent-review"])
        data["actions"].append(independent_action)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["conflicted_criteria"], ["verify-db"])
        self.assertEqual(result["eligible_actions"], ["perform-independent-review"])
        self.assertIn("verify-db", result["pending_criteria"])

    def test_conflict_still_blocks_a_dependent_branch(self):
        data = complete(fixture())
        data["evidence"].append(observation(data, "negative", "origin-negative", outcome="FAIL"))
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "dependent-review"}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PENDING", "evidence_ids": [], "waiver": None})
        dependent = copy.deepcopy(data["actions"][0])
        dependent.update(id="perform-dependent-review", criterion_ids=["dependent-review"], depends_on=["verify-db"])
        data["actions"].append(dependent)
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_every_binding_dimension_is_checked(self):
        for key in policy.BINDING_KEYS:
            data = complete(fixture())
            data["evidence"][0]["binding"][key] = 2 if key == "goal_revision" else "another-context"
            with self.subTest(key=key):
                self.assertEqual(self.decision(data), "BLOCKED")

    def test_permission_cannot_be_replayed_from_other_session(self):
        data = fixture()
        data["actions"][0]["authorization"]["binding"]["session_id"] = "earlier-session"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_goal_change_requires_explicit_current_authority(self):
        data = fixture()
        data["goal"]["current"] = "Deploy to production."
        self.assertEqual(self.decision(data), "BLOCKED")
        data["goal"]["change_authority"] = copy.deepcopy(data["actions"][0]["authorization"])
        data["goal"]["change_authority"]["source_type"] = "HOST_PERMISSION"
        self.assertEqual(self.decision(data), "BLOCKED")
        data["goal"]["change_authority"]["source_type"] = "EXPLICIT_APPROVAL"
        self.assertEqual(self.decision(data), "CONTINUE")
        data["goal"]["change_authority"]["current"] = False
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_memory_is_not_an_authority_source(self):
        data = fixture()
        data["actions"][0]["authorization"]["source_type"] = "MEMORY"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_unknown_and_stale_controls_do_not_mean_running(self):
        for state, current in (("UNKNOWN", True), ("RUNNING", False)):
            data = complete(fixture())
            data["control"].update(state=state, current=current)
            self.assertEqual(self.decision(data), "BLOCKED")

    def test_stop_precedes_completion_and_malformed_rest_of_receipt(self):
        data = complete(fixture())
        data["control"]["state"] = "STOP"
        self.assertEqual(self.decision(data), "STOP")
        self.assertEqual(self.decision({"control": {"state": "STOP"}}), "STOP")
        self.assertEqual(self.decision({"control": {"state": "REVOKED"}}), "STOP")

    def test_partial_block_keeps_independent_local_work_running(self):
        data = fixture("blocked-panel")
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "review-package"}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PENDING", "evidence_ids": [], "waiver": None})
        action = copy.deepcopy(fixture()["actions"][0])
        action.update(id="review-independent-package", criterion_ids=["review-package"])
        data["actions"].append(action)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["eligible_actions"], ["review-independent-package"])
        self.assertEqual(len(result["blockers"]), 1)

    def test_optional_prerequisite_of_mandatory_work_is_executable(self):
        data = fixture()
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "prepare-inspection", "required": False}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PENDING", "evidence_ids": [], "waiver": None})
        main = data["actions"][0]
        main["depends_on"] = ["prepare-inspection"]
        preparation = copy.deepcopy(main)
        preparation.update(id="prepare-read-only-inspection", criterion_ids=["prepare-inspection"], depends_on=[])
        data["actions"].append(preparation)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["eligible_actions"], ["prepare-read-only-inspection"])
        self.assertEqual(result["supporting_criteria"], ["prepare-inspection"])

    def test_unrelated_optional_work_does_not_expand_scope(self):
        data = fixture("blocked-panel")
        definition = {**copy.deepcopy(data["baseline_criteria"][0]), "id": "unrequested-extra", "required": False}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**copy.deepcopy(definition), "status": "PENDING", "evidence_ids": [], "waiver": None})
        extra = copy.deepcopy(fixture()["actions"][0])
        extra.update(id="perform-unrequested-extra", criterion_ids=["unrequested-extra"])
        data["actions"].append(extra)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["eligible_actions"], [])
        self.assertEqual(result["supporting_criteria"], [])

    def test_real_other_host_handoff_retains_receiver_revalidation(self):
        data = fixture()
        action = data["actions"][0]
        action["target_host"] = "CODEX"
        action["handoff"] = {"reason": "CAPABILITY_UNAVAILABLE_HERE", "source_ref": "fixture:host-capability-check", "current": True}
        result = policy.assess(data)
        self.assertEqual(result["decision"], "HANDOFF")
        self.assertEqual(result["handoffs"][0]["target_host"], "CODEX")
        self.assertTrue(result["handoffs"][0]["recipient_must_revalidate"])

    def test_same_host_handoff_cannot_end_executable_work(self):
        data = fixture()
        data["actions"][0]["handoff"] = {"reason": "USER_REQUESTED_HOST", "source_ref": "fixture:format-preference", "current": True}
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_local_executable_work_precedes_unnecessary_handoff(self):
        data = fixture()
        remote = copy.deepcopy(data["actions"][0])
        remote.update(id="remote-copy", target_host="CODEX", handoff={"reason": "CAPABILITY_UNAVAILABLE_HERE", "source_ref": "fixture:remote-capability", "current": True})
        data["actions"].append(remote)
        self.assertEqual(self.decision(data), "CONTINUE")

    def test_unknown_capability_and_revoked_action_do_not_execute(self):
        data = fixture()
        data["actions"][0]["capability"]["state"] = "UNKNOWN"
        self.assertEqual(self.decision(data), "BLOCKED")
        data = fixture()
        data["actions"][0]["authorization"]["state"] = "REVOKED"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_expected_negative_result_can_satisfy_audit_criterion(self):
        data = complete(fixture(), outcome="FAIL")
        data["baseline_criteria"][0]["expected_outcome"] = "FAIL"
        data["criteria"][0]["expected_outcome"] = "FAIL"
        self.assertEqual(self.decision(data), "CLOSE")

    def test_observed_product_failure_can_be_repaired_within_scope(self):
        data = complete(fixture(), outcome="FAIL")
        data["criteria"][0]["status"] = "FAIL"
        self.assertEqual(self.decision(data), "CONTINUE")

    def test_waiver_preserves_id_and_requires_scope_decision(self):
        data = fixture()
        criterion = data["criteria"][0]
        criterion["status"] = "WAIVED"
        criterion["waiver"] = {"reason": "User explicitly removed this acceptance requirement.",
                               "authority": copy.deepcopy(data["actions"][0]["authorization"])}
        self.assertEqual(self.decision(data), "CLOSE")
        criterion["waiver"]["authority"]["state"] = "UNKNOWN"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_explicit_prompt_deliverable_closes_as_an_artifact(self):
        data = complete(fixture(), kind="ARTIFACT")
        for c in (data["baseline_criteria"][0], data["criteria"][0]):
            c["description"] = "Prepare the exact reusable prompt requested by the user."
            c["expected_basis"] = "ARTIFACT"
        data["goal"]["baseline"] = data["goal"]["current"] = "Prepare an exact prompt only."
        data["actions"] = []
        self.assertEqual(self.decision(data), "CLOSE")

    def test_wrong_types_and_missing_fields_fail_closed(self):
        for path, value in ((["control", "current"], "true"), (["binding", "goal_revision"], True),
                            (["baseline_criteria", 0, "required"], "false"), (["current_host"], ["WORK"]),
                            (["control", "state"], []), (["actions", 0, "criterion_ids"], "verify-db")):
            data = fixture()
            target = data
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            self.assertEqual(self.decision(data), "BLOCKED")
        for value in (None, True, 1, [], "", {}, {"control": None}):
            self.assertEqual(self.decision(value), "BLOCKED")

    def test_text_limit_counts_whitespace_bytes_as_text_characters(self):
        data = fixture()
        data["goal"]["baseline"] = data["goal"]["current"] = " " * 10001 + "a"
        self.assertEqual(self.decision(data), "BLOCKED")

    def test_cli_duplicate_keys_and_nonfinite_json_fail_closed(self):
        for raw in ('{"control":{"state":"RUNNING"},"control":{"state":"STOP"}}', '{"value":NaN}', '{"value":Infinity}'):
            run = subprocess.run([sys.executable, "-B", str(SCRIPT), "-"], input=raw, capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout)["decision"], "BLOCKED")
            self.assertEqual(run.stderr, "")

    def test_cli_deep_json_returns_blocked_instead_of_traceback(self):
        raw = "[" * 11000 + "0" + "]" * 11000
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), "-"], input=raw, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(json.loads(run.stdout)["decision"], "BLOCKED")
        self.assertEqual(run.stderr, "")

    def test_non_utf8_and_surrogate_text_fail_closed(self):
        with self.assertRaises(UnicodeError):
            policy.parse_receipt(b'\xff')
        data = fixture()
        data["goal"]["current"] = "\ud800"
        self.assertEqual(self.decision(data), "BLOCKED")


if __name__ == "__main__":
    unittest.main()
