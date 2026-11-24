import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / "fusion_analysis.py"
spec = importlib.util.spec_from_file_location("fusion_analysis_tests_subject", MODULE)
fusion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fusion)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def archive(name, files, status="ANALYZED", zip_hash=None):
    return {"zip": name, "id": name, "zip_sha256": zip_hash or digest(name), "status": status,
            "entries": [{"id": name + ":" + path, "path": path, "logical_path": path,
                         "sha256": digest(value), "size": len(value), "status": "ANALYZED", "issues": []}
                        for path, value in files.items()]}


def report(*archives):
    return {"schema_version": "0.2", "tool_version": "0.2.2", "archives": list(archives),
            "dependency_analysis": {"nodes": [], "edges": [], "status": "STATIC_ANALYZED_WITH_LIMITS",
                                    "summary": {"omitted_edges": 0}}}


class FusionTests(unittest.TestCase):
    def classify(self, left, right):
        result = fusion.summarize(report(left, right))
        self.assertEqual(result["status"], "PROPOSED_ONLY")
        self.assertEqual(result["automatic_actions"], [])
        return result["candidates"][0]

    def test_exact_zip_is_byte_identity_even_if_inventory_partial(self):
        left = archive("a.zip", {"a.py": "a"}, zip_hash=digest("zip"))
        right = archive("b.zip", {"a.py": "a"}, "PARTIAL", zip_hash=digest("zip"))
        item = self.classify(left, right)
        self.assertEqual(item["classification"], "IDENTICAL_ZIPS")
        self.assertEqual(item["evidence_scope"], "INCOMPLETE_INVENTORY_REVIEW")
        self.assertEqual(item["functional_compatibility"], "NOT_VERIFIED")

    def test_same_file_set_not_same_container_bytes(self):
        item = self.classify(archive("a.zip", {"main.py": "code"}), archive("b.zip", {"main.py": "code"}))
        self.assertEqual(item["classification"], "SAME_FILE_SET")
        self.assertFalse(item["evidence"]["zip_bytes_identical"])

    def test_subset_and_overlap(self):
        item = self.classify(archive("small.zip", {"common.py": "same"}),
                             archive("large.zip", {"common.py": "same", "extra.py": "more"}))
        self.assertEqual(item["classification"], "COMPLETE_INCLUSION")
        self.assertEqual(item["containment"]["contained_zip"], "small.zip")
        item = self.classify(archive("a.zip", {"common.py": "same", "a.py": "a"}),
                             archive("b.zip", {"common.py": "same", "b.py": "b"}))
        self.assertEqual(item["classification"], "SHARED_COMPONENTS")

    def test_variants_and_case_collisions(self):
        item = self.classify(archive("a.zip", {"main.py": "version a"}), archive("b.zip", {"main.py": "version b"}))
        self.assertEqual(item["classification"], "PATH_CONFLICTS")
        self.assertEqual(item["counts"]["same_path_different_hash"], 1)
        item = self.classify(archive("a.zip", {"MAIN.py": "same"}), archive("b.zip", {"main.py": "same"}))
        self.assertEqual(item["classification"], "PATH_CONFLICTS")
        self.assertEqual(item["counts"]["case_collisions"], 1)

    def test_file_directory_namespace_conflict(self):
        item = self.classify(archive("a.zip", {"module": "file"}), archive("b.zip", {"module/x.py": "code"}))
        self.assertEqual(item["classification"], "PATH_CONFLICTS")
        self.assertEqual(item["counts"]["namespace_collisions"], 1)

    def test_same_hash_different_name_is_reuse_with_references(self):
        item = self.classify(archive("a.zip", {"old.py": "same"}), archive("b.zip", {"new.py": "same"}))
        self.assertEqual(item["classification"], "REUSE_RENAMED_CONTENT")
        self.assertEqual(item["counts"]["renamed_content_groups"], 1)
        self.assertIsNone(item["automatic_action"])

    def test_partial_missing_hash_and_unsafe_path_are_not_complete_claims(self):
        left = archive("a.zip", {"a.py": "same"}, "PARTIAL")
        right = archive("b.zip", {"a.py": "same"})
        self.assertEqual(self.classify(left, right)["classification"], "INCOMPLETE_REVIEW")
        left["status"] = "ANALYZED"
        left["entries"][0]["sha256"] = None
        item = self.classify(left, right)
        self.assertEqual(item["classification"], "INCOMPLETE_REVIEW")
        self.assertEqual(item["counts"]["same_path_without_both_hashes"], 1)
        unsafe = archive("unsafe.zip", {"../escape.py": "same"})
        summary = fusion.summarize(report(unsafe, right))
        self.assertEqual(summary["coverage"]["incomplete_archive_count"], 1)
        self.assertFalse(any(item["classification"] in {"SAME_FILE_SET", "COMPLETE_INCLUSION", "SHARED_COMPONENTS"}
                             for item in summary["candidates"]))

    def test_duplicate_and_casefold_paths_need_review(self):
        left = archive("a.zip", {"main.py": "same"})
        left["entries"].append(copy.deepcopy(left["entries"][0]))
        right = archive("b.zip", {"main.py": "same"})
        self.assertEqual(self.classify(left, right)["classification"], "INCOMPLETE_REVIEW")
        left["entries"][1]["path"] = "MAIN.py"
        left["entries"][1]["logical_path"] = "MAIN.py"
        self.assertIn("DUPLICATE_OR_CASEFOLD_PATH", self.classify(left, right)["archives"][0]["issues"])

    def test_readme_only_overlap_is_weak_but_same_inventory_is_fact(self):
        item = self.classify(archive("a.zip", {"README.md": "same", "a.py": "a"}),
                             archive("b.zip", {"README.md": "same", "b.py": "b"}))
        self.assertEqual(item["classification"], "DOCUMENTATION_ONLY")
        self.assertTrue(item["documentation_only_signal"])
        item = self.classify(archive("a.zip", {"README.md": "same"}), archive("b.zip", {"README.md": "same"}))
        self.assertEqual(item["classification"], "SAME_FILE_SET")
        self.assertTrue(item["documentation_only_signal"])

    def test_skill_agents_and_contract_markdown_are_behavior_components(self):
        for name in ["SKILL.md", "AGENTS.md", "CONTRATO.md", "instrucciones.md", "behavior.md", "docs/contract.md"]:
            item = self.classify(archive("a.zip", {name: "same", "a.py": "a"}),
                                 archive("b.zip", {name: "same", "b.py": "b"}))
            self.assertEqual(item["classification"], "SHARED_COMPONENTS", name)

    def test_dependency_context_tracks_dependents_and_unresolved_manifest(self):
        left = archive("a.zip", {"helper.py": "same", "main.py": "call"})
        right = archive("b.zip", {"helper.py": "same", "other.py": "other"})
        value = report(left, right)
        helper, main = left["entries"]
        value["dependency_analysis"]["nodes"] = [dict(helper, zip="a.zip", runtime_dependents=[main["id"]]),
                                                    dict(main, zip="a.zip")]
        value["dependency_analysis"]["edges"] = [{"source": main["id"], "status": "UNRESOLVED_MANIFEST_REFERENCE",
                                                   "reference": "missing.json", "line": 1}]
        item = fusion.summarize(value)["candidates"][0]
        context = item["dependency_context"][0]
        self.assertEqual(context["runtime_dependents_count"], 1)
        self.assertEqual(context["reference_issue_counts"]["UNRESOLVED_MANIFEST_REFERENCE"], 1)

    def test_bounded_coverage_and_no_transitive_merge(self):
        value = report(archive("a.zip", {"a.py": "a"}),
                       archive("b.zip", {"a.py": "a", "c.py": "c"}),
                       archive("c.zip", {"c.py": "c"}))
        original = copy.deepcopy(value)
        summary = fusion.summarize(value)
        self.assertEqual(value, original)
        self.assertEqual(summary["coverage"]["examined_pairs"], 3)
        self.assertEqual(len(summary["candidates"]), 2)
        self.assertTrue(all(len(item["archives"]) == 2 for item in summary["candidates"]))
        with patch.object(fusion, "MAX_PAIRS", 1), patch.object(fusion, "MAX_CANDIDATES", 1):
            limited = fusion.summarize(value)
        self.assertEqual(limited["coverage"]["unexamined_pairs"], 2)
        self.assertEqual(limited["coverage"]["status"], "LIMITED")

    def test_html_escaping_and_origin_files_unchanged(self):
        value = report(archive("<script>alert(1)</script>.zip", {"main.py": "same"}),
                       archive("second.zip", {"main.py": "same"}))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "report.json"
            source.write_text(json.dumps(value), encoding="utf-8")
            checksums = root / "SHA256SUMS.json"
            checksums.write_text(json.dumps({"report.json": hashlib.sha256(source.read_bytes()).hexdigest()}))
            verification = root / "verificacion.json"
            verification.write_text('{"status":"PASS"}')
            original_zip = root / "original.zip"
            original_zip.write_bytes(b"unchanged-original")
            before = {path.name: path.read_bytes() for path in (source, checksums, verification, original_zip)}
            result = fusion.write_summary(source)
            for name, data in before.items():
                self.assertEqual((root / name).read_bytes(), data)
            html = Path(result["paths"]["html"]).read_text(encoding="utf-8")
            self.assertNotIn("<script>alert(1)</script>", html)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
            self.assertIn('href="report.html"', html)
            self.assertTrue(Path(result["paths"]["json"]).is_file())
            source.write_text(source.read_text() + " ")
            with self.assertRaises(ValueError):
                fusion.write_summary(source)

    def test_write_requires_verified_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "report.json"
            source.write_text(json.dumps(report()))
            (root / "SHA256SUMS.json").write_text(json.dumps({"report.json": hashlib.sha256(source.read_bytes()).hexdigest()}))
            (root / "verificacion.json").write_text('{"status":"FAIL"}')
            with self.assertRaises(ValueError):
                fusion.write_summary(source)
            self.assertFalse((root / "RESUMEN_FUSIONES.json").exists())

    def test_unrelated_zip_root_readme_package_json_not_fusion(self):
        value = report(
            archive("alpha.zip", {"README.md": "Proyecto Alpha", "package.json": '{"name":"alpha"}', "alpha.js": "a"}),
            archive("beta.zip", {"README.md": "Proyecto Beta", "package.json": '{"name":"beta"}', "beta.js": "b"}))
        result = fusion.summarize(value)
        self.assertEqual(result["coverage"]["incidental_generic_path_pairs_suppressed"], 1)
        self.assertEqual(result["candidates"], [])
        self.assertIn("descartadas", " ".join(result["console_lines"]))
        self.assertEqual(result["distribution_unification"]["mode"], "KEEP_ORIGINAL_ZIPS")

    def test_root_scaffold_collision_does_not_hide_real_code_conflict(self):
        item = self.classify(
            archive("alpha.zip", {"README.md": "A", "package.json": '{"name":"a"}', "main.py": "first"}),
            archive("beta.zip", {"README.md": "B", "package.json": '{"name":"b"}', "main.py": "second"}))
        self.assertEqual(item["classification"], "PATH_CONFLICTS")
        self.assertEqual(item["counts"]["same_path_different_hash"], 3)

    def test_incomplete_generic_collision_preserves_review(self):
        item = self.classify(
            archive("a.zip", {"package.json": '{"name":"a"}'}, "PARTIAL"),
            archive("b.zip", {"package.json": '{"name":"b"}'}))
        self.assertEqual(item["classification"], "INCOMPLETE_REVIEW")

    def test_generic_root_case_collision_without_content_match_is_not_fusion(self):
        value = report(archive("a.zip", {"README.md": "A", "left.py": "left"}),
                       archive("b.zip", {"readme.md": "B", "right.py": "right"}))
        result = fusion.summarize(value)
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["coverage"]["incidental_generic_path_pairs_suppressed"], 1)

    def test_disjoint_packages_can_share_distribution_without_content_merge(self):
        value = report(archive("alpha.zip", {"alpha.py": "alpha"}),
                       archive("beta.zip", {"beta.py": "beta"}))
        result = fusion.summarize(value)
        self.assertEqual(result["candidates"], [])
        distribution = result["distribution_unification"]
        self.assertEqual(distribution["mode"], "KEEP_ORIGINAL_ZIPS")
        self.assertEqual(distribution["status"], "PROPOSED_ONLY")
        self.assertEqual(distribution["functional_integration"], "NOT_PROPOSED")
        self.assertEqual(len(distribution["source_archives"]), 2)
        self.assertTrue(distribution["source_identity_complete"])
        self.assertIsNone(distribution["automatic_action"])
        value["archives"][0]["status"] = "ERROR"
        value["archives"][0]["zip_sha256"] = None
        result = fusion.summarize(value)
        distribution = result["distribution_unification"]
        self.assertFalse(distribution["source_identity_complete"])
        self.assertEqual(distribution["source_archives"][0]["status"], "ERROR")
        self.assertIn("MISSING_ARCHIVE_HASH", distribution["source_archives"][0]["issues"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
