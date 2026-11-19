"""Read-only activity snapshots. Registered state never proves process liveness."""
import argparse, collections, ctypes, datetime, hashlib, json, os, sqlite3, stat, sys, time
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def safe_path(root, relative):
    p = root / relative
    for item in [root, *p.parents, p]:
        if item.exists() or item.is_symlink():
            s = item.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Links/reparse points are not accepted: ' + str(item))
    if not p.resolve().is_relative_to(root):
        raise ValueError('Source escapes selected project')
    return p

def read_file(p, tail=False):
    before = p.stat()
    if not tail and before.st_size > MAX_BYTES:
        raise ValueError('Source exceeds 8 MiB bound')
    with p.open('rb') as f:
        start = max(0, before.st_size - MAX_BYTES) if tail else 0
        f.seek(start)
        if start: f.readline()
        data = f.read(MAX_BYTES + 1)
    after = p.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Source changed during snapshot; retry')
    if len(data) > MAX_BYTES: raise ValueError('Source exceeds bound')
    return data, {'path': str(p), 'sha256_read_bytes': hashlib.sha256(data).hexdigest(),
                  'bytes_read': len(data), 'tail_only': bool(start), 'mtime_ns': after.st_mtime_ns}

def pick(value, fields):
    return {k: value[k] for k in fields if k in value}

def team_snapshot(root, limit):
    p = safe_path(root, '.bago5-team/runtime/state.json')
    if not p.exists(): return {'availability': 'NO_STATE', 'source': str(p)}
    raw, identity = read_file(p); state = json.loads(raw)
    if not isinstance(state, dict) or not isinstance(state.get('mission'), dict):
        raise ValueError('Invalid team state object')
    tasks = state.get('work_status', {})
    executions = state.get('executions', {})
    if not isinstance(tasks, dict) or not isinstance(executions, dict):
        raise ValueError('Invalid team work/execution mappings')
    if any(not isinstance(v,dict) for v in [*tasks.values(),*executions.values()]):raise ValueError('Invalid task/execution record')
    result = {'availability': 'READ', 'source': identity, 'controller': 'teamctl',
              'mission': pick(state['mission'], ['mission_id', 'operation']),
              'state': pick(state, ['lifecycle', 'task_state', 'product_state', 'evidence_state',
                                   'terminal_gate', 'candidate_id', 'updated_at']),
              'tasks': [{'id': k, **pick(v, ['status', 'agent', 'claimed_at', 'done_at'])} for k,v in list(tasks.items())[:limit]],
              'executions': [{'id': k, **pick(v, ['work_id', 'check_id', 'state', 'pid', 'started_at',
                                      'result', 'path', 'sha256', 'pause_requested', 'pause_observed'])} for k,v in sorted(executions.items(),key=lambda kv:str(kv[1].get('started_at','')),reverse=True)[:limit]],
              'events': [], 'warnings': []}
    ep = safe_path(root, '.bago5-team/runtime/events.jsonl')
    if ep.exists():
        eventraw, ei = read_file(ep, tail=True);result['event_source'] = ei
        for line in eventraw.splitlines()[-limit:]:
            try:
                e=json.loads(line)
                if not isinstance(e,dict): raise ValueError('not object')
                result['events'].append(pick(e,['at','kind','work_id','check_id','execution_id','request_id','result','from_agent','to_agent']))
            except (ValueError,TypeError):result['warnings'].append('Malformed or incomplete event omitted; source may be being written')
    result['task_counts'] = dict(collections.Counter(str(x.get('status','UNKNOWN')) for x in tasks.values()))
    result['total_tasks']=len(tasks);result['total_executions']=len(executions);result['rows_limited_to']=limit;result['view_notice']='Lists may be truncated; event tail is bounded separately. See total_tasks/total_executions.'
    result['integrity'] = 'NOT_VERIFIED: display only; use controller verify for evidence integrity'
    return result

def suite_snapshot(root, relative, limit):
    p = safe_path(root, relative)
    if not p.exists():return {'availability':'NO_STATE','source':str(p)}
    if not p.is_file():raise ValueError('Expected control.sqlite3 file')
    # Deserialize a stable database image in memory; never create SQLite sidecars in the project.
    for suffix in ['-wal','-journal']:
        sidecar=safe_path(root,relative+suffix)
        if sidecar.exists() and sidecar.stat().st_size:raise ValueError('Active WAL/journal: provide a consistent exported SQLite snapshot')
    raw, identity=read_file(p)
    for suffix in ['-wal','-journal']:
        sidecar=safe_path(root,relative+suffix)
        if sidecar.exists() and sidecar.stat().st_size:raise ValueError('Database changed during snapshot; retry')
    conn=sqlite3.connect(':memory:')
    conn.deserialize(raw)
    conn.row_factory=sqlite3.Row
    deadline=time.monotonic()+1
    conn.set_progress_handler(lambda: int(time.monotonic()>deadline),1000)
    try:
        conn.execute('PRAGMA query_only=ON');conn.execute('PRAGMA trusted_schema=OFF');conn.execute('BEGIN')
        objects={r['name']:r for r in conn.execute("SELECT name,type,sql FROM sqlite_master WHERE name IN ('meta','checks','runs','assignments','events')")}
        if any(n not in objects or objects[n]['type']!='table' or 'VIRTUAL TABLE' in objects[n]['sql'].upper() for n in ['meta','checks','runs','assignments','events']):raise ValueError('Expected ordinary Suite tables; views/virtual tables rejected')
        meta={r['key']:json.loads(r['value']) for r in conn.execute('SELECT key,value FROM meta LIMIT 64')}
        plan=meta.get('plan',{})
        result={'availability':'READ','controller':'suite','source':identity,'transaction_snapshot':True,
                'mission':pick(plan,['mission_id','operation']),
                'state':pick(meta,['control','closed','round','candidate']),
                'tasks':[dict(r) for r in conn.execute('SELECT id,outcome,consumed FROM checks ORDER BY id LIMIT ?', (limit,))],
                'executions':[dict(r) for r in conn.execute('SELECT id,check_id,pid,started,finished,returncode,state,interruption,receipt FROM runs ORDER BY started DESC LIMIT ?', (limit,))],
                'assignments':[dict(r) for r in conn.execute('SELECT id,check_id,worker,round,state,interruption FROM assignments ORDER BY id LIMIT ?', (limit,))],
                'events':[dict(r) for r in conn.execute('SELECT seq,at,action FROM events ORDER BY seq DESC LIMIT ?', (limit,))],
                'integrity':'NOT_VERIFIED: transaction read, not receipt validation',
                'rows_limited_to':limit,
                'total_tasks':conn.execute('SELECT count(*) FROM checks').fetchone()[0],
                'total_executions':conn.execute('SELECT count(*) FROM runs').fetchone()[0],
                'view_notice':'Each list is limited; events newest first; assignments/checks ordered by ID'}
        return result
    finally:conn.close()

def process_snapshot(pid):
    if not isinstance(pid,int) or isinstance(pid,bool) or not 1<=pid<=0xFFFFFFFF:raise ValueError('PID outside1..4294967295')
    result={'pid':pid,'observed_at':utc(),'mission_binding':'UNVERIFIED: an equal PID is not an authenticated mission binding'}
    if os.name!='nt':
        try:os.kill(pid,0);result['observed_state']='EXISTS';result['metrics']='NOT_AVAILABLE on this platform'
        except ProcessLookupError:result['observed_state']='NOT_FOUND'
        except PermissionError:result['observed_state']='ACCESS_DENIED'
        return result
    from ctypes import wintypes as w
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
    k.CloseHandle.argtypes=[w.HANDLE];k.CloseHandle.restype=w.BOOL
    k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD];k.WaitForSingleObject.restype=w.DWORD
    k.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)];k.GetProcessTimes.restype=w.BOOL
    k.QueryFullProcessImageNameW.argtypes=[w.HANDLE,w.DWORD,w.LPWSTR,ctypes.POINTER(w.DWORD)];k.QueryFullProcessImageNameW.restype=w.BOOL
    handle=k.OpenProcess(0x1000|0x100000,False,pid)
    if not handle:
        err=ctypes.get_last_error();result.update(observed_state='NOT_FOUND' if err==87 else 'ACCESS_DENIED_OR_UNKNOWN',winerror=err);return result
    try:
        wait=k.WaitForSingleObject(handle,0)
        result['observed_state']={0:'EXITED',258:'ALIVE'}.get(wait,'UNKNOWN')
        create,exit_,kernel,user=w.FILETIME(),w.FILETIME(),w.FILETIME(),w.FILETIME()
        ticks=lambda x:(x.dwHighDateTime<<32)|x.dwLowDateTime
        if k.GetProcessTimes(handle,ctypes.byref(create),ctypes.byref(exit_),ctypes.byref(kernel),ctypes.byref(user)):
            result['instance_key']=str(pid)+':'+str(ticks(create))
            result['started_at']=datetime.datetime.fromtimestamp(ticks(create)/1e7-11644473600,datetime.timezone.utc).isoformat()
            result['cpu_seconds']=(ticks(kernel)+ticks(user))/1e7
        size=w.DWORD(32768);buf=ctypes.create_unicode_buffer(size.value)
        if k.QueryFullProcessImageNameW(handle,0,buf,ctypes.byref(size)):result['executable_name']=Path(buf.value).name
        class Counters(ctypes.Structure):
            _fields_=[('cb',w.DWORD),('PageFaultCount',w.DWORD)]+[(n,ctypes.c_size_t) for n in ['PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage']]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        api=ctypes.WinDLL('psapi',use_last_error=True);api.GetProcessMemoryInfo.argtypes=[w.HANDLE,ctypes.POINTER(Counters),w.DWORD];api.GetProcessMemoryInfo.restype=w.BOOL
        if api.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb):result['working_set_bytes']=counters.WorkingSetSize
        else:result['working_set_bytes']=None;result['memory_metric']='UNAVAILABLE'
    finally:k.CloseHandle(handle)
    return result

def snapshot(root,controller,db,limit,pids,previous=None):
    root=Path(root).absolute()
    if not root.is_dir():raise ValueError('Selected project root is not a directory')
    safe_path(root,'.')
    now=time.monotonic()
    try:registered=team_snapshot(root,limit) if controller=='team' else suite_snapshot(root,db,limit)
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error) as e:registered={'availability':'ERROR','error':str(e)}
    processes=[process_snapshot(p) for p in pids]
    if previous:
        elapsed=now-previous['monotonic']
        old={p['pid']:p for p in previous['observed_processes']}
        for p in processes:
            prior=old.get(p['pid'],{})
            if p.get('instance_key') and p['instance_key']==prior.get('instance_key') and 'cpu_seconds' in p and 'cpu_seconds' in prior and elapsed>0:
                p['cpu_percent_one_core']=max(0,(p['cpu_seconds']-prior['cpu_seconds'])/elapsed*100)
                p['sample_interval_seconds']=elapsed
            elif prior.get('instance_key') and p.get('instance_key') and p['instance_key']!=prior['instance_key']:p['pid_reused']=True
    return {'schema':'bago5.activity.v1','observed_at':utc(),'monotonic':now,'project':str(root),
            'registered_activity':registered,'observed_processes':processes,
            'limits':['State is recorded history, not liveness or integrity validation.',
                      'Only explicitly selected PIDs are queried; no commands, environment or log contents collected.',
                      'No ChatGPT internal activity, background service, scheduling or mission writes.']}

def markdown(r):
    a=r['registered_activity'];out=['# Monitor de actividad BAGO5','', 'Observado: '+r['observed_at'], 'Proyecto: '+r['project'], '', '## 1. Misiones y tareas registradas','', 'Disponibilidad: '+a['availability']]
    if a.get('error'):out+=['Error: '+a['error']]
    for key in ['mission','state','task_counts','total_tasks','total_executions','rows_limited_to','view_notice','tasks','executions','assignments','events','warnings','source','event_source']:
        if key in a:out+=['',key+':','```json',json.dumps(a[key],ensure_ascii=False,indent=2),'```']
    out+=['','Integridad: '+a.get('integrity','NOT_VERIFIED'),'','## 2. Procesos observados','']
    out+=['```json',json.dumps(r['observed_processes'],ensure_ascii=False,indent=2),'```'] if r['observed_processes'] else ['Sin PID seleccionado; actividad de procesos NOT_RUN.']
    out+=['','## Limites','']+['- '+x for x in r['limits']]
    return '\n'.join(out)

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',required=True);ap.add_argument('--controller',choices=['team','suite'],default='team');ap.add_argument('--suite-db',default='.bago/suite-control/control.sqlite3');ap.add_argument('--pid',type=int,action='append',default=[]);ap.add_argument('--limit',type=int,default=30);ap.add_argument('--format',choices=['json','markdown'],default='markdown');ap.add_argument('--watch-seconds',type=float,default=0);ap.add_argument('--interval',type=float,default=2);args=ap.parse_args(argv)
    if not 1<=args.limit<=200 or not 0<=args.watch_seconds<=60 or not 0.5<=args.interval<=10 or any(not 1<=p<=0xFFFFFFFF for p in args.pid) or len(args.pid)>32:ap.error('limits: events1..200, watch0..60s, interval0.5..10s, at most32 PIDs in1..4294967295')
    end=time.monotonic()+args.watch_seconds;previous=None
    while True:
        try:r=snapshot(args.root,args.controller,args.suite_db,args.limit,sorted(set(args.pid)),previous)
        except (ValueError,OSError) as e:print(json.dumps({'status':'ERROR','error':str(e)}));return 2
        print(json.dumps(r,ensure_ascii=False) if args.format=='json' else markdown(r),flush=True);previous=r
        remaining=end-time.monotonic()
        if remaining<=0:return 2 if r['registered_activity']['availability']=='ERROR' else 0
        time.sleep(min(args.interval,remaining))

if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:sys.exit(130)
