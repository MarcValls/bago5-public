"""Focused fail-closed tests. These fixtures do not count as live reasoning."""
from pathlib import Path
import sys,os,json,hashlib,tempfile,unittest,threading,time,shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT))
import mission_runtime as m
import run_mission as runner

class AdapterControls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory(prefix='cog-controls-')
  cls.work=Path(cls.tmp.name)/'test'
  skill=Path(os.environ.get('COG_SKILL_ROOT',str(ROOT.parents[1])))
  runner.init(cls.work,skill,'live')
  cls.cfg=m.load(cls.work/'CONFIG.json');suite=Path(cls.cfg['suite'])
  m.configure(suite,cls.work)
  import session_utils
  session_utils.ADAPTER_REGISTRY['cognitive-host']=m.host_adapter_class()
  from session_manager import SessionManager
  class S(m.MissionContextMixin, SessionManager):
   @staticmethod
   def _mirror_session_root(sid):return cls.work/'mirrors'/sid
  cls.session=S(session_id=cls.cfg['session_id'],provider='cognitive-host',model='current-chatgpt-host',base_path=str(cls.work/'project'),state_root=str(cls.work/'user/state'),system_prompt='Controls only; no model call',require_project_identity=True)
  cls.authority=m.MissionAuthority(cls.session,cls.work,m.Trace(cls.work,0))
 @classmethod
 def tearDownClass(cls): cls.tmp.cleanup()
 def test_allow_registered_read(self):
  self.authority._admit('filesystem.read',{'path':'config_manager.py'},{})
 def test_deny_path_escape(self):
  with self.assertRaises(m.MissionError):self.authority._admit('filesystem.read',{'path':'../CONFIG.json'},{})
 def test_deny_protected_write(self):
  with self.assertRaises(m.MissionError):self.authority._admit('filesystem.write',{'path':'REQUIREMENTS.md','expected_sha256':m.file_sha(self.work/'project/REQUIREMENTS.md')},{'content':'pass\n'})
 def test_deny_stale_write(self):
  p=self.work/'project/config_manager.py';before=p.read_bytes()
  with self.assertRaisesRegex(m.MissionError,'stale_file'):self.authority._admit('filesystem.write',{'path':'config_manager.py','expected_sha256':'0'*64},{'content':'pass\n'})
  self.assertEqual(before,p.read_bytes())
 def test_deny_syntax_error(self):
  p=self.work/'project/config_manager.py'
  with self.assertRaises(SyntaxError):self.authority._admit('filesystem.write',{'path':'config_manager.py','expected_sha256':m.file_sha(p)},{'content':'def broken(:\n'})
 def test_deny_unknown_effect(self):
  with self.assertRaises(m.MissionError):self.authority._admit('network.send',{}, {})
 def test_deny_unregistered_command(self):
  with self.assertRaises(m.MissionError):self.authority._admit('process.execute',{'command':'echo false','cwd':str(self.work/'project')},{})
 def test_deny_changed_evaluator(self):
  p=Path(self.cfg['evaluator_path']);old=p.read_bytes()
  try:
   p.write_bytes(old+b'\n# identity change\n')
   with self.assertRaisesRegex(m.MissionError,'evaluator_identity'):self.authority._admit('process.execute',{'command':self.cfg['evaluator_command'],'cwd':str(self.session.project_root)},{})
  finally:p.write_bytes(old)
 def test_deny_changed_grant(self):
  p=self.work/'HOST_GRANT.json';old=p.read_bytes()
  try:
   p.write_bytes(old+b' ')
   with self.assertRaisesRegex(m.MissionError,'grant_changed'):self.authority._admit('filesystem.read',{'path':'config_manager.py'},{})
  finally:p.write_bytes(old)
 def test_deny_missing_native_response_fields(self):
  with self.assertRaises(m.MissionError):m.validate_response({'confidence':1,'proposed_changes':[]})
 def test_deny_symlink(self):
  p=self.work/'project/config_manager.py';old=p.read_bytes();other=self.work/'outside.py';other.write_bytes(old)
  try:
   p.unlink();p.symlink_to(other)
   with self.assertRaises(m.MissionError):m.safe_file(self.work/'project','config_manager.py',m.FILES)
  finally:p.unlink();p.write_bytes(old)
 def test_native_single_use_permit(self):
  from execution_gateway import ExecutionContext
  result,req,approved=self.authority.execute('filesystem.read',{'path':'config_manager.py'},{})
  self.assertTrue(result['executed'])
  from authorization_boundary import AuthorizationError
  with self.assertRaises(AuthorizationError):
   self.authority.gateway.execute(permit_token=approved['permit']['token'],request=req,context=ExecutionContext(manager=self.session))
 def test_native_stop_resume(self):
  cfg=m.load(self.work/'CONFIG.json')
  from suite_control import TaskStore
  store=TaskStore(Path(cfg['suite_control']),{})
  # Use native public CLI so the Suite identity is supplied, not bypassed.
  r=runner.suite_call(self.work,['stop','--reason','Negative control'])
  self.assertEqual(r['result']['status'],'PASS')
  with self.assertRaises(m.MissionError):m.check_control(self.work)
  self.assertEqual(runner.suite_call(self.work,['resume','--reason','Explicit test resume'])['result']['status'],'PASS')
  m.check_control(self.work)
 def test_native_classifier_remains_active(self):
  before=set((self.work/'mailbox').glob('*.request.json'))
  answer=self.session.send('Inspecciona credentials.json',route_info={'kind':'chat'})
  self.assertTrue(self.session.last_code_task['blocked'])
  self.assertIn('dangerous_or_sensitive_request',self.session.last_code_task['reasons'])
  self.assertEqual(before,set((self.work/'mailbox').glob('*.request.json')))
 def test_context_rejects_unbound_packet(self):
  self.session._mission_packet={'data':'observation'}
  self.session._mission_packet_sha256='0'*64
  with self.assertRaisesRegex(m.MissionError,'mission_packet_identity_mismatch'):
   self.session._build_context_envelope()
 def _bad_mailbox(self,kind):
  os.environ['COG_PHASE']='negative-'+kind
  adapter=m.host_adapter_class()()
  results=[]
  def invoke():
   try:adapter.chat([{'role':'user','content':'Negative control only'}],'current-chatgpt-host')
   except Exception as e:results.append(str(e))
  t=threading.Thread(target=invoke);t.start();p=self.work/'mailbox'/('negative-'+kind+'-01.request.json')
  for _ in range(100):
   if p.exists():break
   time.sleep(.05)
  self.assertTrue(p.exists());q=m.load(p)
  reply={'schema':'bago.cognitive.host-response.v1','request_id':q['id'],'request_sha256':m.digest(q),'mode':'live','content':{}}
  if kind=='hash':reply['request_sha256']='0'*64
  if kind=='mode':reply['mode']='replay'
  m.save(p.with_name(p.name.replace('.request.','.response.')),reply)
  t.join(3);self.assertFalse(t.is_alive());return results
 def test_mailbox_wrong_binding(self):self.assertIn('host_reply_binding_mismatch',self._bad_mailbox('hash')[0])
 def test_mailbox_live_replay_separation(self):self.assertIn('host_live_replay_mode_mismatch',self._bad_mailbox('mode')[0])
 def test_mailbox_invalid_contract(self):self.assertIn('invalid_native_task_contract',self._bad_mailbox('contract')[0])

if __name__=='__main__':unittest.main(verbosity=2)
