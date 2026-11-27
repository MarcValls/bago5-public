#!/usr/bin/env python3
"""Conversation provenance. No network, credentials or transcript collection."""
from __future__ import annotations
import argparse
import copy
import json
import sys
import uuid
from datetime import datetime, timezone

SCHEMA = "bago-conversation-trace/1"
MARKER = "BAGO5-CONV-001: "


class TraceError(ValueError):
    pass


def _text(value, field, limit=500):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise TraceError(f"Invalid {field}")
    if any(ord(ch) < 32 for ch in value):
        raise TraceError(f"Control characters in {field}")
    return value.strip()


def _native(value, evidence):
    if value is None:
        return None
    return {"id": _text(value, "native ID"),
            "evidence": _text(evidence, "native ID evidence", 2000)}


def new_conversation(title, host="unknown", native_id=None, evidence=None):
    native = _native(native_id, evidence)
    return {"schema": SCHEMA, "conversation_id": native["id"] if native else "C-" + str(uuid.uuid4()),
            "title": _text(title, "title", 250), "host": _text(host, "host", 100),
            "id_kind": "native" if native else "generated_label", "native": native,
            "conversation_availability": "unknown", "messages": [],
            "created_at": datetime.now(timezone.utc).isoformat()}


def validate(state):
    if not isinstance(state, dict) or state.get("schema") != SCHEMA:
        raise TraceError("Unsupported conversation state")
    for field, limit in (("conversation_id", 500), ("title", 250), ("host", 100)):
        _text(state.get(field), field, limit)
    if state.get("id_kind") not in ("native", "generated_label"):
        raise TraceError("Unknown ID origin")
    native = state.get("native")
    if native is not None:
        _native(native.get("id"), native.get("evidence"))
    if state["id_kind"] == "native" and (not native or native["id"] != state["conversation_id"]):
        raise TraceError("Native identity requires matching sourced evidence")
    if state.get("conversation_availability") not in ("unknown", "available", "unavailable"):
        raise TraceError("Unknown availability")
    if not isinstance(state.get("messages"), list):
        raise TraceError("Messages must be a list")
    seen = set()
    for item in state["messages"]:
        if item.get("role") not in ("user", "assistant") or item.get("conversation_id") != state["conversation_id"]:
            raise TraceError("Message belongs to another conversation or role")
        identifier = _text(item.get("id"), "message ID", 1200)
        if identifier in seen:
            raise TraceError("Duplicate message ID")
        seen.add(identifier)
    return state


def bind_native(state, native_id, evidence):
    result = copy.deepcopy(validate(state))
    _text(native_id, "native conversation ID")
    native = _native(native_id, evidence)
    if result["native"] and result["native"]["id"] != native["id"]:
        raise TraceError("Conflicting native conversation identity")
    # Keep the original primary label: old memories must continue to resolve it.
    result["native"] = native
    return result


def add_message(state, role, native_id=None, evidence=None, event_key=None):
    result = copy.deepcopy(validate(state))
    if role not in ("user", "assistant"):
        raise TraceError("Unsupported message role")
    native = _native(native_id, evidence)
    if event_key is not None:
        event_key = _text(event_key, "event key", 500)
        for item in result["messages"]:
            if item.get("event_key") == event_key:
                if item["role"] != role or item.get("native") != native:
                    raise TraceError("Event key reused for a different message")
                return result, item
    for item in result["messages"]:
        if native and item.get("native") and item["native"]["id"] == native["id"]:
            if item["role"] != role:
                raise TraceError("Native message ID reused across roles")
            return result, item
    prefix = "U" if role == "user" else "A"
    identifier = native["id"] if native else f"{result['conversation_id']}/{prefix}-{uuid.uuid4()}"
    item = {"id": identifier, "conversation_id": result["conversation_id"], "role": role,
            "id_kind": "native" if native else "generated_label", "native": native,
            "event_key": event_key}
    result["messages"].append(item)
    return result, item


def reference(state, relation="origin", user_id=None, assistant_id=None):
    validate(state)
    if relation not in ("origin", "update", "related"):
        raise TraceError("Unknown provenance relation")
    for role, identifier in (("user", user_id), ("assistant", assistant_id)):
        if identifier is not None and not any(m["role"] == role and m["id"] == identifier for m in state["messages"]):
            raise TraceError("Unknown or mismatched message reference")
    return {"conversation_id": state["conversation_id"], "title": state["title"],
            "id_kind": state["id_kind"], "host": state["host"],
            "native_conversation_id": state["native"]["id"] if state["native"] else None,
            "user_message_id": user_id, "assistant_response_id": assistant_id,
            "relation": relation, "conversation_availability": state["conversation_availability"]}


def read_references(memory):
    refs = []
    for field in ("source", "content"):
        for line in memory.get(field, "").splitlines():
            if line.startswith(MARKER):
                try:
                    ref = json.loads(line[len(MARKER):])
                except json.JSONDecodeError as exc:
                    raise TraceError("Malformed stored conversation reference") from exc
                if not isinstance(ref, dict) or not ref.get("conversation_id") or not ref.get("title"):
                    raise TraceError("Incomplete stored conversation reference")
                refs.append(ref)
    return refs


def attach(memory, ref, source_limit=1000, content_limit=100000):
    """Return a delta-ready record without altering old provenance or unknown fields."""
    result = copy.deepcopy(memory)
    if not isinstance(ref, dict) or not ref.get("conversation_id") or not ref.get("title"):
        raise TraceError("Conversation ID and title are mandatory")
    existing = read_references(result)
    if ref in existing:
        return result
    if result.get("id") and ref.get("relation") == "origin" and not existing:
        raise TraceError("An existing record cannot be assigned a new historical origin")
    line = MARKER + json.dumps(ref, ensure_ascii=False, separators=(",", ":"))
    for field, limit in (("source", source_limit), ("content", content_limit)):
        previous = result.get(field, "")
        if not isinstance(previous, str):
            raise TraceError("Unsupported memory field")
        # Appending prose to a typed JSON document would invalidate its contract.
        if field == "content":
            try:
                json.loads(previous)
                continue
            except (json.JSONDecodeError, TypeError):
                pass
        value = previous + ("\n" if previous else "") + line
        if len(value) <= limit:
            result[field] = value
            return result
    raise TraceError("REFERENCE_CAPACITY_EXCEEDED: preserve existing fields; choose a supported storage shape")


def verify_saved(memory, ref):
    return ref in read_references(memory)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("init", "message", "bind-native", "attach"))
    p.add_argument("--title"); p.add_argument("--host", default="unknown")
    p.add_argument("--role", choices=("user", "assistant"))
    p.add_argument("--native-id"); p.add_argument("--evidence"); p.add_argument("--event-key")
    args = p.parse_args()
    try:
        if args.action == "init":
            out = new_conversation(args.title, args.host, args.native_id, args.evidence)
        else:
            data = json.load(sys.stdin)
            if args.action == "message":
                state, event = add_message(data, args.role, args.native_id, args.evidence, args.event_key)
                out = {"state": state, "event": event}
            elif args.action == "bind-native":
                out = bind_native(data, args.native_id, args.evidence)
            else:
                ref = reference(data["state"], data.get("relation", "origin"), data.get("user_id"), data.get("assistant_id"))
                out = {"memory": attach(data["memory"], ref), "reference": ref}
        print(json.dumps(out, ensure_ascii=False))
    except (TraceError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
