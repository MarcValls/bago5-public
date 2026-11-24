#!/usr/bin/env python3
"""Validate BAGO-CDP-001 route records and local evidence hashes; NEVER run a project."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

STATES = {"PROPOSED", "IMPLEMENTED", "VERIFIED", "DEMONSTRABLE", "BLOCKED"}
CHANNELS = {"ui", "cli", "api", "trace", "state", "artifact", "hardware", "other"}
RESULTS = {"PASS", "FAIL", "NOT_RUN"}
SCHEMA = "bago.cdp.capability_demonstration.v1"


def _is_str(value):
    return isinstance(value, str) and bool(value.strip())


def _safe_local(record_dir, ref):
    if not _is_str(ref) or '\\' in ref or ':' in ref or ref.startswith('/'):
        return None
    parts = PurePosixPath(ref).parts
    if any(part in {".", "..", ""} for part in parts):
        return None
    base = record_dir.resolve()
    target = record_dir.joinpath(*parts)
    if target.is_symlink() or not target.is_file():
        return None
    if not target.resolve().is_relative_to(base):
        return None
    return target


def validate_record(data, record_dir):
    """Return (errors, observed_hashes). PASS is only structural + hash conformance."""
    errors = []
    if not isinstance(data, dict):
        return ["record must be an object"], 0
    required = {'schema','project_id','capability_id','claim','candidate_id','state','route','checks','evidence','limits'}
    extra = set(data) - required
    if extra: errors.append('unknown keys: ' + ', '.join(sorted(extra)))
    missing = required - set(data)
    if missing: errors.append('missing keys: ' + ', '.join(sorted(missing)))
    if data.get('schema') != SCHEMA: errors.append('wrong schema')
    for key in ('project_id','capability_id','claim','candidate_id'):
        if not _is_str(data.get(key)): errors.append(f'{key}: required nonempty string')
    state = data.get('state')
    if not isinstance(state,str) or state not in STATES: errors.append('invalid state')
    route = data.get('route')
    if not isinstance(route, dict):
        errors.append('route must be object'); route = {}
    route_keys={'entry_point','boundary','dependencies','requires_unfinished_platform','preconditions','steps','observation','expected_result','negative_path'}
    if set(route) != route_keys: errors.append('route keys missing/extra: ' + ', '.join(sorted(route_keys ^ set(route))))
    for key in ('entry_point','boundary','expected_result','negative_path'):
        if not _is_str(route.get(key)): errors.append(f'route.{key}: nonempty string required')
    for key in ('dependencies','preconditions'):
        value=route.get(key)
        if not isinstance(value,list) or any(not _is_str(item) for item in value):errors.append(f'route.{key}: array of strings required')
    steps=route.get('steps')
    if not isinstance(steps,list) or not steps or any(not _is_str(step) for step in steps):errors.append('route.steps: nonempty array of strings required')
    if type(route.get('requires_unfinished_platform')) is not bool:errors.append('route.requires_unfinished_platform: boolean required')
    observation=route.get('observation')
    if not isinstance(observation,dict) or set(observation)!={'channel','probe'} or not isinstance(observation.get('channel'),str) or observation.get('channel') not in CHANNELS or not _is_str(observation.get('probe')):
        errors.append('route.observation: channel and probe required')
    limits=data.get('limits')
    if not isinstance(limits,list) or any(not _is_str(x) for x in limits):errors.append('limits: string array required')
    checks=data.get('checks')
    if not isinstance(checks,list):errors.append('checks: array required');checks=[]
    evidence=data.get('evidence')
    if not isinstance(evidence,list):errors.append('evidence: array required');evidence=[]
    evidence_by_ref={}
    hashes_checked=0
    for i,item in enumerate(evidence):
        if not isinstance(item,dict) or set(item)!={'ref','sha256'}:
            errors.append(f'evidence[{i}]: must contain ref/sha256');continue
        ref=item.get('ref');digest=item.get('sha256')
        if not _is_str(ref) or not isinstance(digest,str) or re.fullmatch(r'[0-9a-f]{64}',digest) is None:
            errors.append(f'evidence[{i}]: invalid ref/hash');continue
        if ref in evidence_by_ref:errors.append(f'evidence[{i}]: duplicate ref')
        evidence_by_ref[ref]=digest
        target=_safe_local(record_dir,ref)
        if target is None:
            errors.append(f'evidence[{i}]: missing/unsafe local evidence');continue
        if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
            errors.append(f'evidence[{i}]: hash mismatch');continue
        hashes_checked+=1
    passing=[]
    for i,item in enumerate(checks):
        if not isinstance(item,dict) or set(item)!={'id','result','scope','evidence_ref'}:
            errors.append(f'checks[{i}]: invalid shape');continue
        if not _is_str(item.get('id')) or not _is_str(item.get('scope')) or not isinstance(item.get('result'),str) or item.get('result') not in RESULTS or not isinstance(item.get('evidence_ref'),str):
            errors.append(f'checks[{i}]: invalid fields');continue
        if item['result']=='PASS':
            passing.append(item)
            if not item['evidence_ref'] or item['evidence_ref'] not in evidence_by_ref:
                errors.append(f'checks[{i}]: PASS needs linked evidence')
        elif item['evidence_ref'] and item['evidence_ref'] not in evidence_by_ref:
            errors.append(f'checks[{i}]: unlisted evidence ref')
    if isinstance(state,str) and state in {'VERIFIED','DEMONSTRABLE'}:
        if data.get('candidate_id')=='NOT_BUILT':errors.append('verified state cannot have NOT_BUILT identity')
        if not passing:errors.append('verified state needs passing checks')
        if not evidence:errors.append('verified state needs evidence')
        if any(item.get('result')=='FAIL' for item in checks if isinstance(item,dict)):
            errors.append('verified state cannot coexist with recorded FAIL check')
    if state=='DEMONSTRABLE' and route.get('requires_unfinished_platform') is True:
        errors.append('DEMONSTRABLE depends on unfinished platform')
    if state=='BLOCKED' and not limits:
        errors.append('BLOCKED requires reason/unblock condition in limits')
    return errors,hashes_checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('record',type=Path)
    args=parser.parse_args()
    try:
        record=args.record.resolve(strict=True)
        value=json.loads(record.read_text(encoding='utf-8'))
        errors,hashes=validate_record(value,record.parent)
        report={'status':'FAIL' if errors else 'PASS','check':'STRUCTURE_AND_LOCAL_EVIDENCE_ONLY',
                'capability_id':value.get('capability_id') if isinstance(value,dict) else None,
                'claimed_state':value.get('state') if isinstance(value,dict) else None,
                'operational_retest':'NOT_RUN','evidence_hashes_checked':hashes,'errors':errors}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report={'status':'FAIL','check':'STRUCTURE_AND_LOCAL_EVIDENCE_ONLY','operational_retest':'NOT_RUN','errors':[str(exc)]}
    print(json.dumps(report,sort_keys=True,ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
