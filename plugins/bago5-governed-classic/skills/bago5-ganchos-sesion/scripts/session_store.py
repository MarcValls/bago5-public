"""Bounded, locked, atomic session state in an explicitly authorized data root.

No files are created for an uninitialized native hook. This is a small local
receipt/cache, not a replacement TaskStore, remote memory or security boundary.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time

LIMIT = 2_000_000


class StoreError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse(raw):
    if len(raw) > LIMIT:
        raise StoreError("STATE_SIZE_LIMIT")
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(StoreError("NONFINITE_JSON")))


def _no_links(path):
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise StoreError("STATE_SYMLINK_OR_REPARSE_POINT")


def state_path(data_dir, host, session):
    if not isinstance(data_dir, str) or not data_dir.strip():
        return None
    root = Path(data_dir)
    if not root.is_absolute():
        raise StoreError("ABSOLUTE_PLUGIN_DATA_REQUIRED")
    if host not in {"CHAT", "WORK", "CODEX", "COPILOT"} or not isinstance(session, str) or not session.strip() or len(session) > 500:
        raise StoreError("INVALID_STATE_SCOPE")
    _no_links(root)
    key = hashlib.sha256((host + "\0" + session).encode("utf-8")).hexdigest()
    path = root / "bago5-session-hooks" / (key + ".json")
    _no_links(path)
    return path


def _read(path):
    _no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > LIMIT:
        raise StoreError("STATE_FILE_TYPE_OR_SIZE")
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    value = parse(raw)
    if not isinstance(value, dict):
        raise StoreError("STATE_OBJECT_REQUIRED")
    return value


class Transaction:
    def __init__(self, path, state, host, session):
        self.path, self.state, self.host, self.session = path, state, host, session

    def save(self, value):
        if self.path is None:
            raise StoreError("NO_AUTHORIZED_STATE_SURFACE")
        if not isinstance(value, dict) or value.get("host") != self.host or value.get("host_session_id") != self.session:
            raise StoreError("STATE_BINDING_MISMATCH")
        if value.get("persistence", {}).get("authorized") is not True or not value["persistence"].get("source_ref"):
            raise StoreError("LOCAL_PERSISTENCE_NOT_AUTHORIZED")
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        if len(raw) > LIMIT:
            raise StoreError("STATE_SIZE_LIMIT")
        _no_links(self.path)
        descriptor, temporary = tempfile.mkstemp(prefix=".state-", suffix=".tmp", dir=self.path.parent)
        try:
            os.chmod(temporary, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            _no_links(self.path)
            os.replace(temporary, self.path)
            # Persist directory entry on POSIX; Windows replace is atomic locally.
            if os.name != "nt":
                descriptor = os.open(self.path.parent, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
            if _read(self.path) != value:
                raise StoreError("LOCAL_STATE_READBACK_MISMATCH")
            self.state = value
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


@contextmanager
def transaction(data_dir, host, session, create=False):
    path = state_path(data_dir, host, session)
    if path is None or not create and not path.exists():
        if create:
            raise StoreError("NO_AUTHORIZED_STATE_SURFACE")
        yield Transaction(None, None, host, session)
        return
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    _no_links(path.parent)
    lock_path = path.with_suffix(".lock")
    _no_links(lock_path)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    locked = False
    try:
        if os.name == "nt":
            import msvcrt
            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            def lock():
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            def unlock():
                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            def lock():
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            def unlock():
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        deadline = time.monotonic() + 1.0
        while not locked:
            try:
                lock()
                locked = True
            except (BlockingIOError, OSError):
                if time.monotonic() >= deadline:
                    raise StoreError("SESSION_STATE_BUSY_RETRY_WITHOUT_DISPATCH")
                time.sleep(0.01)
        state = _read(path) if path.exists() else None
        if state is not None and (state.get("host") != host or state.get("host_session_id") != session):
            raise StoreError("STATE_BINDING_MISMATCH")
        yield Transaction(path, state, host, session)
    finally:
        if locked:
            unlock()
        os.close(descriptor)
