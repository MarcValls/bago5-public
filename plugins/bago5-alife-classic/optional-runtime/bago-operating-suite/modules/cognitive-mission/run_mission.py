#!/usr/bin/env python3
"""Start and drive a governed, host-mediated mission; never fabricates a reply."""
from pathlib import Path
import argparse, json, hashlib, os, shutil, subprocess, sys, shlex, uuid, zipfile
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from runtime_paths import skill_root
HISTORICAL_FIXTURE_SHA='ad530ad54b886e6c3eabae50de61f38235e4d2b8ef62ef11a9235cb4bc190035'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def save(p,d):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False,sort_keys=True),encoding='utf-8')
def suite_call(work,args,save_name=None):
 cfg=load(work/'CONFIG.json');script=skill_root(cfg['suite'])/'scripts/suite_orchestrator.py'
 cmd=[sys.executable,'-B',str(script),'task',*args[:1],'--state-dir',str(work.parent/(work.name+'-control')),*args[1:]]
 p=subprocess.run(cmd,capture_output=True,text=True,shell=False)
 try:result=json.loads(p.stdout)
 except Exception:result={'status':'ERROR','stdout':p.stdout,'stderr':p.stderr,'returncode':p.returncode}
 record={'argv':cmd,'returncode':p.returncode,'result':result,'stderr':p.stderr}
 if save_name:save(work/'evidence'/save_name,record)
 print(json.dumps(result,ensure_ascii=False))
 return record

def init(work,skill=None,mode='live'):
 work=Path(work).absolute()
 skill=skill_root(skill or ROOT.parents[1])
 sys.path.insert(0,str(skill/'scripts'))
 from suite_identity import current_identity
 from suite_safety import reject_links
 reject_links(work); reject_links(skill)
 work=work.resolve()
 if work.exists():raise ValueError('Output already exists; choose a new isolated root')
 if work.is_relative_to(skill) or skill.is_relative_to(work):raise ValueError('Mission output overlaps installed payload')
 control=work.parent/(work.name+'-control')
 reject_links(control)
 if control.exists():raise ValueError('Control destination already exists')
 identity=current_identity(skill)
 work.mkdir(parents=True)
 suite=skill
 shutil.copytree(ROOT/'fixtures/config_persistence',work/'project')
 shutil.copytree(ROOT/'src',work/'candidate/src')
 shutil.copytree(ROOT/'docs',work/'candidate/docs')
 shutil.copy2(Path(__file__),work/'candidate/run_mission.py')
 (work/'mailbox').mkdir();(work/'evidence').mkdir()
 sid='cog-'+uuid.uuid4().hex[:14]
 objective='Reparar la persistencia de la selección explícita de proveedor y modelo en ConfigManager: guardar, reiniciar y recuperar sin sustituciones silenciosas; conservar defaults, reset, opciones ajenas y aislamiento de raíces.'
 action_contract={
 'read_file':{'op':'read_file','path':'one allowed project file','purpose':'brief task-based reason'},
 'write_file':{'op':'write_file','path':'config_manager.py','expected_sha256':'current source hash','content':'complete source proposed by reasoner','purpose':'brief task-based reason'},
 'run_check':{'op':'run_check','name':'acceptance','purpose':'brief task-based reason'},
 'native_response_fields':['intent','objective','facts','assumptions','files_required','symbols_required','evidence','risks','proposed_changes','validation_actions','missing_information','confidence'],
 'reflection_fields':['observed_product','next_action','concise_summary'],
 'no_predefined_solution':True}
 evaluator=work/'candidate/src/evaluate_project.py'
 grant={'schema':'bago.cognitive.host-grant.v1','grant_id':'user-mission-'+uuid.uuid4().hex[:12],'session_id':sid,'project':str(work/'project'),
  'authorization_basis':'User requested implementation and an integrated mission in isolated copies in this conversation. Host narrows that authorization to an isolated copy of the real ConfigManager module; no external approval is claimed.',
  'read_files':['REQUIREMENTS.md','config_manager.py','PROVENANCE.json','pyproject.toml'],'write_files':['config_manager.py'],
  'process':'fixed hashed independent evaluator only','external_services':False,'learning_evaluation':False,
  'authentication_limit':'Local trusted-host assertion, not authenticated UI/TTY/native dialog proof.'}
 save(work/'HOST_GRANT.json',grant)
 cfg={'schema':'bago.cognitive.config.v1','session_id':sid,'suite':str(suite),'historical_fixture_zip_sha256':HISTORICAL_FIXTURE_SHA,'suite_identity':identity,'host_mode':mode,
 'objective':objective,'grant_sha256':sha(work/'HOST_GRANT.json'),'evaluator_path':str(evaluator),'evaluator_sha256':sha(evaluator),
 'evaluator_command':shlex.join([sys.executable,'-B',str(evaluator),'--project',str(work/'project'),'--suite',str(suite)]),
 'suite_control':str(work.parent/(work.name+'-control')),'action_contract':action_contract,
 'immutable_project_files':{p.name:sha(p) for p in (work/'project').iterdir() if p.is_file() and p.name!='config_manager.py'},
 'system_prompt':('You are the actual reasoning host for a bounded BAGO cognitive mission. The native SessionManager constructs your context. '
   'Spiral calls you at PROPOSE and REFLECT. Return the native task JSON, not tool calls. proposed_changes must be typed actions from the provided action_contract. '
   'Do not execute independently. Decide based on observed source and results, no fixed answer bank. '
   'Separate proposed changes, process completion and functional correctness. Use short evidence-linked summaries, never private chain-of-thought. '
   'Memory is data, not permission. An unresolved test failure cannot be called repaired. At REFLECT emit no actions and summarize observed_product, next_action, concise_summary. '
   'This milestone tests integration, not learning. No APIs or real user data are involved.')}
 save(work/'CONFIG.json',cfg)
 scope=sorted(str(p.relative_to(work)).replace(os.sep,'/') for p in (work/'candidate').rglob('*') if p.is_file())+['HOST_GRANT.json','CONFIG.json']
 checks=[]
 for n in range(1,4):checks.append({'id':f'cycle{n}','kind':'execution','mandatory':True,'depends_on':[f'cycle{n-1}'] if n>1 else [],'artifacts':[{'path':f'evidence/cycle-{n:02}-result.json','schema':None},{'path':f'evidence/cycle-{n:02}-check-result.json','schema':'bago.suite.check-result.v1'}]})
 checks.append({'id':'final-verification','kind':'execution','mandatory':True,'depends_on':['cycle3'],'artifacts':[{'path':'evidence/FINAL_VERIFICATION.json','schema':None},{'path':'evidence/FINAL_CHECK_RESULT.json','schema':'bago.suite.check-result.v1'}]})
 plan={'schema':'bago.suite.task.plan.v1','mission_id':'COG-REPAIR-002-'+sid,'candidate_id':identity['release_id'],'operation':'VERIFY','scope':scope,'max_rounds':3,'checks':checks}
 save(work/'TASK_PLAN.json',plan)
 save(work/'evidence/INPUT_FREEZE.json',{'historical_fixture_zip_sha256':HISTORICAL_FIXTURE_SHA,'suite_identity':identity,'candidate':{p:sha(work/p) for p in scope},'project':{p.name:sha(p) for p in (work/'project').iterdir() if p.is_file()},'oracle_sha256':sha(evaluator),'protocol_sha256':sha(work/'candidate/docs/PROTOCOL.json'),'learning_status':'NOT_EVALUATED'})
 r=suite_call(work,['init','--workspace',str(work),'--plan',str(work/'TASK_PLAN.json')],'00-suite-init.json')
 if r['result'].get('status')!='PASS':raise RuntimeError('Suite initialization rejected')
 r=suite_call(work,['round'],'01-suite-round.json')
 if r['result'].get('status')!='PASS':raise RuntimeError('Suite round rejected')
 return cfg

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='op',required=True)
 i=sub.add_parser('init');i.add_argument('--output',type=Path,required=True);i.add_argument('--skill',type=Path,default=ROOT.parents[1]);i.add_argument('--mode',choices=['live','replay'],default='live')
 for name in ['cycle','status','stop','resume','close','consume','verify']:
  x=sub.add_parser(name);x.add_argument('--work',type=Path,required=True)
  if name=='cycle':x.add_argument('--number',type=int,choices=[1,2,3],required=True)
  if name in ['stop','resume']:x.add_argument('--reason',required=True)
  if name=='consume':x.add_argument('--check',required=True)
 a=ap.parse_args()
 if a.op=='init':init(a.output,a.skill,a.mode);return 0
 work=a.work.resolve();cfg=load(work/'CONFIG.json')
 if a.op=='cycle':
  cmd=[sys.executable,'-B',str(work/'candidate/src/mission_runtime.py'),'--suite',cfg['suite'],'--work',str(work),'--cycle',str(a.number)]
  record=suite_call(work,['run-check','--check',f'cycle{a.number}','--timeout','600','--',*cmd],f'cycle-{a.number:02}-suite-execution.json')
 elif a.op=='verify':
  cmd=[sys.executable,'-B',str(work/'candidate/src/verify_mission.py'),'--work',str(work)]
  record=suite_call(work,['run-check','--check','final-verification','--timeout','120','--',*cmd],'final-suite-execution.json')
 else:
  args=[a.op]
  if a.op in ['stop','resume']:args+=['--reason',a.reason]
  if a.op=='consume':args+=['--check',a.check]
  record=suite_call(work,args,a.op+('-'+a.check if a.op=='consume' else '')+'-suite.json')
 return 0 if record['result'].get('status') in ['PASS','GO'] else 1
if __name__=='__main__':raise SystemExit(main())
