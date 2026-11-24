"""Synthetic acceptance cases for justified pauses and continued verification.

These exercise the public evaluator/CLI, not a live host or database.
"""
import copy
import json
import subprocess
import sys
import unittest

from test_turn_decision import SCRIPT, complete, fixture, observation, policy


def documented_blocker(data, basis="OBSERVATION", current=True):
    data["actions"][0]["blocker"] = {
        "reason": "The selected private configuration cannot be accessed by this operation.",
        "source_ref": "fixture:current-operation-access-check",
        "intervention": "Have the authorized operator configure that connection through the approved private channel.",
        "basis": basis,
        "current": current,
    }
    return data


class ClosureContinuityTests(unittest.TestCase):
    def test_not_run_with_available_action_continues(self):
        data = fixture()
        data["criteria"][0]["status"] = "NOT_RUN"
        before = copy.deepcopy(data)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertFalse(result["closure"]["report_ready"])
        self.assertFalse(result["closure"]["review_required"])
        self.assertEqual(data, before)

    def test_omitted_next_operation_is_not_a_substantiated_blocker(self):
        data = fixture()
        data["actions"] = []
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(result["closure"]["review_required"])
        self.assertEqual(result["closure"]["unmapped_criteria"], ["verify-db"])
        self.assertEqual(result["eligible_actions"], [])

    def test_result_labels_cannot_be_the_cause_of_a_pause(self):
        for label in ("NOT_RUN", "NO COMPROBADO", "No comprobados.", "PENDIENTE", "BLOCKED"):
            data = documented_blocker(fixture())
            data["actions"][0]["blocker"]["reason"] = label
            with self.subTest(label=label):
                result = policy.assess(data)
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertTrue(result["closure"]["review_required"])
                self.assertFalse(result["closure"]["report_ready"])

    def test_known_cause_without_minimum_intervention_needs_review(self):
        data = documented_blocker(fixture())
        data["actions"][0]["blocker"]["intervention"] = "NOT_RUN"
        self.assertTrue(policy.assess(data)["closure"]["review_required"])

    def test_current_observed_blocker_can_be_reported_without_claiming_completion(self):
        result = policy.assess(documented_blocker(fixture()))
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(result["closure"]["report_ready"])
        self.assertFalse(result["closure"]["review_required"])
        self.assertEqual(result["pending_criteria"], ["verify-db"])
        self.assertEqual(result["eligible_actions"], [])

    def test_instruction_boundary_needs_no_prohibited_attempt(self):
        data = documented_blocker(fixture(), basis="INSTRUCTION")
        data["actions"][0]["blocker"].update(
            reason="A host instruction requires human entry before a non-sensitive check.",
            source_ref="fixture:host-instruction/credential-entry",
            intervention="Complete only the protected human-entry step, then resume permitted checks.")
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(result["closure"]["report_ready"])
        self.assertEqual(data["evidence"], [])

    def test_unknown_capability_does_not_authorize_execution_or_explain_itself(self):
        data = fixture()
        data["actions"][0]["capability"]["state"] = "UNKNOWN"
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["eligible_actions"], [])
        self.assertTrue(result["closure"]["review_required"])

    def test_legacy_blocker_remains_readable_but_requires_current_cause_metadata(self):
        data = fixture("blocked-panel")
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertNotEqual(result.get("validation"), "INVALID")
        self.assertTrue(result["closure"]["review_required"])

    def test_stale_blocker_is_reconciled_not_silently_removed(self):
        data = documented_blocker(fixture(), current=False)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(result["closure"]["review_required"])
        self.assertIsNotNone(data["actions"][0]["blocker"])
        self.assertEqual(result["eligible_actions"], [])

    def test_human_done_does_not_prove_connection_and_existing_permission_is_preserved(self):
        data = documented_blocker(fixture(), basis="REQUIRED_INPUT")
        authority = copy.deepcopy(data["actions"][0]["authorization"])
        # A human declaration alone is not the observed connection criterion.
        complete(data, kind="DECLARATION")
        data["actions"][0]["blocker"]["current"] = False
        self.assertEqual(policy.assess(data)["decision"], "BLOCKED")
        # After non-sensitive preconditions are established, run the remaining check.
        data["actions"][0]["blocker"] = None
        self.assertEqual(policy.assess(data)["decision"], "CONTINUE")
        self.assertEqual(data["actions"][0]["authorization"], authority)
        # Only an actual observation of that criterion supports completion.
        data["evidence"] = [observation(data)]
        self.assertEqual(policy.assess(data)["decision"], "CLOSE")

    def test_panel_observation_cannot_satisfy_another_connection_criterion(self):
        data = fixture()
        panel = {**data["baseline_criteria"][0], "id": "panel-created",
                 "description": "Observe the database entry in the selected panel."}
        data["baseline_criteria"].append(panel)
        data["criteria"].append({**panel, "status": "PASS", "evidence_ids": ["panel"], "waiver": None})
        data["evidence"] = [observation(data, eid="panel", origin="panel-event", cid="panel-created")]
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["pending_criteria"], ["verify-db"])
        data["criteria"][0].update(status="PASS", evidence_ids=["panel"])
        self.assertEqual(policy.assess(data)["decision"], "BLOCKED")

    def test_independent_authorized_work_continues_beside_a_private_boundary(self):
        data = documented_blocker(fixture(), basis="INSTRUCTION")
        definition = {**data["baseline_criteria"][0], "id": "inspect-manifest",
                      "description": "Inspect a non-sensitive package manifest."}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**definition, "status": "NOT_RUN", "evidence_ids": [], "waiver": None})
        action = copy.deepcopy(data["actions"][0])
        action.update(id="inspect-manifest", criterion_ids=["inspect-manifest"], blocker=None)
        data["actions"].append(action)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["eligible_actions"], ["inspect-manifest"])

    def test_upstream_cause_explains_dependent_pause_without_inventing_another_blocker(self):
        data = fixture()
        definition = {**data["baseline_criteria"][0], "id": "private-input", "required": False,
                      "description": "Establish the required connection configuration."}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**definition, "status": "BLOCKED", "evidence_ids": [], "waiver": None})
        data["actions"][0]["depends_on"] = ["private-input"]
        precursor = copy.deepcopy(documented_blocker(fixture(), basis="REQUIRED_INPUT")["actions"][0])
        precursor.update(id="configure-private-input", criterion_ids=["private-input"])
        data["actions"].append(precursor)
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertTrue(result["closure"]["report_ready"])
        self.assertEqual(result["closure"]["dependent_action_ids"], ["inspect-application-db"])
        self.assertEqual(result["closure"]["documented_action_ids"], ["configure-private-input"])

    def test_unmapped_dependency_still_requires_review(self):
        data = fixture()
        definition = {**data["baseline_criteria"][0], "id": "missing-prerequisite", "required": False}
        data["baseline_criteria"].append(definition)
        data["criteria"].append({**definition, "status": "NOT_RUN", "evidence_ids": [], "waiver": None})
        data["actions"][0]["depends_on"] = ["missing-prerequisite"]
        result = policy.assess(data)
        self.assertTrue(result["closure"]["review_required"])
        self.assertIn("missing-prerequisite", result["closure"]["unmapped_criteria"])

    def test_stop_never_requests_another_closure_review(self):
        data = fixture()
        data["actions"] = []
        for state in ("STOP", "REVOKED"):
            data["control"]["state"] = state
            result = policy.assess(data)
            self.assertEqual(result["decision"], "STOP")
            self.assertFalse(result["closure"]["review_required"])

    def test_unknown_control_is_a_safety_pause_not_permission_to_research(self):
        data = fixture()
        data["control"]["state"] = "UNKNOWN"
        result = policy.assess(data)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertFalse(result["closure"]["review_required"])
        self.assertEqual(result["eligible_actions"], [])

    def test_completed_limited_assignment_closes_without_extra_work(self):
        result = policy.assess(fixture("close-identification"))
        self.assertEqual(result["decision"], "CLOSE")
        self.assertTrue(result["closure"]["report_ready"])

    def test_wrong_blocker_metadata_types_fail_closed(self):
        for key, value in (("current", "true"), ("current", 1), ("basis", "NOT_RUN"), ("basis", [])):
            data = documented_blocker(fixture())
            data["actions"][0]["blocker"][key] = value
            result = policy.assess(data)
            self.assertEqual(result["decision"], "BLOCKED")
            self.assertEqual(result["validation"], "INVALID")

    def test_cli_reports_unsubstantiated_pause_without_invoking_any_operation(self):
        data = fixture()
        data["actions"] = []
        run = subprocess.run([sys.executable, "-B", str(SCRIPT), "-"], input=json.dumps(data),
                             text=True, capture_output=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stderr, "")
        result = json.loads(run.stdout)
        self.assertTrue(result["closure"]["review_required"])
        self.assertEqual(result["eligible_actions"], [])


if __name__ == "__main__":
    unittest.main()
