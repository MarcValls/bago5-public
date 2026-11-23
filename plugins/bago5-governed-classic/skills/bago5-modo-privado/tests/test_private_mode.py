"""Synthetic tests: prove the cooperative core, NOT real host-wide isolation."""
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from private_mode import Code, Coordinator, Denied, Gate, State, WindowsKeePassXC


class SyntheticHost:
    """Deliberately NOT a deployable ChatGPT/Codex adapter."""
    def __init__(self):
        self.fail_at = None
        self.order = []
        self.freeze_callback = None
    def _step(self, step):
        self.order.append(step)
        if self.fail_at == step:
            raise RuntimeError('SYNTHETIC_SECRET_MUST_NOT_LEAK')
    def validate_coverage(self, gate): self._step('coverage')
    def freeze_and_flush(self, gate):
        self._step('freeze')
        if self.freeze_callback: self.freeze_callback()
    def confirm_sealed(self, gate):
        self._step('sealed')
        if gate.snapshot().state == State.NORMAL or gate.snapshot().active:
            raise Denied(Code.HOST_BOUNDARY_UNPROVEN)
    def prepare_resume(self, gate):
        self._step('resume')
        assert gate.snapshot().state == State.RESUMING


class SyntheticLauncher:
    def __init__(self, gate):
        self.gate, self.verified, self.opened = gate, 0, 0
        self.fail_verify = self.fail_open = False
    def verify(self):
        self.verified += 1
        if self.fail_verify: raise Denied(Code.EXECUTABLE_UNTRUSTED)
    def open(self):
        if self.fail_open: raise RuntimeError('SECRET_IN_LAUNCH_EXCEPTION')
        assert self.gate.snapshot().state == State.PRIVATE
        assert self.gate.snapshot().active == 0
        self.opened += 1


class PrivateModeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'gate.sqlite'
        self.gate = Gate(self.path)
        self.gate.bootstrap()  # Synthetic host installed with explicit test authority.
        self.host = SyntheticHost()
        self.launcher = SyntheticLauncher(self.gate)
        self.c = Coordinator(self.gate, self.launcher, self.host)
    def tearDown(self): self.tmp.cleanup()
    def denied(self, code, fn):
        with self.assertRaises(Denied) as ctx: fn()
        self.assertEqual(ctx.exception.code, code)

    def test_fresh_store_starts_blocked(self):
        gate = Gate(Path(self.tmp.name) / 'new.sqlite')
        self.assertEqual(gate.snapshot().state, State.BLOCKED)
        self.denied(Code.GATE_CLOSED, lambda: gate.invoke(lambda _: 'data'))
    def test_missing_host_blocks_and_does_not_launch(self):
        c = Coordinator(self.gate, self.launcher)
        self.denied(Code.HOST_UNAVAILABLE, c.start)
        self.assertEqual(self.gate.snapshot().state, State.BLOCKED)
        self.assertEqual(self.launcher.opened, 0)
    def test_start_opens_only_after_drain(self):
        self.assertEqual(self.c.start(), State.PRIVATE)
        self.assertEqual(self.host.order, ['coverage','freeze','sealed'])
        self.assertEqual(self.launcher.opened, 1)
    def test_every_controlled_tool_blocked_during_private(self):
        self.c.start()
        for channel in ['screenshot','video','accessibility','keyboard','clipboard','vault',
                        'temporary_files','process_memory','shell','worker','unknown_tool','export']:
            with self.subTest(channel=channel):
                called = []
                self.denied(Code.GATE_CLOSED, lambda: self.gate.invoke(lambda _: called.append(channel)))
                self.assertEqual(called, [])
    def test_preparing_closes_admission_before_host_callback(self):
        def callback():
            self.assertEqual(self.gate.snapshot().state, State.PREPARING)
            self.denied(Code.GATE_CLOSED, lambda: self.gate.invoke(lambda _: None))
        self.host.freeze_callback = callback
        self.c.start()
    def test_unstoppable_observer_blocks_launch(self):
        with self.gate.ticket():
            self.denied(Code.OBSERVATION_NOT_DRAINED, lambda: self.c.start(timeout=0.01))
            self.assertEqual(self.launcher.opened, 0)
        self.assertEqual(self.gate.snapshot().state, State.BLOCKED)
    def test_running_observer_cooperatively_stops_and_result_discarded(self):
        entered, release = threading.Event(), threading.Event()
        outcomes = []
        def work():
            def observe(ticket):
                entered.set()
                self.assertTrue(release.wait(2))
                self.assertTrue(ticket.cancelled)
                return 'SYNTHETIC_FRAME'
            try: self.gate.invoke(observe)
            except Denied as error: outcomes.append(error.code)
        th = threading.Thread(target=work); th.start(); self.assertTrue(entered.wait(2))
        self.host.freeze_callback = release.set
        self.c.start(timeout=2)
        th.join(2)
        self.assertFalse(th.is_alive())
        self.assertEqual(outcomes, [Code.STALE_RESULT])
        self.assertEqual(self.launcher.opened, 1)
    def test_second_process_sees_closed_gate(self):
        self.c.start()
        script = "from pathlib import Path;from private_mode import *;g=Gate(Path(__import__('sys').argv[1]));\ntry:g.invoke(lambda _:1)\nexcept Denied as e:print(e.code.value)"
        proc = subprocess.run([sys.executable, '-B', '-c', script, str(self.path)],
            env={**os.environ,'PYTHONPATH':str(SCRIPTS)},capture_output=True,text=True,timeout=5)
        self.assertEqual(proc.returncode,0)
        self.assertEqual(proc.stdout.strip(),'GATE_CLOSED')
    def test_second_controller_cannot_take_over(self):
        self.c.start()
        other = Coordinator(Gate(self.path),self.launcher,self.host)
        self.denied(Code.CONTROLLER_BUSY,other.start)
        self.assertEqual(self.launcher.opened,1)
    def test_crashed_private_session_remains_closed_on_restart(self):
        self.c.start()
        second = Gate(self.path)
        self.assertEqual(second.snapshot().state,State.PRIVATE)
        self.denied(Code.RECOVERY_REQUIRED,second.bootstrap)
        self.denied(Code.GATE_CLOSED,lambda:second.invoke(lambda _:None))
    def test_crashed_observer_ticket_is_not_auto_expired(self):
        script = "from pathlib import Path;from private_mode import *;import os,sys;g=Gate(Path(sys.argv[1]));t=g.ticket();t.__enter__();os._exit(0)"
        result = subprocess.run([sys.executable,'-B','-c',script,str(self.path)],
            env={**os.environ,'PYTHONPATH':str(SCRIPTS)},timeout=5)
        self.assertEqual(result.returncode,0)
        self.assertEqual(self.gate.snapshot().active,1)
        self.denied(Code.OBSERVATION_NOT_DRAINED,lambda:self.c.start(timeout=0))
        self.assertEqual(self.launcher.opened,0)
    def test_cancel_does_not_reopen(self):
        self.c.start(); self.c.cancel()
        self.assertEqual(self.gate.snapshot().state,State.CANCELLED)
        self.denied(Code.GATE_CLOSED,lambda:self.gate.invoke(lambda _:None))
    def test_done_needs_explicit_safety_acknowledgment(self):
        self.c.start()
        self.denied(Code.EXPLICIT_CONFIRMATION_REQUIRED,lambda:self.c.finish('done',safe_to_resume=False))
        self.assertEqual(self.gate.snapshot().state,State.PRIVATE)
    def test_done_reports_only_user_finished_not_saved(self):
        self.c.start()
        result = self.c.finish('done',safe_to_resume=True)
        self.assertEqual(result,{'state':'NORMAL','user_finished':True,'save_verified':False})
        self.assertEqual(self.gate.invoke(lambda _:42),42)
    def test_cancel_resume_is_explicit_and_not_success(self):
        self.c.start();self.c.cancel()
        result=self.c.finish('cancel',safe_to_resume=True)
        self.assertFalse(result['user_finished']);self.assertFalse(result['save_verified'])
        self.assertEqual(self.gate.snapshot().state,State.NORMAL)
    def test_cancelled_cannot_claim_done(self):
        self.c.start();self.c.cancel()
        self.denied(Code.INVALID_ACTION,lambda:self.c.finish('done',safe_to_resume=True))
    def test_arbitrary_action_not_echoed(self):
        self.c.start()
        self.denied(Code.INVALID_ACTION,lambda:self.c.finish('SECRET_INPUT',safe_to_resume=True))
    def test_invalid_executable_blocks(self):
        self.launcher.fail_verify=True
        self.denied(Code.EXECUTABLE_UNTRUSTED,self.c.start)
        self.assertEqual(self.gate.snapshot().state,State.BLOCKED)
        self.assertEqual(self.launcher.opened,0)
    def test_host_failures_are_sanitized_and_fail_closed(self):
        for step in ['coverage','freeze','sealed']:
            with self.subTest(step=step):
                gate=Gate(Path(self.tmp.name)/f'{step}.sqlite');gate.bootstrap()
                host=SyntheticHost();host.fail_at=step
                launcher=SyntheticLauncher(gate);c=Coordinator(gate,launcher,host)
                self.denied(Code.HOST_FAILURE,c.start)
                self.assertEqual(gate.snapshot().state,State.BLOCKED)
                self.assertEqual(launcher.opened,0)
                self.assertNotIn('SYNTHETIC_SECRET',str(gate.audit()))
    def test_launch_exception_never_echoes_secret(self):
        self.launcher.fail_open=True
        self.denied(Code.HOST_FAILURE,self.c.start)
        self.assertNotIn('SECRET',str(self.gate.audit()))
        self.assertEqual(self.gate.snapshot().state,State.BLOCKED)
    def test_resume_failure_keeps_gate_blocked(self):
        self.c.start();self.host.fail_at='resume'
        self.denied(Code.HOST_FAILURE,lambda:self.c.finish('done',safe_to_resume=True))
        self.assertEqual(self.gate.snapshot().state,State.BLOCKED)
        self.denied(Code.GATE_CLOSED,lambda:self.gate.invoke(lambda _:None))
    def test_audit_contains_only_time_and_state(self):
        self.c.start();self.c.finish('done',safe_to_resume=True)
        self.assertEqual([s for _,s in self.gate.audit()],['NORMAL','PREPARING','PRIVATE','RESUMING','NORMAL'])
        for at,state in self.gate.audit(): self.assertIsInstance(at,float);self.assertIn(state,State._value2member_map_)
        con=sqlite3.connect(self.path)
        self.assertEqual([r[1] for r in con.execute('PRAGMA table_info(audit)')],['at','state'])
        con.close()
    def test_storage_error_is_failure_not_normal(self):
        self.c.start()
        self.path.unlink()
        # Re-open of a missing gate is BLOCKED, never auto-NORMAL.
        other=Gate(self.path)
        self.assertEqual(other.snapshot().state,State.BLOCKED)
        self.denied(Code.INVALID_ACTION,lambda:self.c.finish('done',safe_to_resume=True))
        self.denied(Code.CONTROLLER_BUSY,lambda:self.c.finish('cancel',safe_to_resume=True))
        self.assertEqual(other.snapshot().state,State.BLOCKED)
    def test_cli_without_host_never_launches_or_writes(self):
        proc=subprocess.run([sys.executable,'-B',str(SCRIPTS/'private_mode.py'),'--check'],cwd=self.tmp.name,capture_output=True,text=True,timeout=5)
        self.assertEqual(proc.returncode,3)
        self.assertIn('HOST_UNAVAILABLE',proc.stdout)
        self.assertNotIn('PRIVATE"',proc.stdout)
        self.assertEqual({p.name for p in Path(self.tmp.name).iterdir()},{'gate.sqlite'})
    def test_invalid_cli_values_not_echoed(self):
        marker = 'FICTIONAL_CREDENTIAL_7930'
        for arguments in [["--password=" + marker], ["--check=" + marker], [marker]]:
            with self.subTest(arguments=arguments):
                proc=subprocess.run([sys.executable,'-B',str(SCRIPTS/'private_mode.py'),*arguments],
                    cwd=self.tmp.name,capture_output=True,text=True,timeout=5)
                self.assertEqual(proc.returncode,2)
                self.assertNotIn(marker,proc.stdout+proc.stderr)
                self.assertIn('INVALID_ACTION',proc.stdout)

    def test_windows_launcher_rejects_other_platform(self):
        if os.name=='nt': self.skipTest('Linux-only negative test')
        launcher=WindowsKeePassXC(Path('/tmp/KeePassXC.exe'),'a'*64,'A'*40)
        self.denied(Code.UNSUPPORTED_PLATFORM,launcher.verify)
    def test_launcher_no_args_no_stdin_no_secret_environment(self):
        launcher=WindowsKeePassXC(Path('/trusted/KeePassXC.exe'),'a'*64,'A'*40)
        with patch.object(launcher,'verify') as verify, patch('private_mode.subprocess.Popen') as popen, patch.dict(os.environ,{'VERY_SECRET':'fixture','QT_PLUGIN_PATH':'bad','PYTHONPATH':'bad'}):
            launcher.open()
            verify.assert_called_once()
            args,kw=popen.call_args
            self.assertEqual(args[0],['/trusted/KeePassXC.exe'])
            self.assertFalse(kw['shell']);self.assertEqual(kw['stdin'],subprocess.DEVNULL)
            for key in ['VERY_SECRET','QT_PLUGIN_PATH','PYTHONPATH']: self.assertNotIn(key,kw['env'])
            self.assertEqual(kw['stdout'],subprocess.DEVNULL);self.assertEqual(kw['stderr'],subprocess.DEVNULL)
    def test_cancellation_during_preparation_prevents_launch(self):
        self.host.freeze_callback=self.c.request_cancel
        self.denied(Code.CANCEL_REQUESTED,self.c.start)
        self.assertEqual(self.gate.snapshot().state,State.CANCELLED)
        self.assertEqual(self.launcher.opened,0)
    def test_second_request_after_done_is_possible_but_new_epoch(self):
        self.c.start();old=self.gate.snapshot().epoch
        self.c.finish('done',safe_to_resume=True);self.c.start()
        self.assertGreater(self.gate.snapshot().epoch,old)
        self.assertEqual(self.launcher.opened,2)
    def test_repeated_start_cannot_double_launch(self):
        self.c.start();self.denied(Code.CONTROLLER_BUSY,self.c.start)
        self.assertEqual(self.launcher.opened,1)
    def test_preparing_state_cannot_jump_directly_to_normal(self):
        owner=self.gate.begin()
        self.denied(Code.INVALID_STATE,lambda:self.gate.transition(owner,State.NORMAL))
    def test_foreign_controller_cannot_resume(self):
        self.c.start()
        self.denied(Code.CONTROLLER_BUSY,lambda:self.gate.transition('forged',State.RESUMING))
        self.assertEqual(self.gate.snapshot().state,State.PRIVATE)


if __name__=='__main__': unittest.main()
