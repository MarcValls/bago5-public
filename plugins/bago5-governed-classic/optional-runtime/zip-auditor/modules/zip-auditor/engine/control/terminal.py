#!/usr/bin/env python3
"""Control de ZIP AUDITOR: menu de consola y CLI, sin dependencias externas."""
import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urlsplit
import unicodedata
import webbrowser

sys.dont_write_bytecode = True

VERSION = '0.3.0'
PROGRAM_NAME = 'ZIP_AUDITOR_v0.3.0'
PAGE_SIZE = 9
CANCEL = -1


@dataclass(frozen=True)
class Option:
    value: object
    label: str
    aliases: tuple = ()


def safe_display(value):
    """Escapa controles de datos sin cambiar las rutas utilizadas por el motor."""
    result = []
    for char in str(value):
        if unicodedata.category(char).startswith('C'):
            number = ord(char)
            result.append(('\\x%02x' if number < 256 else '\\u%04x' if number <= 65535 else '\\U%08x') % number)
        else:
            result.append(char)
    return ''.join(result)


def selection_step(index, event, count, page_size=PAGE_SIZE):
    """Estado de seleccion independiente del teclado/plataforma.

    Devuelve (indice, seleccion); None significa seguir, -1 cancelar.
    Los numeros 1..9 corresponden a las opciones visibles de la pagina.
    """
    if count <= 0:
        return 0, CANCEL if event in ('ESC', '0') else None
    index %= count
    if event == 'UP':
        return (index - 1) % count, None
    if event == 'DOWN':
        return (index + 1) % count, None
    if event == 'HOME':
        return 0, None
    if event == 'END':
        return count - 1, None
    if event == 'NEXT':
        return min((index // page_size + 1) * page_size, count - 1), None
    if event == 'PREV':
        return max(0, (index // page_size - 1) * page_size), None
    if event in ('ESC', '0'):
        return index, CANCEL
    if event == 'ENTER':
        return index, index
    if event in tuple(str(i) for i in range(1, page_size + 1)):
        chosen = index // page_size * page_size + int(event) - 1
        if chosen < count:
            return chosen, chosen
    return index, None


def enable_ansi():
    if not sys.stdout.isatty():
        return False
    if os.name != 'nt':
        return True
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel.GetStdHandle.restype = wintypes.HANDLE
        kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetConsoleMode.restype = wintypes.BOOL
        kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.SetConsoleMode.restype = wintypes.BOOL
        handle = kernel.GetStdHandle(-11)
        mode = wintypes.DWORD()
        return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and
                    kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (OSError, AttributeError):
        return False


def windows_key():
    import msvcrt
    char = msvcrt.getwch()
    if char in ('\x00', '\xe0'):
        return {'H': 'UP', 'P': 'DOWN', 'K': 'PREV', 'M': 'NEXT',
                'I': 'PREV', 'Q': 'NEXT', 'G': 'HOME', 'O': 'END'}.get(msvcrt.getwch(), '')
    if char == '\x03':
        raise KeyboardInterrupt
    return {'\r': 'ENTER', '\n': 'ENTER', '\x1b': 'ESC'}.get(char, char.lower())


class Console:
    def __init__(self, numbers=False):
        self.ansi = enable_ansi()
        self.keys = bool(os.name == 'nt' and sys.stdin.isatty() and
                         sys.stdout.isatty() and self.ansi and not numbers)

    def style(self, text, code):
        return '\x1b[' + code + 'm' + text + '\x1b[0m' if self.ansi else text

    def heading(self, title, subtitle=''):
        if self.ansi:
            print('\x1b[2J\x1b[H', end='')
        width = min(78, max(34, shutil.get_terminal_size((80, 25)).columns - 2))
        print(self.style('ZIP AUDITOR  /  ' + VERSION, '1;36'))
        print(self.style('─' * width, '2'))
        print(self.style(safe_display(title), '1'))
        if subtitle:
            print(subtitle)
        print()

    def choose(self, title, options, subtitle='', initial=0, cancel_label='Volver'):
        index = initial % len(options) if options else 0
        while True:
            self.heading(title, subtitle)
            start = index // PAGE_SIZE * PAGE_SIZE
            visible = options[start:start + PAGE_SIZE]
            for number, option in enumerate(visible, 1):
                selected = start + number - 1 == index
                prefix = '›' if selected else ' '
                line = f' {prefix}  {number}  {safe_display(option.label)}'
                print(self.style(line, '1;36') if selected else line)
            print()
            pages = max(1, (len(options) + PAGE_SIZE - 1) // PAGE_SIZE)
            if pages > 1:
                print(f' Pagina {index // PAGE_SIZE + 1}/{pages}  ·  N siguiente / P anterior')
            print(' 0  ' + cancel_label)
            if self.keys:
                print(self.style('\n Flechas ↑ ↓ y Enter · numeros 1–9 · Esc para volver', '2'), flush=True)
                event = windows_key()
            else:
                if options:
                    print(' Enter: ' + safe_display(options[index].label))
                try:
                    event = input('\n Elige una opcion: ').strip().casefold()
                except EOFError:
                    return None
                event = 'ENTER' if event == '' else event
            for option in options:
                if event in option.aliases:
                    return option.value
            if event == 'n':
                event = 'NEXT'
            elif event == 'p':
                event = 'PREV'
            index, selected = selection_step(index, event, len(options))
            if selected == CANCEL:
                return None
            if selected is not None:
                return options[selected].value

    def confirm(self, title, subtitle='', default=False):
        answer = self.choose(title, [Option(True, 'Si', ('s', 'si', 'sí')),
                                     Option(False, 'No', ('n', 'no'))],
                             subtitle=subtitle, initial=0 if default else 1,
                             cancel_label='Cancelar')
        return answer

    def read_text(self, prompt):
        try:
            return input(prompt)
        except EOFError:
            return None

    def pause(self, message='Pulsa Enter para volver al menu.'):
        print()
        self.read_text(message)


def folder_from_text(text, base):
    value = text.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    if not value:
        raise ValueError('La ruta esta vacia.')
    folder = Path(value).expanduser()
    if not folder.is_absolute():
        folder = Path(base) / folder
    folder = folder.resolve()
    if not folder.is_dir():
        raise ValueError('No existe esa carpeta o no se puede acceder a ella: ' + str(folder))
    return folder


def available_drives():
    if os.name == 'nt':
        import ctypes
        mask = ctypes.windll.kernel32.GetLogicalDrives()
        return [Path(chr(65 + n) + ':\\') for n in range(26) if mask & (1 << n)]
    return [Path('/')]


def pick_folder(console, initial):
    """Navegador de carpetas; no analiza nada hasta que se confirma despues."""
    current = Path(initial).resolve()
    if not current.is_dir():
        current = Path.home()
    while True:
        options = [Option(('use', current), 'Usar esta carpeta'),
                   Option(('parent', current.parent), 'Subir un nivel'),
                   Option(('paste', None), 'Escribir o pegar una ruta completa'),
                   Option(('drives', None), 'Elegir unidad / raiz')]
        try:
            folders = []
            for child in current.iterdir():
                try:
                    if child.is_dir():
                        folders.append(child)
                except OSError:
                    continue
            folders.sort(key=lambda p: (p.name.casefold(), p.name))
            options.extend(Option(('open', folder), '[Carpeta] ' + folder.name) for folder in folders)
            warning = ''
        except OSError as exc:
            warning = '\nNo se puede listar esta carpeta: ' + safe_display(exc)
        choice = console.choose('Elegir carpeta para analizar', options,
                                subtitle='Ruta actual:\n' + safe_display(current) + warning,
                                cancel_label='Cancelar seleccion')
        if choice is None:
            return None
        action, value = choice
        if action == 'use':
            return current
        if action in ('parent', 'open'):
            current = value
        elif action == 'paste':
            value = console.read_text('\nPega la ruta (Enter para volver): ')
            if value is not None and value.strip():
                try:
                    current = folder_from_text(value, current)
                except (OSError, ValueError) as exc:
                    print('\n' + safe_display(exc))
                    console.pause('Pulsa Enter para seguir eligiendo.')
        elif action == 'drives':
            drive = console.choose('Elegir unidad / raiz',
                                   [Option(p, str(p)) for p in available_drives()])
            if drive is not None:
                current = drive


def python_environment():
    environment = dict(os.environ)
    environment['PYTHONUTF8'] = '1'
    environment['PYTHONIOENCODING'] = 'utf-8'
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    return environment


def verify_program(base, verbose=True):
    command = [sys.executable, '-I', '-B', '-X', 'utf8', str(Path(base) / 'VERIFICAR_PACK.py')]
    result = subprocess.run(command, cwd=base, env=python_environment(),
                            capture_output=True, text=True, encoding='utf-8', errors='replace')
    try:
        details = json.loads(result.stdout)
    except (ValueError, TypeError):
        details = {}
    passed = result.returncode == 0 and isinstance(details, dict) and details.get('status') == 'PASS'
    if passed:
        if verbose:
            print('Integridad del programa: CORRECTA.')
    else:
        print('La integridad del programa no es correcta. No se inicia el analisis.')
        print(result.stdout or result.stderr or 'No se recibio un resultado del verificador.')
    return 0 if passed else 2


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError('No se pudo cargar el componente: ' + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def atomic_text(path, text):
    path = Path(path)
    descriptor, temporary_name = tempfile.mkstemp(prefix='.zipa_control_', dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def publish_reader(base, target, reader_name, title):
    destination = reports_folder(base) / reader_name
    relative = os.path.relpath(Path(target).resolve(), destination.parent.resolve())
    href = html.escape(quote(Path(relative).as_posix(), safe='/'), quote=True)
    label = html.escape(title)
    document = ('<!doctype html><html lang="es"><meta charset="utf-8">'
                '<meta http-equiv="refresh" content="0; url=' + href + '">'
                '<title>' + label + '</title><h1>' + label + '</h1>'
                '<p><a href="' + href + '">Abrir</a></p></html>')
    atomic_text(destination, document)
    return destination


def publish_latest_summary(base, summary_path):
    return publish_reader(base, summary_path, 'ULTIMO_RESUMEN.html', 'Ultimo resumen ZIP AUDITOR')


def publish_latest_grouping(base, proposal_path):
    return publish_reader(base, proposal_path, 'ULTIMA_AGRUPACION.html', 'Ultima propuesta de agrupacion')


def _io_path(value):
    """Use extended Windows paths only for IO, retaining lexical validation paths."""
    path = os.path.abspath(os.fspath(value))
    if os.name != "nt" or path.startswith("\\\\?\\"):
        return Path(path)
    if path.startswith("\\\\"):
        return Path("\\\\?\\UNC\\" + path[2:])
    return Path("\\\\?\\" + path)


def file_sha256(path):
    digest = hashlib.sha256()
    with _io_path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def grouping_component():
    return load_module(Path(__file__).with_name('content_grouping.py'), '_zipa_content_grouping')


def output_component():
    return load_module(Path(__file__).with_name('grouped_output.py'), '_zipa_grouped_output')


def validate_current_plan(base, output, plan, expected_digest=None):
    """Ata la aceptacion al plan sellado del informe verificado mas reciente."""
    output = Path(output).resolve()
    digest = plan.get('plan_sha256')
    component = grouping_component()
    if not isinstance(digest, str) or component.plan_digest(plan) != digest:
        raise ValueError('La propuesta ha cambiado o su digest no coincide. Genera un analisis nuevo.')
    if expected_digest is not None and digest != expected_digest:
        raise ValueError('La propuesta no coincide con la que genero esta interfaz.')
    report_path = output / 'report.json'
    if Path(plan['report_path']).resolve() != report_path:
        raise ValueError('La propuesta corresponde a otro informe.')
    if file_sha256(report_path) != plan['report_sha256']:
        raise ValueError('El informe cambio desde que se preparo la propuesta.')
    for kind, name in [('json', 'PROPUESTA_AGRUPACION.json'), ('html', 'PROPUESTA_AGRUPACION.html')]:
        if Path(plan['paths'][kind]).resolve() != output / name:
            raise ValueError('La propuesta apunta a archivos ajenos a este analisis.')
    persisted = json.loads((output / 'PROPUESTA_AGRUPACION.json').read_text(encoding='utf-8'))
    if persisted.get('plan_sha256') != digest or component.plan_digest(persisted) != digest:
        raise ValueError('La propuesta guardada cambio durante la revision. Vuelve a revisar el ultimo analisis.')
    latest = pointer_output(reports_folder(base) / 'ULTIMO_INFORME.html')
    if latest != output:
        raise ValueError('Hay un analisis mas reciente o no se puede identificar el ultimo informe. Revisa su propuesta.')
    verification = json.loads((output / 'verificacion.json').read_text(encoding='utf-8'))
    if verification.get('status') != 'PASS':
        raise ValueError('El informe no tiene una verificacion correcta.')
    manifest = json.loads((output / 'SHA256SUMS.json').read_text(encoding='utf-8'))
    if manifest.get('report.json') != plan['report_sha256']:
        raise ValueError('La identidad del informe no coincide con su manifiesto.')
    return digest


def grouping_review_text(plan, output):
    destination = output_component().output_directory_for(plan, output)
    archives = {item['id']: item for item in plan['archives']}
    eligible = [item for item in plan['archives'] if item.get('eligible')]
    total_bytes = sum(item['size_bytes'] for item in eligible)
    lines = ['Entrada: ' + safe_display(plan['source_root']),
             'Destino previsto: ' + safe_display(destination),
             'Si el nombre se ocupa, se anadira un sufijo sin sobrescribir.',
             f'ZIP a copiar: {len(eligible)} | Tamano total: {total_bytes:,} bytes',
             'Propuesta: ' + safe_display(plan['plan_sha256']), '']
    for number, group in enumerate(plan['groups'], 1):
        lines.append(f"{number}. {safe_display(group['label'])}  [{safe_display(group.get('confidence', ''))}]")
        lines.append('   Carpeta: ' + safe_display(group['directory_name']))
        for member in group['member_ids']:
            item = archives[member]
            lines.append('   - ' + safe_display(item['relative_path']) +
                         '  (' + str(item['size_bytes']) + ' bytes)')
        if group.get('status'):
            lines.append('   Estado: ' + safe_display(group['status']))
        lines.append('')
    excluded = [item for item in plan['archives'] if not item.get('eligible')]
    if excluded:
        lines.append('No elegibles para copiar:')
        lines.extend(' - ' + safe_display(item['relative_path']) for item in excluded)
        lines.append('')
    lines.append('Se copiaran los ZIP completos; los archivos de entrada permanecen en su lugar.')
    return '\n'.join(lines)


def apply_or_decline(base, output, plan, ui_state, accepted, mode):
    """La unica puerta de copia; la aceptacion nunca se infiere de un plan."""
    ui_state['grouping_acceptance'] = {'accepted': accepted is True, 'mode': mode,
                                      'plan_sha256': plan['plan_sha256'],
                                      'at_utc': datetime.now(timezone.utc).isoformat()}
    if accepted is not True:
        ui_state['grouping_state'] = 'DECLINED'
        ui_state['copied_count'] = 0
        ui_state['copy_output'] = None
        print('Agrupacion no aceptada. No se ha creado ninguna carpeta de copias.')
        return 0
    try:
        validate_current_plan(base, output, plan, ui_state.get('grouping_plan_sha256'))
        result = output_component().apply_grouping(plan, output, accepted=True)
        ui_state['grouping_result'] = result
        ui_state['copied_count'] = result.get('copied_count', 0)
        ui_state['copy_output'] = result.get('output_directory')
        if result.get('status') == 'COPIED':
            ui_state['grouping_state'] = 'APPLIED'
            print('Agrupacion aplicada: ' + str(ui_state['copied_count']) + ' ZIP copiados.')
            print('Destino: ' + safe_display(ui_state['copy_output']))
            return 0
        ui_state['grouping_state'] = 'FAILED'
        ui_state['grouping_error'] = result.get('errors') or ['La copia no se ha completado.']
        print('La agrupacion no se ha completado. Revisa INTERFAZ.json.')
        errors = ui_state['grouping_error']
        for error in errors if isinstance(errors, list) else [errors]:
            print(' - ' + safe_display(error))
        return 5
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        ui_state['grouping_state'] = 'FAILED'
        ui_state['grouping_error'] = type(exc).__name__ + ': ' + str(exc)
        print('No se aplico la agrupacion: ' + safe_display(exc))
        return 5


def write_ui_state(output, ui_state):
    atomic_text(Path(output) / 'INTERFAZ.json', json.dumps(ui_state, ensure_ascii=False, indent=2) + '\n')


def analyze(base, folder, recursive=False, no_open=False, console=None, accept_grouping=False):
    base = Path(base).resolve()
    folder = folder_from_text(str(folder), Path.cwd())
    if verify_program(base) != 0:
        return 2
    print('\nCarpeta de entrada: ' + safe_display(folder), flush=True)
    print('Subcarpetas: ' + ('SI' if recursive else 'NO'), flush=True)
    print('Los ZIP de entrada se conservan. Los resultados van a una carpeta aparte.\n', flush=True)
    original = load_module(base / 'ZIP_AUDITOR' / 'un_clic.py', '_zipa_original_one_click')
    result = original.run_once(base, folder, recursive=recursive, open_browser=False)
    exit_code = result['exit_code']
    if result.get('output'):
        print('Informes: ' + safe_display(result['output']))
    if result.get('error'):
        print(safe_display(result['error']))
    if result.get('verification_state') != 'PASS' or not result.get('output'):
        return exit_code

    output = Path(result['output'])
    ui_state = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'analysis_output': str(output), 'analysis_exit_code': exit_code,
                'summary_state': 'NOT_RUN', 'summary_paths': {},
                'grouping_state': 'NOT_RUN', 'grouping_paths': {},
                'copied_count': 0, 'copy_output': None,
                'viewer_state': 'NOT_REQUESTED'}
    target = output / 'report.html'
    try:
        fusion = load_module(Path(__file__).with_name('fusion_analysis.py'), '_zipa_fusion_analysis')
        summary = fusion.write_summary(output / 'report.json')
        ui_state['summary_state'] = 'GENERATED'
        ui_state['summary_paths'] = summary['paths']
        target = Path(summary['paths']['html'])
        if not target.is_file() or target.resolve().parent != output.resolve():
            raise ValueError('El resumen no se ha guardado junto al informe de este analisis.')
        ui_state['latest_summary'] = str(publish_latest_summary(base, target))
        print('\nRESUMEN DE POSIBLES UNIFICACIONES\n')
        for line in summary['console_lines']:
            print(safe_display(line))
        print('\nResumen HTML: ' + safe_display(target))
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        ui_state['summary_state'] = 'FAILED'
        ui_state['summary_error'] = type(exc).__name__ + ': ' + str(exc)
        target = output / 'report.html'
        print('El analisis esta guardado, pero no se pudo generar el resumen: ' + safe_display(exc))
        print('Informe detallado: ' + safe_display(target))
        exit_code = 4

    try:
        plan = grouping_component().write_proposal(output / 'report.json')
        digest = validate_current_plan(base, output, plan)
        proposal_path = Path(plan['paths']['html'])
        if not proposal_path.is_file():
            raise ValueError('No se ha generado el HTML de la propuesta de agrupacion.')
        ui_state['grouping_state'] = 'PROPOSED'
        ui_state['grouping_plan_sha256'] = digest
        ui_state['grouping_paths'] = plan['paths']
        ui_state['grouping_apply_available'] = any(item.get('eligible') for item in plan['archives'])
        ui_state['latest_grouping'] = str(publish_latest_grouping(base, proposal_path))
        target = proposal_path
        print('\nPROPUESTA DE AGRUPACION POR CONTENIDO\n')
        for line in plan['console_lines']:
            print(safe_display(line))
        print('\nPropuesta HTML: ' + safe_display(proposal_path))
        review = grouping_review_text(plan, output)
        if not ui_state['grouping_apply_available']:
            ui_state['grouping_no_copy_reason'] = 'NO_ELIGIBLE_ARCHIVES'
            print('No hay ZIP elegibles para copiar. No hay ninguna operacion de agrupacion que aceptar.')
        elif console is not None:
            # Mostrar el plan concreto en la misma pantalla que la aceptacion.
            write_ui_state(output, ui_state)
            accepted = console.confirm('Aceptar esta agrupacion y copiar los ZIP a la salida?',
                                       subtitle=review, default=False)
            if apply_or_decline(base, output, plan, ui_state, accepted, 'MENU'):
                exit_code = 5
        elif accept_grouping:
            print('\n' + review)
            if apply_or_decline(base, output, plan, ui_state, True, 'CLI_FLAG'):
                exit_code = 5
        else:
            print('\n' + review)
            print('\nPropuesta guardada. No se han creado carpetas de copias.')
            print('Puedes aceptarla desde el menu; en CLI usa --aceptar-agrupacion con --analizar.')
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        ui_state['grouping_state'] = 'FAILED'
        ui_state['grouping_error'] = type(exc).__name__ + ': ' + str(exc)
        print('El analisis esta guardado, pero la agrupacion no esta disponible: ' + safe_display(exc))
        exit_code = 5

    if not (no_open or os.environ.get('ZIPA_NO_OPEN') == '1'):
        try:
            open_path(target)
            ui_state['viewer_state'] = 'OPEN_REQUESTED'
            ui_state['viewer_target'] = str(target)
        except OSError as exc:
            ui_state['viewer_state'] = 'OPEN_FAILED'
            ui_state['viewer_error'] = str(exc)
            print('El informe esta guardado. No se pudo abrir el navegador: ' + safe_display(exc))
            if exit_code not in (4, 5):
                exit_code = 3
    ui_state['exit_code'] = exit_code
    write_ui_state(output, ui_state)
    return exit_code


def reports_folder(base):
    external = os.environ.get("BAGO_ZIPA_REPORTS_DIR")
    if external:
        return Path(external).expanduser().resolve()
    base = Path(base)
    return base.parent / (base.name + '_INFORMES')


class _PointerLink(HTMLParser):
    def __init__(self):
        super().__init__()
        self.href = None

    def handle_starttag(self, tag, attrs):
        if tag == 'a' and self.href is None:
            self.href = dict(attrs).get('href')


def pointer_output(pointer):
    """Resuelve solo punteros relativos locales para emparejar detalle/resumen."""
    try:
        parser = _PointerLink()
        parser.feed(Path(pointer).read_text(encoding='utf-8'))
        if not parser.href:
            return None
        address = urlsplit(parser.href)
        if address.scheme or address.netloc:
            return None
        parent = Path(pointer).parent.resolve()
        target = (parent / unquote(address.path)).resolve()
        if not target.is_relative_to(parent) or not target.is_file():
            return None
        return target.parent
    except (OSError, ValueError):
        return None


def review_latest_grouping(base, console):
    if verify_program(base) != 0:
        return 2
    output = pointer_output(reports_folder(base) / 'ULTIMO_INFORME.html')
    if output is None:
        print('No se puede identificar un ultimo informe. Analiza primero una carpeta de ZIP.')
        return 2
    try:
        state_path = output / 'INTERFAZ.json'
        ui_state = json.loads(state_path.read_text(encoding='utf-8'))
        if Path(ui_state['analysis_output']).resolve() != output:
            raise ValueError('El estado guardado pertenece a otro informe.')
        expected = ui_state.get('grouping_plan_sha256')
        if not expected:
            raise ValueError('El ultimo analisis no tiene una propuesta de agrupacion disponible.')
        plan = json.loads((output / 'PROPUESTA_AGRUPACION.json').read_text(encoding='utf-8'))
        validate_current_plan(base, output, plan, expected)
        if not any(item.get('eligible') for item in plan['archives']):
            print('Esta propuesta no contiene ZIP elegibles para copiar. No hay ninguna operacion que aceptar.')
            return 0
        if ui_state.get('grouping_state') == 'APPLIED':
            print('Esta agrupacion ya se aplico; no se repetiran las copias.')
            print('Destino: ' + safe_display(ui_state.get('copy_output', '')))
            return 0
        review = grouping_review_text(plan, output)
        accepted = console.confirm('Aceptar esta agrupacion y copiar los ZIP a la salida?',
                                   subtitle=review, default=False)
        code = apply_or_decline(base, output, plan, ui_state, accepted, 'MENU_REVIEW')
        ui_state['grouping_reviewed_at_utc'] = datetime.now(timezone.utc).isoformat()
        ui_state['exit_code'] = code
        write_ui_state(output, ui_state)
        return code
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print('La propuesta no se puede aplicar: ' + safe_display(exc))
        return 5


def find_report(base):
    grouping = reports_folder(base) / 'ULTIMA_AGRUPACION.html'
    summary = reports_folder(base) / 'ULTIMO_RESUMEN.html'
    latest = reports_folder(base) / 'ULTIMO_INFORME.html'
    latest_output = pointer_output(latest)
    if grouping.is_file() and latest_output is not None and pointer_output(grouping) == latest_output:
        return grouping, False
    if summary.is_file():
        summary_output = pointer_output(summary)
        if summary_output is not None and summary_output == latest_output:
            return summary, False
    if latest.is_file():
        return latest, False
    return None, False


def open_path(path):
    path = Path(path).resolve()
    if os.name == 'nt':
        os.startfile(str(path))
    elif not webbrowser.open(path.as_uri(), new=2):
        raise OSError('El sistema no ha aceptado la solicitud de apertura.')
    print('Se ha solicitado abrir: ' + safe_display(path))


def show_help(console, root, base):
    console.heading('Como usar ZIP AUDITOR')
    print('1. Elige la carpeta que contiene tus archivos ZIP.')
    print('2. Decide si quieres incluir las subcarpetas.')
    print('3. Revisa la ruta y confirma el analisis.')
    print('4. Revisa los grupos propuestos por el contenido de los ZIP.')
    print('5. Si aceptas, se copiaran los ZIP a carpetas de salida por grupo.')
    print('\nControl: flechas y Enter, o numeros. Esc / 0 vuelve atras.')
    print('En Si/No tambien puedes escribir S o N. Ctrl+C cierra el programa.')
    print('\nEl lector de resultados se abre en tu navegador habitual.')
    print('Cada analisis conserva HTML, JSON, CSV y registros de ejecucion.')
    print('El resumen propone posibles unificaciones y enlaza al informe detallado.')
    print('La agrupacion distingue copias/versiones candidatas sin fusionar su codigo.')
    print('La copia necesita tu aceptacion. Los ZIP originales permanecen en su lugar.')
    print('\nResultados:\n' + safe_display(reports_folder(base)))
    print('Los ZIP analizados no se extraen, ejecutan ni modifican.')
    print('\nCLI: --analizar RUTA genera la propuesta y no copia por defecto.')
    print('Anade --aceptar-agrupacion para autorizar expresamente sus copias en CLI.')
    print('En el menu puedes aceptar despues con Revisar y aplicar ultima agrupacion.')
    print('\nPython va incluido en la version EXE. No necesitas instalarlo.')
    print('El EXE comprueba su contenido antes de iniciar esta interfaz.')
    print('\nEstado de pruebas de esta entrega: consulta LEEME_EXE.txt en\n' + safe_display(root))


def menu(root, console, no_open=False):
    base = Path(root) / PROGRAM_NAME
    current = Path(root).parent
    last_message = 'Elige una accion. Puedes analizar cualquier carpeta con ZIP.'
    options = [Option('choose', 'Elegir carpeta y analizar mis ZIP'),
               Option('grouping', 'Revisar y aplicar ultima agrupacion'),
               Option('report', 'Abrir la ultima propuesta e informe'),
               Option('results', 'Abrir la carpeta de resultados'),
               Option('verify', 'Comprobar la integridad del programa'),
               Option('help', 'Ayuda y ubicacion de los resultados')]
    while True:
        action = console.choose('Panel de control', options, subtitle=last_message, cancel_label='Salir')
        if action is None:
            return 0
        try:
            if action == 'choose':
                folder = pick_folder(console, current)
                if folder is None:
                    continue
                current = folder
                recursive = console.confirm('Incluir subcarpetas?',
                                            subtitle='Carpeta seleccionada:\n' + safe_display(folder))
                if recursive is None:
                    last_message = 'Seleccion cancelada. No se ha iniciado el motor.'
                    continue
                summary = ('Carpeta seleccionada:\n' + safe_display(folder) +
                           '\n\nIncluir subcarpetas: ' + ('SI' if recursive else 'NO') +
                           '\nSalida:\n' + safe_display(reports_folder(base)))
                if not console.confirm('Empezar el analisis?', subtitle=summary):
                    last_message = 'Analisis cancelado. No se ha iniciado el motor.'
                    continue
                console.heading('Analizando', subtitle=safe_display(folder))
                code = analyze(base, folder, recursive=recursive, no_open=no_open, console=console)
                last_message = ('Analisis terminado. Revisa la propuesta y el estado de las copias.' if code == 0 else
                                'Analisis parcial; revisa las incidencias del informe.' if code == 1 else
                                'Analisis guardado; no se pudo generar el resumen.' if code == 4 else
                                'Analisis guardado; la agrupacion no se ha completado.' if code == 5 else
                                'La operacion termino con una incidencia. Revisa el mensaje y los registros.')
                print('\n' + last_message)
            elif action == 'grouping':
                code = review_latest_grouping(base, console)
                last_message = ('Revision de agrupacion terminada.' if code == 0 else
                                'La agrupacion no se ha aplicado. Revisa la incidencia.')
            elif action == 'report':
                path, _ = find_report(base)
                if path is None:
                    print('No hay informes disponibles. Inicia un analisis primero.')
                else:
                    open_path(path)
            elif action == 'results':
                path = reports_folder(base)
                if not path.is_dir():
                    print('Aun no existe una carpeta de resultados. Se crea con el primer analisis.')
                else:
                    open_path(path)
            elif action == 'verify':
                console.heading('Comprobacion de integridad')
                verify_program(base)
            elif action == 'help':
                show_help(console, root, base)
        except (OSError, ValueError, subprocess.SubprocessError) as exc:
            last_message = 'No se ha completado la operacion: ' + safe_display(exc)
            print('\n' + last_message)
        console.pause()


def main(argv=None, root=None, console=None):
    parser = argparse.ArgumentParser(description='ZIP AUDITOR: menu con flechas/numeros y analisis de carpetas.')
    parser.add_argument('carpeta', nargs='?', help='Carpeta de ZIP, alternativa a --analizar.')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--analizar', metavar='CARPETA', help='Analiza la carpeta indicada sin menu.')
    action.add_argument('--verificar', action='store_true', help='Comprueba los archivos del programa y termina.')
    parser.add_argument('--aceptar-agrupacion', action='store_true',
                        help='Autoriza copiar los ZIP segun la propuesta del analisis indicado; requiere --analizar o CARPETA.')
    parser.add_argument('--recursive', action='store_true', help='Incluye subcarpetas en el analisis.')
    parser.add_argument('--no-open', action='store_true', help='Guarda los resultados sin abrir el navegador.')
    parser.add_argument('--menu-numeros', action='store_true', help='Usa numeros en lugar de lectura de flechas.')
    args = parser.parse_args(argv)
    if args.carpeta and (args.analizar or args.verificar):
        parser.error('Usa una sola accion o carpeta de entrada.')
    if args.aceptar_agrupacion and not (args.analizar or args.carpeta):
        parser.error('--aceptar-agrupacion requiere --analizar CARPETA o una CARPETA de entrada.')
    root = Path(root).resolve() if root else Path(__file__).resolve().parent.parent
    base = root / PROGRAM_NAME
    try:
        if args.verificar:
            return verify_program(base)
        if args.analizar or args.carpeta:
            folder = args.analizar or args.carpeta
            return analyze(base, folder, recursive=args.recursive, no_open=args.no_open,
                           accept_grouping=args.aceptar_agrupacion)
        return menu(root, console or Console(numbers=args.menu_numeros), no_open=args.no_open)
    except KeyboardInterrupt:
        print('\nOperacion interrumpida. Los resultados ya guardados se conservan.')
        return 130
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print('No se pudo completar la operacion: ' + safe_display(exc))
        return 2


if __name__ == '__main__':
    sys.exit(main())
