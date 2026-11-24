"""CCR-001 through actual session transitions, persisted CLI and host adapters.

All observations and permissions are synthetic fixtures. Local state files and
a temporary native TaskStore are real; no host is installed and no remote
service or mission effect is invoked.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_session_acceptance as acceptance


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/bago5-ganchos-sesion/scripts"))
sys.path.insert(0, str(ROOT / "skills/bago5/scripts"))
engine = importlib.import_module("session_engine")
native = importlib.import_module("native_hooks")
bridge = importlib.import_module("runtime_turn_decision")
FIXTURE = ROOT / "skills/bago5/tests/fixtures/behavior-recovery/ccr-001.json"
CLI = ROOT / "skills/bago5-ganchos-sesion/scripts/session_cli.py"
SUITE = ROOT / "optional-runtime/bago-operating-suite"


class RecoverySessionIntegration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bago5-ccr-session-")
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / "project"
        self.workspace.mkdir()
        self.data = self.workspace.parent / "session-data"
        self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.now = self.fixture["registered_at"]

    def initialize(self, host="WORK", runtime_selection=None):
        receipt = deepcopy(self.fixture["receipt"])
        receipt["current_host"] = host
        receipt["actions"][0]["target_host"] = host
        self.initial = {
            "op": "INIT", "host": host,
            "host_session_id": receipt["binding"]["session_id"],
            "workspace_root": str(self.workspace), "receipt": receipt,
            "source_ref": "synthetic-ccr:current-request",
            "persistence": {"authorized": True, "source_ref": "synthetic-ccr:local-state"},
        }
        if runtime_selection is not None:
            self.initial["runtime_selection"] = runtime_selection
        self.state = engine.apply_command(None, self.initial, now=self.now)["state"]

    def command(self, op, **fields):
        command = {"op": op, "source_ref": "synthetic-ccr:current-request", **fields}
        result = engine.apply_command(self.state, command, now=self.now)
        self.state = result["state"]
        return result["result"]

    def register(self):
        return self.command("REGISTER_CORRECTION", correction=self.fixture["spec"])

    def current_receipt(self):
        receipt = deepcopy(self.state["receipt"])
        receipt["actions"][0]["preconditions"] = "SATISFIED"
        return receipt

    def recover(self, observation=None):
        self.now = self.fixture["now"]
        return self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                            receipt=self.current_receipt(),
                            observation=observation or self.fixture["observation"])

    def event(self, kind, **fields):
        result = engine.handle_event(self.state, {
            "event": kind, "host": self.state["host"],
            "host_session_id": self.state["host_session_id"],
            "cwd": str(self.workspace), **fields,
        }, now=self.now)
        self.state = result["state"]
        return result["result"]

    def test_receipt_refresh_cannot_bypass_registered_cause(self):
        self.initialize()
        self.register()
        receipt = self.current_receipt()
        receipt["actions"][0]["blocker"] = None
        self.command("SET_RECEIPT", receipt=receipt)
        blocked = self.event("BEFORE_TURN_CLOSE")
        self.assertEqual(blocked["action"], "BLOCKED")
        self.assertEqual(blocked["data"]["eligible_actions"], [])
        self.assertEqual(self.state["corrections"]["CCR-001"]["state"], "WAITING_CONDITIONS")
        self.assertEqual(self.state["anchor"], {
            "goal": self.initial["receipt"]["goal"],
            "baseline_criteria": self.initial["receipt"]["baseline_criteria"],
        })

    def test_recovery_keeps_valid_authority_then_verifies_completion(self):
        self.initialize()
        self.register()
        authority = deepcopy(self.state["receipt"]["actions"][0]["authorization"])
        result = self.recover()
        self.assertEqual(result["action"], "CONTINUE")
        self.assertEqual(result["execution"], "NOT_RUN")
        self.assertEqual(self.state["receipt"]["actions"][0]["authorization"], authority)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "CONTINUE")
        complete = acceptance.completed_receipt(self.state["receipt"])
        complete["actions"] = []
        self.command("SET_RECEIPT", receipt=complete)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "CLOSE")
        self.assertEqual(self.state["receipt"]["baseline_criteria"],
                         self.initial["receipt"]["baseline_criteria"])

    def test_conditions_change_requires_a_new_observation(self):
        self.initialize()
        self.register()
        self.recover()
        self.now = "2026-11-20T12:00:03+00:00"
        self.event("CONDITIONS_CHANGED", correction_ids=["CCR-001"],
                   source_ref="synthetic-ccr:connection-changed")
        old = deepcopy(self.fixture["observation"])
        old["id"] = "old-data-with-new-label"
        result = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                              receipt=self.current_receipt(), observation=old)
        self.assertEqual(result["action"], "BLOCKED")
        fresh = deepcopy(old)
        fresh.update(id="fresh-after-change", observed_at="2026-11-20T12:00:04+00:00")
        self.now = "2026-11-20T12:00:05+00:00"
        result = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                              receipt=self.current_receipt(), observation=fresh)
        self.assertEqual(result["action"], "CONTINUE")

    def test_resolution_expiry_restores_blocking_without_repeating_effects(self):
        self.initialize()
        self.register()
        self.recover()
        self.now = "2026-11-20T12:06:00+00:00"
        result = self.event("BEFORE_TURN_CLOSE")
        self.assertEqual(result["action"], "BLOCKED")
        self.assertEqual(result["data"]["eligible_actions"], [])

    def test_receipt_rollback_cannot_restore_a_revoked_permission_or_old_resolution(self):
        self.initialize()
        self.register()
        self.recover()
        original = deepcopy(self.state["receipt"])
        revoked = deepcopy(original)
        revoked["actions"][0]["authorization"].update(
            state="REVOKED", source_ref="synthetic-ccr:later-revocation")
        self.now = "2026-11-20T12:00:03+00:00"
        self.command("SET_RECEIPT", receipt=revoked)
        self.now = "2026-11-20T12:00:04+00:00"
        self.command("SET_RECEIPT", receipt=original)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "BLOCKED")
        observation = deepcopy(self.fixture["observation"])
        observation.update(id="after-rollback", observed_at="2026-11-20T12:00:05+00:00")
        self.now = "2026-11-20T12:00:06+00:00"
        rejected = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                                receipt=original, observation=observation)
        self.assertEqual(rejected["action"], "BLOCKED")
        current = deepcopy(original)
        current["actions"][0]["authorization"]["source_ref"] = "synthetic-ccr:explicit-new-authorization"
        observation.update(id="new-authorization", observed_at="2026-11-20T12:00:07+00:00")
        self.now = "2026-11-20T12:00:08+00:00"
        allowed = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                               receipt=current, observation=observation)
        self.assertEqual(allowed["action"], "CONTINUE")

    def test_candidate_switch_revalidates_same_goal_corrections_and_preserves_recovery(self):
        for cause in ("CONDITION", "PROHIBITION"):
            with self.subTest(cause=cause):
                self.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
                self.fixture["spec"]["cause_kind"] = cause
                if cause == "PROHIBITION":
                    self.fixture["spec"]["restriction_source_type"] = "USER_INSTRUCTION"
                self.now = self.fixture["registered_at"]
                self.initialize()
                self.register()
                authority = deepcopy(self.state["receipt"]["actions"][0]["authorization"])
                switch = json.loads(json.dumps(self.initial).replace("synthetic-candidate-01", "synthetic-candidate-02"))
                switch["receipt"]["actions"][0].update(preconditions="SATISFIED", blocker=None)
                switch.update(op="PROJECT_SWITCH", authority=authority)
                self.now = "2026-11-20T12:00:03+00:00"
                self.state = engine.apply_command(self.state, switch, now=self.now)["state"]
                self.assertEqual(self.state["corrections"]["CCR-001"]["binding"], self.state["binding"])
                self.assertIsNone(self.state["corrections"]["CCR-001"]["resolution"])
                self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "BLOCKED")
                observation = deepcopy(self.fixture["observation"])
                observation.update(binding=deepcopy(self.state["binding"]), id="new-candidate-observation",
                                   observed_at="2026-11-20T12:00:04+00:00")
                self.now = "2026-11-20T12:00:05+00:00"
                result = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                                      receipt=self.current_receipt(), observation=observation)
                self.assertEqual(result["action"], "CONTINUE" if cause == "CONDITION" else "BLOCKED")

    def test_stop_prevents_recovery_and_resume_does_not_restore_it(self):
        self.initialize()
        self.register()
        self.recover()
        running = deepcopy(self.state["control"])
        authority = deepcopy(self.state["receipt"]["actions"][0]["authorization"])
        self.command("STOP")
        before = deepcopy(self.state)
        with self.assertRaisesRegex(engine.HookError, "CONTROL_NOT_RUNNING"):
            self.recover()
        self.assertEqual(self.state, before)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "STOP")
        self.now = "2026-11-20T12:00:03+00:00"
        self.command("RESUME", control=running, authority=authority)
        self.assertEqual(self.state["corrections"]["CCR-001"]["state"], "WAITING_CONDITIONS")
        self.assertTrue(self.state["receipt_stale"])
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "BLOCKED")

    def test_repeated_registration_and_observation_do_not_rearm_host_loop(self):
        self.initialize("CODEX")
        self.register()
        registered = deepcopy(self.state["corrections"])
        self.now = self.fixture["now"]
        self.register()
        self.assertEqual(self.state["corrections"], registered)
        self.recover()
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "CONTINUE")
        before = deepcopy(self.state)
        result = self.recover()
        self.assertFalse(result["changed"])
        self.assertEqual(self.state, before)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["reason"],
                         "UNCHANGED_CONTINUATION_REPORT_BLOCKER_NO_LOOP")

    def test_duplicate_observation_with_historical_blocker_preserves_other_resolutions(self):
        self.initialize()
        self.register()
        second = deepcopy(self.fixture["spec"])
        second["id"] = "CCR-002"
        self.command("REGISTER_CORRECTION", correction=second)
        original_input = self.current_receipt()
        self.recover()
        observation = deepcopy(self.fixture["observation"])
        observation.update(id="second-cause-resolved", correction_id="CCR-002",
                           observed_at="2026-11-20T12:00:03+00:00")
        self.now = "2026-11-20T12:00:04+00:00"
        result = self.command("REASSESS_CORRECTION", correction_id="CCR-002",
                              receipt=self.current_receipt(), observation=observation)
        self.assertEqual(result["action"], "CONTINUE")
        before = deepcopy(self.state)
        duplicate = self.command("REASSESS_CORRECTION", correction_id="CCR-001",
                                 receipt=original_input, observation=self.fixture["observation"])
        self.assertFalse(duplicate["changed"])
        self.assertEqual(duplicate["action"], "CONTINUE")
        self.assertEqual(self.state, before)

    def test_codex_and_copilot_adapters_request_continuation_after_recovery(self):
        for host, event_name in (("CODEX", "Stop"), ("COPILOT", "agentStop")):
            with self.subTest(host=host):
                self.now = self.fixture["registered_at"]
                self.initialize(host)
                self.register()
                self.recover()
                payload = {"cwd": str(self.workspace), "hook_event_name": event_name,
                           "session_id" if host == "CODEX" else "sessionId": self.state["host_session_id"]}
                decisions = []
                def callback(event):
                    result = engine.handle_event(self.state, event, now=self.now)
                    self.state = result["state"]
                    decisions.append(result["result"]["action"])
                    return result["result"]
                output, _ = native.dispatch(json.dumps(payload).encode(), host, event_name, callback)
                self.assertEqual(decisions, ["CONTINUE"])
                self.assertEqual(output["decision"], "block")
                output, _ = native.dispatch(json.dumps(payload).encode(), host, event_name, callback)
                self.assertEqual(decisions[-1], "BLOCKED")
                self.assertNotEqual(output.get("decision"), "block")

    def test_project_change_keeps_history_without_importing_old_restrictions(self):
        self.initialize()
        self.register()
        authority = deepcopy(self.state["receipt"]["actions"][0]["authorization"])
        switch = json.loads(json.dumps(self.initial).replace("synthetic-alife", "synthetic-other-project"))
        switch["receipt"]["actions"][0].update(preconditions="SATISFIED", blocker=None)
        switch.update(op="PROJECT_SWITCH", authority=authority)
        result = engine.apply_command(self.state, switch, now=self.now)
        self.state = result["state"]
        self.assertFalse(self.state.get("corrections"))
        history = self.state["correction_history"][0]
        self.assertEqual(history["authority"], "DATA_ONLY")
        self.assertEqual(history["records"]["CCR-001"]["binding"]["project_id"], "synthetic-alife")
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "CONTINUE")

    def test_expired_order_stays_retired_while_a_new_explicit_request_can_proceed(self):
        self.fixture["spec"]["expires_at"] = "2026-11-20T11:59:00+00:00"
        self.initialize()
        self.register()
        receipt = self.current_receipt()
        receipt["actions"][0]["blocker"] = None
        self.command("SET_RECEIPT", receipt=receipt)
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "BLOCKED")
        authority = deepcopy(receipt["actions"][0]["authorization"])
        authority["source_ref"] = "synthetic-ccr:explicit-new-request"
        switch = deepcopy(self.initial)
        switch["receipt"] = json.loads(json.dumps(receipt).replace('"verify-staging"', '"verify-staging-new-request"'))
        switch["receipt"]["actions"][0]["authorization"]["source_ref"] = authority["source_ref"]
        switch.update(op="PROJECT_SWITCH", authority=authority,
                      source_ref="synthetic-ccr:explicit-new-request")
        self.state = engine.apply_command(self.state, switch, now=self.now)["state"]
        self.assertEqual(self.event("BEFORE_TURN_CLOSE")["action"], "CONTINUE")
        self.assertFalse(self.state.get("corrections"))
        self.assertEqual(self.state["correction_history"][0]["records"]["CCR-001"]["state"], "EXPIRED")

    def test_continuity_contains_corrections_as_data_without_authority(self):
        self.initialize()
        self.register()
        binding = self.state["binding"]
        result = self.command("PREPARE_CONTINUITY",
            architecture="Existing project controller and host tools.",
            resume_steps=["Revalidate current conditions and permissions."],
            invariants=["Preserve original objective and criteria."],
            handoff={
                "project_id": binding["project_id"], "mission_id": binding["mission_id"],
                "candidate": binding["candidate_id"], "operation": "VERIFICATION",
                "scope": binding["scope_id"],
                "acceptance": [c["description"] for c in self.state["anchor"]["baseline_criteria"]],
                "stop_status": "NOT_STOPPED", "sources": [{"ref": "synthetic-ccr:request", "version": "1", "retrieved": True}],
                "decisions": [], "evidence": [], "status": "PROPOSED",
                "pending": ["verify-db"], "resumption_authorized": False,
            })
        packet = result["data"]
        self.assertEqual(packet["corrections"], self.state["corrections"])
        self.assertEqual(packet["execution"], "NOT_RUN_AT_RECIPIENT")
        self.assertEqual(packet["authority"], "DATA_ONLY_REVALIDATE_AT_DESTINATION")
        self.assertFalse(packet["handoff"]["resumption_authorized"])

    def cli(self, command):
        result = subprocess.run([
            sys.executable, "-B", str(CLI), "--host", "WORK",
            "--session-id", self.initial["host_session_id"], "--data-dir", str(self.data),
        ], input=json.dumps(command), text=True, capture_output=True, check=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertIn(result.returncode, (0, 2), result.stderr)
        return json.loads(result.stdout)

    def cli_prepare(self, runtime_selection=None):
        self.initialize(runtime_selection=runtime_selection)
        self.assertEqual(self.cli(self.initial)["action"], "ALLOW")
        self.assertEqual(self.cli({"op": "REGISTER_CORRECTION", "source_ref": "synthetic-ccr:request",
                                  "correction": self.fixture["spec"]})["action"], "NOTICE")
        observed = datetime.now(timezone.utc)
        observation = deepcopy(self.fixture["observation"])
        observation.update(observed_at=observed.isoformat(),
                           valid_until=(observed + timedelta(minutes=5)).isoformat())
        return {"op": "REASSESS_CORRECTION", "source_ref": "synthetic-ccr:current-request",
                "correction_id": "CCR-001", "receipt": self.current_receipt(),
                "observation": observation}

    def test_persisted_cli_preserves_correction_and_resolves_with_current_evidence(self):
        command = self.cli_prepare()
        self.assertEqual(self.cli(command)["action"], "CONTINUE")
        status = self.cli({"op": "STATUS"})["data"]
        self.assertEqual(status["corrections"][0]["state"], "RESOLVED")
        saved = next(self.data.rglob("*.json"))
        content = json.loads(saved.read_text(encoding="utf-8"))
        self.assertEqual(content["receipt"]["actions"][0]["authorization"],
                         self.initial["receipt"]["actions"][0]["authorization"])
        self.assertEqual(len(content["corrections"]["CCR-001"]["events"]), 1)
        self.assertIsNone(content["memory"])

    def test_native_stop_rejects_cli_recovery_and_is_latched_without_controller_mutation(self):
        identity = bridge.inspect_suite(SUITE)["identity"]
        sys.path.insert(0, str(SUITE / "scripts"))
        from suite_control import TaskStore
        (self.workspace / "candidate.txt").write_text("fixed candidate\n", encoding="utf-8")
        (self.workspace / "acceptance.json").write_text(json.dumps({
            "schema": "bago.suite.check-result.v1", "status": "PASS", "findings": [], "coverage": "COMPLETE",
        }), encoding="utf-8")
        binding = self.fixture["receipt"]["binding"]
        selected = self.workspace.parent / "native-controller"
        store = TaskStore(selected, identity)
        store.initialize(self.workspace, {
            "schema": "bago.suite.task.plan.v1", "mission_id": binding["mission_id"],
            "candidate_id": binding["candidate_id"], "operation": "VERIFY", "scope": ["candidate.txt"],
            "max_rounds": 3, "checks": [{"id": "verify-db", "kind": "artifact", "mandatory": True,
                "depends_on": [], "artifacts": [{"path": "acceptance.json", "schema": "bago.suite.check-result.v1"}]}],
        })
        store.open_round()
        digest = bridge.observe_runtime(SUITE, selected, self.workspace)["controller"]["database_sha256"]
        command = self.cli_prepare({"state_dir": str(selected), "workspace_root": str(self.workspace),
                                   "expected_state_sha256": digest, "source_ref": "synthetic-ccr:selected-controller"})
        store.stop("synthetic explicit stop before recovery")
        before = {str(p): p.read_bytes() for p in selected.rglob("*") if p.is_file()}
        result = self.cli(command)
        self.assertEqual(result["action"], "BLOCKED")
        self.assertIn("NATIVE_CONTROLLER_REJECTED_RECOVERY", result["reason"])
        status = self.cli({"op": "STATUS"})["data"]
        self.assertEqual(status["control"], "STOP")
        self.assertEqual(status["corrections"][0]["state"], "WAITING_CONDITIONS")
        self.assertEqual(before, {str(p): p.read_bytes() for p in selected.rglob("*") if p.is_file()})


if __name__ == "__main__":
    unittest.main()
