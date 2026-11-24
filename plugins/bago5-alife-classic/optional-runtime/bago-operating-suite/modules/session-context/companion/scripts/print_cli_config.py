"""Print a native CLI hooks.json proposal. Never install, merge or trust it."""
from __future__ import annotations

import json
from pathlib import Path
import shlex
import shutil
import sys


def configuration() -> dict:
    script = Path(__file__).resolve().parents[1] / "hooks/session_start.py"
    if sys.platform == "win32":
        # Simple command-name + quoted script path works without a plugin env var.
        # Refuse interpolation characters instead of guessing shell semantics.
        if any(c in str(script) for c in '$`%!"\r\n\0'):
            raise ValueError("Move the companion to a path without shell interpolation characters")
        runner = "py -3" if shutil.which("py") else "python"
        command = f'{runner} -B -I "{script}"'
        handler = {"type": "command", "command": command, "commandWindows": command}
    else:
        command = " ".join(shlex.quote(x) for x in (sys.executable, "-B", "-I", str(script)))
        handler = {"type": "command", "command": command}
    handler.update(timeout=5, additionalContextLimit=2500,
                   statusMessage="Inspeccionando contexto BAGO (solo lectura)")
    return {"description": "BAGO SessionStart CLI: review and trust this exact definition in /hooks.",
            "hooks": {"SessionStart": [{"matcher": "^(startup|resume|clear|compact|fork)$",
                                        "hooks": [handler]}]}}


if __name__ == "__main__":
    print(json.dumps(configuration(), ensure_ascii=True, indent=2))
