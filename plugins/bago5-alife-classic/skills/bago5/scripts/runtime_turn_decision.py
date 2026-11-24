#!/usr/bin/env python3
"""Read-only bridge from the pinned Suite to the shared turn decision policy.

It observes an explicitly selected existing TaskStore. It neither runs Suite
commands nor imports its code, creates a controller, authenticates a user, grants
permission, consumes receipts, or closes/resumes a mission. Observations expire
at the next state change and never replace the controller's effect-time gates.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import stat
import sys
from typing import Any


SCHEMA = "bago5.runtime-turn-decision.v1"
OBSERVATION_SCHEMA = "bago5.runtime-observation.v1"
PINNED_IDENTITY_SHA256 = "ffd27584a68fc7fe5d3454f50c41d7a5fccbda0afe845dfcd1866856efd03506"
MAX_BYTES = 25_000_000
MAX_TOTAL_BYTES = 100_000_000
HASH = re.compile(r"[0-9a-f]{64}\Z")


class ObservationError(ValueError):
    """An absent or mismatched observation must not enable continuation."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(data: bytes | str) -> Any:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ObservationError("duplicate_json_key")
            result[key] = value
        return result

    def invalid(_value):
        raise ObservationError("nonfinite_json_number")

    try:
        return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)
    except RecursionError as error:
        raise ObservationError("json_nesting_exceeds_parser_limit") from error


def _reject_links(path: Path) -> None:
    path = path.absolute()
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ObservationError("symlink_or_reparse_point")


def _read(path: Path, limit: int = MAX_BYTES) -> bytes:
    _reject_links(path)
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ObservationError("file_type_or_size")
    with path.open("rb") as stream:
        content = stream.read(limit + 1)
    after = path.stat()
    attrs = ("st_size", "st_mtime_ns", "st_ino", "st_dev")
    if (len(content) != before.st_size or len(content) > limit
            or any(getattr(before, name) != getattr(after, name) for name in attrs)):
        raise ObservationError("file_changed_during_observation")
    _reject_links(path)
    return content


def _safe_member(root: Path, name: str) -> Path:
    if (not isinstance(name, str) or not name or "\\" in name
            or PurePosixPath(name).is_absolute()
            or any(part in ("", ".", "..") for part in name.split("/"))
            or any(ord(char) < 32 for char in name)
            or any(char in name for char in '<>:"|?*')):
        raise ObservationError("unsafe_relative_path")
    path = root.joinpath(*name.split("/"))
    _reject_links(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ObservationError("path_outside_selected_root")
    return path


def expected_suite_root() -> Path:
    return Path(__file__).resolve().parents[3] / "optional-runtime/bago-operating-suite"


def inspect_suite(suite_root: str | Path) -> dict:
    """Verify the packaged payload without executing unverified Python files."""
    root = Path(suite_root).expanduser().absolute()
    _reject_links(root)
    if root.resolve(strict=True) != expected_suite_root().resolve(strict=True):
        raise ObservationError("suite_root_is_not_this_plugins_pinned_payload")
    root = root.resolve()
    identity_bytes = _read(root / "PACKAGE_IDENTITY.json")
    if _sha(identity_bytes) != PINNED_IDENTITY_SHA256:
        raise ObservationError("suite_identity_pin_mismatch")
    metadata = _json(identity_bytes)
    declared = metadata["files"]
    actual, total = [], 0
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).parts):
        _reject_links(path)
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc" or path.is_dir():
            continue
        if relative.as_posix() == "PACKAGE_IDENTITY.json":
            continue
        content = _read(path)
        total += len(content)
        if total > MAX_TOTAL_BYTES or len(actual) >= 10_000:
            raise ObservationError("suite_inventory_limit")
        actual.append({"path": relative.as_posix(), "bytes": len(content), "sha256": _sha(content)})
    if actual != declared or _read(root / "PACKAGE_IDENTITY.json") != identity_bytes:
        raise ObservationError("suite_payload_changed")
    identity_sha = _sha(identity_bytes)
    identity = {"schema": "bago.suite.candidate-identity.v1",
                **{key: metadata[key] for key in
                   ("package_id", "display_name", "version", "candidate", "release_id")},
                "payload_sha256": _sha(_canonical({"identity_sha256": identity_sha, "files": actual})),
                "payload_files": len(actual) + 1, "identity_sha256": identity_sha,
                "scope": "exact installed skill bytes; unsigned integrity, not publisher authentication"}
    return {"status": "VERIFIED", "root": str(root), "identity": identity,
            "scope": "packaged-byte integrity only; not host authorization or functioning"}


def _no_sidecars(database: Path) -> None:
    # No immutable SQLite read may silently ignore an active journal or WAL.
    # Refuse instead of checkpointing it or creating shared-memory files.
    for suffix in ("-journal", "-wal", "-shm"):
        sidecar = Path(str(database) + suffix)
        _reject_links(sidecar)
        if sidecar.exists():
            raise ObservationError("sqlite_sidecar_present_observation_unavailable")


def inspect_taskstore(state_dir: str | Path, suite: dict, workspace_root: str | Path,
                      expected_binding: dict | None = None) -> dict:
    """Read a bounded stable copy of an existing ledger into in-memory SQLite."""
    state = Path(state_dir).expanduser().absolute()
    _reject_links(state)
    state = state.resolve(strict=True)
    suite_root = Path(suite["root"])
    if (not state.is_dir() or state.is_relative_to(suite_root)
            or suite_root.is_relative_to(state)):
        raise ObservationError("invalid_existing_state_directory")
    database = state / "control.sqlite3"
    _no_sidecars(database)
    raw = _read(database)
    if not raw.startswith(b"SQLite format 3\x00"):
        raise ObservationError("not_a_sqlite_ledger")
    # deserialize() never opens or writes the source database or its sidecars.
    # Concurrent changes are rejected by the byte comparison at the end.
    connection = sqlite3.connect(":memory:")
    try:
        if not callable(getattr(connection, "deserialize", None)):
            raise ObservationError("sqlite_deserialize_unavailable_python_3_11_plus_required")
        connection.deserialize(raw)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT key,value FROM meta LIMIT 101").fetchall()
        if len(rows) > 100:
            raise ObservationError("ledger_metadata_limit")
        meta = {row["key"]: _json(row["value"]) for row in rows}
        if len(meta) != len(rows) or meta.get("schema") != "bago.suite.task.control.v1":
            raise ObservationError("unrecognized_taskstore")
        if (not isinstance(meta.get("plan"), dict) or not isinstance(meta.get("candidate"), dict)
                or not isinstance(meta.get("snapshot"), dict)
                or not isinstance(meta.get("workspace"), str)
                or not 0 < len(meta["workspace"]) < 10_000):
            raise ObservationError("invalid_taskstore_metadata_types")
        plan = meta["plan"]
        if (plan.get("schema") != "bago.suite.task.plan.v1"
                or plan.get("operation") not in {"AUDIT", "VERIFY", "REPAIR", "PROMOTE"}
                or not all(isinstance(plan.get(key), str) and bool(plan[key]) for key in ("mission_id", "candidate_id"))
                or not isinstance(plan.get("scope"), list)
                or not 1 <= len(plan["scope"]) <= 10_000
                or not all(isinstance(item, str) for item in plan["scope"])
                or not isinstance(plan.get("checks"), list)
                or not 1 <= len(plan["checks"]) <= 1_000
                or not all(isinstance(item, dict) and isinstance(item.get("id"), str)
                           for item in plan["checks"])
                or type(meta["closed"]) is not bool
                or meta["control"] not in {"ACTIVE", "STOPPED"}
                or type(meta["round"]) is not int
                or type(plan["max_rounds"]) is not int
                or not 0 <= meta["round"] <= plan["max_rounds"] <= 100):
            raise ObservationError("invalid_taskstore_metadata")
        if meta["candidate"]["id"] != plan["candidate_id"]:
            raise ObservationError("ledger_candidate_binding_mismatch")
        checks = [dict(row) for row in connection.execute(
            "SELECT id,consumed,outcome FROM checks ORDER BY id LIMIT 1001")]
        required_checks = {item["id"]: item for item in plan["checks"]}
        if (len(checks) > 1_000 or len(required_checks) != len(plan["checks"])
                or {row["id"] for row in checks} != set(required_checks)
                or any(type(item.get("mandatory")) is not bool for item in plan["checks"])):
            raise ObservationError("ledger_check_inventory_mismatch")
        for row in checks:
            row["mandatory"] = required_checks[row["id"]]["mandatory"]
            row["evidence_validation"] = "NOT_RUN"
        running = connection.execute("SELECT count(*) FROM runs WHERE state='RUNNING'").fetchone()[0]
        last_event = connection.execute("SELECT seq,action FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        collaboration = {"enabled": "collaboration" in meta, "admission": "NATIVE_CONTROLLER_ONLY"}
        if collaboration["enabled"]:
            collaboration["work"] = [dict(row) for row in connection.execute(
                "SELECT check_id,state FROM relay_work ORDER BY check_id LIMIT 1001")]
            if len(collaboration["work"]) > 1_000:
                raise ObservationError("relay_inventory_limit")
    finally:
        connection.close()

    # STOP is reported independently of candidate integrity; it never resumes.
    errors = []
    if meta["candidate"].get("suite") != suite["identity"]:
        errors.append("suite_identity_differs_from_ledger")
    native_controls = {"round_open": meta["round"] > 0,
                       "another_round_available": meta["round"] < plan["max_rounds"],
                       "running_children_recorded": running,
                       "relay_enabled": collaboration["enabled"],
                       "relay_pending_checks": [item["check_id"] for item in collaboration.get("work", [])
                                                if item["state"] != "DONE"]}
    if meta["control"] == "STOPPED":
        return {"kind": "SUITE_TASKSTORE", "state_dir": str(state),
                "database_sha256": _sha(raw), "mission_id": plan["mission_id"],
                "candidate_id": plan["candidate_id"], "operation": plan["operation"],
                "control": "STOPPED", "task_status": "CLOSED" if meta["closed"] else "OPEN",
                "round": meta["round"], "max_rounds": plan["max_rounds"],
                "checks_recorded": checks, "running_children_recorded": running,
                "collaboration": collaboration,
                "last_event": dict(last_event) if last_event else None,
                "candidate_scope": "NOT_RUN_STOP", "current_gate_errors": errors,
                "native_effect_admission": "DENIED_STOP", "native_controls_observed": native_controls,
                "binding_fields_observed": ["mission_id", "candidate_id"],
                "closure_verification": "NOT_RUN",
                "limits": "STOP observed in the read snapshot; no further candidate reads or admission."}
    if expected_binding is not None and (
            expected_binding.get("mission_id") != plan["mission_id"]
            or expected_binding.get("candidate_id") != plan["candidate_id"]):
        raise ObservationError("receipt_controller_binding_mismatch")
    workspace = Path(meta["workspace"])
    selected_workspace = Path(workspace_root).expanduser().absolute()
    _reject_links(selected_workspace)
    selected_workspace = selected_workspace.resolve(strict=True)
    _reject_links(workspace)
    if (not workspace.is_absolute() or workspace.resolve() != selected_workspace
            or not selected_workspace.is_dir()):
        raise ObservationError("ledger_workspace_differs_from_selected_root")
    if not workspace.is_dir():
        raise ObservationError("candidate_workspace_unavailable")
    declared_snapshot = meta["snapshot"]
    scope = plan["scope"]
    if (len(scope) != len(set(scope)) or set(scope) != set(declared_snapshot)
            or meta["candidate"].get("scope_sha256") != _sha(_canonical(declared_snapshot))):
        raise ObservationError("candidate_scope_inventory_mismatch")
    observed_snapshot, total = {}, 0
    for name in sorted(scope):
        content = _read(_safe_member(workspace, name))
        total += len(content)
        if total > MAX_TOTAL_BYTES:
            raise ObservationError("candidate_snapshot_limit")
        observed_snapshot[name] = {"sha256": _sha(content), "size": len(content)}
    if observed_snapshot != declared_snapshot:
        errors.append("candidate_files_differ_from_frozen_scope")
    _no_sidecars(database)
    if _read(database) != raw:
        raise ObservationError("ledger_changed_during_observation")
    return {"kind": "SUITE_TASKSTORE", "state_dir": str(state),
            "database_sha256": _sha(raw), "mission_id": plan["mission_id"],
            "candidate_id": plan["candidate_id"], "operation": plan["operation"],
            "control": meta["control"], "task_status": "CLOSED" if meta["closed"] else "OPEN",
            "round": meta["round"], "max_rounds": plan["max_rounds"],
            "checks_recorded": checks, "running_children_recorded": running,
            "collaboration": collaboration,
            "last_event": dict(last_event) if last_event else None,
            "candidate_scope": "MATCH" if observed_snapshot == declared_snapshot else "MISMATCH",
            "scope_sha256_observed": _sha(_canonical(observed_snapshot)),
            "binding_fields_observed": ["mission_id", "candidate_id"],
            "native_effect_admission": "NOT_EVALUATED_USE_EXISTING_CONTROLLER",
            "native_controls_observed": native_controls,
            "current_gate_errors": errors, "closure_verification": "NOT_RUN",
            "limits": "Checks and CLOSED are recorded facts; receipts and host permissions are not verified here."}


def observe_runtime(suite_root: str | Path, state_dir: str | Path | None = None,
                    workspace_root: str | Path | None = None,
                    expected_binding: dict | None = None) -> dict:
    if state_dir is not None and workspace_root is None:
        raise ObservationError("explicit_workspace_root_required_for_selected_taskstore")
    if state_dir is None and workspace_root is not None:
        raise ObservationError("workspace_root_without_selected_taskstore")
    suite = inspect_suite(suite_root)
    controller = inspect_taskstore(state_dir, suite, workspace_root, expected_binding) if state_dir is not None else None
    return {"schema": OBSERVATION_SCHEMA,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "suite": suite, "controller": controller,
            "controller_selection": "EXPLICIT_EXISTING" if controller else "NONE_OBSERVED",
            "writes_performed": False, "authority": "OBSERVATION_ONLY",
            "validity": "snapshot only; recheck native controls before each effect"}


def _controller_gate(observation: dict, binding: dict,
                     expected_state_sha256: str | None) -> str:
    """Share negative native checks; CLEAR never admits an operation or close."""
    controller = observation["controller"]
    if controller is None:
        if expected_state_sha256 is not None:
            raise ObservationError("state_digest_without_selected_controller")
        return "CLEAR"
    if controller["control"] == "STOPPED":
        return "STOP"
    if (binding["mission_id"] != controller["mission_id"]
            or binding["candidate_id"] != controller["candidate_id"]):
        raise ObservationError("receipt_controller_binding_mismatch")
    if (not isinstance(expected_state_sha256, str)
            or not HASH.fullmatch(expected_state_sha256)):
        raise ObservationError("expected_state_digest_required_use_observe_first")
    if expected_state_sha256 != controller["database_sha256"]:
        raise ObservationError("controller_changed_since_receipt")
    if controller["current_gate_errors"]:
        raise ObservationError(";".join(controller["current_gate_errors"]))
    return "CLEAR"


def observe_turn_gate(binding: dict, control: dict, suite_root: str | Path,
                      state_dir: str | Path | None = None,
                      expected_state_sha256: str | None = None,
                      workspace_root: str | Path | None = None) -> dict:
    """Observe native constraints before reviewing obsolete turn metadata.

    No acceptance evidence/actions are consumed and assess() is never invoked.
    A fresh receipt must still pass evaluate(), including OPEN/CLOSED scope
    checks, before a continuation or closure decision. This is not a lease.
    """
    from turn_decision import _binding, _object, _enum, _text, _bool

    result = {"schema": SCHEMA, "decision": "BLOCKED", "gate_only": True,
              "runtime_observation": None, "issues": [], "writes_performed": False,
              "execution": "NOT_RUN", "permissions_granted": False,
              "decision_scope": "Negative controller observations for metadata review only; CLEAR is not execution or closure permission."}
    if isinstance(control, dict) and control.get("state") in ("STOP", "REVOKED"):
        result.update(decision="STOP", issues=["runtime_read_not_run_under_stop"])
        return result
    try:
        _binding(binding, "binding")
        _object(control, {"state", "source_ref", "current", "binding"}, "control")
        _enum(control["state"], {"RUNNING", "STOP", "REVOKED", "UNKNOWN"}, "control.state")
        _text(control["source_ref"], "control.source_ref")
        _bool(control["current"], "control.current")
        _binding(control["binding"], "control.binding", binding)
        if control["state"] != "RUNNING" or not control["current"]:
            raise ObservationError("current_control_required_before_runtime_observation")
        observation = observe_runtime(suite_root, state_dir, workspace_root, binding)
        result["runtime_observation"] = observation
        result["decision"] = _controller_gate(observation, binding, expected_state_sha256)
        if result["decision"] == "STOP":
            result["issues"].append("selected_taskstore_is_stopped")
        return result
    except (ObservationError, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, sqlite3.Error) as error:
        result["issues"].append(str(error))
        return result


def evaluate(receipt: dict, suite_root: str | Path, state_dir: str | Path | None = None,
             expected_state_sha256: str | None = None,
             workspace_root: str | Path | None = None, closure_scope: str = "MISSION",
             closure_scope_ref: str | None = None, *, corrections: list | None = None,
             now=None) -> dict:
    from turn_decision import assess

    policy = assess(receipt)
    result = {"schema": SCHEMA, "decision": policy["decision"], "policy_result": policy,
              "runtime_observation": None, "issues": [], "writes_performed": False,
              "execution": "NOT_RUN", "permissions_granted": False,
              "closure_scope": closure_scope if isinstance(closure_scope, str) and closure_scope in {"MISSION", "SUBTASK"} else "INVALID",
              "closure_scope_ref": None,
              "native_mission_status": None,
              "decision_scope": "Host turn only. Every material controller action still requires native admission; "
                                "CONTINUE is not a lease, an open round, or permission to bypass a running child."}
    # Respect a STOP already provided by the host without new runtime reads.
    if policy["decision"] == "STOP":
        result["issues"].append("runtime_read_not_run_under_stop")
        return result
    if policy.get("validation") == "INVALID":
        result["issues"].append("runtime_read_not_run_for_invalid_receipt")
        return result
    try:
        if corrections is not None:
            from behavior_recovery import guard_receipt
            receipt = guard_receipt(receipt, corrections, now=now)
            policy = assess(receipt)
            result["policy_result"] = policy
            result["decision"] = policy["decision"]
        if not isinstance(closure_scope, str) or closure_scope not in {"MISSION", "SUBTASK"}:
            raise ObservationError("invalid_closure_scope")
        if closure_scope_ref is not None:
            if (not isinstance(closure_scope_ref, str) or not 0 < len(closure_scope_ref) <= 10_000
                    or not closure_scope_ref.strip()):
                raise ObservationError("invalid_closure_scope_reference")
            try:
                closure_scope_ref.encode("utf-8")
            except UnicodeError as error:
                raise ObservationError("invalid_utf8_closure_scope_reference") from error
            result["closure_scope_ref"] = closure_scope_ref
        elif closure_scope == "SUBTASK":
            raise ObservationError("subtask_closure_requires_original_scope_reference")
        observation = observe_runtime(suite_root, state_dir, workspace_root, receipt.get("binding"))
        result["runtime_observation"] = observation
        controller = observation["controller"]
        if controller is None:
            _controller_gate(observation, receipt["binding"], expected_state_sha256)
            return result
        result["native_mission_status"] = controller["task_status"]
        if _controller_gate(observation, receipt["binding"], expected_state_sha256) == "STOP":
            # Negative control only: this never changes STOP to RUNNING.
            stopped = copy.deepcopy(receipt)
            stopped["control"] = {"state": "STOP", "binding": receipt["binding"], "current": True,
                                  "source_ref": "taskstore:" + controller["database_sha256"]}
            result["policy_result"] = assess(stopped)
            result["decision"] = "STOP"
            result["issues"].append("selected_taskstore_is_stopped")
            return result
        if controller["task_status"] == "CLOSED" and policy["decision"] in {"CONTINUE", "HANDOFF"}:
            raise ObservationError("native_task_closed_no_implicit_continuation")
        if controller["task_status"] == "OPEN" and policy["decision"] == "CLOSE":
            if closure_scope == "MISSION":
                raise ObservationError("native_task_closure_still_pending")
            result["issues"].append("subtask_result_only_native_mission_remains_open")
        # Native checks never become policy acceptance evidence. A core CLOSE
        # still depends entirely on separately supplied criterion evidence.
        return result
    except (ObservationError, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, sqlite3.Error) as error:
        result["decision"] = "BLOCKED"
        result["issues"].append(str(error))
        return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite-root", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path)
    parser.add_argument("--workspace-root", type=Path,
                        help="Explicitly authorized candidate root; required with --state-dir")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--receipt", type=Path)
    mode.add_argument("--observe", action="store_true")
    parser.add_argument("--expected-state-sha256")
    parser.add_argument("--closure-scope", choices=["MISSION", "SUBTASK"], default="MISSION")
    parser.add_argument("--closure-scope-ref", help="Original user task/scope reference; required for SUBTASK")
    parser.add_argument("--corrections", type=Path,
                        help="Existing correction records as a JSON list; data only, no resolution or dispatch")
    args = parser.parse_args(argv)
    try:
        if args.observe:
            if args.expected_state_sha256 or args.corrections:
                raise ObservationError("observe_does_not_consume_receipts")
            result = observe_runtime(args.suite_root, args.state_dir, args.workspace_root)
        else:
            receipt = _json(_read(args.receipt))
            # Known STOP does not authorize reading another state file.
            stopped = isinstance(receipt, dict) and receipt.get("control", {}).get("state") in {"STOP", "REVOKED"}
            corrections = None if stopped or not args.corrections else _json(_read(args.corrections))
            result = evaluate(receipt, args.suite_root,
                              args.state_dir, args.expected_state_sha256, args.workspace_root,
                              args.closure_scope, args.closure_scope_ref, corrections=corrections)
    except (ObservationError, OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError, sqlite3.Error) as error:
        result = {"schema": SCHEMA, "decision": "BLOCKED", "issues": [str(error)],
                  "writes_performed": False, "execution": "NOT_RUN", "permissions_granted": False}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    return 3 if result.get("decision") in {"BLOCKED", "STOP"} else 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
