#!/usr/bin/env python3
"""Detecta y corrige interpolaciones `$VAR:` invalidas en PowerShell."""
from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


DOUBLE_QUOTED = re.compile(r'"(?:[^"`]|`.)*"')
VARIABLE_COLON = re.compile(r"\$(?!\()(?P<name>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?):")
VALID_SCOPES = {"env", "global", "script", "local", "private", "using", "variable", "function", "alias"}


def fix_text(text: str) -> tuple[str, int]:
    changes = 0

    def fix_string(match: re.Match[str]) -> str:
        nonlocal changes

        def replace_variable(variable: re.Match[str]) -> str:
            nonlocal changes
            name = variable.group("name")
            if "." not in name and name.casefold() in VALID_SCOPES:
                return variable.group(0)
            changes += 1
            return f"$({name}):"

        return VARIABLE_COLON.sub(replace_variable, match.group(0))

    return DOUBLE_QUOTED.sub(fix_string, text), changes


def _backup_path(path: Path) -> Path:
    candidate = path.with_suffix(path.suffix + ".bak")
    counter = 1
    while candidate.exists():
        candidate = path.with_suffix(path.suffix + f".bak.{counter}")
        counter += 1
    return candidate


def fix_file(path: Path, *, apply: bool) -> int:
    original = path.read_text(encoding="utf-8-sig")
    updated, changes = fix_text(original)
    if not changes:
        return 0
    if not apply:
        print(f"[DRY] {path}: {changes} cambio(s)")
        return changes
    backup = _backup_path(path)
    shutil.copy2(path, backup)
    path.write_text(updated, encoding="utf-8-sig")
    print(f"[FIXED] {path}: {changes} cambio(s); backup={backup.name}")
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description="Repara interpolaciones PowerShell invalidas")
    parser.add_argument("target", type=Path)
    parser.add_argument("--apply", action="store_true", help="Aplica cambios; por defecto solo informa")
    args = parser.parse_args()
    if not args.target.exists():
        parser.error(f"no existe: {args.target}")
    files = [args.target] if args.target.is_file() else sorted(args.target.rglob("*.ps1"))
    changed = sum(fix_file(path, apply=args.apply) for path in files)
    print(f"Total: {changed} sustitucion(es); modo={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
