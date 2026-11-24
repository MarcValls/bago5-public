"""Real temporary TaskStore integration; no services, accounts or installed writes."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


PLUGIN = Path(__file__).resolve().parents[3]
SCRIPTS = PLUGIN / "skills/bago5/scripts"
SUITE = PLUGIN / "optional-runtime/bago-operating-suite"
sys.path.insert(0, str(SCRIPTS))
import runtime_turn_decision as bridge


def receipt(complete=False):
    binding = {"project_id": "project-a", "mission_id": "test-mission", "goal_id": "goal-a",
               "goal_revision": 1, "candidate_id": "candidate-1", "scope_id": "scope-a",
               "session_id": "session-a"}
    definition = {"id": "c1", "description": "Verify the selected candidate", "required": True,
                  "expected_basis": "OBSERVATION", "expected_outcome": "PASS", "min_independent_origins": 1}
    evidence = [{"id": "e1", "criterion_id": "c1", "binding": binding, "kind": "OBSERVATION",
                 "outcome": "PASS", "source_ref": "test:independent-observation", "origin_id": "origin-a",
                 "derived_from": []}] if complete else []
    action = {"id": "observe", "binding": binding, "criterion_ids": ["c1"], "depends_on": [],
              "target_host": "WORK", "capability": {"state": "AVAILABLE", "source_ref": "test:host-tool",
              "current": True, "binding": binding}, "authorization": {"state": "ALLOWED",
              "source_type": "USER_INSTRUCTION", "source_ref": "test:user-request", "current": True,
              "binding": binding}, "preconditions": "SATISFIED", "blocker": None, "handoff": None}
    return {"schema": "bago5.turn-decision.v1", "binding": binding, "current_host": "WORK",
            "goal": {"baseline": "Verify candidate", "current": "Verify candidate", "change_authority": None},
            "control": {"state": "RUNNING", "source_ref": "test:current-host-control", "current": True,
                        "binding": binding}, "baseline_criteria": [definition],
            "criteria": [{**definition, "status": "PASS" if complete else "PENDING",
                          "evidence_ids": ["e1"] if complete else [], "waiver": None}],
            "evidence": evidence, "actions": [] if complete else [action]}


class RuntimeTurnDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Verify pinned bytes before importing the native controller for fixture setup.
        cls.suite_observation = bridge.inspect_suite(SUITE)
        cls.identity = cls.suite_observation["identity"]
        sys.path.insert(0, str(SUITE / "scripts"))
        from suite_control import TaskStore
        cls.store_type = TaskStore

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="bago-turn-runtime-")
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "project"
        self.workspace.mkdir()
        (self.workspace / "candidate.txt").write_text("fixed candidate\n", encoding="utf-8")
        (self.workspace / "acceptance.json").write_text(json.dumps({
            "schema": "bago.suite.check-result.v1", "status": "PASS", "findings": [], "coverage": "COMPLETE"
        }), encoding="utf-8")
        self.state = self.root / "controller"
        plan = {"schema": "bago.suite.task.plan.v1", "mission_id": "test-mission", "candidate_id": "candidate-1",
                "operation": "VERIFY", "scope": ["candidate.txt"], "max_rounds": 3,
                "checks": [{"id": "c1", "kind": "artifact", "mandatory": True, "depends_on": [],
                            "artifacts": [{"path": "acceptance.json", "schema": "bago.suite.check-result.v1"}]}]}
        self.plan = plan
        self.store = self.store_type(self.state, self.identity)
        self.store.initialize(self.workspace, plan)
        self.store.open_round()

    def tearDown(self):
        self.temporary.cleanup()

    def evaluate(self, *args, **kwargs):
        if len(args) >= 3 and args[2] is not None:
            kwargs.setdefault("workspace_root", self.workspace)
        return bridge.evaluate(*args, **kwargs)

    def observed(self):
        return bridge.observe_runtime(SUITE, self.state, self.workspace)

    def digest(self):
        return self.observed()["controller"]["database_sha256"]

    def file_snapshot(self):
        return {str(path.relative_to(self.root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.root.rglob("*") if path.is_file()}

    def close_native(self):
        self.store.record_artifact("c1")
        self.store.consume("c1")
        self.assertEqual(self.store.close()["task_status"], "CLOSED")

    def recovery_fixture(self):
        import behavior_recovery as recovery
        fixture = json.loads((PLUGIN / "skills/bago5/tests/fixtures/behavior-recovery/ccr-001.json").read_text())
        value = receipt()
        value["actions"][0]["preconditions"] = "UNSATISFIED"
        value["actions"][0]["blocker"] = copy.deepcopy(fixture["receipt"]["actions"][0]["blocker"])
        spec = copy.deepcopy(fixture["spec"])
        spec["action_id"] = "observe"
        record = recovery.register(value, spec, now=fixture["registered_at"])
        observation = copy.deepcopy(fixture["observation"])
        observation.update(binding=value["binding"], action_id="observe")
        current = copy.deepcopy(value)
        current["actions"][0]["preconditions"] = "SATISFIED"
        return recovery, fixture, record, current, observation

    def test_recovery_registry_is_applied_before_readonly_native_decision(self):
        recovery, fixture, record, current, observation = self.recovery_fixture()
        before = self.file_snapshot()
        unresolved = copy.deepcopy(current)
        unresolved["actions"][0]["blocker"] = None
        blocked = self.evaluate(unresolved, SUITE, self.state, self.digest(),
                                corrections=[record], now=fixture["now"])
        self.assertEqual(blocked["decision"], "BLOCKED")
        resolved = recovery.reassess(record, current, observation, now=fixture["now"])
        continued = self.evaluate(resolved["receipt"], SUITE, self.state, self.digest(),
                                  corrections=[resolved["record"]], now=fixture["now"])
        self.assertEqual(continued["decision"], "CONTINUE")
        self.assertFalse(continued["permissions_granted"])
        self.assertEqual(continued["execution"], "NOT_RUN")
        self.assertEqual(before, self.file_snapshot())

    def test_recovered_policy_cannot_override_native_stop_or_changed_candidate(self):
        recovery, fixture, record, current, observation = self.recovery_fixture()
        resolved = recovery.reassess(record, current, observation, now=fixture["now"])
        selected = self.digest()
        (self.workspace / "candidate.txt").write_text("changed after recovery\n", encoding="utf-8")
        blocked = self.evaluate(resolved["receipt"], SUITE, self.state, selected,
                                corrections=[resolved["record"]], now=fixture["now"])
        self.assertEqual(blocked["policy_result"]["decision"], "CONTINUE")
        self.assertEqual(blocked["decision"], "BLOCKED")
        self.assertIn("candidate_files_differ_from_frozen_scope", blocked["issues"])
        self.store.stop("synthetic stop after policy recovery")
        stopped = self.evaluate(resolved["receipt"], SUITE, self.state, selected,
                                corrections=[resolved["record"]], now=fixture["now"])
        self.assertEqual(stopped["decision"], "STOP")

    def test_host_stop_does_not_parse_or_read_corrections(self):
        value = receipt()
        value["control"]["state"] = "STOP"
        with patch.object(bridge, "observe_runtime", side_effect=AssertionError("STOP forbids runtime read")):
            result = self.evaluate(value, self.root / "absent", self.state,
                                   corrections=[{"deliberately": "invalid"}])
        self.assertEqual(result["decision"], "STOP")
        source = self.root / "stop-receipt.json"
        source.write_text(json.dumps(value), encoding="utf-8")
        completed = subprocess.run([
            sys.executable, "-B", str(SCRIPTS / "runtime_turn_decision.py"),
            "--suite-root", str(self.root / "absent"), "--receipt", str(source),
            "--corrections", str(self.root / "absent-corrections.json"),
        ], capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(json.loads(completed.stdout)["decision"], "STOP")

    def test_pinned_runtime_identity_is_really_inspected(self):
        self.assertEqual(self.identity["payload_files"], 611)
        # Exact payload for 0.4.40: generic template plus its agents handlers.
        # Identity/provenance metadata and unrelated runtime files are preserved.
        self.assertEqual(self.identity["payload_sha256"], "69aaed6c3efb98e0fa1009ad5c088e467182864049729d03ce52d79b7ed54095")

    def test_continue_existing_open_controller_without_mutating_it(self):
        before = self.file_snapshot()
        result = self.evaluate(receipt(), SUITE, self.state, self.digest())
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["runtime_observation"]["controller"]["candidate_scope"], "MATCH")
        self.assertFalse(result["writes_performed"])
        self.assertFalse(result["permissions_granted"])
        self.assertEqual(before, self.file_snapshot())

    def test_native_stop_overrides_stale_host_receipt_without_resume(self):
        previous = self.digest()
        self.store.stop("synthetic explicit stop")
        before = self.file_snapshot()
        result = self.evaluate(receipt(), SUITE, self.state, previous)
        self.assertEqual(result["decision"], "STOP")
        self.assertEqual(result["runtime_observation"]["controller"]["candidate_scope"], "NOT_RUN_STOP")
        self.assertEqual(self.store.status()["control"], "STOPPED")
        self.assertEqual(before, self.file_snapshot())

    def test_host_stop_short_circuits_all_runtime_reads(self):
        value = receipt()
        value["control"]["state"] = "STOP"
        with patch.object(bridge, "observe_runtime", side_effect=AssertionError("must not read")):
            result = self.evaluate(value, self.root / "absent", self.state)
        self.assertEqual(result["decision"], "STOP")
        self.assertIsNone(result["runtime_observation"])

    def test_expected_state_digest_is_required(self):
        result = self.evaluate(receipt(), SUITE, self.state)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("expected_state_digest_required_use_observe_first", result["issues"])

    def test_changed_controller_snapshot_is_blocked(self):
        previous = self.digest()
        self.store.open_round()
        result = self.evaluate(receipt(), SUITE, self.state, previous)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("controller_changed_since_receipt", result["issues"])

    def test_changed_candidate_is_blocked(self):
        previous = self.digest()
        (self.workspace / "candidate.txt").write_text("different bytes", encoding="utf-8")
        result = self.evaluate(receipt(), SUITE, self.state, previous)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("candidate_files_differ_from_frozen_scope", result["issues"])

    def test_foreign_mission_receipt_is_blocked(self):
        value = receipt()
        # Bind every core record to one different mission so the core is valid.
        value = json.loads(json.dumps(value).replace("test-mission", "another-mission"))
        result = self.evaluate(value, SUITE, self.state, self.digest())
        self.assertEqual(result["policy_result"]["decision"], "CONTINUE")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("receipt_controller_binding_mismatch", result["issues"])

    def test_core_close_cannot_skip_native_closure(self):
        result = self.evaluate(receipt(complete=True), SUITE, self.state, self.digest())
        self.assertEqual(result["policy_result"]["decision"], "CLOSE")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("native_task_closure_still_pending", result["issues"])

    def test_completed_explicit_subtask_can_close_while_native_mission_stays_open(self):
        value = receipt(complete=True)
        original = copy.deepcopy(value)
        before = self.file_snapshot()
        result = self.evaluate(value, SUITE, self.state, self.digest(), closure_scope="SUBTASK",
                               closure_scope_ref="test:user-request-identify-only")
        self.assertEqual(result["decision"], "CLOSE")
        self.assertEqual(result["closure_scope"], "SUBTASK")
        self.assertEqual(result["native_mission_status"], "OPEN")
        self.assertEqual(result["runtime_observation"]["controller"]["closure_verification"], "NOT_RUN")
        self.assertEqual(before, self.file_snapshot())
        self.assertEqual(original, value)

    def test_subtask_label_without_original_scope_reference_is_blocked(self):
        result = self.evaluate(receipt(complete=True), SUITE, self.state, self.digest(), closure_scope="SUBTASK")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("subtask_closure_requires_original_scope_reference", result["issues"])

    def test_invalid_scope_reference_is_blocked_without_echoing_invalid_text(self):
        for reference in [" " * 10_001 + "a", "\ud800", "", " " * 10_001, 123]:
            with self.subTest(reference_type=type(reference).__name__):
                result = self.evaluate(receipt(complete=True), SUITE, closure_scope="SUBTASK",
                                       closure_scope_ref=reference)
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertIsNone(result["closure_scope_ref"])
                json.dumps(result, ensure_ascii=False).encode("utf-8")

    def test_invalid_scope_is_sanitized_before_serialization(self):
        for scope in ["\ud800", " " * 10_001, [], None]:
            with self.subTest(scope_type=type(scope).__name__):
                result = self.evaluate(receipt(complete=True), SUITE, closure_scope=scope)
                self.assertEqual(result["decision"], "BLOCKED")
                self.assertEqual(result["closure_scope"], "INVALID")
                json.dumps(result, ensure_ascii=False).encode("utf-8")

    def test_explicit_mission_close_still_requires_native_closure(self):
        result = self.evaluate(receipt(complete=True), SUITE, self.state, self.digest(), closure_scope="MISSION")
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["native_mission_status"], "OPEN")

    def test_native_closed_cannot_enable_new_continuation(self):
        self.close_native()
        result = self.evaluate(receipt(), SUITE, self.state, self.digest())
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("native_task_closed_no_implicit_continuation", result["issues"])

    def test_native_closed_and_independent_core_evidence_can_close(self):
        self.close_native()
        result = self.evaluate(receipt(complete=True), SUITE, self.state, self.digest())
        self.assertEqual(result["decision"], "CLOSE")
        observed = result["runtime_observation"]["controller"]
        self.assertEqual(observed["closure_verification"], "NOT_RUN")
        self.assertEqual(observed["checks_recorded"][0]["evidence_validation"], "NOT_RUN")
        self.assertEqual(result["policy_result"]["independent_origins"]["c1"], ["origin-a"])

    def test_missing_state_is_not_created(self):
        missing = self.root / "missing-state"
        result = self.evaluate(receipt(), SUITE, missing, "0" * 64)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertFalse(missing.exists())

    def test_taskstore_does_not_authorize_an_implicit_workspace_read(self):
        result = bridge.evaluate(receipt(), SUITE, self.state, "0" * 64)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("explicit_workspace_root_required_for_selected_taskstore", result["issues"])

    def test_mismatched_workspace_is_rejected_before_candidate_read(self):
        selected = self.root / "another-project"
        selected.mkdir()
        with patch.object(bridge, "_read", wraps=bridge._read) as reads:
            result = bridge.evaluate(receipt(), SUITE, self.state, "0" * 64, workspace_root=selected)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("ledger_workspace_differs_from_selected_root", result["issues"])
        self.assertFalse(any(call.args[0] == self.workspace / "candidate.txt" for call in reads.call_args_list))

    def test_malformed_ledger_metadata_types_are_blocked(self):
        with sqlite3.connect(self.state / "control.sqlite3") as db:
            original = dict(db.execute("SELECT key,value FROM meta"))
        for key, value in [("plan", None), ("plan", []), ("plan", "text"),
                           ("candidate", []), ("snapshot", []), ("workspace", None)]:
            with self.subTest(key=key, value=value):
                try:
                    with sqlite3.connect(self.state / "control.sqlite3") as db:
                        db.execute("UPDATE meta SET value=? WHERE key=?", (json.dumps(value), key))
                    result = self.evaluate(receipt(), SUITE, self.state, "0" * 64)
                    self.assertEqual(result["decision"], "BLOCKED")
                    self.assertIn("invalid_taskstore_metadata_types", result["issues"])
                finally:
                    with sqlite3.connect(self.state / "control.sqlite3") as db:
                        db.execute("UPDATE meta SET value=? WHERE key=?", (original[key], key))

    def test_sqlite_sidecars_are_not_checkpointed_or_ignored(self):
        sidecar = self.state / "control.sqlite3-wal"
        sidecar.write_bytes(b"synthetic WAL marker")
        before = self.file_snapshot()
        result = self.evaluate(receipt(), SUITE, self.state, "0" * 64)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("sqlite_sidecar_present_observation_unavailable", result["issues"])
        self.assertEqual(before, self.file_snapshot())

    def test_unselected_runtime_root_is_rejected(self):
        result = self.evaluate(receipt(), self.root)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("suite_root_is_not_this_plugins_pinned_payload", result["issues"])

    def test_missing_sqlite_deserialize_is_blocked_without_traceback(self):
        class OlderConnection:
            def close(self):
                pass
        with patch.object(bridge.sqlite3, "connect", return_value=OlderConnection()):
            result = self.evaluate(receipt(), SUITE, self.state, "0" * 64)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("sqlite_deserialize_unavailable_python_3_11_plus_required", result["issues"])

    def test_unopened_round_does_not_admit_native_effects(self):
        state = self.root / "unopened-controller"
        store = self.store_type(state, self.identity)
        store.initialize(self.workspace, self.plan)
        observed = bridge.observe_runtime(SUITE, state, self.workspace)
        result = self.evaluate(receipt(), SUITE, state, observed["controller"]["database_sha256"])
        native = result["runtime_observation"]["controller"]
        self.assertEqual(result["decision"], "CONTINUE")  # e.g. explicit opening of a round remains possible
        self.assertFalse(native["native_controls_observed"]["round_open"])
        self.assertEqual(native["native_effect_admission"], "NOT_EVALUATED_USE_EXISTING_CONTROLLER")
        with self.assertRaisesRegex(ValueError, "open an explicit bounded round"):
            store.record_artifact("c1")

    def test_last_round_does_not_grant_an_extra_round(self):
        self.store.open_round()
        self.store.open_round()
        result = self.evaluate(receipt(), SUITE, self.state, self.digest())
        native = result["runtime_observation"]["controller"]
        self.assertEqual(result["decision"], "CONTINUE")  # unrun checks in the current round remain possible
        self.assertFalse(native["native_controls_observed"]["another_round_available"])
        with self.assertRaisesRegex(ValueError, "round budget exhausted"):
            self.store.open_round()

    def test_pending_relay_does_not_mint_a_worker_lease(self):
        state = self.root / "relay-controller"
        plan = copy.deepcopy(self.plan)
        plan["checks"].append({"id": "verify", "kind": "execution", "mandatory": True,
                               "depends_on": ["c1"], "artifacts": []})
        store = self.store_type(state, self.identity)
        store.initialize(self.workspace, plan)
        store.relay().enable({"schema": "bago.suite.collaboration.v1",
                              "workers": [{"id": "worker-a", "role": "executor"},
                                          {"id": "worker-b", "role": "verifier"}],
                              "verification_checks": ["verify"], "lease_seconds": 30,
                              "max_claims": 4, "max_handoffs": 4, "max_checkpoints": 4})
        store.open_round()
        store.relay().claim("c1", "worker-a")
        observed = bridge.observe_runtime(SUITE, state, self.workspace)
        before = self.file_snapshot()
        result = self.evaluate(receipt(), SUITE, state, observed["controller"]["database_sha256"])
        native = result["runtime_observation"]["controller"]
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertTrue(native["native_controls_observed"]["relay_enabled"])
        self.assertEqual(native["native_controls_observed"]["relay_pending_checks"], ["c1", "verify"])
        self.assertNotIn("token", json.dumps(result))
        self.assertFalse(result["permissions_granted"])
        self.assertEqual(before, self.file_snapshot())
        with self.assertRaises(ValueError):
            store.record_artifact("c1")

    def test_supervised_child_retains_native_conflict_gate(self):
        state = self.root / "running-controller"
        plan = copy.deepcopy(self.plan)
        plan["checks"][0].update(kind="execution", artifacts=[])
        store = self.store_type(state, self.identity)
        store.initialize(self.workspace, plan)
        store.open_round()
        release = self.root / "release-child"
        command = [sys.executable, "-B", "-c",
                   "import pathlib,sys,time\np=pathlib.Path(sys.argv[1]); end=time.monotonic()+8\n"
                   "while not p.exists() and time.monotonic()<end: time.sleep(.02)\n", str(release)]
        responses = []
        worker = threading.Thread(target=lambda: responses.append(store.run_check("c1", command, timeout=10)))
        worker.start()
        try:
            deadline = time.monotonic() + 4
            while time.monotonic() < deadline:
                if any(run["state"] == "RUNNING" for run in store.status()["runs"]):
                    break
                time.sleep(.01)
            else:
                self.fail("fixture child was not recorded as running")
            observed = bridge.observe_runtime(SUITE, state, self.workspace)
            result = self.evaluate(receipt(), SUITE, state, observed["controller"]["database_sha256"])
            self.assertEqual(result["decision"], "CONTINUE")  # polling is possible, no new execution is granted
            native = result["runtime_observation"]["controller"]
            self.assertEqual(native["native_controls_observed"]["running_children_recorded"], 1)
            self.assertEqual(native["native_effect_admission"], "NOT_EVALUATED_USE_EXISTING_CONTROLLER")
            with self.assertRaisesRegex(ValueError, "while a child runs"):
                store.open_round()
        finally:
            release.write_text("release synthetic child", encoding="utf-8")
            worker.join(timeout=12)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(responses), 1)

    def test_symlink_state_is_rejected(self):
        link = self.root / "state-link"
        link.symlink_to(self.state, target_is_directory=True)
        result = self.evaluate(receipt(), SUITE, link, "0" * 64)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIn("symlink_or_reparse_point", result["issues"])

    def test_invalid_core_receipt_does_not_read_runtime(self):
        with patch.object(bridge, "observe_runtime", side_effect=AssertionError("must not read")):
            result = self.evaluate({}, SUITE, self.state)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertIsNone(result["runtime_observation"])

    def test_cli_observes_existing_runtime_without_writes(self):
        before = self.file_snapshot()
        output = subprocess.run([sys.executable, "-B", str(SCRIPTS / "runtime_turn_decision.py"),
                                 "--suite-root", str(SUITE), "--state-dir", str(self.state), "--workspace-root", str(self.workspace), "--observe"],
                                capture_output=True, text=True, timeout=20, check=True)
        observation = json.loads(output.stdout)
        self.assertEqual(observation["controller"]["mission_id"], "test-mission")
        self.assertFalse(observation["writes_performed"])
        self.assertEqual(before, self.file_snapshot())

    def test_cli_deeply_nested_json_returns_structured_blocked(self):
        malformed = self.root / "deep.json"
        malformed.write_bytes(b"[" * 11_000 + b"0" + b"]" * 11_000)
        output = subprocess.run([sys.executable, "-B", str(SCRIPTS / "runtime_turn_decision.py"),
                                 "--suite-root", str(SUITE), "--receipt", str(malformed)],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(output.returncode, 3)
        self.assertEqual(json.loads(output.stdout)["decision"], "BLOCKED")
        self.assertNotIn("Traceback", output.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
