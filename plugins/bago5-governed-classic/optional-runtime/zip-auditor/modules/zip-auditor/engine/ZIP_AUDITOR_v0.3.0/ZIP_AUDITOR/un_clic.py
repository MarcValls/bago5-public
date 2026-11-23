#!/usr/bin/env python3
"""Ejecuta el motor existente, verifica el resultado y solicita abrir su HTML."""
import argparse
from datetime import datetime
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import quote
import webbrowser

LAUNCHER_VERSION = '0.2.2'


def reports_root(base):
    external = os.environ.get("BAGO_ZIPA_REPORTS_DIR")
    if external:
        return Path(external).expanduser().resolve()
    base = Path(base).resolve()
    return base.parent / (base.name + '_INFORMES')


def _relative(path, base):
    try:
        return os.path.relpath(path, base)
    except ValueError:  # Carpeta elegida por el usuario en otra unidad de Windows.
        return str(path)


def _atomic_text(path, text):
    path = Path(path)
    handle, name = tempfile.mkstemp(prefix='.escritura_', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _open_report(path):
    if sys.platform == 'win32':
        os.startfile(str(path))
        return True  # Solicitud al sistema; no observación de la ventana.
    return bool(webbrowser.open(path.as_uri(), new=2))


def _publish_latest(base, report):
    destination = reports_root(base) / 'ULTIMO_INFORME.html'
    # El lector sigue funcionando si programa e informes se mueven juntos.
    relative = os.path.relpath(report.resolve(), destination.parent.resolve())
    uri = html.escape(quote(Path(relative).as_posix(), safe='/'), quote=True)
    document = ('<!doctype html><html lang="es"><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="0; url=' + uri + '">'
                '<title>Último informe ZIP AUDITOR</title><h1>Último informe</h1>'
                '<p><a href="' + uri + '">Abrir informe</a></p></html>')
    _atomic_text(destination, document)
    return destination


def run_once(base, folder=None, recursive=False, opener=None, runner=None,
             open_browser=True):
    """opener/runner se sustituyen solo en pruebas; el flujo normal usa procesos reales."""
    base = Path(base).resolve()
    input_folder = Path(folder) if folder is not None else base / 'ORIGINALES'
    if not input_folder.is_absolute():
        input_folder = base / input_folder
    input_folder = input_folder.resolve()
    result = {'launcher_version': LAUNCHER_VERSION, 'analysis_state': 'NOT_RUN',
              'verification_state': 'NOT_RUN', 'viewer_state': 'NOT_RUN',
              'input': str(input_folder), 'output': None, 'exit_code': 2}
    if not input_folder.is_dir():
        result['error'] = 'No existe la carpeta de ZIP: ' + str(input_folder)
        return result
    candidates = input_folder.rglob('*') if recursive else input_folder.iterdir()
    if not any(p.is_file() and p.suffix.lower() == '.zip' for p in candidates):
        result['error'] = 'No hay archivos ZIP en la carpeta elegida.'
        return result
    for filename in ('zip_auditor.py', 'verify_results.py'):
        if not (base / 'ZIP_AUDITOR' / filename).is_file():
            result['error'] = 'Falta el motor/verificador en ZIP_AUDITOR: ' + filename
            return result
    output_root = reports_root(base)
    output_root.mkdir(parents=True, exist_ok=True)
    prefix = 'INFORME_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '_'
    output = Path(tempfile.mkdtemp(prefix=prefix, dir=output_root))
    result['output'] = str(output)
    execute = runner if runner is not None else subprocess.run
    open_html = opener if opener is not None else _open_report
    environment = dict(os.environ)
    environment['PYTHONIOENCODING'] = 'utf-8'
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    options = dict(cwd=base, capture_output=True, text=True, encoding='utf-8',
                   errors='replace', env=environment)
    report = output / 'report.html'
    command = [sys.executable, 'ZIP_AUDITOR/zip_auditor.py', '--folder',
               _relative(input_folder, base), '--output', _relative(output, base)]
    if recursive:
        command.append('--recursive')
    result['engine_command'] = command
    try:
        print('Analizando ZIP. Los originales se conservan.')
        process = execute(command, **options)
        _atomic_text(output / 'ejecucion.log', (process.stdout or '') + (process.stderr or ''))
        result['engine_exit_code'] = process.returncode
        if process.returncode not in (0, 1):
            result['analysis_state'] = 'FAILED'
            result['error'] = 'El motor no ha terminado. Consulte ejecucion.log; no se abre un informe anterior como nuevo.'
        elif not report.is_file() or not (output / 'report.json').is_file():
            result['analysis_state'] = 'FAILED'
            result['error'] = 'El motor no ha generado los informes esperados.'
        else:
            result['analysis_state'] = 'PARTIAL' if process.returncode == 1 else 'ANALYZED'
            verification_command = [sys.executable, 'ZIP_AUDITOR/verify_results.py',
                                    _relative(output / 'report.json', base),
                                    '--sources', _relative(input_folder, base)]
            result['verification_command'] = verification_command
            checked = execute(verification_command, **options)
            _atomic_text(output / 'verificacion.json', (checked.stdout or '') + (checked.stderr or ''))
            try:
                verification = json.loads(checked.stdout or '{}')
            except ValueError:
                verification = {}
            if not isinstance(verification, dict):
                verification = {}
            if checked.returncode != 0 or verification.get('status') != 'PASS':
                result['verification_state'] = 'FAIL'
                result['error'] = 'El informe no supera la comprobacion de contrato e identidad. Consulte verificacion.json.'
            else:
                result['verification_state'] = 'PASS'
                result['verification_scope'] = 'Contrato e identidad, no funcionamiento de las fuentes.'
                result['latest_reader'] = str(_publish_latest(base, report))
                if not open_browser:
                    result['viewer_state'] = 'NOT_REQUESTED'
                    result['exit_code'] = process.returncode
                else:
                    try:
                        opened = open_html(report)
                        if opened is False:
                            raise OSError('El sistema no ha aceptado la solicitud de apertura.')
                        result['viewer_state'] = 'OPEN_REQUESTED'
                        result['exit_code'] = process.returncode
                    except OSError as exc:
                        result['viewer_state'] = 'OPEN_FAILED'
                        result['error'] = 'Informe generado; no se pudo abrir el navegador: ' + str(exc)
                        result['exit_code'] = 3
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        result['error'] = type(exc).__name__ + ': ' + str(exc)
    _atomic_text(output / 'ARRANQUE.json', json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', nargs='?', type=Path, help='Opcional: carpeta de ZIP; por defecto ORIGINALES del pack.')
    parser.add_argument('--recursive', action='store_true')
    parser.add_argument('--no-open', action='store_true',
                        help='Genera y verifica el informe sin abrir el navegador.')
    args = parser.parse_args(argv)
    try:
        open_browser = not (args.no_open or os.environ.get('ZIPA_NO_OPEN') == '1')
        result = run_once(Path(__file__).resolve().parent.parent, args.folder,
                          args.recursive, open_browser=open_browser)
    except (OSError, ValueError) as exc:
        print('No se pudo iniciar: ' + str(exc))
        return 2
    if result.get('output'):
        print('Informes: ' + result['output'])
    if result.get('error'):
        print(result['error'])
    elif result['analysis_state'] == 'PARTIAL':
        print('Analisis PARCIAL: informe verificado y conservado con sus incidencias.')
    elif result['viewer_state'] == 'NOT_REQUESTED':
        print('Analisis terminado. Informe verificado y guardado.')
    else:
        print('Analisis terminado. Se ha solicitado abrir el informe en el navegador.')
    return result['exit_code']


if __name__ == '__main__':
    sys.exit(main())
