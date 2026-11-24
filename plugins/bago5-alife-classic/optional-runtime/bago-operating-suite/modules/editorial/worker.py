#!/usr/bin/env python3
"""Isolated subprocess entry point for the pinned IALP runtime.

Invoked by the Suite adapter, never by importing manuscript/project Python.
An isolated Python process is NOT an operating-system sandbox.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import runpy
import shutil
import sys

PACKAGES = ('mistune', 'PyMuPDF', 'Pillow', 'weasyprint', 'Jinja2', 'PyYAML',
            'Pygments', 'matplotlib', 'openpyxl', 'XlsxWriter', 'graphviz')


def doctor(kit: Path, mmdc: str | None) -> dict:
    versions = {}
    pinned = {}
    for line in (kit / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        if '==' in line and not line.lstrip().startswith('#'):
            name, version = line.strip().split('==', 1)
            pinned[name] = version
    for name in PACKAGES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = 'NOT_INSTALLED'
    native = {'weasyprint_import': 'NOT_RUN'}
    try:
        import weasyprint  # Load native dependencies; no render, network or install.
        native['weasyprint_import'] = 'PASS'
    except (ImportError, OSError) as exc:
        native = {'weasyprint_import': 'FAIL', 'reason': str(exc)}
    missing = [name for name, value in versions.items() if value == 'NOT_INSTALLED']
    drift = {name: {'expected': value, 'actual': versions.get(name)}
             for name, value in pinned.items() if versions.get(name) != value}
    return {
        'status': 'PASS' if not missing and native['weasyprint_import'] == 'PASS' else 'INCONCLUSIVE',
        'python': platform.python_version(), 'python_executable': sys.executable,
        'platform': platform.platform(), 'isolated_mode': sys.flags.isolated,
        'packages': versions, 'missing': missing, 'version_differences': drift,
        'exact_dependency_lock': not drift, 'native': native,
        'external_tools': {'dot': shutil.which('dot'), 'node': shutil.which('node'),
                           'mermaid': mmdc or shutil.which('mmdc')},
        'claim': 'Environment probe, not a render or Windows/Codex acceptance test',
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--kit', type=Path, required=True)
    p.add_argument('--operation', required=True, choices=['doctor', 'preflight', 'build', 'record-review', 'validate-review', 'close', 'test'])
    p.add_argument('--source', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--input', type=Path)
    p.add_argument('--mmdc')
    p.add_argument('--clean-mode', choices=['preserve', 'explicit'], default='preserve')
    p.add_argument('--family', choices=['auto', 'puerta', 'doctrina', 'sintesis'], default='auto')
    p.add_argument('--checklist', type=Path)
    p.add_argument('--reviewer')
    p.add_argument('--pages')
    p.add_argument('--verdict', choices=['PASS', 'FAIL'])
    p.add_argument('--note', default='')
    a = p.parse_args()
    kit = a.kit.resolve(strict=True)
    # Only trusted pinned runtime is imported. Do not add project/source to sys.path.
    sys.path.insert(0, str(kit / '02_SCRIPTS'))
    if a.operation == 'doctor':
        result = doctor(kit, a.mmdc)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'PASS' else 3
    if a.operation == 'preflight':
        from ialp.source import preflight_source
        pattern_path = kit / '05_CONFIG/patrones_no_editoriales.txt'
        patterns = [re.compile(s.strip(), re.I) for s in pattern_path.read_text(encoding='utf-8').splitlines()
                    if s.strip() and not s.lstrip().startswith('#')]
        result = preflight_source(a.source.read_bytes().decode('utf-8'), patterns)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result['status'] == 'PASS' else 3 if result['status'] == 'REVIEW' else 1
    if a.operation == 'test':
        import pytest
        return pytest.main([str(kit / '07_TESTS'), '-q', '-p', 'no:cacheprovider'])
    if a.operation == 'build':
        target = kit / '02_SCRIPTS/07_pipeline_ialp.py'
        argv = [str(a.source), '--outdir', str(a.output), '--clean-mode', a.clean_mode,
                '--family', a.family, '--engine', 'weasyprint', '--pages', 'all']
        if a.mmdc:
            argv += ['--mmdc', a.mmdc]
    elif a.operation == 'record-review':
        run = json.loads((a.input / 'RUN.json').read_text(encoding='utf-8'))
        target = kit / '02_SCRIPTS/09_registrar_revision_visual.py'
        argv = [str(a.input / run['pdf']), '--reviewer', a.reviewer, '--pages', a.pages,
                '--verdict', a.verdict, '--checklist', str(a.checklist), '--note', a.note]
    elif a.operation == 'validate-review':
        target = kit / '02_SCRIPTS/09_registrar_revision_visual.py'
        argv = ['--validate', str(a.input / 'REVISION_VISUAL.json')]
    else:
        target = kit / '02_SCRIPTS/10_cerrar_entrega.py'
        argv = [str(a.input)]
    sys.argv = [str(target), *argv]
    runpy.run_path(str(target), run_name='__main__')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
