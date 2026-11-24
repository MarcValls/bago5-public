#!/usr/bin/env python3
"""BAGO Evidence Guard v1.0.0 — deterministic SHA-256 evidence creation and checks.

Standard-library only. No changes to source files, existing reports, or TaskStore.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SPEC_SCHEMA = "bago.evidence.guard.spec.v1"
BINDINGS_SCHEMA = "bago.evidence.guard.bindings.v1"
MANIFEST_SCHEMA = "bago.evidence.guard.manifest.v1"
HEX64 = re.compile(r"[0-9a-fA-F]{64}\Z")
ROLE = re.compile(r"[a-z][a-z0-9_-]{0,39}\Z")
DYNAMIC_HASH_KEYS = {"sha256", "hash", "file_hash", "file_sha256", "content_sha256"}


class GuardError(Exception):
    """A configuration, integrity, provenance, or safety check failed."""


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise GuardError(reason)


def forbidden_characters(value: str, *, allow_text_layout: bool = True) -> list[tuple[int, str]]:
    allowed = "\t\r\n" if allow_text_layout else ""
    return [(i, f"U+{ord(c):04X}") for i, c in enumerate(value)
            if (ord(c) < 32 and c not in allowed) or ord(c) == 127]


def check_text(value: str, name: str, *, layout: bool = True) -> None:
    issues = forbidden_characters(value, allow_text_layout=layout)
    require(not issues, f"FORBIDDEN_C0_DEL:{name}:{issues[:5]}")


def check_json_strings(obj: Any, at: str = "$", *, allow_layout: bool = True) -> None:
    if isinstance(obj, str):
        check_text(obj, at, layout=allow_layout)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            check_text(k, f"{at}.key", layout=False)
            check_json_strings(v, at + "/" + k, allow_layout=allow_layout)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            check_json_strings(v, at + f"/{i}", allow_layout=allow_layout)


def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        raw = path.read_bytes()
        require(not raw.startswith(b"\xef\xbb\xbf"), f"UTF8_BOM_FORBIDDEN:{path}")
        text = raw.decode("utf-8", errors="strict")
        check_text(text, f"json_raw:{path}")
        def reject_constant(v: str) -> None:
            raise GuardError(f"NON_STANDARD_JSON_NUMBER:{v}")
        parsed = json.loads(text, object_pairs_hook=no_duplicate_keys,
                            parse_constant=reject_constant)
        check_json_strings(parsed)
        return parsed
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GuardError(f"INVALID_JSON:{path}:{exc}") from exc
    except FileNotFoundError as exc:
        raise GuardError(f"MISSING_FILE:{path}") from exc


def json_data_bytes(obj: Any) -> bytes:
    check_json_strings(obj)
    return (json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False)
            + "\n").encode("utf-8")


def check_markdown(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
        require(not data.startswith(b"\xef\xbb\xbf"), f"UTF8_BOM_FORBIDDEN:{path}")
        text = data.decode("utf-8", errors="strict")
        check_text(text, f"markdown:{path}")
        return {"path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    except (UnicodeError, FileNotFoundError) as exc:
        raise GuardError(f"INVALID_TEXT:{path}:{exc}") from exc


def canonical_hash(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                     allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def safe_relative_path(text: Any) -> tuple[str, ...]:
    require(isinstance(text, str) and bool(text), f"INVALID_PATH:{text!r}")
    check_text(text, "relative_path", layout=False)
    value = text.replace("\\", "/")
    require(not value.startswith("/") and not re.match(r"^[A-Za-z]:", value),
            f"ABSOLUTE_PATH_FORBIDDEN:{text}")
    components = value.split("/")
    require(all(x not in ("", ".", "..") for x in components),
            f"PATH_TRAVERSAL_OR_AMBIGUITY:{text}")
    require(not any(":" in x for x in components), f"COLON_FORBIDDEN_IN_PATH:{text}")
    return tuple(components)


def safe_root(value: str) -> Path:
    p = Path(value).expanduser()
    require(p.is_dir(), f"ROOT_NOT_DIRECTORY:{value}")
    return p.resolve(strict=True)


def resolve_file(root: Path, rel: str) -> Path:
    root = root.resolve(strict=True)
    parts = safe_relative_path(rel)
    p = root
    for item in parts:
        p = p / item
        try:
            meta = p.lstat()
        except OSError as exc:
            raise GuardError(f"MISSING_OR_INACCESSIBLE_SOURCE:{rel}:{exc}") from exc
        # On Windows, junctions are reparse points, even when is_symlink() is false.
        attrs = getattr(meta, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        require(not stat.S_ISLNK(meta.st_mode) and not (attrs & reparse_flag)
                and not getattr(p, "is_junction", lambda: False)(),
                f"LINK_OR_REPARSE_POINT_REJECTED:{rel}")
    require(p.is_file(), f"SOURCE_NOT_REGULAR_FILE:{rel}")
    require(p.resolve(strict=True).is_relative_to(root), f"PATH_OUTSIDE_ROOT:{rel}")
    return p


def signature(st: os.stat_result) -> tuple[int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def file_sha256(root: Path, rel: str) -> tuple[str, int]:
    p = resolve_file(root, rel)
    try:
        before = p.stat(follow_symlinks=False)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(p, flags)
        try:
            opened = os.fstat(fd)
            # Path stat and descriptor stat can expose different Windows ctime semantics.
            # Compare identity/size/mtime across surfaces, and full signatures within each.
            require(signature(opened)[:-1] == signature(before)[:-1],
                    f"SOURCE_CHANGED_BEFORE_READ:{rel}")
            hasher = hashlib.sha256()
            size = 0
            with os.fdopen(fd, "rb", closefd=False) as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    size += len(chunk)
                    hasher.update(chunk)
            after_fd = os.fstat(fd)
        finally:
            os.close(fd)
        after_path = p.stat(follow_symlinks=False)
        require(signature(before) == signature(after_path)
                and signature(opened) == signature(after_fd)
                and size == before.st_size, f"FILE_CHANGED_DURING_HASH:{rel}")
        return hasher.hexdigest(), size
    except OSError as exc:
        raise GuardError(f"READ_FAILED:{rel}:{exc}") from exc


def validate_entries(entries: Any, *, require_role: bool) -> list[dict[str, Any]]:
    require(isinstance(entries, list) and len(entries) > 0, "EMPTY_OR_INVALID_FILES")
    paths: set[str] = set()
    result = []
    for item in entries:
        require(isinstance(item, dict), "INVALID_FILE_ENTRY")
        keys = {"path", "role"} if require_role else {"path", "role", "sha256", "size"}
        require(set(item) == keys, f"FILE_ENTRY_FIELDS_MISMATCH:{item}")
        parts = safe_relative_path(item["path"])
        canonical = "/".join(parts)
        key = canonical.casefold()
        require(key not in paths, f"DUPLICATE_SOURCE_PATH:{canonical}")
        paths.add(key)
        role = item["role"]
        require(isinstance(role, str) and ROLE.fullmatch(role) is not None,
                f"INVALID_ROLE:{role}")
        result.append({"path": canonical, "role": role, **({} if require_role else {
            "sha256": item["sha256"], "size": item["size"]})})
    result.sort(key=lambda x: x["path"].casefold())
    return result


def md_escaped(text: str) -> str:
    return text.replace("\\", "\\\\").replace("|", "\\|").replace("<", "&lt;")


def render_markdown(manifest: dict[str, Any]) -> bytes:
    lines = ["# Informe de integridad — BAGO Evidence Guard", "",
             f"Identidad del inventario: `{manifest['entries_sha256']}`", "",
             f"Generado (UTC): {manifest['generated_at_utc']}", "",
             f"Archivos: {len(manifest['entries'])}", "",
             "| Archivo (relativo a la raíz) | Rol | Bytes | SHA-256 |",
             "| --- | --- | ---: | --- |"]
    for entry in manifest["entries"]:
        lines.append(f"| `{md_escaped(entry['path'])}` | {entry['role']} | "
                     f"{entry['size']} | `{entry['sha256']}` |")
    lines.extend(["", "**Alcance:** los hashes describen bytes observados; no prueban "
                  "la ejecución funcional, la autorización ni el origen humano de los datos.", ""])
    result = "\n".join(lines)
    check_text(result, "generated_markdown")
    return result.encode("utf-8")


def validate_manifest_structure(manifest: Any) -> dict[str, Any]:
    require(isinstance(manifest, dict), "MANIFEST_NOT_OBJECT")
    expected = {"schema", "tool_version", "generator_sha256", "generated_at_utc",
                "root_label", "algorithm", "entries", "entries_sha256"}
    require(set(manifest) == expected, "MANIFEST_FIELDS_MISMATCH")
    require(manifest["schema"] == MANIFEST_SCHEMA and manifest["algorithm"] == "SHA-256",
            "MANIFEST_SCHEMA_OR_ALGORITHM_MISMATCH")
    require(isinstance(manifest["tool_version"], str), "INVALID_TOOL_VERSION")
    require(isinstance(manifest["generator_sha256"], str) and
            HEX64.fullmatch(manifest["generator_sha256"]) is not None, "INVALID_GENERATOR_DIGEST")
    require(isinstance(manifest["root_label"], str), "INVALID_ROOT_LABEL")
    check_text(manifest["root_label"], "root_label", layout=False)
    require(isinstance(manifest["generated_at_utc"], str) and
            manifest["generated_at_utc"].endswith("Z"), "INVALID_TIME")
    entries = validate_entries(manifest["entries"], require_role=False)
    require(entries == manifest["entries"], "ENTRIES_NOT_CANONICAL_SORTED")
    for item in entries:
        require(isinstance(item["sha256"], str) and HEX64.fullmatch(item["sha256"]) is not None,
                f"INVALID_SHA256_FORMAT:{item['path']}")
        require(item["sha256"] == item["sha256"].lower(), f"NONCANONICAL_SHA:{item['path']}")
        require(type(item["size"]) is int and item["size"] >= 0,
                f"INVALID_SIZE:{item['path']}")
    require(isinstance(manifest["entries_sha256"], str) and
            HEX64.fullmatch(manifest["entries_sha256"]) is not None and
            canonical_hash(entries) == manifest["entries_sha256"],
            "ENTRIES_DIGEST_MISMATCH")
    return manifest


def verify_manifest_model(root: Path, manifest: Any) -> list[dict[str, Any]]:
    document = validate_manifest_structure(manifest)
    results = []
    for entry in document["entries"]:
        actual, size = file_sha256(root, entry["path"])
        require(actual == entry["sha256"] and size == entry["size"],
                f"FILE_MISMATCH:{entry['path']}:expected={entry['sha256']}:actual={actual}")
        results.append({"path": entry["path"], "status": "PASS"})
    return results


def create_manifest(root: Path, spec_path: Path, output_dir: Path, label: str) -> dict[str, Any]:
    spec = load_json(spec_path)
    require(isinstance(spec, dict) and set(spec) == {"schema", "files"} and
            spec["schema"] == SPEC_SCHEMA, "INVALID_SPEC_SCHEMA_OR_FIELDS")
    entries = validate_entries(spec["files"], require_role=True)
    for entry in entries:
        entry["sha256"], entry["size"] = file_sha256(root, entry["path"])
    check_text(label, "root_label", layout=False)
    manifest = {"schema": MANIFEST_SCHEMA, "tool_version": VERSION,
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
                "root_label": label, "algorithm": "SHA-256", "entries": entries,
                "entries_sha256": canonical_hash(entries)}
    verify_manifest_model(root, manifest)
    require(not output_dir.exists(), f"OUTPUT_ALREADY_EXISTS:{output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}.partial.", dir=output_dir.parent))
    try:
        (staged / "manifest.json").write_bytes(json_data_bytes(manifest))
        (staged / "informe.md").write_bytes(render_markdown(manifest))
        reread = load_json(staged / "manifest.json")
        verify_manifest_model(root, reread)
        require((staged / "informe.md").read_bytes() == render_markdown(reread),
                "MARKDOWN_SERIALIZATION_MISMATCH")
        check_markdown(staged / "informe.md")
        require(not output_dir.exists(), f"OUTPUT_ALREADY_EXISTS:{output_dir}")
        os.rename(staged, output_dir)
        reread = load_json(output_dir / "manifest.json")
        verify_manifest_model(root, reread)
        require((output_dir / "informe.md").read_bytes() == render_markdown(reread),
                "OUTPUT_MODIFIED_AFTER_WRITE")
        return {"status": "PASS", "items": len(entries),
                "manifest": str(output_dir / "manifest.json"),
                "markdown": str(output_dir / "informe.md"),
                "entries_sha256": manifest["entries_sha256"]}
    finally:
        if staged.exists():
            import shutil
            shutil.rmtree(staged)


def binding_config(config_path: Path) -> list[dict[str, str]]:
    obj = load_json(config_path)
    require(isinstance(obj, dict) and {"schema", "bindings"} <= set(obj)
            and set(obj) <= {"schema", "bindings", "expected_count"}
            and obj["schema"] == BINDINGS_SCHEMA, "INVALID_BINDINGS_SCHEMA_OR_FIELDS")
    items = obj["bindings"]
    require(isinstance(items, list) and items, "BINDINGS_EMPTY")
    if "expected_count" in obj:
        require(type(obj["expected_count"]) is int and obj["expected_count"] == len(items),
                "BINDINGS_EXPECTED_COUNT_MISMATCH")
    pointers: set[str] = set()
    result: list[dict[str, str]] = []
    for item in items:
        require(isinstance(item, dict) and set(item) == {"pointer", "path"},
                "INVALID_BINDING_FIELDS")
        require(isinstance(item["pointer"], str) and item["pointer"].startswith("/"),
                "JSON_POINTER_REQUIRED")
        check_text(item["pointer"], "json_pointer", layout=False)
        require(item["pointer"] not in pointers, f"DUPLICATE_POINTER:{item['pointer']}")
        pointers.add(item["pointer"])
        path = "/".join(safe_relative_path(item["path"]))
        result.append({"pointer": item["pointer"], "path": path})
    return result


def pointer_tokens(pointer: str) -> list[str]:
    out = []
    for part in pointer[1:].split("/"):
        require(not re.search(r"~(?![01])", part), f"INVALID_JSON_POINTER_ESCAPE:{pointer}")
        out.append(part.replace("~1", "/").replace("~0", "~"))
    return out


def get_pointer(obj: Any, pointer: str) -> Any:
    node = obj
    for token in pointer_tokens(pointer):
        if isinstance(node, dict):
            require(token in node, f"POINTER_FIELD_NOT_FOUND:{pointer}")
            node = node[token]
        elif isinstance(node, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None and
                    int(token) < len(node), f"POINTER_INDEX_NOT_FOUND:{pointer}")
            node = node[int(token)]
        else:
            raise GuardError(f"POINTER_NOT_CONTAINER:{pointer}")
    return node


def set_pointer(obj: Any, pointer: str, value: str) -> None:
    parent_tokens = pointer_tokens(pointer)
    require(bool(parent_tokens), "POINTER_EMPTY")
    node = obj
    for token in parent_tokens[:-1]:
        if isinstance(node, dict):
            require(token in node, f"POINTER_FIELD_NOT_FOUND:{pointer}")
            node = node[token]
        elif isinstance(node, list):
            require(re.fullmatch(r"0|[1-9][0-9]*", token) is not None
                    and int(token) < len(node), f"POINTER_INDEX_NOT_FOUND:{pointer}")
            node = node[int(token)]
        else:
            raise GuardError(f"POINTER_NOT_CONTAINER:{pointer}")
    leaf = parent_tokens[-1]
    if isinstance(node, dict):
        require(leaf in node, f"POINTER_FIELD_NOT_FOUND:{pointer}")
        require(node[leaf] in (None, "", "__SHA256__"), f"NONEMPTY_DIGEST_PLACEHOLDER:{pointer}")
        node[leaf] = value
    elif isinstance(node, list):
        require(re.fullmatch(r"0|[1-9][0-9]*", leaf) is not None
                and int(leaf) < len(node), f"POINTER_INDEX_NOT_FOUND:{pointer}")
        require(node[int(leaf)] in (None, "", "__SHA256__"), f"NONEMPTY_DIGEST_PLACEHOLDER:{pointer}")
        node[int(leaf)] = value
    else:
        raise GuardError(f"POINTER_NOT_CONTAINER:{pointer}")


def leaf_hash_fields(obj: Any, base: str = "") -> list[str]:
    out: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            pointer = base + "/" + key.replace("~", "~0").replace("/", "~1")
            if (key.lower().endswith("_sha256") or key.lower() in DYNAMIC_HASH_KEYS):
                out.append(pointer)
            else:
                out.extend(leaf_hash_fields(value, pointer))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            out.extend(leaf_hash_fields(value, base + f"/{i}"))
    return out


def verify_json_model(root: Path, obj: Any, bindings: list[dict[str, str]], *,
                      strict_claims: bool) -> dict[str, Any]:
    observed = {x["pointer"] for x in bindings}
    if strict_claims:
        unbound = sorted(set(leaf_hash_fields(obj)) - observed)
        require(not unbound, f"UNBOUND_HASH_CLAIMS:{unbound[:12]}")
    checks = []
    failures = 0
    for binding in bindings:
        path = binding["path"]
        pointer = binding["pointer"]
        value = get_pointer(obj, pointer)
        actual, size = file_sha256(root, path)
        if not isinstance(value, str) or HEX64.fullmatch(value) is None:
            outcome = "INVALID_SHA256_FORMAT"
            recoveries = []
            if isinstance(value, str) and len(value) == 65:
                recoveries = [{"position_1_based": i + 1, "character": c}
                              for i, c in enumerate(value)
                              if (value[:i] + value[i + 1:]).lower() == actual]
        elif value.lower() != actual:
            outcome = "DIGEST_MISMATCH"
            recoveries = []
        else:
            outcome = "PASS"
            recoveries = []
        if outcome != "PASS":
            failures += 1
        checks.append({"pointer": pointer, "path": path, "status": outcome,
                       "actual_sha256": actual, "declared_sha256": value,
                       "size": size, "one_character_insertion_candidates": recoveries})
    return {"status": "PASS" if failures == 0 else "FAIL", "checked": len(checks),
            "passed": len(checks) - failures, "failed": failures, "checks": checks}


def no_clobber_file(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists() and not path.is_symlink(), f"OUTPUT_ALREADY_EXISTS:{path}")
    fd, stage = tempfile.mkstemp(prefix=f".{path.name}.partial.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(stage, path)
        except OSError as exc:
            raise GuardError(f"ATOMIC_NO_CLOBBER_UNAVAILABLE:{path}:{exc}") from exc
    finally:
        if os.path.exists(stage):
            os.unlink(stage)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="BAGO Evidence Guard v1.0.0 — integrity reports without manually transcribed hashes")
    sp = ap.add_subparsers(dest="command", required=True)

    p = sp.add_parser("create-manifest", help="Generate an immutable new manifest+Markdown from a file inventory")
    p.add_argument("--root", required=True)
    p.add_argument("--spec", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--label", default="workspace")

    p = sp.add_parser("verify-manifest", help="Recalculate all source digests and check a generated report")
    p.add_argument("--root", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--markdown")

    p = sp.add_parser("verify-json", help="Verify SHA-256 fields in any existing JSON via explicit JSON-pointer bindings")
    p.add_argument("--root", required=True)
    p.add_argument("--report", required=True)
    p.add_argument("--bindings", required=True)
    p.add_argument("--text", action="append", default=[], help="Additional UTF-8 Markdown/text file to check for C0/DEL")
    p.add_argument("--allow-unbound-claims", action="store_true", help="Explicitly waive full coverage of hash-named fields")
    p.add_argument("--expected-count", type=int, help="Require exactly N mapped claims (e.g. W12: 15)")

    p = sp.add_parser("seal-json", help="Populate SHA-256 placeholders in a NEW JSON; never overwrite the template")
    p.add_argument("--root", required=True)
    p.add_argument("--template", required=True)
    p.add_argument("--bindings", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--expected-count", type=int, help="Require exactly N mapped claims")

    p = sp.add_parser("check-text", help="Check UTF-8 JSON/Markdown for prohibited controls and duplicate JSON keys")
    p.add_argument("--file", action="append", required=True)

    args = ap.parse_args(argv)
    try:
        if args.command == "create-manifest":
            result = create_manifest(safe_root(args.root), Path(args.spec),
                                     Path(args.out_dir), args.label)
        elif args.command == "verify-manifest":
            root = safe_root(args.root)
            obj = load_json(Path(args.manifest))
            checks = verify_manifest_model(root, obj)
            if args.markdown:
                path = Path(args.markdown)
                check_markdown(path)
                require(path.read_bytes() == render_markdown(obj),
                        "MARKDOWN_MANIFEST_MISMATCH")
            result = {"status": "PASS", "verified": len(checks), "entries_sha256": obj["entries_sha256"]}
        elif args.command == "verify-json":
            root = safe_root(args.root)
            doc = load_json(Path(args.report))
            bindings = binding_config(Path(args.bindings))
            if args.expected_count is not None:
                require(args.expected_count > 0 and len(bindings) == args.expected_count,
                        "EXPECTED_BINDING_COUNT_MISMATCH")
            result = verify_json_model(root, doc, bindings,
                                       strict_claims=not args.allow_unbound_claims)
            for filename in args.text:
                check_markdown(Path(filename))
            result["text_files_checked"] = len(args.text)
        elif args.command == "seal-json":
            root = safe_root(args.root)
            doc = load_json(Path(args.template))
            bindings = binding_config(Path(args.bindings))
            if args.expected_count is not None:
                require(args.expected_count > 0 and len(bindings) == args.expected_count,
                        "EXPECTED_BINDING_COUNT_MISMATCH")
            for entry in bindings:
                digest, _ = file_sha256(root, entry["path"])
                set_pointer(doc, entry["pointer"], digest)
            result = verify_json_model(root, doc, bindings, strict_claims=True)
            require(result["status"] == "PASS", "SOURCE_CHANGED_WHILE_SEALING")
            dest = Path(args.out)
            require(dest.resolve() not in (Path(args.template).resolve(), Path(args.bindings).resolve()),
                    "OUTPUT_MUST_BE_NEW")
            no_clobber_file(dest, json_data_bytes(doc))
            persisted = load_json(dest)
            recheck = verify_json_model(root, persisted, bindings, strict_claims=True)
            require(recheck["status"] == "PASS", "PERSISTED_JSON_NOT_VERIFIED")
            result = {"status": "PASS", "out": str(dest), "verified": len(bindings),
                      "report_sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
        elif args.command == "check-text":
            records = []
            for filename in args.file:
                p = Path(filename)
                if p.suffix.casefold() == ".json":
                    obj = load_json(p)
                    raw = p.read_bytes()
                    records.append({"path": str(p), "kind": "json",
                                    "sha256": hashlib.sha256(raw).hexdigest(),
                                    "bytes": len(raw), "status": "PASS"})
                else:
                    records.append({"kind": "text", "status": "PASS", **check_markdown(p)})
            result = {"status": "PASS", "files": records}
        else:
            raise GuardError("UNKNOWN_COMMAND")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("status") == "PASS" else 2
    except (GuardError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)},
                         indent=2, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
