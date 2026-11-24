"""Bounded closure review with synthetic receipts and native payloads.

The real evaluator, session transitions and adapters execute locally. These
checks do not install hooks, observe host events or call a memory service.
"""
from copy import deepcopy
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_session_acceptance as fixtures


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/bago5-ganchos-sesion/scripts"))
engine = importlib.import_module("session_engine")
native = importlib.import_module("native_hooks")
HOSTS = (("CODEX", "Stop"), ("COPILOT", "agentStop"))


def native_payload(host, name, workspace, session, **fields):
    payload = {"cwd": str(workspace), "hook_event_name": name}
    payload["session_id" if host == "CODEX" else "sessionId"] = session
    if native.EVENTS[host][name] in {"BEFORE_TOOL", "AFTER_TOOL"}:
        if host == "CODEX":
            payload.update(tool_name="mcp__synthetic__get_memory", tool_input={})
        else:
            payload.update(toolName="mcp__synthetic__get_memory", toolArgs={})
    payload.update(fields)
    return json.dumps(payload).encode()


class ClosureReviewRegression(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bago5-closure-review-")
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)

    def initialize(self, host="CODEX", receipt=None, runtime=False):
        self.original_receipt = fixtures.session_receipt(host)
        if receipt is None:
            receipt = deepcopy(self.original_receipt)
            receipt["actions"] = []
        command = {
            "op": "INIT", "host": host,
            "host_session_id": receipt["binding"]["session_id"],
            "workspace_root": str(self.workspace), "receipt": receipt,
            "source_ref": "synthetic-closure:current-scope",
            "persistence": {"authorized": True, "source_ref": "synthetic-closure:local-state"},
        }
        if runtime:
            command["runtime_selection"] = {
                "state_dir": str(self.workspace / "selected-controller"),
                "workspace_root": str(self.workspace), "expected_state_sha256": "a" * 64,
                "source_ref": "synthetic-closure:existing-controller",
            }
        self.state = engine.apply_command(None, command, now=fixtures.NOW)["state"]

    def command(self, op, **fields):
        output = engine.apply_command(self.state, {
            "op": op, "source_ref": "synthetic-closure:current-instruction", **fields,
        }, now=fixtures.NOW)
        self.state = output["state"]
        return output["result"]

    def event(self, kind, **fields):
        return {
            "event": kind, "host": self.state["host"],
            "host_session_id": self.state["host_session_id"],
            "cwd": str(self.workspace), **fields,
        }

    def observe(self, event):
        output = engine.handle_event(self.state, event, now=fixtures.NOW)
        self.state = output["state"]
        self.result = output["result"]
        return self.result

    def close(self, active=False, callback=None):
        host = self.state["host"]
        name = dict(HOSTS)[host]
        raw = native_payload(host, name, self.workspace,
                             self.state["host_session_id"], stop_hook_active=active)
        return native.dispatch(raw, host, name, callback or self.observe)

    def make_receipt_stale(self, source):
        if source == "USER_PROMPT":
            self.observe(self.event("USER_PROMPT", prompt="A current clarification."))
        else:
            binding = fixtures.selected_memory_binding(self.state["binding"])
            self.command("SELECT_MEMORY", memory_binding=binding)
            fields = {
                "tool_name": binding["tools"]["search_memories"],
                "arguments": {"project_id": binding["project_id"]},
                "call_id": "synthetic-search" if self.state["host"] == "CODEX" else "",
            }
            before = self.observe(self.event("BEFORE_TOOL", **fields))
            self.assertEqual(before["action"], "ALLOW")
            after = self.observe(self.event("AFTER_TOOL", **fields, response={"memories": []}))
            self.assertEqual(after["checkpoint_status"], "EXECUTED")
        self.assertIs(self.state["receipt_stale"], True)

    def test_first_review_blocks_closure_without_new_state_or_operation_authority(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                self.initialize(host)
                before = deepcopy(self.state)
                output, _ = self.close()
                self.assertEqual(output["decision"], "block")
                self.assertEqual(self.result["action"], "BLOCKED")
                self.assertIs(self.result["review_before_close"], True)
                self.assertIs(self.result["data"]["closure"]["review_required"], True)
                self.assertEqual(self.result["data"]["eligible_actions"], [])
                self.assertIn("no concede permisos", output["reason"])
                self.assertEqual(set(self.state), set(before))
                before["last_continue_digest"] = engine.digest(before["receipt"])
                self.assertEqual(self.state, before)
                self.assertEqual(engine.summary(self.state)["authority"], "DATA_ONLY_NOT_PERMISSION")

    def test_unchanged_receipt_does_not_repeat_or_erase_the_closure_diagnosis(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                self.initialize(host)
                self.close()
                first = deepcopy(self.result)
                before = deepcopy(self.state)
                output, _ = self.close()
                self.assertNotEqual(output.get("decision"), "block")
                self.assertEqual(self.result["action"], "BLOCKED")
                self.assertIs(self.result["review_before_close"], False)
                self.assertEqual(self.result["data"], first["data"])
                self.assertEqual(self.result["reason"], first["reason"])
                self.assertIn("cierre no sustentado", self.result["context"])
                self.assertEqual(self.state, before)

    def test_active_stop_hook_suppresses_review_even_on_the_first_receipt(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                self.initialize(host)
                output, _ = self.close(active=True)
                self.assertNotEqual(output.get("decision"), "block")
                self.assertEqual(self.result["action"], "BLOCKED")
                self.assertIs(self.result["review_before_close"], False)
                self.assertIs(self.result["data"]["closure"]["review_required"], True)
                self.assertIsNone(self.state["last_continue_digest"])

    def test_refreshing_an_identical_receipt_does_not_rearm_review(self):
        self.initialize()
        receipt = deepcopy(self.state["receipt"])
        self.close()
        self.command("SET_RECEIPT", receipt=receipt)
        output, _ = self.close()
        self.assertNotEqual(output.get("decision"), "block")
        self.assertIs(self.result["review_before_close"], False)

    def test_corrected_receipt_returns_to_existing_continuation_without_a_loop(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                self.initialize(host)
                self.close()
                self.command("SET_RECEIPT", receipt=self.original_receipt)
                output, _ = self.close()
                self.assertEqual(self.result["action"], "CONTINUE")
                self.assertNotIn("review_before_close", self.result)
                self.assertEqual(output["decision"], "block")
                self.assertEqual(self.state["receipt"]["baseline_criteria"],
                                 self.original_receipt["baseline_criteria"])
                output, _ = self.close()
                self.assertEqual(self.result["action"], "BLOCKED")
                self.assertNotEqual(output.get("decision"), "block")

    def test_documented_current_blocker_allows_reporting_without_forced_review(self):
        for host, _name in HOSTS:
            with self.subTest(host=host):
                receipt = fixtures.session_receipt(host)
                for action in receipt["actions"]:
                    action["blocker"] = {
                        "reason": "The selected fixture source returned an access denial.",
                        "source_ref": "synthetic-closure:observed-denial:" + action["id"],
                        "intervention": "Restore access to the selected source.",
                        "basis": "OBSERVATION", "current": True,
                    }
                self.initialize(host, receipt)
                output, _ = self.close()
                self.assertEqual(self.result["action"], "BLOCKED")
                self.assertIs(self.result["data"]["closure"]["review_required"], False)
                self.assertIs(self.result["data"]["closure"]["report_ready"], True)
                self.assertNotIn("review_before_close", self.result)
                self.assertNotEqual(output.get("decision"), "block")
                self.assertIsNone(self.state["last_continue_digest"])

    def test_stop_and_global_revocation_precede_closure_evaluation(self):
        for host, _name in HOSTS:
            for control in ("STOP", "REVOKED"):
                with self.subTest(host=host, control=control):
                    receipt = fixtures.session_receipt(host)
                    receipt["actions"] = []
                    receipt["control"]["state"] = control
                    self.initialize(host, receipt)
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("STOP precedes review")) as assess:
                        output, _ = self.close()
                    assess.assert_not_called()
                    self.assertEqual(self.result["action"], "STOP")
                    self.assertNotIn("review_before_close", self.result)
                    self.assertNotEqual(output.get("decision"), "block")
                    self.assertEqual(self.state["control"]["state"], control)
                    self.assertIsNone(self.state["last_continue_digest"])
                    if host == "CODEX":
                        self.assertIs(output["continue"], False)

    def test_stale_running_receipt_requests_metadata_review_without_assessing_old_data(self):
        for host, _name in HOSTS:
            for source in ("USER_PROMPT", "AFTER_TOOL"):
                with self.subTest(host=host, source=source):
                    self.initialize(host)
                    self.make_receipt_stale(source)
                    before = deepcopy(self.state)
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale receipt cannot be assessed")) as assess:
                        output, _ = self.close()
                    assess.assert_not_called()
                    self.assertEqual(self.result["action"], "BLOCKED")
                    self.assertIs(self.result["review_before_close"], True)
                    self.assertNotIn("data", self.result)
                    self.assertEqual(output["decision"], "block")
                    self.assertIn("metadatos", output["reason"])
                    self.assertIn("no concede permisos", output["reason"])
                    before["last_continue_digest"] = engine.digest({
                        "receipt": before["receipt"], "receipt_stale": True,
                    })
                    self.assertEqual(self.state, before)

    def test_stale_review_is_distinct_from_fresh_review_and_does_not_repeat(self):
        for host, _name in HOSTS:
            for source in ("USER_PROMPT", "AFTER_TOOL"):
                with self.subTest(host=host, source=source):
                    self.initialize(host)
                    self.close()
                    fresh_digest = self.state["last_continue_digest"]
                    self.make_receipt_stale(source)
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale receipt cannot be assessed")) as assess:
                        output, _ = self.close()
                        self.assertEqual(output["decision"], "block")
                        self.assertNotEqual(self.state["last_continue_digest"], fresh_digest)
                        first_reason = self.result["reason"]
                        before = deepcopy(self.state)
                        output, _ = self.close()
                    assess.assert_not_called()
                    self.assertNotEqual(output.get("decision"), "block")
                    self.assertEqual(self.result["action"], "BLOCKED")
                    self.assertIs(self.result["review_before_close"], False)
                    self.assertEqual(self.result["reason"], first_reason)
                    self.assertIn("recibo de turno obsoleto", self.result["context"])
                    self.assertEqual(self.state, before)

    def test_stale_receipt_respects_active_stop_hook_without_assessment(self):
        for host, _name in HOSTS:
            for source in ("USER_PROMPT", "AFTER_TOOL"):
                with self.subTest(host=host, source=source):
                    self.initialize(host)
                    self.make_receipt_stale(source)
                    before = deepcopy(self.state)
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("Stale receipt cannot be assessed")) as assess:
                        output, _ = self.close(active=True)
                    assess.assert_not_called()
                    self.assertEqual(self.result["action"], "BLOCKED")
                    self.assertIs(self.result["review_before_close"], False)
                    self.assertNotEqual(output.get("decision"), "block")
                    self.assertEqual(self.state, before)

    def test_renewed_stale_receipt_can_continue_authorized_work(self):
        for host, _name in HOSTS:
            for source in ("USER_PROMPT", "AFTER_TOOL"):
                with self.subTest(host=host, source=source):
                    self.initialize(host)
                    self.make_receipt_stale(source)
                    self.close()
                    self.command("SET_RECEIPT", receipt=self.original_receipt)
                    self.assertIs(self.state["receipt_stale"], False)
                    output, _ = self.close()
                    self.assertEqual(self.result["action"], "CONTINUE")
                    self.assertNotIn("review_before_close", self.result)
                    self.assertEqual(output["decision"], "block")
                    output, _ = self.close()
                    self.assertEqual(self.result["action"], "BLOCKED")
                    self.assertNotEqual(output.get("decision"), "block")

    def test_stale_receipt_without_current_running_control_never_forces_review(self):
        for host, _name in HOSTS:
            for control, current in (("UNKNOWN", True), ("RUNNING", False), ("STOP", True), ("REVOKED", True)):
                with self.subTest(host=host, control=control, current=current):
                    self.initialize(host)
                    self.make_receipt_stale("USER_PROMPT")
                    if control == "UNKNOWN":
                        self.observe(self.event("INTERRUPT"))
                    elif control == "STOP":
                        self.command("STOP")
                    else:
                        # A synthetic observation of noncurrent or revoked
                        # control must remain dominant over stale metadata.
                        self.state["control"].update(state=control, current=current)
                        self.state["receipt"]["control"] = deepcopy(self.state["control"])
                    before = deepcopy(self.state)
                    with patch.object(engine.policy, "assess", side_effect=AssertionError("Control precedes metadata review")) as assess:
                        output, _ = self.close()
                    assess.assert_not_called()
                    self.assertEqual(self.result["action"], "STOP" if control in {"STOP", "REVOKED"} else "BLOCKED")
                    self.assertNotIn("review_before_close", self.result)
                    self.assertNotEqual(output.get("decision"), "block")
                    self.assertEqual(self.state, before)

    def test_controller_gate_precedes_review_and_cannot_be_overridden(self):
        store = importlib.import_module("session_store")
        for host, _name in HOSTS:
            for gate in ("BLOCKED", "STOP"):
                for stale in (False, True):
                    with self.subTest(host=host, gate=gate, stale=stale):
                        self.initialize(host, runtime=True)
                        if stale:
                            self.make_receipt_stale("USER_PROMPT")
                        data_dir = self.workspace / (host + "-" + gate + "-" + str(stale))
                        with store.transaction(str(data_dir), host, self.state["host_session_id"], create=True) as tx:
                            tx.save(self.state)
                        observation = {"decision": gate, "issues": ["synthetic selected controller gate"]}
                        with patch.dict(os.environ, {"PLUGIN_DATA": str(data_dir)}), \
                                patch.object(engine, "_runtime_check", return_value=observation), \
                                patch.object(engine.policy, "assess", side_effect=AssertionError("Controller gate precedes review")) as assess:
                            output, _ = self.close(callback=engine.run_native)
                        assess.assert_not_called()
                        self.assertNotEqual(output.get("decision"), "block")
                        with store.transaction(str(data_dir), host, self.state["host_session_id"], create=False) as tx:
                            self.assertIsNone(tx.state["last_continue_digest"])
                            self.assertEqual(tx.state["control"]["state"], "STOP" if gate == "STOP" else "RUNNING")
                        if gate == "STOP" and host == "CODEX":
                            self.assertIs(output["continue"], False)

    def test_closure_review_does_not_grant_missing_or_revoked_memory_permission(self):
        for revoked in (False, True):
            with self.subTest(revoked=revoked):
                self.initialize()
                tool = "mcp__synthetic_a__get_memory"
                if revoked:
                    binding = fixtures.selected_memory_binding(self.state["binding"])
                    self.command("SELECT_MEMORY", memory_binding=binding)
                    tool = binding["tools"]["get_memory"]
                    self.command("REVOKE_MEMORY", reason="Current memory permission revoked.")
                self.close()
                self.assertIs(self.result["review_before_close"], True)
                result = self.observe(self.event("BEFORE_TOOL", tool_name=tool,
                                                arguments={"id": "synthetic-record"}, call_id="after-review"))
                self.assertEqual(result["action"], "DENY")
                if revoked:
                    self.assertIs(self.state["memory"]["revoked"], True)
                else:
                    self.assertIsNone(self.state["memory"])


class NativeReviewContractRegression(unittest.TestCase):
    def test_optional_review_flag_is_strictly_boolean_and_only_valid_for_blocked(self):
        self.assertNotIn("review_before_close", native._decision({"action": "BLOCKED"}))
        for flag in (True, False):
            self.assertIs(native._decision({"action": "BLOCKED", "review_before_close": flag})["review_before_close"], flag)
        for flag in (None, 0, 1, "true", [], {}):
            with self.subTest(flag=flag), self.assertRaises(native.ContractError):
                native._decision({"action": "BLOCKED", "review_before_close": flag})
        for action in native.ACTIONS - {"BLOCKED"}:
            for flag in (True, False):
                with self.subTest(action=action, flag=flag), self.assertRaises(native.ContractError):
                    native._decision({"action": action, "review_before_close": flag})

    def test_review_flag_changes_no_other_event_contract_or_permissions(self):
        base = {"action": "BLOCKED", "reason": "synthetic pending work", "context": "synthetic review context"}
        for host, events in native.EVENTS.items():
            for name, kind in events.items():
                if kind == "BEFORE_TURN_CLOSE":
                    continue
                with self.subTest(host=host, event=name):
                    raw = native_payload(host, name, "/synthetic/project", "synthetic-session")
                    ordinary = native.dispatch(raw, host, name, lambda _event: base)
                    review = native.dispatch(raw, host, name, lambda _event: {**base, "review_before_close": True})
                    self.assertEqual(review, ordinary)
                    output, _ = review
                    self.assertNotEqual(output.get("decision"), "block")
                    fields = output.get("hookSpecificOutput", output)
                    self.assertNotEqual(fields.get("permissionDecision"), "allow")
                    if kind == "BEFORE_TOOL":
                        self.assertEqual(fields["permissionDecision"], "deny")

    def test_malformed_review_flag_cannot_allow_memory_or_force_a_turn(self):
        for host, close in HOSTS:
            before = "PreToolUse" if host == "CODEX" else "preToolUse"
            for name in (before, close):
                with self.subTest(host=host, event=name):
                    raw = native_payload(host, name, "/synthetic/project", "synthetic-session")
                    output, _ = native.dispatch(raw, host, name, lambda _event: {
                        "action": "BLOCKED", "review_before_close": "true",
                    })
                    self.assertNotEqual(output.get("decision"), "block")
                    if name == before:
                        fields = output.get("hookSpecificOutput", output)
                        self.assertEqual(fields["permissionDecision"], "deny")


if __name__ == "__main__":
    unittest.main()
