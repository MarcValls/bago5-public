#!/usr/bin/env python3
"""Verifica integridad del pack extraído; no demuestra funcionamiento ni firma."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Clave duplicada en el manifiesto: ' + key)
        result[key] = value
    return result


def _link_or_reparse(path):
    info = path.lstat()
    return (stat.S_ISLNK(info.st_mode) or
            bool(getattr(info, 'st_file_attributes', 0) & 0x400))


def _walk_error(error):
    raise error


def verify(root):
    """Comprueba todos los archivos, sin cargar codigo del paquete ni seguir enlaces."""
    root = Path(root).resolve()
    try:
        manifest_path = root / 'SHA256SUMS.json'
        if _link_or_reparse(manifest_path):
            raise ValueError('El manifiesto no puede ser un enlace o punto de reanalisis.')
        manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'),
                              object_pairs_hook=_unique_object)
        if not isinstance(manifest, dict) or not manifest:
            raise ValueError('El manifiesto debe ser un objeto no vacio de rutas y SHA-256.')
        failures = []
        for name, expected in manifest.items():
            relative = PurePosixPath(name)
            if (not name or relative.is_absolute() or
                    any(part in ('', '.', '..') for part in name.split('/')) or
                    '\\' in name or ':' in name):
                failures.append({'file': name, 'reason': 'UNSAFE_MANIFEST_PATH'})
                continue
            if (not isinstance(expected, str) or len(expected) != 64 or
                    any(char not in '0123456789abcdefABCDEF' for char in expected)):
                failures.append({'file': name, 'reason': 'INVALID_SHA256'})
                continue
            path = root/Path(*relative.parts)
            chain = [root.joinpath(*relative.parts[:end])
                     for end in range(1, len(relative.parts) + 1)]
            if (not path.is_file() or not path.resolve().is_relative_to(root) or
                    any(_link_or_reparse(part) for part in chain)):
                failures.append({'file': name, 'reason': 'MISSING_OR_UNSAFE_FILE'})
            elif sha(path) != expected.lower():
                failures.append({'file': name, 'reason': 'SHA256_MISMATCH'})
        actual = set()
        for folder, directories, files in os.walk(root, followlinks=False, onerror=_walk_error):
            safe_directories = []
            for name in sorted(directories):
                path = Path(folder) / name
                if _link_or_reparse(path):
                    failures.append({'file': path.relative_to(root).as_posix(),
                                     'reason': 'SYMLINK_OR_REPARSE_POINT'})
                else:
                    safe_directories.append(name)
            directories[:] = safe_directories
            for name in files:
                path = Path(folder) / name
                relative = path.relative_to(root).as_posix()
                actual.add(relative)
                if _link_or_reparse(path):
                    failures.append({'file': relative, 'reason': 'SYMLINK_OR_REPARSE_POINT'})
        unexpected = sorted(actual - set(manifest) - {'SHA256SUMS.json'})
        result = {'status': 'FAIL' if failures or unexpected else 'PASS',
                  'expected_files': len(manifest), 'failures': failures, 'unexpected': unexpected,
                  'identity': 'SELF_DECLARED_SHA256_UNSIGNED',
                  'scope': 'Integridad de archivos del pack; no firma ni equivalencia funcional.'}
    except (OSError, ValueError, TypeError) as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
    return result


def main():
    result = verify(Path(__file__).resolve().parent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
