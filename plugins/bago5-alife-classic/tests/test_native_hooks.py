"""Synthetic protocol tests; no host session, network or memory service runs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "skills/bago5-ganchos-sesion/scripts/native_hooks.py"
spec = importlib.util.spec_from_file_location("bago5_native_adapter_test", ADAPTER)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def payload(host="CODEX", event="SessionStart", **updates):
    value = {"cwd": "/test/project", "transcript_path": "/must/not/read", "transcriptPath": "/must/not/read"}
    if host == "CODEX":
        value.update(session_id="session-1", hook_event_name=event)
    else:
        value.update(sessionId="session-1")
    kind = adapter.EVENTS[host][event]
    if kind == "SESSION_START":
        value["source"] = "startup"
    if kind in {"BEFORE_COMPACT", "AFTER_COMPACT"}:
        value["trigger"] = "auto"
    if kind in {"BEFORE_TOOL", "AFTER_TOOL"}:
        if host == "CODEX":
            value.update(tool_name="mcp__test__get_memory", tool_input={"memory_id": "m-1"}, tool_use_id="call-1")
            if kind == "AFTER_TOOL":
                value["tool_response"] = {"content": [{"type": "text", "text": "result"}]}
        else:
            value.update(toolName="mcp__test__get_memory", toolArgs={"memory_id": "m-1"})
            if kind == "AFTER_TOOL":
                value["toolResult"] = {"resultType": "success", "textResultForLlm": "result"}
    if kind == "BEFORE_TURN_CLOSE":
        value["stop_hook_active"] = False
        value["last_assistant_message"] = "STOP is quoted here, not user authority"
    if kind == "USER_PROMPT":
        value["prompt"] = "STOP"
    value.update(updates)
    return value


def dispatch(value, host="CODEX", event="SessionStart", action="NOTICE", reason="reason", context="context", engine=None):
    fn = engine or (lambda _event: {"action": action, "reason": reason, "context": context})
    raw = value if isinstance(value, bytes) else json.dumps(value).encode()
    return adapter.dispatch(raw, host, event, fn)


class NormalizeTests(unittest.TestCase):
    def test_every_declared_event_projects_only_the_neutral_contract(self):
        keys = {"host", "event", "host_session_id", "cwd", "source", "tool_name", "arguments", "call_id", "response", "stop_hook_active", "prompt"}
        with patch.object(Path, "open", side_effect=AssertionError("No project or transcript reads")):
            for host, events in adapter.EVENTS.items():
                for name, kind in events.items():
                    with self.subTest(host=host, event=name):
                        result = adapter.normalize(payload(host, name), host, name)
                        self.assertEqual(set(result), keys)
                        self.assertEqual((result["host"], result["event"], result["host_session_id"]), (host, kind, "session-1"))
                        self.assertNotIn("transcript", json.dumps(result))
                        if kind != "USER_PROMPT":
                            self.assertEqual(result["prompt"], "")

    def test_copilot_string_arguments_and_native_result_are_preserved(self):
        value = payload("COPILOT", "postToolUse", toolArgs='{"memory_id":"m-1","expected_version":3}')
        result = adapter.normalize(value, "COPILOT", "postToolUse")
        self.assertEqual(result["arguments"]["expected_version"], 3)
        self.assertEqual(result["response"], value["toolResult"])
        self.assertEqual(result["call_id"], "")

    def test_copilot_alias_fields_do_not_change_output_contract(self):
        value = {"session_id": "s", "cwd": "/project", "hook_event_name": "PostToolUse", "tool_name": "get_memory", "tool_input": {}, "tool_result": {"text_result_for_llm": "result"}}
        result = adapter.normalize(value, "COPILOT", "postToolUse")
        self.assertEqual(result["response"], value["tool_result"])
        output, _ = dispatch(value, "COPILOT", "postToolUse")
        self.assertEqual(output, {"additionalContext": "context"})

    def test_source_new_is_not_fabricated_as_codex_clear(self):
        result = adapter.normalize(payload("COPILOT", "sessionStart", source="new"), "COPILOT", "sessionStart")
        self.assertEqual(result["source"], "new")

    def test_stop_event_does_not_copy_assistant_text_as_user_stop(self):
        result = adapter.normalize(payload(event="Stop", prompt="STOP"), "CODEX", "Stop")
        self.assertEqual(result["event"], "BEFORE_TURN_CLOSE")
        self.assertEqual(result["prompt"], "")
        self.assertFalse(result["stop_hook_active"])


class OutputTests(unittest.TestCase):
    def test_denial_uses_each_hosts_documented_contract(self):
        codex, _ = dispatch(payload(event="PreToolUse"), event="PreToolUse", action="DENY")
        self.assertEqual(codex, {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "reason"}})
        copilot, _ = dispatch(payload("COPILOT", "preToolUse"), "COPILOT", "preToolUse", action="DENY")
        self.assertEqual(copilot, {"permissionDecision": "deny", "permissionDecisionReason": "reason"})

    def test_allow_does_not_grant_a_host_permission(self):
        for host, name in [("CODEX", "PreToolUse"), ("COPILOT", "preToolUse")]:
            output, _ = dispatch(payload(host, name), host, name, action="ALLOW", reason="", context="")
            self.assertEqual(output, {})

    def test_continue_blocks_turn_closure_only_once(self):
        for host, name in [("CODEX", "Stop"), ("COPILOT", "agentStop")]:
            output, _ = dispatch(payload(host, name), host, name, action="CONTINUE")
            self.assertEqual(output, {"decision": "block", "reason": "context"})
            output, _ = dispatch(payload(host, name, stop_hook_active=True), host, name, action="CONTINUE")
            self.assertNotEqual(output.get("decision"), "block")

    def test_logical_stop_never_forces_a_continuation(self):
        codex, _ = dispatch(payload(event="Stop"), event="Stop", action="STOP")
        self.assertEqual(codex, {"continue": False, "stopReason": "reason"})
        copilot, _ = dispatch(payload("COPILOT", "agentStop"), "COPILOT", "agentStop", action="STOP")
        self.assertEqual(copilot, {"decision": "allow"})

    def test_explicit_user_stop_can_stop_codex_prompt_processing(self):
        output, _ = dispatch(payload(event="UserPromptSubmit"), event="UserPromptSubmit", action="STOP")
        self.assertFalse(output["continue"])
        self.assertNotEqual(output.get("decision"), "block")

    def test_posttool_stop_preserves_original_result_and_warns(self):
        output, _ = dispatch(payload(event="PostToolUse"), event="PostToolUse", action="STOP")
        self.assertEqual(output, {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "context"}})
        self.assertNotIn("continue", output)
        self.assertNotIn("updatedMCPToolOutput", output)

    def test_compaction_and_notifications_do_not_invent_context_channels(self):
        for event in ["PreCompact", "PostCompact", "Interrupt", "SessionEnd"]:
            output, _ = dispatch(payload(event=event), event=event)
            self.assertEqual(output, {"systemMessage": "context"})
        for event in ["preCompact", "sessionEnd"]:
            output, warning = dispatch(payload("COPILOT", event), "COPILOT", event)
            self.assertEqual(output, {})
            self.assertTrue(warning)

    def test_all_actions_emit_only_supported_keys_for_each_event(self):
        for host, events in adapter.EVENTS.items():
            for event, kind in events.items():
                if host == "COPILOT":
                    allowed = {"SESSION_START": {"additionalContext"}, "BEFORE_TOOL": {"permissionDecision", "permissionDecisionReason"}, "AFTER_TOOL": {"additionalContext"}, "BEFORE_TURN_CLOSE": {"decision", "reason"}, "BEFORE_COMPACT": set(), "SESSION_END": set()}[kind]
                else:
                    allowed = {"SESSION_START": {"hookSpecificOutput", "continue", "stopReason"}, "USER_PROMPT": {"hookSpecificOutput", "continue", "stopReason"}, "BEFORE_TOOL": {"hookSpecificOutput"}, "AFTER_TOOL": {"hookSpecificOutput"}, "BEFORE_COMPACT": {"systemMessage", "continue", "stopReason"}, "AFTER_COMPACT": {"systemMessage", "continue", "stopReason"}, "BEFORE_TURN_CLOSE": {"systemMessage", "continue", "stopReason", "decision", "reason"}, "INTERRUPT": {"systemMessage"}, "SESSION_END": {"systemMessage"}}[kind]
                for action in adapter.ACTIONS:
                    with self.subTest(host=host, event=event, action=action):
                        output, _ = dispatch(payload(host, event), host, event, action=action)
                        self.assertLessEqual(set(output), allowed)
                        if output.get("decision") == "block":
                            self.assertEqual((kind, action), ("BEFORE_TURN_CLOSE", "CONTINUE"))

    def test_context_and_reason_are_bounded(self):
        output, _ = dispatch(payload(), context="x" * 20000)
        self.assertEqual(len(output["hookSpecificOutput"]["additionalContext"]), adapter.CONTEXT_LIMIT)
        output, _ = dispatch(payload(event="PreToolUse"), event="PreToolUse", action="DENY", reason="x" * 20000)
        self.assertEqual(len(output["hookSpecificOutput"]["permissionDecisionReason"]), adapter.REASON_LIMIT)


class InvalidInputTests(unittest.TestCase):
    def assert_denied(self, raw, host="CODEX", event="PreToolUse"):
        engine = Mock(side_effect=AssertionError("Must not call engine"))
        output, _ = dispatch(raw, host, event, engine=engine)
        fields = output["hookSpecificOutput"] if host == "CODEX" else output
        self.assertEqual(fields["permissionDecision"], "deny")
        engine.assert_not_called()

    def test_duplicate_keys_cannot_hide_a_memory_call(self):
        self.assert_denied(b'{"tool_name":"get_memory","tool_name":"Bash"}')

    def test_duplicate_keys_in_copilot_argument_string_are_rejected(self):
        self.assert_denied(payload("COPILOT", "preToolUse", toolArgs='{"memory_id":"a","memory_id":"b"}'), "COPILOT", "preToolUse")

    def test_oversized_invalid_or_nonobject_input_cannot_allow_unknown_call(self):
        for raw in [b"x" * (adapter.INPUT_LIMIT + 1), b"{", b"[]", b'{}{}', b'"text"', b'\xff']:
            with self.subTest(size=len(raw)):
                self.assert_denied(raw)

    def test_nonfinite_numbers_are_rejected_including_exponent_overflow(self):
        for token in ["NaN", "Infinity", "-Infinity", "1e999"]:
            raw = json.dumps(payload(event="PreToolUse")).replace('"m-1"', token).encode()
            self.assert_denied(raw)

    def test_mismatched_event_and_invalid_argument_shapes_fail_closed_for_memory(self):
        self.assert_denied(payload(event="PreToolUse", hook_event_name="PostToolUse"))
        self.assert_denied(payload(event="PreToolUse", tool_input=[]))
        self.assert_denied(payload(event="PreToolUse", session_id=None))

    def test_engine_failure_denies_memory_but_does_not_approve_or_deny_other_tools(self):
        engine = Mock(side_effect=RuntimeError("DO_NOT_LEAK_SECRET"))
        output, _ = dispatch(payload(event="PreToolUse"), event="PreToolUse", engine=engine)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertNotIn("DO_NOT_LEAK_SECRET", json.dumps(output))
        output, _ = dispatch(payload(event="PreToolUse", tool_name="Bash"), event="PreToolUse", engine=engine)
        self.assertNotIn("permissionDecision", output.get("hookSpecificOutput", {}))

    def test_invalid_engine_contract_cannot_allow_memory(self):
        output, _ = dispatch(payload(event="PreToolUse"), event="PreToolUse", engine=lambda _event: {"action": "BOGUS"})
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_noisy_engine_cannot_corrupt_stdout(self):
        def noisy(_event):
            print("SECRET_ENGINE_NOISE")
            return {"action": "NOTICE", "context": "safe"}
        import contextlib
        import io
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            output, _ = dispatch(payload(), engine=noisy)
        self.assertEqual(capture.getvalue(), "")
        self.assertEqual(output["hookSpecificOutput"]["additionalContext"], "safe")


class LauncherTests(unittest.TestCase):
    def test_bundled_manifests_use_only_supported_host_events(self):
        codex = json.loads((ROOT / "skills/bago5-ganchos-sesion/references/codex-hooks.json").read_text())
        copilot = json.loads((ROOT / "skills/bago5-ganchos-sesion/references/copilot-hooks.json").read_text())
        self.assertEqual(set(codex["hooks"]), set(adapter.EVENTS["CODEX"]))
        self.assertEqual(set(copilot["hooks"]), set(adapter.EVENTS["COPILOT"]))
        self.assertEqual(copilot["version"], 1)
        for name, groups in codex["hooks"].items():
            handler = groups[0]["hooks"][0]
            self.assertIn("commandWindows", handler)
            self.assertNotIn("$env:", handler["commandWindows"])
            if name in {"SessionEnd", "Interrupt"}:
                self.assertLessEqual(handler["timeout"], 3)
            if name in {"PreCompact", "PostCompact", "Stop", "SessionEnd", "Interrupt"}:
                self.assertNotIn("additionalContextLimit", handler)

    def test_actual_posix_launchers_work_from_unrelated_cwd_and_quoted_plugin_path(self):
        with tempfile.TemporaryDirectory(prefix="bago5 hooks ' ; $(data) ") as temp:
            root = Path(temp)
            scripts = root / "skills/bago5-ganchos-sesion/scripts"
            scripts.mkdir(parents=True)
            shutil.copyfile(ADAPTER, scripts / "native_hooks.py")
            (scripts / "session_engine.py").write_text("def run_native(event):\n    print('NOISY_ENGINE_SECRET')\n    return {'action':'NOTICE','context':event['host']+'|'+event['event']}\n")
            hook_dir = root / "com.github.copilot/hooks"
            hook_dir.mkdir(parents=True)
            workspace = root / "different workspace"
            workspace.mkdir()
            for host, path, native in [("CODEX", ROOT / "skills/bago5-ganchos-sesion/references/codex-hooks.json", "SessionStart"), ("COPILOT", ROOT / "skills/bago5-ganchos-sesion/references/copilot-hooks.json", "sessionStart")]:
                manifest = json.loads(path.read_text())
                handler = manifest["hooks"][native][0]
                if host == "CODEX":
                    handler = handler["hooks"][0]
                command = handler["command"] if host == "CODEX" else handler["bash"]
                env = dict(os.environ, PLUGIN_ROOT=str(root), COPILOT_HOOK_DIR=str(hook_dir))
                completed = subprocess.run(["bash", "-c", command], input=json.dumps(payload(host, native, cwd=str(workspace))), text=True, capture_output=True, cwd=workspace, env=env, timeout=10, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertNotIn("NOISY_ENGINE_SECRET", completed.stdout)
                self.assertEqual(completed.stderr, "")
                output = json.loads(completed.stdout)
                context = output["hookSpecificOutput"]["additionalContext"] if host == "CODEX" else output["additionalContext"]
                self.assertEqual(context, host + "|SESSION_START")
                self.assertFalse(list(root.rglob("*.pyc")))
                # Execute the Python bootstrap extracted from the Windows
                # variant, without claiming to test a Windows shell or host.
                windows = handler["commandWindows"] if host == "CODEX" else handler["powershell"]
                args = shlex.split(windows)
                bootstrap = args[args.index("-c") + 1]
                tail = args[args.index("-c") + 2:]
                completed = subprocess.run([sys.executable, "-B", "-I", "-c", bootstrap, *tail], input=json.dumps(payload(host, native, cwd=str(workspace))), text=True, capture_output=True, cwd=workspace, env=env, timeout=10, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertEqual(json.loads(completed.stdout), output)


if __name__ == "__main__":
    unittest.main()
