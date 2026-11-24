#!/usr/bin/env python3
"""Capture a scoped, read-only baseline; NEVER infer functional verification from files."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from preservation_core import (snapshot, load, dump_new, validate_schema, current_git,
                               evidence_hash_ok, platform_name)


def capture(root, project_id, baseline_id, includes, excludes, target, runtime,
            configuration, capabilities_file, evidence_dir, max_files, max_bytes):
    if not includes or any(x.startswith('/') or '..' in Path(x).parts for x in includes+excludes):
        raise ValueError('explicit relative include/exclude glob required, no traversal')
    snap=snapshot(root,includes,excludes,max_files,max_bytes)
    rev, dirty=current_git(root)
    capabilities, ev=[], []
    if capabilities_file:
        supplied=load(capabilities_file)
        capabilities=supplied.get('capabilities',[])
        ev=supplied.get('evidence',[])
        for e in ev:
            if not evidence_dir or not evidence_hash_ok(e,evidence_dir):
                raise ValueError('baseline evidence invalid: '+e['id'])
        by_id={e['id'] for e in ev}
        for cap in capabilities:
            if cap.get('state')=='VERIFIED' and (not cap.get('evidence_refs') or
                                                not set(cap['evidence_refs']).issubset(by_id)):
                raise ValueError('VERIFIED capability without authentic evidence: '+cap['id'])
        if len({c['id'] for c in capabilities}) != len(capabilities):raise ValueError('duplicate capability')
    baseline={
        'schema':'bago.app_game.baseline.v1', 'project_id':project_id,'baseline_id':baseline_id,
        'captured_at':datetime.now(timezone.utc).isoformat(),
        'origin':{'root_ref':'project://'+project_id,'git_revision':rev,'git_dirty':dirty,
                  'snapshot_sha256':snap['snapshot_sha256']},
        'scope':{'include':includes,'exclude':excludes,'inventory_status':
                 'PARTIAL' if snap['gaps'] else 'COMPLETE','files_scanned':snap['files_scanned'],
                 'truncated':snap['truncated'],'coverage_gaps':snap['gaps']},
        'environment':{'platform':platform_name(), 'target':target,'runtime':runtime,
                       'configuration':configuration},
        'capabilities':capabilities,'evidence':ev,
        'extensions':{'file_manifest':snap['files'],'total_bytes':snap['total_bytes'],
                      'snapshot_limits':{'max_files':max_files,'max_bytes':max_bytes}}
    }
    validate_schema(baseline,'baseline')
    return baseline


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--project-id',required=True)
    ap.add_argument('--baseline-id',required=True)
    ap.add_argument('--include',action='append',required=True,help='Relative glob, repeat for multiple')
    ap.add_argument('--exclude',action='append',default=[])
    ap.add_argument('--target',default='source:scoped')
    ap.add_argument('--runtime',default=None)
    ap.add_argument('--configuration',default='local')
    ap.add_argument('--capabilities-file',type=Path)
    ap.add_argument('--evidence-dir',type=Path)
    ap.add_argument('--max-files',type=int,default=10000)
    ap.add_argument('--max-bytes',type=int,default=100_000_000)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        if a.output.resolve().is_relative_to(a.root.resolve(strict=True)):
            raise ValueError('baseline output must be outside inspected project')
        b=capture(a.root,a.project_id,a.baseline_id,a.include,a.exclude,a.target,a.runtime,
                  a.configuration,a.capabilities_file,a.evidence_dir,a.max_files,a.max_bytes)
        dump_new(a.output,b)
        print(json.dumps({'ok':True,'snapshot_sha256':b['origin']['snapshot_sha256'],
              'inventory_status':b['scope']['inventory_status'],'output':str(a.output)}))
        return 3 if b['scope']['inventory_status']=='PARTIAL' else 0
    except (OSError,ValueError,KeyError,TypeError) as ex:
        print(json.dumps({'ok':False,'error':str(ex)}));return 2

if __name__=='__main__':raise SystemExit(main())
