#!/usr/bin/env python3
"""Local byte transport for authenticated ALIFE Vault MCP calls.

No HTTP, credentials, artifact execution or archive extraction. The caller owns
authentication and project authorization; matching IDs are integrity checks.
"""
from __future__ import annotations

import argparse
import base64
import binascii
from contextlib import contextmanager
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import stat
import tempfile

CHUNK_BYTES = 49152
MAX_BYTES = 32 * 1024 * 1024
MAX_JSON = 128 * 1024
SHA256 = re.compile(r'[0-9a-f]{64}\Z')


class VaultBytesError(ValueError):
    pass


def no_links(path: Path) -> None:
    for item in (path, *path.parents):
        try:
            entry = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(entry.st_mode) or getattr(entry, 'st_file_attributes', 0) & 0x400:
            raise VaultBytesError('SYMLINK_OR_REPARSE_POINT')


@contextmanager
def open_regular(path: Path):
    no_links(path)
    if not stat.S_ISREG(path.stat().st_mode):
        raise VaultBytesError('NOT_A_REGULAR_FILE')
    flags = (os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
             | getattr(os, 'O_NONBLOCK', 0))
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise VaultBytesError('NOT_A_REGULAR_FILE')
        handle = os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise
    with handle:
        yield handle, info.st_size


def chunk_count(size: int) -> int:
    return (size + CHUNK_BYTES - 1) // CHUNK_BYTES


def integer(value, minimum: int, maximum: int, label: str) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise VaultBytesError('INVALID_' + label)
    return value


def read_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise VaultBytesError('DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def constant(_):
        raise VaultBytesError('NONFINITE_JSON')
    with open_regular(path) as (handle, size):
        if size > MAX_JSON:
            raise VaultBytesError('JSON_TOO_LARGE')
        raw = handle.read(MAX_JSON + 1)
    if len(raw) > MAX_JSON:
        raise VaultBytesError('JSON_TOO_LARGE')
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise VaultBytesError('INVALID_JSON') from exc
    if not isinstance(result, dict):
        raise VaultBytesError('JSON_OBJECT_REQUIRED')
    return result


def inspect_file(path: Path) -> dict:
    digest = hashlib.sha256()
    total = 0
    with open_regular(path) as (handle, size):
        integer(size, 0, MAX_BYTES, 'FILE_SIZE')
        for data in iter(lambda: handle.read(CHUNK_BYTES), b''):
            total += len(data)
            integer(total, 0, MAX_BYTES, 'FILE_SIZE')
            digest.update(data)
    if total != size:
        raise VaultBytesError('SOURCE_SIZE_CHANGED')
    return {'filename': path.name, 'media_type': mimetypes.guess_type(path.name)[0] or 'application/octet-stream',
            'bytes': total, 'sha256': digest.hexdigest(), 'chunk_bytes': CHUNK_BYTES,
            'total_chunks': chunk_count(total), 'execution': 'NOT_RUN'}


def encode_chunk(path: Path, index: int) -> dict:
    with open_regular(path) as (handle, size):
        integer(size, 0, MAX_BYTES, 'FILE_SIZE')
        integer(index, 0, chunk_count(size) - 1, 'CHUNK_INDEX')
        handle.seek(index * CHUNK_BYTES)
        data = handle.read(CHUNK_BYTES)
        if len(data) != min(CHUNK_BYTES, size - index * CHUNK_BYTES):
            raise VaultBytesError('SOURCE_SIZE_CHANGED')
    return {'chunk_index': index, 'data_base64': base64.b64encode(data).decode('ascii'),
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def validate_metadata(meta: dict) -> dict:
    for key in ('artifact_id', 'project_id', 'filename', 'media_type'):
        value = meta.get(key)
        if not isinstance(value, str) or not value or len(value) > 512 or any(ord(c) < 32 for c in value):
            raise VaultBytesError('INVALID_' + key.upper())
        value.encode('utf-8')
    if meta['filename'] in ('.', '..') or any(c in meta['filename'] for c in '/\\'):
        raise VaultBytesError('INVALID_FILENAME')
    integer(meta.get('revision'), 1, 2**53 - 1, 'REVISION')
    size = integer(meta.get('bytes'), 0, MAX_BYTES, 'FILE_SIZE')
    if type(meta.get('chunk_bytes')) is not int or meta['chunk_bytes'] != CHUNK_BYTES:
        raise VaultBytesError('INVALID_CHUNK_BYTES')
    count = integer(meta.get('total_chunks'), 0, chunk_count(MAX_BYTES), 'TOTAL_CHUNKS')
    if count != chunk_count(size):
        raise VaultBytesError('TOTAL_CHUNKS_MISMATCH')
    if not isinstance(meta.get('sha256'), str) or not SHA256.fullmatch(meta['sha256']):
        raise VaultBytesError('INVALID_FILE_SHA256')
    if meta.get('execution') != 'NOT_RUN':
        raise VaultBytesError('INVALID_EXECUTION_STATE')
    return meta


def decode_chunk(chunk: dict, meta: dict, index: int) -> bytes:
    for key in ('artifact_id', 'project_id', 'revision', 'filename', 'total_chunks'):
        if type(chunk.get(key)) is not type(meta[key]) or chunk[key] != meta[key]:
            raise VaultBytesError('CHUNK_' + key.upper() + '_MISMATCH')
    if type(chunk.get('chunk_index')) is not int or chunk['chunk_index'] != index:
        raise VaultBytesError('CHUNK_SEQUENCE_MISMATCH')
    if type(chunk.get('file_bytes')) is not int or chunk['file_bytes'] != meta['bytes']:
        raise VaultBytesError('CHUNK_FILE_SIZE_MISMATCH')
    if chunk.get('file_sha256') != meta['sha256']:
        raise VaultBytesError('CHUNK_FILE_HASH_MISMATCH')
    expected_next = index + 1 if index + 1 < meta['total_chunks'] else None
    if type(chunk.get('next_chunk_index')) is not type(expected_next) or chunk['next_chunk_index'] != expected_next:
        raise VaultBytesError('NEXT_CHUNK_MISMATCH')
    if chunk.get('execution') != 'NOT_RUN':
        raise VaultBytesError('INVALID_EXECUTION_STATE')
    encoded = chunk.get('data_base64')
    if not isinstance(encoded, str) or len(encoded) > CHUNK_BYTES * 4 // 3:
        raise VaultBytesError('INVALID_BASE64')
    try:
        data = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise VaultBytesError('INVALID_BASE64') from exc
    if base64.b64encode(data).decode('ascii') != encoded:
        raise VaultBytesError('NONCANONICAL_BASE64')
    expected_size = min(CHUNK_BYTES, meta['bytes'] - index * CHUNK_BYTES)
    if type(chunk.get('bytes')) is not int or chunk['bytes'] != expected_size or len(data) != expected_size:
        raise VaultBytesError('CHUNK_SIZE_MISMATCH')
    if hashlib.sha256(data).hexdigest() != chunk.get('sha256'):
        raise VaultBytesError('CHUNK_HASH_MISMATCH')
    return data


def assemble(metadata: Path, chunks_dir: Path, output: Path) -> dict:
    meta = validate_metadata(read_json(metadata))
    no_links(chunks_dir)
    if not chunks_dir.is_dir():
        raise VaultBytesError('CHUNKS_DIRECTORY_REQUIRED')
    expected = {f'{index:06d}.json' for index in range(meta['total_chunks'])}
    if {path.name for path in chunks_dir.iterdir()} != expected:
        raise VaultBytesError('CHUNK_FILES_MISMATCH')
    if output.exists() or output.is_symlink():
        raise VaultBytesError('OUTPUT_ALREADY_EXISTS')
    no_links(output)
    parent = output.parent.resolve(strict=True)
    output = parent / output.name
    temporary = None
    digest = hashlib.sha256()
    total = 0
    try:
        with tempfile.NamedTemporaryFile(dir=parent, prefix='.alife-vault-', delete=False) as handle:
            temporary = Path(handle.name)
            for index in range(meta['total_chunks']):
                chunk = read_json(chunks_dir / f'{index:06d}.json')
                data = decode_chunk(chunk, meta, index)
                handle.write(data)
                digest.update(data)
                total += len(data)
            if total != meta['bytes'] or digest.hexdigest() != meta['sha256']:
                raise VaultBytesError('FILE_INTEGRITY_MISMATCH')
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise VaultBytesError('OUTPUT_ALREADY_EXISTS') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'status': 'ASSEMBLED', 'artifact_id': meta['artifact_id'], 'project_id': meta['project_id'],
            'revision': meta['revision'], 'bytes': total, 'sha256': digest.hexdigest(),
            'output': str(output), 'execution': 'NOT_RUN'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    inspect = sub.add_parser('inspect'); inspect.add_argument('path', type=Path)
    encode = sub.add_parser('encode'); encode.add_argument('path', type=Path)
    encode.add_argument('--index', type=int, required=True)
    combine = sub.add_parser('assemble')
    combine.add_argument('--metadata', type=Path, required=True)
    combine.add_argument('--chunks-dir', type=Path, required=True)
    combine.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'inspect':
            result = inspect_file(args.path)
        elif args.action == 'encode':
            result = encode_chunk(args.path, args.index)
        else:
            result = assemble(args.metadata, args.chunks_dir, args.output)
    except (OSError, ValueError, KeyError, RecursionError) as exc:
        print(json.dumps({'status': 'BLOCKED', 'reason': str(exc), 'execution': 'NOT_RUN'}))
        return 3
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
