"""BAGO5: plantilla lógica inerte y catálogo de habilidades asignables.

Crear una definición NO crea un worker, NO concede permisos y NO accede a memoria.
"""
from __future__ import annotations

import json
from pathlib import Path

TEMPLATE_ID = "bago5-generic"
# Directorio del plugin cuando el runtime opcional conserva su ubicación distribuida.
PLUGIN_ROOT = Path(__file__).resolve().parents[7]
CATALOG_PATH = PLUGIN_ROOT / "skills/bago5/references/CATALOGO_HABILIDADES.json"


class SkillBindingError(ValueError):
    """Asignación inválida o catálogo inaccesible: fallar cerrado."""


def generic_template() -> dict:
    """Definición canónica sin especialización ni autoridad por defecto."""
    return {
        "id": TEMPLATE_ID,
        "name": "Agente genérico",
        "description": "Base clonable; se especializa para una misión.",
        "systemPrompt": "",
        "model": "",
        "provider": "",
        "temperature": 0.7,
        "maxTokens": 4096,
        "enabled": False,
        "skills": [],
        "templateId": TEMPLATE_ID,
        "sandboxMode": "read-only",
        "createdAt": "",
        "updatedAt": "",
        "revision": "1",
    }


def new_generic_clone(agent_id: str, now: str) -> dict:
    """Cada copia parte vacía; jamás hereda prompts, secretos, bindings ni permisos."""
    agent = generic_template()
    agent.update({
        "id": agent_id,
        "name": f"Agente genérico {agent_id}",
        "createdAt": now,
        "updatedAt": now,
    })
    return agent


def available_skills() -> dict[str, str]:
    """Mapea solo habilidades portables publicadas y con fuente existente."""
    try:
        root = PLUGIN_ROOT.resolve()
        catalog = CATALOG_PATH.resolve()
        if not catalog.is_relative_to(root):
            raise SkillBindingError("Catálogo fuera del paquete: denegado")
        data = json.loads(catalog.read_text(encoding="utf-8"))
        entries = data["skills"]
        if not isinstance(entries, list):
            raise ValueError("skills debe ser una lista")
        found: dict[str, str] = {}
        for item in entries:
            if not isinstance(item, dict) or item.get("scope") != "publica":
                continue
            name = item.get("new_name")
            rel = item.get("new_path")
            if not isinstance(name, str) or not name.startswith("bago5-"):
                continue
            if not isinstance(rel, str) or not rel.startswith("skills/"):
                continue
            source = (root / rel).resolve()
            if source.is_relative_to(root / "skills") and source.is_file():
                found[name] = "$" + name
        if not found:
            raise ValueError("Sin habilidades portables comprobables")
        return found
    except (OSError, KeyError, ValueError, TypeError) as exc:
        raise SkillBindingError(f"Catálogo no disponible o inválido: {exc}") from exc


def validate_skill_bindings(value: object) -> list[str]:
    """Valida referencias; NO activa skills ni amplía autorización del host."""
    if not isinstance(value, list) or len(value) > 32:
        raise SkillBindingError("skills debe ser una lista de máximo 32 referencias")
    if not value:
        return []  # Permite retirar habilidades incluso sin catálogo operativo.
    catalog = available_skills()
    selected: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise SkillBindingError("Cada habilidad debe ser un identificador de texto")
        name = item.removeprefix("$")
        if name not in catalog:
            raise SkillBindingError(f"Habilidad inexistente o no portable: {item}")
        canonical = catalog[name]
        if canonical in selected:
            raise SkillBindingError(f"Habilidad duplicada: {item}")
        selected.append(canonical)
    return selected
