#!/usr/bin/env python3
"""Localiza instalaciones BAGO actuales sin modificar el sistema."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class BagoCandidate:
    root: str
    engine_root: str
    kind: str
    version: str
    roles: list[str]
    git_branch: str = ""
    git_head: str = ""
    git_commit_date: str = ""
    git_changes: int = 0
    capabilities: list[str] | None = None


def _resolve(path: Path) -> Path:
    try:
        return path.expanduser().resolve()
    except (OSError, RuntimeError):
        return path.expanduser().absolute()


def _is_engine(path: Path) -> bool:
    return any(
        marker.is_file()
        for marker in (
            path / "bago_core" / "cli.py",
            path / "bago_core" / "launcher.py",
            path / ".bago" / "tools" / "bago_chat.py",
            path / ".bago" / "tools" / "bago_validate.py",
        )
    )


def detect_capabilities(root: Path, engine_root: Path) -> list[str]:
    probes = {
        "cli": engine_root / "bago_core" / "cli.py",
        "launcher": engine_root / "bago_core" / "launcher.py",
        "legacy-chat": engine_root / ".bago" / "tools" / "bago_chat.py",
        "legacy-validate": engine_root / ".bago" / "tools" / "bago_validate.py",
        "session-manager": engine_root / ".bago" / "core" / "session_manager.py",
        "repl": engine_root / ".bago" / "chat" / "repl.py",
        "frontend-source": root / "frontend" / "src",
        "ui-dist": engine_root / "ui-react" / "dist" / "index.html",
        "powershell-launcher": engine_root / "bago.ps1",
        "git": root / ".git",
    }
    return sorted(name for name, path in probes.items() if path.exists())


def resolve_layout(path: str | Path) -> tuple[Path, Path, str] | None:
    """Devuelve (raiz_logica, engine_root, tipo) para layouts soportados."""
    candidate = _resolve(Path(path))
    if _is_engine(candidate / "backend"):
        return candidate, candidate / "backend", "monorepo"
    if candidate.name.casefold() == "backend" and _is_engine(candidate):
        parent = candidate.parent
        if (parent / ".git").exists() or (parent / "frontend").is_dir():
            return parent, candidate, "monorepo"
    if _is_engine(candidate):
        kind = "runtime" if "program files" in str(candidate).casefold() else "backend"
        return candidate, candidate, kind
    return None


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def read_install_roles() -> dict[str, str]:
    role_files = [
        Path.home() / ".bago" / "install_selection.json",
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        / "BAGO"
        / "install_selection.json",
    ]
    roles: dict[str, str] = {}
    for role_file in role_files:
        raw_roles = _read_json(role_file).get("roles", {})
        if not isinstance(raw_roles, dict):
            continue
        for name, value in raw_roles.items():
            if isinstance(value, dict) and value.get("path"):
                roles[str(name)] = str(_resolve(Path(value["path"])))
    return roles


def _version(root: Path, engine_root: Path) -> str:
    version_file = engine_root / "release_version.txt"
    if version_file.is_file():
        try:
            return version_file.read_text(encoding="utf-8-sig").strip()
        except OSError:
            pass
    for package_file in (root / "package.json", engine_root / "package.json"):
        version = _read_json(package_file).get("version")
        if version:
            return str(version)
    return "unknown"


def _git_info(root: Path) -> tuple[str, str, str, int]:
    git_root = root if (root / ".git").exists() else None
    if git_root is None:
        return "", "", "", 0

    def run(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=git_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    branch = run("branch", "--show-current")
    head = run("rev-parse", "--short=12", "HEAD")
    commit_date = run("log", "-1", "--date=iso-strict", "--format=%cd")
    changes = len([line for line in run("status", "--porcelain=v1").splitlines() if line])
    return branch, head, commit_date, changes


def _version_key(version: str) -> tuple[int, ...]:
    numbers = [int(item) for item in re.findall(r"\d+", version)]
    return tuple(numbers or [-1])


def _seed_paths() -> Iterable[Path]:
    for name in ("BAGO_ROOT", "BAGO_HOME", "BAGO_MOTOR_ROOT"):
        value = os.environ.get(name)
        if value:
            yield Path(value)

    cwd = Path.cwd()
    yield cwd
    yield from cwd.parents

    roles = read_install_roles()
    for value in roles.values():
        yield Path(value)

    home = Path.home()
    try:
        for child in home.iterdir():
            if child.is_dir() and re.search(r"(?i)bago|bag4", child.name):
                yield child
    except OSError:
        pass

    desktop = home / "Desktop"
    if desktop.is_dir():
        try:
            for child in desktop.iterdir():
                if child.is_dir() and re.search(r"(?i)bago|bag4", child.name):
                    yield child
                    yield child / "BAGO"
        except OSError:
            pass

    local_app_data = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
    known_paths = [
        local_app_data / "BAGO",
        home / ".local" / "share" / "BAGO",
        Path("/opt/BAGO"),
        Path("/usr/local/lib/BAGO"),
    ]
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        known_paths.append(program_files / "BAGO")
    for known in known_paths:
        yield known


def discover_candidates() -> list[BagoCandidate]:
    roles = read_install_roles()
    seen: set[str] = set()
    found: list[BagoCandidate] = []
    for raw_path in _seed_paths():
        layout = resolve_layout(raw_path)
        if layout is None:
            continue
        root, engine_root, kind = layout
        key = os.path.normcase(str(engine_root))
        if key in seen:
            continue
        seen.add(key)
        candidate_roles = [
            name
            for name, value in roles.items()
            if os.path.normcase(value) in {os.path.normcase(str(root)), key}
        ]
        branch, head, commit_date, changes = _git_info(root)
        found.append(
            BagoCandidate(
                root=str(root),
                engine_root=str(engine_root),
                kind=kind,
                version=_version(root, engine_root),
                roles=sorted(candidate_roles),
                git_branch=branch,
                git_head=head,
                git_commit_date=commit_date,
                git_changes=changes,
                capabilities=detect_capabilities(root, engine_root),
            )
        )
    return sorted(
        found,
        key=lambda item: (
            "active" in item.roles,
            _version_key(item.version),
            item.git_commit_date,
        ),
        reverse=True,
    )


def choose_candidate(path: str | None = None, *, prefer_source: bool = False) -> BagoCandidate:
    if path:
        layout = resolve_layout(path)
        if layout is None:
            raise SystemExit(f"No es una copia BAGO compatible: {path}")
        root, engine_root, kind = layout
        branch, head, commit_date, changes = _git_info(root)
        roles = read_install_roles()
        candidate_roles = [name for name, value in roles.items() if _resolve(Path(value)) in {root, engine_root}]
        return BagoCandidate(
            root=str(root),
            engine_root=str(engine_root),
            kind=kind,
            version=_version(root, engine_root),
            roles=candidate_roles,
            git_branch=branch,
            git_head=head,
            git_commit_date=commit_date,
            git_changes=changes,
            capabilities=detect_capabilities(root, engine_root),
        )

    candidates = discover_candidates()
    if not candidates:
        raise SystemExit("No se ha localizado ninguna copia BAGO compatible.")
    if prefer_source:
        for candidate in candidates:
            if candidate.kind == "monorepo":
                return candidate
        for candidate in candidates:
            if candidate.git_head:
                return candidate
    for candidate in candidates:
        if "active" in candidate.roles:
            return candidate
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Localiza copias BAGO compatibles")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    candidates = discover_candidates()
    if args.json:
        print(json.dumps([asdict(item) for item in candidates], indent=2, ensure_ascii=False))
    else:
        if not candidates:
            print("No se localizaron copias BAGO compatibles.")
            return 1
        for item in candidates:
            roles = ",".join(item.roles) or "-"
            git = f"{item.git_branch}@{item.git_head}" if item.git_head else "-"
            caps = ",".join(item.capabilities or [])
            print(f"{item.version:8} {item.kind:10} roles={roles:12} git={git:24} caps={caps} {item.engine_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
