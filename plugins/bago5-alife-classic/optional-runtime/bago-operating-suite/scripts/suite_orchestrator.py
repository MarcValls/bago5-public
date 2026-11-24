#!/usr/bin/env python3
"""BAGO Operating Suite deterministic, bounded integration router (stdlib only).

Does not replace BAGO's authority or run arbitrary projects. Bundled packs are
immutable references; explicit BPBR fixture execution is isolated from host work.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import stat
from datetime import datetime, timezone
from uuid import uuid4
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from suite_safety import safe_rel, collision_key, strict_json, read_json, reject_links, new_external_path, write_new_json
from suite_identity import current_identity

SKILL = Path(__file__).resolve().parents[1]
STORE = SKILL / 'integrations' / 'source-packs'
MODULES = {
    'architecture': {'archive': 'AUDITORIA_EXTERNA_BAGO5_ARQUITECTURA_001.zip',
                     'stage': 'baseline', 'kind': 'HISTORICAL_EVIDENCE', 'host': 'NOT_RUN'},
    'bpbr': {'archive': 'BPBR_v0.1_REFERENCE_20261011.zip',
             'stage': 'reference_conformance', 'kind': 'EXECUTABLE_REFERENCE', 'host': 'NOT_RUN'},
    'frontend': {'archive': 'BAGO5_FRONTEND_PACKS_v0.1.zip',
                 'stage': 'ui_specification', 'kind': 'CONTRACTS_AND_MOCK', 'host': 'NOT_RUN'},
}
MODULES['editorial'] = {'archive': 'IALP_EDITORIAL_1.1.0_BAGO_RUNTIME.zip',
                       'stage': 'editorial_generation_review_closure',
                       'kind': 'PINNED_EDITORIAL_RUNTIME', 'host': 'NOT_RUN'}
_REFERENCE_ORDER = ('architecture', 'bpbr', 'frontend')
_ORDER = (*_REFERENCE_ORDER, 'editorial')
_ALLOWED_TOTAL_BYTES = 35_000_000
_SHA256 = re.compile(r'^[0-9a-f]{64}$')


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fail(msg: str) -> dict:
    return {'status': 'FAIL', 'reason': msg}


def _zip_index(zf: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    """Validate raw portable paths before normalization; reject aliases and bombs."""
    index, seen, kinds, total = {}, set(), {}, 0
    infos = zf.infolist()
    if len(infos) > 1000:
        raise ValueError('too many archive members')
    for info in infos:
        raw = info.filename
        if info.orig_filename != raw:
            raise ValueError('archive member contains NUL')
        name = raw[:-1] if info.is_dir() else raw
        safe_rel(name)
        key = collision_key(name)
        if key in seen:
            raise ValueError('duplicate/case-colliding archive member')
        seen.add(key)
        kinds[key] = 'dir' if info.is_dir() else 'file'
        mode = stat.S_IFMT(info.external_attr >> 16)
        if mode not in (0, stat.S_IFREG, stat.S_IFDIR) or info.flag_bits & 1:
            raise ValueError('links, special or encrypted archive members forbidden')
        if (mode == stat.S_IFDIR) != info.is_dir() and mode != 0:
            raise ValueError('archive member type mismatch')
        if info.is_dir():
            continue
        total += info.file_size
        if info.file_size < 0 or total > _ALLOWED_TOTAL_BYTES or len(index) >= 500:
            raise ValueError('archive exceeds bounded verification budget')
        index[raw] = info
    for key in kinds:
        for parent in PurePosixPath(key).parents:
            if str(parent) != '.' and kinds.get(str(parent)) == 'file':
                raise ValueError('archive file/directory prefix conflict')
    if not index:
        raise ValueError('empty source archive')
    return index


def _verify_sha_file(zf: zipfile.ZipFile, prefix: str, index: dict) -> dict:
    record = prefix + 'SHA256SUMS.txt'
    if record not in index:
        raise ValueError('missing inner SHA256SUMS')
    lines = zf.read(record).decode('utf-8').splitlines()
    checked = set()
    for line in lines:
        match = re.fullmatch(r'([0-9a-f]{64})  (.+)', line)
        if not match:
            raise ValueError('invalid SHA256SUMS entry')
        digest, rel = match.groups()
        safe_rel(rel)
        member = prefix + rel
        if member in checked or member not in index:
            raise ValueError('duplicate or missing member declared')
        data = zf.read(member)
        if _digest(data) != digest:
            raise ValueError('inner SHA256 mismatch: ' + rel)
        checked.add(member)
    expected = set(index) - {record}
    # BPBR duplicates its top-level checksums at evidence/FILE_HASHES.sha256.
    mirror = prefix + 'evidence/FILE_HASHES.sha256'
    if mirror in expected:
        if zf.read(mirror) != zf.read(record):
            raise ValueError('BPBR evidence hash mirror mismatch')
        expected.remove(mirror)
    if checked != expected:
        raise ValueError('SHA256SUMS coverage incomplete: ' + str(sorted(expected - checked)[:4]))
    return {'inner_items_verified': len(checked), 'inner_hashes': 'PASS'}


def _verify_frontend(zf: zipfile.ZipFile, prefix: str, index: dict) -> dict:
    record = prefix + 'MANIFEST_SHA256.json'
    obj = strict_json(zf.read(record))
    checked = set()
    for item in obj['files']:
        rel = safe_rel(item['path']).as_posix()
        member = prefix + rel
        if member in checked or member not in index:
            raise ValueError('missing/duplicate frontend manifest path')
        data = zf.read(member)
        if _digest(data) != item['sha256'] or len(data) != item['size']:
            raise ValueError('frontend SHA or size mismatch: ' + rel)
        checked.add(member)
    # The source also includes secondary packed copies in PACKS_COMPRIMIDOS;
    # these are protected by the outer archive's locked digest, not inner list.
    extra = sorted(set(index) - checked - {record})
    if any(not x.startswith(prefix + 'PACKS_COMPRIMIDOS/') for x in extra):
        raise ValueError('unaccounted frontend member')
    return {'inner_items_verified': len(checked), 'nested_pack_copies': len(extra),
            'inner_hashes': 'PASS'}


def verify_module(module: str, *, blob: bytes | None = None) -> dict:
    name = MODULES[module]['archive']
    try:
        source_lock = read_json(STORE / 'SOURCE_PACKS_LOCK.json')
        if source_lock.get('schema') != 'bago.suite.integrations.sources.v1':
            raise ValueError('unexpected source lock schema')
        recorded = source_lock['sources'][name]
        source = STORE / name
        reject_links(source)
        if blob is None:
            if source.stat().st_size > _ALLOWED_TOTAL_BYTES:
                raise ValueError('source archive exceeds read budget')
            blob = source.read_bytes()
        if _digest(blob) != recorded['sha256'] or len(blob) != recorded['size']:
            raise ValueError('source archive differs from locked identity')
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            index = _zip_index(zf)
            roots = {k.split('/')[0] for k in index}
            if len(roots) != 1:
                raise ValueError('source contains multiple roots')
            prefix = next(iter(roots)) + '/'
            if module == 'frontend':
                detail = _verify_frontend(zf, prefix, index)
            else:
                detail = _verify_sha_file(zf, prefix, index)
        return {'module': module, 'status': 'PASS', 'archive_sha256': recorded['sha256'],
                'archive_bytes': len(blob), 'zip_members': len(index), **detail,
                'host_integration': 'NOT_RUN', 'authority': 'UNCHANGED'}
    except (KeyError, TypeError, AttributeError, ValueError, OSError, zipfile.BadZipFile, UnicodeError) as exc:
        return {'module': module, **_fail(str(exc)), 'host_integration': 'NOT_RUN'}


def _selected(names: str) -> list[str]:
    if names == 'all':
        return list(_ORDER)
    selected = [s.strip() for s in names.split(',')]
    if not selected or any(s not in MODULES for s in selected):
        raise ValueError('modules must be all, architecture, bpbr, frontend, editorial or comma-separated subset')
    return [name for name in _ORDER if name in selected]


def _plan(task: str, explicitly: str | None) -> dict:
    if explicitly:
        modules = _selected(explicitly)
    else:
        txt = task.casefold()
        editorial_intent = any(word in txt for word in ('$bago-pdf', 'ialp', 'maquet', 'editorial', 'pdf', 'manual'))
        words = {
            'architecture': ('auditor', 'arquitect', 'brecha', 'contract audit', 'arquitectura', 'scaffold'),
            'bpbr': ('bpbr', 'comportam', 'behavior', 'compos', 'procedural'),
            'frontend': ('frontend', 'interfaz', 'configur', 'pantalla', 'visual', 'ui ', 'react'),
        }
        words['editorial'] = ('$bago-pdf', 'ialp', 'maquet', 'editorial', 'pdf', 'manual')
        if editorial_intent:
            # A PDF audit/visual composition is not an architecture/BPBR/UI task.
            words['architecture'] = ('arquitect', 'architecture', 'contract audit', 'scaffold')
            words['bpbr'] = ('bpbr', 'comportam', 'behavior', 'procedural')
            words['frontend'] = ('frontend', 'interfaz', 'pantalla', 'react', 'ui ')
        modules = [name for name in _ORDER if any(word in txt for word in words[name])]
        if not modules:
            modules = ['architecture']  # safe read-only preliminary disposition
    return {'status': 'PROPOSED', 'requested_task': task, 'authority': 'OPERATING_LAYER',
            'actions_executed': [], 'delegations': [
                {'module': name, 'stage': MODULES[name]['stage'],
                 'requires': 'explicit read authorization for target project',
                 'source_type': MODULES[name]['kind'], 'host_state': 'NOT_RUN'} for name in modules],
            'gates': ['project root, scope, branch and hash preflight',
                      'do not equate reference pack with live runtime',
                      'do not grant effects through BPBR reference flags',
                      'test positive/negative and preserve prior capabilities',
                      'require independent evidence before VERIFIED/GO',
                      'editorial generation never implies visual approval or functional verification'],
            'outcome': 'PLAN_ONLY'}


def _verified_blob(module: str):
    """Hash and subsequently use the SAME in-memory bytes, avoiding path reopens."""
    source = STORE / MODULES[module]['archive']
    reject_links(source)
    if source.stat().st_size > _ALLOWED_TOTAL_BYTES:
        raise ValueError('source archive exceeds byte budget')
    blob = source.read_bytes()
    integrity = verify_module(module, blob=blob)
    return integrity, blob


def _reference_root(zf: zipfile.ZipFile, dest: Path) -> Path:
    """Extract locked BPBR source into a disposable workspace, not into project."""
    idx = _zip_index(zf)
    for name in idx:
        out = dest.joinpath(*PurePosixPath(name).parts)
        if not out.resolve().is_relative_to(dest.resolve()):
            raise ValueError('unsafe member target')
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open('xb') as stream:
            stream.write(zf.read(name))
    return dest / next(iter({name.split('/')[0] for name in idx}))


def bpbr_run(mode: str, output: Path | None) -> dict:
    if mode not in ('test', 'demo'):
        return _fail('unsupported BPBR operation')
    integrity, blob = _verified_blob('bpbr')
    if integrity['status'] != 'PASS':
        return integrity
    if mode == 'demo':
        if output is None:
            return _fail('explicit --output required')
        # Prevent overwriting existing evidence, including a directory, and
        # prevent operating inside the installed suite tree.
        try:
            output = new_external_path(output, (SKILL.parent,))
        except (ValueError, OSError) as exc:
            return _fail(str(exc))
    try:
        with tempfile.TemporaryDirectory(prefix='bago-bpbr-reference-') as tmp:
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                cwd = _reference_root(zf, Path(tmp))
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8')
            for name in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP'):
                env.pop(name, None)
            if mode == 'test':
                cmd = [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v']
            else:
                cmd = [sys.executable, '-B', '-m', 'bpbr.demo', '--output', str(output)]
            res = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=100)
            return {'module': 'bpbr', 'operation': 'REFERENCE_'+mode.upper(),
                    'status': 'PASS' if res.returncode == 0 else 'FAIL',
                    'returncode': res.returncode, 'stdout_tail': res.stdout[-2200:],
                    'stderr_tail': res.stderr[-3500:],
                    'host_integration': 'NOT_RUN', 'os_sandbox': 'NOT_PROVIDED',
                    'evidence': str(output / 'DEMO_EVIDENCE.json') if mode == 'demo' and res.returncode == 0 else None}
    except (OSError, ValueError, subprocess.TimeoutExpired, zipfile.BadZipFile) as exc:
        return {'module': 'bpbr', **_fail(str(exc))}


def frontend_preview(output: Path) -> dict:
    integrity, blob = _verified_blob('frontend')
    if integrity['status'] != 'PASS':
        return integrity
    try:
        output = new_external_path(output, (SKILL.parent,))
    except (ValueError, OSError) as exc:
        return _fail(str(exc))
    archive = STORE / MODULES['frontend']['archive']
    files = {}
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        index = _zip_index(zf)
        for member in index:
            marker = '/PACK_08_PREVIEW_REFERENCES/'
            if marker in member:
                relative = member.split(marker, 1)[1]
                if relative:
                    files[relative] = zf.read(member)
    if 'preview.html' not in files:
        return _fail('mock preview missing from verified source')
    # Explicit derived preview patch, never mutate the locked source archive.
    patch_root = SKILL / 'modules/frontend-contracts'
    metadata = read_json(patch_root/'PREVIEW_PROVENANCE.json')
    reject_links(patch_root/'preview_auditada.html')
    derived = (patch_root/'preview_auditada.html').read_bytes()
    if _digest(files['preview.html']) != metadata['source_html_sha256'] or _digest(derived) != metadata['derived_sha256']:
        return _fail('derived preview provenance/hash mismatch')
    files['preview.html'] = derived
    files['PREVIEW_PROVENANCE.json'] = json.dumps(metadata, indent=2).encode('utf-8')
    # A fresh output directory is required; never merge with user files.
    output.mkdir(parents=True, exist_ok=False)
    for relative, data in files.items():
        path = output.joinpath(*PurePosixPath(relative).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as out:
            out.write(data)
    return {'status': 'PASS', 'module': 'frontend', 'kind': 'MOCK_ONLY',
            'browser_tests': 'NOT_RUN', 'connected_backend': 'NOT_RUN',
            'preview': str(output / 'preview.html'), 'exported_files': len(files),
            'preview_variant': 'DERIVED_AUDIT_1.3.1', 'preview_sha256': _digest(derived)}


def architecture_report() -> dict:
    integrity, blob = _verified_blob('architecture')
    if integrity['status'] != 'PASS':
        return integrity
    archive = STORE / MODULES['architecture']['archive']
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        index = _zip_index(zf)
        root = next(iter({name.split('/')[0] for name in index}))
        gap = strict_json(zf.read(root+'/evidence/gap-register.json'))
        identity = strict_json(zf.read(root+'/evidence/IDENTITY.json'))
    by_status = {}
    for item in gap.get('gaps', []):
        k = item.get('status', 'UNKNOWN')
        by_status[k] = by_status.get(k, 0) + 1
    return {'status': 'PASS', 'module': 'architecture', 'kind': 'HISTORICAL_READ_ONLY',
            'pack_identity': identity, 'gap_status_counts': by_status,
            'live_repository_audited': False, 'new_audit': 'NOT_RUN',
            'note': 'report summarizes supplied evidence, not independent current verification'}


def orchestrated_reference_demo(output: Path, with_editorial: bool = False, python: str | None = None, mmdc: str | None = None) -> dict:
    """Sequential required gates, explicit NOT_RUN for dependent skipped steps."""
    try:
        output = new_external_path(output, (SKILL.parent,))
    except (ValueError, OSError) as exc:
        return _fail(str(exc))
    identity = current_identity(SKILL)
    integrity = {k: verify_module(k) for k in (_ORDER if with_editorial else _REFERENCE_ORDER)}
    if any(v['status'] != 'PASS' for v in integrity.values()):
        return {'status': 'FAIL', 'gate': 'SOURCE_INTEGRITY', 'checks': integrity,
                'actions_executed': []}
    output.mkdir(parents=True, exist_ok=False)
    actions = [
        ('ARCHITECTURE_HISTORICAL_BASELINE', architecture_report),
        ('BPBR_REFERENCE_TESTS', lambda: bpbr_run('test', None)),
        ('BPBR_ACQUIRE_REUSE_FIXTURE', lambda: bpbr_run('demo', output/'bpbr-demo')),
        ('FRONTEND_OFFLINE_MOCK', lambda: frontend_preview(output/'frontend-mock')),
    ]
    if with_editorial:
        import argparse as _args
        fixture = output / 'editorial-source'
        fixture.mkdir()
        shutil_source = SKILL / 'modules/editorial/fixtures/SMOKE.md'
        (fixture / 'SMOKE.md').write_bytes(shutil_source.read_bytes())
        action_args = _args.Namespace(operation='build', source=fixture/'SMOKE.md', output=output/'editorial-draft',
            input=None, python=python, mmdc=mmdc, clean_mode='preserve', family='auto', timeout=300,
            checklist=None, reviewer=None, pages=None, verdict=None, note='')
        actions.append(('EDITORIAL_DRAFT_AUTOMATIC_CHECKS', lambda: _editorial_execute(action_args)))
    steps, blocked = [], None
    for name, action in actions:
        if blocked:
            result = {'status': 'NOT_RUN', 'reason': 'required gate did not pass: ' + blocked}
        else:
            try:
                result = action()
                if not isinstance(result, dict) or 'status' not in result:
                    result = _fail('invalid child result')
            except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
                result = _fail(str(exc))
            if result['status'] != 'PASS':
                blocked = name
        steps.append({'step': name, 'result': result})
    verdict = 'PASS' if blocked is None else 'FAIL'
    receipt = {
        'schema': 'bago.suite.orchestrated_reference.v1',
        'suite_version': identity['version'],
        'candidate': identity['candidate'],
        'suite_identity': identity,
        'run_id': str(uuid4()), 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'orchestrator_sha256': _digest(Path(__file__).read_bytes()),
        'status': verdict, 'authority': 'READ_REFERENCE_ONLY_AND_EXPLICIT_LOCAL_FIXTURES',
        'origin_archives': {key: value['archive_sha256'] for key, value in integrity.items()},
        'orchestrator': 'BAGO Operating Suite Operating Layer', 'steps': steps,
        'real_BAGO5_integration': 'NOT_RUN', 'production_execution_authorization': 'NOT_RUN',
        'frontend_real_backend': 'NOT_RUN', 'new_independent_architecture_audit': 'NOT_RUN',
        'os_sandbox': 'NOT_PROVIDED',
        'editorial_visual_review': 'NOT_RUN',
        'editorial_document_release': 'DRAFT_REQUIRES_VISUAL_REVIEW' if with_editorial else 'NOT_RUN',
        'conclusion': 'reference package orchestration only, not product verification',
    }
    write_new_json(output/'ORCHESTRATION_RECEIPT.json', receipt)
    return {'status': verdict, 'operation': 'ORCHESTRATED_REFERENCE',
            'receipt': str(output/'ORCHESTRATION_RECEIPT.json'), 'host_integration': 'NOT_RUN',
            'steps': [{'step': r['step'], 'status': r['result']['status']} for r in steps]}


def _editorial_execute(args) -> dict:
    # Lazy load: no external dependency enters ordinary Suite commands.
    from types import SimpleNamespace
    from suite_editorial import execute
    context = SimpleNamespace(SKILL=SKILL, _verified_blob=_verified_blob, _reference_root=_reference_root)
    return execute(args, context)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='BAGO5os 1.4.6 SESSION CONTEXT RC1: bounded control and observable execution')
    sub = p.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('identity', help='Verify the exact installed payload and print its identity')
    plan = sub.add_parser('plan');plan.add_argument('--task', required=True)
    plan.add_argument('--modules', default=None)
    check = sub.add_parser('verify');check.add_argument('--modules', default='all')
    sub.add_parser('bpbr-test')
    flow = sub.add_parser('orchestrated-demo');flow.add_argument('--output', required=True, type=Path)
    flow.add_argument('--with-editorial', action='store_true')
    flow.add_argument('--python');flow.add_argument('--mmdc')
    sub.add_parser('architecture-report')
    fprev = sub.add_parser('frontend-preview');fprev.add_argument('--output', required=True, type=Path)
    demo = sub.add_parser('bpbr-demo');demo.add_argument('--output', required=True, type=Path)
    snap = sub.add_parser('snapshot');snap.add_argument('--root', type=Path, required=True)
    snap.add_argument('--output', type=Path, required=True)
    snap.add_argument('--before', type=Path)
    snap.add_argument('--include', action='append', required=True)
    snap.add_argument('--exclude', action='append', default=[])
    snap.add_argument('--max-files', type=int, default=10000)
    snap.add_argument('--max-bytes', type=int, default=100_000_000)
    editorial = sub.add_parser('editorial', help='Explicit editorial operations; no dependency installation')
    editorial.add_argument('operation', choices=['doctor', 'export-kit', 'preflight', 'build', 'record-review', 'validate-review', 'close', 'test'])
    editorial.add_argument('--source', type=Path)
    editorial.add_argument('--input', type=Path)
    editorial.add_argument('--output', type=Path)
    editorial.add_argument('--python', help='Executable of an external editorial Python environment')
    editorial.add_argument('--mmdc', help='Explicit local Mermaid executable; no downloads')
    editorial.add_argument('--clean-mode', choices=['preserve', 'explicit'], default='preserve')
    editorial.add_argument('--family', choices=['auto', 'puerta', 'doctrina', 'sintesis'], default='auto')
    editorial.add_argument('--timeout', type=int, default=300)
    editorial.add_argument('--reviewer')
    editorial.add_argument('--pages')
    editorial.add_argument('--verdict', choices=['PASS', 'FAIL'])
    editorial.add_argument('--checklist', type=Path)
    editorial.add_argument('--note', default='')
    from suite_control import add_parser as add_control_parser
    from suite_runtime import add_parsers as add_runtime_parsers
    add_control_parser(sub)
    add_runtime_parsers(sub)
    from suite_cognitive import add_parser as add_cognitive_parser
    add_cognitive_parser(sub)
    from suite_pytest_checkpoint import add_parser as add_pytest_checkpoint_parser
    add_pytest_checkpoint_parser(sub)
    from suite_context import add_parser as add_context_parser
    add_context_parser(sub)
    from suite_context_lifecycle import add_parser as add_lifecycle_parser
    add_lifecycle_parser(sub)
    args = p.parse_args(argv)
    try:
        from types import SimpleNamespace
        context = SimpleNamespace(SKILL=SKILL, candidate_identity=lambda: current_identity(SKILL))
        if args.command == 'context-lifecycle':
            from suite_context_lifecycle import execute as lifecycle_execute
            result = lifecycle_execute(args, context)
        elif args.command == 'session-context':
            from suite_context import execute
            result = execute(args, context)
        elif args.command == 'pytest-checkpoint':
            from suite_pytest_checkpoint import execute
            result = execute(args, context)
        elif args.command == 'cognitive':
            from suite_cognitive import execute
            result = execute(args, context)
        elif args.command == 'identity':
            result = {'status': 'PASS', 'identity': current_identity(SKILL)}
        elif args.command == 'task':
            from suite_control import execute
            result = execute(args, context)
        elif args.command in {'spiral', 'adaptation'}:
            from suite_runtime import execute
            current_identity(SKILL)
            result = execute(args, context)
        elif args.command == 'status':
            result = {'status': 'READY_TO_ROUTE', 'orchestrator': 'BAGO Operating Layer',
                      'suite_identity': current_identity(SKILL),
                      'execution_authority': 'HOST_ONLY',
                      'modules': {k: {**v, 'attached_to_suite': True} for k,v in MODULES.items()},
                      'snapshot_sha256': 'AVAILABLE',
                      'agent_collaboration': 'OPT_IN; task collaborate enable/guide/claim/offer/accept; serial; host agents NOT_RUN',
                      'session_context': 'V1 legacy retained; V2 context-lifecycle opt-in; host hook NOT_RUN',
                      'context_lifecycle': 'NATIVE; read/plan/apply via TaskStore + STOP + Relay idle gate; host grants NOT_CLAIMED',
                      'pytest_checkpoint': 'OPT_IN; use pytest-checkpoint doctor/demo/run/resume/status',
                      'editorial_dependencies': 'CHECK_WITH_EDITORIAL_DOCTOR',
                      'real_project_integration': 'NOT_RUN'}
        elif args.command == 'plan':
            result = _plan(args.task, args.modules)
        elif args.command == 'verify':
            rows = [verify_module(m) for m in _selected(args.modules)]
            result = {'status': 'PASS' if all(row['status']=='PASS' for row in rows) else 'FAIL',
                      'checks': rows, 'claim': 'bundled source integrity ONLY',
                      'live_frontend': 'NOT_RUN', 'live_bpbr': 'NOT_RUN', 'new_architecture_audit': 'NOT_RUN'}
        elif args.command == 'editorial':result = _editorial_execute(args)
        elif args.command == 'orchestrated-demo':result = orchestrated_reference_demo(args.output, args.with_editorial, args.python, args.mmdc)
        elif args.command == 'architecture-report':result = architecture_report()
        elif args.command == 'frontend-preview':result = frontend_preview(args.output)
        elif args.command == 'bpbr-test':result = bpbr_run('test', None)
        elif args.command == 'bpbr-demo':result = bpbr_run('demo', args.output)
        else:
            script = SKILL / 'modules/bago-app-game-development/scripts/project_snapshot_diff.py'
            cmd = [sys.executable, '-B', str(script), '--root', str(args.root), '--output', str(args.output)]
            if args.before:cmd += ['--before', str(args.before)]
            for pat in args.include:cmd += ['--include', pat]
            for pat in args.exclude:cmd += ['--exclude', pat]
            cmd += ['--max-files', str(args.max_files), '--max-bytes', str(args.max_bytes)]
            result_cmd = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
            child = strict_json(result_cmd.stdout)
            if not isinstance(child, dict):
                raise ValueError('invalid snapshot result')
            diff = child.get('diff')
            if diff is not None and not isinstance(diff, dict):
                raise ValueError('invalid snapshot diff result')
            partial = child.get('state') == 'PARTIAL' or (diff or {}).get('result') == 'INCONCLUSIVE'
            status = 'FAIL'
            if child.get('ok') is True and result_cmd.returncode in (0, 3):
                if partial or child.get('status') == 'INCONCLUSIVE':
                    status = 'INCONCLUSIVE'
                elif result_cmd.returncode == 0 and child.get('state') == 'COMPLETE' and child.get('status') == 'PASS':
                    status = 'PASS'
            result = {'status': status, 'operation': 'SNAPSHOT',
                      'returncode': result_cmd.returncode, 'snapshot_result': child,
                      'stderr': result_cmd.stderr[-2000:],
                      'note': 'content identity is not functional equivalence'}
    except (ValueError, TypeError, KeyError, OSError, ImportError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
        result = _fail(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    status = result.get('status')
    if status in {'PASS', 'PROPOSED', 'READY_TO_ROUTE', 'REVIEW_REQUIRED', 'CONTEXT_MISSING'}:
        return 0
    return 3 if status in {'INCONCLUSIVE', 'BLOCKED', 'NOT_RUN'} else 1


if __name__ == '__main__':
    raise SystemExit(main())
