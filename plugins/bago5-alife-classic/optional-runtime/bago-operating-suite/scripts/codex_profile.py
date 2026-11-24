#!/usr/bin/env python3
"""Run Codex CLI with only this BAGO5 Unified entry skill enabled.

This creates/updates a dedicated Codex configuration profile. It never edits the
base config.toml or removes skills from their source directories.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROFILE = "bago5-operating-suite-only"
PROFILE_HEADER = "# Managed by BAGO5 Unified; regenerate with codex_profile.py."
PROMPT = "List the skills available to this Codex session."
SUITE_SKILL_NAMES = {
    "bago5-runtime-operating-suite",
    "bago5-governed-classic:bago5-runtime-operating-suite",
    "bago5-local-gobierno",
    "bago5-governed-classic:bago5-local-gobierno",
    "bago-operating-suite",
    "bago-operating-suite:bago-operating-suite",
}


def codex_home(value: Path | None) -> Path:
    if value:
        return value.expanduser().resolve()
    if os.environ.get("CODEX_HOME"):
        return Path(os.environ["CODEX_HOME"]).expanduser().resolve()
    return Path.home() / ".codex"


def run_prompt_input(codex: str, home: Path, profile: str | None = None) -> list[dict[str, str]]:
    command = [codex]
    if profile:
        command += ["--profile", profile]
    command += ["--config", "skills.max_context_tokens=10000", "--no-daemon", "debug", "prompt-input", PROMPT]
    env = os.environ.copy()
    env["CODEX_HOME"] = str(home)
    completed = subprocess.run(command, env=env, capture_output=True, text=True, timeout=120)
    if completed.returncode:
        raise RuntimeError(f"Codex discovery failed ({completed.returncode}): {completed.stderr[-2000:]}")
    try:
        messages = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Codex discovery returned non-JSON output") from exc
    for message in messages:
        for item in message.get("content", []):
            text = item.get("text", "")
            if item.get("type") != "input_text" or "<skills_instructions>" not in text:
                continue
            if re.search(r"(?i)(warning[^\n]*skills?|skills?[^\n]*omitted|skills?[^\n]*truncated)", text):
                raise RuntimeError("Codex reports a shortened or incomplete skill catalog; refusing allowlist generation")
            roots = {key: path.strip().strip("`") for key, path in re.findall(r"(?m)^- `(r\d+)` = (.+)$", text)}
            skills: list[dict[str, str]] = []
            for name, root_id, relative in re.findall(r"(?m)^- ([A-Za-z0-9_-]+(?::[A-Za-z0-9_-]+)?): .*?\(file: (r\d+)/([^\)]+)\)$", text):
                if root_id not in roots:
                    raise RuntimeError(f"skill references unknown path root: {root_id}")
                path = Path(roots[root_id], relative.replace("/", os.sep)).resolve()
                skills.append({"name": name, "path": str(path)})
            return skills
    raise RuntimeError("Codex prompt input did not contain the skill catalog")


def profile_bytes(skills: list[dict[str, str]], suite_skill_md: Path) -> tuple[bytes, int]:
    expected = suite_skill_md.resolve()
    matches = [skill for skill in skills if Path(skill["path"]).resolve() == expected and skill["name"] in SUITE_SKILL_NAMES]
    if len(matches) != 1:
        raise RuntimeError(f"expected one discovered bago5-local-gobierno at {expected}; found {len(matches)}")
    seen: set[str] = set()
    lines = [PROFILE_HEADER, "skills.max_context_tokens = 10000", ""]
    disabled = 0
    for skill in skills:
        path = str(Path(skill["path"]).resolve())
        if path in seen:
            continue
        seen.add(path)
        enabled = path == str(expected)
        lines += ["[[skills.config]]", "path = " + json.dumps(path, ensure_ascii=False), "enabled = " + ("true" if enabled else "false"), ""]
        disabled += int(not enabled)
    return ("\n".join(lines)).encode("utf-8"), disabled


def prepare(home: Path, suite_skill_md: Path, codex: str) -> dict[str, object]:
    home.mkdir(parents=True, exist_ok=True)
    profile_path = home / f"{PROFILE}.config.toml"
    if profile_path.exists() and not profile_path.read_text(encoding="utf-8").startswith(PROFILE_HEADER):
        raise FileExistsError(f"profile exists and is not suite-managed: {profile_path}")
    before = run_prompt_input(codex, home)
    data, disabled = profile_bytes(before, suite_skill_md)
    fd, temp_name = tempfile.mkstemp(prefix="bago-suite-profile-", suffix=".toml", dir=home)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, profile_path)
    finally:
        temporary.unlink(missing_ok=True)
    after = run_prompt_input(codex, home, PROFILE)
    expected = str(suite_skill_md.resolve())
    visible = [skill for skill in after if str(Path(skill["path"]).resolve()) == expected and skill["name"] in SUITE_SKILL_NAMES]
    if len(after) != 1 or len(visible) != 1:
        raise RuntimeError(f"fail-closed: expected only bago5-local-gobierno after profile; visible skills: {[s['name'] for s in after]}")
    return {
        "schema": "bago.skills_suite.codex_profile_receipt.v1",
        "profile": PROFILE,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "codex_executable": codex,
        "codex_home": str(home),
        "enabled_skill": {"name": visible[0]["name"], "path": expected},
        "disabled_skill_count": disabled,
        "catalog_before_count": len(before),
        "catalog_after": [skill["name"] for skill in after],
        "profile_sha256": hashlib.sha256(profile_path.read_bytes()).hexdigest(),
        "governance_scope": "codex_cli_profile_only",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run"), help="prepare/verify the profile, or launch Codex through it")
    parser.add_argument("--codex-home", type=Path)
    parser.add_argument("--skill-md", type=Path, help="skill entrypoint; defaults to CODEX_HOME/skills/bago-operating-suite/SKILL.md")
    parser.add_argument("--codex", default=shutil.which("codex") or "codex", help="Codex CLI executable")
    args, codex_args = parser.parse_known_args()
    args.codex_args = codex_args
    try:
        home = codex_home(args.codex_home)
        skill_md = (args.skill_md or home / "skills" / "bago-operating-suite" / "SKILL.md").resolve(strict=True)
        if not skill_md.is_file():
            raise FileNotFoundError(f"suite entry skill is not a file: {skill_md}")
        receipt = prepare(home, skill_md, args.codex)
        print(json.dumps(receipt, ensure_ascii=False, indent=2), flush=True)
        if args.command == "run":
            forwarded = args.codex_args
            if forwarded and forwarded[0] == "--":
                forwarded = forwarded[1:]
            if not forwarded:
                raise ValueError("run requires Codex arguments after --, for example: run -- exec 'prompt'")
            env = os.environ.copy()
            env["CODEX_HOME"] = str(home)
            return subprocess.call([args.codex, "--profile", PROFILE, *forwarded], env=env)
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
