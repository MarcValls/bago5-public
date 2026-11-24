#!/usr/bin/env python3
"""Smoke test BAGO por capacidades para fuente o runtime."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from bago_paths import choose_candidate


@dataclass
class Check:
    name: str
    status: str
    detail: str


def _run(engine_root: Path, args: list[str], timeout: int) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [sys.executable, *args],
            cwd=engine_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        return result.returncode, output
    except subprocess.TimeoutExpired:
        return 124, f"timeout tras {timeout}s"
    except OSError as exc:
        return 127, str(exc)


def diagnose(root: str | None, timeout: int) -> dict:
    candidate = choose_candidate(root)
    engine_root = Path(candidate.engine_root)
    checks: list[Check] = []

    capabilities = set(candidate.capabilities or [])
    has_entrypoint = bool(capabilities & {"cli", "launcher", "legacy-chat", "legacy-validate"})
    checks.append(Check("structure", "OK" if has_entrypoint else "FAIL", ", ".join(sorted(capabilities)) or "sin entrypoint conocido"))

    commands: list[tuple[str, list[str], tuple[str, ...]]] = []
    if "launcher" in capabilities:
        commands.append(("version", ["bago_core/launcher.py", "--version"], ("bago",)))
    elif "cli" in capabilities:
        commands.append(("version", ["bago_core/cli.py", "--version"], ("bago",)))
    else:
        checks.append(Check("version", "OK" if candidate.version != "unknown" else "WARN", f"metadata={candidate.version}"))

    cli_help = ""
    if "cli" in capabilities:
        help_rc, cli_help = _run(engine_root, ["bago_core/cli.py", "--help"], timeout)
        checks.append(Check("cli-help", "OK" if help_rc == 0 else "FAIL", cli_help[-500:] or f"rc={help_rc}"))
        if "validate" in cli_help:
            commands.append(("validate", ["bago_core/cli.py", "validate"], ("pass", "ok")))
        else:
            checks.append(Check("validate", "SKIP", "comando no anunciado por la CLI"))
        if "exec" in cli_help:
            commands.append(("doctor", ["bago_core/cli.py", "exec", "/doctor"], ("listo", "ready", "ok")))
        else:
            checks.append(Check("doctor", "SKIP", "comando headless no anunciado por la CLI"))
    elif "legacy-validate" in capabilities:
        commands.append(("validate", [".bago/tools/bago_validate.py"], ("pass", "ok")))
        checks.append(Check("doctor", "SKIP", "layout heredado sin doctor headless conocido"))
    else:
        checks.extend((Check("validate", "SKIP", "sin validador conocido"), Check("doctor", "SKIP", "sin doctor conocido")))

    for name, command, expected_any in commands:
        rc, output = _run(engine_root, command, timeout)
        normalized = output.casefold()
        status = "OK" if rc == 0 and any(expected in normalized for expected in expected_any) else "FAIL"
        tail = output[-800:] if output else f"sin salida; rc={rc}"
        checks.append(Check(name, status, tail))

    if candidate.git_head:
        status = "WARN" if candidate.git_changes else "OK"
        detail = f"{candidate.git_branch}@{candidate.git_head}; cambios={candidate.git_changes}"
        checks.append(Check("git", status, detail))

    return {
        "candidate": asdict(candidate),
        "checks": [asdict(item) for item in checks],
        "ok": not any(item.status == "FAIL" for item in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico rapido BAGO por capacidades")
    parser.add_argument("--root", help="Raiz monorepo, backend o runtime")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = diagnose(args.root, args.timeout)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        candidate = result["candidate"]
        print(f"BAGO {candidate['version']} | {candidate['kind']} | {candidate['engine_root']}")
        for check in result["checks"]:
            detail = check["detail"].splitlines()[-1] if check["detail"] else ""
            print(f"[{check['status']:4}] {check['name']:10} {detail}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
