"""Passive, bounded task control for the Suite orchestrator (stdlib only).

This is a local evidence ledger and supervised subprocess runner, not a scheduler,
host permission issuer, OS sandbox or authenticated external-delegate protocol.
Optional cooperative relays use the SAME ledger through suite_relay.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import sqlite3
import stat
import subprocess
import time
import uuid

from suite_safety import collision_key, read_json, reject_links, safe_rel, strict_json, write_new_json

PLAN_SCHEMA = "bago.suite.task.plan.v1"
RECEIPT_SCHEMA = "bago.suite.task.receipt.v1"
RESULT_SCHEMA = "bago.suite.check-result.v1"
CONTROL_SCHEMA = "bago.suite.task.control.v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_OUTCOMES = {"PASS", "FAIL", "NOT_RUN", "INTERRUPTED", "ERROR", "INCONCLUSIVE"}


class ControlError(ValueError):
    pass


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _keys(value, required, optional=()):
    if not isinstance(value, dict) or set(value) != set(required) | (set(value) & set(optional)):
        raise ControlError("missing or unknown object fields")


def _id(value):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ControlError("invalid identifier")
    return value


def _time(value):
    if not isinstance(value, str):
        raise ControlError("timestamp must be an ISO timestamp with timezone")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ControlError("invalid timestamp") from exc
    if result.tzinfo is None:
        raise ControlError("timestamp requires timezone")
    return result


def validate_plan(value):
    _keys(value, {"schema", "mission_id", "candidate_id", "operation", "scope", "max_rounds", "checks"}, {"target"})
    if value["schema"] != PLAN_SCHEMA:
        raise ControlError("unsupported plan schema")
    _id(value["mission_id"]); _id(value["candidate_id"])
    if value["operation"] not in {"AUDIT", "VERIFY", "REPAIR", "PROMOTE"}:
        raise ControlError("invalid operation")
    if value["operation"] == "PROMOTE" and not value.get("target"):
        raise ControlError("PROMOTE requires an explicit target; no publication is performed")
    if "target" in value and (not isinstance(value["target"], str) or not value["target"].strip() or len(value["target"]) > 1000):
        raise ControlError("invalid target")
    if type(value["max_rounds"]) is not int or not 1 <= value["max_rounds"] <= 100:
        raise ControlError("max_rounds must be an integer from 1 to 100")
    if not isinstance(value["scope"], list) or not 1 <= len(value["scope"]) <= 10000:
        raise ControlError("scope must explicitly list 1..10000 candidate files")
    seen = set()
    for path in value["scope"]:
        safe_rel(path)
        key = collision_key(path)
        if key in seen:
            raise ControlError("duplicate or case-aliased scope path")
        seen.add(key)
    checks = value["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 1000:
        raise ControlError("checks must be a nonempty bounded list")
    ids = set()
    for check in checks:
        _keys(check, {"id", "kind", "mandatory", "depends_on", "artifacts"})
        _id(check["id"])
        if check["id"] in ids:
            raise ControlError("duplicate check")
        ids.add(check["id"])
        if check["kind"] not in {"execution", "artifact"} or type(check["mandatory"]) is not bool:
            raise ControlError("invalid check kind or mandatory flag")
        if not isinstance(check["depends_on"], list) or len(check["depends_on"]) != len(set(check["depends_on"])):
            raise ControlError("invalid dependencies")
        if not isinstance(check["artifacts"], list) or len(check["artifacts"]) > 100:
            raise ControlError("invalid artifact list")
        paths = set()
        for artifact in check["artifacts"]:
            _keys(artifact, {"path", "schema"})
            safe_rel(artifact["path"])
            key = collision_key(artifact["path"])
            if key in paths or key in seen:
                raise ControlError("artifact duplicates another path or overlaps candidate scope")
            paths.add(key)
            if artifact["schema"] not in {None, RESULT_SCHEMA}:
                raise ControlError("unsupported artifact schema; use null for byte-only evidence")
        if check["kind"] == "artifact" and not check["artifacts"]:
            raise ControlError("artifact check requires an artifact")
    if not any(c["mandatory"] for c in checks):
        raise ControlError("at least one mandatory check is required")
    graph = {c["id"]: c["depends_on"] for c in checks}
    remaining = {node: len(deps) for node, deps in graph.items()}
    children = {node: [] for node in ids}
    for node, deps in graph.items():
        for dep in deps:
            _id(dep)
            if dep not in ids:
                raise ControlError("unknown check dependency")
            children[dep].append(node)
    ready = [node for node in ids if remaining[node] == 0]
    depth = {node: 1 for node in ready}
    visited = 0
    while ready:
        node = ready.pop(); visited += 1
        if depth[node] > 64:
            raise ControlError("dependency depth exceeds bounded limit of 64")
        for child in children[node]:
            depth[child] = max(depth.get(child, 1), depth[node] + 1)
            remaining[child] -= 1
            if remaining[child] == 0:
                ready.append(child)
    if visited != len(ids):
        raise ControlError("cyclic check dependency")
    return value


def _bytes(path, limit=25_000_000):
    reject_links(path)
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ControlError("evidence must be a regular file")
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    final = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if len(data) > limit or identity(before) != identity(after) or identity(before) != identity(final):
        raise ControlError("file changed during read or exceeded the byte budget")
    reject_links(path)
    return data


def _inside(root, relative):
    safe_rel(relative)
    path = root.joinpath(*relative.split("/"))
    reject_links(path)
    if not path.resolve().is_relative_to(root.resolve()):
        raise ControlError("path leaves its declared root")
    return path


def _snapshot(root, scope):
    return {p: {"sha256": _hash(data), "size": len(data)}
            for p in sorted(scope) for data in [_bytes(_inside(root, p))]}


def _context_identity(context):
    if isinstance(context, dict):
        value = context.get("candidate_identity")
    else:
        value = getattr(context, "candidate_identity", None)
    value = value() if callable(value) else value
    if not isinstance(value, dict) or not value:
        raise ControlError("Suite candidate identity is required")
    # The orchestrator owns the Suite identity schema; preserve it exactly.
    return strict_json(_json(value))


def _terminate_owned(proc):
    """Request termination only for the child/session created by this invocation."""
    if proc.poll() is not None:
        return True
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
            proc.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return proc.poll() is not None
    return proc.poll() is not None


class TaskStore:
    def __init__(self, state_dir, identity, identity_provider=None):
        reject_links(Path(state_dir))
        self.root = Path(state_dir).resolve()
        self.identity = identity
        self.identity_provider = identity_provider
        self.db_path = self.root / "control.sqlite3"

    @contextmanager
    def db(self):
        reject_links(self.db_path)
        for suffix in ("-journal", "-wal", "-shm"):
            reject_links(Path(str(self.db_path) + suffix))
        if not self.db_path.is_file():
            raise ControlError("task does not exist; initialize it explicitly")
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA synchronous=FULL")
        try:
            yield conn
        finally:
            conn.close()

    def relay(self):
        from suite_relay import RelayController
        return RelayController(self)

    def initialize(self, workspace, plan):
        plan = validate_plan(plan)
        reject_links(Path(workspace))
        workspace = Path(workspace).resolve(strict=True)
        if not workspace.is_dir():
            raise ControlError("workspace must be a directory")
        if self.root.exists() or self.root.is_relative_to(workspace) or workspace.is_relative_to(self.root):
            raise ControlError("state directory must be new and separate from workspace")
        scoped = _snapshot(workspace, plan["scope"])
        self.root.mkdir(parents=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("PRAGMA synchronous=FULL")
            conn.executescript("""
                CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE checks (id TEXT PRIMARY KEY, receipt TEXT, receipt_hash TEXT,
                    consumed INTEGER NOT NULL DEFAULT 0, outcome TEXT NOT NULL DEFAULT 'NOT_RUN');
                CREATE TABLE runs (id TEXT PRIMARY KEY, check_id TEXT NOT NULL, round INTEGER NOT NULL,
                    command TEXT NOT NULL, cwd TEXT NOT NULL, pid INTEGER,
                    started TEXT NOT NULL, finished TEXT, returncode INTEGER,
                    state TEXT NOT NULL, interruption TEXT NOT NULL, receipt TEXT);
                CREATE TABLE assignments (id TEXT PRIMARY KEY, check_id TEXT NOT NULL, worker TEXT NOT NULL,
                    round INTEGER NOT NULL, state TEXT NOT NULL, interruption TEXT NOT NULL);
                CREATE TABLE events (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
                    action TEXT NOT NULL, detail TEXT NOT NULL);
            """)
            values = {"schema": CONTROL_SCHEMA, "plan": plan, "workspace": str(workspace),
                      "snapshot": scoped, "candidate": {"id": plan["candidate_id"],
                      "scope_sha256": _hash(_json(scoped).encode()), "suite": self.identity},
                      "control": "ACTIVE", "round": 0, "closed": False}
            conn.executemany("INSERT INTO meta VALUES (?,?)", [(k, _json(v)) for k, v in values.items()])
            conn.executemany("INSERT INTO checks(id) VALUES (?)", [(c["id"],) for c in plan["checks"]])
            self._event(conn, "INIT", {"mission_id": plan["mission_id"], "scope": plan["scope"]})
            conn.commit()
        finally:
            conn.close()
        return self.status()

    @staticmethod
    def _event(conn, action, detail):
        conn.execute("INSERT INTO events(at, action, detail) VALUES (?,?,?)", (_now(), action, _json(detail)))

    @staticmethod
    def _set(conn, key, value):
        conn.execute("UPDATE meta SET value=? WHERE key=?", (_json(value), key))

    def _meta(self, conn):
        meta = {row["key"]: strict_json(row["value"]) for row in conn.execute("SELECT * FROM meta")}
        if meta.get("schema") != CONTROL_SCHEMA:
            raise ControlError("unsupported task ledger")
        validate_plan(meta["plan"])
        return meta

    def _candidate(self, meta):
        current_identity = self.identity_provider() if self.identity_provider is not None else self.identity
        if meta["candidate"]["suite"] != current_identity:
            raise ControlError("Suite candidate identity changed")
        actual = _snapshot(Path(meta["workspace"]), meta["plan"]["scope"])
        if actual != meta["snapshot"]:
            raise ControlError("frozen candidate scope changed")

    def _admit(self, conn, *, round_required=True):
        meta = self._meta(conn)
        if meta["control"] != "ACTIVE":
            raise ControlError("STOP is persistent; explicit resume is required")
        if meta["closed"]:
            raise ControlError("task is closed; no implicit continuation")
        if round_required and meta["round"] < 1:
            raise ControlError("open an explicit bounded round first")
        self._candidate(meta)
        return meta

    def _check(self, meta, check_id):
        _id(check_id)
        for check in meta["plan"]["checks"]:
            if check["id"] == check_id:
                return check
        raise ControlError("check is outside frozen scope")

    def status(self):
        with self.db() as conn:
            meta = self._meta(conn)
            return {"schema": CONTROL_SCHEMA, "status": "PASS", "mission_id": meta["plan"]["mission_id"],
                    "operation": meta["plan"]["operation"], "control": meta["control"],
                    "task_status": "CLOSED" if meta["closed"] else "OPEN", "candidate": meta["candidate"],
                    "round": meta["round"], "max_rounds": meta["plan"]["max_rounds"],
                    "scope": meta["plan"]["scope"], "checks": [dict(r) for r in conn.execute("SELECT * FROM checks ORDER BY id")],
                    "runs": [dict(r) for r in conn.execute("SELECT * FROM runs ORDER BY started")],
                    "assignments": [dict(r) for r in conn.execute("SELECT * FROM assignments ORDER BY id")],
                    "host_interrupt": "NOT_RUN; only owned supervised child processes can be interrupted",
                    "collaboration": self.relay().summary(conn, meta)}

    def stop(self, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ControlError("STOP requires a reason")
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._meta(conn)
            self._set(conn, "control", "STOPPED")
            self.relay().on_stop(conn, meta)
            conn.execute("UPDATE runs SET interruption='REQUESTED' WHERE state='RUNNING'")
            conn.execute("UPDATE assignments SET state='INTERRUPT_REQUESTED', interruption='EXTERNAL_UNINTERRUPTIBLE' WHERE state='ASSIGNED'")
            self._event(conn, "STOP", {"reason": reason, "host_interrupt": "NOT_RUN"})
            conn.commit()
        result = self.status()
        result["interruption_requested"] = True
        return result

    def resume(self, reason):
        if not isinstance(reason, str) or not reason.strip():
            raise ControlError("resume requires an explicit reason")
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._meta(conn)
            self._candidate(meta)
            if meta["closed"]:
                raise ControlError("closed tasks cannot resume")
            if conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone():
                raise ControlError("owned child still running or unconfirmed; resume remains blocked")
            self._set(conn, "control", "ACTIVE")
            self._event(conn, "EXPLICIT_RESUME", {"reason": reason})
            conn.commit()
        return self.status()

    def open_round(self):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._admit(conn, round_required=False)
            self.relay().idle(conn, meta)
            if meta["round"] >= meta["plan"]["max_rounds"]:
                raise ControlError("frozen round budget exhausted")
            if conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone():
                raise ControlError("cannot open another round while a child runs")
            self._set(conn, "round", meta["round"] + 1)
            self._event(conn, "ROUND", {"round": meta["round"] + 1})
            conn.commit()
        return self.status()

    def assign(self, check_id, worker):
        _id(worker)
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._admit(conn)
            check = self._check(meta, check_id)
            self._dependencies(conn, meta, check)
            if self.relay().enabled(meta):
                raise ControlError("use task collaborate claim, not legacy assign, in collaborative missions")
            assignment = uuid.uuid4().hex
            conn.execute("INSERT INTO assignments VALUES (?,?,?,?,?,?)",
                         (assignment, check_id, worker, meta["round"], "ASSIGNED", "EXTERNAL_NOT_CONTROLLED"))
            self._event(conn, "ASSIGN", {"id": assignment, "check_id": check_id, "worker": worker, "spawned": False})
            conn.commit()
        return {"status": "PASS", "assignment_id": assignment, "spawned": False,
                "host_interrupt": "NOT_RUN", "interruptibility": "EXTERNAL_NOT_CONTROLLED"}

    def _dependencies(self, conn, meta, check, chain=(), cache=None):
        cache = {} if cache is None else cache
        result = []
        for dep in check["depends_on"]:
            if dep in chain:
                raise ControlError("cyclic receipt dependency")
            receipt, digest = self._validate_stored(conn, meta, dep, chain + (check["id"],), cache)
            row = conn.execute("SELECT consumed FROM checks WHERE id=?", (dep,)).fetchone()
            if not row["consumed"] or receipt["outcome"] != "PASS":
                raise ControlError("dependency is not consumed PASS evidence")
            result.append({"check_id": dep, "receipt_sha256": digest})
        return result

    def _artifact(self, meta, root_name, path, schema):
        root = self.root if root_name == "state" else Path(meta["workspace"])
        data = _bytes(_inside(root, path))
        if schema is not None:
            payload = strict_json(data)
            _keys(payload, {"schema", "status", "findings", "coverage"})
            if payload["schema"] != RESULT_SCHEMA or payload["status"] not in {"PASS", "FAIL"}:
                raise ControlError("invalid check-result schema/status")
            if payload["coverage"] not in {"COMPLETE", "PARTIAL"}:
                raise ControlError("invalid check-result coverage")
            if not isinstance(payload["findings"], list) or any(not isinstance(x, str) for x in payload["findings"]):
                raise ControlError("findings must be strings")
            if payload["status"] == "FAIL" and not payload["findings"]:
                raise ControlError("FAIL result requires explicit findings")
        return {"root": root_name, "path": path, "sha256": _hash(data), "size": len(data), "schema": schema}

    @staticmethod
    def _report_effect(outcome, payload):
        if outcome in {"PASS", "FAIL", "INCONCLUSIVE"} and payload["coverage"] != "COMPLETE":
            return "INCONCLUSIVE"
        if outcome == "PASS" and payload["status"] == "FAIL":
            return "FAIL"
        return outcome

    def _receipt(self, meta, check, receipt_id, dependencies, execution, outcome):
        artifacts = []
        if execution:
            for name in ("stdout.log", "stderr.log", "process.json"):
                artifacts.append(self._artifact(meta, "state", f"runs/{execution['run_id']}/{name}", None))
        # Missing/invalid required outputs make a receipt invalid, but do not erase
        # the actual process record/logs. The runner records the error separately.
        for artifact in check["artifacts"]:
            artifacts.append(self._artifact(meta, "workspace", artifact["path"], artifact["schema"]))
            if artifact["schema"]:
                payload = strict_json(_bytes(_inside(Path(meta["workspace"]), artifact["path"])))
                outcome = self._report_effect(outcome, payload)
        return {"schema": RECEIPT_SCHEMA, "receipt_id": receipt_id, "mission_id": meta["plan"]["mission_id"],
                "candidate": meta["candidate"], "check_id": check["id"], "kind": check["kind"],
                "outcome": outcome, "dependencies": dependencies, "artifacts": artifacts,
                "execution": execution, "created_at": _now()}

    def _save_receipt(self, conn, check_id, receipt):
        relative = f"receipts/{receipt['receipt_id']}.json"
        path = _inside(self.root, relative)
        write_new_json(path, receipt)
        digest = _hash(_bytes(path))
        conn.execute("UPDATE checks SET receipt=?, receipt_hash=?, consumed=0, outcome=? WHERE id=?",
                     (relative, digest, receipt["outcome"], check_id))
        return relative

    def record_artifact(self, check_id, worker=None, lease_token=None):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._admit(conn)
            check = self._check(meta, check_id)
            self.relay().guard(conn, meta, check_id, worker, lease_token)
            if check["kind"] != "artifact":
                raise ControlError("an execution check requires run-check; claims cannot substitute for execution")
            dependencies = self._dependencies(conn, meta, check)
            receipt = self._receipt(meta, check, uuid.uuid4().hex, dependencies, None, "PASS")
            outcome = receipt["outcome"]
            relative = self._save_receipt(conn, check_id, receipt)
            self._event(conn, "RECORD_ARTIFACT", {"check_id": check_id, "receipt": relative})
            conn.commit()
        return {"status": outcome, "receipt": relative, "execution": "NOT_RUN; artifact evidence only"}

    def run_check(self, check_id, command, timeout=60, worker=None, lease_token=None):
        if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x or "\0" in x for x in command):
            raise ControlError("command must be a nonempty argv list; shell execution is disabled")
        if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 600:
            raise ControlError("timeout must be within (0, 600] seconds")
        run_id = uuid.uuid4().hex
        run_dir = _inside(self.root, f"runs/{run_id}")
        proc = None
        # Admission and process creation share the same write transaction as STOP.
        # A committed STOP cannot be followed by an unadmitted Popen.
        try:
            with self.db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                meta = self._admit(conn)
                check = self._check(meta, check_id)
                self.relay().guard(conn, meta, check_id, worker, lease_token, required_seconds=timeout + 1)
                if check["kind"] != "execution":
                    raise ControlError("check is artifact-only")
                dependencies = self._dependencies(conn, meta, check)
                if conn.execute("SELECT 1 FROM runs WHERE check_id=? AND state='RUNNING'", (check_id,)).fetchone():
                    raise ControlError("check already has a running child")
                if conn.execute("SELECT 1 FROM runs WHERE check_id=? AND round=?", (check_id, meta["round"])).fetchone():
                    raise ControlError("check already attempted in this round; an explicit new round is required")
                run_dir.mkdir(parents=True)
                started = _now()
                with (run_dir / "stdout.log").open("xb") as stdout, (run_dir / "stderr.log").open("xb") as stderr:
                    try:
                        child_env = dict(os.environ)
                        child_env.pop("BAGO_RELAY_TOKEN", None)
                        proc = subprocess.Popen(command, cwd=meta["workspace"], stdout=stdout, stderr=stderr, env=child_env,
                                                stdin=subprocess.DEVNULL, shell=False, start_new_session=(os.name == "posix"))
                    except OSError as exc:
                        stderr.write((type(exc).__name__ + ": " + str(exc)).encode("utf-8", "replace"))
                    conn.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (run_id, check_id, meta["round"], _json(command), meta["workspace"],
                                  proc.pid if proc else None, started, None, None, "RUNNING" if proc else "LAUNCH_FAILED", "NONE", None))
                    self._event(conn, "RUN_START", {"run_id": run_id, "check_id": check_id, "pid": proc.pid if proc else None})
                    conn.commit()
        except BaseException as exc:
            if proc is not None:
                ended = _terminate_owned(proc)
                try:
                    write_new_json(run_dir / "admission_error.json", {
                        "schema": "bago.suite.process.emergency.v1", "run_id": run_id,
                        "pid": proc.pid, "at": _now(), "returncode": proc.poll(),
                        "interruption": "TERMINATED" if ended else "UNINTERRUPTIBLE",
                        "error": f"{type(exc).__name__}: {exc}",
                    })
                except (OSError, ValueError):
                    pass
            raise
        interruption = "NONE"
        supervision_error = None
        start_mono = time.monotonic()
        if proc is not None:
            while proc.poll() is None:
                try:
                    with self.db() as conn:
                        live_meta = self._meta(conn)
                        stopped = live_meta["control"] == "STOPPED"
                        if not stopped:
                            self.relay().guard(conn, live_meta, check_id, worker, lease_token)
                except (ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
                    stopped = True
                    supervision_error = f"{type(exc).__name__}: {exc}"
                if stopped or time.monotonic() - start_mono >= timeout:
                    ended = _terminate_owned(proc)
                    if supervision_error:
                        interruption = "CONTROL_ERROR_TERMINATED" if ended else "UNINTERRUPTIBLE"
                    else:
                        interruption = ("TERMINATED" if stopped else "TIMEOUT_TERMINATED") if ended else "UNINTERRUPTIBLE"
                    break
                time.sleep(0.05)
        code = proc.poll() if proc is not None else None
        finished = _now()
        outcome = "ERROR" if proc is None else ("INTERRUPTED" if interruption != "NONE" else ("PASS" if code == 0 else "FAIL"))
        if interruption == "UNINTERRUPTIBLE" and code is None:
            # Do not close stdout/child ownership by claiming termination.
            with self.db() as conn:
                conn.execute("UPDATE runs SET interruption=? WHERE id=?", (interruption, run_id))
                self._event(conn, "INTERRUPTION_UNCONFIRMED", {"run_id": run_id})
                conn.commit()
            return {"status": "INCONCLUSIVE", "run_id": run_id, "process_state": "RUNNING",
                    "interruption": interruption, "receipt": None}
        execution = {"run_id": run_id, "argv": command, "cwd": meta["workspace"], "pid": proc.pid if proc else None,
                     "started_at": started, "finished_at": finished, "returncode": code, "interruption": interruption}
        write_new_json(run_dir / "process.json", {"schema": "bago.suite.process.observation.v1",
            "execution": execution, "process_outcome": outcome, "supervision_error": supervision_error})
        process_outcome = outcome
        error = None
        try:
            receipt = self._receipt(meta, check, uuid.uuid4().hex, dependencies, execution, outcome)
            # A child can exit zero after changing the candidate it was asked to
            # check. Revalidate after execution before a receipt/status can PASS.
            # This check deliberately does not require ACTIVE: STOP must still
            # allow truthful partial observations to be preserved.
            self._candidate(meta)
            outcome = receipt["outcome"]
        except (ValueError, OSError, KeyError) as exc:
            receipt = None
            outcome = "ERROR"
            error = str(exc)
        try:
            with self.db() as conn:
                conn.execute("BEGIN IMMEDIATE")
                # STOP does not prevent retaining truthful partial execution evidence.
                conn.execute("UPDATE runs SET finished=?, returncode=?, state=?, interruption=? WHERE id=?",
                             (finished, code, "FINISHED" if proc else "LAUNCH_FAILED", interruption, run_id))
                relative = self._save_receipt(conn, check_id, receipt) if receipt else None
                if not receipt:
                    conn.execute("UPDATE checks SET consumed=0, receipt=NULL, receipt_hash=NULL, outcome='ERROR' WHERE id=?", (check_id,))
                conn.execute("UPDATE runs SET receipt=? WHERE id=?", (relative, run_id))
                self._event(conn, "RUN_FINISH", {"run_id": run_id, "outcome": outcome, "receipt": relative, "evidence_error": error,
                                               "supervision_error": supervision_error})
                conn.commit()
        except (OSError, sqlite3.Error) as exc:
            return {"status": "FAIL", "run_id": run_id, "receipt": None, "outcome": outcome,
                    "interruption": interruption, "evidence_error": str(exc),
                    "partial_process_record": f"runs/{run_id}/process.json"}
        return {"status": outcome if receipt else "FAIL", "run_id": run_id, "receipt": relative,
                "outcome": outcome, "interruption": interruption, "evidence_error": error,
                "supervision_error": supervision_error, "process_outcome": process_outcome}

    def _validate_stored(self, conn, meta, check_id, chain=(), cache=None):
        cache = {} if cache is None else cache
        if check_id in cache:
            return cache[check_id]
        check = self._check(meta, check_id)
        row = conn.execute("SELECT * FROM checks WHERE id=?", (check_id,)).fetchone()
        if not row or not row["receipt"]:
            raise ControlError("required check is NOT_RUN or lacks a receipt")
        raw = _bytes(_inside(self.root, row["receipt"]))
        digest = _hash(raw)
        if digest != row["receipt_hash"]:
            raise ControlError("receipt bytes changed")
        receipt = strict_json(raw)
        _keys(receipt, {"schema", "receipt_id", "mission_id", "candidate", "check_id", "kind", "outcome", "dependencies", "artifacts", "execution", "created_at"})
        if receipt["schema"] != RECEIPT_SCHEMA or receipt["mission_id"] != meta["plan"]["mission_id"] or receipt["candidate"] != meta["candidate"]:
            raise ControlError("receipt schema, mission or candidate mismatch")
        _id(receipt["receipt_id"]); _time(receipt["created_at"])
        if row["receipt"] != f"receipts/{receipt['receipt_id']}.json":
            raise ControlError("receipt identifier and stored path differ")
        if receipt["check_id"] != check_id or receipt["kind"] != check["kind"] or receipt["outcome"] not in _OUTCOMES:
            raise ControlError("receipt check, kind or outcome mismatch")
        if receipt["outcome"] != row["outcome"]:
            raise ControlError("receipt outcome differs from execution ledger")
        expected_dependencies = self._dependencies(conn, meta, check, chain, cache)
        if receipt["dependencies"] != expected_dependencies:
            raise ControlError("dependency evidence changed")
        expected_paths = {("workspace", a["path"]): a["schema"] for a in check["artifacts"]}
        execution = receipt["execution"]
        expected = "PASS"
        if check["kind"] == "execution":
            _keys(execution, {"run_id", "argv", "cwd", "pid", "started_at", "finished_at", "returncode", "interruption"})
            _id(execution["run_id"])
            if (execution["pid"] is not None and (type(execution["pid"]) is not int or execution["pid"] < 1)
                    or execution["returncode"] is not None and type(execution["returncode"]) is not int
                    or not isinstance(execution["argv"], list) or not execution["argv"]
                    or any(not isinstance(x, str) or not x or "\0" in x for x in execution["argv"])
                    or not isinstance(execution["cwd"], str)):
                raise ControlError("invalid execution field types")
            run = conn.execute("SELECT * FROM runs WHERE id=?", (execution["run_id"],)).fetchone()
            if not run or run["check_id"] != check_id or run["receipt"] != row["receipt"]:
                raise ControlError("receipt has no matching actual process execution")
            actual = {"run_id": run["id"], "argv": strict_json(run["command"]), "cwd": run["cwd"], "pid": run["pid"],
                      "started_at": run["started"], "finished_at": run["finished"], "returncode": run["returncode"], "interruption": run["interruption"]}
            if execution != actual or run["state"] not in {"FINISHED", "LAUNCH_FAILED"}:
                raise ControlError("claimed execution does not match recorded actual process")
            if _time(execution["finished_at"]) < _time(execution["started_at"]):
                raise ControlError("invalid execution interval")
            expected = "ERROR" if run["state"] == "LAUNCH_FAILED" else ("INTERRUPTED" if run["interruption"] != "NONE" else ("PASS" if run["returncode"] == 0 else "FAIL"))
            for log in ("stdout.log", "stderr.log", "process.json"):
                expected_paths[("state", f"runs/{run['id']}/{log}")] = None
        elif execution is not None:
            raise ControlError("artifact-only evidence cannot claim process execution")
        if not isinstance(receipt["artifacts"], list) or len(receipt["artifacts"]) != len(expected_paths):
            raise ControlError("missing or extra receipt artifacts")
        seen = set()
        for artifact in receipt["artifacts"]:
            _keys(artifact, {"root", "path", "sha256", "size", "schema"})
            safe_rel(artifact["path"])
            key = (artifact["root"], artifact["path"])
            if key in seen or key not in expected_paths or artifact["schema"] != expected_paths[key]:
                raise ControlError("artifact is duplicated or outside declared check scope")
            if not isinstance(artifact["sha256"], str) or not _HASH.fullmatch(artifact["sha256"]) or type(artifact["size"]) is not int:
                raise ControlError("invalid artifact identity")
            seen.add(key)
            if artifact != self._artifact(meta, artifact["root"], artifact["path"], artifact["schema"]):
                raise ControlError("artifact changed since receipt creation")
            if artifact["schema"]:
                payload = strict_json(_bytes(_inside(Path(meta["workspace"]), artifact["path"])))
                expected = self._report_effect(expected, payload)
        if receipt["outcome"] != expected:
            raise ControlError("outcome is inconsistent with actual execution and required result artifacts")
        cache[check_id] = (receipt, digest)
        return receipt, digest

    def consume(self, check_id, receipt_path=None, worker=None, lease_token=None):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._admit(conn)
            self._check(meta, check_id)
            self.relay().guard(conn, meta, check_id, worker, lease_token)
            if receipt_path is not None:
                safe_rel(receipt_path)
                row = conn.execute("SELECT receipt FROM checks WHERE id=?", (check_id,)).fetchone()
                if not row or receipt_path != row["receipt"]:
                    raise ControlError("receipt is not bound to a local execution/artifact record")
            receipt, digest = self._validate_stored(conn, meta, check_id)
            conn.execute("UPDATE checks SET consumed=1 WHERE id=?", (check_id,))
            self._event(conn, "CONSUME", {"check_id": check_id, "receipt_sha256": digest, "outcome": receipt["outcome"]})
            conn.commit()
        return {"status": "PASS", "evidence_status": "VALID", "product_status": receipt["outcome"], "check_id": check_id}

    def close(self):
        with self.db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            meta = self._admit(conn)
            outcomes = {}
            missing = []
            for check in meta["plan"]["checks"]:
                row = conn.execute("SELECT * FROM checks WHERE id=?", (check["id"],)).fetchone()
                if not row["receipt"]:
                    outcomes[check["id"]] = "NOT_RUN"
                    if check["mandatory"]:
                        missing.append(check["id"])
                    continue
                # Revalidate even already consumed evidence immediately before closure.
                receipt, _ = self._validate_stored(conn, meta, check["id"])
                outcomes[check["id"]] = receipt["outcome"]
                if check["mandatory"] and (not row["consumed"] or receipt["outcome"] not in {"PASS", "FAIL"}):
                    missing.append(check["id"])
                if check["mandatory"] and meta["plan"]["operation"] in {"AUDIT", "VERIFY"}:
                    # A crashing auditor is not a completed audit with product findings.
                    reports = [a for a in receipt["artifacts"] if a["schema"] == RESULT_SCHEMA]
                    complete = bool(reports) and all(
                        strict_json(_bytes(_inside(Path(meta["workspace"]), a["path"])))['coverage'] == 'COMPLETE'
                        for a in reports)
                    execution = receipt["execution"]
                    if (not complete or (execution is not None and (execution["returncode"] != 0 or execution["interruption"] != "NONE"))):
                        if check["id"] not in missing:
                            missing.append(check["id"])
            active = bool(conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone())
            relay_incomplete = self.relay().incomplete(conn, meta)
            mandatory_failed = [c["id"] for c in meta["plan"]["checks"] if c["mandatory"] and outcomes[c["id"]] != "PASS"]
            product = "NOT_VERIFIED" if missing or active or relay_incomplete else ("FAIL" if any(v == "FAIL" for v in outcomes.values()) else "PASS")
            blocked = bool(missing or active or relay_incomplete or (meta["plan"]["operation"] in {"REPAIR", "PROMOTE"} and mandatory_failed))
            result = {"status": "INCONCLUSIVE" if missing or active or relay_incomplete else ("FAIL" if blocked else "PASS"),
                      "operation": meta["plan"]["operation"], "task_status": "OPEN" if blocked else "CLOSED",
                      "product_status": product, "evidence_status": "INCOMPLETE" if missing or active or relay_incomplete else "VALID",
                      "outcomes": outcomes, "mandatory_not_satisfied": mandatory_failed,
                      "unconsumed_or_missing": missing, "owned_child_running": active,
                      "target": meta["plan"].get("target"), "published": False,
                      "collaboration_incomplete": bool(relay_incomplete)}
            if not blocked:
                self._set(conn, "closed", True)
            self._event(conn, "CLOSE_ATTEMPT", result)
            conn.commit()
        return result


def add_parser(subparsers):
    parser = subparsers.add_parser("task", help="Explicit bounded task control; no autonomous scheduling")
    actions = parser.add_subparsers(dest="task_action", required=True)
    for name in ("init", "status", "stop", "resume", "round", "assign", "run-check", "record-artifact", "consume", "close"):
        action = actions.add_parser(name)
        action.add_argument("--state-dir", required=True, type=Path)
        if name == "init":
            action.add_argument("--workspace", required=True, type=Path)
            action.add_argument("--plan", required=True, type=Path)
        if name in {"stop", "resume"}:
            action.add_argument("--reason", required=True)
        if name in {"assign", "run-check", "record-artifact", "consume"}:
            action.add_argument("--check", required=True)
        if name == "assign":
            action.add_argument("--worker", required=True)
        if name in {"run-check", "record-artifact", "consume"}:
            action.add_argument("--worker", help="Logical worker; lease is read from BAGO_RELAY_TOKEN")
        if name == "run-check":
            action.add_argument("--timeout", type=float, default=60)
            action.add_argument("argv", nargs=argparse.REMAINDER, help="Use -- followed by the actual executable and argv")
        if name == "consume":
            action.add_argument("--receipt", help="Optional exact ledger-relative receipt path")
    from suite_relay import add_parser as add_relay_parser
    add_relay_parser(actions)
    return parser


def execute(args, context):
    try:
        action = args.task_action
        # STOP must remain available even when the payload/candidate is damaged.
        # The ledger identity is reported as recorded, not freshly re-verified.
        identity = {} if action in {"stop", "status"} else _context_identity(context)
        provider = None if action in {"stop", "status"} else lambda: _context_identity(context)
        if action == "collaborate" and args.relay_action == "demo":
            from suite_relay_demo import run_demo
            skill = context["SKILL"] if isinstance(context, dict) else context.SKILL
            return run_demo(skill, args.output)
        store = TaskStore(args.state_dir, identity, provider)
        if action == "collaborate":
            from suite_relay import execute as execute_relay
            return execute_relay(args, store)
        if action == "init":
            return store.initialize(args.workspace, read_json(args.plan))
        if action == "status":
            result = store.status()
            result["candidate_identity_check"] = "NOT_RUN; recorded identity only"
            return result
        if action == "stop":
            result = store.stop(args.reason)
            result["candidate_identity_check"] = "NOT_RUN; STOP does not depend on candidate integrity"
            return result
        if action == "resume":
            return store.resume(args.reason)
        if action == "round":
            return store.open_round()
        if action == "assign":
            return store.assign(args.check, args.worker)
        if action == "run-check":
            argv = args.argv[1:] if args.argv and args.argv[0] == "--" else args.argv
            return store.run_check(args.check, argv, args.timeout, args.worker, os.environ.get("BAGO_RELAY_TOKEN"))
        if action == "record-artifact":
            return store.record_artifact(args.check, args.worker, os.environ.get("BAGO_RELAY_TOKEN"))
        if action == "consume":
            return store.consume(args.check, args.receipt, args.worker, os.environ.get("BAGO_RELAY_TOKEN"))
        if action == "close":
            return store.close()
        raise ControlError("unsupported task action")
    except (ControlError, ValueError, OSError, sqlite3.Error, KeyError, TypeError) as exc:
        return {"schema": CONTROL_SCHEMA, "status": "FAIL", "task_status": "NOT_CLOSED",
                "product_status": "NOT_VERIFIED", "evidence_status": "INVALID_OR_BLOCKED",
                "error": str(exc), "error_type": type(exc).__name__}
