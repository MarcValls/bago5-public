"""Standalone, read/write-isolated regression tests for BAGO Evidence Guard.

Run with Python's standard unittest; no pytest or project dependencies required.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bago_evidence_guard as guard


class EvidenceGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="bago guard ñ con espacios ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / "código local"
        self.source.mkdir()
        (self.source / "frontend" / "src").mkdir(parents=True)
        (self.source / "logs").mkdir()
        self.css = "frontend/src/ExternalConnections.css"
        self.log = "logs/node-test-wrong-project-root-control.txt"
        (self.source / self.css).write_bytes(b".app { color: red; }\n")
        (self.source / self.log).write_bytes(b"EXPECTED_FAILED_TEST; preserved evidence\n")
        self.bindings = self.base / "bindings.json"
        self.template = self.base / "w12_template.json"
        self.report = self.base / "w12_new.json"
        self.write_json(self.bindings, {
            "schema": guard.BINDINGS_SCHEMA,
            "bindings": [{"path": self.css, "pointer": "/sources/css/sha256"},
                         {"path": self.log, "pointer": "/logs/0/sha256"}],
        })
        self.write_json(self.template, {
            "schema": "example.w12.v1", "sources": {"css": {"sha256": "__SHA256__"}},
            "logs": [{"sha256": "__SHA256__"}], "notes": "fixture"})

    @staticmethod
    def cli(argv: list[str]) -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return guard.main(argv)

    @staticmethod
    def write_json(path: Path, obj: object) -> None:
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def load_template_filled(self) -> dict:
        obj = guard.load_json(self.template)
        guard.set_pointer(obj, "/sources/css/sha256", guard.file_sha256(self.source, self.css)[0])
        guard.set_pointer(obj, "/logs/0/sha256", guard.file_sha256(self.source, self.log)[0])
        return obj

    def check_json(self, obj: dict, strict: bool = True) -> dict:
        return guard.verify_json_model(
            self.source, obj, guard.binding_config(self.bindings), strict_claims=strict)

    def test_01_seal_json_no_manual_hash_and_verify(self) -> None:
        args = ["seal-json", "--root", str(self.source), "--template", str(self.template),
                "--bindings", str(self.bindings), "--out", str(self.report)]
        self.assertEqual(self.cli(args), 0)
        self.assertTrue(self.report.is_file())
        self.assertEqual(self.cli(["verify-json", "--root", str(self.source),
                                     "--bindings", str(self.bindings), "--report", str(self.report)]), 0)
        self.assertEqual(guard.load_json(self.template)["sources"]["css"]["sha256"], "__SHA256__")

    def test_02_prevent_overwriting_existing_report(self) -> None:
        self.assertEqual(self.cli(["seal-json", "--root", str(self.source),
                                     "--template", str(self.template), "--bindings", str(self.bindings),
                                     "--out", str(self.report)]), 0)
        before = self.report.read_bytes()
        self.assertEqual(self.cli(["seal-json", "--root", str(self.source),
                                     "--template", str(self.template), "--bindings", str(self.bindings),
                                     "--out", str(self.report)]), 2)
        self.assertEqual(before, self.report.read_bytes())

    def test_03_css_65_char_redundant_d_rejected_with_diagnostic(self) -> None:
        obj = self.load_template_filled()
        original = obj["sources"]["css"]["sha256"]
        obj["sources"]["css"]["sha256"] = original[:25] + "d" + original[25:]
        found = self.check_json(obj)
        self.assertEqual(found["status"], "FAIL")
        self.assertEqual(found["failed"], 1)
        self.assertEqual(found["checks"][0]["status"], "INVALID_SHA256_FORMAT")
        self.assertEqual(found["checks"][0]["one_character_insertion_candidates"][0]["position_1_based"], 26)
        # This diagnostic never alters the supplied JSON.
        self.assertEqual(len(obj["sources"]["css"]["sha256"]), 65)

    def test_04_log_65_char_redundant_1_rejected_with_diagnostic(self) -> None:
        obj = self.load_template_filled()
        original = obj["logs"][0]["sha256"]
        obj["logs"][0]["sha256"] = original[:11] + "1" + original[11:]
        found = self.check_json(obj)
        self.assertEqual(found["status"], "FAIL")
        self.assertEqual(found["failed"], 1)
        self.assertEqual(found["checks"][1]["status"], "INVALID_SHA256_FORMAT")
        self.assertEqual(found["checks"][1]["one_character_insertion_candidates"][0]["position_1_based"], 12)

    def test_05_64_char_wrong_hash_rejected(self) -> None:
        obj = self.load_template_filled()
        obj["logs"][0]["sha256"] = "0" * 64
        self.assertEqual(self.check_json(obj)["checks"][1]["status"], "DIGEST_MISMATCH")

    def test_06_source_changed_after_receipt_rejected(self) -> None:
        obj = self.load_template_filled()
        (self.source / self.css).write_text("changed after audit\n", encoding="utf-8")
        self.assertEqual(self.check_json(obj)["checks"][0]["status"], "DIGEST_MISMATCH")

    def test_07_control_chars_in_markdown_rejected(self) -> None:
        p = self.base / "r3.md"
        p.write_bytes(b"Valid text\nBad control: \x1b[31m and \x00\n")
        with self.assertRaisesRegex(guard.GuardError, "FORBIDDEN_C0_DEL"):
            guard.check_markdown(p)

    def test_08_escaped_control_in_json_rejected(self) -> None:
        p = self.base / "r3.json"
        p.write_bytes(b'{"comment":"bad\\u0007 content"}\n')
        with self.assertRaisesRegex(guard.GuardError, "FORBIDDEN_C0_DEL"):
            guard.load_json(p)

    def test_09_duplicate_json_keys_rejected(self) -> None:
        p = self.base / "duplicate.json"
        p.write_text('{"hash":"x","hash":"y"}\n', encoding="utf-8")
        with self.assertRaisesRegex(guard.GuardError, "DUPLICATE_JSON_KEY"):
            guard.load_json(p)

    def test_10_nonstandard_json_number_rejected(self) -> None:
        p = self.base / "nan.json"
        p.write_text('{"score":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(guard.GuardError, "NON_STANDARD_JSON_NUMBER"):
            guard.load_json(p)

    def test_11_path_traversal_and_absolute_paths_rejected(self) -> None:
        for candidate in ("../private.txt", "/etc/passwd", "C:\\Users\\user\\secret.txt",
                          "frontend//src/a.css", "frontend/./src/a.css"):
            with self.subTest(path=candidate), self.assertRaises(guard.GuardError):
                guard.resolve_file(self.source, candidate)

    def test_12_symlink_rejected(self) -> None:
        target = self.base / "secret.txt"
        target.write_text("hidden", encoding="utf-8")
        link = self.source / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("Filesystem disallows symlink creation")
        with self.assertRaisesRegex(guard.GuardError, "LINK_OR_REPARSE_POINT_REJECTED"):
            guard.file_sha256(self.source, "link.txt")

    def test_13_directory_symlink_rejected(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "file.txt").write_bytes(b"x")
        link = self.source / "linked_folder"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Filesystem disallows symlink creation")
        with self.assertRaisesRegex(guard.GuardError, "LINK_OR_REPARSE_POINT_REJECTED"):
            guard.file_sha256(self.source, "linked_folder/file.txt")

    def test_14_manifest_generation_and_15_files_verify(self) -> None:
        entries = [{"path": self.css, "role": "source"}, {"path": self.log, "role": "log"}]
        for i in range(13):
            p = f"logs/passed-{i:02}.txt"
            (self.source / p).write_bytes(f"PASS {i}\n".encode())
            entries.append({"path": p, "role": "log"})
        spec = self.base / "inventory.json"
        self.write_json(spec, {"schema": guard.SPEC_SCHEMA, "files": entries})
        out = self.base / "r4_integridad"
        result = guard.create_manifest(self.source, spec, out, "BAGO_ADL")
        self.assertEqual(result["items"], 15)
        doc = guard.load_json(out / "manifest.json")
        self.assertEqual(len(guard.verify_manifest_model(self.source, doc)), 15)
        self.assertEqual((out / "informe.md").read_bytes(), guard.render_markdown(doc))
        self.assertEqual(self.cli(["verify-manifest", "--root", str(self.source),
                                     "--manifest", str(out / "manifest.json"),
                                     "--markdown", str(out / "informe.md")]), 0)
        with self.assertRaisesRegex(guard.GuardError, "OUTPUT_ALREADY_EXISTS"):
            guard.create_manifest(self.source, spec, out, "BAGO_ADL")

    def test_15_manifest_source_change_detected(self) -> None:
        spec = self.base / "inventory.json"
        self.write_json(spec, {"schema": guard.SPEC_SCHEMA,
                               "files": [{"path": self.css, "role": "source"}]})
        out = self.base / "receipt"
        guard.create_manifest(self.source, spec, out, "workspace")
        (self.source / self.css).write_bytes(b"new content\n")
        with self.assertRaisesRegex(guard.GuardError, "FILE_MISMATCH"):
            guard.verify_manifest_model(self.source, guard.load_json(out / "manifest.json"))

    def test_16_modified_manifest_detected(self) -> None:
        spec = self.base / "spec.json"
        self.write_json(spec, {"schema": guard.SPEC_SCHEMA,
                               "files": [{"path": self.css, "role": "source"}]})
        out = self.base / "receipt"
        guard.create_manifest(self.source, spec, out, "workspace")
        doc = guard.load_json(out / "manifest.json")
        doc["entries"][0]["sha256"] = "a" * 64
        self.write_json(out / "manifest.json", doc)
        with self.assertRaisesRegex(guard.GuardError, "ENTRIES_DIGEST_MISMATCH"):
            guard.verify_manifest_model(self.source, guard.load_json(out / "manifest.json"))

    def test_17_invalid_extra_hash_claim_rejected(self) -> None:
        obj = self.load_template_filled()
        obj["other_sha256"] = "1" * 64
        with self.assertRaisesRegex(guard.GuardError, "UNBOUND_HASH_CLAIMS"):
            self.check_json(obj)

    def test_18_nonempty_template_digest_cannot_be_replaced(self) -> None:
        doc = self.load_template_filled()
        with self.assertRaisesRegex(guard.GuardError, "NONEMPTY_DIGEST_PLACEHOLDER"):
            guard.set_pointer(doc, "/sources/css/sha256", "a" * 64)

    def test_19_wrong_size_field_detected(self) -> None:
        spec = self.base / "spec.json"
        self.write_json(spec, {"schema": guard.SPEC_SCHEMA,
                               "files": [{"path": self.css, "role": "source"}]})
        out = self.base / "receipt"
        guard.create_manifest(self.source, spec, out, "workspace")
        obj = guard.load_json(out / "manifest.json")
        obj["entries"][0]["size"] += 1
        obj["entries_sha256"] = guard.canonical_hash(obj["entries"])
        with self.assertRaisesRegex(guard.GuardError, "FILE_MISMATCH"):
            guard.verify_manifest_model(self.source, obj)

    def test_20_markdown_tampering_detected(self) -> None:
        spec = self.base / "spec.json"
        self.write_json(spec, {"schema": guard.SPEC_SCHEMA,
                               "files": [{"path": self.css, "role": "source"}]})
        out = self.base / "receipt"
        guard.create_manifest(self.source, spec, out, "workspace")
        with (out / "informe.md").open("a", encoding="utf-8") as f:
            f.write("\nextra\n")
        self.assertEqual(self.cli(["verify-manifest", "--root", str(self.source),
                                     "--manifest", str(out / "manifest.json"),
                                     "--markdown", str(out / "informe.md")]), 2)

    def test_21_template_empty_hash_cover_fail(self) -> None:
        obj = guard.load_json(self.template)
        outcome = self.check_json(obj)
        self.assertEqual(outcome["status"], "FAIL")
        self.assertEqual(outcome["failed"], 2)

    def test_23_explicit_15_claims_required_catches_2_only(self) -> None:
        obj = self.load_template_filled()
        self.write_json(self.report, obj)
        rc = self.cli(["verify-json", "--root", str(self.source),
                         "--bindings", str(self.bindings), "--report", str(self.report),
                         "--expected-count", "15"])
        self.assertEqual(rc, 2)

    def test_24_unbound_numerical_hash_claim_rejected(self) -> None:
        obj = self.load_template_filled()
        obj["other_sha256"] = 9
        with self.assertRaisesRegex(guard.GuardError, "UNBOUND_HASH_CLAIMS"):
            self.check_json(obj)

    def test_22_byte_only_source_allowed_no_text_assumptions(self) -> None:
        p = self.source / "logs" / "arbitrary.bin"
        p.write_bytes(b"\x00\xff\x1b\x00")
        h, size = guard.file_sha256(self.source, "logs/arbitrary.bin")
        self.assertEqual(h, __import__("hashlib").sha256(p.read_bytes()).hexdigest())
        self.assertEqual(size, 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
