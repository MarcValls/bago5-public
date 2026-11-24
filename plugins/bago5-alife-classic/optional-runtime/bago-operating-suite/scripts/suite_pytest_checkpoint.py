"""Explicit, bounded facade for the opt-in BAGO pytest companion.

A host, user or governed task must initiate every action. This is neither an
agent scheduler nor a process-isolation or permissions boundary.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sqlite3
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from suite_safety import reject_links


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _external(path: Path, skill: Path, *, new: bool = False) -> Path:
    path = Path(path).expanduser()
    if ".." in path.parts:
        raise ValueError("output contains parent traversal")
    reject_links(path)
    target = path.resolve()
    base = skill.resolve(strict=True)
    if target == base or target.is_relative_to(base) or base.is_relative_to(target):
        raise ValueError("checkpoint/evidence/workspace must be separate from installed payload")
    if new and target.exists():
        raise ValueError("output must be new; existing evidence is preserved")
    return target


def _env(skill: Path) -> dict[str, str]:
    env = os.environ.copy()
    env['PYTHONPATH'] = os.pathsep.join(filter(None, (str(skill), env.get('PYTHONPATH'))))
    return env


def _result(record: dict, evidence_dir: Path | None, stdout: str, stderr: str) -> dict:
    if evidence_dir is None:
        record['stdout_tail'] = stdout[-1600:]
        record['stderr_tail'] = stderr[-1600:]
        return record
    evidence_dir.mkdir(parents=True, exist_ok=False)
    (evidence_dir / 'stdout.log').write_text(stdout, encoding='utf-8')
    (evidence_dir / 'stderr.log').write_text(stderr, encoding='utf-8')
    record['evidence_dir'] = str(evidence_dir)
    record['stdout_sha256'] = _sha((evidence_dir / 'stdout.log').read_bytes())
    record['stderr_sha256'] = _sha((evidence_dir / 'stderr.log').read_bytes())
    (evidence_dir / 'result.json').write_text(json.dumps(record, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return record


def add_parser(subparsers):
    parser = subparsers.add_parser('pytest-checkpoint', help='Opt-in pytest durable resume; no automatic launch')
    actions = parser.add_subparsers(dest='pytest_action', required=True)
    actions.add_parser('doctor', help='Dependency and installed binding check, no tests run')
    status = actions.add_parser('status', help='Read checkpoint ledger only')
    status.add_argument('--checkpoint', required=True, type=Path)
    demo = actions.add_parser('demo', help='Run the independent synthetic interruption/restart suite')
    demo.add_argument('--output', required=True, type=Path)
    for action_name in ('run', 'resume'):
        child = actions.add_parser(action_name, help='Explicit pytest invocation on provided workspace')
        child.add_argument('--workspace', required=True, type=Path)
        child.add_argument('--checkpoint', required=True, type=Path)
        child.add_argument('--context', default='', help='External fixture identity; caller maintains it')
        child.add_argument('--evidence', type=Path, help='New evidence directory outside the workspace')
        child.add_argument('pytest_args', nargs='*', help='Use -- before explicit pytest selectors/options')
    return parser


def execute(args, context):
    skill = context.SKILL
    from suite_identity import current_identity
    current_identity(skill)
    action = args.pytest_action
    if action == 'doctor':
        pytest_spec = importlib.util.find_spec('pytest')
        git = shutil.which('git')
        ok = pytest_spec is not None and git is not None
        return {'status': 'PASS' if ok else 'BLOCKED',
                'operation': 'PYTEST_CHECKPOINT_DOCTOR',
                'pytest_available': pytest_spec is not None, 'git_available': bool(git),
                'execution': 'NOT_RUN', 'workspace_integration': 'NOT_RUN',
                'scope': 'dependency presence and installed payload identity only'}
    if action == 'status':
        from pytest_checkpoint import _status
        state = _external(args.checkpoint, skill)
        if not state.is_file():
            raise ValueError('checkpoint is missing')
        return {'status': 'PASS', 'operation': 'READ_LEDGER',
                'checkpoint_record': _status(state), 'live_identity_recheck': 'NOT_RUN',
                'scope': 'recorded results only, not a new test run or authority receipt'}
    if action == 'demo':
        output = _external(args.output, skill, new=True)
        if not importlib.util.find_spec('pytest') or not shutil.which('git'):
            return {'status': 'BLOCKED', 'operation': 'PYTEST_CHECKPOINT_DEMO',
                    'reason': 'Python pytest and Git required', 'tests': 'NOT_RUN'}
        testfile = skill / 'modules/pytest-checkpoint/tests/test_pytest_checkpoint_companion.py'
        env = _env(skill)
        env['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
        cmd = [sys.executable, '-B', '-m', 'pytest', '-p', 'no:cacheprovider', '-q', str(testfile)]
        started = datetime.now(timezone.utc).isoformat()
        proc = subprocess.run(cmd, cwd=skill, env=env, capture_output=True,
                              text=True, encoding='utf-8', errors='replace', timeout=300)
        total_match = re.search(r'\b(\d+) passed\b', proc.stdout)
        passed = int(total_match.group(1)) if total_match else 0
        record = {'status': 'PASS' if proc.returncode == 0 and passed == 9 else 'FAIL',
                  'operation': 'PYTEST_CHECKPOINT_DEMO', 'candidate': 'installed-payload',
                  'tests_passed': passed, 'expected': 9, 'returncode': proc.returncode,
                  'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
                  'checks': 'synthetic interruption, resume, stale-code/args/context, teardown, skip, lock, collection',
                  'workspace_integration': 'NOT_RUN', 'windows': 'NOT_RUN',
                  'scope': 'self-contained subprocess fixtures; no ADL/BAGO5 host execution'}
        return _result(record, output, proc.stdout, proc.stderr)
    if action in {'run', 'resume'}:
        workspace = _external(args.workspace, skill)
        if not workspace.is_dir():
            raise ValueError('workspace must exist as a directory')
        state = _external(args.checkpoint, skill)
        evidence = _external(args.evidence, skill, new=True) if args.evidence else None
        if evidence and (evidence == workspace or evidence.is_relative_to(workspace)):
            raise ValueError('evidence must be outside workspace to avoid source identity changes')
        given = list(args.pytest_args)
        if given and given[0] == '--':
            given.pop(0)
        if not given or any(x.startswith('--bago-') for x in given):
            raise ValueError('provide explicit pytest selectors/options after --; plugin flags are managed by the Suite')
        state.parent.mkdir(parents=True, exist_ok=True)
        argv = [sys.executable, '-B', '-m', 'pytest', '-p', 'scripts.pytest_checkpoint',
                '--bago-checkpoint', str(state)]
        if args.context:
            argv.extend(['--bago-context', args.context])
        if action == 'resume':
            argv.append('--bago-resume')
        argv.extend(given)
        started = datetime.now(timezone.utc).isoformat()
        proc = subprocess.run(argv, cwd=workspace, env=_env(skill), capture_output=True,
                              text=True, encoding='utf-8', errors='replace')
        from pytest_checkpoint import _status
        try:
            progress = _status(state)
        except (ValueError, KeyError, OSError, sqlite3.Error) as exc:
            # A failed collection/invalid DB is not transformed into a valid PASS.
            progress = {'status': 'UNAVAILABLE', 'reason': type(exc).__name__ + ': ' + str(exc)}
        complete = progress.get('checkpoint_complete') is True
        outcome = 'PASS' if proc.returncode == 0 and complete else 'FAIL' if proc.returncode else 'INCONCLUSIVE'
        record = {'status': outcome, 'operation': 'PYTEST_CHECKPOINT_' + action.upper(),
                  'returncode': proc.returncode, 'started_at': started,
                  'finished_at': datetime.now(timezone.utc).isoformat(),
                  'workspace': str(workspace), 'checkpoint': str(state),
                  'argv_sha256': _sha(json.dumps(argv).encode()),
                  'checkpoint_record': progress, 'sandbox': 'NOT_PROVIDED',
                  'scope': 'only selected tests; no authority, exactly-once, or automatic rescheduling'}
        return _result(record, evidence, proc.stdout, proc.stderr)
    raise ValueError('unsupported pytest checkpoint action')
