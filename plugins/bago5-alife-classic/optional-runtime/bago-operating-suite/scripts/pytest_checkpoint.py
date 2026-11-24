"""Opt-in, fail-closed checkpoints for sequential pytest runs.

Use: python -m pytest -p scripts.pytest_checkpoint --bago-checkpoint .pytest_cache/run.sqlite3 tests -q
Then add --bago-resume with the same arguments to rerun only unverified items.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone

import pytest

SCHEMA_VERSION = 1


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_args(args: tuple[str, ...]) -> list[str]:
    """Remove only this plugin's transport options, retaining pytest selection flags."""
    result: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--bago-resume":
            i += 1
        elif arg in {"--bago-checkpoint", "--bago-context"}:
            if i + 1 >= len(args):
                raise pytest.UsageError(f"missing value after {arg}")
            i += 2
        elif arg.startswith("--bago-checkpoint=") or arg.startswith("--bago-context="):
            i += 1
        else:
            result.append(arg)
            i += 1
    return result


def _snapshot_git(root: Path, state_file: Path) -> str:
    """Fingerprint all tracked and visible untracked Git files, not only commit HEAD.

    Ignored files, external services, env secrets, and side effects are out of scope.
    A mutation while hashing raises instead of producing a misleading identity.
    """
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=root, capture_output=True, check=False, timeout=60,
        )
        if top.returncode:
            raise pytest.UsageError("BAGO checkpoint requires a Git working tree")
        # pytest.rootpath can be tests/, while imported application code lives above it.
        root = Path(os.fsdecode(top.stdout).strip()).resolve()
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, capture_output=True, check=False, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise pytest.UsageError(f"BAGO checkpoint needs a stable Git workspace: {exc}") from exc
    if result.returncode:
        raise pytest.UsageError("BAGO checkpoint needs a Git workspace; git ls-files failed")
    digest = hashlib.sha256()
    excluded = {state_file, Path(str(state_file) + ".lock")}
    excluded |= {Path(str(state_file) + ext) for ext in ("-journal", "-wal", "-shm")}
    for entry in sorted(set(filter(None, result.stdout.split(b"\0")))):
        relative = Path(os.fsdecode(entry))
        if relative.is_absolute() or ".." in relative.parts:
            raise pytest.UsageError("invalid Git inventory entry")
        path = root / relative
        if path in excluded:
            continue
        # No external symlink target may silently be treated as protected source.
        candidate = root
        for part in relative.parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise pytest.UsageError(f"checkpoint cannot fingerprint symlink: {relative}")
        if not path.is_file():
            raise pytest.UsageError(f"Git-listed source disappeared or is not a file: {relative}")
        before = path.stat()
        digest.update(entry + b"\0")
        digest.update(str(before.st_size).encode() + b"\0")
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise pytest.UsageError(f"source changed while fingerprinting: {relative}")
        digest.update(b"\0")
    return digest.hexdigest()


def _packages_sha() -> str:
    """Bind resumes to installed distribution versions without persisting secrets."""
    packages = sorted(
        (d.metadata.get("Name", "").lower(), d.version)
        for d in importlib.metadata.distributions()
    )
    return hashlib.sha256(json.dumps(packages).encode()).hexdigest()


class _Lock:
    """Kernel-released, cross-platform exclusive lock; safe after SIGKILL."""

    def __init__(self, path: Path) -> None:
        self._file = path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt
                self._file.seek(0, 2)
                if self._file.tell() == 0:
                    self._file.write(b"\0")
                    self._file.flush()
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            self._file.close()
            raise pytest.UsageError(f"checkpoint already in use: {path}") from exc

    def close(self) -> None:
        if self._file.closed:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._file.seek(0)
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()


class CheckpointPlugin:
    def __init__(self, config: pytest.Config) -> None:
        self.config = config
        self.resume = bool(config.getoption("--bago-resume"))
        state = Path(config.getoption("--bago-checkpoint"))
        self.state = state if state.is_absolute() else config.rootpath / state
        self.state = self.state.absolute()
        self._phases: dict[str, dict[str, str]] = {}
        self._all_count = 0
        self._resumed_count = 0
        self._fully_resumed = False
        self._started = False
        self._collection_failed = False
        self._conn: sqlite3.Connection | None = None
        self._lock: _Lock | None = None
        self._verify_options()
        if self.resume and not self.state.is_file():
            raise pytest.UsageError(f"checkpoint does not exist: {self.state}")
        if not self.resume and self.state.exists():
            raise pytest.UsageError("checkpoint exists: use --bago-resume or a NEW path (history is never overwritten)")
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self._lock = _Lock(Path(str(self.state) + ".lock"))

    def _verify_options(self) -> None:
        # xdist workers may interleave reports; this v1 intentionally does not claim parallel coverage.
        processes = self.config.getoption("numprocesses", default=None)
        if processes not in (None, 0, "0") or hasattr(self.config, "workerinput"):
            raise pytest.UsageError("BAGO checkpoint v1 supports sequential pytest only (no xdist -n)")
        for name in ("lf", "failedfirst", "stepwise", "stepwise_skip", "cacheclear"):
            if self.config.getoption(name, default=False):
                raise pytest.UsageError(f"BAGO checkpoint cannot combine with --{name}")

    def pytest_collectreport(self, report: pytest.CollectReport) -> None:
        if report.failed:
            self._collection_failed = True

    @pytest.hookimpl(trylast=True)
    def pytest_collection_modifyitems(self, items: list[pytest.Item]) -> None:
        if self._collection_failed:
            raise pytest.UsageError("collection failed: no reliable checkpoint manifest")
        if not items:
            raise pytest.UsageError("cannot checkpoint an empty collection")
        nodeids = [item.nodeid for item in items]
        if len(nodeids) != len(set(nodeids)):
            raise pytest.UsageError("cannot checkpoint duplicate node IDs")
        meta = {
            "schema": SCHEMA_VERSION,
            "root": str(self.config.rootpath.resolve()),
            "python": [sys.version_info.major, sys.version_info.minor, sys.version_info.micro],
            "python_executable": sys.executable,
            "pytest": pytest.__version__,
            "plugin_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "packages_sha256": _packages_sha(),
            "files_sha256": _snapshot_git(self.config.rootpath, self.state),
            "arguments": _canonical_args(tuple(self.config.invocation_params.args)),
            "context": self.config.getoption("--bago-context") or "",
            "nodeids": nodeids,
        }
        self._all_count = len(nodeids)
        conn: sqlite3.Connection | None = None
        try:
            conn = sqlite3.connect(self.state)
            conn.execute("PRAGMA synchronous=FULL")
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("CREATE TABLE IF NOT EXISTS run_info (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
            conn.execute("""CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nodeid TEXT NOT NULL,
                status TEXT NOT NULL,
                phases_json TEXT NOT NULL,
                at_utc TEXT NOT NULL
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS attempts_by_nodeid ON attempts(nodeid, id)")
            conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                at_utc TEXT NOT NULL,
                pytest_exit_code INTEGER NOT NULL,
                resume INTEGER NOT NULL
            )""")
            if self.resume:
                row = conn.execute("SELECT value FROM run_info WHERE key='metadata'").fetchone()
                if row is None:
                    raise pytest.UsageError("checkpoint missing identity metadata")
                saved = json.loads(row[0])
                for key, value in meta.items():
                    if saved.get(key) != value:
                        raise pytest.UsageError(f"checkpoint identity mismatch: {key} (refusing stale PASS)")
            else:
                conn.execute("INSERT INTO run_info VALUES (?, ?)", ("metadata", json.dumps(meta, sort_keys=True)))
                conn.execute("INSERT INTO run_info VALUES (?, ?)", ("created_at", _utcnow()))
            conn.commit()
            self._conn = conn
            self._started = True
            if self.resume:
                done = {row[0] for row in conn.execute("""
                    SELECT a.nodeid FROM attempts AS a
                    WHERE a.id = (SELECT MAX(b.id) FROM attempts AS b WHERE b.nodeid=a.nodeid)
                      AND a.status='PASSED'
                """)}
                removed = [item for item in items if item.nodeid in done]
                if removed:
                    items[:] = [item for item in items if item.nodeid not in done]
                    self.config.hook.pytest_deselected(items=removed)
                self._resumed_count = len(removed)
                self._fully_resumed = self._resumed_count == self._all_count
        except (sqlite3.Error, ValueError, pytest.UsageError) as exc:
            if conn is not None and self._conn is None:
                conn.close()
            if isinstance(exc, pytest.UsageError):
                raise
            raise pytest.UsageError(f"checkpoint database invalid/unavailable: {exc}") from exc

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        if report.when not in {"setup", "call", "teardown"}:
            return
        phases = self._phases.setdefault(report.nodeid, {})
        # Explicit xfail is not promoted to PASS even if pytest exits 0.
        if hasattr(report, "wasxfail"):
            result = "XFAIL" if report.skipped else "XPASS"
        else:
            result = report.outcome.upper()
        phases[report.when] = result
        if report.when != "teardown":
            return
        snapshot = dict(phases)
        self._phases.pop(report.nodeid, None)
        if any(phase in {"FAILED", "XPASS"} for phase in snapshot.values()):
            status = "FAILED"
        elif any(phase in {"SKIPPED", "XFAIL"} for phase in snapshot.values()):
            status = "SKIPPED"
        elif snapshot.get("setup") == snapshot.get("call") == snapshot.get("teardown") == "PASSED":
            status = "PASSED"
        else:
            status = "INCOMPLETE"
        if self._conn is None:
            raise pytest.UsageError("checkpoint database was not initialized")
        try:
            self._conn.execute(
                "INSERT INTO attempts (nodeid, status, phases_json, at_utc) VALUES (?, ?, ?, ?)",
                (report.nodeid, status, json.dumps(snapshot, sort_keys=True), _utcnow()),
            )
            self._conn.commit()  # Full-synchronous durable boundary per finalized test.
        except sqlite3.Error as exc:
            raise pytest.UsageError(f"checkpoint write failed; stopping: {exc}") from exc

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int) -> None:
        if (
            self._started
            and self.resume
            and self._fully_resumed
            and exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED
            and session.testsfailed == 0
        ):
            session.exitstatus = pytest.ExitCode.OK
        if self._started and self._conn is not None:
            try:
                self._conn.execute(
                    "INSERT INTO sessions (at_utc, pytest_exit_code, resume) VALUES (?, ?, ?)",
                    (_utcnow(), int(session.exitstatus), int(self.resume)),
                )
                self._conn.commit()
            except sqlite3.Error as exc:
                raise pytest.UsageError(f"checkpoint session finalization failed: {exc}") from exc

    def pytest_terminal_summary(self, terminalreporter: object) -> None:
        if self._conn is None:
            return
        counts = _current_counts(self._conn)
        terminalreporter.write_sep("-", "BAGO durable checkpoint")
        terminalreporter.write_line(
            f"{counts.get('PASSED', 0)}/{self._all_count} PASSED; "
            f"{self._resumed_count} reused on resume; "
            f"remaining={self._all_count - counts.get('PASSED', 0)}; "
            f"state={self.state}"
        )

    def pytest_unconfigure(self, config: pytest.Config) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None
        if self._lock is not None:
            self._lock.close()
            self._lock = None


def _current_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {status: count for status, count in conn.execute("""
        SELECT a.status, COUNT(*) FROM attempts AS a
        WHERE a.id = (SELECT MAX(b.id) FROM attempts AS b WHERE b.nodeid=a.nodeid)
        GROUP BY a.status
    """)}


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("bago-checkpoint", "BAGO per-test durable resume")
    group.addoption("--bago-checkpoint", metavar="FILE", help="new or existing SQLite checkpoint file")
    group.addoption("--bago-resume", action="store_true", help="rerun only items not previously PASSED")
    group.addoption("--bago-context", metavar="ID", default="", help="identity for external fixtures/services")


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--bago-resume") and not config.getoption("--bago-checkpoint"):
        raise pytest.UsageError("--bago-resume requires --bago-checkpoint")
    if config.getoption("--bago-context") and not config.getoption("--bago-checkpoint"):
        raise pytest.UsageError("--bago-context requires --bago-checkpoint")
    if config.getoption("--bago-checkpoint"):
        config.pluginmanager.register(CheckpointPlugin(config), "bago_checkpoint_active")


def _status(state: Path) -> dict[str, object]:
    # Read only; a missing/corrupt file is an error, not an empty successful state.
    conn = sqlite3.connect(f"file:{state.resolve().as_posix()}?mode=ro", uri=True)
    try:
        row = conn.execute("SELECT value FROM run_info WHERE key='metadata'").fetchone()
        if row is None:
            raise ValueError("checkpoint missing metadata")
        meta = json.loads(row[0])
        counts = _current_counts(conn)
        session_row = conn.execute("SELECT pytest_exit_code FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
        total = len(meta["nodeids"])
        return {
            "schema": SCHEMA_VERSION,
            "checkpoint": str(state),
            "files_sha256": meta["files_sha256"],
            "test_count": total,
            "passed": counts.get("PASSED", 0),
            "remaining": total - counts.get("PASSED", 0),
            "statuses": counts,
            "checkpoint_complete": counts.get("PASSED", 0) == total,
            "last_recorded_pytest_exit_code": session_row[0] if session_row else None,
            "recorded_sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
            "attempts": conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0],
            "created_at": conn.execute("SELECT value FROM run_info WHERE key='created_at'").fetchone()[0],
        }
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "status":
        print("usage: python scripts/pytest_checkpoint.py status CHECKPOINT.sqlite3", file=sys.stderr)
        sys.exit(2)
    try:
        print(json.dumps(_status(Path(sys.argv[2])), indent=2, sort_keys=True))
    except (OSError, sqlite3.Error, ValueError, KeyError) as exc:
        print(f"checkpoint status unavailable: {exc}", file=sys.stderr)
        sys.exit(2)
