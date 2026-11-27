"""Preservation and distribution checks; these do not prove OAuth or host behaviour."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "plugins" / "bago5-alife-classic"
BASELINE = ROOT / "dist" / "bago5-alife-classic-0.4.60-rc.12.zip"
CHANGED = {
    "plugin.json", "skills/alife-conectar-vault/SKILL.md", "skills/bago5/SKILL.md",
    "skills/bago5/agents/openai.yaml", "skills/bago5/references/autonomia-vectores.json",
    "skills/bago5/references/CATALOGO_HABILIDADES.json", "skills/bago5/references/ROUTES.json",
    "skills/bago5/references/memory-scope.md", "skills/bago5/references/onboarding.md",
    "skills/bago5/references/operational-continuity.md", "skills/bago5/references/turn-decision.md",
    "skills/bago5-alife-vault/SKILL.md", "skills/bago5-ciclo-contexto/SKILL.md",
    "skills/bago5-contexto-sesion/SKILL.md", "skills/bago5-integridad-evidencias/SKILL.md",
    "skills/bago5-memoria/SKILL.md", "skills/bago5-memoria-viva/SKILL.md",
    "skills/bago5-memorias-conectadas/SKILL.md",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ClassicOnboardingPackage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with zipfile.ZipFile(BASELINE) as archive:
            cls.baseline = {name: archive.read(name) for name in archive.namelist()
                            if not name.endswith("/")}

    def test_all_original_files_retained_and_unrelated_bytes_unchanged(self):
        for name, content in self.baseline.items():
            with self.subTest(path=name):
                self.assertTrue((SOURCE / name).is_file())
                if name not in CHANGED:
                    self.assertEqual((SOURCE / name).read_bytes(), content)

    def test_existing_skills_preserved_and_setup_is_discoverable(self):
        before = {name.split("/")[1] for name in self.baseline
                  if name.startswith("skills/") and name.count("/") == 2 and name.endswith("/SKILL.md")}
        after = {p.parent.name for p in (SOURCE / "skills").glob("*/SKILL.md")}
        self.assertEqual(after - before, {"bago5-configurar-alife"})
        self.assertFalse(before - after)
        catalog = load(SOURCE / "skills/bago5/references/CATALOGO_HABILIDADES.json")
        names = [item["new_name"] for item in catalog["skills"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("bago5-configurar-alife", names)
        for route in load(SOURCE / "skills/bago5/references/ROUTES.json")["routes"]:
            self.assertTrue((SOURCE / route["target"]).is_file(), route["target"])

    def test_manifest_changes_are_limited_to_requested_version_and_onboarding(self):
        before = json.loads(self.baseline["plugin.json"])
        after = load(SOURCE / "plugin.json")
        self.assertRegex(after["version"], r"^0\.4\.60-rc\.13$")
        self.assertEqual(after["extensions"]["com.openai"]["onboardingSkill"],
                         "./skills/bago5-configurar-alife/SKILL.md")
        for manifest in (before, after):
            manifest.pop("version")
            manifest["extensions"]["com.openai"].pop("onboardingSkill")
            manifest["extensions"]["com.openai"]["publication"].pop("release_notes")
        self.assertEqual(before, after)

    def test_platform_connection_and_scopes_unchanged(self):
        self.assertEqual((SOURCE / "mcp.json").read_bytes(), self.baseline["mcp.json"])
        servers = load(SOURCE / "mcp.json")["mcpServers"]
        self.assertEqual(list(servers), ["alife-memoria-viva"])
        self.assertEqual(servers["alife-memoria-viva"]["url"], "https://alifememories.com/mcp")
        self.assertFalse((SOURCE / ".app.json").exists())

    def test_active_version_is_consistent(self):
        version = load(SOURCE / "plugin.json")["version"]
        catalog = load(SOURCE / "skills/bago5/references/CATALOGO_HABILIDADES.json")
        routes = load(SOURCE / "skills/bago5/references/ROUTES.json")
        self.assertEqual(catalog["version"], version)
        self.assertEqual(routes["plugin_version"], version)
        for path in ["skills/bago5/SKILL.md", "skills/bago5/agents/openai.yaml"]:
            content = (SOURCE / path).read_text(encoding="utf-8")
            self.assertIn(version, content)
            self.assertNotIn("0.4.60-rc.11", content)

    def test_all_local_links_are_present_and_contained(self):
        for document in SOURCE.rglob("*.md"):
            content = document.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]\n]*\]\(([^ )#]+)(?:#[^ )]*)?\)", content):
                if ":" in target:
                    continue
                resolved = (document.parent / target).resolve()
                with self.subTest(document=str(document), target=target):
                    self.assertTrue(resolved.is_relative_to(SOURCE.resolve()))
                    self.assertTrue(resolved.exists())

    def test_all_json_is_parseable(self):
        for path in SOURCE.rglob("*.json"):
            with self.subTest(path=str(path)):
                load(path)

    def test_archives_are_reproducible_and_do_not_modify_source(self):
        spec = importlib.util.spec_from_file_location("classic_builder", ROOT / "tools/build_classic_package.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        before = {str(p.relative_to(SOURCE)): p.read_bytes() for p in SOURCE.rglob("*") if p.is_file()}
        with tempfile.TemporaryDirectory() as temp:
            first = module.build("platform", Path(temp) / "a")
            second = module.build("platform", Path(temp) / "b")
            self.assertEqual(first["sha256"], second["sha256"])
            with zipfile.ZipFile(first["archive"]) as archive:
                self.assertEqual(set(archive.namelist()), set(before))
                for name, content in before.items():
                    self.assertEqual(archive.read(name), content)
        after = {str(p.relative_to(SOURCE)): p.read_bytes() for p in SOURCE.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_local_variant_separates_manager_and_content_authority(self):
        spec = importlib.util.spec_from_file_location("classic_builder_local", ROOT / "tools/build_classic_package.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            result = module.build("local", Path(temp))
            with zipfile.ZipFile(result["archive"]) as archive:
                manifest = json.loads(archive.read("plugin.json"))
                servers = json.loads(archive.read("mcp.json"))["mcpServers"]
                self.assertEqual(len(servers), 2)
                expected_content = copy.deepcopy(load(SOURCE / "mcp.json")["mcpServers"]["alife-memoria-viva"])
                expected_content["extensions"]["com.openai"]["auth"]["client"] = {"mode": "dcr"}
                self.assertEqual(servers["alife-memoria-viva"], expected_content)
                manager = servers["alife-gestor"]
                self.assertEqual(manager["url"], "https://alifememories.com/mcp/gestor")
                auth = manager["extensions"]["com.openai"]["auth"]
                self.assertEqual(auth["client"], {"mode": "dcr"})
                self.assertEqual(auth["defaultScopes"], ["manager.read"])
                self.assertFalse(manager.get("headers"))
                self.assertEqual(manifest["version"], "0.4.60-rc.13.local.1")
                self.assertNotIn("review", manifest["extensions"]["com.openai"])
                for name in ["skills/bago5/SKILL.md", "skills/bago5/agents/openai.yaml"]:
                    self.assertIn(manifest["version"], archive.read(name).decode())


if __name__ == "__main__":
    unittest.main()
