#!/usr/bin/env python3
"""Explicitly execute a list of user-approved argv checks (no shell, no implicit install).

Runner is NOT an authorization boundary. The caller must obtain host permission BEFORE
running it. Commands can run arbitrary code; do not run on untrusted repositories.
"""
from __future__ import annotations
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from preservation_core import snapshot, load, dump_new, sha_file, validate_schema


def execute(root,base,plan,commands_file,out_dir,timeout):
    validate_schema(base,'baseline');validate_schema(plan,'change_plan')
    if plan['baseline_id']!=base['baseline_id'] or plan['baseline_snapshot_sha256']!=base['origin']['snapshot_sha256']:
        raise ValueError('plan baseline identity mismatch')
    root=root.resolve(strict=True)
    limits=base.get('extensions',{}).get('snapshot_limits',{})
    snap_args=(root,base['scope']['include'],base['scope']['exclude'],
               limits.get('max_files',10000),limits.get('max_bytes',100_000_000))
    before=snapshot(*snap_args)
    if before['gaps']:raise ValueError('candidate snapshot incomplete')
    command_config=load(commands_file)
    declared={t['test_id']:t for t in plan['tests']}
    if not isinstance(command_config,list) or len(command_config)!=len({x['test_id'] for x in command_config}):
        raise ValueError('commands must have unique test IDs')
    for entry in command_config:
        if entry['test_id'] not in declared:raise ValueError('command not in plan')
        if not isinstance(entry.get('argv'),list) or not entry['argv'] or not all(isinstance(x,str) and x for x in entry['argv']):
            raise ValueError('argv must be a nonempty argument list')
    out_dir=out_dir.resolve()
    if out_dir.is_relative_to(root):raise ValueError('evidence directory must be outside project')
    if out_dir.exists():raise FileExistsError('evidence directory already exists, refusing overwrite')
    out_dir.mkdir(parents=True)
    checks=[];evidence=[]
    for i,item in enumerate(command_config):
        test=declared[item['test_id']]
        stamp=datetime.now(timezone.utc).isoformat()
        try:
            cp=subprocess.run(item['argv'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,errors='replace',timeout=timeout,env=os.environ.copy(),shell=False)
            status=('PASS' if cp.returncode==0 else
                    'NOT_RUN' if cp.returncode in item.get('not_run_exit_codes',[]) else 'FAIL')
            result={'exit_code':cp.returncode,'output':cp.stdout}
        except (OSError,subprocess.TimeoutExpired) as e:
            status='ERROR'
            result={'exit_code':None,'output':str(e)}
        # User-managed output can contain secrets: avoid passing passwords/env secrets; review logs.
        # Preserve output digest, but never indiscriminately persist secrets printed by tests.
        output=result.pop('output', '')
        result['output_sha256']=__import__('hashlib').sha256(output.encode('utf-8',errors='replace')).hexdigest()
        result['output_bytes']=len(output.encode('utf-8',errors='replace'))
        record={'check_id':test['test_id'],'boundary':test['boundary'],'status':status,
                'command':item['argv'],'time':stamp,'result':result,
                'candidate_sha256':before['snapshot_sha256']}
        name='check-%03d.json'%(i+1)
        dump_new(out_dir/name,record)
        evid='EV-'+test['test_id']
        evidence.append({'id':evid,'kind':'TEST_RESULT','locator':name,
                         'sha256':sha_file(out_dir/name)})
        checks.append({'test_id':test['test_id'],'boundary':test['boundary'],
                       'status':status,'candidate_sha256':before['snapshot_sha256'],
                       'evidence_refs':[evid],'reason':'exit '+str(result['exit_code'])})
    after=snapshot(*snap_args)
    payload={'schema':'bago.app_game.executed_checks.v1','baseline_id':base['baseline_id'],
             'change_id':plan['change_id'],'candidate_sha256':before['snapshot_sha256'],
             'post_sha256':after['snapshot_sha256'],'stable':before==after,
             'test_results':checks,'evidence':evidence}
    dump_new(out_dir/'checks.json',payload)
    return payload


def completion_status(payload):
    """Successful process invocation alone does not mean checks passed."""
    if not payload['stable'] or any(x['status'] in ('FAIL', 'ERROR') for x in payload['test_results']):
        return 'FAIL', 2
    if not payload['test_results'] or any(x['status'] != 'PASS' for x in payload['test_results']):
        return 'INCONCLUSIVE', 3
    return 'PASS', 0


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--commands',type=Path,required=True)
    ap.add_argument('--evidence-dir',type=Path,required=True);ap.add_argument('--timeout',type=int,default=120)
    a=ap.parse_args()
    try:
        p=execute(a.root,load(a.baseline),load(a.plan),a.commands,a.evidence_dir,a.timeout)
        status, code = completion_status(p)
        print(json.dumps({'ok':status=='PASS','status':status,'stable':p['stable'],'results':[{'test_id':x['test_id'],'status':x['status']} for x in p['test_results']]}))
        return code
    except (OSError,ValueError,KeyError,TypeError) as ex:
        print(json.dumps({'ok':False,'error':str(ex)}));return 2
if __name__=='__main__':raise SystemExit(main())
