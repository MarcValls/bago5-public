"""Propuestas selladas de agrupación por contenido; nunca copia ni ejecuta ZIP.

El nombre del ZIP identifica su procedencia, pero no participa en similitud,
identidad de aplicación ni denominación de grupo.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import html
import itertools
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import tempfile
import unicodedata
import zipfile

SCHEMA_VERSION = "zip-auditor-content-grouping-1.0"
LIMITS = {
    "max_report_bytes": 128 * 1024 * 1024,
    "max_archive_bytes": 512 * 1024 * 1024,
    "max_total_archive_hash_bytes": 2 * 1024 * 1024 * 1024,
    "max_zip_entries": 20000,
    "max_central_directory_bytes": 32 * 1024 * 1024,
    "max_declared_uncompressed_bytes": 1024 * 1024 * 1024,
    "max_text_file_bytes": 512 * 1024,
    "max_text_bytes_per_archive": 4 * 1024 * 1024,
    "max_total_text_bytes": 64 * 1024 * 1024,
    "max_text_files_per_archive": 120,
    "max_compression_ratio": 250,
    "max_tokens_per_file": 30000,
    "max_shingles_per_archive": 12000,
    "max_pairs": 10000,
    "max_pair_evidence_per_group": 40,
    "max_source_examples_per_pair": 12,
    "min_text_coverage_for_similarity": 0.65,
}
EXCLUDED_SEGMENTS = {"node_modules", "vendor", "third_party", "third-party", ".venv", "venv", ".git", ".svn",
                     "site-packages", "__pycache__", "dist", "build", "coverage", ".next", "target"}
LOCK_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "uv.lock", "cargo.lock",
              "go.sum", "composer.lock", "pipfile.lock", "bun.lock", "bun.lockb"}
SUPPORT_NAMES = {"package.json", "pyproject.toml", "requirements.txt", "setup.cfg", "tsconfig.json",
                 "jsconfig.json", "dockerfile", ".gitignore", "vite.config.js", "vite.config.ts",
                 "next.config.js", "next.config.mjs", "next-env.d.ts", "vite-env.d.ts"}
CODE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".htm", ".vue", ".svelte", ".go",
                   ".rs", ".java", ".cs", ".cpp", ".c", ".h", ".php", ".rb", ".ps1", ".cmd", ".sh"}
BOILERPLATE_WORDS = set("""the and for with this that from import export default return const let var function class def self
true false null none undefined public private void string number boolean int float bool async await if else elif while
switch case break continue try catch except finally throw raise new extends implements static final pass in of is not
as to a an or on at by it we you your our has have can will do does are was were been be all any each only use using
html head body meta charset title script style div span button input label form section article main header footer
nav ul li table tr td th h1 h2 h3 p br id type name value text content document window console log error event target
queryselector queryselectorall getelementbyid addeventlistener setattribute innerhtml textcontent onclick preventdefault
react usestate useeffect usememo usecallback createelement createroot app root render strictmode reactdom props children
component components interface namespace module require exports path join resolve process env argv sys os json
utf utf8 lang viewport width height flex grid color background display padding margin border solid radius font size
constantes variables funciones funcion functioning elemento elementos el la los las un una unos unas de del y o que
con para por en se es al lo su sus no si como mas más esta este estos estas son sobre entre dentro fuera
""".split())
GENERIC_IDENTITY = set("""app application aplicación aplicacion project proyecto template plantilla boilerplate starter
react vite next nextjs vue svelte typescript javascript python demo prototipo prototype example ejemplo sample test
untitled sin titulo title my new nuevo awesome create ui frontend backend web html version release edition edicion
""".split())
HASH_RE = re.compile(r"^[a-fA-F0-9]{64}$")


def plan_digest(plan: dict) -> str:
    """Única exclusión del sello: su propio campo plan_sha256."""
    content = {key: value for key, value in plan.items() if key != "plan_sha256"}
    encoded = json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _hash(value):
    return isinstance(value, str) and HASH_RE.fullmatch(value) is not None


def _sha_bytes(value):
    return hashlib.sha256(value).hexdigest()


def _normal_file(path: Path, directory=False):
    """Rechaza enlaces/reparse en la ruta completa, sin resolverlos primero."""
    absolute = Path(os.path.abspath(path))
    chain = list(reversed(absolute.parents)) + [absolute]
    for component in chain:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("SYMLINK_OR_REPARSE_POINT")
    info = absolute.lstat()
    if directory and not stat.S_ISDIR(info.st_mode):
        raise ValueError("SOURCE_ROOT_NOT_DIRECTORY")
    if not directory and not stat.S_ISREG(info.st_mode):
        raise ValueError("NOT_A_REGULAR_FILE")
    return absolute, info


def _safe_relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or value.startswith("/"):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def _read_json(path, max_bytes):
    path, info = _normal_file(path)
    if info.st_size > max_bytes:
        raise ValueError("JSON_SIZE_LIMIT")
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), raw


def _load_report(report_path, limits):
    report_path, _ = _normal_file(Path(report_path))
    if report_path.name != "report.json":
        raise ValueError("Se requiere el report.json exacto del análisis verificado.")
    report, raw = _read_json(report_path, limits["max_report_bytes"])
    manifest, _ = _read_json(report_path.parent / "SHA256SUMS.json", 2 * 1024 * 1024)
    verification, _ = _read_json(report_path.parent / "verificacion.json", 8 * 1024 * 1024)
    digest = _sha_bytes(raw)
    expected = manifest.get("report.json") if isinstance(manifest, dict) else None
    if not isinstance(expected, str) or expected.lower() != digest:
        raise ValueError("El report.json no coincide con su SHA-256 verificado.")
    if not isinstance(verification, dict) or verification.get("status") != "PASS":
        raise ValueError("El informe no tiene verificación PASS.")
    if not isinstance(report, dict) or report.get("schema_version") != "0.2" or not isinstance(report.get("archives"), list):
        raise ValueError("Esquema de informe no compatible.")
    root_value = report.get("root")
    if not isinstance(root_value, str) or not Path(root_value).is_absolute():
        raise ValueError("La raíz de fuentes del informe debe ser absoluta.")
    source_root, _ = _normal_file(Path(root_value), directory=True)
    return report_path, report, digest, source_root


def _zip_directory_budget(stream, limits):
    """Acota el directorio central antes de que ZipFile cree objetos de entradas."""
    stream.seek(0, os.SEEK_END)
    size = stream.tell()
    tail_size = min(size, 65535 + 22)
    stream.seek(size - tail_size)
    tail = stream.read(tail_size)
    position = tail.rfind(b"PK\x05\x06")
    while position >= 0:
        if position + 22 <= len(tail):
            comment_size = struct.unpack_from("<H", tail, position + 20)[0]
            if position + 22 + comment_size == len(tail):
                break
        position = tail.rfind(b"PK\x05\x06", 0, position)
    if position < 0:
        raise zipfile.BadZipFile("No se localiza un final de ZIP válido.")
    _, disk, central_disk, disk_entries, total_entries, central_size, central_offset, _ = struct.unpack_from("<4s4H2LH", tail, position)
    if disk or central_disk or disk_entries != total_entries:
        raise ValueError("MULTI_DISK_ZIP_NOT_SUPPORTED")
    if total_entries > limits["max_zip_entries"]:
        raise ValueError("ZIP_ENTRY_LIMIT")
    if central_size == 0xFFFFFFFF or central_offset == 0xFFFFFFFF:
        raise ValueError("ZIP64_DIRECTORY_NOT_SUPPORTED_WITHIN_BUDGET")
    if central_size > limits["max_central_directory_bytes"]:
        raise ValueError("CENTRAL_DIRECTORY_SIZE_LIMIT")
    end_offset = size - tail_size + position
    cursor, stop = end_offset - central_size, end_offset
    if cursor < 0:
        raise ValueError("INVALID_CENTRAL_DIRECTORY")
    actual_count = 0
    while cursor < stop:
        if actual_count >= limits["max_zip_entries"]:
            raise ValueError("ZIP_ENTRY_LIMIT")
        stream.seek(cursor)
        header = stream.read(46)
        if len(header) != 46 or header[:4] != b"PK\x01\x02":
            raise ValueError("INVALID_CENTRAL_DIRECTORY")
        name_size, extra_size, comment_size = struct.unpack_from("<HHH", header, 28)
        cursor += 46 + name_size + extra_size + comment_size
        actual_count += 1
    if cursor != stop or actual_count != total_entries:
        raise ValueError("CENTRAL_DIRECTORY_COUNT_MISMATCH")
    stream.seek(0)


def _role(name):
    parts = PurePosixPath(name.casefold()).parts
    base = parts[-1] if parts else ""
    if any(part in EXCLUDED_SEGMENTS for part in parts) or base in LOCK_NAMES or base.endswith((".lock", ".map", ".min.js", ".min.css")):
        return "excluded"
    if base in SUPPORT_NAMES:
        return "identity" if base in {"package.json", "pyproject.toml"} else "support"
    stem = base.split(".", 1)[0]
    if stem in {"readme", "leeme", "leer_primero"}:
        return "identity"
    if stem in {"license", "licence", "copying", "notice", "authors", "changelog", "changes", "contributing"}:
        return "excluded"
    suffix = PurePosixPath(base).suffix
    if suffix in CODE_EXTENSIONS:
        return "core"
    if suffix in {".md", ".rst", ".txt", ".yaml", ".yml"} and (
            base in {"skill.md", "agents.md", "claude.md"} or "skills" in parts or
            any(word in stem for word in ("contract", "contrat", "instruction", "instruccion", "behavior", "comportamiento"))):
        return "core"
    return "support"


def _identity_label(value):
    if not isinstance(value, str):
        return None
    value = html.unescape(re.sub(r"<[^>]+>", " ", value))
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\bv?\d+(?:\.\d+){1,4}(?:[-_][a-zA-Z0-9]+)?\b|\bv\d+\b", " ", value, flags=re.I)
    value = re.sub(r"\b(?:version|versión|release|prototype|prototipo|demo)\s*\d*\b", " ", value, flags=re.I)
    value = re.sub(r"[@_/|·:+-]+", " ", value)
    words = re.findall(r"[^\W_]+", value, flags=re.UNICODE)
    words = [word for word in words if word.casefold() not in GENERIC_IDENTITY and not word.isdigit()]
    label = " ".join(words).strip()[:100]
    if len(label) < 4:
        return None
    return {"label": label, "key": label.casefold()}


def _identities(text, name):
    base = PurePosixPath(name.casefold()).name
    values = []
    if base == "package.json":
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                values.append((data.get("name"), "package_name", 3))
        except (ValueError, RecursionError):
            pass
    elif base == "pyproject.toml":
        try:
            import tomllib
            data = tomllib.loads(text)
            values.append(((data.get("project") or {}).get("name"), "project_name", 3))
            values.append((((data.get("tool") or {}).get("poetry") or {}).get("name"), "project_name", 3))
        except (ImportError, ValueError, TypeError, AttributeError, RecursionError):
            pass
    if PurePosixPath(base).suffix in {".html", ".htm", ".vue", ".svelte"}:
        values += [(match, "html_title", 3) for match in re.findall(r"<title[^>]*>(.{0,300}?)</title\s*>", text, flags=re.I | re.S)[:2]]
        values += [(match, "heading", 1) for match in re.findall(r"<h1[^>]*>(.{0,300}?)</h1\s*>", text, flags=re.I | re.S)[:2]]
    if base.startswith(("readme", "leeme")) or base in {"skill.md", "agents.md"}:
        values += [(match, "readme_heading" if base.startswith(("readme", "leeme")) else "skill_heading", 2)
                   for match in re.findall(r"^#\s+(.{1,150})$", text, flags=re.M)[:2]]
    if base == "skill.md":
        match = re.search(r"\A\s*---\s*\n(.{0,5000}?)\n---", text, flags=re.S)
        if match:
            values += [(value.strip("\"' "), "skill_name", 3)
                       for value in re.findall(r"^name:\s*(.{1,150})$", match.group(1), flags=re.M)[:1]]
    values += [(value, "application_title", 2) for value in re.findall(
        r"(?:\.title\s*\(|\btitle\s*=\s*)[\"']([^\"'\r\n]{4,120})[\"']", text)[:2]]
    result = []
    for value, kind, weight in values:
        identity = _identity_label(value)
        if identity:
            result.append(dict(identity, kind=kind, weight=weight, internal_path=name))
    return result


def _core_text(text, name):
    suffix = PurePosixPath(name.casefold()).suffix
    if suffix in {".html", ".htm", ".vue", ".svelte"}:
        scripts = []
        for attrs, body in re.findall(r"<script\b([^>]*)>(.*?)</script\s*>", text, flags=re.I | re.S):
            if not re.search(r"\bsrc\s*=", attrs, flags=re.I) and not re.search(r"type\s*=\s*['\"]application/(?:ld\+)?json", attrs, flags=re.I):
                scripts.append(body)
        visible = re.sub(r"<(style|script|title)\b[^>]*>.*?</\1\s*>", " ", text, flags=re.I | re.S)
        visible = re.sub(r"<!--.*?-->", " ", visible, flags=re.S)
        visible = html.unescape(re.sub(r"<[^>]*>", " ", visible))
        text = "\n".join(scripts) + "\n" + visible
    # Framework imports and dependency lists are corroboration, not application identity.
    text = re.sub(r"^\s*(?:from\s+\S+\s+import|import\s).*$", " ", text, flags=re.M)
    text = re.sub(r"\b(?:require|import)\s*\([^)]*\)", " ", text)
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    words = re.findall(r"[^\W\d]\w*", text.casefold(), flags=re.UNICODE)
    return [word for word in words if len(word) > 2 and word not in BOILERPLATE_WORDS]


def _shingles(tokens):
    return {int.from_bytes(hashlib.blake2b("\x1f".join(tokens[i:i + 5]).encode("utf-8"), digest_size=8).digest(), "big")
            for i in range(max(0, len(tokens) - 4))}


def _profile(archive, source_root, budget, limits):
    relative = archive.get("zip")
    reported_hash = archive.get("zip_sha256")
    identity = str(relative) + "\0" + str(reported_hash)
    record = {"id": "A-" + _sha_bytes(identity.encode("utf-8"))[:18],
              "relative_path": str(relative), "sha256": reported_hash.lower() if _hash(reported_hash) else None,
              "size_bytes": 0, "eligible": False, "issues": []}
    profile = {"record": record, "archive_status": archive.get("status", "UNKNOWN"),
               "identities": [], "core_files": [], "core_hashes": {}, "shingles": set(), "tokens": set(),
               "all_core_files": [], "all_core_tokens": set(),
               "core_bytes_total": 0, "core_bytes_read": 0, "text_bytes_read": 0,
               "text_files_read": 0, "excluded_files": 0, "source_files_considered": 0,
               "notes": [], "extensions": Counter(), "coverage": 0.0}
    try:
        if not _safe_relative(relative) or not str(relative).casefold().endswith(".zip"):
            raise ValueError("UNSAFE_SOURCE_RELATIVE_PATH")
        if not _hash(reported_hash):
            raise ValueError("MISSING_SOURCE_HASH")
        source, before = _normal_file(source_root.joinpath(*PurePosixPath(relative).parts))
        record["size_bytes"] = before.st_size
        if before.st_size > limits["max_archive_bytes"]:
            raise ValueError("ARCHIVE_SIZE_LIMIT")
        if budget["archive_bytes"] + before.st_size > limits["max_total_archive_hash_bytes"]:
            raise ValueError("TOTAL_ARCHIVE_HASH_LIMIT")
        budget["archive_bytes"] += before.st_size
        with source.open("rb") as stream:
            digest = hashlib.sha256()
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
            if digest.hexdigest() != record["sha256"]:
                raise ValueError("SOURCE_HASH_MISMATCH")
            stream.seek(0)
            _zip_directory_budget(stream, limits)
            with zipfile.ZipFile(stream) as zipped:
                infos = zipped.infolist()
                if len(infos) > limits["max_zip_entries"]:
                    raise ValueError("ZIP_ENTRY_LIMIT")
                if sum(info.file_size for info in infos) > limits["max_declared_uncompressed_bytes"]:
                    raise ValueError("DECLARED_UNCOMPRESSED_SIZE_LIMIT")
                entries = archive.get("entries")
                if not isinstance(entries, list):
                    raise ValueError("INVALID_ENTRY_INVENTORY")
                indexes = set()
                candidates = []
                for entry in entries:
                    if not isinstance(entry, dict):
                        raise ValueError("INVALID_ENTRY_INVENTORY")
                    index = entry.get("entry_index")
                    if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(infos) or index in indexes:
                        raise ValueError("ENTRY_INDEX_MISMATCH")
                    indexes.add(index)
                    info = infos[index]
                    if (info.is_dir() or info.filename != entry.get("path") or info.file_size != entry.get("size") or
                            info.compress_size != entry.get("compressed_size")):
                        raise ValueError("ENTRY_METADATA_MISMATCH")
                    logical = entry.get("logical_path", info.filename)
                    if not _safe_relative(logical) or not _safe_relative(info.filename):
                        profile["notes"].append("UNSAFE_MEMBER_PATH_NOT_USED")
                        continue
                    if stat.S_ISLNK(info.external_attr >> 16):
                        profile["notes"].append("SYMLINK_MEMBER_NOT_USED")
                        continue
                    role = _role(logical)
                    if role in {"excluded", "support"}:
                        profile["excluded_files"] += 1
                        continue
                    if role == "core":
                        profile["core_bytes_total"] += info.file_size
                        profile["source_files_considered"] += 1
                    candidates.append((role != "identity", logical.casefold(), entry, info, role))
                if archive.get("status") == "ANALYZED" and len(indexes) != sum(not info.is_dir() for info in infos):
                    raise ValueError("ENTRY_INVENTORY_INCOMPLETE")
                # Content-derived order: archive entry order and outer folder names cannot select different samples.
                candidates.sort(key=lambda item: (item[0], item[1], item[2].get("sha256") or ""))
                for _, _, entry, info, role in candidates:
                    if not _hash(entry.get("sha256")) or entry.get("status") != "ANALYZED" or entry.get("issues"):
                        profile["notes"].append("ENTRY_NOT_FULLY_ANALYZED")
                        continue
                    if info.flag_bits & 1:
                        profile["notes"].append("ENCRYPTED_MEMBER_NOT_READ")
                        continue
                    if (info.file_size > limits["max_text_file_bytes"] or
                            info.file_size / max(info.compress_size, 1) > limits["max_compression_ratio"]):
                        profile["notes"].append("TEXT_FILE_OR_RATIO_LIMIT")
                        continue
                    if (profile["text_files_read"] >= limits["max_text_files_per_archive"] or
                            profile["text_bytes_read"] + info.file_size > limits["max_text_bytes_per_archive"] or
                            budget["text_bytes"] + info.file_size > limits["max_total_text_bytes"]):
                        profile["notes"].append("TEXT_BUDGET_LIMIT")
                        continue
                    with zipped.open(info) as member:
                        data = member.read(limits["max_text_file_bytes"] + 1)
                    if len(data) != info.file_size or len(data) > limits["max_text_file_bytes"]:
                        raise ValueError("MEMBER_READ_SIZE_MISMATCH")
                    if _sha_bytes(data) != entry["sha256"].lower():
                        raise ValueError("MEMBER_HASH_MISMATCH")
                    budget["text_bytes"] += len(data)
                    profile["text_bytes_read"] += len(data)
                    profile["text_files_read"] += 1
                    try:
                        text = data.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        profile["notes"].append("NON_UTF8_SOURCE_NOT_COMPARED")
                        continue
                    logical = entry.get("logical_path", info.filename)
                    profile["identities"].extend(_identities(text, logical))
                    if role != "core":
                        continue
                    profile["core_bytes_read"] += len(data)
                    extension = PurePosixPath(logical.casefold()).suffix
                    lines = text.splitlines() or [text]
                    if extension in {".js", ".ts", ".jsx", ".tsx"} and len(text) > 2000 and max(map(len, lines)) > 3000 and len(text) / len(lines) > 500:
                        profile["notes"].append("MINIFIED_SOURCE_NOT_USED")
                        continue
                    tokens = _core_text(text, logical)
                    if len(tokens) > limits["max_tokens_per_file"]:
                        tokens = tokens[:limits["max_tokens_per_file"]]
                        profile["notes"].append("TOKEN_LIMIT")
                    profile["all_core_files"].append({"internal_path": logical, "sha256": entry["sha256"].lower(),
                                                     "tokens": len(tokens)})
                    profile["all_core_tokens"].update(word for token in tokens for word in token.split("_") if len(word) >= 4)
                    # Tiny scaffolding/import-only files cannot identify an application.
                    if len(tokens) < 32 or len(set(tokens)) < 12:
                        profile["notes"].append("LOW_INFORMATION_SOURCE")
                        continue
                    file_shingles = _shingles(tokens)
                    profile["shingles"].update(file_shingles)
                    profile["tokens"].update(tokens)
                    digest = entry["sha256"].lower()
                    weight = min(len(tokens), 10000)
                    profile["core_hashes"][digest] = max(weight, profile["core_hashes"].get(digest, 0))
                    profile["core_files"].append({"internal_path": logical, "sha256": digest,
                                                   "tokens": len(tokens), "distinct_tokens": len(set(tokens))})
                    profile["extensions"][extension] += 1
            after = source.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise ValueError("SOURCE_CHANGED_DURING_READ")
        record["eligible"] = True
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, NotImplementedError, EOFError) as exc:
        record["issues"].append(str(exc) if isinstance(exc, ValueError) else type(exc).__name__ + ": " + str(exc))
    if archive.get("status") != "ANALYZED":
        profile["notes"].append("ORIGINAL_ANALYSIS_INCOMPLETE")
    profile["coverage"] = profile["core_bytes_read"] / profile["core_bytes_total"] if profile["core_bytes_total"] else 0.0
    if not profile["core_bytes_total"]:
        profile["notes"].append("NO_OWN_SOURCE_CONTENT")
    elif profile["coverage"] < limits["min_text_coverage_for_similarity"]:
        profile["notes"].append("LOW_SOURCE_TEXT_COVERAGE")
    if len(profile["shingles"]) > limits["max_shingles_per_archive"]:
        profile["shingles"] = set(sorted(profile["shingles"])[:limits["max_shingles_per_archive"]])
        profile["notes"].append("SHINGLE_SKETCH_LIMIT")
    profile["notes"] = sorted(set(profile["notes"]))
    record["issues"] = sorted(set(record["issues"] + profile["notes"]))
    profile["identity_keys"] = {item["key"] for item in profile["identities"]}
    signature = {"source_hashes": sorted(profile["core_hashes"]), "shingles": sorted(profile["shingles"]),
                 "all_core_hashes": sorted(item["sha256"] for item in profile["all_core_files"]),
                 "identities": sorted(profile["identity_keys"])}
    profile["fingerprint"] = _sha_bytes(json.dumps(signature, sort_keys=True, separators=(",", ":")).encode())
    return profile


def _pair(left, right, limits):
    left_id, right_id = left["record"]["id"], right["record"]["id"]
    identical = left["record"]["sha256"] == right["record"]["sha256"]
    common_hashes = set(left["core_hashes"]) & set(right["core_hashes"])
    shared_weight = sum(min(left["core_hashes"][digest], right["core_hashes"][digest]) for digest in common_hashes)
    exact_left = shared_weight / max(sum(left["core_hashes"].values()), 1)
    exact_right = shared_weight / max(sum(right["core_hashes"].values()), 1)
    shared_shingles = len(left["shingles"] & right["shingles"])
    union = len(left["shingles"] | right["shingles"])
    jaccard = shared_shingles / max(union, 1)
    contained_left = shared_shingles / max(len(left["shingles"]), 1)
    contained_right = shared_shingles / max(len(right["shingles"]), 1)
    identity_common = sorted(left["identity_keys"] & right["identity_keys"])
    identity_words = {word for key in identity_common for word in key.split() if len(word) >= 4 and word not in GENERIC_IDENTITY}
    code_identity_anchors = sorted(identity_words & left["all_core_tokens"] & right["all_core_tokens"])
    all_left_hashes = Counter(item["sha256"] for item in left["all_core_files"])
    all_right_hashes = Counter(item["sha256"] for item in right["all_core_files"])
    small_exact_inventory = bool(all_left_hashes and all_left_hashes == all_right_hashes and
                                 len(left["all_core_files"]) >= 2 and code_identity_anchors)
    coverage_ok = (left["coverage"] >= limits["min_text_coverage_for_similarity"] and
                   right["coverage"] >= limits["min_text_coverage_for_similarity"] and
                   left["archive_status"] == right["archive_status"] == "ANALYZED" and
                   not any(note in {"UNSAFE_MEMBER_PATH_NOT_USED", "SYMLINK_MEMBER_NOT_USED", "ENTRY_NOT_FULLY_ANALYZED"}
                           for note in left["notes"] + right["notes"]))
    rule, qualifies, score = "INSUFFICIENT_CONTENT_EVIDENCE", False, 0.0
    if identical:
        rule, qualifies, score = "EXACT_ZIP_BYTES", True, 1.0
    elif coverage_ok and small_exact_inventory:
        rule, qualifies, score = "EXACT_OWN_CODE_WITH_DOMAIN_IDENTITY", True, 0.84
    elif coverage_ok and shared_weight >= 60 and min(exact_left, exact_right) >= (0.65 if identity_common else 0.85):
        rule, qualifies, score = "SUBSTANTIAL_OWN_SOURCE_IDENTITY", True, 0.8 + 0.19 * min(exact_left, exact_right)
    elif coverage_ok and shared_shingles >= 20 and jaccard >= 0.62:
        rule, qualifies, score = "STRONG_OWN_CONTENT_SIMILARITY", True, 0.65 + 0.3 * jaccard
    elif (coverage_ok and identity_common and shared_shingles >= 18 and jaccard >= 0.40 and
          min(contained_left, contained_right) >= 0.50 and max(contained_left, contained_right) >= 0.80):
        rule, qualifies, score = "CONTENT_SIMILARITY_WITH_DECLARED_IDENTITY", True, 0.65 + 0.25 * jaccard
    elif (coverage_ok and identity_common and shared_weight >= 80 and
          min(exact_left, exact_right) >= 0.35 and max(exact_left, exact_right) >= 0.90):
        rule, qualifies, score = "OWN_SOURCE_INCLUSION_WITH_DECLARED_IDENTITY", True, 0.65 + 0.2 * min(exact_left, exact_right)
    elif not coverage_ok:
        rule = "INCOMPLETE_SOURCE_COVERAGE"
    examples = []
    for digest in sorted(common_hashes):
        lfiles = sorted(item["internal_path"] for item in left["core_files"] if item["sha256"] == digest)
        rfiles = sorted(item["internal_path"] for item in right["core_files"] if item["sha256"] == digest)
        examples.append({"sha256": digest, "left_internal_paths": lfiles[:4], "right_internal_paths": rfiles[:4]})
    return {"left_id": left_id, "right_id": right_id, "qualifies": qualifies, "rule": rule,
            "score": round(score, 6), "declared_identity_corroboration": identity_common,
            "identity_words_observed_in_code": code_identity_anchors,
            "exact_complete_own_code_inventory": small_exact_inventory,
            "metrics": {"own_exact_source_hashes": len(common_hashes), "own_exact_token_weight": shared_weight,
                        "exact_coverage_left": round(exact_left, 6), "exact_coverage_right": round(exact_right, 6),
                        "shared_token_shingles": shared_shingles, "shingle_jaccard": round(jaccard, 6),
                        "shingle_containment_left": round(contained_left, 6), "shingle_containment_right": round(contained_right, 6),
                        "source_text_coverage_left": round(left["coverage"], 6), "source_text_coverage_right": round(right["coverage"], 6)},
            "source_examples": examples[:limits["max_source_examples_per_pair"]],
            "source_examples_omitted": max(0, len(examples) - limits["max_source_examples_per_pair"]),
            "functional_equivalence": "NOT_VERIFIED"}


def _group_name(members):
    counts, labels, weights = Counter(), {}, Counter()
    for member in members:
        present = set()
        for identity in member["identities"]:
            key = identity["key"]
            labels.setdefault(key, set()).add(identity["label"])
            weights[key] += identity["weight"]
            present.add(key)
        counts.update(present)
    if counts:
        chosen = sorted(counts, key=lambda key: (-counts[key], -weights[key], key))[0]
        label = sorted(labels[chosen], key=lambda value: (value.casefold(), value))[0]
        return label, {"kind": "INTERNAL_DECLARED_IDENTITY", "identity_key": chosen,
                       "members_declaring_identity": counts[chosen], "member_count": len(members)}
    types = Counter()
    for member in members:
        types.update(member["extensions"])
    if any(types.get(ext) for ext in (".html", ".htm", ".vue", ".svelte")):
        label = "Aplicación web HTML"
    elif types.get(".py"):
        label = "Aplicación Python"
    elif any(types.get(ext) for ext in (".js", ".jsx", ".ts", ".tsx")):
        label = "Aplicación JavaScript"
    elif types.get(".md"):
        label = "Agente o instrucciones"
    elif types:
        label = "Componentes de código"
    else:
        label = "Contenido sin identidad suficiente"
    return label, {"kind": "DESCRIPTIVE_FALLBACK", "file_types": dict(sorted(types.items())),
                   "limitation": "El contenido disponible no permite afirmar el nombre de la aplicación."}


def _directory_name(label, suffix):
    value = unicodedata.normalize("NFKC", label)
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", "_", value).strip(" ._")[:60].rstrip(" ._")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    if not value or value.split(".", 1)[0].upper() in reserved:
        value = "Contenido"
    return value + "__" + suffix


def _make_groups(profiles, pairs, limits):
    clusters = []
    for profile in profiles:
        candidates = []
        for position, members in enumerate(clusters):
            links = [pairs.get(tuple(sorted((profile["record"]["id"], other["record"]["id"])))) for other in members]
            if links and all(link and link["qualifies"] for link in links):
                candidates.append((min(link["score"] for link in links), -position, position))
        if candidates:
            clusters[max(candidates)[2]].append(profile)
        else:
            clusters.append([profile])
    groups = []
    for members in clusters:
        member_ids = sorted(member["record"]["id"] for member in members)
        content_signature = sorted(member["fingerprint"] for member in members)
        group_hash = _sha_bytes(json.dumps(content_signature, separators=(",", ":")).encode())
        # Source hashes distinguish content-free or identical-profile singleton directories.
        distinction = _sha_bytes((group_hash + "|" + "|".join(member_ids)).encode())[:10]
        label, naming = _group_name(members)
        evidence = [pairs[tuple(sorted((a["record"]["id"], b["record"]["id"])))]
                    for a, b in itertools.combinations(members, 2)]
        minimum = min((item["score"] for item in evidence), default=0.0)
        groups.append({"id": "G-" + distinction, "directory_name": _directory_name(label, distinction),
                       "label": label, "member_ids": member_ids,
                       "confidence": "ALTA" if minimum >= 0.80 else "MEDIA" if evidence else "NO_ESTABLECIDA",
                       "status": "PROPOSED" if len(members) > 1 else "SIN_COINCIDENCIAS",
                       "evidence": {"complete_link": True, "naming": naming,
                                    "pairs": evidence[:limits["max_pair_evidence_per_group"]],
                                    "pair_count": len(evidence), "pairs_omitted": max(0, len(evidence) - limits["max_pair_evidence_per_group"]),
                                    "member_content_profiles": [{"archive_id": member["record"]["id"],
                                        "meaningful_own_sources": len(member["core_files"]),
                                        "text_files_read": member["text_files_read"],
                                        "source_text_coverage": round(member["coverage"], 6),
                                        "notes": member["notes"]} for member in members]},
                       "functional_equivalence": "NOT_VERIFIED"})
    return sorted(groups, key=lambda group: (group["label"].casefold(), group["id"]))


def build_proposal(report_path: Path) -> dict:
    """Sólo lectura. Devuelve todos los campos definitivos y el sello canónico."""
    limits = dict(LIMITS)
    report_path, report, report_sha, source_root = _load_report(report_path, limits)
    source_rows = report["archives"]
    if not all(isinstance(row, dict) and isinstance(row.get("zip"), str) for row in source_rows):
        raise ValueError("Inventario de ZIP no válido.")
    relative_paths = [row["zip"].casefold() for row in source_rows]
    if len(set(relative_paths)) != len(relative_paths):
        raise ValueError("El informe repite rutas de ZIP o contiene una colisión de mayúsculas.")
    # Names are used only for reading exact source files; sampling order uses recorded hashes.
    source_rows = sorted(source_rows, key=lambda row: (str(row.get("zip_sha256")), row["zip"]))
    budget = {"archive_bytes": 0, "text_bytes": 0}
    profiles = [_profile(row, source_root, budget, limits) for row in source_rows]
    eligible = sorted((profile for profile in profiles if profile["record"]["eligible"]),
                      key=lambda profile: (profile["fingerprint"], profile["record"]["sha256"], profile["record"]["id"]))
    pairs = {}
    examined = 0
    for left, right in itertools.islice(itertools.combinations(eligible, 2), limits["max_pairs"]):
        pair = _pair(left, right, limits)
        pairs[tuple(sorted((left["record"]["id"], right["record"]["id"])))] = pair
        examined += 1
    groups = _make_groups(eligible, pairs, limits)
    memberships = [identifier for group in groups for identifier in group["member_ids"]]
    if sorted(memberships) != sorted(profile["record"]["id"] for profile in eligible):
        raise ValueError("Invariante de partición incumplido.")
    possible = len(eligible) * (len(eligible) - 1) // 2
    grouped_count = sum(len(group["member_ids"]) for group in groups if len(group["member_ids"]) > 1)
    effective_limits = {"TEXT_FILE_OR_RATIO_LIMIT", "TEXT_BUDGET_LIMIT", "TOKEN_LIMIT", "SHINGLE_SKETCH_LIMIT",
                        "NON_UTF8_SOURCE_NOT_COMPARED", "ORIGINAL_ANALYSIS_INCOMPLETE", "LOW_SOURCE_TEXT_COVERAGE",
                        "UNSAFE_MEMBER_PATH_NOT_USED", "SYMLINK_MEMBER_NOT_USED", "ENTRY_NOT_FULLY_ANALYZED",
                        "ENCRYPTED_MEMBER_NOT_READ"}
    triggered = sorted({note for profile in profiles for note in profile["notes"] if note in effective_limits})
    coverage = {"archives_in_report": len(profiles), "eligible_archives": len(eligible),
                "ineligible_archives": len(profiles) - len(eligible), "possible_pairs": possible,
                "examined_pairs": examined, "unexamined_pairs": possible - examined,
                "qualifying_pairs": sum(pair["qualifies"] for pair in pairs.values()),
                "groups_with_multiple_archives": sum(len(group["member_ids"]) > 1 for group in groups),
                "archives_in_multiple_member_groups": grouped_count,
                "singleton_groups": sum(len(group["member_ids"]) == 1 for group in groups),
                "archive_bytes_hashed": budget["archive_bytes"], "text_bytes_read": budget["text_bytes"],
                "source_text_files_read": sum(profile["text_files_read"] for profile in profiles),
                "archives_with_limited_source_coverage": sum(profile["core_bytes_total"] > 0 and profile["coverage"] < limits["min_text_coverage_for_similarity"] for profile in eligible),
                "archives_with_low_information_sources": sum("LOW_INFORMATION_SOURCE" in profile["notes"] for profile in eligible),
                "archives_without_own_source_content": sum(not profile["core_bytes_total"] for profile in eligible),
                "effective_limits_triggered": triggered,
                "status": "LIMITED" if examined < possible or triggered or len(eligible) < len(profiles) else "COMPLETE_WITHIN_DECLARED_SCOPE"}
    console = ["Propuesta de agrupación por contenido — preparar esta propuesta no crea copias.",
               f"{len(eligible)} ZIP elegibles; {coverage['groups_with_multiple_archives']} grupos con versiones o contenidos relacionados; {coverage['singleton_groups']} ZIP separados por falta de evidencia suficiente."]
    for group in groups[:8]:
        console.append(f"{group['label']} · {len(group['member_ids'])} ZIP · {group['confidence']} → {group['directory_name']}")
    if len(groups) > 8:
        console.append(f"Hay {len(groups) - 8} grupos adicionales en la propuesta detallada.")
    if coverage["ineligible_archives"]:
        console.append(f"{coverage['ineligible_archives']} ZIP quedan excluidos por incidencias de identidad, lectura o límites.")
    console.append("Aceptar la propuesta sólo permite copiar los ZIP intactos; no mezcla programas ni acredita equivalencia funcional.")
    plan = {"schema_version": SCHEMA_VERSION, "status": "PROPOSED", "report_path": str(report_path),
            "report_sha256": report_sha, "source_root": str(source_root),
            "archives": sorted((profile["record"] for profile in profiles), key=lambda item: item["id"]),
            "groups": groups, "coverage": coverage, "limits": limits,
            "interpretation_limits": [
                "Los nombres de archivo ZIP no se usan como señal de similitud ni para nombrar grupos.",
                "Las señales son estáticas y acotadas: fuentes propias, tokens y coincidencias de contenido. No se ejecuta ningún miembro.",
                "Manifiestos, títulos y encabezados sólo corroboran coincidencias de contenido; nunca bastan por sí solos.",
                "Dependencias, locks, vendor, artefactos compilados y documentación genérica no identifican por sí solos una aplicación.",
                "Todo par de miembros de un grupo debe superar el criterio; no se agrupa por una cadena transitiva sin evidencia directa.",
                "Una aplicación reescrita, ofuscada, minificada o con poco texto puede quedar separada. La detección no es perfecta.",
                "La similitud no demuestra equivalencia funcional, versiones compatibles ni autorización de redistribución.",
                "Los grupos proponen carpetas para copias intactas de los ZIP. No extraen, fusionan ni sustituyen contenidos.",
                "Los límites y cambios concurrentes de las fuentes se registran; la copia debe volver a verificar identidades tras aceptación.",
            ], "console_lines": console,
            "paths": {"json": str(report_path.parent / "PROPUESTA_AGRUPACION.json"),
                      "html": str(report_path.parent / "PROPUESTA_AGRUPACION.html")}}
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def _render(plan):
    escape = lambda value: html.escape(str(value), quote=True)
    archives = {item["id"]: item for item in plan["archives"]}
    cards = []
    for group in plan["groups"]:
        rows = "".join("<tr><td>" + escape(archives[identifier]["relative_path"]) + "</td><td>" +
                       escape(archives[identifier]["size_bytes"]) + "</td><td><code>" + escape(archives[identifier]["sha256"]) +
                       "</code></td></tr>" for identifier in group["member_ids"])
        signals = "".join("<li>" + escape(pair["rule"]) + ": similitud de secuencias " +
                          escape(round(pair["metrics"]["shingle_jaccard"] * 100, 1)) + "% · " +
                          escape(pair["metrics"]["own_exact_source_hashes"]) + " fuentes propias idénticas · identidad declarada compartida: " +
                          escape(", ".join(pair["declared_identity_corroboration"]) or "no requerida/no disponible") + ".</li>"
                          for pair in group["evidence"]["pairs"])
        notes = "".join("<li>" + escape(archives[profile["archive_id"]]["relative_path"]) + ": " +
                        escape(profile["meaningful_own_sources"]) + " fuentes propias con información; cobertura textual " +
                        escape(round(profile["source_text_coverage"] * 100, 1)) + "%" +
                        ("; " + escape(", ".join(profile["notes"])) if profile["notes"] else "") + ".</li>"
                        for profile in group["evidence"]["member_content_profiles"])
        cards.append(f'''<article><div class="eyebrow">{escape(group['confidence'])} · {escape(group['status'])}</div><h2>{escape(group['label'])}</h2><p>Carpeta propuesta: <code>{escape(group['directory_name'])}</code></p><table><thead><tr><th>ZIP original</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{rows}</tbody></table><details><summary>Por qué se propone este grupo</summary><p>Origen del nombre: {escape(group['evidence']['naming']['kind'])}. Se exige evidencia directa entre todos sus miembros.</p><ul>{signals or '<li>No hay una coincidencia suficientemente fuerte con otro paquete; se conserva separado.</li>'}</ul><ul>{notes}</ul><p>Comparaciones del grupo: {group['evidence']['pair_count']}; evidencias omitidas en esta vista: {group['evidence']['pairs_omitted']}. El JSON contiene métricas, hashes y rutas internas de las evidencias incluidas.</p></details></article>''')
    excluded = "".join("<li>" + escape(item["relative_path"]) + ": " + escape(", ".join(item["issues"])) + "</li>"
                       for item in plan["archives"] if not item["eligible"])
    coverage = plan["coverage"]
    limits = "".join("<li>" + escape(value) + "</li>" for value in plan["interpretation_limits"])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ZIP Auditor · Agrupación por contenido</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#f2f5f7;color:#18303e;font:16px/1.6 system-ui}}main{{max-width:1180px;margin:auto;padding:36px 24px 64px}}header{{background:#123444;color:white;border-radius:17px;padding:28px}}header a{{color:#b9f1de}}h1{{font-size:34px;line-height:1.2}}h2{{font-size:22px;overflow-wrap:anywhere}}article,.panel{{background:white;border:1px solid #d5e1e7;border-radius:14px;padding:23px;margin:20px 0}}.eyebrow{{font-size:12px;font-weight:750;letter-spacing:.09em}}.notice{{padding:17px;border-left:4px solid #c99124;background:#fff1d7;border-radius:8px}}table{{width:100%;border-collapse:collapse;font-size:13px;table-layout:fixed}}td,th{{border-bottom:1px solid #dbe5eb;padding:10px;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{background:#f2f7f9}}code{{font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}}details{{margin-top:20px}}summary{{font-weight:650;cursor:pointer}}li{{margin:8px 0;overflow-wrap:anywhere}}.meta{{font-size:14px;color:#536f7e}}@media(max-width:600px){{main{{padding:15px}}header,article{{padding:18px}}th,td{{padding:6px}}}}</style></head><body><main><header><div class="eyebrow">ZIP AUDITOR 0.3.0 · PROPUESTA REVISABLE</div><h1>Agrupar versiones y prototipos por su contenido</h1><p>Los nombres de los ZIP no determinan los grupos. Cada carpeta propuesta conserva los ZIP originales como archivos separados.</p><a href="report.html">Informe detallado</a> · <a href="PROPUESTA_AGRUPACION.json">Plan sellado JSON</a></header><p class="notice"><b>Esta propuesta no crea copias por sí sola.</b> La interfaz mostrará el destino dentro de la carpeta de resultados y pedirá aceptar antes de copiar. Consulta el estado de aplicación en el menú o en el manifiesto de la copia. No se mezclan ni ejecutan programas.</p><section class="panel"><p><b>{coverage['eligible_archives']}</b> ZIP elegibles · <b>{coverage['groups_with_multiple_archives']}</b> grupos con varios paquetes · <b>{coverage['singleton_groups']}</b> grupos individuales · <b>{coverage['ineligible_archives']}</b> excluidos.</p><p class="meta">Parejas examinadas: {coverage['examined_pairs']} / {coverage['possible_pairs']}. Cobertura: {escape(coverage['status'])}. Texto leído: {coverage['text_bytes_read']} bytes.</p><p>Carpeta de origen: <code>{escape(plan['source_root'])}</code></p></section>{''.join(cards)}{'<section class="panel"><h2>Fuentes excluidas de la copia propuesta</h2><ul>' + excluded + '</ul></section>' if excluded else ''}<section class="panel"><h2>Alcance y límites</h2><ul>{limits}</ul><p class="meta">SHA-256 del plan: <code>{escape(plan['plan_sha256'])}</code></p><p class="meta">SHA-256 del informe: <code>{escape(plan['report_sha256'])}</code></p></section></main></body></html>'''


def _write_atomic(path, content):
    if path.is_symlink():
        raise ValueError("No se reemplaza un enlace existente.")
    fd, temporary = tempfile.mkstemp(prefix=".propuesta_", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_proposal(report_path: Path) -> dict:
    plan = build_proposal(report_path)
    _write_atomic(Path(plan["paths"]["json"]), json.dumps(plan, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    _write_atomic(Path(plan["paths"]["html"]), _render(plan))
    return plan
