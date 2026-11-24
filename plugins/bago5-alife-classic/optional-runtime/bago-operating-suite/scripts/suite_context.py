"""Read-only SessionStart module adapter; makes no project-local or host configuration writes."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

COMPANION=Path(__file__).resolve().parents[1]/'modules/session-context/companion'


def add_parser(sub):
    p=sub.add_parser('session-context',help='SessionStart inventory / proposed Codex hook configuration')
    p.add_argument('operation',choices=('doctor','config','demo'))


def execute(args,context):
    from suite_identity import current_identity
    current_identity(context.SKILL)
    if args.operation=='doctor':
        return {'status':'PASS','module':'session-context','mode':'READ_ONLY',
                'companion':str(COMPANION),'source_files':20,
                'host_event':'NOT_RUN','windows':'NOT_RUN',
                'approval':'NOT_GRANTED','effect_authority':'HOST_ONLY'}
    script=COMPANION/'scripts'/('print_cli_config.py' if args.operation=='config' else 'demo.py')
    try:
        p=subprocess.run([sys.executable,'-B','-I',str(script)],capture_output=True,
                         text=True,timeout=35,check=False)
        if p.returncode:
            return {'status':'FAIL','operation':args.operation,'returncode':p.returncode,
                    'diagnostic':'Companion command failed (stderr omitted)'}
        parsed=json.loads(p.stdout)
        if args.operation=='config':
            return {'status':'PROPOSED','mode':'NO_HOST_WRITE','config':parsed,
                    'next':'Review manually in project .codex/hooks.json; trust via Codex /hooks',
                    'codex_cli':'NOT_RUN'}
        return {'status':'PASS' if parsed.get('result')=='PASS' else 'FAIL',
                'operation':'SYNTHETIC_DEMO','demonstration':parsed,'codex_cli':'NOT_RUN'}
    except (OSError,subprocess.SubprocessError,ValueError,TypeError) as exc:
        return {'status':'FAIL','operation':args.operation,
                'diagnostic':type(exc).__name__}
