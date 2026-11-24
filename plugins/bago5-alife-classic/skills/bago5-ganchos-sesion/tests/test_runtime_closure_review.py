"""Closure integration against a real temporary TaskStore and session storage.

The native adapters consume synthetic events. No installed host, remote memory
service or real mission executes; _runtime_check is never replaced by a mock.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_session_acceptance as fixtures
from test_closure_review import HOSTS, native_payload


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills/bago5-ganchos-sesion/scripts"
SUITE = ROOT / "optional-runtime/bago-operating-suite"
sys.path.insert(0, str(SCRIPTS))
engine = importlib.import_module("session_engine")
native = importlib.import_module("native_hooks")
session_store = importlib.import_module("session_store")


class RuntimeClosureReviewRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = engine._module("bago5_runtime_turn_decision",
                                    ROOT / "skills/bago5/scripts/runtime_turn_decision.py")
        cls.identity = cls.bridge.inspect_suite(SUITE)["identity"]
        sys.path.insert(0, str(SUITE / "scripts"))
        from suite_control import TaskStore
        cls.task_store_type = TaskStore

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bago5-runtime-closure-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.workspace = self.root / "project"
        self.workspace.mkdir()
        (self.workspace / "candidate.txt").write_text("fixed synthetic candidate\n", encoding="utf-8")
        (self.workspace / "acceptance.json").write_text(json.dumps({
            "schema": "bago.suite.check-result.v1", "status": "PASS",
            "findings": [], "coverage": "COMPLETE",
        }), encoding="utf-8")
        binding = fixtures.session_receipt()["binding"]
        plan = {
            "schema": "bago.suite.task.plan.v1", "mission_id": binding["mission_id"],
            "candidate_id": binding["candidate_id"], "operation": "VERIFY",
            "scope": ["candidate.txt"], "max_rounds": 3,
            "checks": [{"id": "native-check", "kind": "artifact", "mandatory": True,
                        "depends_on": [], "artifacts": [{"path": "acceptance.json",
                        "schema": "bago.suite.check-result.v1"}]}],
        }
        self.controller_dir = self.root / "controller"
        self.controller = self.task_store_type(self.controller_dir, self.identity)
        self.controller.initialize(self.workspace, plan)
        self.controller.open_round()
        self.session_sequence = 0

    def controller_snapshot(self):
        return {str(path.relative_to(self.controller_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in self.controller_dir.rglob("*") if path.is_file()}

    def observed_controller(self):
        return self.bridge.observe_runtime(SUITE, self.controller_dir, self.workspace)["controller"]

    def initialize(self, host="CODEX", kind="blocked", stale=False):
        self.host = host
        self.allowed_receipt = fixtures.session_receipt(host)
        receipt = deepcopy(self.allowed_receipt)
        if kind == "blocked":
            receipt["actions"] = []
        elif kind == "complete":
            receipt = fixtures.completed_receipt(receipt)
        elif kind == "handoff":
            for action in receipt["actions"]:
                action.update(target_host="WORK", handoff={
                    "reason": "USER_REQUESTED_HOST", "current": True,
                    "source_ref": "synthetic-runtime-closure:user-requested-work",
                })
        self.session_id = receipt["binding"]["session_id"]
        # This snapshot is selected once at initialization. Later controller
        # changes must fail against it; tests never refresh it to pass a gate.
        self.selected_digest = self.observed_controller()["database_sha256"]
        state = engine.apply_command(None, {
            "op": "INIT", "host": host, "host_session_id": self.session_id,
            "workspace_root": str(self.workspace), "receipt": receipt,
            "source_ref": "synthetic-runtime-closure:selected-session",
            "persistence": {"authorized": True, "source_ref": "synthetic-runtime-closure:local-storage"},
            "runtime_selection": {
                "state_dir": str(self.controller_dir), "workspace_root": str(self.workspace),
                "expected_state_sha256": self.selected_digest,
                "source_ref": "synthetic-runtime-closure:observed-controller",
            },
        })["state"]
        self.session_sequence += 1
        self.data_dir = self.root / ("session-data-" + str(self.session_sequence))
        with session_store.transaction(str(self.data_dir), host, self.session_id, create=True) as tx:
            tx.save(state)
        if stale:
            self.run_event("USER_PROMPT", prompt="A current synthetic clarification.")
            self.assertIs(self.read_state()["receipt_stale"], True)

    def read_state(self):
        with session_store.transaction(str(self.data_dir), self.host, self.session_id, create=False) as tx:
            return deepcopy(tx.state)

    def command(self, op, **fields):
        with session_store.transaction(str(self.data_dir), self.host, self.session_id, create=False) as tx:
            result = engine.apply_command(tx.state, {
                "op": op, "source_ref": "synthetic-runtime-closure:current-instruction", **fields,
            })
            tx.save(result["state"])
            return result["result"]

    def event(self, kind, **fields):
        return {"host": self.host, "host_session_id": self.session_id,
                "cwd": str(self.workspace), "event": kind, **fields}

    def run_event(self, kind, **fields):
        with patch.dict(os.environ, {"PLUGIN_DATA": str(self.data_dir)}):
            self.last_result = engine.run_native(self.event(kind, **fields))
        return self.last_result

    def close(self, active=False):
        name = dict(HOSTS)[self.host]
        raw = native_payload(self.host, name, self.workspace, self.session_id, stop_hook_active=active)

        def observe(event):
            self.last_result = engine.run_native(event)
            return self.last_result

        with patch.dict(os.environ, {"PLUGIN_DATA": str(self.data_dir)}):
            return native.dispatch(raw, self.host, name, observe)

    def close_controller(self):
        self.controller.record_artifact("native-check")
        self.controller.consume("native-check")
        self.assertEqual(self.controller.close()["task_status"], "CLOSED")

    def assert_gate_blocks_review(self, reason, action="BLOCKED"):
        before = self.controller_snapshot()
        output, _ = self.close()
        self.assertEqual(self.last_result["action"], action)
        self.assertIn(reason, self.last_result["reason"])
        self.assertNotIn("review_before_close", self.last_result)
        self.assertNotEqual(output.get("decision"), "block")
        stored = self.read_state()
        self.assertIsNone(stored["last_continue_digest"])
        self.assertEqual(stored["runtime_selection"]["expected_state_sha256"], self.selected_digest)
        self.assertEqual(self.controller_snapshot(), before)
        if action == "STOP":
            self.assertEqual(stored["control"]["state"], "STOP")
            self.assertIs(output["continue"], False)

    def test_fresh_policy_block_with_healthy_controller_reaches_bounded_review(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                self.initialize(host)
                before = self.controller_snapshot()
                output, _ = self.close()
                self.assertEqual(self.last_result["action"], "BLOCKED")
                self.assertIs(self.last_result["review_before_close"], True)
                self.assertIs(self.last_result["data"]["closure"]["review_required"], True)
                self.assertEqual(self.last_result["data"]["eligible_actions"], [])
                self.assertEqual(output["decision"], "block")
                output, _ = self.close()
                self.assertEqual(self.last_result["action"], "BLOCKED")
                self.assertIs(self.last_result["review_before_close"], False)
                self.assertNotEqual(output.get("decision"), "block")
                self.assertEqual(self.controller_snapshot(), before)

    def test_stale_receipt_with_healthy_controller_never_assesses_old_acceptance(self):
        for host, _name in HOSTS:
            for kind in ("blocked", "complete"):
                with self.subTest(host=host, old_receipt=kind):
                    self.initialize(host, kind=kind, stale=True)
                    before = self.controller_snapshot()
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("Obsolete acceptance must not be assessed")) as assess:
                        output, _ = self.close()
                        self.assertEqual(output["decision"], "block")
                        self.assertEqual(self.last_result["action"], "BLOCKED")
                        self.assertIs(self.last_result["review_before_close"], True)
                        self.assertNotIn("data", self.last_result)
                        output, _ = self.close()
                    assess.assert_not_called()
                    self.assertIs(self.last_result["review_before_close"], False)
                    self.assertNotEqual(output.get("decision"), "block")
                    self.assertEqual(self.controller_snapshot(), before)
                    stored = self.read_state()
                    self.assertIs(stored["receipt_stale"], True)
                    self.assertEqual(stored["runtime_selection"]["expected_state_sha256"], self.selected_digest)

    def test_stale_review_then_renewed_receipt_can_continue_with_same_controller_snapshot(self):
        self.initialize(stale=True)
        before = self.controller_snapshot()
        self.close()
        self.command("SET_RECEIPT", receipt=self.allowed_receipt)
        output, _ = self.close()
        self.assertEqual(self.last_result["action"], "CONTINUE")
        self.assertEqual(output["decision"], "block")
        self.assertEqual(self.read_state()["runtime_selection"]["expected_state_sha256"], self.selected_digest)
        self.assertEqual(self.controller_snapshot(), before)

    def test_before_tool_keeps_aggregate_policy_block_without_memory_admission(self):
        self.initialize()
        binding = fixtures.selected_memory_binding(self.read_state()["binding"])
        binding["authorization"]["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        self.command("SELECT_MEMORY", memory_binding=binding)
        with patch.object(engine.memory_guard, "before_tool", side_effect=AssertionError("Policy block precedes memory admission")) as admission:
            result = self.run_event("BEFORE_TOOL", tool_name=binding["tools"]["search_memories"],
                                    arguments={"project_id": binding["project_id"]}, call_id="synthetic-search")
        admission.assert_not_called()
        self.assertEqual(result["action"], "DENY")
        self.assertNotIn("review_before_close", result)
        self.assertEqual(self.read_state()["memory"]["calls"], {})

    def test_changed_native_snapshot_blocks_fresh_and_stale_closure_review(self):
        for stale in (False, True):
            with self.subTest(stale=stale):
                self.initialize(stale=stale)
                self.controller.open_round()
                self.assert_gate_blocks_review("controller_changed_since_receipt")

    def test_changed_candidate_blocks_stale_metadata_review(self):
        self.initialize(stale=True)
        (self.workspace / "candidate.txt").write_text("different candidate bytes\n", encoding="utf-8")
        with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale gate must not assess")) as assess:
            self.assert_gate_blocks_review("candidate_files_differ_from_frozen_scope")
        assess.assert_not_called()

    def test_native_stop_precedes_fresh_closure_review(self):
        self.initialize()
        self.controller.stop("synthetic current STOP")
        self.assert_gate_blocks_review("selected_taskstore_is_stopped", action="STOP")

    def test_native_stop_precedes_stale_review_and_old_policy_assessment(self):
        self.initialize(stale=True)
        self.controller.stop("synthetic current STOP")
        with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale gate must not assess")) as assess:
            self.assert_gate_blocks_review("selected_taskstore_is_stopped", action="STOP")
        assess.assert_not_called()

    def test_closed_native_task_keeps_composite_continue_and_handoff_gates(self):
        self.close_controller()
        self.assertEqual(self.observed_controller()["current_gate_errors"], [])
        for kind, policy_action in (("continue", "CONTINUE"), ("handoff", "HANDOFF")):
            with self.subTest(policy_action=policy_action):
                self.initialize(kind=kind)
                self.assertEqual(engine.policy.assess(self.read_state()["receipt"])["decision"], policy_action)
                self.assert_gate_blocks_review("native_task_closed_no_implicit_continuation")

    def test_open_native_task_keeps_mission_close_gate(self):
        self.initialize(kind="complete")
        self.assertEqual(self.observed_controller()["current_gate_errors"], [])
        self.assertEqual(engine.policy.assess(self.read_state()["receipt"])["decision"], "CLOSE")
        self.assert_gate_blocks_review("native_task_closure_still_pending")
        self.assertEqual(self.controller.status()["task_status"], "OPEN")

    def test_closed_native_task_metadata_review_never_becomes_execution_permission(self):
        self.close_controller()
        self.initialize(kind="continue", stale=True)
        with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale gate must not assess")) as assess:
            output, _ = self.close()
        assess.assert_not_called()
        self.assertEqual(self.last_result["action"], "BLOCKED")
        self.assertEqual(output["decision"], "block")
        self.command("SET_RECEIPT", receipt=self.allowed_receipt)
        output, _ = self.close()
        self.assertEqual(self.last_result["action"], "BLOCKED")
        self.assertIn("native_task_closed_no_implicit_continuation", self.last_result["reason"])
        self.assertNotIn("review_before_close", self.last_result)
        self.assertNotEqual(output.get("decision"), "block")
        self.assertEqual(self.controller.status()["task_status"], "CLOSED")

    def test_work_cli_close_uses_same_runtime_review_for_fresh_and_stale_receipts(self):
        for stale in (False, True):
            with self.subTest(stale=stale):
                self.initialize("WORK", stale=stale)
                before = self.controller_snapshot()
                command = {"op": "EVENT", "source_ref": "synthetic-runtime-closure:work-event",
                           "event": self.event("BEFORE_TURN_CLOSE", stop_hook_active=False)}
                for expected_review in (True, False):
                    process = subprocess.run([
                        sys.executable, "-B", str(SCRIPTS / "session_cli.py"), "--host", self.host,
                        "--session-id", self.session_id, "--data-dir", str(self.data_dir),
                    ], input=json.dumps(command), capture_output=True, text=True, timeout=20)
                    self.assertEqual(process.returncode, 2, process.stderr)
                    result = json.loads(process.stdout)
                    self.assertEqual(result["action"], "BLOCKED")
                    self.assertIs(result["review_before_close"], expected_review)
                self.assertEqual(self.controller_snapshot(), before)

    def test_resume_keeps_existing_aggregate_check_even_with_closure_flag(self):
        self.initialize(stale=True)
        before = self.controller_snapshot()
        result = engine._runtime_check(self.read_state(), resume=True, turn_close=True)
        self.assertIsNotNone(result)
        self.assertEqual(result["decision"], "BLOCKED")
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")
        self.assertEqual(self.controller_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
