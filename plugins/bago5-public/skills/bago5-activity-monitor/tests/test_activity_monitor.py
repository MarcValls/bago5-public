import importlib.util,json,hashlib,os,sqlite3,subprocess,sys,tempfile,time,unittest
from pathlib import Path
script=Path(__file__).resolve().parents[1]/'scripts/activity_monitor.py'
spec=importlib.util.spec_from_file_location('activity_monitor',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class MonitorTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.state=self.root/'.bago5-team/runtime';self.state.mkdir(parents=True)
 def write_state(self,lifecycle='ACTIVE'):
  (self.state/'state.json').write_text(json.dumps({'mission':{'mission_id':'M1','operation':'AUDIT'},'lifecycle':lifecycle,'work_status':{'W1':{'status':'CLAIMED','agent':'worker'}},'executions':{'E1':{'state':'RUNNING','pid':999999,'result':'NOT_RUN'}},'candidate_id':'fixture'}))
 def digest(self):return {p.relative_to(self.root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.rglob('*') if p.is_file()}
 def test_registered_active_does_not_imply_process_alive(self):
  self.write_state();r=m.snapshot(self.root,'team','unused',30,[]);self.assertEqual(r['registered_activity']['state']['lifecycle'],'ACTIVE');self.assertEqual(r['observed_processes'],[]);self.assertIn('NOT_VERIFIED',r['registered_activity']['integrity'])
 def test_pause_and_events_read_only(self):
  self.write_state('PAUSED');(self.state/'events.jsonl').write_text('{"at":"now","kind":"PAUSED"}\n{partial');before=self.digest();r=m.snapshot(self.root,'team','unused',30,[]);self.assertEqual(r['registered_activity']['state']['lifecycle'],'PAUSED');self.assertEqual(r['registered_activity']['events'][0]['kind'],'PAUSED');self.assertTrue(r['registered_activity']['warnings']);self.assertEqual(before,self.digest())
 def test_malformed_state_not_silent_empty(self):
  (self.state/'state.json').write_text('{broken');r=m.snapshot(self.root,'team','unused',30,[]);self.assertEqual(r['registered_activity']['availability'],'ERROR')
 def test_missing_state_no_creation(self):
  before=self.digest();r=m.snapshot(self.root,'team','unused',30,[]);self.assertEqual(r['registered_activity']['availability'],'NO_STATE');self.assertEqual(before,self.digest())
 def test_path_escape_rejected(self):
  r=m.snapshot(self.root,'suite','../escape.sqlite3',30,[]);self.assertEqual(r['registered_activity']['availability'],'ERROR')
 def test_symbolic_source_rejected(self):
  outside=self.root/'source.json';outside.write_text('{}')
  try:(self.state/'state.json').symlink_to(outside)
  except OSError:self.skipTest('Host cannot create symbolic link')
  self.assertEqual(m.snapshot(self.root,'team','unused',30,[])['registered_activity']['availability'],'ERROR')
 def database(self):
  p=self.root/'control.sqlite3';con=sqlite3.connect(p);con.executescript('CREATE TABLE meta(key TEXT,value TEXT);CREATE TABLE checks(id TEXT,outcome TEXT,consumed INTEGER);CREATE TABLE runs(id TEXT,check_id TEXT,pid INTEGER,started TEXT,finished TEXT,returncode INTEGER,state TEXT,interruption TEXT,receipt TEXT);CREATE TABLE assignments(id TEXT,check_id TEXT,worker TEXT,round INTEGER,state TEXT,interruption TEXT);CREATE TABLE events(seq INTEGER,at TEXT,action TEXT);');con.executemany('INSERT INTO meta VALUES (?,?)',[('plan',json.dumps({'mission_id':'SUITE1','operation':'AUDIT'})),('control',json.dumps('STOPPED'))]);con.execute("INSERT INTO checks VALUES ('C1','FAIL',0)");con.commit();con.close();return p
 def test_sqlite_views_rejected(self):
  db=self.database();conn=sqlite3.connect(db);conn.executescript('DROP TABLE checks;CREATE VIEW checks AS WITH RECURSIVE c(x) AS (VALUES(0) UNION ALL SELECT x+1 FROM c) SELECT x AS id, x AS outcome,x AS consumed FROM c;');conn.close();r=m.snapshot(self.root,'suite','control.sqlite3',30,[]);self.assertEqual(r['registered_activity']['availability'],'ERROR')
 def test_pid_overflow_rejected(self):
  with self.assertRaises(ValueError):m.process_snapshot(os.getpid()+4294967296)
 def test_suite_read_only_snapshot(self):
  self.database();before=self.digest();r=m.snapshot(self.root,'suite','control.sqlite3',30,[]);self.assertEqual(r['registered_activity']['mission']['mission_id'],'SUITE1');self.assertEqual(r['registered_activity']['tasks'][0]['outcome'],'FAIL');self.assertEqual(before,self.digest())
 def test_suite_live_journal_not_ignored(self):
  self.database();(self.root/'control.sqlite3-wal').write_bytes(b'not empty');r=m.snapshot(self.root,'suite','control.sqlite3',30,[]);self.assertEqual(r['registered_activity']['availability'],'ERROR')
 def test_real_process_start_exit_and_identity(self):
  proc=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);self.addCleanup(lambda:proc.poll() is None and proc.kill())
  a=m.process_snapshot(proc.pid);self.assertIn(a['observed_state'],['ALIVE','EXISTS']);self.assertIn('UNVERIFIED',a['mission_binding'])
  if os.name=='nt':self.assertIn('instance_key',a);self.assertIn('cpu_seconds',a);self.assertIn('started_at',a)
  proc.terminate();proc.wait(timeout=5);b=m.process_snapshot(proc.pid);self.assertIn(b['observed_state'],['NOT_FOUND','EXITED'])
 def test_watch_bounded_real_cli(self):
  self.write_state();before=self.digest();p=subprocess.run([sys.executable,'-B',str(script),'--root',str(self.root),'--format','json','--pid',str(os.getpid()),'--watch-seconds','0.6','--interval','0.5'],capture_output=True,text=True,timeout=8);self.assertEqual(p.returncode,0,p.stderr);frames=[json.loads(s) for s in p.stdout.splitlines()];self.assertGreaterEqual(len(frames),2);self.assertLessEqual(len(frames),4);self.assertEqual(before,self.digest())
 def test_instance_change_not_cpu_continuity(self):
  if os.name!='nt':self.skipTest('Windows instance identity')
  prior=m.snapshot(self.root,'team','unused',30,[os.getpid()]);prior['observed_processes'][0]['instance_key']='old-instance'
  current=m.snapshot(self.root,'team','unused',30,[os.getpid()],prior);p=current['observed_processes'][0];self.assertTrue(p['pid_reused']);self.assertNotIn('cpu_percent_one_core',p)
 def test_invalid_pid_and_duration_rejected(self):
  for extra in [['--pid','0'],['--pid','4294967296'],['--watch-seconds','61']]:
   p=subprocess.run([sys.executable,'-B',str(script),'--root',str(self.root),*extra],capture_output=True,text=True,timeout=5);self.assertEqual(p.returncode,2)
 def test_truncation_visible(self):
  self.write_state();r=m.snapshot(self.root,'team','unused',1,[]);text=m.markdown(r);self.assertIn('rows_limited_to',text);self.assertIn('total_tasks',text)
  self.database();r=m.snapshot(self.root,'suite','control.sqlite3',1,[]);self.assertEqual(r['registered_activity']['total_tasks'],1);self.assertIn('limited',r['registered_activity']['view_notice'])
 def test_markdown_separates_sources(self):
  self.write_state();t=m.markdown(m.snapshot(self.root,'team','unused',30,[]));self.assertIn('1. Misiones',t);self.assertIn('2. Procesos',t);self.assertIn('NOT_RUN',t)
if __name__=='__main__':unittest.main()
