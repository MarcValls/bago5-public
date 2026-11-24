"""Fixed independent observer for a real ConfigManager copy.

A zero process exit means the observer finished, NOT that the product passed.
All configuration writes occur in temporary roots. No inference is requested.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(project: Path, suite: Path, request: dict) -> dict:
    root = Path(request['sandbox']).resolve()
    app = root / 'app'
    app.mkdir(parents=True, exist_ok=True)
    (app / 'pyproject.toml').write_text('[project]\nname="config-consumer-probe"\nversion="0.0.0"\n')
    state = root / request.get('state_name', 'state')
    from runtime_paths import skill_root
    backend = skill_root(suite) / 'runtime/BAGO-4.11.10/backend'
    os.environ.update({
        'BAGO_USER_ROOT': str(root / 'user'), 'BAGO_STATE_ROOT': str(root / 'environment-state'),
        'BAGO_RUNTIME_ROOT': str(root / 'runtime'), 'BAGO_WORKSPACE_ROOT': str(app),
        'BAGO_SCAN_ROOT': str(app), 'BAGO_PADRE_PATH': str(app),
        'BAGO_SESSION_MIRROR': '0', 'BAGO_ORCHESTRATE': '0', 'BAGO_AUTO_DELEGATE': '0',
        'OTEL_SDK_DISABLED': 'true', 'PYTHONDONTWRITEBYTECODE': '1',
    })
    # Probe guard, not an OS sandbox. No provider availability claim is made.
    import socket
    def deny_network(*args, **kwargs):
        raise RuntimeError('external_network_not_allowed_in_config_probe')
    socket.socket.connect = deny_network
    socket.create_connection = deny_network
    installed = request.get('installed', False)
    sys.path[:0] = ([str(project)] if not installed else []) + [str(backend), str(backend / '.bago/core'), str(backend / '.bago/tools')]
    source = (backend / '.bago/core/config_manager.py') if installed else (project / 'config_manager.py')
    import config_manager
    if Path(config_manager.__file__).resolve() != source.resolve():
        raise RuntimeError('wrong_config_module_imported')
    if request.get('session'):
        from session_manager import SessionManager
        class ProbeSession(SessionManager):
            @staticmethod
            def _mirror_session_root(session_id):
                return root / 'mirrors' / session_id
        # This loads config via the native consumer. There is no send()/inference.
        s = ProbeSession(session_id='config-consumer', base_path=str(app), state_root=str(state),
                         provider='ollama-cloud', model='deepseek-v3.1:671b', require_project_identity=True)
        c = s.config
        if request.get('rebind'):
            app2 = root / 'app2'
            app2.mkdir(exist_ok=True)
            (app2 / 'pyproject.toml').write_text('[project]\nname="config-consumer-rebind"\nversion="0.0.0"\n')
            s.rebind_project_root(app2)
            c = s.config
        consumer = 'SessionManager.rebind_project_root' if request.get('rebind') else 'SessionManager.__init__'
    else:
        c = config_manager.ConfigManager(base_path=str(app), state_root=str(state))
        consumer = 'ConfigManager'
    if type(c) is not config_manager.ConfigManager:
        raise RuntimeError('consumer_uses_other_config_class')
    if request.get('reset'):
        c.reset()
    for key, value in request.get('sets', {}).items():
        c.set(key, value)
    for key, value in request.get('properties', {}).items():
        setattr(c, key, value)
    return {'pid': os.getpid(), 'provider': c.default_provider, 'model': c.default_model,
            'data': c.all(), 'source': str(Path(config_manager.__file__).resolve()),
            'source_sha256': sha(source), 'consumer': consumer,
            'config_sha256': sha(c.config_path), 'inference_executed': False}


def evaluate(project: Path, suite: Path, installed: bool = False) -> dict:
    from runtime_paths import skill_root
    source = skill_root(suite) / 'runtime/BAGO-4.11.10/backend/.bago/core/config_manager.py' if installed else project / 'config_manager.py'
    tests = []
    def call(root: Path, **data):
        request = {'sandbox': str(root), 'installed': installed, **data}
        p = subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), '--worker',
                            '--project', str(project), '--suite', str(suite)],
                           input=json.dumps(request), capture_output=True, text=True, timeout=15)
        lines = [line[len('COG_CONFIG_RESULT='):] for line in p.stdout.splitlines() if line.startswith('COG_CONFIG_RESULT=')]
        if p.returncode or len(lines) != 1:
            raise RuntimeError(json.dumps({'exit': p.returncode, 'stdout': p.stdout[-2000:], 'stderr': p.stderr[-2000:]}))
        x = json.loads(lines[0])
        if x['source_sha256'] != sha(source):
            raise RuntimeError('candidate_changed_or_wrong_module')
        return x
    def expect(actual, expected, label):
        if actual != expected:
            raise AssertionError(json.dumps({'field': label, 'expected': expected, 'observed': actual}, ensure_ascii=False))
    def record(name, fn):
        try:
            with tempfile.TemporaryDirectory(prefix='cog-config-observer-') as tmp:
                detail = fn(Path(tmp))
            tests.append({'id': name, 'status': 'PASS', 'observed': detail})
        except Exception as exc:
            tests.append({'id': name, 'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)})
    def persisted(root, sets=None, properties=None):
        before = call(root, sets=sets or {}, properties=properties or {})
        after = call(root)
        expect(before['pid'] != after['pid'], True, 'new_process')
        for key, val in {**(sets or {}), **(properties or {})}.items():
            expect(after['data'][key], val, key)
        return {'before_pid': before['pid'], 'after_pid': after['pid'], 'provider': after['provider'], 'model': after['model']}
    def defaults(root):
        x = call(root)
        expect((x['provider'], x['model']), ('ollama-cloud', 'deepseek-v3.1:671b'), 'unchanged_new_defaults')
        return {'provider': x['provider'], 'model': x['model']}
    def partial(root):
        state = root / 'state'; state.mkdir()
        (state / 'config.json').write_text(json.dumps({'default_provider': 'ollama-local', 'custom': {'keep': 7}}))
        x = call(root)
        expect(x['provider'], 'ollama-local', 'partial_explicit_provider')
        expect(x['model'], 'deepseek-v3.1:671b', 'missing_model_default')
        expect(x['data']['custom'], {'keep': 7}, 'unknown_fields')
        return {'provider': x['provider'], 'model': x['model'], 'custom': x['data']['custom']}
    def unrelated(root):
        x = call(root, sets={'features.streaming': False, 'sources.read_roots': [{'path': 'LOCAL_TEST', 'key': 'test'}], 'custom.tag': 'keep'})
        y = call(root)
        expect(y['data'], x['data'], 'other_config_preserved')
        return {'options_preserved': True}
    def stable(root):
        x = call(root, sets={'default_provider': 'ollama-local', 'default_model': 'llama3.2:3b'})
        for _ in range(3):
            y = call(root)
            expect(y['config_sha256'], x['config_sha256'], 'reload_preserves_config_bytes')
        return {'config_sha256': x['config_sha256'], 'fresh_reloads': 3}
    def reset(root):
        call(root, sets={'default_provider': 'openrouter', 'default_model': 'custom-model', 'custom.tag': 'gone'})
        x = call(root, reset=True)
        y = call(root)
        expect((y['provider'], y['model']), ('ollama-cloud', 'deepseek-v3.1:671b'), 'reset_defaults')
        expect('custom' in y['data'], False, 'reset_removes_custom')
        return {'reset_survives_reload': True}
    def isolated(root):
        x = call(root, state_name='a', sets={'custom.owner': 'A'})
        y = call(root, state_name='b', sets={'custom.owner': 'B'})
        expect(call(root, state_name='a')['data']['custom']['owner'], 'A', 'root_a')
        expect(call(root, state_name='b')['data']['custom']['owner'], 'B', 'root_b')
        return {'separate_state_roots': True}
    def consumer(root, rebind=False):
        x = call(root, sets={'default_provider': 'ollama-local', 'default_model': 'llama3.2:3b', 'custom.keep': 1})
        y = call(root, session=True, rebind=rebind)
        expect((y['provider'], y['model']), ('ollama-local', 'llama3.2:3b'), 'native_consumer_config')
        expect(y['config_sha256'], x['config_sha256'], 'consumer_did_not_rewrite_config')
        return {'consumer': y['consumer'], 'module_sha256': y['source_sha256'], 'configuration_preserved': True, 'inference_executed': False}
    for name, fn in [
        ('C01_provider_set_survives_restart', lambda r: persisted(r, sets={'default_provider': 'ollama-local'})),
        ('C02_model_set_survives_restart', lambda r: persisted(r, sets={'default_model': 'llama3.2:3b'})),
        ('C03_property_setters_survive_restart', lambda r: persisted(r, properties={'default_provider': 'ollama-local', 'default_model': 'llama3.2:3b'})),
        ('C04_other_choices_preserved', lambda r: persisted(r, sets={'default_provider': 'openrouter', 'default_model': 'custom-model'})),
        ('C05_missing_config_defaults', defaults), ('C06_partial_config_preserves_choice', partial),
        ('C07_unrelated_options_preserved', unrelated), ('C08_repeated_reload_bytes_stable', stable),
        ('C09_explicit_reset', reset), ('C10_state_root_isolation', isolated),
        ('C11_native_session_consumer', consumer), ('C12_native_session_rebind', lambda r: consumer(r, True)),
    ]: record(name, fn)
    return {'schema': 'bago.cognitive.acceptance.v1', 'tests': tests, 'passed': sum(x['status'] == 'PASS' for x in tests),
            'total': len(tests), 'all_passed': all(x['status'] == 'PASS' for x in tests), 'evaluator_error': False,
            'project_files': {p.name: sha(p) for p in sorted(project.glob('*.py'))},
            'source_path': str(source), 'source_sha256': sha(source), 'installed_source': installed,
            'scope': 'canonical installed module' if installed else 'historical RC2 module copy; replay regression, not installed product defect'}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--project', required=True, type=Path)
    ap.add_argument('--suite', required=True, type=Path)
    ap.add_argument('--worker', action='store_true')
    ap.add_argument('--installed', action='store_true')
    a = ap.parse_args()
    if a.worker:
        result = worker(a.project.resolve(), a.suite.resolve(), json.load(sys.stdin))
        print('COG_CONFIG_RESULT=' + json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(evaluate(a.project.resolve(), a.suite.resolve(), a.installed), ensure_ascii=False, sort_keys=True))
