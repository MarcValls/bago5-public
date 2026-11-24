#!/usr/bin/env python3
"""BAGO5os Context Lifecycle LAB-RC1 (stdlib only).

Experimental, opt-in context management. NEVER a permission issuer or automatic
Codex hook installer. The 1.4.6 SessionStart companion remains byte-for-byte intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from datetime import datetime, timezone
from urllib.parse import quote

HERE = Path(__file__).resolve().parents[1]
DEFAULT_PATH = HERE / 'assets' / 'project-context-structure.v1.json'
DEFAULT_SHA = '5c87880f41e39c1b5605c0c3e65ad1ff80e69c2209894c64b0a978129aaed471'
SUITE_CONTEXT_DIR = '.bago_skill'
STRUCTURE_REL = SUITE_CONTEXT_DIR + '/CONTEXT_STRUCTURE.json'
ARTIFACT_IDS = ('project_context', 'project_state', 'active_handoff')
MAX_FILE = 1_000_000
MAX_ANCESTORS = 8
MAX_VIEW = 6500
MAX_HISTORY = 20
MARK_BEGIN = '<!-- BAGO5os CONTEXT-LIFECYCLE BEGIN (proposed; not authorization) -->'
MARK_END = '<!-- BAGO5os CONTEXT-LIFECYCLE END -->'
CODE = re.compile(r'^[a-zA-Z0-9_.-]{1,100}$')


class ContextError(ValueError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ContextError('DUPLICATE_JSON_KEY')
            result[k] = v
        return result

    def no_constant(_):
        raise ContextError('NONFINITE_JSON')

    try:
        return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=no_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
        if isinstance(exc, ContextError):
            raise
        raise ContextError('INVALID_JSON') from None


def no_links(path: Path):
    # Windows reparse points include junctions; reject rather than traverse.
    for part in (*reversed(path.parents), path):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ContextError('LINK_OR_REPARSE_POINT')


def read_regular(path: Path, limit: int = MAX_FILE) -> bytes:
    no_links(path)
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise ContextError('NOT_REGULAR_OR_OVERSIZE')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    flags |= getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode):
            raise ContextError('NOT_REGULAR_FILE')
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ContextError('FILE_TOO_LARGE')
    return raw


def safe_path(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or len(rel) > 512 or '\\' in rel:
        raise ContextError('INVALID_PATH')
    parts = rel.split('/')
    reserved = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{s}{i}' for s in ('COM','LPT') for i in range(1,10)}
    for item in parts:
        if item in ('', '.', '..') or item.endswith(('.', ' ')) or any(x in item for x in ':<>"|?*'):
            raise ContextError('INVALID_PATH')
        if any(ord(ch) < 32 or ord(ch) == 127 for ch in item) or item.split('.')[0].upper() in reserved:
            raise ContextError('INVALID_PATH')
    result = root.joinpath(*parts)
    no_links(result)
    return result


def default_structure() -> dict:
    raw = read_regular(DEFAULT_PATH, 64_000)
    if digest(raw) != DEFAULT_SHA:
        raise ContextError('BUNDLED_STRUCTURE_CHANGED')
    return strict_json(raw)


def compatible(local: object, default: dict) -> list[dict]:
    if not isinstance(local, dict):
        raise ContextError('STRUCTURE_NOT_OBJECT')
    for key in ('schema','version','purpose','policy'):
        if type(local.get(key)) is not type(default[key]) or local[key] != default[key]:
            raise ContextError('UNSUPPORTED_STRUCTURE')
    if set(local) != set(default):
        raise ContextError('UNSUPPORTED_STRUCTURE_FIELDS')
    if not isinstance(local.get('extensions'), dict):
        raise ContextError('INVALID_STRUCTURE_EXTENSIONS')
    rows = local.get('artifacts')
    if not isinstance(rows, list) or len(rows) != 3:
        raise ContextError('INVALID_ARTIFACT_SET')
    by_id = {r['id']: r for r in default['artifacts']}
    ids, portable_paths = set(), {STRUCTURE_REL.casefold()}
    for row in rows:
        if not isinstance(row, dict) or set(row) != set(default['artifacts'][0]):
            raise ContextError('INVALID_ARTIFACT_SHAPE')
        name = row.get('id')
        if not isinstance(name, str) or name not in by_id or name in ids:
            raise ContextError('INVALID_ARTIFACT_ID')
        if type(row['enabled']) is not bool:
            raise ContextError('INVALID_ENABLED')
        for key in ('format','purpose','template'):
            if type(row[key]) is not type(by_id[name][key]) or row[key] != by_id[name][key]:
                raise ContextError('GOVERNED_ARTIFACT_CHANGED')
        rel = row.get('path')
        if not isinstance(rel, str) or rel.casefold() in portable_paths:
            raise ContextError('DUPLICATE_PATH')
        # This is Suite-owned context, not the .bago canon of ADL/BAGO.
        # Custom locations remain possible only INSIDE the Suite's own directory.
        if not rel.startswith(SUITE_CONTEXT_DIR + '/'):
            raise ContextError('CONTEXT_PATH_OUTSIDE_SUITE_DIRECTORY')
        ids.add(name); portable_paths.add(rel.casefold())
    if ids != set(ARTIFACT_IDS):
        raise ContextError('INVALID_ARTIFACT_SET')
    return rows


def _cwd(raw: str | Path) -> Path:
    if not isinstance(raw, (str, Path)) or not str(raw) or len(str(raw)) > 4096 or '\0' in str(raw):
        raise ContextError('INVALID_CWD')
    p = Path(raw)
    if not p.is_absolute():
        raise ContextError('CWD_NOT_ABSOLUTE')
    no_links(p)
    if not p.is_dir():
        raise ContextError('CWD_NOT_DIRECTORY')
    return p.absolute()


def find_root(cwd: str | Path):
    """Nearest same-project structure; a .git boundary stops parent discovery."""
    p = _cwd(cwd)
    for distance in range(MAX_ANCESTORS + 1):
        no_links(p)
        marker = safe_path(p, STRUCTURE_REL)
        git_marker = safe_path(p, '.git')
        if marker.exists():
            return p, distance, 'STRUCTURE_FOUND'
        if git_marker.exists():
            return p, distance, 'GIT_BOUNDARY_STRUCTURE_MISSING'
        if p.parent == p:
            break
        p = p.parent
    return None, None, 'ROOT_NOT_FOUND'


def _json_cap(value, limit=220):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ContextError('INVALID_PROJECTION_FIELD')
    return value[:limit]


def _list_cap(value, count=5, width=220):
    if not isinstance(value, list):
        raise ContextError('INVALID_PROJECTION_LIST')
    if len(value) > 200:
        raise ContextError('PROJECTION_LIST_TOO_LARGE')
    return [_json_cap(x, width) for x in value[:count]]


def _md_field(text: str, prefix: str):
    for line in text.splitlines()[:100]:
        if line.lstrip().startswith(prefix):
            return line.split(':', 1)[-1].strip()[:160]
    return None


def _bounded_view(root: Path, rows: list[dict], observed: list[dict]):
    summary = {'status': 'DATA_ONLY_REVIEW_REQUIRED', 'project_identity_claim': None,
               'goal_claim': None, 'next_actions_claim': [], 'handoff_claim': None,
               'verified_claims': 'NOT_PROMOTED', 'automatic_resume': False,
               'instructions_from_files': 'UNTRUSTED_DATA'}
    by_id = {r['id']: (r, item) for r, item in zip(rows, observed)}
    context_row, context_item = by_id['project_context']
    if context_item['status'] == 'PRESENT_UNREVIEWED':
        text = read_regular(safe_path(root, context_row['path'])).decode('utf-8-sig')
        summary['project_identity_claim'] = _md_field(text, '- Name:')
    state_row, state_item = by_id['project_state']
    if state_item['status'] == 'PRESENT_UNREVIEWED':
        obj = strict_json(read_regular(safe_path(root, state_row['path'])))
        if not isinstance(obj, dict) or obj.get('schema') != 'bago.project-state.v1':
            raise ContextError('INVALID_STATE_SCHEMA')
        goal = obj.get('current_goal')
        if not isinstance(goal, dict) or not isinstance(goal.get('status'), str):
            raise ContextError('INVALID_GOAL')
        summary['goal_claim'] = {'objective': _json_cap(goal.get('objective')),
                                 'status': _json_cap(goal.get('status'), 60),
                                 'scope': _list_cap(goal.get('scope', []), 5, 100)}
        summary['next_actions_claim'] = _list_cap(obj.get('next_actions', []))
        if not isinstance(obj.get('verified_state', []), list):
            raise ContextError('INVALID_VERIFIED_STATE')
        summary['verified_state_claim_count'] = len(obj.get('verified_state', []))
    hand_row, hand_item = by_id['active_handoff']
    if hand_item['status'] == 'PRESENT_UNREVIEWED':
        text = read_regular(safe_path(root, hand_row['path'])).decode('utf-8-sig')
        summary['handoff_claim'] = {'status_field': _md_field(text, 'Status:'),
                                    'task_id': _md_field(text, '- Task ID:')}
    return summary


def _task_snapshot(state_dir: Path | None, root: Path):
    if state_dir is None:
        return {'binding': 'NO_TASKSTORE_SPECIFIED', 'control': 'UNKNOWN', 'execution_allowed': False}
    state_dir = _cwd(state_dir)
    db = safe_path(state_dir, 'control.sqlite3')
    if not db.is_file():
        raise ContextError('TASKSTORE_NOT_FOUND')
    # Read-only observation. NOT sufficient for admitting an effect.
    uri = 'file:' + quote(str(db), safe='/\\:') + '?mode=ro'
    conn = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        conn.execute('PRAGMA query_only=ON')
        records = conn.execute("SELECT key,value FROM meta WHERE key IN ('schema','workspace','control','closed','plan')").fetchall()
    finally:
        conn.close()
    fields = {k: strict_json(v.encode('utf-8')) for k, v in records}
    if fields.get('schema') != 'bago.suite.task.control.v1':
        raise ContextError('UNSUPPORTED_TASKSTORE')
    workspace = fields.get('workspace')
    if not isinstance(workspace, str) or not os.path.samefile(_cwd(workspace), _cwd(root)):
        raise ContextError('TASKSTORE_WORKSPACE_MISMATCH')
    plan = fields.get('plan')
    if not isinstance(plan, dict) or not CODE.fullmatch(str(plan.get('mission_id', ''))):
        raise ContextError('INVALID_TASKSTORE_PLAN')
    control = fields.get('control')
    if control not in {'ACTIVE', 'STOPPED'}:
        raise ContextError('INVALID_TASKSTORE_CONTROL')
    return {'binding': 'READ_OBSERVATION_ONLY', 'control': control,
            'task_status': 'CLOSED' if fields.get('closed') else 'OPEN',
            'mission_id': plan['mission_id'], 'execution_allowed': False}


def inspect(cwd: str | Path, task_state_dir: Path | None = None) -> dict:
    root, distance, reason = find_root(cwd)
    result = {'schema': 'bago.context-lifecycle.observation.v0.1',
              'status': 'ROOT_UNCONFIRMED', 'authority': 'DATA_ONLY',
              'root_binding': 'CANDIDATE_NOT_AUTHORIZATION', 'root_reason': reason,
              'walk_up': distance, 'artifacts': [], 'semantic_projection': None}
    if root is None:
        result['taskstore'] = {'binding': 'NO_ROOT', 'execution_allowed': False}
        return result
    result['root'] = str(root)
    result['taskstore'] = _task_snapshot(task_state_dir, root)
    if reason != 'STRUCTURE_FOUND':
        return result
    marker = safe_path(root, STRUCTURE_REL)
    raw = read_regular(marker, 64_000)
    local = strict_json(raw)
    rows = compatible(local, default_structure())
    entries=[]
    # Fail closed on *all* invalid paths before reading any artifact.
    paths = [safe_path(root, row['path']) for row in rows]
    for row, path in zip(rows, paths):
        item={'id':row['id'],'path':row['path'],'enabled':row['enabled']}
        if not row['enabled']:
            item['status']='DISABLED'
        elif not path.exists():
            item['status']='MISSING'
        else:
            blob = read_regular(path)
            try:
                blob.decode('utf-8-sig')
            except UnicodeError:
                raise ContextError('INVALID_UTF8') from None
            if row['format'] == 'json':
                parsed = strict_json(blob)
                if not isinstance(parsed, dict):
                    raise ContextError('CONTEXT_JSON_NOT_OBJECT')
            item.update({'status':'PRESENT_UNREVIEWED','bytes':len(blob),'sha256':digest(blob)})
        entries.append(item)
    result['artifacts']=entries
    result['structure_sha256']=digest(raw)
    result['status']='REVIEW_REQUIRED' if any(x['status']=='PRESENT_UNREVIEWED' for x in entries) else 'CONTEXT_MISSING'
    try:
        result['semantic_projection']=_bounded_view(root, rows, entries)
    except (ContextError, UnicodeError):
        result['semantic_projection']={'status':'INSPECTION_BLOCKED_BAD_SEMANTICS', 'authority':'DATA_ONLY'}
        result['status']='SEMANTIC_REVIEW_BLOCKED'
    scope={'root':str(root),'structure_sha256':result['structure_sha256'],
           'artifacts':entries,'root_reason':reason}
    result['snapshot_sha256']=digest(canonical(scope))
    return result


def _bootstrap_entries(root: Path):
    default=default_structure()
    marker=safe_path(root,STRUCTURE_REL)
    if marker.is_file():
        structure_raw=read_regular(marker,64_000)
        structure=strict_json(structure_raw)
    else:
        structure_raw=read_regular(DEFAULT_PATH,64_000)
        structure=default
    rows=compatible(structure,default)
    expected=[(STRUCTURE_REL,structure_raw)]
    for row in rows:
        if not row['enabled']:
            continue
        if row['format']=='json':
            data=json.dumps(row['template'],ensure_ascii=False,indent=2).encode('utf-8')+b'\n'
        else:
            data=row['template'].encode('utf-8')
        expected.append((row['path'],data))
    for rel,_ in expected:
        safe_path(root,rel)
    return expected


def plan_bootstrap(root: Path) -> dict:
    root=_cwd(root)
    structure=safe_path(root,STRUCTURE_REL)
    if not (safe_path(root,'.git').exists() or structure.is_file()):
        raise ContextError('EXPLICIT_PROJECT_MARKER_REQUIRED')
    expected=_bootstrap_entries(root)
    if structure.is_file():
        compatible(strict_json(read_regular(structure,64_000)),default_structure())
    files=[]
    for rel,data in expected:
        p=safe_path(root,rel)
        status='ALREADY_PRESENT_UNCHANGED' if p.exists() else 'CREATE_ONLY'
        if status=='ALREADY_PRESENT_UNCHANGED':
            read_regular(p)
        files.append({'path':rel,'action':status,'expected_sha256':digest(data),
                      'existing_sha256':digest(read_regular(p)) if p.exists() else None})
    canonical_adl_present = safe_path(root, '.bago/INDEX.md').exists()
    legacy_lifecycle_present = safe_path(root, '.bago/CONTEXT_STRUCTURE.json').exists()
    current={'root':str(root),'files':files}
    return {'schema':'bago.context-lifecycle.bootstrap-plan.v0.1','status':'PROPOSED',
            'effect_authority':'USER_EXPLICIT_APPROVAL_REQUIRED', 'root':str(root),
            'expected_plan_sha256':digest(canonical(current)), 'files':files,
            'existing_files_overwritten':0, 'approval':'NOT_GRANTED',
            'other_context_authorities': {'.bago/INDEX.md': 'PRESENT_UNREAD' if canonical_adl_present else 'NOT_FOUND',
                                          '.bago/CONTEXT_STRUCTURE.json': 'PRESENT_UNREAD' if legacy_lifecycle_present else 'NOT_FOUND'},
            'no_automatic_migration':True, 'suite_context_root':SUITE_CONTEXT_DIR}


def _create_exclusive(path: Path, contents: bytes):
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    no_links(path.parent)
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0)
    fd=os.open(path,flags,0o600)
    with os.fdopen(fd,'wb') as output:
        output.write(contents)
        output.flush();os.fsync(output.fileno())


def apply_bootstrap(root: Path, expected_plan_sha256: str, approval: str):
    if approval!='APROBAR_CREACION_CONTEXTO':
        raise ContextError('EXPLICIT_APPROVAL_REQUIRED')
    plan=plan_bootstrap(root)
    if plan['expected_plan_sha256']!=expected_plan_sha256:
        raise ContextError('STALE_BOOTSTRAP_PLAN')
    root=Path(plan['root'])
    created=[]
    try:
        for rel, data in _bootstrap_entries(root):
            target=safe_path(root,rel)
            if target.exists():
                # Existing data must remain byte-identical to the reviewed plan.
                continue
            _create_exclusive(target,data)
            created.append(rel)
        view=inspect(root)
        return {'status':'PASS','mode':'EXPLICIT_LOCAL_BOOTSTRAP', 'created':created,
                'unmodified_existing':len(plan['files'])-len(created),'snapshot_sha256':view.get('snapshot_sha256'),
                'host_permission':'NOT_INFERRED', 'project_verified':'NO'}
    except (OSError, ContextError) as exc:
        return {'status':'PARTIAL_UNCERTAIN','created':created,'error':getattr(exc,'code',type(exc).__name__),
                'note':'No se revierte automaticamente ni se afirma exito. Revisar antes de continuar.'}


def _user_text(value: str, maxlen=300):
    if not isinstance(value,str) or not value.strip() or len(value)>maxlen or any(ord(c)<32 or ord(c)==127 for c in value):
        raise ContextError('INVALID_USER_TEXT')
    return value.strip()


def _current_rows(root: Path):
    obj=strict_json(read_regular(safe_path(root, STRUCTURE_REL),64000))
    rows=compatible(obj,default_structure())
    by_id={r['id']:r for r in rows}
    if not all(by_id[artifact_id]['enabled'] for artifact_id in ARTIFACT_IDS):
        raise ContextError('REQUIRED_ARTIFACT_DISABLED')
    return by_id


def _patched_state(old: dict, objective: str, next_action: str) -> dict:
    if not isinstance(old,dict) or old.get('schema')!='bago.project-state.v1':
        raise ContextError('UNSUPPORTED_STATE_SCHEMA')
    if not isinstance(old.get('current_goal'),dict) or not isinstance(old.get('extensions'),dict):
        raise ContextError('STATE_SHAPE_INCOMPATIBLE')
    if not isinstance(old.get('next_actions'),list) or not isinstance(old.get('verified_state'),list):
        raise ContextError('STATE_SHAPE_INCOMPATIBLE')
    # Deep copy; keep ALL unknown fields, verified entries, checks and user extensions.
    result=strict_json(canonical(old))
    ext=result['extensions']
    history=ext.get('context_lifecycle_history', [])
    if not isinstance(history,list) or len(history)>=MAX_HISTORY:
        raise ContextError('HISTORY_LIMIT_REVIEW_REQUIRED')
    history.append({'previous_goal_sha256':digest(canonical(result['current_goal'])),
                    'previous_next_actions_sha256':digest(canonical(result['next_actions'])),
                    'kind':'PROPOSED_GOAL_CHANGE'})
    ext['context_lifecycle_history']=history
    result['current_goal'].update({'objective':objective, 'scope':[], 'acceptance':[], 'status':'PROPOSED'})
    result['next_actions']=[next_action]
    result['updated_at']=datetime.now(timezone.utc).isoformat()
    result['lifecycle']='PROPOSED'
    # Never append to verified_state/checks or infer PASS.
    return result


def _handoff_text(before: str, objective: str, next_action: str):
    if MARK_BEGIN in before or MARK_END in before:
        if before.count(MARK_BEGIN)!=1 or before.count(MARK_END)!=1:
            raise ContextError('HANDOFF_MARKERS_CONFLICT')
        start=before.find(MARK_BEGIN);end=before.find(MARK_END,start)
        if end<start:
            raise ContextError('HANDOFF_MARKERS_CONFLICT')
        preserved=before[:start]+before[end+len(MARK_END):]
    else:
        preserved=before
    block=(f'\n\n{MARK_BEGIN}\n## Propuesta de continuidad BAGO5os (no autorizacion)\n'
           f'- Objetivo propuesto: {objective}\n- Siguiente accion propuesta: {next_action}\n'
           f'- Decision del usuario: revision requerida\n- Ejecucion y pruebas: NOT_RUN\n'
           f'- Reanudacion: NUNCA automatica; comprobar TaskStore y permisos del host\n{MARK_END}\n')
    return preserved.rstrip()+block


def plan_update(root: Path, objective: str, next_action: str):
    objective=_user_text(objective);next_action=_user_text(next_action)
    root=_cwd(root)
    found, distance,reason=find_root(root)
    if found!=root or reason!='STRUCTURE_FOUND':
        raise ContextError('CONFIRMED_EXPLICIT_ROOT_REQUIRED')
    view=inspect(root)
    if view['status']!='REVIEW_REQUIRED':
        raise ContextError('CONTEXT_UNAVAILABLE')
    if any(item['status'] != 'PRESENT_UNREVIEWED' for item in view['artifacts']):
        raise ContextError('CONTEXT_INCOMPLETE')
    rows=_current_rows(root)
    state=safe_path(root, rows['project_state']['path'])
    handoff=safe_path(root, rows['active_handoff']['path'])
    if not state.is_file() or not handoff.is_file():
        raise ContextError('CONTEXT_INCOMPLETE')
    obj=strict_json(read_regular(state))
    _patched_state(obj,objective,next_action)
    _handoff_text(read_regular(handoff).decode('utf-8-sig'),objective,next_action)
    return {'schema':'bago.context-lifecycle.update-plan.v0.1','status':'PROPOSED',
            'root':str(root),'snapshot_sha256':view['snapshot_sha256'],
            'operation':'SET_PROPOSED_GOAL_AND_HANDOFF', 'objective':objective,'next_action':next_action,
            'writes':[rows['project_state']['path'],rows['active_handoff']['path']],
            'requires':['TASKSTORE_ACTIVE','EXPLICIT_APPROVAL','UNCHANGED_SNAPSHOT','HOST_PERMISSION'],
            'verified_state_promotion':'FORBIDDEN','approval':'NOT_GRANTED'}


def _suite_store(root: Path, task_state_dir: Path, suite_skill: Path):
    # Caller explicitly authorizes the installed Suite code from a trusted path.
    suite_skill = _cwd(suite_skill)
    scripts = safe_path(suite_skill,'scripts')
    if not scripts.is_dir():
        raise ContextError('SUITE_SCRIPTS_NOT_FOUND')
    if str(scripts) not in sys.path:
        sys.path.insert(0,str(scripts))
    from suite_control import TaskStore
    from suite_identity import current_identity
    identity=current_identity(suite_skill)
    return TaskStore(task_state_dir,identity,lambda:current_identity(suite_skill))


def _atomic_replace(expected: Path, data: bytes):
    # One-file atomic replace (no all-files transaction). Expect snapshot checked by caller.
    no_links(expected)
    if not expected.is_file():
        raise ContextError('UPDATE_TARGET_MISSING')
    temp=expected.parent / ('.'+expected.name+'.bago-stage-'+os.urandom(6).hex())
    no_links(temp)
    try:
        fd=os.open(temp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_BINARY',0),0o600)
        with os.fdopen(fd,'wb') as h:
            h.write(data);h.flush();os.fsync(h.fileno())
        no_links(expected)
        os.replace(temp,expected)
    finally:
        if temp.exists():
            temp.unlink()


def apply_update(root:Path, objective:str, next_action:str, expected:str, approval:str,
                 task_state_dir:Path, suite_skill:Path):
    if approval!='APROBAR_ACTUALIZACION_CONTEXTO':
        raise ContextError('EXPLICIT_APPROVAL_REQUIRED')
    plan=plan_update(root,objective,next_action)
    if plan['snapshot_sha256']!=expected:
        raise ContextError('STALE_CONTEXT_SNAPSHOT')
    root=Path(plan['root']);store=_suite_store(root,task_state_dir,suite_skill)
    changed=[]
    try:
        with store.db() as conn:
            # This is the existing TaskStore ledger/STOP, NOT a second authority.
            conn.execute('BEGIN IMMEDIATE')
            meta=store._admit(conn,round_required=False)
            # Same TaskStore transaction and STOP authority; no second ledger.
            # Do not write while an owned subprocess or a Relay worker is live.
            if conn.execute("SELECT 1 FROM runs WHERE state='RUNNING'").fetchone():
                raise ContextError('TASK_CHILD_RUNNING')
            if conn.execute("SELECT 1 FROM assignments WHERE state='ASSIGNED'").fetchone():
                raise ContextError('TASK_ASSIGNMENT_ACTIVE')
            store.relay().idle(conn, meta)
            workspace=meta.get('workspace')
            if not isinstance(workspace,str) or not os.path.samefile(_cwd(workspace),_cwd(root)):
                raise ContextError('TASKSTORE_WORKSPACE_MISMATCH')
            again=inspect(root)
            if again.get('snapshot_sha256')!=expected:
                raise ContextError('STALE_CONTEXT_SNAPSHOT')
            rows=_current_rows(root)
            # TaskStore's candidate scope is immutable. Reject an update that
            # would invalidate the task's frozen candidate or artifact evidence.
            managed={rows['project_state']['path'].casefold(),
                     rows['active_handoff']['path'].casefold()}
            protected={p.casefold() for p in meta['plan']['scope']}
            for check in meta['plan']['checks']:
                protected.update(a['path'].casefold() for a in check['artifacts'])
            if managed & protected:
                raise ContextError('TASK_FROZEN_SCOPE_CONFLICT')
            sp=safe_path(root,rows['project_state']['path'])
            hp=safe_path(root,rows['active_handoff']['path'])
            before_state=strict_json(read_regular(sp))
            state_after=_patched_state(before_state,objective,next_action)
            before_handoff=read_regular(hp).decode('utf-8-sig')
            handoff_after=_handoff_text(before_handoff,objective,next_action)
            if len(canonical(state_after))>120_000 or len(handoff_after.encode('utf-8'))>120_000:
                raise ContextError('UPDATE_TOO_LARGE')
            _atomic_replace(sp,json.dumps(state_after,ensure_ascii=False,indent=2).encode('utf-8')+b'\n')
            changed.append(rows['project_state']['path'])
            _atomic_replace(hp,handoff_after.encode('utf-8'))
            changed.append(rows['active_handoff']['path'])
            after=inspect(root)
            store._event(conn,'CONTEXT_PROPOSAL_UPDATED',{'before_sha256':expected,
                'after_sha256':after['snapshot_sha256'],'artifacts':changed,
                'claims_verified':False,'host_permission':'NOT_ATTESTED_BY_LAB'})
            conn.commit()
        return {'status':'PASS','changed':changed,'snapshot_sha256':after['snapshot_sha256'],
                'control':'ACTIVE_AT_COMMIT','claims_verified':False,
                'permission':'USER_OPT_IN; HOST_AUTH_NOT_PROVEN','automatic_resume':False}
    except Exception as exc:
        # An error after one replacement can leave a partial update. Never report PASS.
        return {'status':'PARTIAL_UNCERTAIN' if changed else 'BLOCKED',
                'changed_before_error':changed,'error':getattr(exc,'code',type(exc).__name__),
                'warning':'Los archivos modificados no se revierten automaticamente; revisar diffs y recibos.'}


def cli(argv=None):
    p=argparse.ArgumentParser(description='BAGO5os Context Lifecycle LAB; NO cambia Codex ni instala hooks')
    p.add_argument('action',choices=('inspect','plan-bootstrap','apply-bootstrap','plan-update','apply-update'))
    p.add_argument('--root',required=True,type=Path,help='Ruta absoluta del proyecto. Nunca inferida para escrituras')
    p.add_argument('--task-state-dir',type=Path)
    p.add_argument('--suite-skill',type=Path)
    p.add_argument('--expected',default='')
    p.add_argument('--approve',default='')
    p.add_argument('--objective',default='')
    p.add_argument('--next-action',default='')
    args=p.parse_args(argv)
    try:
        if args.action=='inspect':
            result=inspect(args.root,args.task_state_dir)
        elif args.action=='plan-bootstrap':
            result=plan_bootstrap(args.root)
        elif args.action=='apply-bootstrap':
            result=apply_bootstrap(args.root,args.expected,args.approve)
        elif args.action=='plan-update':
            result=plan_update(args.root,args.objective,args.next_action)
        elif args.action=='apply-update':
            if not args.task_state_dir or not args.suite_skill:
                raise ContextError('TASKSTORE_AND_SUITE_REQUIRED')
            result=apply_update(args.root,args.objective,args.next_action,args.expected,args.approve,
                                args.task_state_dir,args.suite_skill)
        else:
            raise ContextError('ACTION_UNSUPPORTED')
    except (ContextError,OSError,ValueError,TypeError,sqlite3.Error) as exc:
        result={'status':'BLOCKED','error':getattr(exc,'code',type(exc).__name__),
                'effects':'NONE_CONFIRMED'}
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result.get('status') in {'PASS','PROPOSED','REVIEW_REQUIRED','CONTEXT_MISSING','ROOT_UNCONFIRMED','SEMANTIC_REVIEW_BLOCKED'} else 1


if __name__=='__main__':
    raise SystemExit(cli())
