#!/usr/bin/env python3
"""Editorial specialist adapter. Stdlib only; all editorial imports are deferred.

The Operating Layer owns authority. The IALP pipeline owns document generation.
Never infer visual review, semantic correctness or product verification from a
successful process exit. No automatic installation, overwrite or network grant.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
from uuid import uuid4
import zipfile

from suite_safety import safe_rel, collision_key, read_json, strict_json, reject_links, new_external_path, write_new_json

SUITE_VERSION = '1.4.0'
ADAPTER_VERSION = '1.0.0'
MAX_FILES = 5000
MAX_BYTES = 250_000_000
MAX_SOURCE = 5_000_000
MAX_LOG = 1_000_000
OPERATIONS = ('doctor', 'export-kit', 'preflight', 'build', 'record-review', 'validate-review', 'close', 'test')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def _file(path: Path, max_bytes=MAX_BYTES) -> Path:
    reject_links(path)
    path = path.expanduser().resolve(strict=True)
    st = path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_size > max_bytes:
        raise ValueError('input must be a bounded regular file')
    return path


def _tree(root: Path) -> dict[str, dict]:
    """Bounded read-only inventory; reject links, aliases and special files."""
    reject_links(root)
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('input must be a directory')
    result, keys, total = {}, set(), 0
    def error(exc):
        raise exc
    for base, dirs, files in os.walk(root, onerror=error, followlinks=False):
        for name in sorted(dirs + files):
            path = Path(base) / name
            reject_links(path)
            rel = safe_rel(path.relative_to(root).as_posix()).as_posix()
            key = collision_key(rel)
            if key in keys:
                raise ValueError('case-colliding input paths')
            keys.add(key)
            st = path.stat()
            if stat.S_ISDIR(st.st_mode):
                continue
            if not stat.S_ISREG(st.st_mode):
                raise ValueError('special input file forbidden')
            total += st.st_size
            if len(result) >= MAX_FILES or total > MAX_BYTES:
                raise ValueError('editorial input exceeds inventory budget')
            result[rel] = {'sha256': _file_digest(path), 'bytes': st.st_size}
    return result


def _check_evidence(root: Path) -> None:
    """Constrain evidence before invoking upstream validation (read-only)."""
    run = read_json(root / 'RUN.json')
    pdf = safe_rel(run['pdf']).as_posix()
    _file(root / pdf)
    for rel in run.get('generation_files', {}):
        safe_rel(rel)
        _file(root / rel)
    review_path = root / 'REVISION_VISUAL.json'
    if review_path.exists():
        review = read_json(review_path)
        for item in review.get('evidence', {}).values():
            rel = safe_rel(item['path']).as_posix()
            _file(root / rel)


def _validate_generation(root: Path) -> dict:
    """Reconcile the child success claim with complete current file evidence."""
    run = read_json(root / 'RUN.json')
    if run.get('schema') != 'ialp.run.v1' or run.get('visual_review') != 'NOT_RUN':
        raise ValueError('unexpected generation schema or implicit visual approval')
    inventory = run.get('generation_files')
    if not isinstance(inventory, dict) or not inventory:
        raise ValueError('missing generation inventory')
    pdf = safe_rel(run['pdf']).as_posix()
    required = {pdf, str(Path(pdf).with_suffix('.html')), 'AUDITORIA.json', 'VISUALES.json',
                'MAQUETACION.json', 'LIMPIEZA.json', 'verificacion_visual/PREVIEW.json'}
    if not required.issubset(inventory):
        raise ValueError('incomplete generation evidence coverage')
    for relative, expected in inventory.items():
        rel = safe_rel(relative).as_posix()
        path = _file(root / rel)
        if _file_digest(path) != expected:
            raise ValueError('generation evidence changed: ' + rel)
    if _file_digest(root / pdf) != run.get('pdf_sha256'):
        raise ValueError('PDF identity differs from generation receipt')
    audit = read_json(root / 'AUDITORIA.json')
    if (audit.get('pdf_sha256') != run['pdf_sha256'] or audit.get('TEXT_AUDIT') != 'PASS'
            or audit.get('CONTENT_CHECK') != 'PASS'):
        raise ValueError('automatic audit is not current or did not pass')
    preview = read_json(root / 'verificacion_visual/PREVIEW.json')
    n = preview.get('total_pages')
    if (type(n) is not int or n <= 0 or preview.get('coverage') != 'ALL_PAGES'
            or preview.get('selected_pages') != list(range(1, n + 1))
            or preview.get('pdf_sha256') != run['pdf_sha256']):
        raise ValueError('missing or incomplete all-page preview evidence')
    for entry in preview.get('images', []) + preview.get('contact_sheets', []):
        rel = 'verificacion_visual/' + safe_rel(entry['path']).as_posix()
        if rel not in inventory or inventory[rel] != entry['sha256']:
            raise ValueError('preview is not bound to generation inventory')
    if len(preview.get('images', [])) != n:
        raise ValueError('preview image count does not match the document')
    return {'generation_files_verified': len(inventory), 'pages_with_previews': n,
            'run_sha256': _file_digest(root / 'RUN.json'), 'environment': run.get('environment', {})}


def _copy_input(root: Path, output: Path, inventory: dict) -> None:
    """Copy a captured inventory; do not follow links or reuse old receipts."""
    output.mkdir(parents=True, exist_ok=False)
    excluded = {'BAGO_EDITORIAL_RECEIPT.json', 'BAGO_PIPELINE_STDOUT.log', 'BAGO_PIPELINE_STDERR.log'}
    for rel, entry in inventory.items():
        if rel in excluded or rel.endswith(('_BORRADOR.zip', '_ENTREGA.zip')):
            continue
        origin = _file(root / rel)
        data = origin.read_bytes()
        if len(data) != entry['bytes'] or digest(data) != entry['sha256']:
            raise ValueError('input changed while copying: ' + rel)
        dest = output / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('xb') as stream:
            stream.write(data)


def _interpreter(value: str | None) -> str:
    # Preserve a venv path: resolving its symlink can escape the venv.
    selected = value or sys.executable
    found = shutil.which(selected)
    if found is None and Path(selected).is_file():
        found = str(Path(selected).expanduser().absolute())
    if not found or not Path(found).is_file():
        raise ValueError('Python executable not found; use --python with a real executable')
    return str(Path(found).absolute())


def _tool(value: str | None) -> str | None:
    if not value:
        return shutil.which('mmdc')
    found = shutil.which(value) or (str(Path(value).absolute()) if Path(value).is_file() else None)
    if not found:
        raise ValueError('Mermaid executable not found; no automatic download is performed')
    return found


def _process(cmd: list[str], cwd: Path, timeout: int) -> tuple[int, str, str]:
    env = dict(os.environ)
    for key in list(env):
        if key.startswith('PYTHON'):
            env.pop(key, None)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8',
               MPLCONFIGDIR=str(cwd / '.mpl'), XDG_CACHE_HOME=str(cwd / '.cache'))
    # Log to temporary files: subprocess output must not grow unbounded in memory.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=stdout, stderr=stderr, shell=False,
                                start_new_session=(os.name != 'nt'))
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                import signal
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()  # Not a Windows job object; descendant containment NOT_RUN.
            proc.wait()
            raise TimeoutError('editorial subprocess exceeded the declared time budget')
        def tail(stream):
            n = stream.tell()
            stream.seek(max(0, n - MAX_LOG))
            return stream.read(MAX_LOG).decode('utf-8', errors='replace')
        return proc.returncode, tail(stdout), tail(stderr)


def execute(args, router) -> dict:
    """Execute only the chosen specialist action under the central router."""
    op = args.operation
    if op not in OPERATIONS:
        raise ValueError('unknown editorial operation')
    timeout = args.timeout
    if type(timeout) is not int or not 1 <= timeout <= 1800:
        raise ValueError('--timeout must be between 1 and 1800 seconds')
    integrity, blob = router._verified_blob('editorial')
    if integrity['status'] != 'PASS':
        return {'status': 'FAIL', 'gate': 'EDITORIAL_SOURCE_INTEGRITY', 'integrity': integrity,
                'actions_executed': []}
    kit_identity = integrity['archive_sha256']
    worker = router.SKILL / 'modules/editorial/worker.py'
    worker = _file(worker, 100_000)
    source = None
    output = None
    inputs = None
    source_before = None
    input_inventory = None
    checklist = None
    protected = (router.SKILL.parent,)
    if op in ('preflight', 'build'):
        if args.source is None:
            raise ValueError('--source is required')
        source = _file(args.source, MAX_SOURCE)
        if source.suffix.lower() != '.md':
            raise ValueError('the source must be an explicit Markdown (.md) file')
        if source.is_relative_to(router.SKILL.parent.resolve()):
            raise ValueError('copy the manuscript outside the installed suite before building')
        source_before = _file_digest(source)
        protected += (source.parent,)
    if op in ('record-review', 'validate-review', 'close'):
        if args.input is None:
            raise ValueError('--input is required')
        reject_links(args.input)
        inputs = args.input.expanduser().resolve(strict=True)
        if inputs.is_relative_to(router.SKILL.parent.resolve()):
            raise ValueError('editorial evidence must be outside the installed suite')
        input_inventory = _tree(inputs)
        _check_evidence(inputs)
        protected += (inputs,)
        if op in ('record-review', 'close') and (inputs / 'ENTREGA.json').exists():
            raise ValueError('already finalized: preserve the closed delivery and start a new generation')
        if op == 'record-review':
            if (inputs / 'REVISION_VISUAL.json').exists():
                raise ValueError('existing visual receipt must not be overwritten')
            if not all((args.reviewer, args.pages, args.verdict, args.checklist)):
                raise ValueError('review requires --reviewer, --pages, --verdict and --checklist')
            checklist = _file(args.checklist, 100_000)
            read_json(checklist, 100_000)  # Fail closed on duplicate JSON keys, before execution.
    if op in ('build', 'record-review', 'close', 'export-kit', 'test'):
        if args.output is None:
            raise ValueError('--output is required and must be a new directory')
        output = new_external_path(args.output, protected)
    elif args.output is not None:
        raise ValueError('this read-only operation does not accept --output')
    if args.clean_mode not in ('preserve', 'explicit'):
        raise ValueError('legacy cleanup is not routed by the Suite')
    result = {
        'schema': 'bago.suite.editorial.operation.v1', 'suite_version': SUITE_VERSION,
        'adapter_version': ADAPTER_VERSION, 'operation': op, 'module': 'editorial',
        'run_id': str(uuid4()), 'started_at': datetime.now(timezone.utc).isoformat(),
        'status': 'FAIL', 'kit_archive_sha256': kit_identity,
        'adapter_sha256': _file_digest(Path(__file__)), 'worker_sha256': _file_digest(worker),
        'authority': 'HOST_ONLY_EXPLICIT_INPUTS_AND_NEW_OUTPUTS',
        'os_sandbox': 'NOT_PROVIDED', 'network_isolation': 'NOT_PROVIDED',
        'automatic_dependency_install': False,
        'visual_review': 'NOT_RUN', 'document_release': 'NOT_APPROVED',
        'source': str(source) if source else None, 'source_sha256_before': source_before,
        'input': str(inputs) if inputs else None,
        'input_inventory_sha256': digest(json.dumps(input_inventory, sort_keys=True).encode()) if input_inventory else None,
    }
    stdout = stderr = ''
    with tempfile.TemporaryDirectory(prefix='bago-editorial-') as temp:
        tmp = Path(temp)
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            kit = router._reference_root(zf, tmp / 'runtime')
        try:
            if op == 'export-kit':
                shutil.copytree(kit, output)
                result.update(status='PASS', runtime=str(output), dependencies_installed=False,
                              claim='Pinned runtime exported, not installed or executed')
            else:
                python = _interpreter(args.python)
                mmdc = _tool(args.mmdc)
                command = [python, '-I', '-B', str(worker), '--kit', str(kit), '--operation', op]
                result['python_executable'] = python
                if mmdc:
                    command += ['--mmdc', mmdc]
                if source:
                    command += ['--source', str(source)]
                if op == 'build':
                    command += ['--output', str(output), '--clean-mode', args.clean_mode, '--family', args.family]
                if op in ('record-review', 'close'):
                    _copy_input(inputs, output, input_inventory)
                    command += ['--input', str(output)]
                    if op == 'record-review':
                        # Pin the explicit checklist beside the new review, never invent one.
                        checklist_bytes = checklist.read_bytes()
                        (output / 'BAGO_CHECKLIST_DECLARADO.json').write_bytes(checklist_bytes)
                        command += ['--checklist', str(output / 'BAGO_CHECKLIST_DECLARADO.json'),
                                    '--reviewer', args.reviewer, '--pages', args.pages,
                                    '--verdict', args.verdict, '--note', args.note]
                        result['checklist_sha256'] = digest(checklist_bytes)
                elif inputs:
                    command += ['--input', str(inputs)]
                if op == 'test':
                    output.mkdir(parents=True, exist_ok=False)
                rc, stdout, stderr = _process(command, tmp, timeout)
                result['returncode'] = rc
                result['status'] = 'PASS' if rc == 0 else 'INCONCLUSIVE' if rc == 3 else 'FAIL'
                if op in ('doctor', 'preflight', 'record-review', 'validate-review', 'close'):
                    try:
                        detail = strict_json(stdout)
                    except ValueError:
                        detail = {'error': 'Child output is not a valid JSON result'}
                        result['status'] = 'FAIL'
                    result['result'] = detail
                if op == 'build':
                    run = read_json(output / 'RUN.json') if (output / 'RUN.json').is_file() else {}
                    state = run.get('status', 'NOT_GENERATED')
                    result.update(pipeline_status=state, clean_mode=args.clean_mode,
                                  all_page_previews_required=True,
                                  document_release='DRAFT_REQUIRES_VISUAL_REVIEW',
                                  pdf=run.get('pdf'), pdf_sha256=run.get('pdf_sha256'))
                    if rc == 0 and state in ('AUTOMATIC_CHECKS_PASSED', 'GENERATED_WITH_LIMITATIONS'):
                        result['generation_verification'] = _validate_generation(output)
                    result['status'] = ('PASS' if rc == 0 and state == 'AUTOMATIC_CHECKS_PASSED'
                                        else 'INCONCLUSIVE' if rc == 0 and state == 'GENERATED_WITH_LIMITATIONS'
                                        else 'FAIL')
                if op in ('record-review', 'validate-review'):
                    detail = result['result']
                    eligible = detail.get('eligible_for_final_delivery') is True
                    visual = detail.get('VISUAL_REVIEW', detail.get('result', 'NOT_RUN'))
                    result['visual_review'] = visual
                    if rc == 0 and eligible and (op == 'record-review' or detail.get('status') == 'VALID'):
                        result.update(status='PASS', document_release='REVIEW_VALIDATED_NOT_CLOSED')
                    elif isinstance(detail, dict) and (detail.get('schema') == 'ialp.visual_review.v1' or detail.get('status') == 'VALID'):
                        result.update(status='INCONCLUSIVE', document_release='BLOCKED_BY_REVIEW')
                if op == 'close':
                    if rc == 0 and result['result'].get('status') == 'FINAL_REVIEWED':
                        delivery = read_json(output / 'ENTREGA.json')
                        package = _file(Path(result['result']['package']))
                        if (not package.is_relative_to(output) or _file_digest(package) != result['result'].get('sha256')
                                or delivery.get('status') != 'FINAL_REVIEWED' or delivery.get('VISUAL_REVIEW') != 'PASS'):
                            raise ValueError('closure claim does not match the actual delivery evidence')
                        result.update(status='PASS', visual_review='PASS', document_release='FINAL_REVIEWED')
                    else:
                        result.update(status='FAIL', document_release='CLOSURE_BLOCKED')
                if op == 'test':
                    result['claim'] = 'Upstream automated tests, including mocks; not production visual approval'
            if source is not None:
                after = _file_digest(source)
                result['source_sha256_after'] = after
                result['source_unchanged'] = after == source_before
                if after != source_before:
                    result.update(status='FAIL', error='source changed during operation', document_release='NOT_APPROVED')
                if op == 'build' and output.exists():
                    original = output / (source.stem + '_ORIGINAL.md')
                    if not original.is_file() or _file_digest(original) != source_before:
                        result.update(status='FAIL', error='captured source does not match the requested bytes')
            if inputs is not None:
                result['input_unchanged'] = _tree(inputs) == input_inventory
                if not result['input_unchanged']:
                    result.update(status='FAIL', error='input evidence changed during operation', document_release='NOT_APPROVED')
        except (OSError, ValueError, KeyError, TypeError, TimeoutError, subprocess.SubprocessError) as exc:
            result.update(status='FAIL', error=str(exc), document_release='NOT_APPROVED')
    result['finished_at'] = datetime.now(timezone.utc).isoformat()
    result['stdout_tail'] = stdout[-5000:]
    result['stderr_tail'] = stderr[-3000:]
    if output is not None:
        # The caller authorized this new output even on failure; preserve diagnostics.
        if not output.exists():
            output.mkdir(parents=True, exist_ok=False)
        (output / 'BAGO_PIPELINE_STDOUT.log').write_text(stdout, encoding='utf-8')
        (output / 'BAGO_PIPELINE_STDERR.log').write_text(stderr, encoding='utf-8')
        result['output'] = str(output)
        result['receipt'] = str(output / 'BAGO_EDITORIAL_RECEIPT.json')
        write_new_json(output / 'BAGO_EDITORIAL_RECEIPT.json', result)
    return result
