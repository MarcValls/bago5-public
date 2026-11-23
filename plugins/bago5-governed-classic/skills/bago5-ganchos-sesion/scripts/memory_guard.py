"""Pure admission and read-back verification for a host-selected memory binding.

No I/O, authentication or permissions are created here. Identity and authorization
are attestations supplied by the host. Returned state must be persisted BEFORE an
ALLOWed save is dispatched; an IN_FLIGHT save recovered after a crash is uncertain.

State v1: context/binding are the exact selected attestations; destination/tools
freeze the selected store and tool scope independently of refreshed attestations.
searches counts
successful scoped searches; known_ids is their union plus accepted saves; reads
contains validated records; calls correlates admitted calls with their arguments;
pending is the current checkpoint; events retains checkpoint digests/statuses.
Checkpoint status: PREPARED, IN_FLIGHT, EXECUTED, UNCERTAIN, FAILED, CONFLICT,
VERIFIED. EXECUTED means NO_COMPROBADO until a separate get verifies every field.
VERIFIED attests observed state, never exactly-once delivery or authorship.
now accepts an aware datetime or ISO-8601 timestamp; None means current UTC.
"""

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re


SCHEMA = "bago5.memory-guard.v1"
CONTEXT = {"project_id", "mission_id", "goal_id", "goal_revision",
           "candidate_id", "scope_id", "session_id"}
FIELDS = {"title", "content", "project_id", "kind", "status", "source",
          "tags", "pinned", "archived"}
OPTIONAL = {"decision_closed", "id", "expected_version"}
OPERATIONS = {"search_memories", "get_memory", "save_memory"}
MODES = {"READ", "READ_WRITE"}
STOP = {"STOP", "STOPPED", "REVOKED"}
DESTINATION = {"store_id", "owner_id", "connector_id", "project_id"}


class MemoryGuardError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _require(condition, code):
    if not condition:
        raise MemoryGuardError(code)


def _text(value, limit=1000, empty=False):
    return isinstance(value, str) and len(value) <= limit and (empty or bool(value.strip()))


def _integer(value):
    return type(value) is int and value >= 1


def _time(value):
    if value is None:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
        _require(isinstance(parsed, datetime) and parsed.tzinfo is not None
                 and parsed.utcoffset() is not None, "invalid_time")
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError) as exc:
        raise MemoryGuardError("invalid_time") from exc


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _copy(value):
    try:
        json.dumps(value, allow_nan=False)
        return deepcopy(value)
    except (TypeError, ValueError, RecursionError):
        return None


def _context(value):
    _require(isinstance(value, dict) and set(value) == CONTEXT, "invalid_context")
    _require(_integer(value["goal_revision"]), "invalid_goal_revision")
    _require(all(_text(value[k], 500) for k in CONTEXT - {"goal_revision"}), "invalid_context")


def _binding(binding, context, now):
    _context(context)
    _require(isinstance(binding, dict) and set(binding) == {
        "store_id", "owner_id", "connector_id", "project_id", "mode", "tools",
        "identity", "authorization"}, "invalid_binding")
    _require(all(_text(binding[k], 500) for k in ("store_id", "owner_id", "connector_id", "project_id")),
             "invalid_destination")
    _require(binding["mode"] in MODES, "invalid_mode")
    names = binding["tools"]
    _require(isinstance(names, dict) and OPERATIONS <= set(names)
             and set(names) <= OPERATIONS | {"list_projects", "identity"}, "invalid_tools")
    _require(all(_text(v, 500) for v in names.values())
             and len(set(names.values())) == len(names), "invalid_tools")
    identity = binding["identity"]
    _require(isinstance(identity, dict) and set(identity) == {
        "verified", "store_id", "owner_id", "connector_id", "source_ref"}, "invalid_identity")
    _require(identity["verified"] is True and _text(identity["source_ref"]), "unverified_identity")
    _require(all(identity[k] == binding[k] for k in ("store_id", "owner_id", "connector_id")),
             "identity_mismatch")
    auth = binding["authorization"]
    _require(isinstance(auth, dict) and set(auth) == {
        "binding", "destination", "read", "write", "source_ref", "expires_at"}, "invalid_authorization")
    _context(auth["binding"])
    _require(auth["binding"] == context, "authorization_context_mismatch")
    _require(isinstance(auth["destination"], dict) and set(auth["destination"]) == DESTINATION
             and all(auth["destination"][k] == binding[k] for k in DESTINATION),
             "authorization_destination_mismatch")
    _require(type(auth["read"]) is bool and type(auth["write"]) is bool
             and _text(auth["source_ref"]), "invalid_authorization")
    _require(isinstance(auth["expires_at"], str)
             and _time(auth["expires_at"]) > _time(now), "authorization_expired")


def select_memory(binding, context, now=None):
    """Select exactly one explicitly attested destination; raise on invalid config."""
    try:
        _binding(binding, context, now)
    except MemoryGuardError:
        raise
    except (TypeError, KeyError, ValueError) as exc:
        raise MemoryGuardError("invalid_binding") from exc
    return {"schema": SCHEMA, "context": deepcopy(context), "binding": deepcopy(binding),
            "destination": {k: binding[k] for k in DESTINATION}, "tools": deepcopy(binding["tools"]),
            "searches": 0, "known_ids": [], "reads": {}, "calls": {}, "pending": None,
            "events": {}, "revoked": False}


def revoke_memory(memory, reason):
    state = _copy(memory) if isinstance(memory, dict) else {}
    state = state or {}
    state.update(revoked=True, revoke_reason=reason[:1000] if isinstance(reason, str) else "revoked")
    return state


def _result(state, decision, reason, status=None):
    result = {"decision": decision, "state": state, "reason": reason}
    if status is not None:
        result["status"] = status
    return result


def _check(state, context, now, write=False):
    _require(isinstance(state, dict) and state.get("schema") == SCHEMA, "memory_not_selected")
    _require(not state.get("revoked"), "memory_revoked")
    _binding(state.get("binding"), context, now)
    _require(state.get("context") == context, "context_changed")
    _require(state.get("destination") == {k: state["binding"][k] for k in DESTINATION}
             and state.get("tools") == state["binding"]["tools"], "selection_scope_changed")
    _require(isinstance(state.get("known_ids"), list) and isinstance(state.get("reads"), dict)
             and isinstance(state.get("calls"), dict) and isinstance(state.get("events"), dict)
             and type(state.get("searches")) is int, "invalid_state")
    auth = state["binding"]["authorization"]
    _require(auth["read"], "read_not_authorized")
    if write:
        _require(state["binding"]["mode"] == "READ_WRITE" and auth["write"], "write_not_authorized")


def _operation(state, name):
    binding = state.get("binding", {}) if isinstance(state, dict) else {}
    names = binding.get("tools", {}) if isinstance(binding, dict) else {}
    if isinstance(names, dict):
        for operation, configured in names.items():
            if isinstance(name, str) and configured == name:
                return operation, True
    if isinstance(name, str):
        match = re.search(r"(?:^|[_:./])((?:search_memories|get_memory|save_memory))$", name)
        if match:
            return match.group(1), False
    return None, False


def _payload(payload, project_id):
    _require(isinstance(payload, dict) and FIELDS <= set(payload)
             and set(payload) <= FIELDS | OPTIONAL, "invalid_payload_fields")
    _require(payload["project_id"] == project_id, "project_mismatch")
    for name, maximum, empty in (("title", 180, False), ("content", 30000, False), ("source", 1000, True)):
        _require(_text(payload[name], maximum, empty), "invalid_" + name)
    _require(payload["kind"] in {"context", "idea", "learning", "decision"}, "invalid_kind")
    _require(payload["status"] in {"active", "pending", "superseded"}, "invalid_status")
    _require(isinstance(payload["tags"], list) and len(payload["tags"]) <= 12
             and all(_text(tag, 40) for tag in payload["tags"]), "invalid_tags")
    _require(all(type(payload[k]) is bool for k in ("pinned", "archived")), "invalid_flags")
    _require("decision_closed" not in payload or type(payload["decision_closed"]) is bool,
             "invalid_decision_closed")
    _require(("id" in payload) == ("expected_version" in payload), "incomplete_edit")
    if "id" in payload:
        _require(_text(payload["id"], 500) and _integer(payload["expected_version"]), "invalid_edit")
        _require("decision_closed" in payload, "edit_requires_explicit_decision_closed")


def _record(record, state):
    _require(isinstance(record, dict), "missing_record")
    fields = {k: deepcopy(v) for k, v in record.items() if k in FIELDS | {"decision_closed"}}
    _payload(fields, state["binding"]["project_id"])
    _require(_text(record.get("id"), 500) and _integer(record.get("version")), "invalid_record_identity")
    _require("owner_id" not in record or record["owner_id"] == state["binding"]["owner_id"],
             "record_owner_mismatch")
    fields.update(id=record["id"], version=record["version"])
    fields.setdefault("decision_closed", False)
    return fields


def merge_checkpoint(existing, changes):
    """Preserve every unchanged writable field in an explicitly requested edit."""
    _require(isinstance(existing, dict) and isinstance(changes, dict), "invalid_edit")
    _require(set(changes) <= FIELDS | {"decision_closed"}, "invalid_change_fields")
    payload = {k: deepcopy(v) for k, v in existing.items() if k in FIELDS | {"decision_closed"}}
    payload.update(deepcopy(changes))
    payload.setdefault("decision_closed", existing.get("decision_closed", False))
    payload.update(id=existing.get("id"), expected_version=existing.get("version"))
    _payload(payload, existing.get("project_id"))
    return payload


def prepare_checkpoint(memory, context, event_id, payload, source_ref, now=None):
    state = _copy(memory)
    try:
        _check(state, context, now, write=True)
        _require(_text(event_id, 180) and _text(source_ref), "invalid_checkpoint_provenance")
        _payload(payload, state["binding"]["project_id"])
        digest = _digest(payload)
        previous = state["events"].get(event_id)
        if previous:
            if previous["digest"] != digest:
                return _result(state, "CONFLICT", "event_payload_conflict", "CONFLICT")
            if previous["status"] == "VERIFIED":
                return _result(state, "SKIP", "event_already_verified", "VERIFIED")
            if previous["status"] == "PREPARED":
                return _result(state, "SKIP", "event_already_prepared", "PREPARED")
            return _result(state, "DENY", "event_requires_reconciliation", previous["status"])
        pending = state["pending"]
        if pending and pending["status"] == "CONFLICT":
            _require(pending.get("id") is not None and payload.get("id") == pending["id"]
                     and pending.get("reconciled_version") == payload.get("expected_version")
                     and _integer(pending.get("reconciled_version")), "conflict_requires_fresh_get_and_new_intent")
        else:
            _require(not pending or pending["status"] in {"VERIFIED", "FAILED"}, "checkpoint_unresolved")
        expected = {k: deepcopy(v) for k, v in payload.items() if k in FIELDS | {"decision_closed"}}
        version = 1
        if "id" in payload:
            record = state["reads"].get(payload["id"])
            _require(record is not None, "edit_requires_get")
            _require(record["version"] == payload["expected_version"], "expected_version_conflict")
            expected.setdefault("decision_closed", record["decision_closed"])
            version = payload["expected_version"] + 1
        expected.setdefault("decision_closed", False)
        state["pending"] = {"event_id": event_id, "digest": digest, "payload": deepcopy(payload),
                            "expected": expected, "source_ref": source_ref, "status": "PREPARED",
                            "id": payload.get("id"), "version": version, "call_id": None,
                            "prior_ids": [], "reconciled_version": None}
        state["events"][event_id] = {"digest": digest, "status": "PREPARED"}
        return _result(state, "PREPARED", "checkpoint_prepared", "PREPARED")
    except (MemoryGuardError, TypeError, KeyError, ValueError, RecursionError) as exc:
        return _result(state, "DENY", getattr(exc, "code", "invalid_input"))


def _halted(state, control):
    return (isinstance(control, str) and control in STOP) or (isinstance(state, dict) and state.get("revoked") is True)


def _checkpoint_status(state, status):
    pending = state["pending"]
    pending["status"] = status
    if status == "CONFLICT":
        pending["reconciled_version"] = None
    state["events"][pending["event_id"]] = {"digest": pending["digest"], "status": status}


def before_tool(memory, context, tool_name, arguments, call_id, control="RUNNING", now=None):
    state = _copy(memory)
    if _halted(memory, control):
        return _result(state, "DENY", "control_stopped")
    try:
        operation, selected = _operation(state, tool_name)
        if operation is None:
            return _result(state, "UNRELATED", "unrelated_tool")
        _require(control == "RUNNING", "control_not_running")
        _require(selected, "memory_tool_not_bound")
        _check(state, context, now, write=operation == "save_memory")
        _require(isinstance(arguments, dict) and _copy(arguments) is not None, "invalid_arguments")
        _require(_text(call_id, 180) and call_id not in state["calls"], "duplicate_or_invalid_call")
        if operation == "search_memories":
            _require(arguments.get("project_id") == state["binding"]["project_id"], "search_requires_project")
        elif operation == "get_memory":
            _require(set(arguments) == {"id"} and _text(arguments["id"], 500), "invalid_get")
            _require(arguments["id"] in state["known_ids"], "get_requires_scoped_id")
        elif operation == "save_memory":
            pending = state["pending"]
            _require(isinstance(pending, dict) and pending["status"] == "PREPARED", "save_requires_prepared_checkpoint")
            _require(arguments == pending["payload"] and _digest(arguments) == pending["digest"], "save_payload_mismatch")
            _payload(arguments, state["binding"]["project_id"])
            _require(state["searches"] > 0, "save_requires_search")
            if "id" in arguments:
                record = state["reads"].get(arguments["id"])
                _require(record is not None and record["version"] == arguments["expected_version"], "edit_requires_current_get")
            pending["call_id"] = call_id
            pending["prior_ids"] = list(state["known_ids"])
            _checkpoint_status(state, "IN_FLIGHT")
        state["calls"][call_id] = {"operation": operation, "tool": tool_name,
                                  "arguments": deepcopy(arguments), "status": "IN_FLIGHT"}
        return _result(state, "ALLOW", "persist_before_dispatch", "IN_FLIGHT")
    except (MemoryGuardError, TypeError, KeyError, ValueError, RecursionError) as exc:
        return _result(state, "DENY", getattr(exc, "code", "invalid_input"))


def _unpack(response):
    """Inspect transport envelopes, never parse a memory record's content string."""
    documents, errors = [], []

    def walk(node, depth=0):
        if depth > 20:
            raise MemoryGuardError("response_too_deep")
        if isinstance(node, str):
            try:
                walk(json.loads(node), depth + 1)
            except (json.JSONDecodeError, ValueError):
                pass
        elif isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, dict):
            if node.get("isError") is True:
                errors.append(node)
            # Copilot postToolUse wraps the actual tool/MCP result in a JSON
            # string. These are transport fields, not memory record content.
            transport_keys = {"resultType", "result_type", "textResultForLlm", "text_result_for_llm"}
            if transport_keys.intersection(node):
                result_types = [node[k] for k in ("resultType", "result_type") if k in node]
                texts = [node[k] for k in ("textResultForLlm", "text_result_for_llm") if k in node]
                if (not result_types or any(value != "success" for value in result_types)
                        or not texts or len(texts) == 2 and texts[0] != texts[1]):
                    errors.append({"transport_result_error": True})
                for raw in texts:
                    try:
                        if not isinstance(raw, str):
                            raise ValueError("not a JSON result string")
                        parsed = json.loads(raw)
                    except (TypeError, ValueError, RecursionError):
                        errors.append({"transport_result_error": True})
                    else:
                        walk(parsed, depth + 1)
            # Structured output has priority over redundant textual envelopes.
            if "structuredContent" in node:
                walk(node["structuredContent"], depth + 1)
            if "memory" in node or "memories" in node:
                documents.append(node)
            for key, value in node.items():
                if key in {"structuredContent", "memory", "memories", "history"} | transport_keys:
                    continue
                if key == "content" and isinstance(value, list):
                    for block in value:
                        if isinstance(block, dict) and block.get("type") == "text":
                            walk(block.get("text"), depth + 1)
                        elif isinstance(block, dict) and block.get("isError") is True:
                            errors.append(block)
                elif isinstance(value, (dict, list)):
                    walk(value, depth + 1)
    walk(response)
    return documents, errors


def _verify_read(state, record):
    pending = state["pending"]
    if pending and pending["status"] == "CONFLICT" and record["id"] == pending["id"]:
        # Preserve the conflict; a subsequent explicit event may use this version.
        pending["reconciled_version"] = record["version"]
        return "READ", "conflict_current_version_read"
    if not pending or pending["status"] not in {"EXECUTED", "UNCERTAIN", "IN_FLIGHT"}:
        return "READ", "record_read"
    target = pending["id"]
    if target is not None and record["id"] != target:
        return "READ", "other_record_read"
    matches = record["version"] == pending["version"] and all(
        record.get(key) == value for key, value in pending["expected"].items())
    if target is None:
        # An uncertain create can be reconciled only to a scoped, newly observed
        # id with all planned fields and version 1. This proves state, not authorship.
        if record["id"] in pending["prior_ids"] or not matches:
            return "UNCERTAIN", "create_not_reconciled"
        pending["id"] = record["id"]
    if not matches:
        if pending["status"] in {"UNCERTAIN", "IN_FLIGHT"}:
            # A read of an old/different revision does not prove a timed-out write
            # cannot still commit. It must never unlock a blind second save.
            _checkpoint_status(state, "UNCERTAIN")
            return "UNCERTAIN", "write_not_reconciled"
        _checkpoint_status(state, "CONFLICT")
        return "CONFLICT", "readback_mismatch"
    _checkpoint_status(state, "VERIFIED")
    return "VERIFIED", "separate_readback_verified"


def after_tool(memory, context, tool_name, arguments, call_id, response, control="RUNNING", now=None):
    state = _copy(memory)
    if _halted(memory, control):
        return _result(state, "DENY", "control_stopped")
    try:
        operation, selected = _operation(state, tool_name)
        if operation is None:
            return _result(state, "UNRELATED", "unrelated_tool")
        _require(control == "RUNNING", "control_not_running")
        _require(selected, "memory_tool_not_bound")
        _check(state, context, now, write=operation == "save_memory")
        _require(_text(call_id, 180), "invalid_call_id")
        call = state["calls"].get(call_id)
        _require(isinstance(call, dict) and call["tool"] == tool_name
                 and _digest(call["arguments"]) == _digest(arguments), "unadmitted_or_mismatched_result")
        _require(call["status"] == "IN_FLIGHT", "result_already_processed")
        if operation == "save_memory":
            _require(state["pending"] is not None
                     and state["pending"]["call_id"] == call_id
                     and state["pending"]["status"] == "IN_FLIGHT", "checkpoint_call_mismatch")
        documents, errors = _unpack(response)
        if errors:
            error_text = json.dumps(errors, ensure_ascii=False).lower()
            status = "CONFLICT" if any(x in error_text for x in ("conflict", "409", "otra sesión", "another session")) else "FAILED"
            transport_error = any(error.get("transport_result_error") is True for error in errors)
            if operation == "save_memory" and transport_error:
                # A failed/malformed transport result does not prove no commit.
                status = "UNCERTAIN"
            call["status"] = status
            if operation == "save_memory":
                _checkpoint_status(state, status)
            return _result(state, "DENY", "transport_result_unusable" if transport_error else "mcp_is_error", status)
        if operation == "search_memories":
            document = next((d for d in documents if isinstance(d.get("memories"), list)), None)
            _require(document is not None, "missing_search_result")
            for record in document["memories"]:
                if (isinstance(record, dict) and record.get("project_id") == state["binding"]["project_id"]
                        and _text(record.get("id"), 500)
                        and ("owner_id" not in record or record["owner_id"] == state["binding"]["owner_id"])):
                    if record["id"] not in state["known_ids"]:
                        state["known_ids"].append(record["id"])
            state["searches"] += 1
            status, reason = "EXECUTED", "scoped_search_recorded"
        elif operation in {"get_memory", "save_memory"}:
            document = next((d for d in documents if isinstance(d.get("memory"), dict)), None)
            if operation == "save_memory":
                try:
                    record = _record(document["memory"] if document else None, state)
                except (MemoryGuardError, TypeError, KeyError, ValueError):
                    call["status"] = "UNCERTAIN"
                    _checkpoint_status(state, "UNCERTAIN")
                    return _result(state, "DENY", "save_result_unknown_reconcile_by_read", "UNCERTAIN")
                pending = state["pending"]
                _require(pending["call_id"] == call_id, "checkpoint_call_mismatch")
                if ((pending["id"] is not None and record["id"] != pending["id"])
                        or record["version"] != pending["version"]):
                    call["status"] = "CONFLICT"
                    _checkpoint_status(state, "CONFLICT")
                    return _result(state, "DENY", "save_identity_version_conflict", "CONFLICT")
                pending["id"] = record["id"]
                if record["id"] not in state["known_ids"]:
                    state["known_ids"].append(record["id"])
                _checkpoint_status(state, "EXECUTED")
                status, reason = "EXECUTED", "NO_COMPROBADO_requires_separate_get"
            else:
                record = _record(document["memory"] if document else None, state)
                _require(record["id"] == arguments["id"], "get_identity_mismatch")
                previous = state["reads"].get(record["id"])
                _require(previous is None or record["version"] >= previous["version"], "stale_get_result")
                state["reads"][record["id"]] = record
                status, reason = _verify_read(state, record)
        else:
            status, reason = "EXECUTED", "auxiliary_read_recorded"
        call["status"] = status
        return _result(state, "DENY" if status == "CONFLICT" else "ALLOW", reason, status)
    except (MemoryGuardError, TypeError, KeyError, ValueError, RecursionError) as exc:
        return _result(state, "DENY", getattr(exc, "code", "invalid_input"))
