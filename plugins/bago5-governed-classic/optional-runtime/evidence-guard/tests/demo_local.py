"""Demonstration limited to bundled synthetic data and a temporary output directory."""
import contextlib
import hashlib
import io
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import bago_evidence_guard as guard


def perform(argv):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        exit_code = guard.main(argv)
    try:
        result = json.loads(stdout.getvalue() or stderr.getvalue())
    except Exception:
        raise RuntimeError(f"No valid receipt. Code={exit_code} stdout={stdout.getvalue()} stderr={stderr.getvalue()}")
    return exit_code, result


def main():
    examples = HERE / 'examples'
    data = examples / 'datos_sinteticos'
    css = data / 'frontend' / 'src' / 'ExternalConnections.css'
    log = data / 'logs' / 'node-test-wrong-project-root-control.txt'
    baseline = {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (css, log)}
    bindings = examples / 'vinculos.json'
    with tempfile.TemporaryDirectory(prefix='BAGO_W12_sintetico_') as temp:
        new = Path(temp) / 'W12_CORREGIDO.json'
        stage = Path(temp) / 'integrity_receipts'
        cmd = ['--root', str(data)]
        code, before = perform(['verify-json', *cmd, '--bindings', str(bindings),
                                '--report', str(examples / 'W12_R1_SINTETICO_INVALIDO.json'), '--expected-count', '2'])
        assert code == 2 and before['status'] == 'FAIL' and before['failed'] == 2
        assert [x['status'] for x in before['checks']] == ['INVALID_SHA256_FORMAT'] * 2
        code, control = perform(['check-text', '--file', str(examples / 'W12_R3_SINTETICO_CONTROL_INVALIDO.md')])
        assert code == 2 and 'FORBIDDEN_C0_DEL' in control['error']
        code, generated = perform(['seal-json', *cmd, '--template', str(examples / 'W12_TEMPLATE_SINTETICO.json'),
                                   '--bindings', str(bindings), '--out', str(new), '--expected-count', '2'])
        assert code == 0 and generated['verified'] == 2
        code, after = perform(['verify-json', *cmd, '--bindings', str(bindings),
                               '--report', str(new), '--expected-count', '2'])
        assert code == 0 and after['passed'] == 2
        code, manifests = perform(['create-manifest', *cmd, '--spec', str(examples / 'inventario.json'),
                                   '--out-dir', str(stage), '--label', 'DEMO_SINTETICA'])
        assert code == 0
        code, result = perform(['verify-manifest', *cmd, '--manifest', str(stage / 'manifest.json'),
                                '--markdown', str(stage / 'informe.md')])
        assert code == 0 and result['verified'] == 2
    final = {str(p.relative_to(data)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (css, log)}
    assert baseline == final, 'Source files changed during demo'
    print(json.dumps({
        'schema': 'bago.evidence.guard.demo.v1',
        'status': 'PASS',
        'r1_wrong_digest': {'expected': 'FAIL', 'observed': before['status'], 'bad_hashes': before['failed']},
        'r3_wrong_control': {'expected': 'FAIL', 'observed': control['status']},
        'new_json_report': {'expected': 'PASS', 'observed': after['status'], 'valid_hashes': after['passed']},
        'new_manifest': {'expected': 'PASS', 'observed': result['status'], 'valid_hashes': result['verified']},
        'sources_unchanged': baseline == final,
        'temporary_outputs_cleaned': True,
        'windows_live': 'NOT_RUN',
        'real_W12': 'NOT_RUN'
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
