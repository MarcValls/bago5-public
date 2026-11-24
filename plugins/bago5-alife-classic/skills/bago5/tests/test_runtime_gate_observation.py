"""Native constraints for stale-receipt review, using a real temporary TaskStore."""
import copy
import unittest
from unittest.mock import patch

import test_runtime_turn_decision as fixtures
import turn_decision


class RuntimeGateObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.RuntimeTurnDecisionTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.RuntimeTurnDecisionTests("test_continue_existing_open_controller_without_mutating_it")
        self.fixture.setUp()
        self.receipt = fixtures.receipt()

    def tearDown(self):
        self.fixture.tearDown()

    def gate(self, digest=None):
        return fixtures.bridge.observe_turn_gate(
            self.receipt["binding"], self.receipt["control"], fixtures.SUITE,
            self.fixture.state, digest or self.fixture.digest(), self.fixture.workspace)

    def test_observation_does_not_assess_stale_acceptance_or_write(self):
        expected = self.fixture.digest()
        before = self.fixture.file_snapshot()
        with patch.object(turn_decision, "assess", side_effect=AssertionError("stale policy must not run")):
            result = self.gate(expected)
        self.assertEqual(result["decision"], "CLEAR")
        self.assertTrue(result["gate_only"])
        self.assertFalse(result["permissions_granted"])
        self.assertFalse(result["writes_performed"])
        self.assertEqual(before, self.fixture.file_snapshot())

    def test_declared_stop_or_revocation_never_reads_runtime(self):
        for state in ("STOP", "REVOKED"):
            self.receipt["control"]["state"] = state
            with patch.object(fixtures.bridge, "observe_runtime", side_effect=AssertionError("must not read")):
                result = self.gate("0" * 64)
            self.assertEqual(result["decision"], "STOP")

    def test_unknown_stale_or_foreign_control_never_reads_runtime(self):
        original = copy.deepcopy(self.receipt)
        for change in ("unknown", "stale", "foreign"):
            self.receipt = copy.deepcopy(original)
            if change == "unknown": self.receipt["control"]["state"] = "UNKNOWN"
            elif change == "stale": self.receipt["control"]["current"] = False
            else: self.receipt["control"]["binding"] = {**self.receipt["binding"], "session_id": "another-session"}
            with patch.object(fixtures.bridge, "observe_runtime", side_effect=AssertionError("must not read")):
                result = self.gate("0" * 64)
            self.assertEqual(result["decision"], "BLOCKED")
            self.assertIsNone(result["runtime_observation"])

    def test_observed_stop_precedes_a_changed_digest(self):
        expected = self.fixture.digest()
        self.fixture.store.stop("synthetic stop")
        result = self.gate(expected)
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["runtime_observation"]["controller"]["candidate_scope"], "NOT_RUN_STOP")

    def test_changed_digest_or_candidate_remains_blocked(self):
        expected = self.fixture.digest()
        self.fixture.store.open_round()
        result = self.gate(expected)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("controller_changed_since_receipt", result["issues"])
        expected = self.fixture.digest()
        (self.fixture.workspace / "candidate.txt").write_text("changed candidate\n")
        result = self.gate(expected)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("candidate_files_differ_from_frozen_scope", result["issues"])

    def test_clear_observation_does_not_bypass_fresh_open_or_closed_mission_checks(self):
        expected = self.fixture.digest()
        self.assertEqual(self.gate(expected)["decision"], "CLEAR")
        result = self.fixture.evaluate(fixtures.receipt(complete=True), fixtures.SUITE,
                                       self.fixture.state, expected)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("native_task_closure_still_pending", result["issues"])
        self.fixture.close_native()
        expected = self.fixture.digest()
        self.assertEqual(self.gate(expected)["decision"], "CLEAR")
        result = self.fixture.evaluate(fixtures.receipt(), fixtures.SUITE,
                                       self.fixture.state, expected)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("native_task_closed_no_implicit_continuation", result["issues"])


if __name__ == "__main__":
    unittest.main()
