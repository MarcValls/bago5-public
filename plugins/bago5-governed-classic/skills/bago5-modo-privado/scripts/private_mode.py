"""BAGO5 private-mode core, v1. No installed ChatGPT/Codex host binding.

The SQLite gate enforces *cooperative* admission across participating processes.
A trusted host must bind every controlled observer, worker, shell and dispatcher;
it must also cancel/flush streams. This library is not an OS sandbox.
No vault path, account, username or password is accepted by this interface.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Iterator, Protocol, TypeVar

T = TypeVar('T')


class State(str, Enum):
    NORMAL = 'NORMAL'
    PREPARING = 'PREPARING'
    PRIVATE = 'PRIVATE'
    RESUMING = 'RESUMING'
    CANCELLED = 'CANCELLED'
    BLOCKED = 'BLOCKED'


class Code(str, Enum):
    HOST_UNAVAILABLE = 'HOST_UNAVAILABLE'
    HOST_BOUNDARY_UNPROVEN = 'HOST_BOUNDARY_UNPROVEN'
    OBSERVATION_NOT_DRAINED = 'OBSERVATION_NOT_DRAINED'
    GATE_CLOSED = 'GATE_CLOSED'
    STALE_RESULT = 'STALE_RESULT'
    CONTROLLER_BUSY = 'CONTROLLER_BUSY'
    RECOVERY_REQUIRED = 'RECOVERY_REQUIRED'
    EXPLICIT_CONFIRMATION_REQUIRED = 'EXPLICIT_CONFIRMATION_REQUIRED'
    INVALID_STATE = 'INVALID_STATE'
    INVALID_ACTION = 'INVALID_ACTION'
    STORAGE_UNAVAILABLE = 'STORAGE_UNAVAILABLE'
    EXECUTABLE_UNTRUSTED = 'EXECUTABLE_UNTRUSTED'
    UNSUPPORTED_PLATFORM = 'UNSUPPORTED_PLATFORM'
    LAUNCH_FAILED = 'LAUNCH_FAILED'
    HOST_FAILURE = 'HOST_FAILURE'
    CANCEL_REQUESTED = 'CANCEL_REQUESTED'


class Denied(RuntimeError):
    """Only fixed, non-sensitive diagnostics may cross the host boundary."""
    def __init__(self, code: Code):
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True)
class Snapshot:
    state: State
    epoch: int
    active: int
    owned: bool


class Gate:
    """Durable, fail-closed gate; all participating processes use ONE local DB.

    New stores start BLOCKED. No timeout/TTL or constructor opens a closed gate.
    Only the trusted, local host bootstrap/resume path may enable admission.
    SQLite/DLL/Python binaries, directory ACLs and host wiring are trusted inputs.
    """
    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        if self.path.is_symlink() or not self.path.parent.is_dir():
            raise Denied(Code.STORAGE_UNAVAILABLE)
        try:
            with self._db() as con:
                con.executescript('''
                    CREATE TABLE IF NOT EXISTS control (
                        singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                        state TEXT NOT NULL, epoch INTEGER NOT NULL,
                        owner TEXT);
                    CREATE TABLE IF NOT EXISTS active (
                        ticket TEXT PRIMARY KEY, epoch INTEGER NOT NULL);
                    CREATE TABLE IF NOT EXISTS audit (
                        at REAL NOT NULL, state TEXT NOT NULL);
                    INSERT OR IGNORE INTO control VALUES(1,'BLOCKED',0,NULL);
                ''')
        except Exception:
            raise Denied(Code.STORAGE_UNAVAILABLE) from None

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        # Explicit transaction rollback on every exception. No payload logging.
        con = None
        try:
            con = sqlite3.connect(str(self.path), timeout=2, isolation_level=None)
            con.execute('PRAGMA synchronous=FULL')
            con.execute('BEGIN IMMEDIATE')
            yield con
            if con.in_transaction:
                con.commit()
        except sqlite3.Error:
            if con is not None and con.in_transaction:
                con.rollback()
            raise Denied(Code.STORAGE_UNAVAILABLE) from None
        except BaseException:
            if con is not None and con.in_transaction:
                con.rollback()
            raise
        finally:
            if con is not None:
                con.close()

    @staticmethod
    def _row(con: sqlite3.Connection) -> tuple[str, int, str | None]:
        row = con.execute('SELECT state,epoch,owner FROM control WHERE singleton=1').fetchone()
        if row is None or row[0] not in {x.value for x in State}:
            raise Denied(Code.STORAGE_UNAVAILABLE)
        return row

    @staticmethod
    def _audit(con: sqlite3.Connection, state: State) -> None:
        con.execute('INSERT INTO audit VALUES(?,?)', (time.time(), state.value))

    def snapshot(self) -> Snapshot:
        with self._db() as con:
            state, epoch, owner = self._row(con)
            active = con.execute('SELECT COUNT(*) FROM active').fetchone()[0]
            return Snapshot(State(state), epoch, active, owner is not None)

    def bootstrap(self) -> None:
        """Trusted host installation only, AFTER local approval/coverage checks.
        Not a model-facing tool. Never recovers an interrupted private session.
        """
        with self._db() as con:
            state, epoch, owner = self._row(con)
            if state != State.BLOCKED or epoch != 0 or owner is not None:
                raise Denied(Code.RECOVERY_REQUIRED)
            if con.execute('SELECT COUNT(*) FROM active').fetchone()[0]:
                raise Denied(Code.OBSERVATION_NOT_DRAINED)
            con.execute("UPDATE control SET state='NORMAL',epoch=1 WHERE singleton=1")
            self._audit(con, State.NORMAL)

    def begin(self) -> str:
        with self._db() as con:
            state, _, owner = self._row(con)
            if owner is not None:
                raise Denied(Code.CONTROLLER_BUSY)
            if state != State.NORMAL:
                raise Denied(Code.RECOVERY_REQUIRED)
            token = uuid.uuid4().hex
            con.execute("UPDATE control SET state='PREPARING',epoch=epoch+1,owner=? WHERE singleton=1", (token,))
            self._audit(con, State.PREPARING)
            return token

    def transition(self, owner: str, state: State) -> None:
        allowed = {
            State.PREPARING: {State.PRIVATE, State.CANCELLED, State.BLOCKED},
            State.PRIVATE: {State.RESUMING, State.CANCELLED, State.BLOCKED},
            State.CANCELLED: {State.RESUMING, State.BLOCKED},
            State.BLOCKED: {State.RESUMING, State.CANCELLED},
            State.RESUMING: {State.NORMAL, State.BLOCKED, State.CANCELLED},
        }
        with self._db() as con:
            current, _, actual = self._row(con)
            if actual != owner or not actual:
                raise Denied(Code.CONTROLLER_BUSY)
            if state not in allowed.get(State(current), set()):
                raise Denied(Code.INVALID_STATE)
            if state in {State.PRIVATE, State.RESUMING, State.NORMAL}:
                if con.execute('SELECT COUNT(*) FROM active').fetchone()[0]:
                    raise Denied(Code.OBSERVATION_NOT_DRAINED)
            if state == State.NORMAL:
                con.execute("UPDATE control SET state='NORMAL',epoch=epoch+1,owner=NULL WHERE singleton=1")
            else:
                con.execute('UPDATE control SET state=? WHERE singleton=1', (state.value,))
            self._audit(con, state)

    @contextmanager
    def ticket(self) -> Iterator['Ticket']:
        with self._db() as con:
            state, epoch, _ = self._row(con)
            if state != State.NORMAL:
                raise Denied(Code.GATE_CLOSED)
            token = uuid.uuid4().hex
            con.execute('INSERT INTO active VALUES(?,?)', (token, epoch))
        lease = Ticket(self, epoch)
        try:
            yield lease
        finally:
            with self._db() as con:
                con.execute('DELETE FROM active WHERE ticket=?', (token,))

    def invoke(self, operation: Callable[['Ticket'], T]) -> T:
        """Wrap full lifetime INCLUDING payload delivery/logging by the host.
        Buffered results from a cancelled generation must not be delivered.
        """
        with self.ticket() as ticket:
            value = operation(ticket)
            if ticket.cancelled:
                raise Denied(Code.STALE_RESULT)
            return value

    def wait_idle(self, timeout: float) -> None:
        deadline = time.monotonic() + max(0.0, timeout)
        while self.snapshot().active:
            if time.monotonic() >= deadline:
                raise Denied(Code.OBSERVATION_NOT_DRAINED)
            time.sleep(0.01)

    def audit(self) -> list[tuple[float, str]]:
        with self._db() as con:
            return list(con.execute('SELECT at,state FROM audit ORDER BY rowid'))


@dataclass(frozen=True)
class Ticket:
    gate: Gate
    epoch: int

    @property
    def cancelled(self) -> bool:
        s = self.gate.snapshot()
        return s.state != State.NORMAL or s.epoch != self.epoch


class HostBoundary(Protocol):
    """Implemented INSIDE a trusted host, not by a JSON flag/model response.

    Must cover all controlled sessions, tools, streams, video, accessibility,
    keyboard, clipboard, shell, file/memory readers, observers, worker creation,
    retries, telemetry/export queues. Unknown coverage => raise Denied.
    freeze_and_flush must stop producers AND discard/flush pre-private buffers.
    prepare_resume must NOT start observers or replay pending work.
    """
    def validate_coverage(self, gate: Gate) -> None: ...
    def freeze_and_flush(self, gate: Gate) -> None: ...
    def confirm_sealed(self, gate: Gate) -> None: ...
    def prepare_resume(self, gate: Gate) -> None: ...


class MissingHost:
    def validate_coverage(self, gate: Gate) -> None:
        raise Denied(Code.HOST_UNAVAILABLE)
    def freeze_and_flush(self, gate: Gate) -> None:
        raise Denied(Code.HOST_UNAVAILABLE)
    def confirm_sealed(self, gate: Gate) -> None:
        raise Denied(Code.HOST_UNAVAILABLE)
    def prepare_resume(self, gate: Gate) -> None:
        raise Denied(Code.HOST_UNAVAILABLE)


class Launcher(Protocol):
    def verify(self) -> None: ...
    def open(self) -> None: ...


class WindowsKeePassXC:
    """GUI only, no arguments/vault/key/stdin. Local trusted pins are essential.

    Pins must come from operator-verified installation, never from an LLM or
    arbitrary JSON approval. Version updates require explicit re-verification.
    Host must verify protected installation/config ACLs; same-user malware and
    administrator/OS compromise are outside this guarantee.
    """
    def __init__(self, executable: Path, sha256_pin: str, signer_thumbprint: str):
        self.executable = Path(executable)
        self.sha256_pin = sha256_pin.lower()
        self.signer_thumbprint = signer_thumbprint.upper()

    def verify(self) -> None:
        if os.name != 'nt':
            raise Denied(Code.UNSUPPORTED_PLATFORM)
        p = self.executable
        if not p.is_absolute() or str(p).startswith('\\\\') or p.name.lower() != 'keepassxc.exe':
            raise Denied(Code.EXECUTABLE_UNTRUSTED)
        if not re.fullmatch(r'[a-f0-9]{64}', self.sha256_pin) or not re.fullmatch(r'[A-F0-9]{40,64}', self.signer_thumbprint):
            raise Denied(Code.EXECUTABLE_UNTRUSTED)
        try:
            # Reject links/junctions along the complete installation path.
            for part in [p, *p.parents]:
                st = part.lstat()
                if part.is_symlink() or getattr(st, 'st_file_attributes', 0) & 0x400:
                    raise Denied(Code.EXECUTABLE_UNTRUSTED)
            if not stat.S_ISREG(p.stat().st_mode):
                raise Denied(Code.EXECUTABLE_UNTRUSTED)
            roots = [Path(os.environ[k]).resolve() for k in ('ProgramFiles', 'ProgramFiles(x86)') if k in os.environ]
            if not any(p.resolve().is_relative_to(root) for root in roots):
                raise Denied(Code.EXECUTABLE_UNTRUSTED)
            with p.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != self.sha256_pin:
                raise Denied(Code.EXECUTABLE_UNTRUSTED)
            ps = Path(os.environ['SystemRoot']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            literal = str(p).replace("'", "''")
            script = ("$ErrorActionPreference='Stop';$s=Get-AuthenticodeSignature -LiteralPath '" + literal
                      + "';@{Status=$s.Status.ToString();Thumbprint=$s.SignerCertificate.Thumbprint}|ConvertTo-Json -Compress")
            check = subprocess.run([str(ps), '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', script],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   timeout=15, shell=False, env=self._environment())
            signature = json.loads(check.stdout.decode('utf-8-sig'))
            if check.returncode or signature.get('Status') != 'Valid' or signature.get('Thumbprint', '').upper() != self.signer_thumbprint:
                raise Denied(Code.EXECUTABLE_UNTRUSTED)
        except Denied:
            raise
        except Exception:
            raise Denied(Code.EXECUTABLE_UNTRUSTED) from None

    def _environment(self) -> dict[str, str]:
        # Do not inherit API keys, password vars, QT_PLUGIN_PATH, Python hooks etc.
        allowed = ('SystemRoot', 'WINDIR', 'USERPROFILE', 'LOCALAPPDATA', 'APPDATA', 'TEMP', 'TMP', 'ProgramFiles', 'ProgramFiles(x86)')
        env = {k: os.environ[k] for k in allowed if k in os.environ}
        env['PATH'] = str(Path(env.get('SystemRoot', 'C:\\Windows')) / 'System32')
        return env

    def open(self) -> None:
        self.verify()  # Re-check immediately before spawn; protected ACL is still required.
        try:
            subprocess.Popen([str(self.executable)], shell=False,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, cwd=str(self.executable.parent),
                             env=self._environment(), close_fds=True)
        except Exception:
            raise Denied(Code.LAUNCH_FAILED) from None


class Coordinator:
    def __init__(self, gate: Gate, launcher: Launcher, host: HostBoundary | None = None):
        self.gate = gate
        self.launcher = launcher
        self.host = host if host is not None else MissingHost()
        self._owner: str | None = None
        self._lock = threading.RLock()
        self._cancel_requested = threading.Event()

    def _block(self) -> None:
        if self._owner:
            try:
                if self.gate.snapshot().state != State.BLOCKED:
                    self.gate.transition(self._owner, State.BLOCKED)
            except Denied:
                # Never reopen after failure, including unavailable storage.
                pass

    def request_cancel(self) -> None:
        # Non-blocking even while the host handshake holds the controller lock.
        self._cancel_requested.set()

    def _check_cancelled(self) -> None:
        if self._cancel_requested.is_set():
            raise Denied(Code.CANCEL_REQUESTED)

    def start(self, timeout: float = 5.0) -> State:
        with self._lock:
            if self._owner is not None:
                raise Denied(Code.CONTROLLER_BUSY)
            # Close local admission even when the external host is unsupported.
            self._owner = self.gate.begin()
            try:
                self._check_cancelled()
                self.host.validate_coverage(self.gate)
                self.host.freeze_and_flush(self.gate)
                self._check_cancelled()
                self.gate.wait_idle(timeout)
                self.host.confirm_sealed(self.gate)
                self.launcher.verify()
                self._check_cancelled()
                self.gate.transition(self._owner, State.PRIVATE)
                self._check_cancelled()
                self.launcher.open()
                return State.PRIVATE
            except Denied as error:
                if error.code == Code.CANCEL_REQUESTED and self._owner:
                    self.gate.transition(self._owner, State.CANCELLED)
                else:
                    self._block()
                raise
            except Exception:
                self._block()
                raise Denied(Code.HOST_FAILURE) from None

    def cancel(self) -> State:
        self.request_cancel()
        with self._lock:
            if self._owner is None:
                raise Denied(Code.RECOVERY_REQUIRED)
            state = self.gate.snapshot().state
            if state != State.CANCELLED:
                self.gate.transition(self._owner, State.CANCELLED)
            return State.CANCELLED  # Gate deliberately remains closed.

    def finish(self, action: str, *, safe_to_resume: bool) -> dict[str, object]:
        """LOCAL human UI callback only; must NOT be exposed as an agent tool.
        safe_to_resume confirms app locked/closed and clipboard dealt with by user;
        neither this assertion nor 'done' claims a password was actually saved.
        """
        with self._lock:
            if action not in {'done', 'cancel'}:
                raise Denied(Code.INVALID_ACTION)
            if safe_to_resume is not True:
                raise Denied(Code.EXPLICIT_CONFIRMATION_REQUIRED)
            if self._owner is None:
                raise Denied(Code.RECOVERY_REQUIRED)
            current = self.gate.snapshot().state
            if current not in {State.PRIVATE, State.CANCELLED, State.BLOCKED}:
                raise Denied(Code.INVALID_STATE)
            if current != State.PRIVATE and action == 'done':
                raise Denied(Code.INVALID_ACTION)
            try:
                self.host.validate_coverage(self.gate)
                self.gate.wait_idle(0)
                self.host.confirm_sealed(self.gate)
                self.gate.transition(self._owner, State.RESUMING)
                self.host.prepare_resume(self.gate)
                self.gate.transition(self._owner, State.NORMAL)
                self._owner = None
                self._cancel_requested.clear()
            except Denied:
                self._block()
                raise
            except Exception:
                self._block()
                raise Denied(Code.HOST_FAILURE) from None
            return {'state': State.NORMAL.value, 'user_finished': action == 'done', 'save_verified': False}


class SafeArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        # argparse's default echoes unrecognized values; never mirror input.
        print(json.dumps({'state': 'BLOCKED', 'code': 'INVALID_ACTION'}))
        raise SystemExit(2)


def main() -> int:
    parser = SafeArgumentParser(description='BAGO5 private-mode capability check; no installed host adapter.')
    parser.add_argument('--check', action='store_true', help='Read-only check, no vault, app or state creation')
    parser.parse_args()
    # No --force / --approved / --host-safe escape hatch.
    print(json.dumps({'state': 'BLOCKED', 'code': 'HOST_UNAVAILABLE',
                      'host_binding': 'NOT_INSTALLED', 'windows_keepassxc': 'NOT_RUN',
                      'note': 'No trusted host adapter is bundled. Do not enter real secrets on a claimed private session.'}))
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
