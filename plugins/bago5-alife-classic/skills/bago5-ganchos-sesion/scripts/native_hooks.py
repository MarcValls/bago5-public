#!/usr/bin/env python3
"""Translate documented Codex/Copilot hooks to the shared BAGO5 engine.

This adapter neither reads transcripts nor calls memory services. Host event
names arrive as launcher arguments, not as executable instructions from stdin.
Only this file and its trusted sibling engine are loaded by the launchers.
"""
from __future__ import annotations

import contextlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Callable


INPUT_LIMIT = 1024 * 1024
CONTEXT_LIMIT = 6500
REASON_LIMIT = 1000
EVENTS = {
    "CODEX": {
        "SessionStart": "SESSION_START",
        "UserPromptSubmit": "USER_PROMPT",
        "PreToolUse": "BEFORE_TOOL",
        "PostToolUse": "AFTER_TOOL",
        "PreCompact": "BEFORE_COMPACT",
        "PostCompact": "AFTER_COMPACT",
        "Stop": "BEFORE_TURN_CLOSE",
        "Interrupt": "INTERRUPT",
        "SessionEnd": "SESSION_END",
    },
    "COPILOT": {
        "sessionStart": "SESSION_START",
        "preToolUse": "BEFORE_TOOL",
        "postToolUse": "AFTER_TOOL",
        "agentStop": "BEFORE_TURN_CLOSE",
        "preCompact": "BEFORE_COMPACT",
        "sessionEnd": "SESSION_END",
    },
}
COPILOT_ALIASES = {
    "sessionStart": "SessionStart", "preToolUse": "PreToolUse",
    "postToolUse": "PostToolUse", "agentStop": "Stop",
    "preCompact": "PreCompact", "sessionEnd": "SessionEnd",
}
ACTIONS = {"ALLOW", "DENY", "CONTINUE", "CLOSE", "HANDOFF", "BLOCKED", "STOP", "NOTICE"}
MEMORY_SUFFIXES = ("search_memories", "get_memory", "save_memory")
Engine = Callable[[dict], dict]


class ContractError(ValueError):
    """Only fixed codes may cross the adapter's error boundary."""


def _pairs(items):
    value = {}
    for key, item in items:
        if key in value:
            raise ContractError("DUPLICATE_JSON_KEY")
        value[key] = item
    return value


def _constant(_value):
    raise ContractError("NONFINITE_JSON_NUMBER")


def _float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ContractError("NONFINITE_JSON_NUMBER")
    return number


def _json(blob: str | bytes):
    try:
        text = blob.decode("utf-8-sig") if isinstance(blob, bytes) else blob
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=_constant, parse_float=_float)
    except ContractError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        raise ContractError("INVALID_JSON") from None


def _string(value, limit: int, *, required=False) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ContractError("INVALID_FIELD")
    try:
        value.encode("utf-8")
    except UnicodeError:
        raise ContractError("INVALID_FIELD") from None
    return value


def normalize(payload: dict, host: str, native_event: str) -> dict:
    """Project a native payload; deliberately omit transcripts and chat text."""
    event = EVENTS.get(host, {}).get(native_event)
    if event is None:
        raise ContractError("UNSUPPORTED_HOST_EVENT")
    if not isinstance(payload, dict):
        raise ContractError("EVENT_NOT_OBJECT")
    stated = payload.get("hook_event_name")
    accepted = {native_event, COPILOT_ALIASES.get(native_event)}
    if host == "CODEX" and stated != native_event:
        raise ContractError("EVENT_NAME_MISMATCH")
    if host == "COPILOT" and stated is not None and stated not in accepted:
        raise ContractError("EVENT_NAME_MISMATCH")

    session = payload.get("session_id") if host == "CODEX" else payload.get("sessionId", payload.get("session_id"))
    result = {
        "host": host,
        "event": event,
        "host_session_id": _string(session, 1024, required=True),
        "cwd": _string(payload.get("cwd"), 32768, required=True),
        "source": _string(payload.get("source", payload.get("trigger", "")), 128),
        "tool_name": "",
        "arguments": {},
        "call_id": "",
        "response": None,
        "stop_hook_active": False,
        "prompt": "",
    }
    if event in {"BEFORE_TOOL", "AFTER_TOOL"}:
        tool = payload.get("tool_name") if host == "CODEX" else payload.get("toolName", payload.get("tool_name"))
        result["tool_name"] = _string(tool, 1024, required=True)
        arguments = payload.get("tool_input", {}) if host == "CODEX" else payload.get("toolArgs", payload.get("tool_input", {}))
        if isinstance(arguments, str):
            arguments = _json(arguments)
        if not isinstance(arguments, dict):
            raise ContractError("ARGUMENTS_NOT_OBJECT")
        result["arguments"] = arguments
        # Copilot's documented native payload has no required call identifier.
        if host == "CODEX":
            result["call_id"] = _string(payload.get("tool_use_id", ""), 1024)
        if event == "AFTER_TOOL":
            result["response"] = payload.get("tool_response") if host == "CODEX" else payload.get("toolResult", payload.get("tool_result"))
    if event == "BEFORE_TURN_CLOSE":
        active = payload.get("stop_hook_active", False)
        if type(active) is not bool:
            raise ContractError("INVALID_STOP_FLAG")
        result["stop_hook_active"] = active
    if event == "USER_PROMPT":
        # Only the engine may interpret an explicit STOP. Other prompts, tool
        # results and assistant messages cannot masquerade as user authority.
        result["prompt"] = _string(payload.get("prompt", ""), INPUT_LIMIT)
    return result


def _load_engine() -> Engine:
    trusted = str(Path(__file__).resolve().parent)
    if trusted not in sys.path:
        sys.path.insert(0, trusted)
    from session_engine import run_native
    return run_native


def _decision(value: dict) -> dict:
    if not isinstance(value, dict) or value.get("action") not in ACTIONS:
        raise ContractError("INVALID_ENGINE_RESULT")
    reason = _string(value.get("reason", ""), INPUT_LIMIT)
    context = _string(value.get("context", ""), INPUT_LIMIT)
    result = {"action": value["action"], "reason": reason[:REASON_LIMIT], "context": context[:CONTEXT_LIMIT]}
    if "review_before_close" in value:
        if value["action"] != "BLOCKED" or type(value["review_before_close"]) is not bool:
            raise ContractError("INVALID_ENGINE_RESULT")
        result["review_before_close"] = value["review_before_close"]
    return result


def render(event: dict, decision: dict) -> tuple[dict, str]:
    """Return valid host JSON and an optional bounded stderr-only notice.

    ALLOW means this plugin declines to deny; it never grants a host approval.
    Post-tool output is preserved. In Codex even continue:false at PostToolUse
    replaces feedback and does not guarantee that the model stops processing.
    """
    host, kind = event["host"], event["event"]
    action = decision["action"]
    reason = decision["reason"] or "BAGO5: revisar el estado de sesión antes de continuar."
    message = decision["context"] or (decision["reason"] if action not in {"ALLOW", "CLOSE"} else "")
    deny = action in {"DENY", "BLOCKED", "HANDOFF", "STOP"}

    if kind == "BEFORE_TOOL":
        if deny:
            fields = {"permissionDecision": "deny", "permissionDecisionReason": reason}
            if host == "CODEX":
                fields["hookEventName"] = "PreToolUse"
                return {"hookSpecificOutput": fields}, ""
            return fields, ""
        if host == "CODEX" and message:
            return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": message}}, ""
        # Copilot preToolUse has no documented additionalContext output.
        return {}, ("BAGO5: aviso del hook; revisar $bago5-ganchos-sesion." if message else "")

    if kind == "BEFORE_TURN_CLOSE":
        if action == "STOP":
            if host == "CODEX":
                return {"continue": False, "stopReason": reason}, ""
            # Copilot's Stop is end_turn; allow closure, never force another turn.
            return {"decision": "allow"}, ""
        review = action == "BLOCKED" and decision.get("review_before_close") is True
        if (action == "CONTINUE" or review) and not event["stop_hook_active"]:
            return {"decision": "block", "reason": message or reason}, ""
        if host == "CODEX":
            return ({"systemMessage": message} if message else {}), ""
        return {"decision": "allow"}, ("BAGO5: turno cerrado sin forzar otra continuación." if message else "")

    if host == "COPILOT":
        if kind in {"SESSION_START", "AFTER_TOOL"}:
            return ({"additionalContext": message} if message else {}), ""
        # These events are notifications; stdout cannot inject model context.
        return {}, ("BAGO5: evento registrado; el host no admite contexto en este evento." if message else "")

    output = {}
    if kind in {"SESSION_START", "AFTER_TOOL", "USER_PROMPT"} and message:
        native = {"SESSION_START": "SessionStart", "AFTER_TOOL": "PostToolUse", "USER_PROMPT": "UserPromptSubmit"}[kind]
        output["hookSpecificOutput"] = {"hookEventName": native, "additionalContext": message}
    elif message:
        output["systemMessage"] = message
    if action == "STOP" and kind in {"SESSION_START", "USER_PROMPT", "BEFORE_COMPACT", "AFTER_COMPACT"}:
        output.update({"continue": False, "stopReason": reason})
    return output, ""


def _error_event(host: str, native_event: str, payload) -> dict:
    kind = EVENTS.get(host, {}).get(native_event, "INVALID")
    tool = None
    if isinstance(payload, dict):
        tool = payload.get("tool_name") if host == "CODEX" else payload.get("toolName", payload.get("tool_name"))
    return {"host": host, "event": kind, "tool_name": tool, "stop_hook_active": True}


def dispatch(raw: bytes, host: str, native_event: str, engine: Engine | None = None) -> tuple[dict, str]:
    payload = None
    try:
        if host not in EVENTS or native_event not in EVENTS[host]:
            raise ContractError("UNSUPPORTED_HOST_EVENT")
        if len(raw) > INPUT_LIMIT:
            raise ContractError("INPUT_TOO_LARGE")
        payload = _json(raw)
        event = normalize(payload, host, native_event)
        # A stray engine print must not leak arguments or corrupt host JSON.
        with contextlib.redirect_stdout(io.StringIO()):
            decision = _decision((engine or _load_engine())(event))
        return render(event, decision)
    except (Exception, SystemExit) as exc:
        code = str(exc) if isinstance(exc, ContractError) else "ENGINE_UNAVAILABLE"
        # ContractError messages originate only from fixed codes in this module.
        safe_codes = {"DUPLICATE_JSON_KEY", "NONFINITE_JSON_NUMBER", "INVALID_JSON", "INVALID_FIELD", "UNSUPPORTED_HOST_EVENT", "EVENT_NOT_OBJECT", "EVENT_NAME_MISMATCH", "ARGUMENTS_NOT_OBJECT", "INVALID_STOP_FLAG", "INVALID_ENGINE_RESULT", "INPUT_TOO_LARGE"}
        if code not in safe_codes:
            code = "ENGINE_UNAVAILABLE"
        event = _error_event(host, native_event, payload)
        tool = event["tool_name"]
        # A malformed/oversized payload cannot prove it is a non-memory tool.
        memory_or_unknown = not isinstance(tool, str) or not tool or tool.casefold().endswith(MEMORY_SUFFIXES)
        action = "DENY" if event["event"] == "BEFORE_TOOL" and memory_or_unknown else "NOTICE"
        reason = "BAGO5: comprobación del hook no disponible (" + code + ")."
        if host not in EVENTS or event["event"] == "INVALID":
            return {}, reason
        return render(event, {"action": action, "reason": reason, "context": ""})


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 4 or argv[0] != "--host" or argv[2] != "--event":
        output, notice = {}, "BAGO5: argumentos del adaptador no válidos."
    else:
        output, notice = dispatch(sys.stdin.buffer.read(INPUT_LIMIT + 1), argv[1], argv[3])
    if notice:
        sys.stderr.write(notice[:REASON_LIMIT] + "\n")
    sys.stdout.write(json.dumps(output, ensure_ascii=True, separators=(",", ":"), allow_nan=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
