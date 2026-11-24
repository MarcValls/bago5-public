"""Installed cognitive mission entry. Replay is regression, never new reasoning."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from suite_identity import current_identity
from suite_safety import reject_links, new_external_path, read_json, write_new_json


def add_parser(sub):
    p = sub.add_parser('cognitive', help='Integrated Session/Spiral mission and installed configuration acceptance')
    p.add_argument('operation', choices=['config-check', 'replay', 'init', 'cycle', 'consume', 'verify', 'close', 'status', 'stop', 'resume', 'deliver'])
    p.add_argument('--output', type=Path)
    p.add_argument('--work', type=Path)
    p.add_argument('--number', type=int, choices=[1, 2, 3])
    p.add_argument('--check')
    p.add_argument('--reason')
    p.add_argument('--request')
    p.add_argument('--content', type=Path)
    p.add_argument('--author')


def _external(path, skill):
    if path is None:
        raise ValueError('missing work/output path')
    reject_links(path)
    result = path.expanduser().resolve()
    if result.is_relative_to(skill) or skill.is_relative_to(result):
        raise ValueError('work/output overlaps installed payload')
    return result


def _run(command, timeout):
    return subprocess.run(command, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))


def execute(args, context):
    skill = context.SKILL.resolve()
    module = skill / 'modules/cognitive-mission'
    op = args.operation
    # STOP must remain available if installed bytes were damaged. It does not grant new work.
    identity = None if op == 'stop' else current_identity(skill)
    if op == 'config-check':
        output = _external(args.output, skill)
        output = new_external_path(output, (skill,))
        output.mkdir(parents=True, exist_ok=False)
        core = skill / 'runtime/BAGO-4.11.10/backend/.bago/core'
        evaluator = module / 'src/evaluate_project.py'
        command = [sys.executable, '-B', str(evaluator), '--project', str(core), '--suite', str(skill), '--installed']
        p = _run(command, 180)
        (output / 'stdout.log').write_text(p.stdout, encoding='utf-8')
        (output / 'stderr.log').write_text(p.stderr, encoding='utf-8')
        try:
            result = json.loads(p.stdout)
        except ValueError:
            result = {'all_passed': False, 'error': 'invalid evaluator result'}
        expected = hashlib.sha256((core / 'config_manager.py').read_bytes()).hexdigest()
        ok = (p.returncode == 0 and result.get('all_passed') is True
              and result.get('passed') == result.get('total') == 12
              and result.get('installed_source') is True
              and result.get('source_path') == str(core / 'config_manager.py')
              and result.get('source_sha256') == expected
              and current_identity(skill) == identity)
        write_new_json(output / 'ACCEPTANCE.json', result)
        receipt = {'schema': 'bago.suite.installed-config-acceptance.v1',
                   'status': 'PASS' if ok else 'FAIL', 'suite_identity': identity,
                   'command': command, 'returncode': p.returncode,
                   'evaluator_sha256': hashlib.sha256(evaluator.read_bytes()).hexdigest(),
                   'acceptance_sha256': hashlib.sha256((output / 'ACCEPTANCE.json').read_bytes()).hexdigest(),
                   'total': result.get('total', 0), 'passed': result.get('passed', 0),
                   'source_sha256': expected, 'inference_executed': False,
                   'scope': 'installed canonical ConfigManager and native SessionManager configuration consumer in isolated fresh processes'}
        write_new_json(output / 'RECEIPT.json', receipt)
        return receipt
    if op in {'replay', 'init'}:
        output = _external(args.output, skill)
        command = [sys.executable, '-B', str(module / ('replay_mission.py' if op == 'replay' else 'run_mission.py'))]
        if op == 'init':
            command += ['init']
        command += ['--output', str(output), '--skill', str(skill)]
        if op == 'init':
            command += ['--mode', 'live']
        work = output
    else:
        work = _external(args.work, skill)
        cfg = read_json(work / 'CONFIG.json')
        if Path(cfg['suite']).resolve() != skill:
            raise ValueError('mission belongs to another installation')
        if op != 'stop' and cfg['suite_identity'] != identity:
            raise ValueError('mission belongs to another candidate')
        if op == 'deliver':
            if not all([args.request, args.content, args.author]):
                raise ValueError('deliver requires request, content and author')
            command = [sys.executable, '-B', str(module / 'deliver_host_response.py'), '--work', str(work),
                       '--request', args.request, '--content', str(args.content), '--author', args.author]
        else:
            command = [sys.executable, '-B', str(module / 'run_mission.py'), op, '--work', str(work)]
            if op == 'cycle':
                if args.number is None:raise ValueError('cycle requires --number')
                command += ['--number', str(args.number)]
            if op == 'consume':
                if not args.check:raise ValueError('consume requires --check')
                command += ['--check', args.check]
            if op in {'stop','resume'}:
                if not args.reason:raise ValueError('stop/resume requires --reason')
                command += ['--reason', args.reason]
    p = _run(command, 1100 if op == 'replay' else 650)
    result = {'status': 'PASS' if p.returncode == 0 else 'FAIL', 'operation': op,
              'returncode': p.returncode, 'command': command, 'work': str(work),
              'suite_identity': identity, 'stdout_tail': p.stdout[-6000:], 'stderr_tail': p.stderr[-6000:]}
    if op == 'replay':
        report = work / 'evidence/REPLAY_RESULT.json'
        result['mode'] = 'REPLAY'; result['new_reasoning'] = False
        if not report.is_file() or read_json(report).get('status') != 'PASS':
            result['status'] = 'FAIL'
        result['report'] = str(report)
        result['scope'] = 'historical RC2 defect fixture; current installed cognitive runtime; not current product defect or new host reasoning'
    return result
