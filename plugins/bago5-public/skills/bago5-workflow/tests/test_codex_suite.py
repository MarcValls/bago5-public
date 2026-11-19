"""Regression checks for incomplete catalogs, profile ownership and safe launch."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/codex_suite.py"
SPEC = importlib.util.spec_from_file_location("bago5_codex_profile", SCRIPT)
suite = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(suite)


class ProfileTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.home = Path(directory.name)
        self.entry = self.home / "bago5-workflow/SKILL.md"
        self.entry.parent.mkdir()
        self.entry.write_text("entry")
        self.selected = [("public-plugin:bago5-workflow", self.entry)]

    def message(self, line):
        text = ("<skills_instructions>\n### Skill roots\n- `r0` = `" + self.home.as_posix() +
                "`\n### Available skills\n" + line + "\n</skills_instructions>")
        return [{"role": "developer", "content": [{"type": "input_text", "text": text}]}]

    def test_qualified_name_and_invalid_inventory(self):
        entry = "- public-plugin:bago5-workflow: test (file: r0/bago5-workflow/SKILL.md)"
        self.assertEqual(suite.parse_catalog(self.message(entry)), self.selected)
        for line in [entry + "\nunknown listing format", entry + "\nSome skills were omitted.",
                     entry.replace("r0/", "r9/"), entry.replace("r0/", "r0/../"), entry + "\n" + entry]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                suite.parse_catalog(self.message(line))

    def test_run_refuses_failed_catalog_and_never_launches(self):
        with patch.object(suite, "catalog", side_effect=ValueError("incomplete")), \
             patch.object(suite, "executable", return_value="test-cli"), \
             patch.object(suite.subprocess, "call") as launched:
            result = suite.main(["run","--codex-home",str(self.home),"--skill-md",str(self.entry)])
        self.assertEqual(result, 2)
        launched.assert_not_called()
        self.assertFalse(list(self.home.glob("*.config.toml")))

    def test_postcheck_failure_and_foreign_profile_preservation(self):
        with patch.object(suite, "catalog", side_effect=[self.selected, self.selected, []]):
            with self.assertRaises(ValueError):
                suite.prepare("test-cli", self.home, self.entry)
        self.assertFalse(list(self.home.glob("*.config.toml")))
        with patch.object(suite, "catalog", return_value=self.selected):
            _, receipt = suite.prepare("test-cli", self.home, self.entry)
            target = self.home / (receipt["profile"] + ".config.toml")
            target.write_bytes(b"# custom profile\n")
            with self.assertRaises(FileExistsError):
                suite.prepare("test-cli", self.home, self.entry)
            self.assertEqual(target.read_bytes(), b"# custom profile\n")
        self.assertFalse(list(self.home.glob("bago5-probe-*")))


if __name__ == "__main__":
    unittest.main()
