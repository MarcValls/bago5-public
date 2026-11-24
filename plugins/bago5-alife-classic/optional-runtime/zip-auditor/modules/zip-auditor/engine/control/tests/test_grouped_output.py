"""Meaningful filesystem checks for accepted, transactional ZIP copying."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import zipfile


SOURCE = Path(__file__).resolve().parents[1] / "grouped_output.py"
SPEC = importlib.util.spec_from_file_location("zipa_grouped_output", SOURCE)
grouped = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = grouped
SPEC.loader.exec_module(grouped)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal(plan):
    plan["plan_sha256"] = grouped.plan_digest(plan)
    return plan


def fixture(root, names=("alpha.zip", "beta.zip"), identical=False):
    sources = root / "Fuentes á漢 O'Brien & ! %TEMP% (2)"
    sources.mkdir()
    archives = []
    for index, name in enumerate(names, 1):
        path = sources.joinpath(*name.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            info = zipfile.ZipInfo("proyecto/README.md", (2026, 11, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, "Contenido compartido" if identical else "Contenido " + str(index))
        archives.append({"id": "A-" + str(index), "relative_path": name,
                         "sha256": sha(path), "size_bytes": path.stat().st_size,
                         "eligible": True, "issues": []})
    report = root / "report.json"
    report.write_text(json.dumps({"archives": archives}, ensure_ascii=False), encoding="utf-8")
    plan = {"schema_version": grouped.SCHEMA, "status": "PROPOSED",
            "report_path": str(report), "report_sha256": sha(report),
            "source_root": str(sources), "archives": archives,
            "groups": [{"id": "G-1", "directory_name": "01_Grupo_á漢",
                        "label": "Proyecto compartido", "member_ids": [a["id"] for a in archives],
                        "confidence": "HIGH", "evidence": [{"kind": "EXACT_CONTENT"}],
                        "status": "PROPOSED"}],
            "coverage": {}, "limits": ["No acredita equivalencia funcional"],
            "console_lines": [], "paths": {"json": str(root / "plan.json"),
                                            "html": str(root / "plan.html")}}
    return seal(plan), sources, root / "Salida á漢 & ! % ' (2)"


class GroupedOutputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="zipa-grouping-")
        self.root = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def assert_no_staging(self, output):
        if output.exists():
            self.assertEqual([], list(output.glob(".ZIP_AUDITOR_AGRUPAR_*")))

    def test_decline_does_not_access_filesystem_even_for_truthy_values(self):
        class NoPath:
            def __fspath__(self):
                raise AssertionError("The declined operation inspected the path")

        with mock.patch.object(grouped, "_validate_plan", side_effect=AssertionError("read")), \
                mock.patch.object(grouped.tempfile, "mkdtemp", side_effect=AssertionError("write")):
            for accepted in (False, None, 1, "True", [], {}):
                with self.subTest(accepted=accepted):
                    result = grouped.apply_grouping(None, NoPath(), accepted=accepted)
                    self.assertEqual("DECLINED", result["status"])
                    self.assertEqual(0, result["copied_count"])

    def test_happy_path_preserves_zip_bytes_and_sources_with_unicode(self):
        plan, sources, output = fixture(self.root, ("paquete á漢.zip", "segundo β.zip"))
        original = {a["relative_path"]: (sources / a["relative_path"]).read_bytes() for a in plan["archives"]}
        predicted = grouped.output_directory_for(plan, output)
        self.assertFalse(output.exists())
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("COPIED", result["status"], result)
        self.assertEqual(predicted, Path(result["output_directory"]))
        self.assertEqual(2, result["copied_count"])
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(sha(result["manifest_path"]), result["manifest_sha256"])
        self.assertTrue(Path(result["readme_path"]).is_file())
        for row in manifest["copies"]:
            target = predicted / row["destination_relative_path"]
            self.assertEqual(original[row["source_relative_path"]], target.read_bytes())
            self.assertEqual(row["source_zip_sha256"], sha(target))
            self.assertEqual(row["source_zip_sha256"], row["copied_sha256"])
            self.assertEqual([{"kind": "EXACT_CONTENT"}], row["group_evidence"])
            self.assertEqual(original[row["source_relative_path"]], Path(row["source"]).read_bytes())
        self.assertEqual(2, len(list(predicted.rglob("*.zip"))))
        self.assert_no_staging(output)

    def test_singleton_without_matches_is_copyable(self):
        plan, _, output = fixture(self.root, ("independiente.zip",))
        plan["groups"][0]["status"] = "SIN_COINCIDENCIAS"
        seal(plan)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("COPIED", result["status"], result)
        self.assertEqual(1, result["copied_count"])

    def test_stable_fstat_ctime_with_different_semantics_is_accepted(self):
        plan, sources, output = fixture(self.root)
        original_fstat = os.fstat

        def changed_semantics(fd):
            info = original_fstat(fd)
            return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino,
                                   st_size=info.st_size, st_mtime_ns=info.st_mtime_ns,
                                   st_ctime_ns=info.st_ctime_ns + 10_000_000)

        with mock.patch.object(grouped.os, "fstat", side_effect=changed_semantics):
            result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("COPIED", result["status"], result)
        self.assertEqual(2, result["copied_count"])
        self.assertEqual({a["relative_path"]: a["sha256"] for a in plan["archives"]},
                         {a["relative_path"]: sha(sources / a["relative_path"]) for a in plan["archives"]})

    def test_handle_ctime_changed_during_read_or_copy_is_rejected(self):
        # Call 2 is the end of report verification; call 8 is the end of the
        # first ZIP copy after report + two source prechecks (six fstat calls).
        for changed_call in (2, 8):
            with self.subTest(changed_call=changed_call):
                case = self.root / ("case_" + str(changed_call)); case.mkdir()
                plan, _, output = fixture(case)
                original_fstat = os.fstat
                calls = 0

                def changed_metadata(fd):
                    nonlocal calls
                    calls += 1
                    info = original_fstat(fd)
                    return SimpleNamespace(st_dev=info.st_dev, st_ino=info.st_ino,
                                           st_size=info.st_size, st_mtime_ns=info.st_mtime_ns,
                                           st_ctime_ns=info.st_ctime_ns + (1 if calls == changed_call else 0))

                with mock.patch.object(grouped.os, "fstat", side_effect=changed_metadata):
                    result = grouped.apply_grouping(plan, output, accepted=True)
                self.assertEqual("FAILED", result["status"], result)
                self.assertEqual("SOURCE_CHANGED", result["error_code"])
                self.assertFalse(output.exists())

    def test_casefold_basename_collisions_get_unique_names_even_for_identical_zips(self):
        plan, sources, output = fixture(self.root, ("a/Informe.zip", "b/informe.ZIP", "c/Informe.zip"), identical=True)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("COPIED", result["status"], result)
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        rows = manifest["copies"]
        names = [Path(row["destination_relative_path"]).name for row in rows]
        self.assertEqual(3, len({name.casefold() for name in names}))
        self.assertTrue(all(row["renamed_for_collision"] for row in rows))
        self.assertTrue(all("__" in name for name in names))
        for row in rows:
            self.assertEqual((sources / row["source_relative_path"]).read_bytes(),
                             (Path(result["output_directory"]) / row["destination_relative_path"]).read_bytes())

    def test_repeated_application_never_overwrites_existing_results(self):
        plan, _, output = fixture(self.root)
        previous = output / grouped.OUTPUT_NAME
        previous.mkdir(parents=True)
        sentinel = previous / "trabajo_del_usuario.txt"
        sentinel.write_text("Conservar exactamente")
        one = grouped.apply_grouping(plan, output, accepted=True)
        two = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual(("COPIED", "COPIED"), (one["status"], two["status"]), (one, two))
        self.assertNotEqual(one["output_directory"], two["output_directory"])
        self.assertEqual("Conservar exactamente", sentinel.read_text())
        self.assertTrue(Path(one["manifest_path"]).is_file())
        self.assertTrue(Path(two["manifest_path"]).is_file())

    def test_output_inside_sources_uses_fixed_plan_without_recursive_rescanning(self):
        plan, sources, _ = fixture(self.root)
        output = sources / "informes" / "analisis_actual"
        first = grouped.apply_grouping(plan, output, accepted=True)
        second = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual(("COPIED", "COPIED"), (first["status"], second["status"]), (first, second))
        self.assertEqual((2, 2), (first["copied_count"], second["copied_count"]))
        manifest = json.loads(Path(second["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual("FIXED_PLAN_NO_RESCAN", manifest["source_selection"])
        self.assertIs(manifest["output_root_within_source_root"], True)
        self.assertEqual({a["id"] for a in plan["archives"]}, {r["archive_id"] for r in manifest["copies"]})

    def test_modified_plan_is_rejected_before_writing(self):
        plan, _, output = fixture(self.root)
        plan["groups"][0]["directory_name"] = "cambiado_despues_de_revisar"
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("PLAN_CHANGED", result["error_code"])
        self.assertFalse(output.exists())

    def test_modified_report_is_rejected_before_writing(self):
        plan, _, output = fixture(self.root)
        Path(plan["report_path"]).write_text("Informe sustituido")
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("SOURCE_CHANGED", result["error_code"])
        self.assertFalse(output.exists())

    def test_source_hash_drift_with_same_size_is_rejected(self):
        plan, sources, output = fixture(self.root)
        changed = sources / "alpha.zip"
        data = bytearray(changed.read_bytes()); data[-1] ^= 1; changed.write_bytes(data)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("SOURCE_CHANGED", result["error_code"])
        self.assertFalse(output.exists())
        self.assertEqual(bytes(data), changed.read_bytes())

    def test_missing_source_is_rejected_before_writing(self):
        plan, sources, output = fixture(self.root)
        (sources / "alpha.zip").unlink()
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("SOURCE_MISSING", result["error_code"])
        self.assertFalse(output.exists())

    def test_group_membership_and_directory_ambiguities_are_rejected(self):
        plan, _, output = fixture(self.root)
        variants = []
        missing = copy.deepcopy(plan); missing["groups"][0]["member_ids"] = ["A-1"]; variants.append(missing)
        repeated = copy.deepcopy(plan); repeated["groups"][0]["member_ids"].append("A-1"); variants.append(repeated)
        unknown = copy.deepcopy(plan); unknown["groups"][0]["member_ids"][0] = "missing"; variants.append(unknown)
        empty = copy.deepcopy(plan); empty["groups"][0]["member_ids"] = []; variants.append(empty)
        ineligible = copy.deepcopy(plan); ineligible["archives"][0]["eligible"] = False; variants.append(ineligible)
        group_id = copy.deepcopy(plan); group_id["groups"].append(copy.deepcopy(group_id["groups"][0])); variants.append(group_id)
        singleton = copy.deepcopy(plan); singleton["groups"][0]["status"] = "SIN_COINCIDENCIAS"; variants.append(singleton)
        duplicate_dir = copy.deepcopy(plan)
        duplicate_dir["groups"][0]["member_ids"] = ["A-1"]
        second = copy.deepcopy(duplicate_dir["groups"][0]); second.update(id="G-2", member_ids=["A-2"], directory_name=second["directory_name"].upper())
        duplicate_dir["groups"].append(second); variants.append(duplicate_dir)
        for variant in variants:
            with self.subTest(variant=variant["groups"]):
                result = grouped.apply_grouping(seal(variant), output, accepted=True)
                self.assertEqual("FAILED", result["status"], result)
                self.assertFalse(output.exists())

    def test_windows_reserved_and_unsafe_group_names_are_rejected(self):
        plan, _, output = fixture(self.root)
        for name in ("CON", "con.txt", "LPT9", "COM¹", "AUX", "folder.", "folder ",
                     "../escape", "a/b", "a\\b", "C:stream", "a?b", "nul.zip", grouped.MANIFEST_NAME):
            with self.subTest(name=name):
                modified = copy.deepcopy(plan); modified["groups"][0]["directory_name"] = name
                result = grouped.apply_grouping(seal(modified), output, accepted=True)
                self.assertEqual("FAILED", result["status"])
                self.assertFalse(output.exists())

    def test_unsafe_source_paths_are_rejected_before_access(self):
        plan, _, output = fixture(self.root)
        for name in ("../escape.zip", "/absolute.zip", "dir\\name.zip", "a//name.zip", "a/./name.zip",
                     "a/../name.zip", "C:stream.zip", "AUX.zip", "name.zip ", "other.txt"):
            with self.subTest(name=name):
                modified = copy.deepcopy(plan); modified["archives"][0]["relative_path"] = name
                result = grouped.apply_grouping(seal(modified), output, accepted=True)
                self.assertEqual("FAILED", result["status"])
                self.assertFalse(output.exists())

    def _symlink_or_skip(self, target, link, directory=False):
        try:
            link.symlink_to(target, target_is_directory=directory)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("No se pueden crear enlaces para esta prueba: " + str(exc))

    def test_symlink_source_file_is_not_followed(self):
        plan, sources, output = fixture(self.root)
        original = sources / "alpha.zip"
        held = self.root / "held.zip"; original.rename(held)
        self._symlink_or_skip(held, original)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("LINK_NOT_ALLOWED", result["error_code"])
        self.assertFalse(output.exists())
        self.assertTrue(held.is_file())

    def test_symlink_source_parent_is_not_followed(self):
        plan, sources, output = fixture(self.root, ("sub/alpha.zip", "sub/beta.zip"))
        held = self.root / "held_sources"; (sources / "sub").rename(held)
        self._symlink_or_skip(held, sources / "sub", directory=True)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("LINK_NOT_ALLOWED", result["error_code"])
        self.assertFalse(output.exists())

    def test_symlink_output_root_and_existing_destination_are_rejected(self):
        plan, _, output = fixture(self.root)
        other = self.root / "otra_carpeta"; other.mkdir()
        self._symlink_or_skip(other, output, directory=True)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual([], list(other.iterdir()))
        output.unlink(); output.mkdir()
        self._symlink_or_skip(other, output / grouped.OUTPUT_NAME, directory=True)
        result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("LINK_NOT_ALLOWED", result["error_code"])
        self.assertEqual([], list(other.iterdir()))

    def test_failed_copy_cleans_only_own_staging_and_preserves_existing_work(self):
        plan, sources, output = fixture(self.root)
        previous = output / grouped.OUTPUT_NAME; previous.mkdir(parents=True)
        sentinel = previous / "manual.txt"; sentinel.write_text("No tocar")
        foreign = output / ".ZIP_AUDITOR_AGRUPAR_de_otro_proceso"; foreign.mkdir()
        (foreign / "manual.txt").write_text("Otro proceso")
        before = {a["relative_path"]: sha(sources / a["relative_path"]) for a in plan["archives"]}
        original_copy = grouped._copy_verified
        count = 0

        def fail_second(source, target):
            nonlocal count
            count += 1
            if count == 2:
                target.write_bytes(b"copia parcial")
                raise OSError("Disco lleno simulado")
            return original_copy(source, target)

        with mock.patch.object(grouped, "_copy_verified", side_effect=fail_second):
            result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual(0, result["copied_count"])
        self.assertIsNone(result["output_directory"])
        self.assertEqual({previous.name, foreign.name}, {p.name for p in output.iterdir()})
        self.assertEqual("No tocar", sentinel.read_text())
        self.assertEqual("Otro proceso", (foreign / "manual.txt").read_text())
        self.assertEqual(before, {a["relative_path"]: sha(sources / a["relative_path"]) for a in plan["archives"]})

    def test_source_changed_after_copy_blocks_publication(self):
        plan, _, output = fixture(self.root)
        original_copy = grouped._copy_verified
        count = 0

        def change_after_copy(source, target):
            nonlocal count
            count += 1
            result = original_copy(source, target)
            if count == 1:
                with source["path"].open("ab") as stream:
                    stream.write(b"Cambio concurrente")
            return result

        with mock.patch.object(grouped, "_copy_verified", side_effect=change_after_copy):
            result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertEqual("SOURCE_CHANGED", result["error_code"])
        self.assertFalse(output.exists())

    def test_destination_second_read_detects_corruption(self):
        plan, _, output = fixture(self.root)
        original_snapshot = grouped._verified_snapshot

        def corrupt_before_destination_check(path, expected_hash, expected_size=None, previous=None):
            if ".ZIP_AUDITOR_AGRUPAR_" in str(path) and str(path).lower().endswith(".zip"):
                data = bytearray(path.read_bytes()); data[0] ^= 1; path.write_bytes(data)
            return original_snapshot(path, expected_hash, expected_size, previous)

        with mock.patch.object(grouped, "_verified_snapshot", side_effect=corrupt_before_destination_check):
            result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("FAILED", result["status"])
        self.assertFalse(output.exists())

    def test_atomic_publish_race_preserves_competing_directory_and_uses_suffix(self):
        plan, _, output = fixture(self.root)
        actual_publish = grouped._atomic_publish_noreplace
        raced = []

        def competing_publisher(source, destination):
            if not raced:
                destination.mkdir()
                (destination / "otro.txt").write_text("Publicacion concurrente")
                raced.append(destination)
            return actual_publish(source, destination)

        with mock.patch.object(grouped, "_atomic_publish_noreplace", side_effect=competing_publisher):
            result = grouped.apply_grouping(plan, output, accepted=True)
        self.assertEqual("COPIED", result["status"], result)
        self.assertNotEqual(raced[0], Path(result["output_directory"]))
        self.assertEqual("Publicacion concurrente", (raced[0] / "otro.txt").read_text())

    def test_atomic_publish_refuses_to_replace_even_an_empty_directory(self):
        source, destination = self.root / "stage", self.root / "existing"
        source.mkdir(); destination.mkdir()
        (source / "content.txt").write_text("Content")
        with self.assertRaises(FileExistsError):
            grouped._atomic_publish_noreplace(source, destination)
        self.assertEqual([], list(destination.iterdir()))
        self.assertEqual("Content", (source / "content.txt").read_text())

    def test_keyboard_interrupt_cleans_staging_without_publishing(self):
        plan, _, output = fixture(self.root)
        with mock.patch.object(grouped, "_copy_verified", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                grouped.apply_grouping(plan, output, accepted=True)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
