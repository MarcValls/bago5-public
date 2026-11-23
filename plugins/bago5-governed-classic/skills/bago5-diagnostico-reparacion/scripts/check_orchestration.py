#!/usr/bin/env python3
"""Comprueba superficies de orquestacion disponibles sin abrir un REPL."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from bago_paths import choose_candidate


def _run(engine_root: Path, command: list[str], timeout: int) -> dict:
    try:
        result = subprocess.run(
            [sys.executable, *command],
            cwd=engine_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        return {"command": " ".join(command), "ok": result.returncode == 0, "rc": result.returncode, "output": output}
    except subprocess.TimeoutExpired:
        return {"command": " ".join(command), "ok": False, "rc": 124, "output": f"timeout tras {timeout}s"}
    except OSError as exc:
        return {"command": " ".join(command), "ok": False, "rc": 127, "output": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke de orquestacion BAGO por capacidades")
    parser.add_argument("--root", help="Raiz monorepo, backend o runtime")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    candidate = choose_candidate(args.root)
    engine_root = Path(candidate.engine_root)
    capabilities = set(candidate.capabilities or [])
    checks: list[dict] = []
    commands: list[list[str]] = []
    if "cli" in capabilities:
        help_check = _run(engine_root, ["bago_core/cli.py", "--help"], args.timeout)
        checks.append(help_check)
        help_text = help_check["output"]
        if "llm" in help_text:
            llm_help = _run(engine_root, ["bago_core/cli.py", "llm", "--help"], args.timeout)
            checks.append(llm_help)
            if "list" in llm_help["output"]:
                commands.append(["bago_core/cli.py", "llm", "list"])
        if "exec" in help_text:
            commands.extend(["bago_core/cli.py", "exec", slash] for slash in ("/status", "/models", "/doctor"))
    elif "legacy-chat" in capabilities:
        commands.append([".bago/tools/bago_chat.py", "--help"])
    else:
        checks.append({"command": "discover", "ok": False, "rc": 2, "output": "sin superficie de orquestacion conocida"})
    checks.extend(_run(engine_root, command, args.timeout) for command in commands)
    result = {"engine_root": str(engine_root), "checks": checks, "ok": all(item["ok"] for item in checks)}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Orquestacion: {engine_root}")
        for item in checks:
            print(f"[{'OK' if item['ok'] else 'FAIL'}] {item['command']} (rc={item['rc']})")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
