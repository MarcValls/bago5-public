"""Propuestas de unificación a partir de un informe ZIP ya verificado.

No extrae, ejecuta, fusiona, modifica ni elimina archivos de los ZIP analizados.
Las coincidencias de bytes no acreditan compatibilidad funcional.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import html
import itertools
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile

MAX_PAIRS = 10000
MAX_CANDIDATES = 150
MAX_EVIDENCE = 32
HASH = re.compile(r"^[a-fA-F0-9]{64}$")
LABELS = {
    "IDENTICAL_ZIPS": "ZIP idénticos byte por byte",
    "SAME_FILE_SET": "Mismo inventario lógico y mismos contenidos",
    "COMPLETE_INCLUSION": "Un inventario está incluido en el otro",
    "SHARED_COMPONENTS": "Contenido compartido, sin conflicto observado de rutas",
    "REUSE_RENAMED_CONTENT": "Mismos bytes con rutas diferentes",
    "PATH_CONFLICTS": "Variantes o colisiones que requieren resolución",
    "DOCUMENTATION_ONLY": "Coincidencia limitada a documentación",
    "INCOMPLETE_REVIEW": "Evidencia incompleta: revisar antes de proponer una unión",
}
PRIORITY = {name: rank for rank, name in enumerate(LABELS)}
PLAN = [
    "Conservar los ZIP originales y sus SHA-256 como referencia inmutable.",
    "Crear una distribución nueva en otra carpeta; mantener procedencia, versiones y licencias.",
    "Separar nombres y espacios de módulos; decidir explícitamente cada conflicto de ruta o contenido.",
    "Ajustar y comprobar referencias, configuraciones, recursos, puntos de entrada y dependencias.",
    "Ejecutar pruebas de cada paquete y del conjunto; comparar resultados con los originales.",
    "Aceptar la nueva distribución solo con evidencia de ausencia de regresiones en el alcance acordado.",
]
LIMITS = [
    "Todas las acciones son propuestas. No se ha realizado ninguna fusión, sustitución ni eliminación.",
    "Un SHA-256 coincidente acredita identidad de bytes; no compatibilidad funcional ni permisos de redistribución.",
    "Las rutas lógicas pueden omitir una carpeta raíz común del ZIP. Hay que revisar el diseño final de carpetas.",
    "Las dependencias se resuelven estáticamente dentro de cada ZIP independiente. No se ha probado un entorno combinado.",
    "Los conteos son por pareja; no se suman como ahorro global ni se agrupan paquetes por transitividad.",
    "Los ZIP anidados no se abren para esta comparación. Los límites del informe original siguen vigentes.",
]


def _valid_hash(value):
    return isinstance(value, str) and HASH.fullmatch(value) is not None


def _safe_path(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        return False
    parts = value.split("/")
    reserved = {"con", "prn", "aux", "nul"} | {f"{prefix}{n}" for prefix in ("com", "lpt") for n in range(1, 10)}
    return (not value.startswith("/") and
            all(part not in ("", ".", "..") and not part.endswith((" ", ".")) and
                not any(ord(char) < 32 or char in '<>"|?*' for char in part) and
                part.casefold().split(".", 1)[0] not in reserved for part in parts))


def _documentation(path):
    value = path.casefold()
    base = PurePosixPath(value).name
    stem = base.split(".", 1)[0]
    if (base in {"skill.md", "agents.md", "claude.md", "instructions.md", "instrucciones.md"} or
            any(token in stem for token in ("contract", "contrat", "instruction", "instruccion"))):
        return False
    return (stem in {"readme", "license", "licence", "copying", "notice", "authors",
                     "changelog", "changes", "contributing", "leeme", "leer_primero"}
            or value.startswith(("docs/", "doc/", "documentation/")))


def _reference(entry, archive):
    return {"id": entry.get("id"), "zip": archive["zip"], "path": entry.get("path"),
            "logical_path": entry.get("logical_path", entry.get("path")),
            "sha256": entry.get("sha256"), "size": entry.get("size")}


def _profile(archive, index):
    entries = archive.get("entries", [])
    if not isinstance(entries, list):
        entries = []
    result = {"id": str(archive.get("id", f"A{index:05d}")),
              "zip": str(archive.get("zip", f"paquete-{index}")),
              "zip_sha256": archive.get("zip_sha256") if _valid_hash(archive.get("zip_sha256")) else None,
              "status": archive.get("status", "UNKNOWN"), "entry_count": len(entries),
              "issues": [], "paths": {}, "known_paths": {}, "hashes": defaultdict(list), "entries": []}
    if result["status"] != "ANALYZED":
        result["issues"].append("ARCHIVE_NOT_FULLY_ANALYZED")
    if not result["zip_sha256"]:
        result["issues"].append("MISSING_ARCHIVE_HASH")
    if not entries:
        result["issues"].append("NO_FILE_INVENTORY")
    spelling = {}
    for entry in entries:
        if not isinstance(entry, dict):
            result["issues"].append("INVALID_ENTRY")
            continue
        logical = entry.get("logical_path", entry.get("path"))
        raw = entry.get("path")
        digest = entry.get("sha256")
        safe = _safe_path(logical) and _safe_path(raw)
        if not safe:
            result["issues"].append("UNSAFE_PATH")
        if entry.get("status") != "ANALYZED" or entry.get("issues"):
            result["issues"].append("ENTRY_REQUIRES_REVIEW")
        if safe:
            result["known_paths"].setdefault(str(logical), entry)
        if not _valid_hash(digest):
            result["issues"].append("MISSING_CONTENT_HASH")
            continue
        if not safe:
            continue
        logical = str(logical)
        folded = logical.casefold()
        if folded in spelling:
            result["issues"].append("DUPLICATE_OR_CASEFOLD_PATH")
        else:
            spelling[folded] = logical
            result["paths"][logical] = entry
        result["hashes"][digest.lower()].append(entry)
        result["entries"].append(entry)
    result["issues"] = sorted(set(result["issues"]))
    result["complete"] = not result["issues"]
    return result


def _dependency_index(report):
    analysis = report.get("dependency_analysis") or {}
    nodes = {node.get("id"): node for node in analysis.get("nodes", [])
             if isinstance(node, dict) and node.get("id")}
    by_zip = defaultdict(list)
    for edge in analysis.get("edges", []):
        if isinstance(edge, dict):
            source = nodes.get(edge.get("source"), {})
            if source.get("zip"):
                by_zip[source["zip"]].append(edge)
    return analysis, nodes, by_zip


def _dependency_context(profile, affected_ids, index):
    analysis, nodes, by_zip = index
    dependents = set()
    for identifier in affected_ids:
        node = nodes.get(identifier, {})
        dependents.update(node.get("runtime_dependents") or [])
    issues = [edge for edge in by_zip[profile["zip"]]
              if edge.get("status") in {"MISSING_LOCAL", "AMBIGUOUS_INTERNAL", "UNRESOLVED_IMPORT",
                                        "UNRESOLVED_MANIFEST_REFERENCE", "EXTERNAL_OR_ALIAS"}]
    counts = Counter(edge.get("status", "UNKNOWN") for edge in issues)
    return {"zip": profile["zip"], "affected_nodes": len(affected_ids),
            "runtime_dependents_count": len(dependents),
            "runtime_dependents": [{"id": identifier, "path": nodes.get(identifier, {}).get("path")}
                                   for identifier in sorted(dependents)[:MAX_EVIDENCE]],
            "reference_issue_counts": dict(counts),
            "reference_issues": [{key: edge.get(key) for key in ("source", "reference", "line", "status", "candidates")}
                                 for edge in issues[:MAX_EVIDENCE]],
            "reference_issues_omitted": max(0, len(issues) - MAX_EVIDENCE),
            "analysis_status": analysis.get("status", "NOT_AVAILABLE"),
            "omitted_edges_in_original_report": (analysis.get("summary") or {}).get("omitted_edges", 0),
            "runtime_verification": analysis.get("runtime_verification", "NOT_RUN")}


def _incidental_top_level_path(name):
    """Common ZIP root filenames are not evidence that products are related.

    Restrict this rule to the ZIP logical root. A nested package.json is not
    automatically generic: its parent namespace may be informative.
    """
    return (isinstance(name, str) and '/' not in name and name.casefold() in {
        'readme.md', 'readme.txt', 'leeme.md', 'leeme.txt',
        'license', 'license.md', 'license.txt', 'licence', 'licence.md',
        'copying', 'notice', 'notice.txt', 'changelog.md',
        'package.json', 'package-lock.json', 'yarn.lock',
        'pyproject.toml', 'requirements.txt', 'setup.cfg',
    })


def _incidental_collisions_only(left, right):
    """Only same *generic names* with different bytes; never merge on this.

    This does not assert packages are unrelated. It suppresses a misleading
    merger candidate while still allowing an independent distribution.
    Incomplete inventories keep their review signal.
    """
    if not left['complete'] or not right['complete']:
        return False
    if left['zip_sha256'] == right['zip_sha256']:
        return False
    if set(left['hashes']) & set(right['hashes']):
        return False
    lp, rp = left['paths'], right['paths']
    common = set(lp) & set(rp)
    folded_left = {name.casefold(): name for name in lp}
    folded_right = {name.casefold(): name for name in rp}
    cross_case = [(folded_left[key], folded_right[key])
                  for key in (set(folded_left) & set(folded_right))
                  if folded_left[key] != folded_right[key]]
    if not (common or cross_case):
        return False
    if not all(_incidental_top_level_path(name) for name in common):
        return False
    if not all(_incidental_top_level_path(a) and _incidental_top_level_path(b)
               for a, b in cross_case):
        return False
    # Even a generic root name colliding with another file's ancestor is a
    # real namespace conflict. Do not hide it.
    for name in lp:
        if any(str(parent).casefold() in folded_right for parent in PurePosixPath(name).parents):
            return False
    for name in rp:
        if any(str(parent).casefold() in folded_left for parent in PurePosixPath(name).parents):
            return False
    return True


def _candidate(left, right, dep_index):
    if _incidental_collisions_only(left, right):
        return None
    left_paths, right_paths = left["paths"], right["paths"]
    common = set(left_paths) & set(right_paths)
    known_common = set(left["known_paths"]) & set(right["known_paths"])
    unhashed_common = sorted(known_common - common)
    same = sorted(name for name in common if left_paths[name]["sha256"].lower() == right_paths[name]["sha256"].lower())
    different = sorted(common - set(same))
    shared_hashes = sorted(set(left["hashes"]) & set(right["hashes"]))
    right_folded = {name.casefold(): name for name in right_paths}
    left_folded = {name.casefold(): name for name in left_paths}
    case_collisions = [(name, right_folded[name.casefold()]) for name in left_paths
                       if name.casefold() in right_folded and name != right_folded[name.casefold()]]
    namespace_collisions = set()
    for name in right_paths:
        for parent in PurePosixPath(name).parents:
            if str(parent).casefold() in left_folded:
                namespace_collisions.add((left_folded[str(parent).casefold()], name))
    for name in left_paths:
        for parent in PurePosixPath(name).parents:
            if str(parent).casefold() in right_folded:
                namespace_collisions.add((name, right_folded[str(parent).casefold()]))
    namespace_collisions = sorted(namespace_collisions)
    exact_zip = bool(left["zip_sha256"] and right["zip_sha256"] and
                     left["zip_sha256"].lower() == right["zip_sha256"].lower())
    if not exact_zip and not known_common and not shared_hashes and not case_collisions and not namespace_collisions:
        return None
    complete = left["complete"] and right["complete"]
    signature_left = {(name, entry["sha256"].lower()) for name, entry in left_paths.items()}
    signature_right = {(name, entry["sha256"].lower()) for name, entry in right_paths.items()}
    relevant = [entry for profile in (left, right) for digest in shared_hashes
                for entry in profile["hashes"][digest]]
    relevant += [left_paths[name] for name in different] + [right_paths[name] for name in different]
    relevant += [left_paths[a] for a, _ in case_collisions] + [right_paths[b] for _, b in case_collisions]
    relevant += [left_paths[a] for a, _ in namespace_collisions] + [right_paths[b] for _, b in namespace_collisions]
    docs_only = bool(relevant) and all(_documentation(entry.get("logical_path", entry["path"])) for entry in relevant)
    containment = None
    if exact_zip:
        classification = "IDENTICAL_ZIPS"
        action = "Registrar la identidad de ambos ZIP y elegir una copia de referencia, conservando los originales."
    elif not complete:
        classification = "INCOMPLETE_REVIEW"
        action = "Resolver entradas incompletas, rutas inseguras o colisiones antes de decidir una unificación."
    elif signature_left == signature_right:
        classification = "SAME_FILE_SET"
        action = "Evaluar una distribución común en una copia nueva; revisar carpetas raíz, metadatos, configuración y puntos de entrada."
        if docs_only:
            action += " El inventario coincidente es documental; esto no acredita un módulo de ejecución compartido."
    elif docs_only:
        classification = "DOCUMENTATION_ONLY"
        action = "Revisar documentación y licencias. Esta coincidencia aislada no justifica crear un módulo común."
    elif different or case_collisions or namespace_collisions:
        classification = "PATH_CONFLICTS"
        action = "Mantener variantes separadas y decidir explícitamente qué versión conserva cada ruta en una copia nueva."
    elif signature_left < signature_right or signature_right < signature_left:
        classification = "COMPLETE_INCLUSION"
        small, large = (left, right) if signature_left < signature_right else (right, left)
        containment = {"contained_zip": small["zip"], "containing_zip": large["zip"]}
        action = (f"Evaluar si {small['zip']} debe mantenerse como distribución independiente o referenciar componentes de {large['zip']}; conservar ambos.")
    elif same:
        classification = "SHARED_COMPONENTS"
        action = "Evaluar componentes compartidos con referencias explícitas; probar cada distribución por separado antes de unirlas."
    else:
        classification = "REUSE_RENAMED_CONTENT"
        action = "Evaluar reutilización de los mismos bytes con referencias o adaptadores de ruta; no borrar copias por el hash."
    affected = {}
    for profile in (left, right):
        affected[profile["id"]] = {entry.get("id") for entry in profile["entries"]
                                   if entry.get("id") and (entry["sha256"].lower() in shared_hashes or
                                       entry.get("logical_path", entry.get("path")) in common)}
    matches = [{"logical_path": name, "sha256": left_paths[name]["sha256"],
                "left": _reference(left_paths[name], left), "right": _reference(right_paths[name], right)}
               for name in same[:MAX_EVIDENCE]]
    conflicts = [{"logical_path": name, "reason": "DIFFERENT_CONTENT",
                  "left": _reference(left_paths[name], left), "right": _reference(right_paths[name], right)}
                 for name in different[:MAX_EVIDENCE]]
    conflicts.extend({"logical_path": a, "reason": "WINDOWS_CASE_COLLISION",
                      "left": _reference(left_paths[a], left), "right": _reference(right_paths[b], right)}
                     for a, b in case_collisions[:MAX_EVIDENCE])
    conflicts.extend({"logical_path": a, "reason": "FILE_DIRECTORY_COLLISION",
                      "left": _reference(left_paths[a], left), "right": _reference(right_paths[b], right)}
                     for a, b in namespace_collisions[:MAX_EVIDENCE])
    renamed = []
    for digest in shared_hashes:
        lpaths = sorted({entry.get("logical_path", entry["path"]) for entry in left["hashes"][digest]})
        rpaths = sorted({entry.get("logical_path", entry["path"]) for entry in right["hashes"][digest]})
        if lpaths != rpaths:
            renamed.append({"sha256": digest, "left_paths": lpaths[:MAX_EVIDENCE], "right_paths": rpaths[:MAX_EVIDENCE],
                            "left_count": len(lpaths), "right_count": len(rpaths)})
    validations = ["Comprobar versiones, licencias, configuraciones y puntos de entrada.",
                   "Revisar referencias de los archivos que se compartirían o cambiarían de ruta.",
                   "Ejecutar pruebas de los originales y del conjunto; no inferir equivalencia funcional por los hashes."]
    if different or case_collisions or namespace_collisions:
        validations.insert(0, "Resolver cada conflicto de contenido o capitalización; no sobrescribir automáticamente.")
    if not complete:
        validations.insert(0, "Completar el inventario de las dos fuentes y repetir la comparación.")
    return {"classification": classification, "label": LABELS[classification],
            "status": "PROPOSED_ONLY", "automatic_action": None,
            "evidence_scope": "COMPLETE_FILE_INVENTORIES" if complete else "INCOMPLETE_INVENTORY_REVIEW",
            "functional_compatibility": "NOT_VERIFIED", "action": action, "containment": containment,
            "documentation_only_signal": docs_only,
            "archives": [{key: profile[key] for key in ("id", "zip", "zip_sha256", "status", "entry_count", "issues")}
                         for profile in (left, right)],
            "counts": {"same_path_same_hash": len(same), "same_path_different_hash": len(different),
                       "case_collisions": len(case_collisions), "shared_content_hashes": len(shared_hashes),
                       "namespace_collisions": len(namespace_collisions),
                       "same_path_without_both_hashes": len(unhashed_common),
                       "renamed_content_groups": len(renamed),
                       "left_only_paths": len(set(left_paths) - set(right_paths)),
                       "right_only_paths": len(set(right_paths) - set(left_paths))},
            "evidence": {"zip_bytes_identical": exact_zip, "matches": matches, "conflicts": conflicts,
                         "unhashed_overlap": [{"logical_path": name,
                                               "left": _reference(left["known_paths"][name], left),
                                               "right": _reference(right["known_paths"][name], right)}
                                              for name in unhashed_common[:MAX_EVIDENCE]],
                         "renamed_content": renamed[:MAX_EVIDENCE],
                         "matches_omitted": max(0, len(same) - MAX_EVIDENCE),
                         "conflicts_omitted": (max(0, len(different) - MAX_EVIDENCE) + max(0, len(case_collisions) - MAX_EVIDENCE) +
                                               max(0, len(namespace_collisions) - MAX_EVIDENCE)),
                         "renamed_groups_omitted": max(0, len(renamed) - MAX_EVIDENCE)},
            "dependency_context": [_dependency_context(profile, affected[profile["id"]], dep_index)
                                   for profile in (left, right)],
            "validations_required": validations}


def summarize(report: dict) -> dict:
    """Produce propuestas; función pura, sin acceso a archivos ni ejecución."""
    if not isinstance(report, dict) or not isinstance(report.get("archives"), list):
        raise ValueError("El informe no contiene un inventario de archivos ZIP.")
    profiles = [_profile(archive, i) for i, archive in enumerate(report["archives"], 1)
                if isinstance(archive, dict)]
    dep_index = _dependency_index(report)
    candidates = []
    examined = 0
    incidental_pairs_suppressed = 0
    for left, right in itertools.islice(itertools.combinations(profiles, 2), MAX_PAIRS):
        examined += 1
        candidate = _candidate(left, right, dep_index)
        if candidate:
            candidates.append(candidate)
        elif _incidental_collisions_only(left, right):
            incidental_pairs_suppressed += 1
    candidates.sort(key=lambda item: (PRIORITY[item["classification"]],
                                     -item["counts"]["same_path_same_hash"],
                                     item["archives"][0]["zip"], item["archives"][1]["zip"]))
    found = len(candidates)
    candidates = candidates[:MAX_CANDIDATES]
    for i, candidate in enumerate(candidates, 1):
        candidate["id"] = f"FUS-{i:03d}"
    possible = len(profiles) * (len(profiles) - 1) // 2
    review_archives = [{key: profile[key] for key in ("id", "zip", "status", "issues")}
                       for profile in profiles if not profile["complete"]]
    coverage = {"archives": len(profiles), "possible_pairs": possible, "examined_pairs": examined,
                "unexamined_pairs": possible - examined, "pair_limit": MAX_PAIRS,
                "candidates_found": found, "candidates_returned": len(candidates),
                "candidates_omitted": found - len(candidates), "candidate_limit": MAX_CANDIDATES,
                "incidental_generic_path_pairs_suppressed": incidental_pairs_suppressed,
                "status": "LIMITED" if examined < possible or found > len(candidates) else "COMPLETE_PAIRWISE_WITHIN_REPORT",
                "incomplete_archive_count": len(review_archives),
                "evidence_items_per_kind_limit": MAX_EVIDENCE,
                "original_dependency_status": dep_index[0].get("status", "NOT_AVAILABLE"),
                "original_omitted_edges": (dep_index[0].get("summary") or {}).get("omitted_edges", 0)}
    counts = Counter(item["classification"] for item in candidates)
    distribution = {
        "status": "PROPOSED_ONLY", "mode": "KEEP_ORIGINAL_ZIPS", "automatic_action": None,
        "available": bool(profiles), "functional_integration": "NOT_PROPOSED",
        "source_identity_complete": bool(profiles) and all(profile["zip_sha256"] for profile in profiles),
        "source_archives": [{key: profile[key] for key in ("id", "zip", "zip_sha256", "status", "entry_count", "issues")}
                            for profile in profiles],
        "action": "Preparar una entrega común nueva que conserve cada ZIP original, separado y con un nombre inequívoco, junto a un inventario de procedencia y SHA-256.",
        "scope": "Unificación de la distribución. No mezcla rutas internas, no extrae ni ejecuta los programas y no acredita integración funcional.",
        "checks_required": [
            "Releer y comprobar el SHA-256 de cada ZIP antes de incorporarlo; resolver cualquier identidad ausente.",
            "Copiar cada ZIP como archivo intacto a una ruta única y conservar sus nombres originales en el inventario.",
            "Comprobar que los bytes recuperados del contenedor nuevo coinciden con cada SHA-256 de origen.",
            "Comprobar que los originales siguen intactos; no sustituirlos ni eliminarlos.",
            "Identificar expresamente fuentes corruptas, parciales o con incidencias; conservarlas no demuestra que funcionen.",
        ],
    }
    lines = ["Resumen de posibles unificaciones — propuestas, sin modificar originales.",
             f"{examined} de {possible} parejas comparadas; {found} con coincidencias o conflictos revisables."]
    if profiles:
        lines.append(f"Opción de distribución: un contenedor común con los {len(profiles)} ZIP originales separados e inventariados, sin mezclar sus programas.")
    if incidental_pairs_suppressed:
        lines.append(f"{incidental_pairs_suppressed} parejas descartadas como propuesta de fusión: solo comparten nombres genéricos de raíz con contenidos diferentes, sin identidad de bytes compartida.")
    for candidate in candidates[:5]:
        names = " + ".join(archive["zip"] for archive in candidate["archives"])
        lines.append(f"{candidate['id']} · {names}: {candidate['label']}.")
        lines.append("  " + candidate["action"])
    if not candidates:
        lines.append("No se han encontrado coincidencias suficientes para proponer una unificación en el alcance analizado.")
    if review_archives:
        lines.append(f"Atención: {len(review_archives)} ZIP tienen inventario incompleto o incidencias; requieren revisión.")
    if coverage["status"] == "LIMITED":
        lines.append("Cobertura limitada: consulte los pares o propuestas omitidos en el resumen detallado.")
    lines.append("La compatibilidad funcional está SIN VERIFICAR. No se ha fusionado ni borrado nada.")
    return {"schema_version": "zip-auditor-fusion-summary-1.0", "status": "PROPOSED_ONLY",
            "automatic_actions": [], "source_tool_version": report.get("tool_version"),
            "source_generated_utc": report.get("generated_utc"),
            "coverage": coverage, "classification_counts": dict(counts),
            "distribution_unification": distribution,
            "archives_requiring_review": review_archives, "candidates": candidates,
            "future_merge_plan": list(PLAN), "limits": list(LIMITS), "console_lines": lines}


def _render(summary):
    escape = lambda value: html.escape(str(value), quote=True)
    coverage = summary["coverage"]
    distribution = summary["distribution_unification"]
    distribution_rows = "".join("<tr><td>" + escape(source["zip"]) + "</td><td>" + escape(source["status"]) +
                                "</td><td>" + escape(source["entry_count"]) + "</td><td><code>" +
                                escape(source["zip_sha256"] or "Identidad pendiente") + "</code></td></tr>"
                                for source in distribution["source_archives"][:100])
    distribution_checks = "".join("<li>" + escape(value) + "</li>" for value in distribution["checks_required"])
    distribution_panel = (f'''<section class="panel"><div class="eyebrow">OPCIÓN DE DISTRIBUCIÓN · PROPUESTA</div>
<h2>Unificar la entrega conservando cada ZIP</h2><p>{escape(distribution['action'])}</p>
<p>{escape(distribution['scope'])}</p><p class="meta">Esta opción también es aplicable cuando los programas no comparten archivos. No se ha construido ningún contenedor.</p>
<details><summary>Inventario de ZIP y comprobaciones requeridas</summary>
<div class="table-wrap"><table><thead><tr><th>ZIP original</th><th>Estado de análisis</th><th>Entradas inventariadas</th><th>SHA-256 del ZIP</th></tr></thead><tbody>{distribution_rows}</tbody></table></div>
<p class="meta">Se muestran hasta 100 ZIP; el JSON contiene el inventario completo. Un estado parcial o erróneo se conserva como incidencia, sin atribuir funcionamiento.</p><ul>{distribution_checks}</ul></details></section>'''
                          if distribution["available"] else "")
    cards = []
    for item in summary["candidates"]:
        pair = " + ".join(archive["zip"] for archive in item["archives"])
        rows = []
        for match in item["evidence"]["matches"]:
            rows.append("<tr><td>Coincidencia</td><td>" + escape(match["logical_path"]) +
                        "</td><td><code>" + escape(match["sha256"]) + "</code></td></tr>")
        for conflict in item["evidence"]["conflicts"]:
            rows.append("<tr><td>" + escape(conflict["reason"]) + "</td><td>" +
                        escape(conflict["left"]["path"]) + " ↔ " + escape(conflict["right"]["path"]) +
                        "</td><td><code>" + escape(conflict["left"]["sha256"]) + "<br>" +
                        escape(conflict["right"]["sha256"]) + "</code></td></tr>")
        for group in item["evidence"]["renamed_content"]:
            rows.append("<tr><td>Mismos bytes, distintas rutas</td><td>" +
                        escape(", ".join(group["left_paths"])) + " ↔ " + escape(", ".join(group["right_paths"])) +
                        "</td><td><code>" + escape(group["sha256"]) + "</code></td></tr>")
        dependencies = "".join("<li><b>" + escape(ctx["zip"]) + "</b>: " +
                               escape(ctx["runtime_dependents_count"]) + " dependientes estáticos de archivos afectados; " +
                               escape(json.dumps(ctx["reference_issue_counts"], ensure_ascii=False)) +
                               ". Estado: " + escape(ctx["analysis_status"]) + ".</li>"
                               for ctx in item["dependency_context"])
        validations = "".join("<li>" + escape(value) + "</li>" for value in item["validations_required"])
        count = item["counts"]
        source_hashes = "".join("<li>" + escape(archive["zip"]) + ": <code>" +
                                escape(archive["zip_sha256"] or "SHA-256 no disponible") + "</code></li>"
                                for archive in item["archives"])
        cards.append(f'''<article><div class="eyebrow">{escape(item['id'])} · PROPUESTA</div>
<h2>{escape(pair)}</h2><span class="badge">{escape(item['label'])}</span>
<p class="action">{escape(item['action'])}</p>
<p class="meta">{count['same_path_same_hash']} rutas idénticas · {count['same_path_different_hash']} variantes de contenido · {count['case_collisions']} colisiones de mayúsculas · {count['renamed_content_groups']} grupos con rutas distintas</p>
<p class="meta">Alcance: {escape(item['evidence_scope'])}. Compatibilidad funcional: SIN VERIFICAR.</p>
<details><summary>Evidencia, dependencias y validaciones pendientes</summary>
<h3>Identidad de las fuentes</h3><ul>{source_hashes}</ul>
<div class="table-wrap"><table><thead><tr><th>Señal</th><th>Ruta lógica / rutas</th><th>SHA-256</th></tr></thead><tbody>{''.join(rows) or '<tr><td colspan="3">La identidad del ZIP es la evidencia disponible; consulte el inventario detallado.</td></tr>'}</tbody></table></div>
<p class="meta">Evidencia limitada a {MAX_EVIDENCE} elementos por tipo. Los conteos completos y omisiones están en el JSON.</p>
<h3>Dependencias estáticas por paquete</h3><ul>{dependencies}</ul>
<h3>Validación requerida</h3><ul>{validations}</ul></details></article>''')
    review = "".join("<li>" + escape(item["zip"]) + ": " + escape(", ".join(item["issues"])) + "</li>"
                     for item in summary["archives_requiring_review"])
    limits = "".join("<li>" + escape(value) + "</li>" for value in summary["limits"])
    plan = "".join("<li>" + escape(value) + "</li>" for value in summary["future_merge_plan"])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>ZIP Auditor · Posibles unificaciones</title>
<style>:root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f2f5f7;color:#18303e;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1180px;margin:0 auto;padding:42px 26px 70px}}header{{background:#112e3d;color:#fff;padding:30px;border-radius:18px}}h1{{font-size:clamp(27px,4vw,42px);line-height:1.15;margin:8px 0 16px}}h2{{margin:8px 0 13px;font-size:22px;overflow-wrap:anywhere}}h3{{font-size:17px;margin:24px 0 8px}}a{{color:#0c6d77}}header a{{color:#b8f2df}}.eyebrow{{font-size:12px;letter-spacing:.12em;font-weight:750}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:14px;margin:20px 0}}.stat,article,.panel{{background:white;border:1px solid #d9e3e7;border-radius:15px;padding:22px}}.stat b{{display:block;font-size:29px;line-height:1.2}}.stat span,.meta{{font-size:14px;color:#526b78}}article{{margin:18px 0}}.badge{{display:inline-block;padding:5px 11px;border-radius:20px;background:#e1f3ed;color:#17604e;font-size:13px;font-weight:650}}.action{{font-size:17px;font-weight:550}}details{{border-top:1px solid #e3e9ed;padding-top:15px}}summary{{cursor:pointer;font-weight:650}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:10px;border-bottom:1px solid #dce5e9;text-align:left;vertical-align:top}}th{{background:#f2f6f7}}code{{font:12px/1.6 ui-monospace,monospace;overflow-wrap:anywhere}}li{{margin-bottom:7px;overflow-wrap:anywhere}}.panel{{margin:22px 0}}.notice{{padding:16px 18px;background:#fff3d9;border-left:4px solid #d69e32;border-radius:8px}}@media print{{body{{background:white}}main{{padding:0}}header{{background:white;color:#18303e;border:1px solid #b7c5cd}}article{{break-inside:avoid}}}}</style></head><body><main>
<header><div class="eyebrow">ZIP AUDITOR · ANÁLISIS DE UNIFICACIÓN</div><h1>Qué paquetes podrían compartir contenido</h1><p>Resumen por parejas con evidencia de identidad, inclusiones y conflictos. Los originales permanecen intactos.</p><a href="report.html">Abrir el informe detallado</a> · <a href="RESUMEN_FUSIONES.json">Abrir los datos del resumen</a></header>
<div class="grid"><div class="stat"><b>{coverage['archives']}</b><span>ZIP en el informe</span></div><div class="stat"><b>{coverage['examined_pairs']} / {coverage['possible_pairs']}</b><span>parejas comparadas</span></div><div class="stat"><b>{coverage['candidates_returned']}</b><span>parejas mostradas</span></div><div class="stat"><b>{coverage['incomplete_archive_count']}</b><span>ZIP requieren revisión</span></div></div>
<p class="notice"><b>Propuestas solamente.</b> No se ha fusionado ni borrado ningún archivo. La compatibilidad funcional de una distribución combinada está sin verificar.</p>
{distribution_panel}
<p class="meta">Cobertura: {escape(coverage['status'])}. Pares no examinados: {coverage['unexamined_pairs']}; propuestas omitidas: {coverage['candidates_omitted']}; aristas omitidas por el analizador original: {escape(coverage['original_omitted_edges'])}. Los conteos por pareja no constituyen un ahorro global.</p>
{''.join(cards) or '<section class="panel"><h2>Sin propuestas suficientes</h2><p>No hay coincidencias suficientes en el alcance analizado para proponer una unificación.</p></section>'}
{'<section class="panel"><h2>Fuentes que requieren revisión</h2><ul>' + review + '</ul></section>' if review else ''}
<section class="panel"><h2>Cómo preparar una futura fusión</h2><ol>{plan}</ol></section>
<section class="panel"><h2>Alcance y límites</h2><ul>{limits}</ul><p class="meta">Informe de origen SHA-256: <code>{escape(summary.get('source_report_sha256',''))}</code></p></section>
</main></body></html>'''


def _atomic_text(path, text):
    if path.is_symlink():
        raise ValueError("No se sustituye un enlace existente: " + str(path))
    descriptor, temporary = tempfile.mkstemp(prefix=".resumen_", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_summary(report_path: Path) -> dict:
    """Valida la identidad del reporte y añade dos salidas sin modificarlo."""
    report_path = Path(report_path)
    if report_path.name != "report.json" or report_path.is_symlink():
        raise ValueError("Se requiere el report.json original y no un enlace.")
    data = report_path.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    manifest = json.loads((report_path.parent / "SHA256SUMS.json").read_text(encoding="utf-8-sig"))
    verification = json.loads((report_path.parent / "verificacion.json").read_text(encoding="utf-8-sig"))
    if not isinstance(manifest, dict) or manifest.get("report.json") != digest:
        raise ValueError("El informe ha cambiado o no coincide con su manifiesto SHA-256.")
    if not isinstance(verification, dict) or verification.get("status") != "PASS":
        raise ValueError("El informe no tiene una verificación PASS; no se generan propuestas.")
    report = json.loads(data.decode("utf-8-sig"))
    summary = summarize(report)
    summary["source_report_sha256"] = digest
    summary["generated_utc"] = datetime.now(timezone.utc).isoformat()
    summary["source_verification"] = "PASS_RECORDED_AND_REPORT_HASH_MATCHED"
    summary["paths"] = {"json": str(report_path.parent / "RESUMEN_FUSIONES.json"),
                        "html": str(report_path.parent / "RESUMEN_FUSIONES.html")}
    _atomic_text(Path(summary["paths"]["json"]), json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    _atomic_text(Path(summary["paths"]["html"]), _render(summary))
    return summary
