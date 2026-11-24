"""Five-incident regression battery; self-contained standard-library tests."""
from __future__ import annotations
import argparse
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PACKAGE))
import goal_bridge as b

P=argparse.ArgumentParser(add_help=False)
P.add_argument('--suite',type=Path, default=PACKAGE.parent/'bago-operating-suite')
P.add_argument('--base',type=Path, default=PACKAGE.parent/'BAGO5os_1.4.7_CONTEXT_LIFECYCLE_NATIVE_RC2_INSTALLED.zip')
A, _ = P.parse_known_args()
SUITE = A.suite.resolve()
BASE = A.base.resolve()
TaskStore,IDENTITY = b._import_suite(SUITE)


def cli(workspace, states, *args):
    cmd = [sys.executable, '-B', str(PACKAGE/'goal_bridge.py'), '--workspace', str(workspace),
           '--state-root', str(states), '--suite', str(SUITE), *args]
    p = subprocess.run(cmd, text=True, capture_output=True, timeout=30, env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    try: payload=json.loads(p.stdout)
    except ValueError: raise AssertionError(f'CLI failed: {p.stderr} {p.stdout}')
    return p.returncode,payload

class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='BAGO GOALS RC2 ')  # Windows path with spaces
        self.addCleanup(self.temp.cleanup)
        self.parent=Path(self.temp.name)
        self.workspace=self.parent/'my project with spaces'
        self.workspace.mkdir()
        (self.workspace/'candidate.txt').write_text('frozen candidate',encoding='utf-8')
        self.states=self.parent/'task stores'
        self.states.mkdir()
        self.docs=self.workspace/'.bago'/'goals'
        self.docs.mkdir(parents=True)

    def goal(self, goal='G1', status='OPEN', task='taskG1', check='codex_exec', text='Fix that & verify | never assume.'):
        data={'schema':'bago.goals.document.v1','goal_id':goal,'status':status,
              'text':text,'task_dir':task,'check_id':check}
        p=self.docs/f'{goal}.goal.json'
        p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
        return p

    def task(self, goal='G1', task='taskG1', open_round=False):
        plan={'schema':'bago.suite.task.plan.v1','mission_id':goal,'candidate_id':'candidateX',
              'operation':'VERIFY','scope':['candidate.txt'],'max_rounds':3,
              'checks':[{'id':'codex_exec','kind':'execution','mandatory':True,'depends_on':[],'artifacts':[]}]}
        store=TaskStore(self.states/task, IDENTITY, lambda:IDENTITY)
        store.initialize(self.workspace,plan)
        if open_round:store.open_round()
        return store

    def test_F01_document_DONE_but_TaskStore_OPEN_remains_pending_and_blocks_run(self):
        self.goal('G1','DONE');self.task()
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,3)
        self.assertEqual(x['pending_count'],1)
        self.assertEqual(x['pending'][0]['effective_state'],'DOCUMENT_DONE_TASKSTORE_OPEN')
        code,x=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(sys.executable))
        self.assertEqual(code,3)
        self.assertEqual(x['status'],'BLOCKED')
        self.assertEqual(self.task_status('taskG1')['runs'],[])

    def test_F01_document_PAUSED_task_OPEN_not_discarded(self):
        self.goal('G1','PAUSED');self.task()
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,0)
        self.assertEqual(x['pending_count'],1)
        self.assertEqual(x['pending'][0]['effective_state'],'PENDING')
        code,y=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(sys.executable))
        self.assertEqual(code,3)
        self.assertEqual(y['status'],'BLOCKED')

    def test_F02_orphan_STOP_outranks_document_and_prevents_other_goal_execution(self):
        self.goal('G1');self.task('G1','taskG1',open_round=True)
        self.task('orphan','orphan-state')  # no GOAL document
        TaskStore(self.states/'orphan-state',{}).stop('user STOP')
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,3)
        self.assertTrue(x['global_stop'])
        self.assertEqual(x['pending_count'],2)
        self.assertTrue(any(z['document_status']=='MISSING' and z['control']=='STOPPED' for z in x['pending']))
        code,y=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(sys.executable))
        self.assertEqual(code,3)
        self.assertIn('STOP',y['reason'])
        self.assertFalse(self.task_status('taskG1')['runs'])

    def test_F01_unrelated_document_ledger_drift_blocks_other_goal_run(self):
        self.goal('G1');self.task('G1','taskG1',open_round=True)
        self.goal('G2',status='DONE',task='taskG2');self.task('G2','taskG2')
        code,x=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(sys.executable))
        self.assertEqual(code,3)
        self.assertIn('inconsistency',x['reason'])
        self.assertEqual(self.task_status('taskG1')['runs'],[])

    def test_F02_STOP_without_goal_document_or_suite_identity(self):
        self.task('orphan','orphan-state')
        # STOP must not read a broken GOAL JSON document, nor hash the suite.
        (self.docs/'broken.goal.json').write_text('{not json',encoding='utf-8')
        code,x=cli(self.workspace,self.states,'stop','--reason','Stop now')
        self.assertEqual(code,0)
        self.assertEqual(x['stopped'],['orphan-state'])
        self.assertEqual(self.task_status('orphan-state')['control'],'STOPPED')

    def test_F03_windows_portable_command_preserves_argv_and_does_not_embed_prompt(self):
        goal=self.goal('G1',text='Unexpected & | > && %COMSPEC% "prompt"')
        self.task()
        argv=b.build_codex_command(sys.executable,str(goal),'a'*64)
        self.assertEqual(argv[0],sys.executable)
        self.assertIn('codex_worker.py',argv[2])
        self.assertEqual(argv[argv.index('--goal')+1],str(goal))
        self.assertNotIn('Unexpected', ' '.join(argv))
        self.assertNotIn('shell', ' '.join(argv))
        if os.name=='nt':
            self.assertIn('"',subprocess.list2cmdline(argv))  # space-safe Windows quoting

    def test_F03_codex_worker_REAL_mock_process_reads_complete_prompt_from_stdin(self):
        goal=self.goal('G1',text='Intención con tildes & símbolos | < > $HOME')
        mock=self.parent/('fake codex.cmd' if os.name=='nt' else 'fake codex')
        if os.name=='nt':
            mock.write_text('@echo off\r\nmore\r\nexit /b 0\r\n',encoding='utf-8')
        else:
            mock.write_text('#!/bin/sh\ncat\nexit 0\n',encoding='utf-8');mock.chmod(0o755)
        expected=b._sha(goal.read_bytes())
        cmd=b.build_codex_command(str(mock),str(goal),expected)
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Intención con tildes',p.stdout)
        self.assertIn('& símbolos | < >',p.stdout)

    def test_F03_taskstore_governs_REAL_mock_codex_run(self):
        self.goal('G1')
        self.task(open_round=True)
        mock=self.parent/('mock codex.cmd' if os.name=='nt' else 'mock codex')
        if os.name=='nt':
            mock.write_text('@echo off\r\nmore >nul\r\necho CODEX_MOCK_OK\r\nexit /b 0\r\n',encoding='utf-8')
        else:
            mock.write_text('#!/bin/sh\ncat >/dev/null\necho CODEX_MOCK_OK\nexit 0\n',encoding='utf-8'); mock.chmod(0o755)
        code,x=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(mock))
        self.assertEqual(code,0,x)
        self.assertEqual(x['status'],'PASS')
        state=self.task_status('taskG1')
        self.assertEqual(len(state['runs']),1)
        self.assertEqual(state['checks'][0]['outcome'],'PASS')

    def test_F03_worker_failure_is_recorded_as_FAIL_not_false_PASS(self):
        self.goal('G1')
        self.task(open_round=True)
        mock=self.parent/('reject codex.cmd' if os.name=='nt' else 'reject codex')
        if os.name=='nt':
            mock.write_text('@echo off\r\nexit /b 9\r\n',encoding='utf-8')
        else:
            mock.write_text('#!/bin/sh\nexit 9\n',encoding='utf-8'); mock.chmod(0o755)
        code,x=cli(self.workspace,self.states,'run','--goal','G1','--approve-run','--codex',str(mock))
        self.assertEqual(code,1,x)
        self.assertEqual(x['status'],'FAIL')
        self.assertEqual(self.task_status('taskG1')['checks'][0]['outcome'],'FAIL')

    def test_F04_cmd_launcher_propagates_child_exit_code(self):
        for name in ('INICIAR_GOALS.cmd','VERIFICAR_GOALS.cmd'):
            data=(PACKAGE/name).read_text(encoding='utf-8').lower()
            self.assertIn('set "result=%errorlevel%"',data)
            self.assertIn('exit /b %result%',data)
            self.assertNotIn('exit /b 0',data)
        if os.name=='nt':
            p=subprocess.run(['cmd.exe','/d','/c',str(PACKAGE/'INICIAR_GOALS.cmd'),
                               '--workspace',str(self.workspace),'--state-root',str(self.states),
                               '--suite',str(SUITE),'run','--goal','missing'],capture_output=True,text=True,timeout=35)
            self.assertEqual(p.returncode,3)

    def test_F05_sqlite_handles_release_across_four_failed_transient_scenarios(self):
        for idx in range(4):
            name=f'task_{idx}'
            self.task(f'G{idx}',name)
            db=self.states/name/'control.sqlite3'
            # Each diagnostic has an error, but never retains an sqlite handle after return.
            code,_=cli(self.workspace,self.states,'run','--goal','missing','--approve-run')
            self.assertEqual(code,3)
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute('PRAGMA quick_check').fetchone()[0],'ok')
            # On Windows this would raise WinError 32 if any SQLite handle remained.
            db.rename(self.states/name/'control_renamed.sqlite3')
            (self.states/name/'control_renamed.sqlite3').rename(db)

    def test_ALL_goals_resumed_as_summary_with_pending_and_orphan(self):
        self.goal('G1');self.task()
        self.goal('G2',task='taskG2');self.task('G2','taskG2')
        self.task('G3','taskG3')
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,0)
        self.assertEqual(x['pending_count'],3)
        self.assertEqual({a['mission_id'] for a in x['pending']},{'G1','G2','G3'})
        self.assertFalse(x['automatic_resume'])

    def test_UNINDEXED_markdown_goal_is_visible_but_not_executable(self):
        (self.docs/'legacy.md').write_text('# Goal pending\n',encoding='utf-8')
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,3)
        self.assertEqual(x['pending_count'],1)
        self.assertEqual(x['pending'][0]['effective_state'],'UNINDEXED_DOCUMENT')

    def test_wrong_mission_binding_is_blocked(self):
        self.goal('G1');self.task('OTHER','taskG1')
        code,x=cli(self.workspace,self.states,'resume')
        self.assertEqual(code,3)
        self.assertEqual(x['pending'][0]['effective_state'],'BINDING_MISMATCH_BLOCKED')

    def test_explicit_resume_required_STOP_persistent(self):
        self.goal('G1');self.task()
        st=TaskStore(self.states/'taskG1',IDENTITY,lambda:IDENTITY)
        st.stop('user')
        cli(self.workspace,self.states,'resume')
        self.assertEqual(self.task_status('taskG1')['control'],'STOPPED')
        code,x=cli(self.workspace,self.states,'task-resume','--goal','G1','--reason','Explicit approval')
        self.assertEqual(code,0,x)
        self.assertEqual(self.task_status('taskG1')['control'],'ACTIVE')

    def test_unapproved_execution_does_not_create_runs(self):
        self.goal('G1');self.task(open_round=True)
        code,x=cli(self.workspace,self.states,'run','--goal','G1')
        self.assertEqual(code,3)
        self.assertEqual(self.task_status('taskG1')['runs'],[])

    def test_baseline_skill_keeps_exact_RC2_identity_and_archived_bytes(self):
        from suite_identity import current_identity
        self.assertEqual(current_identity(SUITE),IDENTITY)
        self.assertEqual(IDENTITY['payload_files'],600)
        self.assertEqual(IDENTITY['release_id'],'BAGO-SUITE-147-BAGO-SKILL-RC2')
        with zipfile.ZipFile(BASE) as archive:
            for r in archive.namelist():
                if r.endswith('/'):continue
                p=SUITE.parent/r
                if not p.is_file():
                    self.fail('Missing original file '+r)
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),hashlib.sha256(archive.read(r)).hexdigest(),r)

    def task_status(self, task):
        return TaskStore(self.states/task,{}).status()


if __name__=='__main__':
    unittest.main(argv=[sys.argv[0]],verbosity=2)
