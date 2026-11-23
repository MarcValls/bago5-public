#!/usr/bin/env python3
"""Compara hashes clave entre una fuente BAGO y su runtime. Solo lectura."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

from bago_paths import choose_candidate, discover_candidates


DEFAULT_FILES = (
    "release_version.txt",
    "versions.json",
    "package.json",
    "bago_core/cli.py",
    "bago_core/launcher.py",
    ".bago/tools/bago_chat.py",
    ".bago/tools/bago_validate.py",
    ".bago/core/session_manager.py",
    ".bago/chat/repl.py",
    ".bago/api/api_dispatch.py",
    ".bago/core/embedding_store.py",
    "electron/window-service.cjs",
    "ui-react/dist/index.html",
    "bago.ps1",
    "bago.cmd",
)


def _hash(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _pick_source(path: str | None):
    if path:
        return choose_candidate(path, prefer_source=True)
    return choose_candidate(prefer_source=True)


def _pick_runtime(path: str | None):
    if path:
        return choose_candidate(path)
    candidates = discover_candidates()
    for candidate in candidates:
        if "active" in candidate.roles:
            return candidate
    for candidate in candidates:
        if candidate.kind == "runtime":
            return candidate
    raise SystemExit("No se ha localizado el runtime activo.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara fuente y runtime BAGO")
    parser.add_argument("--source")
    parser.add_argument("--runtime")
    parser.add_argument("--file", action="append", help="Ruta relativa a comparar; repetible")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true", help="Devuelve rc=1 si hay diferencias")
    args = parser.parse_args()

    source = _pick_source(args.source)
    runtime = _pick_runtime(args.runtime)
    source_root = Path(source.engine_root)
    runtime_root = Path(runtime.engine_root)
    rows = []
    for relative in args.file or DEFAULT_FILES:
        left = _hash(source_root / relative)
        right = _hash(runtime_root / relative)
        if left is None and right is None:
            continue
        state = "MATCH" if left is not None and left == right else "MISSING" if left is None or right is None else "DIFF"
        rows.append({"file": relative, "state": state, "source": left, "runtime": right})

    result = {
        "source": asdict(source),
        "runtime": asdict(runtime),
        "summary": {
            "match": sum(item["state"] == "MATCH" for item in rows),
            "diff": sum(item["state"] == "DIFF" for item in rows),
            "missing": sum(item["state"] == "MISSING" for item in rows),
        },
        "files": rows,
    }
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"SOURCE  {source.version} {source_root}")
        print(f"RUNTIME {runtime.version} {runtime_root}")
        for item in rows:
            print(f"[{item['state']:7}] {item['file']}")
        print("SUMMARY " + " ".join(f"{key}={value}" for key, value in result["summary"].items()))

    divergent = result["summary"]["diff"] + result["summary"]["missing"]
    return 1 if args.strict and divergent else 0


if __name__ == "__main__":
    raise SystemExit(main())
