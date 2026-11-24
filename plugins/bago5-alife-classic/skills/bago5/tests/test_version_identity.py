"""Comprobar las superficies reales de versión y su actualización acotada."""
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / 'scripts/bago5_version.py'
_spec = importlib.util.spec_from_file_location('bago5_version', SCRIPT)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
VERSION = '0.4.40'


class VersionIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for relative in _module.PATHS.values():
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
        self.write_json('plugin.json', {'name': 'bago5-governed-classic', 'version': VERSION})
        self.write_json('.codex-plugin/plugin.json', {
            'name': 'bago5-governed-classic', 'version': VERSION,
            'apps': './.app.json', 'interface': {
                'displayName': f'BAGO5 Gobernado ({VERSION})',
                'defaultPrompt': 'Conservar este prompt: v0.4.36 es historia.',
            },
        })
        self.write('skills/bago5/agents/openai.yaml',
                   f'interface:\n  display_name: $bago5 ({VERSION})\n'
                   '  default_prompt: Conservar la referencia histórica 0.4.36\n'
                   'policy:\n  allow_implicit_invocation: true\n')
        self.write('skills/bago5/SKILL.md',
                   f'---\nname: bago5\ndescription: Entrada\n---\n\n# $bago5 ({VERSION})\n\n'
                   'Historial: 0.4.36; permisos y STOP siguen vigentes.\n')
        self.write_json('skills/bago5/references/CATALOGO_HABILIDADES.json', {
            'schema': 'bago5.catalogo-habilidades.v1', 'version': VERSION,
            'entry': '$bago5', 'entry_display_name': f'$bago5 ({VERSION})',
            'skills': [
                {'new_name': 'bago5', 'display_name': f'$bago5 ({VERSION})',
                 'new_path': 'skills/bago5/SKILL.md', 'invocation': '$bago5'},
                {'new_name': 'bago5-test', 'display_name': 'Prueba 0.4.36', 'scope': 'publica'},
            ],
            'legacy_aliases': {'bago5-old': 'bago5-test'},
        })
        self.write_json('skills/bago5/references/ROUTES.json', {
            'plugin': 'bago5-governed-classic', 'plugin_version': VERSION,
            'entry_skill': 'skills/bago5/SKILL.md', 'source_suite_version': '1.4.8-local-unified',
            'routes': [{'command': '$bago5-old', 'target': 'skills/bago5-test/SKILL.md'}],
            'historical_evidence': {'version': '0.4.36', 'status': 'NOT_RUN'},
        })

    def write(self, relative, value):
        (self.root / relative).write_text(value, encoding='utf-8')

    def write_json(self, relative, value):
        self.write(relative, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

    def read_json(self, relative):
        return json.loads((self.root / relative).read_text(encoding='utf-8'))

    def test_consistent_distribution(self):
        result = _module.inspect(self.root)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['package_version'], VERSION)
        self.assertEqual(len(result['checked']), 9)
        self.assertEqual(result['root'], str(self.root.resolve()))
        self.assertFalse(result['active_host_release_verified'])

    def test_every_required_source_is_checked(self):
        for relative in _module.PATHS.values():
            with self.subTest(source=relative):
                path = self.root / relative
                contents = path.read_bytes()
                path.unlink()
                result = _module.inspect(self.root)
                self.assertEqual(result['status'], 'FAIL')
                expected = None if relative in ('plugin.json', '.codex-plugin/plugin.json') else VERSION
                self.assertEqual(result['package_version'], expected)
                path.write_bytes(contents)

    def test_stale_heading_and_yaml_are_detected(self):
        for relative in ('skills/bago5/SKILL.md', 'skills/bago5/agents/openai.yaml'):
            with self.subTest(source=relative):
                path = self.root / relative
                before = path.read_text()
                path.write_text(before.replace(VERSION, '0.4.36'), encoding='utf-8')
                result = _module.inspect(self.root)
                self.assertEqual(result['status'], 'FAIL')
                self.assertEqual(result['package_version'], VERSION)
                self.assertFalse(result['active_host_release_verified'])
                path.write_text(before, encoding='utf-8')

    def test_every_json_version_surface_is_checked(self):
        cases = [
            ('plugin.json', ('version',)),
            ('.codex-plugin/plugin.json', ('version',)),
            ('.codex-plugin/plugin.json', ('interface', 'displayName')),
            ('skills/bago5/references/CATALOGO_HABILIDADES.json', ('version',)),
            ('skills/bago5/references/CATALOGO_HABILIDADES.json', ('entry_display_name',)),
            ('skills/bago5/references/CATALOGO_HABILIDADES.json', ('skills', 0, 'display_name')),
            ('skills/bago5/references/ROUTES.json', ('plugin_version',)),
        ]
        for relative, keys in cases:
            with self.subTest(source=relative, keys=keys):
                original = (self.root / relative).read_text()
                obj = json.loads(original)
                target = obj
                for key in keys[:-1]:
                    target = target[key]
                target[keys[-1]] = target[keys[-1]].replace(VERSION, '0.4.36')
                self.write_json(relative, obj)
                result = _module.inspect(self.root)
                self.assertEqual(result['status'], 'FAIL')
                expected = None if relative in ('plugin.json', '.codex-plugin/plugin.json') and keys == ('version',) else VERSION
                self.assertEqual(result['package_version'], expected)
                self.write(relative, original)

    def test_malformed_json_roots_and_versions_fail_without_exception(self):
        for relative in ('plugin.json', '.codex-plugin/plugin.json'):
            original = (self.root / relative).read_text()
            for invalid in (None, [], 123, 'version', {'name': 'bago5-governed-classic', 'version': []},
                            {'name': 'bago5-governed-classic', 'version': None}):
                with self.subTest(source=relative, invalid=invalid):
                    self.write_json(relative, invalid)
                    result = _module.inspect(self.root)
                    self.assertEqual(result['status'], 'FAIL')
                    self.assertIsNone(result['package_version'])
            self.write(relative, '{invalid JSON')
            result = _module.inspect(self.root)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIsNone(result['package_version'])
            self.write(relative, original)

    def test_malformed_route_metadata_fails_without_exception(self):
        relative = 'skills/bago5/references/ROUTES.json'
        original = self.read_json(relative)
        for invalid in (None, [], 123, 'routes'):
            with self.subTest(root=invalid):
                self.write_json(relative, invalid)
                self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')
                self.assertEqual(_module.synchronize(self.root)['changed_paths'], [])
        for invalid in (None, [], {}, '0.4', 40):
            with self.subTest(version=invalid):
                value = {**original, 'plugin_version': invalid}
                self.write_json(relative, value)
                self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')
        self.write(relative, '{invalid JSON')
        self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')

    def test_wrong_identity_and_catalog_entry_fail(self):
        for relative in ('plugin.json', '.codex-plugin/plugin.json'):
            plugin = self.read_json(relative)
            plugin['name'] = 'unrelated'
            self.write_json(relative, plugin)
            result = _module.inspect(self.root)
            self.assertEqual(result['status'], 'FAIL')
            self.assertIsNone(result['package_version'])
            plugin['name'] = 'bago5-governed-classic'
            self.write_json(relative, plugin)
        relative = 'skills/bago5/references/CATALOGO_HABILIDADES.json'
        catalog = self.read_json(relative)
        catalog['skills'][0]['new_path'] = 'skills/unrelated/SKILL.md'
        self.write_json(relative, catalog)
        result = _module.inspect(self.root)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['package_version'], VERSION)

    def test_duplicate_main_surfaces_fail(self):
        for relative, addition in (
            ('skills/bago5/SKILL.md', f'\n# $bago5 ({VERSION})\n'),
            ('skills/bago5/agents/openai.yaml', f'  display_name: $bago5 ({VERSION})\n'),
        ):
            with self.subTest(source=relative):
                original = (self.root / relative).read_text()
                self.write(relative, original + addition)
                self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')
                self.write(relative, original)
        relative = 'skills/bago5/references/CATALOGO_HABILIDADES.json'
        catalog = self.read_json(relative)
        catalog['skills'].append(catalog['skills'][0])
        self.write_json(relative, catalog)
        self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')

    def test_quoted_yaml_label_is_supported(self):
        for quote in ('"', "'"):
            with self.subTest(quote=quote):
                self.write('skills/bago5/agents/openai.yaml',
                           f'interface:\n  display_name: {quote}$bago5 ({VERSION}){quote}\n')
                self.assertEqual(_module.inspect(self.root)['status'], 'PASS')

    def test_yaml_label_in_another_section_does_not_identify_the_skill(self):
        for text in (
            f'interface:\n  short_description: Entrada\npolicy:\n  display_name: $bago5 ({VERSION})\n',
            f'interface:\n  nested:\n    display_name: $bago5 ({VERSION})\n',
        ):
            with self.subTest(text=text):
                self.write('skills/bago5/agents/openai.yaml', text)
                self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')
                self.assertEqual(_module.synchronize(self.root)['changed_paths'], [])

    def test_strict_semver(self):
        for version in ('0.4.40', '1.0.0-rc.1+build.7', '2.3.4+007', '2.3.4-alpha-x.0'):
            with self.subTest(version=version):
                self.assertIsNotNone(_module.VERSION_PATTERN.fullmatch(version))
        for version in ('01.4.40', '1.0.0-01', '1.0.0-', '1.0.0+', '1.0', 'v1.0.0', '1.0.0 a'):
            with self.subTest(version=version):
                self.assertIsNone(_module.VERSION_PATTERN.fullmatch(version))

    def test_portable_interface_when_declared_is_checked(self):
        plugin = self.read_json('plugin.json')
        plugin['extensions'] = {'com.openai': {'interface': {'displayName': 'BAGO5 (0.4.36)'}}}
        self.write_json('plugin.json', plugin)
        result = _module.inspect(self.root)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['package_version'], VERSION)
        self.assertEqual(_module.synchronize(self.root)['status'], 'PASS')
        self.assertEqual(self.read_json('plugin.json')['extensions']['com.openai']['interface']['displayName'], f'BAGO5 ({VERSION})')

    def test_sync_updates_live_labels_and_preserves_other_contents(self):
        plugin = self.read_json('plugin.json')
        plugin['version'] = '0.4.41'
        self.write_json('plugin.json', plugin)
        codex_before = self.read_json('.codex-plugin/plugin.json')
        catalog_before = self.read_json('skills/bago5/references/CATALOGO_HABILIDADES.json')
        routes_before = self.read_json('skills/bago5/references/ROUTES.json')
        self.assertEqual(_module.inspect(self.root)['status'], 'FAIL')
        result = _module.synchronize(self.root)
        self.assertEqual(result['status'], 'PASS', result)
        self.assertEqual(result['package_version'], '0.4.41')
        self.assertEqual(len(result['changed_paths']), 5)
        codex_after = self.read_json('.codex-plugin/plugin.json')
        self.assertEqual(codex_before['interface']['defaultPrompt'], codex_after['interface']['defaultPrompt'])
        self.assertEqual(codex_before['apps'], codex_after['apps'])
        catalog_after = self.read_json('skills/bago5/references/CATALOGO_HABILIDADES.json')
        self.assertEqual(catalog_before['skills'][1:], catalog_after['skills'][1:])
        self.assertEqual(catalog_before['legacy_aliases'], catalog_after['legacy_aliases'])
        routes_after = self.read_json('skills/bago5/references/ROUTES.json')
        self.assertEqual(routes_after, {**routes_before, 'plugin_version': '0.4.41'})
        self.assertIn('Historial: 0.4.36', (self.root / 'skills/bago5/SKILL.md').read_text())
        self.assertIn('histórica 0.4.36', (self.root / 'skills/bago5/agents/openai.yaml').read_text())
        self.assertEqual(_module.synchronize(self.root)['changed_paths'], [])

    def test_sync_refuses_incomplete_sources_without_writes(self):
        (self.root / 'skills/bago5/SKILL.md').unlink()
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = _module.synchronize(self.root)
        self.assertEqual(result['status'], 'FAIL')
        self.assertEqual(result['changed_paths'], [])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_inspection_has_no_writes_and_reports_selected_root(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = _module.inspect(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(result['root'], str(self.root.resolve()))
        self.assertFalse(result['active_host_release_verified'])

    def test_cli_default_and_failure_exit_codes(self):
        done = subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), '--json'],
                              text=True, capture_output=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)['package_version'], VERSION)
        (self.root / 'skills/bago5/SKILL.md').unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = _module.main(['--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn(f'BAGO5 (v{VERSION})', output.getvalue())
        self.assertIn('FAIL:', output.getvalue())
        self.assertNotIn('NO_COMPROBADA', output.getvalue())
        (self.root / 'plugin.json').unlink()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = _module.main(['--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn('versión NO_COMPROBADA', output.getvalue())

    def test_cli_conflicting_primary_versions_cannot_choose_a_version(self):
        plugin = self.read_json('plugin.json')
        plugin['version'] = '0.4.41'
        self.write_json('plugin.json', plugin)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = _module.main(['--root', str(self.root)])
        self.assertEqual(code, 1)
        self.assertIn('versión NO_COMPROBADA', output.getvalue())
        self.assertIn('FAIL:', output.getvalue())


if __name__ == '__main__':
    unittest.main()
