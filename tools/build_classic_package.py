#!/usr/bin/env python3
"""Build reproducible Platform or local-client archives from one Classic source.

Does not install a plugin, connect OAuth, change permissions or publish a release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins" / "bago5-alife-classic"


def build(variant: str, destination: Path) -> dict:
    files = {}
    for path in sorted(SOURCE.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlinks are not allowed: {path}")
        if path.is_file():
            relative = path.relative_to(SOURCE).as_posix()
            if any(part in {".git", "__pycache__", "node_modules"} for part in path.parts):
                raise ValueError(f"Unexpected build input: {relative}")
            files[relative] = path.read_bytes()
    manifest = json.loads(files["plugin.json"])
    original_version = manifest["version"]
    version = original_version
    if variant == "local":
        version = original_version + ".local.1"
        manifest["version"] = version
        extension = manifest["extensions"]["com.openai"]
        # Review metadata belongs to the one-server Platform submission only.
        extension.pop("review", None)
        extension.pop("publication", None)
        servers = json.loads(files["mcp.json"])
        # Local hosts register their own redirect URI; the provided client is for Platform.
        servers["mcpServers"]["alife-memoria-viva"]["extensions"]["com.openai"]["auth"]["client"] = {
            "mode": "dcr"
        }
        servers["mcpServers"]["alife-gestor"] = {
            "type": "streamable-http",
            "url": "https://alifememories.com/mcp/gestor",
            "extensions": {"com.openai": {"auth": {
                "type": "oauth", "client": {"mode": "dcr"},
                "baseScopes": ["manager.read"],
                "defaultScopes": ["manager.read"],
            }}},
        }
        files["mcp.json"] = (json.dumps(servers, ensure_ascii=False, indent=2) + "\n").encode()
        for name in ["skills/bago5/SKILL.md", "skills/bago5/agents/openai.yaml",
                     "skills/bago5/references/CATALOGO_HABILIDADES.json",
                     "skills/bago5/references/ROUTES.json"]:
            files[name] = files[name].replace(original_version.encode(), version.encode())
        files["plugin.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / f"{manifest['name']}-{version}.zip"
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 11, 27, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(output) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise ValueError(f"Archive integrity failure: {bad_file}")
        if set(archive.namelist()) != set(files):
            raise ValueError("Archive inventory mismatch")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n")
    return {"variant": variant, "version": version, "archive": str(output),
            "bytes": output.stat().st_size, "sha256": digest,
            "files": len(files), "skills": sum(name.startswith("skills/") and name.count("/") == 2
            and name.endswith("/SKILL.md") for name in files)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=("platform", "local", "all"), default="platform")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    variants = ("platform", "local") if args.variant == "all" else (args.variant,)
    print(json.dumps([build(item, args.output_dir) for item in variants], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
