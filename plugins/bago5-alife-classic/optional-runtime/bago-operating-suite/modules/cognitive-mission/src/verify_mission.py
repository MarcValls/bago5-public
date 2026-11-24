"""Check the completed integrated mission from raw, candidate-bound evidence."""
import argparse,json,hashlib,os
from pathlib import Path

def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(work):
 checks=[]
 def check(name,ok,detail=None):checks.append({'id':name,'status':'PASS' if ok else 'FAIL','detail':detail})
 freeze=load(work/'evidence/INPUT_FREEZE.json');cfg=load(work/'CONFIG.json')
 check('frozen_candidate_unchanged',all(sha(work/p)==s for p,s in freeze['candidate'].items()))
 check('evaluator_unchanged',sha(cfg['evaluator_path'])==freeze['oracle_sha256'])
 results=[load(work/'evidence'/f'cycle-{i:02}-result.json') for i in range(1,4)]
 check('three_actual_processes',len({x['pid'] for x in results})==3,[x['pid'] for x in results])
 check('product_failure_then_repair_then_recovery',[x['product_status'] for x in results]==['FAIL','PASS','PASS'])
 check('all_twelve_functional_criteria',results[1]['observation']['passed']==12 and results[2]['observation']['passed']==12)
 check('memory_accumulates_across_processes',[x['memory_entries'] for x in results]==[1,2,3])
 check('no_learning_claim',all(x['learning_status']=='NOT_EVALUATED' for x in results))
 stages=['OBSERVE','DETECT','PROPOSE','SELECT','ACT','VALIDATE','RECORD','REFLECT','EVOLVE','REMEMBER','DISTILL','EMIT']
 for i,r in enumerate(results,1):
  trace=load(work/'evidence'/f'cycle-{i:02}-trace.json')
  check(f'cycle{i}_native_spiral_order',r['stages']==stages)
  turns=[e for e in trace if e['kind']=='COGNITIVE_TURN']
  check(f'cycle{i}_actual_session_context_and_spbe',len(turns)==2 and all(e['spbe_result']['kind']=='PROPOSAL_READY' and e['context_envelope_id'] and e['reflexive_question'] for e in turns))
  check(f'cycle{i}_typed_context_bound',all(e.get('context_binding',{}).get('sha256')==e['packet_sha256'] and e['context_binding']['authority']=='data_only_no_permissions' for e in turns))
  selected=[e for e in trace if e['kind']=='PLAN_SELECTED']
  check(f'cycle{i}_host_response_consumed',len(selected)==1 and selected[0]['proposal_sha256']==turns[0]['response_sha256'])
  executions=[e for e in trace if e['kind']=='GATEWAY_EXECUTION']
  check(f'cycle{i}_real_process_adapter',any(e['effect_id']=='process.execute' and e['result']['executed'] and e['authorization']['state']=='consumed' for e in executions))
  check(f'cycle{i}_grounded_reflection',load(work/'evidence'/f'cycle-{i:02}-reflect-session.json')['response']['observed_product']==r['product_status'])
  if i==2:check('native_authorized_material_write',any(e['effect_id']=='filesystem.write' and e['result']['executed'] and e['authorization']['state']=='consumed' for e in executions))
  if i==3:check('recovery_does_not_reapply_patch',not any(e['effect_id']=='filesystem.write' for e in executions))
 check('untargeted_files_preserved',all(sha(work/'project'/n)==s for n,s in cfg['immutable_project_files'].items()))
 # Hash-bound mailbox exchanges: no merely written command is counted as execution.
 for request_path in sorted((work/'mailbox').glob('*.request.json')):
  request=load(request_path);response=load(request_path.with_name(request_path.name.replace('.request.','.response.')))
  h=hashlib.sha256(json.dumps(request,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
  check('mailbox_binding_'+request['id'],response['request_sha256']==h and response['request_id']==request['id'] and response['mode']==cfg['host_mode'])
 report={'schema':'bago.cognitive-mission.verification.v1','status':'PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',
         'checks':checks,'passed':sum(c['status']=='PASS' for c in checks),'total':len(checks),'host_mode':cfg['host_mode'],
         'scope':'integrated host-mediated mission; not learning, not standalone autonomy, not native PEC binding'}
 (work/'evidence/FINAL_VERIFICATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 (work/'evidence/FINAL_CHECK_RESULT.json').write_text(json.dumps({'schema':'bago.suite.check-result.v1','status':report['status'],'coverage':'COMPLETE','findings':[] if report['status']=='PASS' else [c['id'] for c in checks if c['status']!='PASS']},ensure_ascii=False,indent=2))
 print(json.dumps(report,ensure_ascii=False));return 0 if report['status']=='PASS' else 1
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);a=ap.parse_args();raise SystemExit(main(a.work.resolve()))
