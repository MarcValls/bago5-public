"""Copy an accepted grouping plan transactionally; never extract or move ZIPs.

The plan digest detects accidental changes, not the identity of its author.
Publication is an atomic, no-replacement directory rename on Windows/Linux.
"""
from datetime import datetime, timezone
import ctypes
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile


SCHEMA = "zip-auditor-content-grouping-1.0"
OUTPUT_NAME = "PAQUETES_AGRUPADOS"
MANIFEST_NAME = "MANIFIESTO_COPIAS.json"
README_NAME = "LEEME_COPIAS.txt"
CHUNK_SIZE = 1024 * 1024
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
_RESERVED.update(prefix + digit for prefix in ("COM", "LPT")
                 for digit in "123456789¹²³")


class GroupingError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def plan_digest(plan):
    """Match content_grouping.plan_digest, excluding only plan_sha256."""
    data = {key: value for key, value in plan.items() if key != "plan_sha256"}
    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _fail(code, message):
    raise GroupingError(code, message)


def _valid_hash(value, label):
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        _fail("INVALID_PLAN", "SHA-256 no valido: " + label)
    return value.lower()


def _component(name, label):
    if (not isinstance(name, str) or not name or name in (".", "..") or
            any(char in '<>:"/\\|?*' or ord(char) < 32 for char in name) or
            name.endswith((" ", "."))):
        _fail("UNSAFE_PATH", "Nombre de ruta no valido para Windows: " + label)
    device = name.split(".", 1)[0].rstrip(" .").upper()
    if device in _RESERVED or len(name.encode("utf-16-le")) // 2 > 255:
        _fail("UNSAFE_PATH", "Nombre reservado o demasiado largo: " + label)
    return name


def _io_path(value):
    """Use extended Windows paths only for IO, retaining lexical validation paths."""
    path = os.path.abspath(os.fspath(value))
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return Path(path)
    if path.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + path[2:])
    return Path("\\\\?\\" + path)


def _absolute_path(value, label):
    if not isinstance(value, (str, os.PathLike)):
        _fail("UNSAFE_PATH", "La ruta debe ser absoluta: " + label)
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        _fail("UNSAFE_PATH", "La ruta debe ser absoluta y sin '..': " + label)
    for part in path.parts:
        if part != path.anchor:
            _component(part, label)
    return path


def _is_link(info):
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & _REPARSE_POINT)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _cross_api_identity(info):
    # Windows stat/lstat and fstat can expose different meanings of ctime.
    # Keep ctime in same-API comparisons; never mix those two timestamps.
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _directory_identity(info):
    return info.st_dev, info.st_ino


def _check_directory_chain(path, must_exist=True):
    """Check lexical ancestors before any resolve can hide a link."""
    chain = list(reversed(path.parents)) + [path]
    for item in chain:
        try:
            info = _io_path(item).lstat()
        except FileNotFoundError:
            if must_exist:
                _fail("MISSING_PATH", "No existe la carpeta: " + str(item))
            return
        if _is_link(info):
            _fail("LINK_NOT_ALLOWED", "No se admiten enlaces o puntos de reanalisis: " + str(item))
        if not stat.S_ISDIR(info.st_mode):
            _fail("UNSAFE_PATH", "Se esperaba una carpeta: " + str(item))


def _regular_info(path):
    _check_directory_chain(path.parent)
    try:
        info = _io_path(path).lstat()
    except FileNotFoundError:
        _fail("SOURCE_MISSING", "Falta el archivo: " + str(path))
    if _is_link(info) or not stat.S_ISREG(info.st_mode):
        _fail("LINK_NOT_ALLOWED", "El origen debe ser un archivo normal, sin enlaces: " + str(path))
    return info


def _open_readonly(path):
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    return os.fdopen(os.open(_io_path(path), flags), "rb")


def _verified_snapshot(path, expected_hash, expected_size=None, previous=None):
    before = _regular_info(path)
    if expected_size is not None and before.st_size != expected_size:
        _fail("SOURCE_CHANGED", "El tamano del archivo ha cambiado: " + str(path))
    if previous is not None and _identity(before) != previous:
        _fail("SOURCE_CHANGED", "La identidad del archivo ha cambiado: " + str(path))
    digest = hashlib.sha256()
    with _open_readonly(path) as stream:
        opened = os.fstat(stream.fileno())
        if _cross_api_identity(opened) != _cross_api_identity(before):
            _fail("SOURCE_CHANGED", "El archivo cambio al abrirlo: " + str(path))
        for block in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(block)
        after_open = os.fstat(stream.fileno())
    after = _regular_info(path)
    if (_identity(opened) != _identity(after_open) or
            _identity(before) != _identity(after) or
            not hmac.compare_digest(digest.hexdigest(), expected_hash)):
        _fail("SOURCE_CHANGED", "Los bytes o la identidad del archivo han cambiado: " + str(path))
    return _identity(after)


def _within(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _same_or_inside(path, root):
    # normcase also makes Windows comparisons insensitive to case.
    return _within(Path(os.path.normcase(str(path))),
                   Path(os.path.normcase(str(root))))


def _relative_source(value):
    if not isinstance(value, str) or not value or "\\" in value:
        _fail("UNSAFE_PATH", "La ruta de un ZIP debe ser relativa y POSIX.")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(part in ("", ".", "..") for part in parts):
        _fail("UNSAFE_PATH", "Ruta relativa de ZIP no valida: " + value)
    for part in parts:
        _component(part, value)
    if not parts[-1].lower().endswith(".zip"):
        _fail("INVALID_PLAN", "El archivo elegible no tiene extension ZIP: " + value)
    return parts


def _validate_plan(plan, output_root):
    if not isinstance(plan, dict):
        _fail("INVALID_PLAN", "La propuesta debe ser un objeto JSON.")
    frozen = json.loads(json.dumps(plan, ensure_ascii=False, allow_nan=False))
    expected = _valid_hash(frozen.get("plan_sha256"), "plan_sha256")
    if not hmac.compare_digest(plan_digest(frozen), expected):
        _fail("PLAN_CHANGED", "La propuesta no coincide con su SHA-256. Genera o revisa otra propuesta.")
    if frozen.get("schema_version") != SCHEMA or frozen.get("status") != "PROPOSED":
        _fail("INVALID_PLAN", "Esquema o estado de propuesta no valido.")
    source_root = _absolute_path(frozen.get("source_root"), "source_root")
    output_root = _absolute_path(output_root, "output_root")
    _check_directory_chain(source_root)
    _check_directory_chain(output_root, must_exist=False)
    source_root = source_root.resolve(strict=True)
    output_root = output_root.resolve(strict=False)
    report = _absolute_path(frozen.get("report_path"), "report_path")
    report_hash = _valid_hash(frozen.get("report_sha256"), "report_sha256")
    report_snapshot = _verified_snapshot(report, report_hash)
    archives = frozen.get("archives")
    groups = frozen.get("groups")
    if not isinstance(archives, list) or not isinstance(groups, list):
        _fail("INVALID_PLAN", "Faltan las listas de archivos o grupos.")
    archive_ids, eligible, source_names = set(), {}, set()
    for archive in archives:
        if not isinstance(archive, dict):
            _fail("INVALID_PLAN", "Entrada de archivo no valida.")
        archive_id = archive.get("id")
        if not isinstance(archive_id, str) or not archive_id or archive_id in archive_ids:
            _fail("INVALID_PLAN", "Identificador de archivo vacio o duplicado.")
        archive_ids.add(archive_id)
        if type(archive.get("eligible")) is not bool:
            _fail("INVALID_PLAN", "El indicador eligible debe ser booleano.")
        if not archive["eligible"]:
            continue
        parts = _relative_source(archive.get("relative_path"))
        folded = "/".join(parts).casefold()
        if folded in source_names:
            _fail("INVALID_PLAN", "Un origen aparece mas de una vez o tiene una ruta ambigua.")
        source_names.add(folded)
        size = archive.get("size_bytes")
        if type(size) is not int or size < 0:
            _fail("INVALID_PLAN", "Tamano de ZIP no valido.")
        source_hash = _valid_hash(archive.get("sha256"), archive_id)
        path = source_root.joinpath(*parts)
        snapshot = _verified_snapshot(path, source_hash, size)
        eligible[archive_id] = {"archive": archive, "path": path, "sha256": source_hash,
                                "snapshot": snapshot, "size_bytes": size}
    if not eligible:
        _fail("NO_ELIGIBLE_ARCHIVES", "No hay ZIP elegibles para copiar.")
    group_ids, directories, assigned = set(), set(), set()
    for group in groups:
        if not isinstance(group, dict):
            _fail("INVALID_PLAN", "Grupo no valido.")
        group_id = group.get("id")
        if not isinstance(group_id, str) or not group_id or group_id in group_ids:
            _fail("INVALID_PLAN", "Identificador de grupo vacio o duplicado.")
        group_ids.add(group_id)
        directory = _component(group.get("directory_name"), "directory_name")
        if directory.casefold() in directories | {MANIFEST_NAME.casefold(), README_NAME.casefold()}:
            _fail("INVALID_PLAN", "Nombre de carpeta de grupo duplicado o reservado.")
        directories.add(directory.casefold())
        members = group.get("member_ids")
        if (not isinstance(members, list) or not members or
                group.get("status") not in ("PROPOSED", "SIN_COINCIDENCIAS") or
                (group.get("status") == "SIN_COINCIDENCIAS" and len(members) != 1)):
            _fail("INVALID_PLAN", "Grupo vacio o con estado no valido.")
        for member in members:
            if not isinstance(member, str) or member not in eligible or member in assigned:
                _fail("INVALID_PLAN", "Un grupo contiene un ZIP desconocido, no elegible o repetido.")
            assigned.add(member)
    if assigned != set(eligible):
        _fail("INVALID_PLAN", "Cada ZIP elegible debe figurar exactamente una vez en los grupos.")
    return {"plan": frozen, "plan_sha256": expected, "source_root": source_root,
            "output_root": output_root, "report": report, "report_hash": report_hash,
            "report_snapshot": report_snapshot, "eligible": eligible, "groups": groups}


def _candidate_path(output_root, digest):
    for number in range(10000):
        name = (OUTPUT_NAME if number == 0 else OUTPUT_NAME + "_" + digest[:12]
                if number == 1 else OUTPUT_NAME + "_" + digest[:12] + "_" + str(number))
        candidate = output_root / name
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            return candidate
        if _is_link(info):
            _fail("LINK_NOT_ALLOWED", "El destino existente es un enlace: " + str(candidate))
    _fail("OUTPUT_COLLISION", "No se encontro un nombre de salida libre.")


def output_directory_for(plan: dict, output_root: Path) -> Path:
    """Read-only destination preview; a concurrent publisher may add a suffix."""
    if not isinstance(plan, dict):
        _fail("INVALID_PLAN", "La propuesta debe ser un objeto JSON.")
    digest = _valid_hash(plan.get("plan_sha256"), "plan_sha256")
    if not hmac.compare_digest(plan_digest(plan), digest):
        _fail("PLAN_CHANGED", "La propuesta no coincide con su SHA-256.")
    root = _absolute_path(output_root, "output_root")
    _check_directory_chain(root, must_exist=False)
    return _candidate_path(root, digest)


def _create_output_root(root):
    created = []
    try:
        for path in list(reversed(root.parents)) + [root]:
            try:
                info = _io_path(path).lstat()
            except FileNotFoundError:
                try:
                    _io_path(path).mkdir()
                    info = _io_path(path).lstat()
                    created.append((path, _directory_identity(info)))
                except FileExistsError:
                    info = _io_path(path).lstat()
            if _is_link(info) or not stat.S_ISDIR(info.st_mode):
                _fail("LINK_NOT_ALLOWED", "La ruta de salida contiene un enlace o no es carpeta: " + str(path))
        return created
    except Exception:
        _remove_empty_created(created)
        raise


def _remove_empty_created(created):
    for path, identity in reversed(created):
        try:
            info = _io_path(path).lstat()
            if not _is_link(info) and _directory_identity(info) == identity:
                path.rmdir()  # Never deletes a folder containing somebody else's files.
        except OSError:
            pass


def _truncate_utf16(text, units):
    while text and len(text.encode("utf-16-le")) // 2 > units:
        text = text[:-1]
    return text


def _destination_names(group, eligible):
    members = group["member_ids"]
    basenames = {member: eligible[member]["path"].name for member in members}
    counts = {}
    for basename in basenames.values():
        counts[basename.casefold()] = counts.get(basename.casefold(), 0) + 1
    used = {name.casefold() for name in basenames.values() if counts[name.casefold()] == 1}
    names = {}
    for member in members:
        basename = basenames[member]
        if counts[basename.casefold()] == 1:
            names[member] = basename
            continue
        token = eligible[member]["sha256"][:12] + "_" + hashlib.sha256(member.encode("utf-8")).hexdigest()[:8]
        for number in range(10000):
            suffix = "__" + token + ("_" + str(number + 1) if number else "") + basename[-4:]
            stem = _truncate_utf16(basename[:-4] or "ZIP", 255 - len(suffix))
            candidate = stem + suffix
            if candidate.casefold() not in used:
                _component(candidate, "nombre de copia")
                names[member] = candidate
                used.add(candidate.casefold())
                break
        else:
            _fail("OUTPUT_COLLISION", "No se pudo asignar un nombre de copia unico.")
    return names


def _copy_verified(source, destination):
    path, expected = source["path"], source["sha256"]
    before = _regular_info(path)
    if _identity(before) != source["snapshot"]:
        _fail("SOURCE_CHANGED", "El origen cambio antes de copiar: " + str(path))
    copied_hash, size = hashlib.sha256(), 0
    with _open_readonly(path) as incoming:
        opened = os.fstat(incoming.fileno())
        if _cross_api_identity(opened) != _cross_api_identity(before):
            _fail("SOURCE_CHANGED", "El origen cambio al abrirlo: " + str(path))
        with _io_path(destination).open("xb") as outgoing:
            for block in iter(lambda: incoming.read(CHUNK_SIZE), b""):
                outgoing.write(block)
                copied_hash.update(block)
                size += len(block)
            outgoing.flush()
            os.fsync(outgoing.fileno())
        after_open = os.fstat(incoming.fileno())
    if (_identity(after_open) != _identity(opened) or
            _identity(_regular_info(path)) != source["snapshot"] or
            size != source["size_bytes"] or copied_hash.hexdigest() != expected):
        _fail("SOURCE_CHANGED", "El ZIP cambio durante la copia: " + str(path))
    _verified_snapshot(destination, expected, size)
    return {"copied_sha256": copied_hash.hexdigest(), "copied_size_bytes": size}


def _write_new(path, data):
    with _io_path(path).open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_publish_noreplace(source, destination):
    if os.name == "nt":
        os.rename(_io_path(source), _io_path(destination))  # Windows fails if the destination exists.
        return
    if sys.platform.startswith("linux"):
        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            _fail("ATOMIC_PUBLISH_UNAVAILABLE", "Este sistema no ofrece renameat2 sin reemplazo.")
        renameat2.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                              ctypes.c_char_p, ctypes.c_uint]
        renameat2.restype = ctypes.c_int
        if renameat2(-100, os.fsencode(source), -100, os.fsencode(destination), 1) != 0:
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code), str(destination))
        return
    _fail("ATOMIC_PUBLISH_UNAVAILABLE", "Publicacion sin reemplazo disponible en Windows y Linux.")


def _clean_staging(stage, identity):
    if stage is None:
        return None
    try:
        _check_directory_chain(stage.parent)
        info = _io_path(stage).lstat()
        if _is_link(info) or _directory_identity(info) != identity:
            return "La carpeta temporal cambio de identidad; se conserva: " + str(stage)
        shutil.rmtree(_io_path(stage))
    except FileNotFoundError:
        pass
    except (OSError, GroupingError) as exc:
        return "No se pudo limpiar la carpeta temporal propia: " + str(exc)
    return None


def apply_grouping(plan: dict, output_root: Path, accepted: bool = False) -> dict:
    """Apply only a literal True acceptance; publish all verified copies or none."""
    result = {"status": "DECLINED", "output_directory": None, "manifest_path": None,
              "readme_path": None, "copied_count": 0, "plan_sha256": None, "errors": []}
    if accepted is not True:
        return result  # Intentionally before every filesystem read or write.
    stage, stage_identity, created = None, None, []
    try:
        context = _validate_plan(plan, output_root)
        result["plan_sha256"] = context["plan_sha256"]
        root = context["output_root"]
        # Fail before writing if the current destination is an unexpected link.
        _candidate_path(root, context["plan_sha256"])
        created = _create_output_root(root)
        stage = Path(tempfile.mkdtemp(prefix=".ZIP_AUDITOR_AGRUPAR_", dir=root))
        stage_identity = _directory_identity(_io_path(stage).lstat())
        copied = []
        for group in context["groups"]:
            folder = stage / group["directory_name"]
            _io_path(folder).mkdir()
            names = _destination_names(group, context["eligible"])
            for member in group["member_ids"]:
                source = context["eligible"][member]
                destination = folder / names[member]
                identity = _copy_verified(source, destination)
                copied.append({"archive_id": member,
                               "source": str(source["path"]),
                               "source_relative_path": source["archive"]["relative_path"],
                               "source_zip_sha256": source["sha256"],
                               "source_size_bytes": source["size_bytes"],
                               "destination_relative_path": destination.relative_to(stage).as_posix(),
                               "original_basename": source["path"].name,
                               "renamed_for_collision": names[member] != source["path"].name,
                               "group_id": group["id"], "group_label": group.get("label"),
                               "group_confidence": group.get("confidence"),
                               "group_evidence": group.get("evidence"), **identity})
        # Recheck every source after all copying, before publishing anything.
        for source in context["eligible"].values():
            _verified_snapshot(source["path"], source["sha256"], source["size_bytes"], source["snapshot"])
        _verified_snapshot(context["report"], context["report_hash"], previous=context["report_snapshot"])
        manifest = {"schema_version": "zip-auditor-grouped-copies-1.0", "status": "COPIED",
                    "created_at_utc": datetime.now(timezone.utc).isoformat(),
                    "plan_sha256": context["plan_sha256"], "report_path": str(context["report"]),
                    "report_sha256": context["report_hash"], "source_root": str(context["source_root"]),
                    "operation": "COPY_INTACT_ZIPS", "source_selection": "FIXED_PLAN_NO_RESCAN",
                    "output_root_within_source_root": _same_or_inside(root, context["source_root"]),
                    "archives_extracted": False,
                    "archives_executed": False, "copied_count": len(copied),
                    "excluded_archives": [a for a in context["plan"]["archives"] if not a["eligible"]],
                    "copies": copied,
                    "verification": "SHA-256 during copy, reread of destination, and final reread of sources; no functional equivalence claim."}
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
        _write_new(stage / MANIFEST_NAME, manifest_bytes)
        readme = ("ZIP AUDITOR - COPIAS AGRUPADAS\n\n"
                  "Se han copiado ZIP completos. No se han extraido, ejecutado, mezclado ni movido sus contenidos.\n"
                  "Los originales se conservaron y sus SHA-256 se comprobaron antes de publicar esta carpeta.\n"
                  "Agrupar por contenido no demuestra que los programas funcionen juntos.\n\n"
                  "Propuesta SHA-256: " + context["plan_sha256"] + "\n"
                  "Carpeta de origen: " + str(context["source_root"]) + "\n"
                  "Copias verificadas: " + str(len(copied)) + "\n\n"
                  + MANIFEST_NAME + " relaciona origen, nombre de copia, grupo, evidencias y SHA-256.\n"
                  "Si coincidian nombres dentro de un grupo, se anadio un sufijo inequívoco; consulta original_basename.\n")
        _write_new(stage / README_NAME, readme.encode("utf-8"))
        for _ in range(32):
            _check_directory_chain(root)
            destination = _candidate_path(root, context["plan_sha256"])
            if _same_or_inside(context["source_root"], destination):
                _fail("OUTPUT_SOURCE_COLLISION", "El destino no puede sustituir a la carpeta de origen ni a uno de sus antecesores.")
            try:
                _atomic_publish_noreplace(stage, destination)
                break
            except FileExistsError:
                continue
        else:
            _fail("OUTPUT_COLLISION", "Otro proceso ocupa repetidamente el destino; no se publico la copia.")
        stage = None
        result.update(status="COPIED", output_directory=str(destination),
                      manifest_path=str(destination / MANIFEST_NAME),
                      readme_path=str(destination / README_NAME), copied_count=len(copied),
                      manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
                      source_hashes_rechecked=True)
        return result
    except KeyboardInterrupt:
        _clean_staging(stage, stage_identity)
        _remove_empty_created(created)
        raise
    except Exception as exc:
        cleanup_error = _clean_staging(stage, stage_identity)
        _remove_empty_created(created)
        result.update(status="FAILED", error_code=getattr(exc, "code", "OPERATION_FAILED"),
                      exception_type=type(exc).__name__, errors=[str(exc)])
        if cleanup_error:
            result["errors"].append(cleanup_error)
            result["unpublished_staging_directory"] = str(stage)
        return result
