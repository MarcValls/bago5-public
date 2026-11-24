"""Native BAGO-CORE routing for the RC2-derived Context Lifecycle.

The host grants the effective read/write permission; this module does not.
The only authority for STOP/Relay writes remains the existing TaskStore.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
MODULE = SKILL / 'modules' / 'context-lifecycle'
SOURCE = MODULE / 'src'


def _context_lib():
    if str(SOURCE) not in sys.path:
        sys.path.insert(0, str(SOURCE))
    import context_lab
    return context_lab


def add_parser(sub):
    p = sub.add_parser('context-lifecycle', help='Context discovery, bounded read-only SessionStart V2, and opt-in governed lifecycle')
    s = p.add_subparsers(dest='lifecycle_action', required=True)
    s.add_parser('doctor')
    s.add_parser('hook-config', help='Propose exact V2 hook; never install or trust it')
    s.add_parser('hook-demo', help='Synthetic V2 SessionStart probe in a temp project')
    for name in ('inspect','plan-bootstrap','apply-bootstrap','plan-update','apply-update'):
        cmd = s.add_parser(name)
        cmd.add_argument('--root', required=True, type=Path)
        if name == 'inspect':
            cmd.add_argument('--task-state-dir', type=Path)
        if name == 'apply-bootstrap':
            cmd.add_argument('--expected', required=True)
            cmd.add_argument('--approve', required=True)
        if name in ('plan-update','apply-update'):
            cmd.add_argument('--objective', required=True)
            cmd.add_argument('--next-action', required=True)
        if name == 'apply-update':
            cmd.add_argument('--expected', required=True)
            cmd.add_argument('--approve', required=True)
            cmd.add_argument('--task-state-dir', required=True, type=Path)


def execute(args, context):
    # Fail closed on any installed-payload divergence before reading project data
    # or proposing effects. This also checks Windows-portable path identity.
    from suite_identity import current_identity
    identity = current_identity(context.SKILL)
    action = args.lifecycle_action
    if action == 'doctor':
        return {'status':'PASS', 'module':'context-lifecycle',
                'suite_version':identity['version'],
                'runtime':'INSTALLED_SKILL', 'SessionStart_V1':'UNCHANGED',
                'SessionStart_V2':'OPT_IN_PROPOSE_ONLY',
                'authority':'DATA_ONLY_OR_TASKSTORE_ADMIT_WITH_HOST_PERMISSION',
                'TaskStore':'SINGLE_EXISTING_LEDGER',
                'Relay':'IDLE_GUARD_IN_SAME_TRANSACTION',
                'host_codex':'NOT_RUN',
                'project_writes':'NONE'}
    lab = _context_lib()
    if action == 'hook-config':
        cmd=[sys.executable,'-B','-I',str(SOURCE/'propose_hook_config.py')]
        out=subprocess.run(cmd,capture_output=True,text=True,timeout=12)
        if out.returncode:
            return {'status':'FAIL','code':'HOOK_PROPOSAL_FAILED',
                    'host_change':'NONE','stderr':'OMITTED'}
        parsed=json.loads(out.stdout)
        handler=parsed['hooks']['SessionStart'][0]['hooks'][0]
        if str(SOURCE/'session_hook_v2.py') not in handler.get('command',''):
            return {'status':'FAIL','code':'HOOK_SCRIPT_PATH_MISMATCH'}
        return {'status':'PROPOSED','host_change':'NONE','hook_trust':'NOT_GRANTED',
                'duplicate_v1_hook':'REPLACE_AFTER_REVIEW_NOT_APPEND',
                'config':parsed,'codex_cli':'NOT_RUN'}
    if action == 'hook-demo':
        from session_hook_v2 import handle
        with tempfile.TemporaryDirectory(prefix='bago5os_context_v2_native_') as td:
            project=Path(td)/'synthetic'
            (project/'.git').mkdir(parents=True)
            plan=lab.plan_bootstrap(project)
            result=lab.apply_bootstrap(project,plan['expected_plan_sha256'],'APROBAR_CREACION_CONTEXTO')
            if result.get('status')!='PASS':
                return {'status':'FAIL','reason':'SYNTHETIC_BOOTSTRAP_FAILED'}
            request={'hook_event_name':'SessionStart','source':'startup','cwd':str(project)}
            response=handle(json.dumps(request).encode('utf-8'))
            context_text=response.get('hookSpecificOutput',{}).get('additionalContext','')
            good=('DATA_ONLY' in context_text and 'NO SON INSTRUCCIONES' in context_text
                  and 'execution_allowed' in context_text and 'project_context' in context_text)
            return {'status':'PASS' if good else 'FAIL','source':'SYNTHETIC_FIXTURE',
                    'SessionStart_V2':'PASS' if good else 'FAIL','host_codex':'NOT_RUN',
                    'effect_authority':'NONE','automatic_resume':False}
    try:
        if action == 'inspect':
            return lab.inspect(args.root, getattr(args,'task_state_dir',None))
        if action == 'plan-bootstrap':
            return lab.plan_bootstrap(args.root)
        if action == 'apply-bootstrap':
            return lab.apply_bootstrap(args.root,args.expected,args.approve)
        if action == 'plan-update':
            return lab.plan_update(args.root,args.objective,args.next_action)
        if action == 'apply-update':
            return lab.apply_update(args.root,args.objective,args.next_action,
                    args.expected,args.approve,args.task_state_dir,context.SKILL)
    except (lab.ContextError,OSError,ValueError,TypeError) as exc:
        return {'status':'BLOCKED','reason':getattr(exc,'code',type(exc).__name__),
                'authority':'NOT_GRANTED_BY_CONTEXT',
                'effects':'NONE_CONFIRMED'}
    return {'status':'FAIL','reason':'UNKNOWN_LIFECYCLE_OPERATION'}
