#!/usr/bin/env python3
"""Opt-in GOALS + Codex bridge for the pinned, unmodified BAGO Suite 1.4.8.

No implicit task resume, subprocess execution, writes to GOALS documents, or host permissions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import sqlite3
import threading
from contextlib import closing, contextmanager

HERE = Path(__file__).resolve().parent
_GOAL_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}\Z')
_STATUSES = {'OPEN', 'ACTIVE', 'PAUSED', 'DONE', 'CANCELLED', 'DISCARDED'}
SCHEMA = 'bago.goals-codex.bridge.rc4-stop-recovery.v1'
from cancel_signal import CancelSignal

class BridgeError(ValueError):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _reject_links(path):
    for item in (Path(path), *Path(path).parents):
        if item.is_symlink() or getattr(item, 'is_junction', lambda: False)():
            raise BridgeError(f'Linked path rejected: {item}')


@contextmanager
def _ownership_lock(state_root, task_dir):
    if not _GOAL_ID.fullmatch(task_dir): raise BridgeError('Invalid ownership target')
    path=state_root/('.bridge-owner.'+task_dir+'.lock')
    _reject_links(path)
    handle=path.open('a+b')
    locked=False
    try:
        handle.seek(0,2)
        if handle.tell()==0: handle.write(b'0');handle.flush()
        handle.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            locked=True
        except OSError as exc:
            raise BridgeError('DISPATCHER_OWNS_TASKSTORE: wait for the existing owner to finish') from exc
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
        handle.close()


def _recovery_path(state_root, task_dir):
    if not _GOAL_ID.fullmatch(task_dir): raise BridgeError('Invalid recovery target')
    path = state_root / ('.bridge-stop-recovery.' + task_dir + '.json')
    _reject_links(path)
    return path


def _recovery_markers(state_root):
    markers = sorted([*state_root.glob('.bridge-stop-recovery.*.json'), *state_root.glob('.bridge-run.*.json')])
    for path in markers: _reject_links(path)
    return markers


def _mark_recovery(state_root, task_dir, reason):
    path = _recovery_path(state_root, task_dir)
    try:
        with path.open('x', encoding='utf-8') as handle:
            json.dump({'schema':'bago.bridge.stop-recovery.v1','task_dir':task_dir,
                       'reason':reason,'requires_explicit_task_resume':True}, handle)
    except FileExistsError:
        pass  # An existing latch is never weakened or replaced automatically.
    return str(path)


def _read_meta(store_path):
    db = Path(store_path) / 'control.sqlite3'
    _reject_links(db)
    if not db.is_file():
        raise BridgeError('TASKSTORE_MISSING')
    with closing(sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True, timeout=2)) as conn:
        values = dict(conn.execute("SELECT key,value FROM meta WHERE key IN ('workspace','plan')"))
    if set(values) != {'workspace','plan'}:
        raise BridgeError('TASKSTORE_METADATA_MISSING')
    return {k: json.loads(v) for k,v in values.items()}


def _same_workspace(store_path, workspace):
    actual = _read_meta(store_path)['workspace']
    if not isinstance(actual, str) or not os.path.samefile(actual, workspace):
        raise BridgeError('TASKSTORE_WORKSPACE_MISMATCH')


def _read_goal(path: Path) -> dict:
    _reject_links(path)
    if not path.is_file():
        raise BridgeError(f'GOAL is not a regular file: {path.name}')
    if path.stat().st_size > 300_000:
        raise BridgeError(f'GOAL file too large: {path.name}')
    data = path.read_bytes()
    value = json.loads(data)
    if not isinstance(value, dict) or set(value) != {'schema', 'goal_id', 'status', 'text', 'task_dir', 'check_id'}:
        raise BridgeError(f'Invalid GOAL document schema: {path.name}')
    if value['schema'] != 'bago.goals.document.v1':
        raise BridgeError(f'Unknown GOAL schema: {path.name}')
    if not isinstance(value['goal_id'], str) or not _GOAL_ID.fullmatch(value['goal_id']):
        raise BridgeError('Invalid goal_id')
    if value['status'] not in _STATUSES:
        raise BridgeError('Invalid documentary GOAL status')
    if not isinstance(value['text'], str) or not value['text'].strip() or len(value['text']) > 120_000:
        raise BridgeError('Missing/oversized GOAL text')
    for key in ('task_dir', 'check_id'):
        if not isinstance(value[key], str) or not _GOAL_ID.fullmatch(value[key]):
            raise BridgeError(f'Invalid {key}')
    return dict(value, document=str(path), document_sha256=_sha(data))


def _import_suite(suite: Path):
    if not suite.is_dir():
        raise BridgeError('Pinned unified Suite missing')
    scripts = suite / 'scripts'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from suite_identity import current_identity
    from suite_control import TaskStore
    identity = current_identity(suite)  # fail-closed: verify exact installed payload identity
    if (identity.get('release_id') != 'BAGO-SUITE-148-UNIFIED-CODEX-20261104'
            or identity.get('payload_files') != 601
            or identity.get('payload_sha256') != '60794235ba0febf81476bc12e3736493bae0d63812ba282db26e944b7c806f74'):
        raise BridgeError('Unexpected Suite identity; pinned unified 1.4.8 required')
    return TaskStore, identity


def _load_state(store_path: Path, TaskStore) -> dict:
    if store_path.is_symlink() or (store_path / 'control.sqlite3').is_symlink():
        raise BridgeError(f'Symlinked TaskStore rejected: {store_path}')
    try:
        return TaskStore(store_path, {}).status()  # read-only status, close SQLite immediately
    except Exception as exc:
        raise BridgeError(f'TaskStore unreadable {store_path.name}: {exc}') from exc


def inspect(workspace: Path, state_root: Path, suite: Path) -> dict:
    """Inspect all known goals AND all task ledgers; STOP outranks documentary status."""
    _reject_links(workspace); _reject_links(state_root); _reject_links(suite)
    TaskStore, identity = _import_suite(suite)
    goals_dir = workspace / '.bago' / 'goals'
    _reject_links(goals_dir)
    if goals_dir.is_symlink() or state_root.is_symlink():
        raise BridgeError('Symlinked goals/state root rejected')
    docs: dict[str, dict] = {}
    if goals_dir.exists():
        if not goals_dir.is_dir():
            raise BridgeError('GOALS folder is not a directory')
        for path in sorted(goals_dir.glob('*.goal.json')):
            doc = _read_goal(path)
            if doc['goal_id'].casefold() in {k.casefold() for k in docs}:
                raise BridgeError(f'Duplicate GOAL id: {doc["goal_id"]}')
            if doc['task_dir'].casefold() in (d['task_dir'].casefold() for d in docs.values()):
                raise BridgeError('Multiple GOAL documents share one TaskStore')
            docs[doc['goal_id']] = doc
    # Enumerate ledgers independently of documents: an orphan STOP still governs.
    stores: dict[str, dict] = {}
    if state_root.exists():
        if not state_root.is_dir():
            raise BridgeError('State root is not a directory')
        for d in sorted(state_root.iterdir()):
            _reject_links(d)
            if d.is_dir() and (d / 'control.sqlite3').exists():
                if not _GOAL_ID.fullmatch(d.name):
                    raise BridgeError('Invalid TaskStore directory name')
                stores[d.name] = _load_state(d, TaskStore)
    # Unknown goal documents must be reported, never silently treated as DONE.
    unindexed = []
    if goals_dir.exists():
        for candidate in sorted(goals_dir.iterdir()):
            _reject_links(candidate)
            if candidate.is_dir():
                unindexed.append({'goal_id': None, 'document_status': 'UNINDEXED',
                    'task_dir': None, 'mission_id': None, 'control': 'UNKNOWN',
                    'task_status': 'UNKNOWN', 'effective_state': 'UNINDEXED_DOCUMENT',
                    'document': str(candidate), 'document_sha256': None, 'check_id': None})
                continue
            if candidate.is_file() and candidate.name not in {Path(d['document']).name for d in docs.values()} and candidate.suffix.lower() in {'.md', '.json'}:
                if candidate.name.lower() not in {'readme.md', 'index.json'}:
                    unindexed.append({'goal_id': None, 'document_status': 'UNINDEXED',
                                      'task_dir': None, 'mission_id': None, 'control': 'UNKNOWN',
                                      'task_status': 'UNKNOWN', 'effective_state': 'UNINDEXED_DOCUMENT',
                                      'document': str(candidate), 'document_sha256': _sha(candidate.read_bytes()),
                                      'check_id': None})
    result = []
    bound = set()
    any_stop = any(s['control'] == 'STOPPED' for s in stores.values())
    for goal in docs.values():
        store = stores.get(goal['task_dir'])
        bound.add(goal['task_dir'])
        if store is None:
            state = 'UNBOUND_BLOCKED'
        elif store['mission_id'] != goal['goal_id']:
            state = 'BINDING_MISMATCH_BLOCKED'
        elif store['control'] == 'STOPPED':
            state = 'STOP_BLOCKED'
        elif store['task_status'] == 'OPEN' and goal['status'] in {'DONE', 'CANCELLED', 'DISCARDED'}:
            state = 'DOCUMENT_DONE_TASKSTORE_OPEN'
        elif store['task_status'] == 'OPEN':
            state = 'PENDING'
        else:
            state = 'CLOSED'
        result.append({'goal_id': goal['goal_id'], 'document_status': goal['status'],
                       'task_dir': goal['task_dir'], 'mission_id': store['mission_id'] if store else None,
                       'control': store['control'] if store else 'UNKNOWN',
                       'task_status': store['task_status'] if store else 'MISSING',
                       'effective_state': state, 'document': goal['document'],
                       'document_sha256': goal['document_sha256'], 'check_id': goal['check_id']})
    for task_dir, store in stores.items():
        if task_dir not in bound:
            state = ('STOP_BLOCKED' if store['control'] == 'STOPPED'
                     else 'ORPHAN_TASKSTORE_OPEN' if store['task_status'] == 'OPEN' else 'ORPHAN_TASKSTORE_CLOSED')
            result.append({'goal_id': None, 'document_status': 'MISSING', 'task_dir': task_dir,
                           'mission_id': store['mission_id'], 'control': store['control'],
                           'task_status': store['task_status'], 'effective_state': state,
                           'document': None, 'document_sha256': None, 'check_id': None})
    result.extend(unindexed)
    result.sort(key=lambda e: (e['effective_state'], str(e['task_dir'])))
    pending = [x for x in result if x['effective_state'] != 'CLOSED' and x['effective_state'] != 'ORPHAN_TASKSTORE_CLOSED']
    recovery_markers = _recovery_markers(state_root)
    blocked = bool(recovery_markers) or any_stop or any(x['effective_state'] in {'UNBOUND_BLOCKED', 'DOCUMENT_DONE_TASKSTORE_OPEN', 'UNINDEXED_DOCUMENT', 'BINDING_MISMATCH_BLOCKED'} for x in result)
    # Native runs/rounds preserve an already-started mission ahead of newly added goals.
    # Multiple started OPEN missions cannot be ordered safely without operator review.
    open_rows = [x for x in result if x['task_status'] == 'OPEN']
    started = [x for x in open_rows if stores[x['task_dir']].get('runs')]
    opened = [x for x in open_rows if stores[x['task_dir']].get('round', 0) > 0]
    ordered = sorted(started or opened or open_rows,
                     key=lambda x: (str(x['mission_id']).casefold(), str(x['task_dir']).casefold()))
    reason = 'NO_PENDING_TASKSTORE'
    head = ordered[0] if ordered else None
    if len(started) > 1:
        blocked = True
        reason = 'MULTIPLE_STARTED_OPEN_TASKSTORES'
    elif blocked:
        reason = 'GROUP_BLOCKED'
    elif any(x['effective_state'] == 'ORPHAN_TASKSTORE_OPEN' for x in result):
        reason = 'ORPHAN_OPEN_REQUIRES_BINDING'
    elif head:
        reason = ('READY' if head['effective_state'] == 'PENDING' and
                  head['document_status'] in {'OPEN','ACTIVE'} else 'HEAD_REQUIRES_REVIEW')
    selected = head['goal_id'] if head and reason == 'READY' else None
    return {'schema': SCHEMA, 'status': 'BLOCKED' if blocked else 'PASS',
            'operation': 'RESUME_SUMMARY_READ_ONLY', 'automatic_resume': False,
            'suite_identity': identity, 'goals_folder': str(goals_dir),
            'state_root': str(state_root), 'all_goals': result, 'pending': pending,
            'pending_count': len(pending), 'global_stop': any_stop,
            'effect_authority': 'NONE', 'native_goal_api': 'NOT_CONNECTED',
            'selected_goal': selected, 'selection_reason': reason,
            'sequence_head': head['goal_id'] if head else None,
            'known_task_dirs': sorted(stores),
            'recovery_required': [p.name for p in recovery_markers],
            'ordering': 'Native started OPEN mission, then opened round, then mission_id lexical; CLOSED only removes a ledger'}


def _validated_target(summary: dict, goal_id: str) -> dict:
    targets = [x for x in summary['all_goals'] if x['goal_id'] == goal_id]
    if len(targets) != 1:
        raise BridgeError('Goal not found or ambiguous')
    return targets[0]


def _store(summary, task_dir, suite):
    TaskStore, identity = _import_suite(suite)
    root = Path(summary['state_root']) / task_dir
    return TaskStore(root, identity, lambda: _import_suite(suite)[1])


def build_codex_command(codex: str, goal_path: str, expected_hash: str, task_state=None, suite=None, workspace=None) -> list[str]:
    """Windows-portable argv. Goal text NEVER enters cmd.exe's command string."""
    resolved = shutil.which(codex) if not Path(codex).is_file() else str(Path(codex).resolve())
    if not resolved:
        raise BridgeError(f'Codex executable not found: {codex}')
    if os.name == 'nt' and Path(resolved).suffix.lower() not in {'.exe', '.cmd', '.bat'}:
        raise BridgeError('Windows Codex must resolve to .exe/.cmd/.bat')
    if os.name == 'nt' and Path(resolved).suffix.lower() in {'.cmd','.bat'} and any(c in resolved for c in '&|<>^%!\"\r\n'):
        raise BridgeError('Unsafe Windows batch executable path')
    command = [sys.executable, '-B', str(HERE / 'codex_worker.py'),
            '--codex', resolved, '--goal', goal_path, '--sha256', expected_hash]
    if task_state is not None:
        command += ['--task-state',str(task_state),'--suite',str(suite),'--workspace',str(workspace)]
    return command


def stop_all(state_root: Path, suite: Path, reason: str) -> dict:
    """STOP remains operational with missing/broken GOALS and damaged Suite identity."""
    if not reason.strip():
        raise BridgeError('STOP requires a reason')
    if state_root.is_symlink() or not state_root.is_dir():
        raise BridgeError('State root missing or symlinked; no STOP claimed')
    scripts = suite / 'scripts'
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    from suite_control import TaskStore
    dirs = []
    for d in sorted(state_root.iterdir()):
        if d.is_symlink():
            raise BridgeError('Symlinked TaskStore directory rejected')
        if d.is_dir() and (d / 'control.sqlite3').exists():
            dirs.append(d)
    if not dirs:
        raise BridgeError('No known TaskStores: STOP could not be persisted')
    stopped, errors = [], []
    for d in dirs:
        try:
            store = TaskStore(d, {})
            state = store.status()
            if state['task_status'] == 'OPEN':
                store.stop(reason)
                stopped.append(d.name)
        except Exception as exc:
            errors.append({'task_dir': d.name, 'reason': str(exc)})
            try: _mark_recovery(state_root,d.name,'STOP persistence failed: '+type(exc).__name__)
            except Exception as marker_exc: errors.append({'task_dir':d.name,'reason':'RECOVERY_MARKER_PERSIST_FAILED:'+type(marker_exc).__name__})
    return {'schema': SCHEMA, 'status': 'PASS' if not errors else 'BLOCKED',
            'operation': 'STOP_PERSIST', 'stopped': stopped, 'errors': errors,
            'host_external_stop': 'NOT_RUN', 'documents_required': False}


def _group_error(state_root, known_dirs, TaskStore, own_run_marker=None):
    try:
        _reject_links(state_root)
        if any(p != own_run_marker for p in _recovery_markers(state_root)): return 'GROUP_RECOVERY_REQUIRED'
        actual = set()
        for item in state_root.iterdir():
            _reject_links(item)
            if item.is_dir() and (item/'control.sqlite3').exists():
                actual.add(item.name)
        if actual != set(known_dirs):
            return 'GROUP_MEMBERSHIP_CHANGED_OR_LEDGER_MISSING'
        for name in sorted(actual):
            value = _load_state(state_root/name, TaskStore)
            if value['control'] != 'ACTIVE':
                return 'GROUP_STOP:' + name
        return None
    except (OSError, ValueError, KeyError, sqlite3.Error) as exc:
        return 'GROUP_UNREADABLE:' + type(exc).__name__


def _run_selected(args, summary, workspace, state_root, suite, admit_round=False):
    selected=summary.get('selected_goal')
    if not args.approve_run or not selected:
        return _run_selected_owned(args,summary,workspace,state_root,suite,admit_round)
    target=_validated_target(summary,selected)
    with _ownership_lock(state_root,target['task_dir']):
        return _run_selected_owned(args,summary,workspace,state_root,suite,admit_round)


def _run_selected_owned(args, summary, workspace, state_root, suite, admit_round=False):
    if not args.approve_run:
        raise BridgeError('Run requires --approve-run; host authorization remains separate')
    if not 1 <= args.timeout <= 600:
        raise BridgeError('TIMEOUT_OUT_OF_RANGE')
    if summary['global_stop']:
        raise BridgeError('STOP active in any TaskStore, including those without a GOAL document')
    if summary['status'] != 'PASS':
        raise BridgeError('Unresolved GOALS/TaskStore inconsistency; global execution blocked')
    selected = summary['selected_goal']
    wanted = selected if admit_round else args.goal
    if not selected or wanted != selected:
        raise BridgeError('SEQUENCE_BLOCKED: ' + summary['selection_reason'] + '; prior OPEN task must be CLOSED')
    target = _validated_target(summary, selected)
    state_path = state_root/target['task_dir']
    _same_workspace(state_path, workspace)
    store = _store(summary, target['task_dir'], suite)
    goal_doc = _read_goal(Path(target['document']))
    if goal_doc['document_sha256'] != target['document_sha256']:
        raise BridgeError('GOAL document changed during admission')
    command = build_codex_command(args.codex, target['document'], target['document_sha256'],
                                  state_path, suite, workspace)
    TaskStore, _ = _import_suite(suite)
    known_dirs = summary['known_task_dirs']
    error = _group_error(state_root, known_dirs, TaskStore)
    if error:
        raise BridgeError(error)
    # Started before admission, ready only after an initial full group scan.
    # Native STOP on the active ledger drives the unchanged TaskStore supervisor.
    run_marker = state_root / ('.bridge-run.' + target['task_dir'] + '.json')
    _reject_links(run_marker)
    owned_run_marker = False
    result_known = False
    watcher_started = False
    channel = CancelSignal(create=True)  # Failure here blocks before native round or child.
    command += ['--cancel-signal', channel.name]
    done = threading.Event(); ready = threading.Event(); observations = []
    def mark_recovery(reason):
        try: _mark_recovery(state_root,target['task_dir'],reason)
        except Exception as exc: observations.append('RECOVERY_MARKER_PERSIST_FAILED:'+type(exc).__name__)
    def persist_stop(reason):
        # Nominal STOP stays native. A blocked SQLite write gets an independent
        # 200ms cancellation fallback; an exception cancels immediately.
        written = threading.Event()
        def timeout_cancel():
            if not written.wait(.2):
                channel.set()
                observations.append('STOP_PERSIST_DELAY_CANCELLED')
                mark_recovery('STOP persistence exceeded cancellation fallback')
        fallback = None; fallback_started = False
        try:
            fallback = threading.Thread(target=timeout_cancel, daemon=False)
            fallback.start(); fallback_started = True
            store.stop(reason)
        except BaseException:
            channel.set()
            mark_recovery('STOP persistence failed; process cancellation requested')
            raise
        finally:
            written.set()
            if fallback_started: fallback.join()

    def watch():
        try:
            while not done.is_set():
                error = _group_error(state_root, known_dirs, TaskStore, run_marker)
                if error:
                    observations.append(error)
                    persist_stop('Bridge group supervision: ' + error)
                    ready.set()
                    return
                ready.set()
                done.wait(.05)
        except BaseException as exc:
            observations.append('GROUP_WATCHER_ERROR:' + type(exc).__name__)
            try: persist_stop('Bridge watcher failed; fail-closed')
            except Exception as stop_exc:
                observations.append('STOP_PERSIST_FAILED:' + type(stop_exc).__name__)
            ready.set()
    watcher = threading.Thread(target=watch, daemon=False)
    try:
        watcher.start();watcher_started = True
        if not ready.wait(10) or observations:
            raise BridgeError('GROUP_SUPERVISION_BLOCKED:' + ','.join(observations))
        # Re-read after watcher readiness, before any round/process effect.
        fresh = inspect(workspace, state_root, suite)
        if fresh['selected_goal'] != selected or fresh['known_task_dirs'] != known_dirs:
            raise BridgeError('SELECTION_CHANGED_BEFORE_ADMISSION')
        # Durable admission latch is armed before a round or process exists.
        # A second concurrent dispatcher cannot silently adopt this run.
        with run_marker.open('x',encoding='utf-8') as handle:
            json.dump({'schema':'bago.bridge.run-latch.v1','task_dir':target['task_dir'],
                       'mission_id':selected,'requires_recovery_on_unclean_exit':True},handle)
            handle.flush();os.fsync(handle.fileno())
        owned_run_marker = True
        if admit_round:
            store.open_round()
        result = store.run_check(target['check_id'], command, args.timeout)
        result_known = result.get('status') in {'PASS','FAIL'} and not result.get('supervision_error')
        final_error = _group_error(state_root, known_dirs, TaskStore, run_marker)
        if final_error and not observations:
            observations.append(final_error)
            persist_stop('Bridge post-execution group observation: ' + final_error)
    finally:
        done.set()
        if watcher_started: watcher.join()  # Never close IPC while its owner can still write.
        cancellation_requested = channel.is_set()
        channel.close()
        if owned_run_marker and result_known and not observations and not cancellation_requested:
            run_marker.unlink()
    state = store.status()
    status = result.get('status','FAIL')
    if state['control'] != 'ACTIVE':
        status = 'STOPPED'
    elif observations:
        status = 'BLOCKED'
    elif admit_round and status == 'PASS' and state['task_status'] == 'OPEN':
        status = 'WAITING_TASKSTORE_EVIDENCE'
    return {'schema': SCHEMA, 'operation': 'DISPATCH' if admit_round else 'CODEX_EXECUTION_TASKSTORE',
            'goal_id': selected, 'status': status, 'taskstore_result': result,
            'task_control': state['control'], 'task_status': state['task_status'], 'round': state['round'],
            'group_observations': observations, 'sandbox': 'read-only',
            'independent_cancellation_requested': cancellation_requested,
            'recovery_required': [p.name for p in _recovery_markers(state_root)],
            'native_goal_api': 'NOT_CONNECTED', 'automatic_resume': False,
            'command_shape': ['PYTHON','codex_worker.py','CODEX_EXEC_SANDBOX_READ_ONLY_STDIN'],
            'host_permission': 'NOT_CLAIMED'}


def _resume_one(args,summary,workspace,state_root,suite):
    target=_validated_target(summary,args.goal)
    locked_task_dir=target['task_dir']
    with _ownership_lock(state_root,locked_task_dir):
        summary=inspect(workspace,state_root,suite)
        target=_validated_target(summary,args.goal)
        if target['task_dir']!=locked_task_dir:
            raise BridgeError('TARGET_CHANGED_DURING_RECOVERY')
        marker=_recovery_path(state_root,target['task_dir'])
        run_marker=state_root/('.bridge-run.'+target['task_dir']+'.json')
        _reject_links(run_marker)
        markers=[p for p in (marker,run_marker) if p.exists()]
        if target['effective_state'] not in {'STOP_BLOCKED','PENDING','DOCUMENT_DONE_TASKSTORE_OPEN'}:
            raise BridgeError('Recovery requires an intact goal/mission binding')
        if target['effective_state']!='STOP_BLOCKED' and not markers:
            raise BridgeError('Requested TaskStore is not STOPPED or pending recovery')
        if not args.reason.strip(): raise BridgeError('Explicit recovery requires a reason')
        _same_workspace(state_root/target['task_dir'],workspace)
        store=_store(summary,target['task_dir'],suite)
        state=store.status()
        if state['mission_id']!=args.goal or state['task_status']!='OPEN':
            raise BridgeError('Recovery mission identity mismatch or CLOSED task')
        if any(run['state']=='RUNNING' for run in state['runs']):
            raise BridgeError('Recovery requires prior owned run to finish')
        if markers and state['control']=='ACTIVE':
            store.stop('Explicit reconciliation before resume: '+args.reason)
        result=store.resume(args.reason)
        for pending_marker in markers: pending_marker.unlink()
        result['operation']='EXPLICIT_TASKSTORE_RESUME'
        result['execution_started']=False
        after=inspect(workspace,state_root,suite)
        result['remaining_group_stop']=after['global_stop']
        result['remaining_recovery_required']=after['recovery_required']
        return result


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description='RC4 external serial GOALS dispatch; not native /goal')
    p.add_argument('--workspace', type=Path, default=Path.cwd())
    p.add_argument('--state-root', type=Path)
    p.add_argument('--suite', type=Path, default=HERE.parent/'bago-operating-suite')
    actions = p.add_subparsers(dest='action', required=True)
    actions.add_parser('resume', help='Read-only summary and next eligible goal; does not resume')
    actions.add_parser('doctor', help='Read-only inspection')
    for action in ('run','dispatch'):
        command = actions.add_parser(action, help='Explicit read-only run; dispatch also admits a native round')
        if action == 'run': command.add_argument('--goal', required=True)
        else: command.add_argument('--max-goals',type=int,default=1)
        command.add_argument('--codex',default='codex')
        command.add_argument('--approve-run',action='store_true')
        command.add_argument('--timeout',type=int,default=180)
    task_resume = actions.add_parser('task-resume',help='Explicitly resume one STOPPED ledger')
    task_resume.add_argument('--goal',required=True);task_resume.add_argument('--reason',required=True)
    stop=actions.add_parser('stop');stop.add_argument('--reason',required=True)
    args=p.parse_args(argv)
    try:
        _reject_links(args.workspace); _reject_links(args.suite)
        if args.state_root: _reject_links(args.state_root)
        workspace=args.workspace.resolve(strict=True)
        if not workspace.is_dir(): raise BridgeError('Workspace is not a directory')
        state_root=(args.state_root or workspace.parent/(workspace.name+'.bago_tasks')).resolve()
        suite=args.suite.resolve(strict=True)
        if args.action=='stop':
            result=stop_all(state_root,suite,args.reason)
        else:
            summary=inspect(workspace,state_root,suite)
            if args.action in {'resume','doctor'}: result=summary
            elif args.action=='task-resume':
                result=_resume_one(args,summary,workspace,state_root,suite)
            elif args.action=='run':
                result=_run_selected(args,summary,workspace,state_root,suite)
            else:
                if not args.approve_run: raise BridgeError('Dispatch requires --approve-run')
                if not 1 <= args.max_goals <= 5: raise BridgeError('MAX_GOALS_OUT_OF_RANGE')
                dispatched=[]
                for _ in range(args.max_goals):
                    summary=inspect(workspace,state_root,suite)
                    if not summary['pending']:
                        result={'status':'PASS','operation':'DISPATCH','dispatched':dispatched,'reason':'NO_PENDING_GOAL','native_goal_api':'NOT_CONNECTED'}
                        break
                    turn=_run_selected(args,summary,workspace,state_root,suite,admit_round=True)
                    dispatched.append(turn)
                    result={**turn,'dispatched':dispatched}
                    if turn['status']!='PASS' or turn['task_status']!='CLOSED':break
                else: result={**result,'limit_reached':True}
    except (BridgeError,OSError,ValueError,KeyError,TypeError,sqlite3.Error) as exc:
        result={'schema':SCHEMA,'status':'BLOCKED','error_type':type(exc).__name__,
                'reason':str(exc),'effects':'MUST_INSPECT_TASKSTORE; no success or rollback claimed'}
    print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0 if result['status'] in {'PASS','WAITING_TASKSTORE_EVIDENCE'} else (3 if result['status'] in {'BLOCKED','STOPPED','NOT_RUN','INCONCLUSIVE'} else 1)

if __name__=='__main__':raise SystemExit(main())
