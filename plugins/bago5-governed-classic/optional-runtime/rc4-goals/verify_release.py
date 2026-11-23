"""Verify integrity of RC2 base and additive sibling bridge without writing source files."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT=Path(__file__).resolve().parent.parent
BRIDGE=Path(__file__).resolve().parent
MANIFEST=ROOT/'PAQUETE_SHA256.json'
BASE=ROOT/'BAGO5os_1.4.7_CONTEXT_LIFECYCLE_NATIVE_RC2_INSTALLED.zip'
SUITE=ROOT/'bago-operating-suite'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    try:
        manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert manifest['schema']=='bago.goals-codex.rc4-stop-recovery.manifest.v1'
        if manifest.get('source_zip_sha256')!='036a0f925d0dc90ce20934dfe9c3a4631126c57be8af8854aebd5627d7e17796' or manifest.get('derivative_id')!='RC4_STOP_RECOVERY':
            raise ValueError('Source provenance or derivative identity mismatch')
        if digest(BASE)!=manifest['original_zip_sha256']:
            raise ValueError('Original ZIP SHA256 changed')
        actual={p.relative_to(ROOT).as_posix():digest(p) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PAQUETE_SHA256.json'}
        if actual!=manifest['files']:
            raise ValueError('Package file manifest differs: missing/extra/modified')
        with zipfile.ZipFile(BASE) as z:
            for n in z.namelist():
                if n.endswith('/'):continue
                if digest(ROOT/n)!=hashlib.sha256(z.read(n)).hexdigest():
                    raise ValueError('Original base byte changed: '+n)
        sys.path.insert(0,str(SUITE/'scripts'))
        from suite_identity import current_identity
        identity=current_identity(SUITE)
        if identity['payload_files']!=600 or identity['release_id']!='BAGO-SUITE-147-BAGO-SKILL-RC2':
            raise ValueError('Original identity mismatch')
        print(json.dumps({'status':'PASS','derivative_id':manifest['derivative_id'],'source_zip_sha256':manifest['source_zip_sha256'],'original_identity':identity,'original_files':603,
                          'package_files':len(actual),'original_zip_sha256':digest(BASE)},indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({'status':'FAIL','reason':str(exc)},indent=2))
        return 1

if __name__=='__main__':
    raise SystemExit(main())
