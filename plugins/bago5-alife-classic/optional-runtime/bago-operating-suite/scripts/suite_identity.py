"""Exact installed-payload identity; hashes are integrity evidence, not signatures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import stat

from suite_safety import collision_key, read_json, reject_links, safe_rel

IDENTITY_FILE = "PACKAGE_IDENTITY.json"


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def inventory(skill: Path) -> list[dict]:
    """Bounded per-file reads; not an atomic snapshot of a concurrent filesystem."""
    reject_links(skill)
    skill = skill.resolve(strict=True)
    files, seen, total = [], set(), 0
    for path in sorted(skill.rglob("*"), key=lambda p: p.relative_to(skill).parts):
        reject_links(path)
        relative = path.relative_to(skill)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_dir():
            continue
        name = safe_rel(relative.as_posix()).as_posix()
        if name == IDENTITY_FILE:
            continue
        key = collision_key(name)
        if key in seen:
            raise ValueError("case-colliding payload path: " + name)
        seen.add(key)
        before = path.stat()
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("payload contains a nonregular file: " + name)
        total += before.st_size
        if total > 100_000_000 or len(files) >= 10000:
            raise ValueError("installed payload exceeds identity budget")
        with path.open("rb") as stream:
            data = stream.read(before.st_size + 1)
        after = path.stat()
        attrs = ("st_size", "st_mtime_ns", "st_ino", "st_dev")
        if (len(data) != before.st_size
                or any(getattr(before, a) != getattr(after, a) for a in attrs)):
            raise ValueError("payload changed while reading: " + name)
        files.append({"path": name, "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
    return files


def current_identity(skill: Path) -> dict:
    skill = Path(skill)
    metadata = read_json(skill / IDENTITY_FILE)
    required = {"schema", "package_id", "display_name", "version", "candidate", "release_id",
                "base_manifest_sha256", "files"}
    if (not isinstance(metadata, dict) or set(metadata) != required
            or metadata["schema"] != "bago.suite.installed-payload.v1"
            or metadata["package_id"] != "bago-operating-suite"
            or metadata["display_name"] != "BAGO Operating Suite 1.4.8"
            or metadata["version"] != "1.4.8"
            or metadata["candidate"] != "UNIFIED-CODEX-ENTRYPOINT"
            or metadata["release_id"] != "BAGO-SUITE-148-UNIFIED-CODEX-20261104"
            or metadata["base_manifest_sha256"] != "88a5c9ef9bf1ad422a58cda61c5c3e1e4e28a20fdb28c85aad15f9b5a8fedbdd"):
        raise ValueError("invalid installed Suite identity")
    actual = inventory(skill)
    if metadata["files"] != actual:
        raise ValueError("installed payload changed: missing, altered or unexpected file")
    metadata_hash = hashlib.sha256((skill / IDENTITY_FILE).read_bytes()).hexdigest()
    digest = hashlib.sha256(_canonical({"identity_sha256": metadata_hash,
                                        "files": actual})).hexdigest()
    return {"schema": "bago.suite.candidate-identity.v1",
            **{k: metadata[k] for k in ("package_id", "display_name", "version", "candidate", "release_id")},
            "payload_sha256": digest, "payload_files": len(actual) + 1,
            "identity_sha256": metadata_hash,
            "scope": "exact installed skill bytes; unsigned integrity, not publisher authentication"}
