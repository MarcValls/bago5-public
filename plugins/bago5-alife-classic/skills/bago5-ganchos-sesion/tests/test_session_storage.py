"""Real local processes and transactions; synthetic tool results, no remote MCP.

These tests exercise the packaged Python CLI/native adapter on this platform.
They do not install hooks or attest execution inside an actual Codex/Copilot host.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "skills/bago5-ganchos-sesion/scripts"
SPEC = importlib.util.spec_from_file_location("storage_test_session_store", SCRIPTS / "session_store.py")
STORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STORE)


class SessionStorageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bago5_session_storage_")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.workspace = self.base / "project"
        self.workspace.mkdir()
        self.data = self.base / "plugin-data"
        self.host = "CODEX"
        self.receipt = json.loads((ROOT / "skills/bago5/tests/fixtures/turn-decision/continue-work.json").read_text())
        self.session = self.receipt["binding"]["session_id"]
        self.receipt["current_host"] = self.host
        self.receipt["actions"][0]["target_host"] = self.host
        self.context = deepcopy(self.receipt["binding"])
        self.init = {
            "op": "INIT", "host": self.host, "host_session_id": self.session,
            "workspace_root": str(self.workspace), "receipt": deepcopy(self.receipt),
            "persistence": {"authorized": True, "source_ref": "test:explicit-local-persistence"},
            "source_ref": "test:explicit-session-request",
        }
        self.names = {operation: "mcp__synthetic_memory__" + operation
                      for operation in ("search_memories", "get_memory", "save_memory")}
        destination = dict(store_id="synthetic-store", owner_id="synthetic-owner",
                           connector_id="synthetic-connector", project_id="synthetic-memory-project")
        self.binding = {**destination, "mode": "READ_WRITE", "tools": deepcopy(self.names),
            "identity": {k: destination[k] for k in ("store_id", "owner_id", "connector_id")},
            "authorization": {
                "binding": deepcopy(self.context), "destination": deepcopy(destination),
                "read": True, "write": True, "source_ref": "test:explicit-memory-authority",
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            }}
        self.binding["identity"].update(verified=True, source_ref="test:observed-identity")
        self.payload = dict(title="Synthetic persisted checkpoint", content="Material observed result.",
                            project_id=destination["project_id"], kind="context", status="active",
                            source="test:observed-result", tags=["storage-test"], pinned=False,
                            archived=False, decision_closed=False)
        self.record = {**deepcopy(self.payload), "id": "synthetic-memory-id", "version": 1,
                       "owner_id": destination["owner_id"]}
        self.env = {**os.environ, "PLUGIN_DATA": str(self.data), "PYTHONDONTWRITEBYTECODE": "1"}

    @property
    def path(self):
        key = hashlib.sha256((self.host + "\0" + self.session).encode()).hexdigest()
        return self.data / "bago5-session-hooks" / (key + ".json")

    def read_state(self):
        return json.loads(self.path.read_text())

    def cli(self, command, data=None):
        process = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "session_cli.py"), "--host", self.host,
             "--session-id", self.session, "--data-dir", str(self.data if data is None else data)],
            input=json.dumps(command), text=True, capture_output=True, timeout=10, env=self.env)
        self.assertEqual(process.stderr, "", process.stderr)
        return process.returncode, json.loads(process.stdout)

    def command(self, operation, **fields):
        return self.cli({"op": operation, "source_ref": "test:explicit-command", **fields})

    def native_payload(self, event, **fields):
        return {"hook_event_name": event, "session_id": self.session,
                "cwd": str(self.workspace), **fields}

    def native(self, event, **fields):
        process = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "native_hooks.py"), "--host", self.host,
             "--event", event], input=json.dumps(self.native_payload(event, **fields)),
            text=True, capture_output=True, timeout=10, env=self.env)
        self.assertEqual(process.returncode, 0, process.stderr)
        return json.loads(process.stdout)

    def denied(self, output):
        return output.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def initialize(self):
        code, result = self.cli(self.init)
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)

    def select(self):
        self.initialize()
        code, result = self.command("SELECT_MEMORY", memory_binding=self.binding)
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)

    def tool(self, operation, args, call_id, response):
        fields = dict(tool_name=self.names[operation], tool_input=args, tool_use_id=call_id)
        before = self.native("PreToolUse", **fields)
        self.assertFalse(self.denied(before), before)
        return self.native("PostToolUse", **fields, tool_response=response)

    def prepared(self):
        self.select()
        self.tool("search_memories", {"project_id": self.binding["project_id"]}, "search-1",
                  {"structuredContent": {"memories": []}})
        code, result = self.command("PREPARE_CHECKPOINT", material=True, event_id="event-1", payload=self.payload)
        self.assertEqual((code, result["checkpoint_status"]), (0, "PREPARED"), result)

    def accepted_save(self):
        self.prepared()
        self.tool("save_memory", self.payload, "save-1", {"memory": self.record})
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "EXECUTED")

    def test_unauthorized_init_creates_no_files(self):
        command = deepcopy(self.init)
        command["persistence"]["authorized"] = False
        code, result = self.cli(command)
        self.assertEqual((code, result["action"]), (2, "BLOCKED"))
        self.assertIn("NOT_AUTHORIZED", result["reason"])
        self.assertFalse(self.data.exists())
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_native_session_start_without_state_creates_no_files(self):
        result = self.native("SessionStart", source="startup")
        self.assertIn("authorized local state surface", json.dumps(result))
        self.assertFalse(self.data.exists())
        before = self.native("PreToolUse", tool_name=self.names["save_memory"],
                             tool_input=self.payload, tool_use_id="unbound-save")
        self.assertTrue(self.denied(before))
        self.assertFalse(self.data.exists())

    def test_authorized_init_readback_permissions_and_no_temporary_leak(self):
        self.initialize()
        state = self.read_state()
        self.assertEqual(state["host_session_id"], self.session)
        self.assertEqual(state["binding"], self.context)
        self.assertTrue(state["persistence"]["authorized"])
        self.assertIsNone(state["memory"])
        if os.name != "nt":
            self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(self.path.parent.stat().st_mode), 0o700)
        self.assertFalse(list(self.path.parent.glob(".state-*.tmp")))
        code, result = self.command("STATUS")
        self.assertEqual(code, 0)
        self.assertEqual(result["data"]["binding"], state["binding"])

    def test_real_process_write_receipt_then_readback(self):
        self.prepared()
        selected = self.read_state()["memory"]
        self.assertEqual(selected["binding"]["authorization"]["destination"], selected["destination"])
        self.assertEqual(selected["binding"]["authorization"]["binding"], self.context)
        fields = dict(tool_name=self.names["save_memory"], tool_input=self.payload, tool_use_id="save-1")
        before = self.native("PreToolUse", **fields)
        self.assertFalse(self.denied(before), before)
        persisted = self.read_state()["memory"]
        self.assertEqual(persisted["pending"]["status"], "IN_FLIGHT")
        self.assertEqual(persisted["calls"]["save-1"]["status"], "IN_FLIGHT")
        self.native("PostToolUse", **fields, tool_response={"memory": self.record})
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "EXECUTED")
        self.tool("get_memory", {"id": self.record["id"]}, "readback-1",
                  {"memory": self.record, "history": [self.record]})
        verified = self.read_state()["memory"]
        self.assertEqual(verified["pending"]["status"], "VERIFIED")
        self.assertEqual(verified["events"]["event-1"]["status"], "VERIFIED")
        self.assertEqual(verified["reads"][self.record["id"]]["content"], self.payload["content"])

    def test_stop_survives_process_restart_without_goodbye_memory_action(self):
        self.accepted_save()
        prior = self.read_state()["memory"]
        code, result = self.command("STOP")
        self.assertEqual((code, result["action"]), (2, "STOP"))
        result = self.native("SessionStart", source="resume")
        self.assertIs(result.get("continue"), False)
        before = self.native("PreToolUse", tool_name=self.names["get_memory"],
                             tool_input={"id": self.record["id"]}, tool_use_id="forbidden-readback")
        self.assertTrue(self.denied(before))
        state = self.read_state()
        self.assertEqual(state["control"]["state"], "STOP")
        self.assertEqual(state["memory"], prior)
        original = self.path.read_bytes()
        code, result = self.cli(self.init)
        self.assertEqual((code, result["action"]), (2, "BLOCKED"))
        self.assertEqual(self.path.read_bytes(), original)

    def test_stop_also_denies_explicitly_bound_identity_and_project_reads(self):
        self.binding["tools"].update(identity="mcp__synthetic_memory__identity",
                                      list_projects="mcp__synthetic_memory__list_projects")
        self.select()
        self.command("STOP")
        original = self.path.read_bytes()
        for operation in ("identity", "list_projects"):
            output = self.native("PreToolUse", tool_name=self.binding["tools"][operation],
                                 tool_input={}, tool_use_id="stopped-" + operation)
            self.assertTrue(self.denied(output), operation)
        self.assertEqual(self.path.read_bytes(), original)

    def test_concurrent_presave_processes_admit_exactly_one(self):
        self.prepared()
        command = [sys.executable, "-B", str(SCRIPTS / "native_hooks.py"),
                   "--host", self.host, "--event", "PreToolUse"]
        processes = []
        original = self.path.read_bytes()
        try:
            with STORE.transaction(str(self.data), self.host, self.session):
                for number in (1, 2):
                    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, text=True, env=self.env)
                    processes.append(process)
                    process.stdin.write(json.dumps(self.native_payload("PreToolUse", tool_name=self.names["save_memory"],
                                                                       tool_input=self.payload, tool_use_id="race-" + str(number))))
                    process.stdin.close()
                    process.stdin = None
                # Hold the real state lock while both independent processes start.
                time.sleep(0.15)
                self.assertEqual(self.path.read_bytes(), original)
            outputs = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                outputs.append(json.loads(stdout))
            self.assertEqual(sum(not self.denied(output) for output in outputs), 1, outputs)
            memory = self.read_state()["memory"]
            self.assertEqual(memory["pending"]["status"], "IN_FLIGHT")
            self.assertEqual(len([key for key in memory["calls"] if key.startswith("race-")]), 1)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.communicate()

    def test_restart_marks_inflight_uncertain_and_does_not_retry(self):
        self.prepared()
        before = self.native("PreToolUse", tool_name=self.names["save_memory"],
                             tool_input=self.payload, tool_use_id="interrupted-save")
        self.assertFalse(self.denied(before))
        self.native("SessionStart", source="resume")
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "UNCERTAIN")
        retry = self.native("PreToolUse", tool_name=self.names["save_memory"],
                            tool_input=self.payload, tool_use_id="forbidden-retry")
        self.assertTrue(self.denied(retry))
        self.assertNotIn("forbidden-retry", self.read_state()["memory"]["calls"])

    def test_recovery_requires_current_receipt_before_dispatching_prepared_save(self):
        self.prepared()
        self.native("SessionStart", source="resume")
        recovered = self.read_state()
        self.assertIs(recovered["scope_current"], False)
        self.assertEqual(recovered["memory"]["pending"]["status"], "PREPARED")
        fields = dict(tool_name=self.names["save_memory"], tool_input=self.payload, tool_use_id="after-recovery")
        denied = self.native("PreToolUse", **fields)
        self.assertTrue(self.denied(denied))
        self.assertNotIn("after-recovery", self.read_state()["memory"]["calls"])
        code, result = self.command("SET_RECEIPT", receipt=deepcopy(self.receipt))
        self.assertEqual(code, 0, result)
        self.assertIs(self.read_state()["scope_current"], True)
        allowed = self.native("PreToolUse", **fields)
        self.assertFalse(self.denied(allowed), allowed)
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "IN_FLIGHT")

    def test_work_cli_event_wrapper_persists_the_same_pre_and_post_receipts(self):
        # WORK uses the explicit CLI workflow. Do not fabricate a native WORK host.
        self.host = "WORK"
        self.receipt["current_host"] = "WORK"
        self.receipt["actions"][0]["target_host"] = "WORK"
        self.init.update(host="WORK", receipt=deepcopy(self.receipt))
        self.select()

        def event(kind, operation, arguments, call_id, response=None):
            return self.command("EVENT", event={
                "event": kind, "host": "WORK", "host_session_id": self.session,
                "cwd": str(self.workspace), "tool_name": self.names[operation],
                "arguments": arguments, "call_id": call_id, "response": response,
            })

        search = {"project_id": self.binding["project_id"]}
        code, result = event("BEFORE_TOOL", "search_memories", search, "work-search")
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)
        code, result = event("AFTER_TOOL", "search_memories", search, "work-search", {"memories": []})
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)
        code, result = self.command("PREPARE_CHECKPOINT", material=True, event_id="work-event", payload=self.payload)
        self.assertEqual((code, result["checkpoint_status"]), (0, "PREPARED"), result)
        code, result = event("BEFORE_TOOL", "save_memory", self.payload, "work-save")
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "IN_FLIGHT")
        code, result = event("AFTER_TOOL", "save_memory", self.payload, "work-save", {"memory": self.record})
        self.assertEqual((code, result["checkpoint_status"]), (0, "EXECUTED"), result)
        get_args = {"id": self.record["id"]}
        code, result = event("BEFORE_TOOL", "get_memory", get_args, "work-readback")
        self.assertEqual((code, result["action"]), (0, "ALLOW"), result)
        code, result = event("AFTER_TOOL", "get_memory", get_args, "work-readback",
                             {"memory": self.record, "history": [self.record]})
        self.assertEqual((code, result["checkpoint_status"]), (0, "VERIFIED"), result)
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "VERIFIED")

    def test_copilot_documented_transport_without_call_id_correlates_serially(self):
        self.host = "COPILOT"
        self.receipt["current_host"] = "COPILOT"
        self.receipt["actions"][0]["target_host"] = "COPILOT"
        self.init.update(host="COPILOT", receipt=deepcopy(self.receipt))
        self.select()

        def copilot(native_event, operation, arguments, response=None):
            # Documented native fields only; no invented tool call identifier.
            payload = {"sessionId": self.session, "cwd": str(self.workspace),
                       "toolName": self.names[operation], "toolArgs": json.dumps(arguments)}
            if native_event == "postToolUse":
                payload["toolResult"] = {"resultType": "success", "textResultForLlm": json.dumps(response)}
            process = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / "native_hooks.py"), "--host", "COPILOT",
                 "--event", native_event], input=json.dumps(payload), text=True,
                capture_output=True, timeout=10, env=self.env)
            self.assertEqual(process.returncode, 0, process.stderr)
            return json.loads(process.stdout)

        search = {"project_id": self.binding["project_id"]}
        admitted = copilot("preToolUse", "search_memories", search)
        self.assertNotEqual(admitted.get("permissionDecision"), "deny", admitted)
        state = self.read_state()
        self.assertEqual(state["anonymous_call"]["call_id"], "anonymous-1")
        self.assertEqual(state["call_sequence"], 1)
        second = copilot("preToolUse", "search_memories", search)
        self.assertEqual(second.get("permissionDecision"), "deny", second)
        self.assertEqual(self.read_state()["call_sequence"], 1)
        # A result with different arguments cannot consume the outstanding call.
        copilot("postToolUse", "search_memories", {**search, "query": "different"}, {"memories": []})
        self.assertEqual(self.read_state()["anonymous_call"]["call_id"], "anonymous-1")
        self.assertEqual(self.read_state()["memory"]["searches"], 0)
        copilot("postToolUse", "search_memories", search, {
            "content": [{"type": "text", "text": json.dumps({"memories": []})}], "isError": False})
        self.assertIsNone(self.read_state()["anonymous_call"])
        self.assertEqual(self.read_state()["memory"]["searches"], 1)
        code, prepared = self.command("PREPARE_CHECKPOINT", material=True, event_id="copilot-event", payload=self.payload)
        self.assertEqual((code, prepared["checkpoint_status"]), (0, "PREPARED"), prepared)
        admitted = copilot("preToolUse", "save_memory", self.payload)
        self.assertNotEqual(admitted.get("permissionDecision"), "deny", admitted)
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "IN_FLIGHT")
        self.assertEqual(self.read_state()["anonymous_call"]["call_id"], "anonymous-2")
        copilot("postToolUse", "save_memory", self.payload, {"result": {"structuredContent": {"memory": self.record}}})
        self.assertEqual(self.read_state()["memory"]["pending"]["status"], "EXECUTED")
        self.assertIsNone(self.read_state()["anonymous_call"])
        get_args = {"id": self.record["id"]}
        admitted = copilot("preToolUse", "get_memory", get_args)
        self.assertNotEqual(admitted.get("permissionDecision"), "deny", admitted)
        result = copilot("postToolUse", "get_memory", get_args, {"memory": self.record, "history": [self.record]})
        self.assertIn("VERIFIED", result.get("additionalContext", ""))
        final = self.read_state()
        self.assertEqual(final["memory"]["pending"]["status"], "VERIFIED")
        self.assertEqual(final["memory"]["events"]["copilot-event"]["status"], "VERIFIED")
        self.assertEqual(set(final["memory"]["calls"]), {"anonymous-1", "anonymous-2", "anonymous-3"})
        self.assertEqual(final["call_sequence"], 3)
        self.assertIsNone(final["anonymous_call"])

    def test_init_rejects_a_different_host_and_authority_session(self):
        mismatch = deepcopy(self.init)
        mismatch["host_session_id"] = "other-session"
        code, result = self.cli(mismatch)
        self.assertEqual((code, result["action"]), (2, "BLOCKED"), result)
        self.assertFalse(self.data.exists())

    def test_work_event_checks_the_explicit_runtime_before_memory_admission(self):
        self.host = "WORK"
        self.receipt["current_host"] = "WORK"
        self.receipt["actions"][0]["target_host"] = "WORK"
        missing_state = self.base / "selected-runtime-without-state"
        missing_state.mkdir()
        self.init.update(host="WORK", receipt=deepcopy(self.receipt), runtime_selection={
            "state_dir": str(missing_state), "workspace_root": str(self.workspace),
            "expected_state_sha256": "0" * 64, "source_ref": "test:explicit-runtime-selection",
        })
        self.select()
        code, result = self.command("EVENT", event={
            "event": "BEFORE_TOOL", "host": "WORK", "host_session_id": self.session,
            "cwd": str(self.workspace), "tool_name": self.names["search_memories"],
            "arguments": {"project_id": self.binding["project_id"]}, "call_id": "runtime-unobserved",
        })
        self.assertEqual(code, 2, result)
        self.assertIn(result["action"], {"DENY", "BLOCKED"})
        self.assertNotIn("runtime-unobserved", self.read_state()["memory"]["calls"])
        self.assertEqual(self.read_state()["memory"]["searches"], 0)

    def test_changing_bound_tool_names_is_explicitly_rejected_without_state_change(self):
        self.select()
        original = self.path.read_bytes()
        changed = deepcopy(self.binding)
        changed["tools"]["save_memory"] = "mcp__different_alias__save_memory"
        code, result = self.command("SELECT_MEMORY", memory_binding=changed)
        self.assertEqual((code, result["action"]), (2, "BLOCKED"), result)
        self.assertEqual(self.path.read_bytes(), original)

    def test_foreign_destination_authority_does_not_persist_selection(self):
        self.initialize()
        original = self.path.read_bytes()
        for dimension in ("store_id", "owner_id", "connector_id", "project_id"):
            changed = deepcopy(self.binding)
            changed[dimension] += "-other"
            if dimension in changed["identity"]:
                changed["identity"][dimension] = changed[dimension]
            code, result = self.command("SELECT_MEMORY", memory_binding=changed)
            self.assertEqual((code, result["action"]), (2, "BLOCKED"), dimension)
            self.assertEqual(self.path.read_bytes(), original)

    def test_changed_working_project_denies_memory_without_mutation(self):
        self.select()
        original = self.path.read_bytes()
        foreign = self.base / "other-project"
        foreign.mkdir()
        result = self.native("PreToolUse", cwd=str(foreign), tool_name=self.names["search_memories"],
                             tool_input={"project_id": self.binding["project_id"]}, tool_use_id="foreign-project")
        self.assertTrue(self.denied(result))
        self.assertEqual(self.path.read_bytes(), original)

    @unittest.skipUnless(hasattr(os, "symlink"), "Platform does not expose symbolic links")
    def test_symlink_data_root_is_refused_without_writing_target(self):
        destination = self.base / "unrelated-data"
        destination.mkdir()
        link = self.base / "linked-data"
        try:
            link.symlink_to(destination, target_is_directory=True)
        except OSError as error:
            self.skipTest("Symbolic links unavailable: " + str(error))
        code, result = self.cli(self.init, data=link)
        self.assertEqual((code, result["action"]), (2, "BLOCKED"))
        self.assertIn("SYMLINK", result["reason"])
        self.assertEqual(list(destination.iterdir()), [])

    @unittest.skipUnless(hasattr(os, "symlink"), "Platform does not expose symbolic links")
    def test_symlink_state_file_is_refused_and_target_stays_unchanged(self):
        self.initialize()
        target = self.base / "unrelated.json"
        target.write_text('{"sentinel":"unchanged"}')
        self.path.unlink()
        try:
            self.path.symlink_to(target)
        except OSError as error:
            self.skipTest("Symbolic links unavailable: " + str(error))
        original = target.read_bytes()
        code, result = self.command("STATUS")
        self.assertEqual((code, result["action"]), (2, "BLOCKED"))
        self.assertIn("SYMLINK", result["reason"])
        self.assertEqual(target.read_bytes(), original)

    def test_malformed_json_or_relative_root_creates_no_state(self):
        code, result = self.cli(self.init, data="relative-plugin-data")
        self.assertEqual((code, result["action"]), (2, "BLOCKED"))
        self.assertEqual(result["reason"], "ABSOLUTE_PLUGIN_DATA_REQUIRED")
        process = subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / "session_cli.py"), "--data-dir", str(self.data)],
            input='{"op":"INIT","op":"STOP"}', text=True, capture_output=True,
            timeout=10, env=self.env)
        self.assertEqual(process.returncode, 2)
        self.assertIn("DUPLICATE_JSON_KEY", process.stdout)
        self.assertFalse(self.data.exists())


if __name__ == "__main__":
    unittest.main()
