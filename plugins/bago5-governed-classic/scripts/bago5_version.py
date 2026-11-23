#!/usr/bin/env python3
"""Comprobar y sincronizar las etiquetas de versión de una distribución BAGO5.

plugin.json es la fuente de la versión al preparar una release. La comprobación
no acredita qué paquete ha cargado otro proceso ni ejecuta el runtime opcional.
Solo la opción explícita --sync escribe; no modifica prompts ni históricos.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = 'bago5-governed-classic'
_NUM = r'(?:0|[1-9][0-9]*)'
_PRE = r'(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)'
VERSION_PATTERN = re.compile(
    rf'{_NUM}\.{_NUM}\.{_NUM}(?:-{_PRE}(?:\.{_PRE})*)?'
    r'(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?'
)
PATHS = {
    'plugin': 'plugin.json',
    'codex': '.codex-plugin/plugin.json',
    'skill_interface': 'skills/bago5/agents/openai.yaml',
    'skill': 'skills/bago5/SKILL.md',
    'catalog': 'skills/bago5/references/CATALOGO_HABILIDADES.json',
    'routes': 'skills/bago5/references/ROUTES.json',
}
YAML_LABEL = re.compile(r'^(?P<indent>[ \t]+)display_name:[ \t]*(?P<label>[^\r\n]*)$', re.M)
SKILL_HEADING = re.compile(r'^# \$bago5 \((?P<version>[^)\r\n]*)\)[ \t]*$', re.M)


def _read(root: Path) -> tuple[dict, dict, list[str]]:
    texts, objects, issues = {}, {}, []
    for name, relative in PATHS.items():
        try:
            texts[name] = (root / relative).read_text(encoding='utf-8')
            if name in ('plugin', 'codex', 'catalog', 'routes'):
                obj = json.loads(texts[name])
                if not isinstance(obj, dict):
                    raise ValueError('Se requiere un objeto JSON')
                objects[name] = obj
        except (OSError, ValueError, UnicodeError) as exc:
            issues.append(f'{relative}: lectura o formato inválido ({type(exc).__name__})')
    return texts, objects, issues


def _collect(texts: dict, objects: dict, issues: list[str]) -> dict[str, str]:
    checked = {}

    def version(key, value):
        if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
            issues.append(f'{key}: versión SemVer ausente o inválida')
        else:
            checked[key] = value

    def label(key, value, prefix=None):
        match = re.fullmatch(r'(.+) \(([^)]+)\)', value) if isinstance(value, str) else None
        if not match or (prefix is not None and match.group(1) != prefix):
            issues.append(f'{key}: etiqueta versionada ausente o inválida')
        else:
            version(key, match.group(2))

    for name in ('plugin', 'codex'):
        obj = objects.get(name)
        if obj is None:
            continue
        if obj.get('name') != IDENTITY:
            issues.append(f'{name}: identidad de plugin distinta')
        version(name, obj.get('version'))
        if name == 'codex':
            interface = obj.get('interface')
            label('plugin_interface', interface.get('displayName') if isinstance(interface, dict) else None)
        else:
            # También revisar una interfaz portable si se declara en V1.
            extensions = obj.get('extensions', {})
            if not isinstance(extensions, dict):
                issues.append('plugin.extensions: objeto inválido')
            elif 'com.openai' in extensions:
                openai = extensions['com.openai']
                if not isinstance(openai, dict):
                    issues.append('plugin.extensions.com.openai: objeto inválido')
                elif 'interface' in openai:
                    interface = openai['interface']
                    label('portable_plugin_interface', interface.get('displayName') if isinstance(interface, dict) else None)

    if 'skill_interface' in texts:
        yaml_text = texts['skill_interface']
        matches = list(YAML_LABEL.finditer(yaml_text))
        headers = list(re.finditer(r'^interface:[ \t]*$', yaml_text, re.M))
        in_interface = False
        if len(headers) == 1 and len(matches) == 1:
            start = headers[0].end()
            next_header = re.search(r'^\S[^\r\n]*:', yaml_text[start:], re.M)
            end = start + next_header.start() if next_header else len(yaml_text)
            direct_fields = list(re.finditer(r'^( +)[^ \t#][^\r\n:]*:', yaml_text[start:end], re.M))
            indentation = min((len(m.group(1)) for m in direct_fields), default=0)
            in_interface = (start < matches[0].start() < end
                            and matches[0].group('indent') == ' ' * indentation)
        if not in_interface:
            issues.append('skill_interface: se requiere una única etiqueta directa bajo interface')
        else:
            value = matches[0].group('label').strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            label('skill_interface', value, '$bago5')

    if 'skill' in texts:
        matches = list(SKILL_HEADING.finditer(texts['skill']))
        if len(matches) != 1:
            issues.append('skill: se requiere una única cabecera versionada de $bago5')
        else:
            version('skill', matches[0].group('version'))

    catalog = objects.get('catalog')
    if catalog is not None:
        if catalog.get('schema') != 'bago5.catalogo-habilidades.v1' or catalog.get('entry') != '$bago5':
            issues.append('catalog: esquema o punto de entrada incorrecto')
        version('catalog', catalog.get('version'))
        label('catalog_entry', catalog.get('entry_display_name'), '$bago5')
        entries = catalog.get('skills')
        main = [e for e in entries if isinstance(e, dict) and e.get('new_name') == 'bago5'] if isinstance(entries, list) else []
        if len(main) != 1:
            issues.append('catalog_skill: se requiere una única entrada bago5')
        else:
            if main[0].get('new_path') != PATHS['skill'] or main[0].get('invocation') != '$bago5':
                issues.append('catalog_skill: ruta o invocación incorrecta')
            label('catalog_skill', main[0].get('display_name'), '$bago5')
    routes = objects.get('routes')
    if routes is not None:
        if routes.get('plugin') != IDENTITY or routes.get('entry_skill') != PATHS['skill']:
            issues.append('routes: identidad de plugin o punto de entrada incorrecto')
        version('routes', routes.get('plugin_version'))
    return checked


def inspect(root: Path) -> dict:
    """Separar identidad primaria de coherencia sin ocultar ningún fallo."""
    root = Path(root).resolve()
    texts, objects, issues = _read(root)
    checked = _collect(texts, objects, issues)
    if len(set(checked.values())) != 1:
        issues.append('Versiones inconsistentes entre superficies de la distribución')
    package_version = checked.get('plugin')
    if (package_version is None or checked.get('codex') != package_version
            or any(objects.get(name, {}).get('name') != IDENTITY
                   for name in ('plugin', 'codex'))):
        package_version = None
    return {
        'status': 'FAIL' if issues else 'PASS',
        'package_version': package_version,
        'source': 'distribución inspeccionada; identidad por ambos manifiestos y coherencia por todas las superficies',
        'root': str(root),
        'active_host_release_verified': False,
        'checked': checked,
        'issues': issues,
    }


def synchronize(root: Path) -> dict:
    """Actualizar únicamente etiquetas vigentes desde plugin.json, tras validarlas.

    Rechazar fuentes incompletas o identidades ajenas antes de escribir. Cada
    reemplazo es atómico; la comprobación final detecta una interrupción entre
    archivos. No sincronizar mientras otro proceso edita estos mismos archivos.
    """
    root = Path(root).resolve()
    texts, objects, issues = _read(root)
    checked = _collect(texts, objects, issues)
    if issues:
        result = inspect(root)
        result['changed_paths'] = []
        return result
    version = checked['plugin']
    objects['codex']['version'] = version
    interface = objects['codex']['interface']
    interface['displayName'] = re.sub(r' \([^)]+\)$', f' ({version})', interface['displayName'])
    portable = objects['plugin'].get('extensions', {}).get('com.openai', {}).get('interface')
    if portable is not None:
        portable['displayName'] = re.sub(r' \([^)]+\)$', f' ({version})', portable['displayName'])
    catalog = objects['catalog']
    catalog['version'] = version
    catalog['entry_display_name'] = f'$bago5 ({version})'
    next(e for e in catalog['skills'] if isinstance(e, dict) and e.get('new_name') == 'bago5')['display_name'] = f'$bago5 ({version})'
    objects['routes']['plugin_version'] = version
    candidate = {name: json.dumps(obj, ensure_ascii=False, indent=2) + '\n' for name, obj in objects.items()}
    candidate['skill_interface'] = YAML_LABEL.sub(lambda m: f'{m.group("indent")}display_name: $bago5 ({version})', texts['skill_interface'])
    candidate['skill'] = SKILL_HEADING.sub(f'# $bago5 ({version})', texts['skill'])
    changed = []
    for name, contents in candidate.items():
        if contents == texts[name]:
            continue
        path = root / PATHS[name]
        fd, temporary = tempfile.mkstemp(prefix='.bago5-version-', dir=path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
                stream.write(contents)
            os.chmod(temporary, path.stat().st_mode & 0o777)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        changed.append(PATHS[name])
    result = inspect(root)
    result['changed_paths'] = changed
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Comprueba la versión de una distribución BAGO5')
    parser.add_argument('--root', type=Path, default=ROOT, help='Distribución que se inspecciona; por defecto la que contiene este script')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--sync', action='store_true', help='Preparación de release: sincronizar etiquetas desde plugin.json; escribe archivos')
    args = parser.parse_args(argv)
    try:
        result = synchronize(args.root) if args.sync else inspect(args.root)
    except OSError as exc:
        result = {'status': 'FAIL', 'package_version': None, 'issues': [f'No se pudo completar la escritura: {type(exc).__name__}']}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result['status'] == 'PASS':
        print(f"BAGO5 (v{result['package_version']}) — distribución inspeccionada: {result['root']}")
    else:
        heading = (f"BAGO5 (v{result['package_version']})" if result['package_version']
                   else 'BAGO5 (versión NO_COMPROBADA)')
        print(heading + ' — FAIL: ' + '; '.join(result['issues']))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
