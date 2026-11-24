"""Synthetic integration demo; creates only a disposable fixture, never installs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = Path(__file__).resolve().parents[1]


def tree(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            if p.is_file() else "directory" for p in sorted(root.rglob("*"))}


def main():
    with tempfile.TemporaryDirectory(prefix="bago-session-demo-") as temporary:
        root = Path(temporary) / "proyecto con espacios"
        root.mkdir()
        raw = (BASE / "schemas/project-context-structure.v1.json").read_bytes()
        structure = json.loads(raw)
        spec = root / ".bago/CONTEXT_STRUCTURE.json"
        spec.parent.mkdir()
        spec.write_bytes(raw)
        existing = root / structure["artifacts"][0]["path"]
        existing.parent.mkdir()
        existing.write_text("# Synthetic fixture\nLifecycle: PROPOSED\nNo host task is authorized.\n", encoding="utf-8")
        before = tree(root)
        event = {"hook_event_name": "SessionStart", "source": "startup",
                 "session_id": "SYNTHETIC-DEMO", "cwd": str(root)}
        run = subprocess.run([sys.executable, "-B", "-I", str(BASE / "hooks/session_start.py")],
                             input=json.dumps(event).encode(), capture_output=True, timeout=5)
        after = tree(root)
        output = json.loads(run.stdout)
        report = json.loads(output["hookSpecificOutput"]["additionalContext"].split("\n", 1)[1])
        passed = (run.returncode == 0 and not run.stderr and before == after
                  and report["status"] == "REVIEW_REQUIRED"
                  and [r["status"] for r in report["artifacts"]]
                  == ["PRESENT_REVIEW_REQUIRED", "MISSING", "MISSING"])
        print(json.dumps({"demo": "BAGO-SCR-001", "event_origin": "SYNTHETIC",
                          "runtime": sys.version, "input": event, "hook_output": output,
                          "before": before, "after": after, "unchanged": before == after,
                          "result": "PASS" if passed else "FAIL", "codex_cli": "NOT_RUN"},
                         ensure_ascii=False, indent=2))
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
