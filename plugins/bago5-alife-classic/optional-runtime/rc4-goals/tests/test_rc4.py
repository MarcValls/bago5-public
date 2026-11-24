"""RC4 regressions with real local processes; no provider or installed state."""
from pathlib import Path
from contextlib import redirect_stdout
from datetime import datetime
from unittest.mock import patch
import ctypes,io,json,os,sqlite3,subprocess,sys,threading,time,unittest
import test_repair as original
import test_rc3 as prior

b=original.b;TaskStore=original.TaskStore;IDENTITY=original.IDENTITY;SUITE=original.SUITE

class RC4(unittest.TestCase):
    setUp=original.Fixture.setUp
    goal=original.Fixture.goal
    task=prior.RC3.task
    mock=prior.RC3.mock

    def call(self,*args):
        output=io.StringIO()
        with redirect_stdout(output):
            code=b.main(['--workspace',str(self.workspace),'--state-root',str(self.states),'--suite',str(SUITE),*args])
        return code,json.loads(output.getvalue())

    def dead(self,pid):
        if os.name!='nt':
            try:os.kill(pid,0)
            except ProcessLookupError:return
            self.fail('Owned process still alive')
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.OpenProcess.argtypes=[ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong];k.OpenProcess.restype=ctypes.c_void_p
        k.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_ulong];k.CloseHandle.argtypes=[ctypes.c_void_p]
        handle=k.OpenProcess(0x00100000,False,pid)
        try:self.assertFalse(handle and k.WaitForSingleObject(handle,1000)==258,'Owned process survived')
        finally:
            if handle:k.CloseHandle(handle)

    def failure_case(self,delay=0,deny_recovery_marker=False,spawn_descendant=False,check_concurrent=False,fallback_start_failure=False):
        a=self.task('A');other=self.task('B');stub,capture=self.mock(6)
        descendant_capture=self.parent/'descendant.json'
        if spawn_descendant:
            desc=self.parent/'descendant.py'
            desc.write_text('import os,time,json\nfrom pathlib import Path\n'+f'Path({str(descendant_capture)!r}).write_text(json.dumps({{"pid":os.getpid()}}))\n'+'time.sleep(6)\n')
            script=self.parent/'capture.py';code=script.read_text('utf-8')
            code=code.replace('import json,os,sys,time','import json,os,sys,time,subprocess')
            code=code.replace('time.sleep(6)',f'subprocess.Popen([sys.executable,"-B",{str(desc)!r}])\ntime.sleep(6)')
            script.write_text(code,encoding='utf-8')
        event={};failed=[];concurrent=[];done=threading.Event();original_store=b._store
        def stores(summary,task_dir,suite):
            store=original_store(summary,task_dir,suite)
            if task_dir=='A':
                def denied(reason):
                    failed.append(time.time_ns())
                    if delay:time.sleep(delay)
                    if check_concurrent:
                        concurrent.append(original.cli(self.workspace,self.states,'task-resume','--goal','A','--reason','Explicit concurrent recovery must wait'))
                    raise sqlite3.OperationalError('RC4 injected write failure')
                store.stop=denied
            return store
        def stop_other():
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                marker=descendant_capture if spawn_descendant else capture
                if marker.exists():break
                if done.wait(.01):return
            else:event['error']='No child';return
            time.sleep(.1)
            event['stop_ns']=time.time_ns();event['stop']=other.stop('Explicit RC4 isolated group STOP')
        thread=threading.Thread(target=stop_other);thread.start()
        native_start=threading.Thread.start
        def start(target_thread):
            if fallback_start_failure and getattr(target_thread,'_target',None).__name__=='timeout_cancel':
                raise RuntimeError('Injected fallback thread start failure')
            return native_start(target_thread)
        try:
            with patch.object(b,'_store',side_effect=stores),patch.object(threading.Thread,'start',start):
                if deny_recovery_marker:
                    with patch.object(b,'_mark_recovery',side_effect=OSError('Injected marker write failure')):
                        code,result=self.call('dispatch','--approve-run','--codex',str(stub),'--timeout','15')
                else:code,result=self.call('dispatch','--approve-run','--codex',str(stub),'--timeout','15')
        finally:done.set();thread.join(timeout=25)
        self.assertFalse(thread.is_alive());self.assertNotIn('error',event)
        if check_concurrent:
            self.assertEqual(len(concurrent),2)
            for recovery_code,recovery in concurrent:
                self.assertEqual(recovery_code,3,recovery)
                self.assertIn('DISPATCHER_OWNS_TASKSTORE',recovery['reason'])
        self.assertEqual(code,3,result);self.assertEqual(result['status'],'BLOCKED')
        self.assertTrue(result['independent_cancellation_requested'])
        if not fallback_start_failure:self.assertGreaterEqual(len(failed),1)
        state=a.status();run=state['runs'][0]
        self.assertEqual(state['control'],'ACTIVE');self.assertEqual(state['task_status'],'OPEN')
        self.assertNotEqual(run['returncode'],0);self.assertEqual(other.status()['control'],'STOPPED')
        self.assertTrue((self.states/'.bridge-run.A.json').exists())
        self.assertNotIn('MOCK_DONE',(self.states/'A/runs'/run['id']/'stdout.log').read_text('utf-8'))
        self.dead(json.loads(capture.read_text('utf-8'))['pid'])
        if spawn_descendant:self.dead(json.loads(descendant_capture.read_text())['pid'])
        finished=datetime.fromisoformat(run['finished']).timestamp()*1e9
        self.assertLess((finished-event['stop_ns'])/1e9,3,'Cancellation waited for slow persistence or child completion')
        self.assertEqual(self.call('task-resume','--goal','B','--reason','Explicit fixture B resume')[0],0)
        self.assertFalse(b.inspect(self.workspace,self.states,SUITE)['global_stop'])
        # The durable pre-admission latch still blocks A even if the later marker write failed.
        self.assertEqual(self.call('dispatch','--approve-run','--codex',str(stub))[0],3)
        self.assertEqual(a.status()['round'],1)
        self.assertEqual(self.call('task-resume','--goal','A','--reason','Explicit fixture A reconciliation')[0],0)
        self.assertEqual(a.status()['control'],'ACTIVE');self.assertEqual(a.status()['round'],1)
        self.assertEqual(len(a.status()['runs']),1);self.assertFalse(b._recovery_markers(self.states))

    def test_stop_persistence_failure_cancels_real_child(self):self.failure_case()
    def test_slow_stop_write_cancels_before_write_returns(self):self.failure_case(delay=.7)
    def test_later_marker_write_failure_keeps_prearmed_latch(self):self.failure_case(deny_recovery_marker=True)
    def test_immediate_descendant_is_in_worker_job_before_stop(self):self.failure_case(spawn_descendant=True)
    def test_writer_over_ten_seconds_retains_owner_until_exit(self):self.failure_case(delay=10.2,check_concurrent=True)
    def test_fallback_thread_start_failure_still_cancels(self):self.failure_case(fallback_start_failure=True)

    def test_binding_changed_during_recovery_does_not_resume_unlocked_target(self):
        a=self.task('A');a.stop('Fixture stopped A')
        plan=b._read_meta(self.states/'A')['plan']
        other=TaskStore(self.states/'C',IDENTITY,lambda:IDENTITY);other.initialize(self.workspace,plan)
        other.stop('Fixture stopped alternate A binding')
        original_inspect=b.inspect;calls=[]
        def inspecting(*args):
            calls.append(1)
            if len(calls)==2:
                doc=json.loads((self.docs/'A.goal.json').read_text('utf-8'));doc['task_dir']='C'
                (self.docs/'A.goal.json').write_text(json.dumps(doc),encoding='utf-8')
            return original_inspect(*args)
        with patch.object(b,'inspect',side_effect=inspecting):
            code,result=self.call('task-resume','--goal','A','--reason','Explicit recovery under concurrent binding change')
        self.assertEqual(code,3,result);self.assertEqual(result['reason'],'TARGET_CHANGED_DURING_RECOVERY')
        self.assertEqual(a.status()['control'],'STOPPED');self.assertEqual(other.status()['control'],'STOPPED')

    def test_recovery_cannot_steal_pre_admission_latch(self):
        a=self.task('A');stub,capture=self.mock();ready=threading.Event();proceed=threading.Event();answer={}
        original_store=b._store
        def stores(summary,task_dir,suite):
            store=original_store(summary,task_dir,suite);native=store.open_round
            def held():
                ready.set()
                if not proceed.wait(20):raise OSError('Test barrier timed out')
                return native()
            store.open_round=held
            return store
        def dispatch():
            try:answer['value']=self.call('dispatch','--approve-run','--codex',str(stub))
            except BaseException as exc:answer['error']=repr(exc)
        with patch.object(b,'_store',side_effect=stores):
            thread=threading.Thread(target=dispatch);thread.start()
            try:
                self.assertTrue(ready.wait(15))
                self.assertEqual(a.status()['round'],0);self.assertFalse(a.status()['runs'])
                code,result=original.cli(self.workspace,self.states,'task-resume','--goal','A','--reason','Explicit concurrent test')
                self.assertEqual(code,3,result);self.assertIn('DISPATCHER_OWNS_TASKSTORE',result['reason'])
                self.assertTrue((self.states/'.bridge-run.A.json').exists())
            finally:proceed.set();thread.join(timeout=30)
        self.assertFalse(thread.is_alive());self.assertNotIn('error',answer)
        self.assertEqual(answer['value'][0],0,answer)

    def test_unknown_native_result_retains_recovery_latch(self):
        a=self.task('A');stub,capture=self.mock();original_store=b._store
        def stores(summary,task_dir,suite):
            store=original_store(summary,task_dir,suite)
            def uncertain(*args):raise OSError('Injected unknown native execution result')
            store.run_check=uncertain
            return store
        with patch.object(b,'_store',side_effect=stores):code,result=self.call('dispatch','--approve-run','--codex',str(stub))
        self.assertEqual(code,3,result);self.assertTrue((self.states/'.bridge-run.A.json').exists())
        self.assertEqual(a.status()['round'],1);self.assertFalse(capture.exists())
        self.assertEqual(self.call('dispatch','--approve-run','--codex',str(stub))[0],3)

    def test_watcher_start_failure_does_not_admit_round_or_leave_channel(self):
        a=self.task('A');stub,capture=self.mock();channels=[];real_signal=b.CancelSignal
        def signals(*args,**kwargs):
            value=real_signal(*args,**kwargs);channels.append(value.name);return value
        with patch.object(b,'CancelSignal',side_effect=signals),patch.object(b.threading.Thread,'start',side_effect=OSError('Injected watcher start failure')):
            code,result=self.call('dispatch','--approve-run','--codex',str(stub))
        self.assertEqual(code,3,result);self.assertEqual(a.status()['round'],0);self.assertFalse(capture.exists())
        with self.assertRaises(FileNotFoundError):real_signal(name=channels[0])

    def test_multiple_stops_resume_one_without_execution_or_global_override(self):
        a=self.task('A');other=self.task('B');stub,capture=self.mock()
        self.assertEqual(self.call('stop','--reason','Explicit multiple STOP fixture')[0],0)
        self.assertEqual(self.call('task-resume','--goal','A','--reason','Explicit A only')[0],0)
        self.assertEqual(a.status()['control'],'ACTIVE');self.assertEqual(other.status()['control'],'STOPPED')
        self.assertEqual(self.call('dispatch','--approve-run','--codex',str(stub))[0],3)
        self.assertFalse(capture.exists());self.assertEqual(a.status()['round'],0)
        self.assertEqual(self.call('task-resume','--goal','B','--reason','Explicit B only')[0],0)
        self.assertFalse(capture.exists());self.assertEqual(other.status()['round'],0)
        self.assertEqual(b.inspect(self.workspace,self.states,SUITE)['selected_goal'],'A')

    def test_marker_cannot_bypass_wrong_mission_binding(self):
        self.task('A');other=self.task('B');other.stop('Fixture STOP B')
        (self.docs/'B.goal.json').unlink()
        doc=json.loads((self.docs/'A.goal.json').read_text('utf-8'));doc['task_dir']='B'
        (self.docs/'A.goal.json').write_text(json.dumps(doc),encoding='utf-8')
        b._mark_recovery(self.states,'B','Fixture bad binding')
        code,result=self.call('task-resume','--goal','A','--reason','Explicit request must not resume wrong mission')
        self.assertEqual(code,3,result);self.assertEqual(other.status()['control'],'STOPPED')
        self.assertTrue(b._recovery_markers(self.states))

    def test_cancel_channel_failure_blocks_before_round(self):
        a=self.task('A');stub,capture=self.mock()
        with patch.object(b,'CancelSignal',side_effect=OSError('Injected memory channel failure')):
            code,result=self.call('dispatch','--approve-run','--codex',str(stub))
        self.assertEqual(code,3,result);self.assertEqual(a.status()['round'],0);self.assertFalse(capture.exists())

    def test_prearm_write_failure_blocks_before_round(self):
        a=self.task('A');stub,capture=self.mock();real_open=Path.open
        def blocked(path,*args,**kwargs):
            if path.name=='.bridge-run.A.json' and args and args[0]=='x':raise OSError('Injected prearm denial')
            return real_open(path,*args,**kwargs)
        with patch.object(Path,'open',blocked):code,result=self.call('dispatch','--approve-run','--codex',str(stub))
        self.assertEqual(code,3,result);self.assertEqual(a.status()['round'],0);self.assertFalse(capture.exists())

    @unittest.skipUnless(os.name=='nt','Windows launcher')
    def test_dispatch_launcher_python_fallback_propagates_cancel(self):
        tools=self.parent/'fallback-bin';tools.mkdir()
        (tools/'python.cmd').write_text('@echo off\r\necho RC4_PYTHON_FALLBACK_SELECTED\r\n"'+sys.executable+'" %*\r\nexit /b %ERRORLEVEL%\r\n',encoding='utf-8')
        env={**os.environ,'PATH':str(tools)+os.pathsep+str(Path(os.environ['SystemRoot'])/'System32')}
        p=subprocess.run(['cmd.exe','/d','/c','GOALS_DESPACHAR.cmd'],cwd=original.PACKAGE.parent,
                         env=env,input='fixture-not-executed\nCANCELAR\n',capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,3,p.stderr);self.assertIn('RC4_PYTHON_FALLBACK_SELECTED',p.stdout)

    @unittest.skipUnless(os.name=='nt','Windows launcher')
    def test_dispatch_launcher_missing_python_returns_9009(self):
        env={**os.environ,'PATH':str(Path(os.environ['SystemRoot'])/'System32')}
        p=subprocess.run(['cmd.exe','/d','/c','GOALS_DESPACHAR.cmd'],cwd=original.PACKAGE.parent,
                         env=env,capture_output=True,text=True,timeout=20)
        self.assertEqual(p.returncode,9009,p.stdout+p.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
