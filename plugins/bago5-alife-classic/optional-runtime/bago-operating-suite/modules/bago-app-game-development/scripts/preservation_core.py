#!/usr/bin/env python3
"""Shared, dependency-free snapshot and schema checks. Never modifies an inspected project."""
from __future__ import annotations
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import stat
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from suite_safety import safe_rel, reject_links

SKIP_DIRS = {'.git', '.hg', '.svn', '.venv', 'node_modules', 'dist', 'build',
             'coverage', '.next', '.godot', 'Library', 'Binaries', '__pycache__'}


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode('utf-8')


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for part in iter(lambda: stream.read(1024*1024), b''):
            h.update(part)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump_new(path, payload):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write('\n')
    return p


def match(rel, patterns):
    return any(fnmatch.fnmatchcase(rel, x) or (x.startswith('**/') and fnmatch.fnmatchcase(rel, x[3:])) or (x.endswith('/**') and (rel == x[:-3] or rel.startswith(x[:-2]))) for x in patterns)


def _read_stable_file(path, root, remaining):
    """Bounded read with pre/post identity checks. Not an atomic tree snapshot."""
    reject_links(path)
    if not path.resolve(strict=True).is_relative_to(root):
        raise ValueError('path escaped root')
    before = path.stat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('not a regular file')
    if before.st_size > remaining:
        raise OverflowError('byte budget')
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, 'rb') as stream:
        first = os.fstat(stream.fileno())
        identity = lambda st: (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
        if not stat.S_ISREG(first.st_mode) or identity(first) != identity(before):
            raise ValueError('changed before read')
        digest, count = hashlib.sha256(), 0
        while True:
            block = stream.read(min(1024 * 1024, remaining - count + 1))
            if not block:
                break
            count += len(block)
            if count > remaining:
                raise OverflowError('byte budget during read')
            digest.update(block)
        after = os.fstat(stream.fileno())
    reject_links(path)
    if not path.resolve(strict=True).is_relative_to(root) or identity(first) != identity(after) or identity(after) != identity(path.stat()) or count != after.st_size:
        raise ValueError('changed during read')
    return digest.hexdigest(), count


def snapshot(root, include, exclude, max_files=10000, max_bytes=100*1024*1024):
    """Scoped byte fingerprints, conservative coverage and bounded reads.

    Implicit omissions, traversal errors and concurrent file changes are gaps.
    Callers can explicitly exclude dependencies to define a complete smaller scope.
    Does not enforce OS authorization or capture a filesystem-atomic snapshot.
    """
    reject_links(Path(root))
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('root must be directory')
    if type(max_files) is not int or type(max_bytes) is not int or max_files < 1 or max_bytes < 1:
        raise ValueError('limits must be positive integers')
    if not isinstance(include, (list, tuple)) or not include or not isinstance(exclude, (list, tuple)):
        raise ValueError('explicit scope lists required')
    for pattern in list(include) + list(exclude):
        safe_rel(pattern, glob=True)
    entries, gaps, total = [], [], 0
    def walk_error(exc):
        try:
            rel = Path(exc.filename).relative_to(root).as_posix()
        except (TypeError, ValueError):
            rel = '<unknown>'
        gaps.append('walk_error:' + rel)
    for dirname, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=walk_error):
        here = Path(dirname)
        try:
            reject_links(here)
            if not here.resolve(strict=True).is_relative_to(root):
                raise ValueError('directory escaped root')
        except (OSError, ValueError):
            gaps.append('unsafe_dir:' + here.relative_to(root).as_posix())
            dirs[:] = []
            continue
        def allowed_dir(name):
            p = here / name
            rel = p.relative_to(root).as_posix()
            if match(rel, exclude) or match(rel + '/file', exclude):
                return False
            try:
                safe_rel(rel)
                reject_links(p)
            except (OSError, ValueError):
                gaps.append('unsafe_or_link_dir:' + rel)
                return False
            if name in SKIP_DIRS:
                gaps.append('default_excluded_dir:' + rel)
                return False
            return True
        dirs[:] = sorted(d for d in dirs if allowed_dir(d))
        for name in sorted(files):
            p = here / name
            rel = p.relative_to(root).as_posix()
            if not match(rel, include) or match(rel, exclude):
                continue
            if len(entries) >= max_files:
                gaps.append('max_files')
                break
            try:
                safe_rel(rel)
                digest, size = _read_stable_file(p, root, max_bytes - total)
                total += size
                entries.append({'path': rel, 'sha256': digest, 'bytes': size})
            except OverflowError:
                gaps.append('max_bytes')
                break
            except OSError:
                gaps.append('unreadable:' + rel)
                break  # do not spend an unbounded read budget on unstable files
            except ValueError:
                gaps.append('unstable_or_unsafe_file:' + rel)
                break
        if gaps and gaps[-1].split(':')[0] in {'max_files','max_bytes','unreadable','unstable_or_unsafe_file'}:
            break
    if not entries:
        gaps.append('no_files_in_scope')
    entries.sort(key=lambda x: x['path'])
    return {'snapshot_sha256': sha_bytes(canonical(entries)), 'files': entries,
            'files_scanned': len(entries), 'total_bytes': total, 'gaps': gaps,
            'truncated': 'max_files' in gaps or 'max_bytes' in gaps}


def validate_schema(obj, schema_name):
    """Validate supported JSON Schema 2020-12 subset used by the three bundled schemas.

    Unsupported schema keywords MUST be rejected (no silent downgrade).
    """
    spec = load(Path(__file__).resolve().parents[1] / 'schemas' / (schema_name + '.schema.json'))
    errors=[]
    allowed={'$schema','$id','title','type','required','properties','items','additionalProperties',
             'const','enum','pattern','minLength','minimum','exclusiveMinimum','minItems','uniqueItems','format'}
    def run(v, s, loc):
        unknown=set(s)-allowed
        if unknown: raise ValueError('unsupported JSON schema keywords: '+repr(sorted(unknown)))
        kinds=s.get('type')
        if kinds is not None:
            kinds=kinds if isinstance(kinds,list) else [kinds]
            def good(k):
                return {'object': lambda: isinstance(v,dict), 'array':lambda:isinstance(v,list),
                        'string':lambda:isinstance(v,str),'null':lambda:v is None,
                        'integer':lambda:isinstance(v,int) and not isinstance(v,bool),
                        'number':lambda:isinstance(v,(float,int)) and not isinstance(v,bool),
                        'boolean':lambda:isinstance(v,bool)}[k]()
            if not any(good(k) for k in kinds):errors.append(loc+': invalid type');return
        if 'const' in s and v!=s['const']:errors.append(loc+': const mismatch')
        if 'enum' in s and v not in s['enum']:errors.append(loc+': enum mismatch')
        if isinstance(v,str):
            if len(v)<s.get('minLength',0):errors.append(loc+': too short')
            if 'pattern' in s and re.search(s['pattern'],v) is None:errors.append(loc+': pattern mismatch')
            if s.get('format')=='date-time':
                from datetime import datetime
                try:
                    d=datetime.fromisoformat(v.replace('Z','+00:00'))
                    if d.tzinfo is None:raise ValueError('missing timezone')
                except ValueError:errors.append(loc+': invalid date-time')
        if isinstance(v,(int,float)) and not isinstance(v,bool):
            if 'minimum' in s and v<s['minimum']:errors.append(loc+': below min')
            if 'exclusiveMinimum' in s and v<=s['exclusiveMinimum']:errors.append(loc+': below exclusive min')
        if isinstance(v,dict):
            for k in s.get('required',[]):
                if k not in v:errors.append(loc+'.'+k+': required')
            props=s.get('properties',{})
            for k,value in v.items():
                if k in props:run(value,props[k],loc+'.'+k)
                elif s.get('additionalProperties') is False: errors.append(loc+'.'+k+': additional property')
        if isinstance(v,list):
            if len(v)<s.get('minItems',0):errors.append(loc+': fewer than minItems')
            if s.get('uniqueItems') and len({canonical(x) for x in v})!=len(v):errors.append(loc+': duplicates')
            if 'items' in s:
                for i,x in enumerate(v):run(x,s['items'],loc+'['+str(i)+']')
    run(obj,spec,'$')
    if errors:raise ValueError('schema '+schema_name+': '+'; '.join(errors[:15]))


def current_git(root):
    def call(*args):
        p=subprocess.run(['git', '-C',str(root),*args], capture_output=True, text=True, timeout=8)
        return p.stdout.strip() if p.returncode==0 else None
    try:
        rev=call('rev-parse','HEAD')
        dirty=call('status','--porcelain','--untracked-files=normal')
        return rev, bool(dirty) if dirty is not None else None
    except (OSError, subprocess.TimeoutExpired): return None,None


def platform_name():
    return {'win32':'Windows','darwin':'macOS','linux':'Linux'}.get(sys.platform,'Other')


def evidence_hash_ok(ev, evidence_dir):
    locator=ev['locator']
    # Never treat external URLs or virtual fixtures as verifiable local evidence.
    p=Path(locator)
    if p.is_absolute() or '..' in p.parts or locator.startswith(('/', '\\')):
        return False
    root=Path(evidence_dir).resolve(strict=True)
    f=(root/p).resolve()
    return f.is_relative_to(root) and f.is_file() and not (root/p).is_symlink() and sha_file(f)==ev['sha256']
