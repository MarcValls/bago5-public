#!/usr/bin/env python3
"""Read-only scoped content snapshot/diff. Exit 3 means INCONCLUSIVE, not PASS."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from preservation_core import canonical, sha_bytes, snapshot, SKIP_DIRS
from suite_safety import safe_rel, SHA256, read_json, write_new_json, new_external_path

SCHEMA = 'bago.project_content_snapshot.v1'
POLICY = {'engine': 'bago.scanner.v2', 'default_excluded_dirs': sorted(SKIP_DIRS),
          'symlinks': 'REJECT', 'consistency': 'PER_FILE_PRE_POST_NOT_ATOMIC_TREE'}


def _patterns(values, required=False):
    if not isinstance(values, list) or (required and not values):
        raise ValueError('scope must contain explicit pattern lists')
    for value in values:
        safe_rel(value, glob=True)
    if len(values) != len(set(values)):
        raise ValueError('duplicate scope patterns')
    return sorted(values)


def capture(root, includes, excludes, max_files=10000, max_bytes=100_000_000):
    includes, excludes = _patterns(includes, True), _patterns(excludes)
    snap = snapshot(root, includes, excludes, max_files, max_bytes)
    return {
        'schema': SCHEMA, 'captured_at': datetime.now(timezone.utc).isoformat(),
        'root': str(Path(root).resolve(strict=True)),
        'scope': {'include': includes, 'exclude': excludes}, 'scan_policy': POLICY,
        'limits': {'max_files': max_files, 'max_bytes': max_bytes},
        'state': 'PARTIAL' if snap['gaps'] else 'COMPLETE', 'files': snap['files'],
        'files_scanned': snap['files_scanned'], 'total_bytes': snap['total_bytes'],
        'coverage_gaps': snap['gaps'], 'snapshot_sha256': snap['snapshot_sha256'],
        'claim': 'CONTENT_INVENTORY_ONLY_NOT_FUNCTIONAL_VERIFICATION',
    }


def validate_snapshot(value):
    if not isinstance(value, dict):
        raise ValueError('snapshot must be object')
    obj = value.get('snapshot', value)
    if not isinstance(obj, dict) or obj.get('schema') != SCHEMA:
        raise ValueError('unsupported snapshot schema')
    if not isinstance(obj.get('root'), str) or not obj['root'] or '\x00' in obj['root']:
        raise ValueError('invalid root identity')
    # Windows snapshots can be validated on POSIX without resolving their paths.
    from pathlib import PureWindowsPath
    if not (Path(obj['root']).is_absolute() or PureWindowsPath(obj['root']).is_absolute()):
        raise ValueError('root identity must be absolute')
    try:
        timestamp = datetime.fromisoformat(obj['captured_at'])
        if timestamp.tzinfo is None:
            raise ValueError('timestamp must have timezone')
    except (TypeError, KeyError):
        raise ValueError('invalid capture timestamp') from None
    scope = obj.get('scope')
    if not isinstance(scope, dict) or set(scope) != {'include', 'exclude'}:
        raise ValueError('invalid scope')
    _patterns(scope['include'], True); _patterns(scope['exclude'])
    state, gaps = obj.get('state'), obj.get('coverage_gaps')
    if state not in ('COMPLETE', 'PARTIAL') or not isinstance(gaps, list) or any(not isinstance(g, str) or not g for g in gaps):
        raise ValueError('invalid coverage state')
    if (state == 'COMPLETE') != (len(gaps) == 0):
        raise ValueError('state contradicts coverage gaps')
    files, paths, total = obj.get('files'), set(), 0
    if not isinstance(files, list):
        raise ValueError('file manifest must be a list')
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {'path', 'sha256', 'bytes'}:
            raise ValueError('malformed file entry')
        rel = safe_rel(entry['path']).as_posix()
        if rel in paths:
            raise ValueError('duplicate manifest path')
        paths.add(rel)
        if type(entry['bytes']) is not int or entry['bytes'] < 0:
            raise ValueError('invalid file size')
        if not isinstance(entry['sha256'], str) or not SHA256.fullmatch(entry['sha256']):
            raise ValueError('invalid file SHA256')
        total += entry['bytes']
    if type(obj.get('files_scanned')) is not int or obj['files_scanned'] != len(files):
        raise ValueError('files_scanned mismatch')
    if type(obj.get('total_bytes')) is not int or obj['total_bytes'] != total:
        raise ValueError('total_bytes mismatch')
    if not files and state == 'COMPLETE':
        raise ValueError('empty scope cannot establish complete coverage')
    if 'scan_policy' in obj and obj['scan_policy'] != POLICY:
        raise ValueError('unknown scan policy')
    if 'limits' in obj:
        limits = obj['limits']
        if not isinstance(limits, dict) or set(limits) != {'max_files', 'max_bytes'} or any(type(v) is not int or v < 1 for v in limits.values()):
            raise ValueError('invalid limits')
        if len(files) > limits['max_files'] or total > limits['max_bytes']:
            raise ValueError('manifest exceeds declared limits')
    expected = sha_bytes(canonical(sorted(files, key=lambda x: x['path'])))
    if expected != obj.get('snapshot_sha256'):
        raise ValueError('snapshot inventory fingerprint mismatch')
    return obj


def compare(before, after):
    before, after = validate_snapshot(before), validate_snapshot(after)
    scope = lambda o: {k: sorted(v) for k, v in o['scope'].items()}
    if before['root'] != after['root'] or scope(before) != scope(after) or before.get('scan_policy') != after.get('scan_policy'):
        raise ValueError('different roots, scope or scan policy; create a new baseline')
    left, right = ({x['path']: x for x in s['files']} for s in (before, after))
    added, removed = sorted(right.keys() - left.keys()), sorted(left.keys() - right.keys())
    changed = sorted(p for p in left.keys() & right.keys() if (left[p]['sha256'],left[p]['bytes']) != (right[p]['sha256'],right[p]['bytes']))
    complete = before['state'] == after['state'] == 'COMPLETE'
    return {'schema': 'bago.project_content_diff.v1', 'comparable': complete,
            'result': 'COMPLETE' if complete else 'INCONCLUSIVE',
            'before_sha256': before['snapshot_sha256'], 'after_sha256': after['snapshot_sha256'],
            'added': added, 'removed': removed, 'modified': changed,
            'unchanged_count': len(left.keys() & right.keys()) - len(changed),
            'counts': {'added': len(added), 'removed': len(removed), 'modified': len(changed)},
            'warning': None if complete else 'Observed set differences only: a partial scan cannot prove complete additions/removals or absence of changes.'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--include',action='append',required=True)
    p.add_argument('--exclude',action='append',default=[])
    p.add_argument('--max-files',type=int,default=10000)
    p.add_argument('--max-bytes',type=int,default=100_000_000)
    p.add_argument('--before',type=Path)
    p.add_argument('--output',type=Path,required=True,help='New destination outside scanned root and suite')
    args=p.parse_args(argv)
    try:
        root=args.root.resolve(strict=True)
        suite=Path(__file__).resolve().parents[4]
        output=new_external_path(args.output,(root,suite))
        before=None
        if args.before:
            if args.before.resolve().is_relative_to(root):
                raise ValueError('previous snapshot must reside outside scanned root')
            before=validate_snapshot(read_json(args.before))
        current=capture(args.root,args.include,args.exclude,args.max_files,args.max_bytes)
        result={'snapshot':current}
        if before is not None:
            result['diff']=compare(before,current)
        write_new_json(output,result)
        partial=current['state']=='PARTIAL' or result.get('diff',{}).get('result')=='INCONCLUSIVE'
        print(json.dumps({'ok':True,'status':'INCONCLUSIVE' if partial else 'PASS',
              'state':current['state'],'snapshot_sha256':current['snapshot_sha256'],
              'coverage_gaps':current['coverage_gaps'],'diff':result.get('diff'),'output':str(output)},ensure_ascii=False))
        return 3 if partial else 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print(json.dumps({'ok':False,'status':'FAIL','error':str(exc)},ensure_ascii=False))
        return 2

if __name__=='__main__':
    raise SystemExit(main())
