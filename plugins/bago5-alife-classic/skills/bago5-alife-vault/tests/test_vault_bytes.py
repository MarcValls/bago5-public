import base64
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'vault_bytes.py'
spec = importlib.util.spec_from_file_location('alife_mcp_vault_bytes', SCRIPT)
vault = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vault)


class ByteTransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.bin'
        self.metadata = self.root / 'metadata.json'
        self.chunks = self.root / 'chunks'
        self.chunks.mkdir()
        self.output = self.root / 'output.bin'

    def fixture(self, data):
        self.source.write_bytes(data)
        meta = vault.inspect_file(self.source)
        meta.update(artifact_id='artifact-a', project_id='project-a', revision=1,
                    source='test:synthetic', created_at='2026-11-20T00:00:00Z')
        self.metadata.write_text(json.dumps(meta), encoding='utf-8')
        for index in range(meta['total_chunks']):
            chunk = vault.encode_chunk(self.source, index)
            chunk.update(artifact_id=meta['artifact_id'], project_id=meta['project_id'],
                         revision=meta['revision'], filename=meta['filename'],
                         total_chunks=meta['total_chunks'], file_bytes=meta['bytes'],
                         file_sha256=meta['sha256'], execution='NOT_RUN',
                         next_chunk_index=index + 1 if index + 1 < meta['total_chunks'] else None)
            (self.chunks / f'{index:06d}.json').write_text(json.dumps(chunk), encoding='utf-8')
        return meta

    def altered_chunk(self, **changes):
        path = self.chunks / '000000.json'
        data = json.loads(path.read_text())
        data.update(changes)
        path.write_text(json.dumps(data), encoding='utf-8')

    def assert_failure_clean(self, error):
        with self.assertRaisesRegex(vault.VaultBytesError, error):
            vault.assemble(self.metadata, self.chunks, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.alife-vault-*')), [])

    def test_real_zip_roundtrip_preserves_bytes_without_extraction(self):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('directory/hello.txt', 'Texto original\r\n')
            archive.writestr('binary.bin', bytes(range(256)) * 500)
        payload = stream.getvalue()
        self.fixture(payload)
        result = vault.assemble(self.metadata, self.chunks, self.output)
        self.assertEqual(self.output.read_bytes(), payload)
        self.assertEqual(result['sha256'], hashlib.sha256(payload).hexdigest())
        self.assertFalse((self.root / 'directory').exists())

    def test_actual_cli_preserves_python_bytes_and_does_not_execute(self):
        sentinel = self.root / 'not-executed'
        data = ('from pathlib import Path\r\nPath(' + repr(str(sentinel)) + ').touch()\r\n').encode()
        self.fixture(data)
        result = subprocess.run([sys.executable, '-B', str(SCRIPT), 'assemble',
            '--metadata', str(self.metadata), '--chunks-dir', str(self.chunks), '--output', str(self.output)],
            text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'ASSEMBLED')
        self.assertEqual(self.output.read_bytes(), data)
        self.assertFalse(sentinel.exists())

    def test_empty_file_uses_no_chunks(self):
        meta = self.fixture(b'')
        self.assertEqual(meta['total_chunks'], 0)
        self.assertEqual(vault.assemble(self.metadata, self.chunks, self.output)['bytes'], 0)
        self.assertEqual(self.output.read_bytes(), b'')
        with self.assertRaisesRegex(vault.VaultBytesError, 'INVALID_CHUNK_INDEX'):
            vault.encode_chunk(self.source, 0)

    def test_chunk_boundaries_and_invalid_indexes(self):
        self.source.write_bytes(b'a' * vault.CHUNK_BYTES + b'bc')
        self.assertEqual(vault.inspect_file(self.source)['total_chunks'], 2)
        self.assertEqual(vault.encode_chunk(self.source, 0)['bytes'], vault.CHUNK_BYTES)
        self.assertEqual(base64.b64decode(vault.encode_chunk(self.source, 1)['data_base64']), b'bc')
        for index in (-1, 2, True):
            with self.assertRaisesRegex(vault.VaultBytesError, 'INVALID_CHUNK_INDEX'):
                vault.encode_chunk(self.source, index)

    def test_oversize_file_rejected_before_reading_payload(self):
        with self.source.open('wb') as handle:
            handle.truncate(vault.MAX_BYTES + 1)
        for action in (lambda: vault.inspect_file(self.source), lambda: vault.encode_chunk(self.source, 0)):
            with self.assertRaisesRegex(vault.VaultBytesError, 'INVALID_FILE_SIZE'):
                action()

    def test_mismatched_identity_revision_and_sequence_are_rejected(self):
        self.fixture(b'bytes')
        original = (self.chunks / '000000.json').read_bytes()
        for change in ({'artifact_id': 'other'}, {'project_id': 'other'}, {'revision': 2},
                       {'revision': True}, {'filename': 'other.bin'}, {'chunk_index': 1},
                       {'total_chunks': 2}, {'file_bytes': 7}, {'file_sha256': '0' * 64},
                       {'next_chunk_index': 1}):
            with self.subTest(change=change):
                self.altered_chunk(**change)
                self.assert_failure_clean('MISMATCH')
                (self.chunks / '000000.json').write_bytes(original)

    def test_corrupt_base64_chunk_hash_and_lengths_are_rejected(self):
        self.fixture(b'bytes')
        original = (self.chunks / '000000.json').read_bytes()
        for change in ({'data_base64': '!invalid!'}, {'sha256': '0' * 64}, {'bytes': 4},
                       {'data_base64': base64.b64encode(b'other').decode()}):
            self.altered_chunk(**change)
            self.assert_failure_clean('BASE64|HASH|SIZE')
            (self.chunks / '000000.json').write_bytes(original)

    def test_total_hash_is_verified_after_all_valid_chunks(self):
        meta = self.fixture(b'original')
        meta['sha256'] = '0' * 64
        self.metadata.write_text(json.dumps(meta))
        self.altered_chunk(file_sha256=meta['sha256'])
        self.assert_failure_clean('FILE_INTEGRITY_MISMATCH')

    def test_missing_and_extra_chunk_files_are_rejected(self):
        self.fixture(b'bytes')
        path = self.chunks / '000000.json'
        backup = path.read_bytes()
        path.unlink()
        self.assert_failure_clean('CHUNK_FILES_MISMATCH')
        path.write_bytes(backup)
        (self.chunks / '000001.json').write_bytes(backup)
        self.assert_failure_clean('CHUNK_FILES_MISMATCH')

    def test_existing_output_is_preserved(self):
        self.fixture(b'bytes')
        self.output.write_bytes(b'preserve')
        with self.assertRaisesRegex(vault.VaultBytesError, 'OUTPUT_ALREADY_EXISTS'):
            vault.assemble(self.metadata, self.chunks, self.output)
        self.assertEqual(self.output.read_bytes(), b'preserve')

    def test_concurrent_output_is_preserved(self):
        self.fixture(b'bytes')
        real_link = os.link
        def race(source, destination):
            self.output.write_bytes(b'concurrent writer')
            return real_link(source, destination)
        with mock.patch.object(vault.os, 'link', side_effect=race):
            with self.assertRaisesRegex(vault.VaultBytesError, 'OUTPUT_ALREADY_EXISTS'):
                vault.assemble(self.metadata, self.chunks, self.output)
        self.assertEqual(self.output.read_bytes(), b'concurrent writer')
        self.assertEqual(list(self.root.glob('.alife-vault-*')), [])

    def test_symlink_input_and_chunk_are_rejected(self):
        self.fixture(b'bytes')
        alias = self.root / 'alias.bin'
        alias.symlink_to(self.source)
        with self.assertRaisesRegex(vault.VaultBytesError, 'SYMLINK'):
            vault.inspect_file(alias)
        path = self.chunks / '000000.json'
        backup = self.root / 'original-chunk.json'
        path.rename(backup)
        path.symlink_to(backup)
        self.assert_failure_clean('SYMLINK')

    def test_symlink_output_parent_is_rejected(self):
        self.fixture(b'bytes')
        alias = self.root / 'alias-dir'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(vault.VaultBytesError, 'SYMLINK'):
            vault.assemble(self.metadata, self.chunks, alias / 'new.bin')
        self.assertFalse((self.root / 'new.bin').exists())

    def test_malformed_json_returns_structured_cli_error(self):
        for raw in ('{"bytes":0,"bytes":1}', '{"bytes":NaN}', 'not-json'):
            self.metadata.write_text(raw)
            captured = io.StringIO()
            with contextlib.redirect_stdout(captured):
                code = vault.main(['assemble', '--metadata', str(self.metadata),
                                   '--chunks-dir', str(self.chunks), '--output', str(self.output)])
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(captured.getvalue())['status'], 'BLOCKED')
            self.assertFalse(self.output.exists())

    def test_metadata_chunk_count_and_boolean_size_are_rejected(self):
        meta = self.fixture(b'bytes')
        for changes in ({'total_chunks': 0}, {'bytes': True}, {'chunk_bytes': 49153},
                        {'revision': 0}, {'execution': 'RUN'}, {'filename': '../escape'}):
            self.metadata.write_text(json.dumps({**meta, **changes}))
            self.assert_failure_clean('INVALID|MISMATCH')


if __name__ == '__main__':
    unittest.main()
