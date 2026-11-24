#!/usr/bin/env python3
"""Print, NEVER INSTALL, one suggested SessionStart hook; requires Codex trust review."""
import json
from pathlib import Path
import shlex
import shutil
import sys

script=Path(__file__).resolve().parent/'session_hook_v2.py'
if sys.platform=='win32':
    if any(ch in str(script) for ch in '$`%!"\r\n\0'):
        raise SystemExit('ERROR: Put package in path without shell interpolation characters.')
    executable='py -3' if shutil.which('py') else 'python'
    cmd=f'{executable} -B -I "{script}"'
    handler={'type':'command','command':cmd,'commandWindows':cmd}
else:
    cmd=' '.join(shlex.quote(x) for x in (sys.executable,'-B','-I',str(script)))
    handler={'type':'command','command':cmd}
handler.update({'timeout':8,'additionalContextLimit':6500,
                'statusMessage':'BAGO5os: contexto estructurado NO CONFIABLE (solo lectura)'})
print(json.dumps({'status':'PROPOSED_NOT_INSTALLED',
    'warning':'Replace existing SessionStart after review; do not add duplicate hooks. /hooks trust is user-only.',
    'hooks':{'SessionStart':[{'matcher':'^(startup|resume|clear|compact|fork)$',
                             'hooks':[handler]}]}},ensure_ascii=False,indent=2))
