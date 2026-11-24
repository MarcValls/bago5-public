"""Package contracts for the governed MCP adapter; no remote service is called."""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
TARGET = "skills/bago5-alife-vault/SKILL.md"


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class AlifeVaultIntegrationTests(unittest.TestCase):
    def test_catalog_resolves_the_complete_public_and_local_skill_sets(self):
        entries = read_json("skills/bago5/references/CATALOGO_HABILIDADES.json")["skills"]
        public = [item for item in entries if item["scope"] == "publica"]
        local = [item for item in entries if item["scope"] == "local"]
        self.assertEqual((len(public), len(local)), (64, 13))
        self.assertEqual(len(entries), len(public) + len(local))
        self.assertEqual(len(entries), len({item["new_name"] for item in entries}))
        discovered = {path.relative_to(ROOT).as_posix()
                      for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({item["new_path"] for item in entries}, discovered)
        for item in entries:
            with self.subTest(skill=item["new_name"]):
                path = ROOT / item["new_path"]
                self.assertTrue(path.is_file(), item["new_path"])
                frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
                match = re.search(r"(?m)^name:\s*([^\r\n]+)$", frontmatter)
                self.assertIsNotNone(match)
                self.assertEqual(match[1].strip().strip("\"'"), item["new_name"])
                self.assertEqual(item["invocation"], "$" + item["new_name"])

    def test_single_canonical_route(self):
        catalog = read_json("skills/bago5/references/ROUTES.json")
        entries = [item for item in catalog["skill_invocations"] if item["target"] == TARGET]
        self.assertEqual([item["invoke"] for item in entries], ["$bago5-alife-vault"])
        self.assertIn("sin_herramientas", next(f for f in read_json("skills/bago5/references/secuencias.json") if f["id"] == "archivo")["next"])

    def test_mcp_adapter_does_not_ship_the_replaced_local_vault_transport(self):
        self.assertFalse((ROOT / "optional-runtime/alife-vault").exists())
        skill = ROOT / "skills/bago5-alife-vault"
        self.assertEqual({p.relative_to(skill).as_posix() for p in skill.rglob("*") if p.is_file()},
                         {"SKILL.md", "assets/alife.png", "agents/openai.yaml", "scripts/vault_bytes.py",
                          "tests/test_vault_bytes.py", "references/vault-protocol.md",
                          "references/source-provenance.json"})
        provenance = read_json("skills/bago5-alife-vault/references/source-provenance.json")
        self.assertEqual(provenance["source_version"], "1.0.4")
        for item in provenance["files"]:
            data = (skill / item["packaged_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item["packaged_sha256"])


if __name__ == "__main__":
    unittest.main()
