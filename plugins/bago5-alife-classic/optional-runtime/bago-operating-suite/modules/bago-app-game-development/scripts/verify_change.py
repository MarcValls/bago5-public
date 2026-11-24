#!/usr/bin/env python3
"""Contract-bound differential verifier, fail closed on contradictory GO claims.

No commands are run by this verifier. External test execution is explicit (run_checks.py).
Approval exceptions require detached Ed25519 verification against a trusted host key.
If the optional cryptography package is unavailable, exceptions are DENIED (not accepted).
"""
from __future__ import annotations
import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from preservation_core import (load, dump_new, validate_schema, snapshot, evidence_hash_ok,
                               platform_name, sha_file, canonical)


def verify_approval(plan, baseline, signed_file, key_file):
    if not plan['authorized_changes']:return True, 'No exceptions requested'
    if not signed_file or not key_file:return False, 'Missing external signed approval and trusted host public key'
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.hazmat.primitives import serialization
        signed=load(signed_file)
        sig=base64.b64decode(signed.pop('signature_base64'),validate=True)
        pk=serialization.load_pem_public_key(Path(key_file).read_bytes())
        if not isinstance(pk,Ed25519PublicKey):return False,'Not an Ed25519 host key'
        pk.verify(sig,canonical(signed))
        if (signed.get('change_id')!=plan['change_id'] or
            signed.get('baseline_id')!=baseline['baseline_id'] or
            signed.get('baseline_snapshot_sha256')!=baseline['origin']['snapshot_sha256'] or
            signed.get('authorized_changes')!=plan['authorized_changes']):
            return False, 'Signed authorization does not bind exactly to this plan/baseline'
        issued=datetime.fromisoformat(signed['issued_at'].replace('Z','+00:00'))
        until=datetime.fromisoformat(signed['expires_at'].replace('Z','+00:00'))
        now=datetime.now(timezone.utc)
        if (issued.tzinfo is None or until.tzinfo is None or not (issued<=now<=until)):
            return False, 'Expired or invalid temporal authority'
        if signed.get('issuer_type')!='EXTERNAL_HOST':return False,'Agent self-approval forbidden'
        return True,'Verified Ed25519 signature bound to scoped host approval'
    except (ImportError,ValueError,KeyError,TypeError,OSError) as e:
        return False,'Invalid external approval: '+str(e)
    except Exception as e:
        return False,'Approval verification failed: '+str(e)


def evaluate(root,baseline,plan,checks,evidence_dir, signed_approval=None, trusted_key=None, baseline_evidence_dir=None):
    baseline_evidence_dir=baseline_evidence_dir or evidence_dir
    validate_schema(baseline,'baseline');validate_schema(plan,'change_plan')
    errors=[]; gaps=[]
    if (plan['baseline_id']!=baseline['baseline_id'] or
        plan['baseline_snapshot_sha256']!=baseline['origin']['snapshot_sha256']):
        errors.append('baseline/plan identity mismatch')
    if plan['change_scope'] and any(not isinstance(x,str) or '..' in Path(x).parts or x.startswith('/')
                                    for x in plan['change_scope']):
        errors.append('unsafe change_scope')
    limits=baseline.get('extensions',{}).get('snapshot_limits',{})
    snap=snapshot(root,baseline['scope']['include'],baseline['scope']['exclude'],
                  limits.get('max_files',10000),limits.get('max_bytes',100_000_000))
    sha=snap['snapshot_sha256']
    if snap['gaps'] or baseline['scope']['truncated'] or baseline['scope']['inventory_status']!='COMPLETE':
        gaps.append('baseline or candidate coverage not complete')
    if checks.get('schema')!='bago.app_game.executed_checks.v1':
        errors.append('untrusted result document format')
    if (checks.get('candidate_sha256')!=sha or checks.get('post_sha256')!=sha or
        checks.get('stable') is not True or checks.get('change_id')!=plan['change_id'] or
        checks.get('baseline_id')!=baseline['baseline_id']):
        errors.append('candidate/runner identity mismatch or mutated during test')
    ok_auth, auth_reason=verify_approval(plan,baseline,signed_approval,trusted_key)
    if not ok_auth:errors.append(auth_reason)
    # Baseline evidence files must remain authentic and attributable.
    for e in baseline['evidence']:
        if not evidence_hash_ok(e,baseline_evidence_dir): gaps.append('baseline evidence unavailable: '+e['id'])
    # Test evidence is local, hashed and checked against recorded runner command/exit status.
    evids=checks.get('evidence',[])
    evid_by={e['id']:e for e in evids}
    if len(evid_by)!=len(evids):errors.append('duplicate evidence IDs')
    for e in evids:
        if not evidence_hash_ok(e,evidence_dir):errors.append('test evidence missing/invalid: '+e['id'])
    tests={x['test_id']:x for x in plan['tests']}
    if len(tests)!=len(plan['tests']):errors.append('duplicate test ID in plan')
    results=checks.get('test_results',[])
    by_id={x['test_id']:x for x in results}
    if len(by_id)!=len(results):errors.append('duplicate test result ID')
    for t in results:
        declared=tests.get(t['test_id'])
        if declared is None:errors.append('undeclared test: '+t['test_id']);continue
        if t['boundary']!=declared['boundary'] or t['candidate_sha256']!=sha:
            errors.append('boundary/candidate mismatch for '+t['test_id'])
        if t['status'] not in ('PASS','FAIL','ERROR','NOT_RUN'):
            errors.append('invalid result status: '+t['test_id']);continue
        if t['status']=='PASS' and not t.get('evidence_refs'):
            gaps.append('PASS without evidence: '+t['test_id'])
        for ref in t.get('evidence_refs',[]):
            if ref not in evid_by:errors.append('missing referenced evidence '+ref)
            elif t['status']!='NOT_RUN':
                p=Path(evidence_dir)/evid_by[ref]['locator']
                if evidence_hash_ok(evid_by[ref],evidence_dir):
                    try:
                        observed=load(p)
                        if (observed.get('check_id')!=t['test_id'] or observed.get('status')!=t['status']
                            or observed.get('candidate_sha256')!=sha or
                            (observed.get('result',{}).get('exit_code')==0)!=(t['status']=='PASS')):
                            errors.append('runner evidence contradicts result: '+t['test_id'])
                    except (OSError,ValueError):errors.append('evidence not executable result: '+t['test_id'])
    if (baseline['environment']['platform']!=platform_name()):
        gaps.append('baseline/current platform mismatch')
    if any(base_property['mandatory'] and baseline['environment'].get('visual_profile') and
           base_property['modality']=='VISUAL' for c in baseline['capabilities'] for base_property in c['properties']):
        gaps.append('visual profile comparison requires external verified Playwright artifact')
    capabilities={c['id']:c for c in baseline['capabilities']}
    if len(capabilities)!=len(baseline['capabilities']):errors.append('duplicate capability')
    all_props={(c['id'],p['property_id']):(c,p) for c in baseline['capabilities'] for p in c['properties']}
    if sum(len(c['properties']) for c in baseline['capabilities'])!=len(all_props):errors.append('duplicate property')
    # Conservative impact: ALL mandatory properties; no silent omission by arbitrary small scopes.
    required={(x['capability_id'],x['property_id']) for x in plan['preservation']['required_properties']}
    authorized={(x['capability_id'],x['property_id']):x for x in plan['authorized_changes']}
    for p in required|set(authorized):
        if p not in all_props:errors.append('reference not in baseline: '+str(p))
    for p,(c,prop) in all_props.items():
        if prop['mandatory'] and p not in required and p not in authorized:
            gaps.append('mandatory property omitted from impact: '+'.'.join(p))
    preservation=[]
    for (cap_id,prop_id),(cap,prop) in all_props.items():
        if not prop['mandatory'] and (cap_id,prop_id) not in required|set(authorized):continue
        related=[x for x in plan['tests'] if x['target_type']=='PROPERTY' and
                 x['target_id']==cap_id+'.'+prop_id and x['mandatory']]
        ids=[t['test_id'] for t in related]
        statuses=[by_id.get(i,{}).get('status','NOT_RUN') for i in ids]
        if (cap_id,prop_id) in authorized and ok_auth:
            # The new approved transition must itself have a mandatory passing check.
            auth=authorized[(cap_id,prop_id)]
            transition=[t for t in related if t['expected']==auth['expected_transition']]
            if transition and all(by_id.get(t['test_id'],{}).get('status')=='PASS' for t in transition):
                result, reason='AUTHORIZED_CHANGE','Host-signed scoped transition checked'
            else:result,reason='UNKNOWN','Transition not verified by mandatory check'
        elif not ids:
            result,reason='UNKNOWN','No mandatory property check'
        elif any(x=='FAIL' for x in statuses):
            result,reason='REGRESSED','Mandatory old behavior check failed'
        elif (cap_id,prop_id) not in authorized and not set(prop['check_refs']).issubset(ids):
            result,reason='UNKNOWN','Original mandatory check IDs were not preserved'
        elif all(x=='PASS' for x in statuses) and cap['state']=='VERIFIED' and prop['check_refs']:
            # Baseline evidence must be present; a marker/discovery alone is insufficient.
            if all(evidence_hash_ok(e,baseline_evidence_dir) for e in baseline['evidence'] if e['id'] in cap['evidence_refs']):
                result,reason='PRESERVED','Baseline verified and mandatory candidate checks pass'
            else:result,reason='UNKNOWN','Baseline evidence absent'
        else:result,reason='UNKNOWN','Unverified baseline or mandatory check unavailable/error'
        modalities={'FUNCTIONAL':{'UNIT','INTEGRATION','RUNTIME','GAMEPLAY'},
                    'STRUCTURAL':{'SOURCE','INTEGRATION','ACCESSIBILITY','RUNTIME'},
                    'VISUAL':{'VISUAL'},'INTEGRATION':{'INTEGRATION','RUNTIME'},
                    'GAMEPLAY':{'GAMEPLAY','RUNTIME'}}
        if result=='PRESERVED' and not any(t['boundary'] in modalities[prop['modality']] for t in related):
            result,reason='UNKNOWN','Check boundary does not establish requested modality'
        preservation.append({'capability_id':cap_id,'property_id':prop_id,'result':result,
                             'test_ids':ids,'reason':reason})
    features=[]
    for feature in plan['features']:
        ids=[t['test_id'] for t in plan['tests'] if t['target_type']=='FEATURE' and
             t['target_id']==feature['id'] and t['mandatory']]
        st=[by_id.get(x,{}).get('status','NOT_RUN') for x in ids]
        if not ids:state='UNKNOWN'
        elif 'FAIL' in st:state='FAIL'
        elif all(x=='PASS' for x in st):state='PASS'
        else:state='UNKNOWN'
        features.append({'feature_id':feature['id'],'result':state,'test_ids':ids})
    for test in plan['tests']:
        if test['mandatory'] and test['test_id'] not in by_id:
            gaps.append('mandatory test not run: '+test['test_id'])
        if test['mandatory'] and by_id.get(test['test_id'],{}).get('status') in ('NOT_RUN','ERROR'):
            gaps.append('mandatory test incomplete: '+test['test_id'])
        if test['mandatory'] and by_id.get(test['test_id'],{}).get('status')=='PASS' and not by_id[test['test_id']].get('evidence_refs'):
            gaps.append('mandatory evidence missing: '+test['test_id'])
    if errors or any(x['result']=='REGRESSED' for x in preservation) or any(x['result']=='FAIL' for x in features) or any(
        t['mandatory'] and by_id.get(t['test_id'],{}).get('status')=='FAIL' and
        not (t['target_type']=='PROPERTY' and tuple(t['target_id'].split('.',1)) in authorized and ok_auth)
        for t in plan['tests']):
        decision='NO_GO'
    elif gaps or any(t['status']=='FAIL' for t in results if not tests[t['test_id']]['mandatory']) or any(x['result']=='UNKNOWN' for x in preservation) or any(x['result']=='UNKNOWN' for x in features):
        decision='INCONCLUSIVE'
    else:decision='GO'
    # This bounded verifier cannot certify actual UI/gameplay/runtime independently of the chosen checks.
    boundary='TESTED' if any(x['status']=='PASS' for x in results) else 'SOURCE'
    report={'schema':'bago.app_game.verification_report.v1',
            'run_id':'RUN-'+plan['change_id'],'change_id':plan['change_id'],
            'baseline_id':baseline['baseline_id'],
            'baseline_snapshot_sha256':baseline['origin']['snapshot_sha256'],
            'candidate':{'revision':None,'snapshot_sha256':sha},
            'environment':baseline['environment'],'test_results':results,
            'preservation_results':preservation,'feature_results':features,'evidence':evids,
            'decision':{'status':decision,'claim_level':boundary,
                        'reason':'; '.join(errors+gaps) if errors+gaps else 'All required checks satisfied in tested scope'},
            'extensions':{'semantic_errors':errors,'coverage_gaps':gaps,
                          'approval_status':auth_reason,
                          'verification_boundary':'Local test results, not independent Codex/engine certification'}}
    validate_schema(report,'verification_report')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('root','baseline','plan','checks','evidence-dir','output'):
        p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--signed-approval',type=Path)
    p.add_argument('--trusted-public-key',type=Path)
    p.add_argument('--baseline-evidence-dir',type=Path)
    a=p.parse_args()
    try:
        r=evaluate(a.root,load(a.baseline),load(a.plan),load(a.checks),a.evidence_dir,
                   a.signed_approval,a.trusted_public_key,a.baseline_evidence_dir)
        dump_new(a.output,r)
        print(json.dumps({'ok':r['decision']['status']=='GO','decision':r['decision']['status'],
                          'report':str(a.output),'reason':r['decision']['reason']}))
        return {'GO':0,'NO_GO':1,'INCONCLUSIVE':3}[r['decision']['status']]
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'decision':'NO_GO','error':str(exc)}));return 2
if __name__=='__main__':raise SystemExit(main())
