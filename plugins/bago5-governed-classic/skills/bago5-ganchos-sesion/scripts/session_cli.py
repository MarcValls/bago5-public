#!/usr/bin/env python3
"""Apply one scoped lifecycle command supplied as bounded JSON on stdin.

Initializing local state is explicit. No remote operation is executed. Set the
host-provided PLUGIN_DATA or pass an explicitly authorized --data-dir. Hook and
CLI must use the same host/session/data root. Do not put credentials in JSON.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


engine = load("bago5_session_engine", HERE / "session_engine.py")
store = load("bago5_session_store", HERE / "session_store.py")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=sorted(engine.HOSTS))
    parser.add_argument("--session-id")
    parser.add_argument("--data-dir", default=os.environ.get("PLUGIN_DATA"))
    args = parser.parse_args(argv)
    try:
        command = store.parse(sys.stdin.buffer.read(store.LIMIT + 1))
        if not isinstance(command, dict):
            raise engine.HookError("COMMAND_OBJECT_REQUIRED")
        host = args.host or command.get("host")
        session = args.session_id or command.get("host_session_id")
        create = command.get("op") == "INIT"
        if create:
            # Validate consent, binding and receipt before creating any file.
            engine.apply_command(None, command)
        with store.transaction(args.data_dir, host, session, create=create) as tx:
            event = command.get("event", {}) if command.get("op") == "EVENT" else {}
            if tx.state and command.get("op") == "EVENT":
                engine.validate_event_scope(tx.state, event)
            if tx.state and event.get("event") in {"BEFORE_TOOL", "BEFORE_TURN_CLOSE"} and (event.get("event") == "BEFORE_TURN_CLOSE" or engine.is_memory_tool(tx.state, event.get("tool_name"))):
                blocked = engine._runtime_check(tx.state, turn_close=event.get("event") == "BEFORE_TURN_CLOSE")
                if blocked:
                    if blocked["decision"] == "STOP":
                        stopped = engine.apply_command(tx.state, {"op": "STOP", "source_ref": "observed:selected-taskstore-stop"})
                        tx.save(stopped["state"])
                    raise engine.HookError("NATIVE_CONTROLLER_BLOCKED:" + ";".join(blocked.get("issues", [])))
            result = engine.apply_command(tx.state, command)
            if command.get("op") == "REASSESS_CORRECTION":
                # A pure recovery decision never overrides the selected native
                # controller. Preserve a failure of conditions as data; block a
                # native STOP, stale digest, closed mission or other native gate.
                blocked = engine._runtime_check(result["state"], turn_close=True)
                if blocked:
                    if blocked["decision"] == "STOP":
                        stopped = engine.apply_command(tx.state, {
                            "op": "STOP", "source_ref": "observed:selected-taskstore-stop"})
                        tx.save(stopped["state"])
                    raise engine.HookError("NATIVE_CONTROLLER_REJECTED_RECOVERY:" +
                                           ";".join(blocked.get("issues", [])))
            if command.get("op") == "RESUME":
                blocked = engine._runtime_check(result["state"], resume=True)
                if blocked:
                    raise engine.HookError("NATIVE_CONTROLLER_REJECTED_RESUME:" + ";".join(blocked.get("issues", [])))
            if result["state"] != tx.state:
                tx.save(result["state"])
            output = result["result"]
        print(json.dumps(output, ensure_ascii=False, sort_keys=True, allow_nan=False))
        return 2 if output["action"] in {"DENY", "BLOCKED", "STOP"} else 0
    except (ValueError, TypeError, KeyError, OSError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"action": "BLOCKED", "reason": str(exc)[:1000]}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
