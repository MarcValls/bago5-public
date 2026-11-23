"""Distribution checks for the public Codex marketplace (standard library only)."""
import importlib.util
import json
import os
import tempfile
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "bago5-governed-classic"


def load_json(path):
    return json.loads(path.read_bytes())


class PublicRelease(unittest.TestCase):
    def test_marketplace_and_version(self):
        entries = load_json(ROOT / ".agents/plugins/marketplace.json")["plugins"]
        self.assertEqual(len({entry["name"] for entry in entries}), len(entries))
        for entry in entries:
            manifest = ROOT / entry["source"]["path"] / ".codex-plugin/plugin.json"
            self.assertEqual(load_json(manifest)["name"], entry["name"])
        result = subprocess.run([sys.executable, "-B", str(PLUGIN / "scripts/bago5_version.py"), "--json"],
                                capture_output=True, text=True, check=True)
        version = json.loads(result.stdout)["package_version"]
        for path in [ROOT / "README.md", ROOT / "Instalar-BAGO5-Classic.cmd"]:
            self.assertIn("v" + version, path.read_text(encoding="utf8"))

    @unittest.skipUnless(os.name == "nt", "Windows installer")
    def test_git_long_paths_with_and_without_inherited_options(self):
        installer = (ROOT / "Instalar-BAGO5-Classic.cmd").read_text(encoding="ascii")
        start = installer.index("rem Git for Windows:")
        end = installer.index('set "MODE=asistido"', start)
        with tempfile.TemporaryDirectory() as temp:
            check = Path(temp) / "comprobar.cmd"
            check.write_text("@echo off\n" + installer[start:end] +
                             "git config --get core.longpaths\n", encoding="ascii")
            for inherited in (None, "'core.autocrlf=false'"):
                env = os.environ.copy()
                if inherited is None:
                    env.pop("GIT_CONFIG_PARAMETERS", None)
                else:
                    env["GIT_CONFIG_PARAMETERS"] = inherited
                with self.subTest(inherited=inherited):
                    result = subprocess.run(["cmd", "/d", "/c", check.name], cwd=temp,
                                            env=env, capture_output=True, text=True, check=True)
                    self.assertEqual(result.stdout.strip(), "true")

    def test_routes_and_optional_modules(self):
        route = PLUGIN / "skills/bago5-flujo-trabajo/scripts/route_suite.py"
        spec = importlib.util.spec_from_file_location("classic_workflow", route)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        policy = load_json(module.POLICY_PATH)
        for intent, settings in policy["routes"].items():
            with self.subTest(intent=intent):
                receipt = module.select(intent, settings["optional"], "test", "test")
                self.assertEqual(set(receipt["selected_modules"]),
                                 set(settings["required"] + settings["optional"]))
        routes = load_json(PLUGIN / "skills/bago5/references/ROUTES.json")
        for entry in routes["routes"]:
            self.assertTrue((PLUGIN / entry["target"]).is_file(), entry["target"])

    def test_public_mcp(self):
        servers = load_json(PLUGIN / ".mcp.json")["mcpServers"]
        self.assertEqual({entry["url"] for entry in servers.values()},
                         {"https://alifememories.com/mcp", "https://alifememories.com/mcp/gestor"})
        for entry in servers.values():
            self.assertFalse(entry.get("headers"))
        self.assertFalse((PLUGIN / ".app.json").exists())

    def test_local_links(self):
        for doc in PLUGIN.rglob("*.md"):
            for target in re.findall(r"\[[^\]\n]*\]\(([^ )#]+)(?:#[^ )]*)?\)", doc.read_text(encoding="utf8")):
                if ":" not in target:
                    self.assertTrue((doc.parent / target).exists(), f"{doc.name} -> {target}")


if __name__ == "__main__":
    unittest.main()
