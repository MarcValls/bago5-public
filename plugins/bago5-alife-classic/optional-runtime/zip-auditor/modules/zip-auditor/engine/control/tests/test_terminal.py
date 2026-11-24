"""Pruebas focalizadas del control: entradas reales y menu sin terminal Windows."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

WORKSPACE = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parents[1] / 'terminal.py'
spec = importlib.util.spec_from_file_location('zipa_terminal', SOURCE)
terminal = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = terminal
spec.loader.exec_module(terminal)


@contextlib.contextmanager
def long_path_temporary_directory(prefix):
    root = Path(tempfile.mkdtemp(prefix=prefix)).resolve()
    assert root.is_relative_to(Path(tempfile.gettempdir()).resolve())
    try:
        yield str(root)
    finally:
        shutil.rmtree(terminal._io_path(root))


def make_app_fixture(parent):
    configured = os.environ.get('ZIPA_ENGINE_FIXTURE')
    if configured:
        original = Path(configured).expanduser().resolve()
        if not (original / 'VERIFICAR_PACK.py').is_file():
            original = original / terminal.PROGRAM_NAME
    else:
        candidates = [WORKSPACE / 'validation_030' / 'minimal_app' / terminal.PROGRAM_NAME,
                      SOURCE.parent.parent / terminal.PROGRAM_NAME,
                      WORKSPACE / terminal.PROGRAM_NAME]
        original = next((path for path in candidates if (path / 'VERIFICAR_PACK.py').is_file()), candidates[0])
    if not original.is_dir():
        raise RuntimeError('Falta la fixture del motor: ' + str(original) +
                           '. Define ZIPA_ENGINE_FIXTURE con la ruta al programa extraido.')
    root = Path(parent) / 'Programa con espacios & á'
    base = root / terminal.PROGRAM_NAME
    shutil.copytree(original, base)
    return root, base


def make_inputs(parent):
    folder = Path(parent) / "Elegida O'Brien ! %TEMP% (2) á漢"
    (folder / 'subcarpeta').mkdir(parents=True)
    for relative, version in [('nombre_cualquiera.zip', '1.0'),
                              ('subcarpeta/descarga_con_otro_nombre漢.zip', '1.1')]:
        with zipfile.ZipFile(folder / relative, 'w') as z:
            z.writestr('package.json', json.dumps({'name': 'cuaderno-aurora', 'version': version}))
            z.writestr('README.md', '# Cuaderno Aurora\nAplicacion para organizar notas de investigacion.\n')
            z.writestr('src/main.py', 'from records import record_note\nprint(record_note("aurora"))\n')
            z.writestr('src/records.py', 'def record_note(value):\n    return {"aurora_note": value}\n')
            z.writestr('src/version.txt', version)
    return folder


def input_hashes(folder):
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*.zip')}


def report_outputs(base):
    return sorted(terminal.reports_folder(base).glob('INFORME_*'))


class ConfirmConsole:
    def __init__(self, answer, hook=None):
        self.answer = answer
        self.hook = hook
        self.confirmations = []

    def confirm(self, title, subtitle='', default=False):
        self.confirmations.append((title, subtitle, default))
        if self.hook:
            self.hook()
        return self.answer


class ScriptedConsole:
    def __init__(self, choices, texts=()):
        self.choices = iter(choices)
        self.texts = iter(texts)
        self.screens = []

    def choose(self, title, options, **kwargs):
        self.screens.append((title, kwargs.get('subtitle', '')))
        choice = next(self.choices)
        if callable(choice):
            return choice(options)
        return choice

    def read_text(self, prompt):
        return next(self.texts)

    def pause(self, *args):
        pass


class SelectionTests(unittest.TestCase):
    def test_arrows_wrap_and_page_selection(self):
        self.assertEqual(terminal.selection_step(0, 'UP', 12), (11, None))
        self.assertEqual(terminal.selection_step(11, 'DOWN', 12), (0, None))
        self.assertEqual(terminal.selection_step(4, 'NEXT', 12), (9, None))
        self.assertEqual(terminal.selection_step(9, '3', 12), (11, 11))
        self.assertEqual(terminal.selection_step(9, '9', 12), (9, None))
        self.assertEqual(terminal.selection_step(10, 'PREV', 12), (0, None))

    def test_enter_cancel_home_and_end(self):
        self.assertEqual(terminal.selection_step(3, 'ENTER', 6), (3, 3))
        self.assertEqual(terminal.selection_step(3, 'ESC', 6), (3, -1))
        self.assertEqual(terminal.selection_step(3, '0', 6), (3, -1))
        self.assertEqual(terminal.selection_step(3, 'HOME', 6), (0, None))
        self.assertEqual(terminal.selection_step(3, 'END', 6), (5, None))

    def test_literal_paths_with_quotes_and_shell_characters(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Mis ZIP & O'Brien ! %TEMP% (2) á漢"
            folder.mkdir()
            self.assertEqual(terminal.folder_from_text('"' + str(folder) + '"', tmp), folder)
            self.assertEqual(terminal.folder_from_text(folder.name, tmp), folder)
            with self.assertRaises(ValueError):
                terminal.folder_from_text('', tmp)
            with self.assertRaises(ValueError):
                terminal.folder_from_text('no-existe', tmp)

    def test_browser_pasted_route_is_shown_then_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'Destino con espacios'
            folder.mkdir()
            console = ScriptedConsole([('paste', None), lambda options: options[0].value],
                                      ['"' + str(folder) + '"'])
            selected = terminal.pick_folder(console, tmp)
            self.assertEqual(selected, folder)
            self.assertIn(str(folder), console.screens[-1][1])

    def test_browser_descends_and_can_cancel(self):
        with tempfile.TemporaryDirectory() as tmp:
            child = Path(tmp) / 'Carpeta'
            child.mkdir()
            console = ScriptedConsole([('open', child), ('parent', Path(tmp)), None])
            self.assertIsNone(terminal.pick_folder(console, tmp))
            self.assertIn(str(child), console.screens[1][1])

    def test_report_has_no_bundled_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / terminal.PROGRAM_NAME
            bundled = base / 'RESULTADOS' / 'report.html'
            bundled.parent.mkdir(parents=True)
            bundled.write_text('example')
            self.assertEqual(terminal.find_report(base), (None, False))
            latest = terminal.reports_folder(base) / 'ULTIMO_INFORME.html'
            latest.parent.mkdir()
            latest.write_text('latest')
            self.assertEqual(terminal.find_report(base), (latest, False))

    def test_yes_no_and_cancel_are_distinct(self):
        console = terminal.Console(numbers=True)
        with contextlib.redirect_stdout(io.StringIO()):
            for entered, expected in [('s', True), ('sí', True), ('n', False), ('0', None)]:
                with mock.patch('builtins.input', return_value=entered):
                    self.assertIs(console.confirm('Continuar?'), expected)

    def test_reader_never_prefers_an_old_summary_over_a_new_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / terminal.PROGRAM_NAME
            reports = terminal.reports_folder(base)
            old = reports / 'INFORME_ANTERIOR'
            new = reports / 'INFORME_NUEVO'
            old.mkdir(parents=True)
            new.mkdir()
            summary = old / 'RESUMEN_FUSIONES.html'
            summary.write_text('resumen anterior')
            detail = new / 'report.html'
            detail.write_text('nuevo detalle')
            terminal.publish_latest_summary(base, summary)
            latest = reports / 'ULTIMO_INFORME.html'
            latest.write_text('<a href="INFORME_NUEVO/report.html">Abrir</a>')
            self.assertEqual(terminal.find_report(base), (latest, False))
            current_summary = new / 'RESUMEN_FUSIONES.html'
            current_summary.write_text('resumen nuevo')
            reader = terminal.publish_latest_summary(base, current_summary)
            self.assertEqual(terminal.find_report(base), (reader, False))

    def test_display_escapes_control_sequences_without_changing_plain_names(self):
        self.assertEqual(terminal.safe_display('Carpeta á漢'), 'Carpeta á漢')
        self.assertEqual(terminal.safe_display('a\x1b[31m\n\u202ez'), 'a\\x1b[31m\\x0a\\u202ez')


class RealEngineTests(unittest.TestCase):
    def test_numbered_menu_selects_folder_rejects_copy_and_returns_to_menu(self):
        with tempfile.TemporaryDirectory(prefix='zipa_menu_') as tmp:
            root, base = make_app_fixture(tmp)
            folder = Path(tmp) / 'Carpeta elegida desde menu á'
            folder.mkdir()
            with zipfile.ZipFile(folder / 'entrada.zip', 'w') as z:
                z.writestr('datos.txt', 'Prueba de la carpeta elegida.\n')
            inputs = ['1', '3', '"' + str(folder) + '"', '1', '2', '1', '2', '', '0']
            screen = io.StringIO()
            with mock.patch('builtins.input', side_effect=inputs), \
                    contextlib.redirect_stdout(screen):
                result = terminal.main(['--menu-numeros', '--no-open'], root=root)
            self.assertEqual(result, 0)
            self.assertGreaterEqual(screen.getvalue().count('Panel de control'), 2)
            self.assertIn(str(folder), screen.getvalue())
            self.assertNotIn('ejemplo', screen.getvalue().lower())
            outputs = report_outputs(base)
            self.assertEqual(len(outputs), 1)
            state = json.loads((outputs[0] / 'ARRANQUE.json').read_text())
            self.assertEqual(state['input'], str(folder.resolve()))
            self.assertEqual(state['verification_state'], 'PASS')
            self.assertEqual(state['viewer_state'], 'NOT_REQUESTED')
            self.assertNotIn('--recursive', state['engine_command'])
            interface = json.loads((outputs[0] / 'INTERFAZ.json').read_text())
            self.assertEqual(interface['grouping_state'], 'DECLINED')
            self.assertEqual(interface['copied_count'], 0)
            self.assertFalse(list(outputs[0].glob('PAQUETES_AGRUPADOS*')))

    def test_cli_default_proposes_without_copying_and_preserves_inputs(self):
        with tempfile.TemporaryDirectory(prefix='zipa_ui_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = make_inputs(tmp)
            before = input_hashes(inputs)
            with mock.patch('builtins.input', side_effect=AssertionError('La CLI no debe preguntar.')):
                result = terminal.main(['--analizar', str(inputs), '--recursive', '--no-open'], root=root)
            self.assertEqual(result, 0)
            outputs = report_outputs(base)
            self.assertEqual(len(outputs), 1)
            state = json.loads((outputs[0] / 'ARRANQUE.json').read_text())
            self.assertEqual(state['input'], str(inputs.resolve()))
            self.assertEqual(state['analysis_state'], 'ANALYZED')
            self.assertEqual(state['verification_state'], 'PASS')
            self.assertEqual(state['viewer_state'], 'NOT_REQUESTED')
            self.assertIn('--recursive', state['engine_command'])
            interface = json.loads((outputs[0] / 'INTERFAZ.json').read_text())
            self.assertEqual(interface['analysis_output'], str(outputs[0]))
            self.assertEqual(interface['summary_state'], 'GENERATED')
            self.assertEqual(interface['viewer_state'], 'NOT_REQUESTED')
            self.assertEqual(interface['grouping_state'], 'PROPOSED')
            self.assertEqual(interface['copied_count'], 0)
            self.assertIsNone(interface['copy_output'])
            self.assertTrue((outputs[0] / 'RESUMEN_FUSIONES.html').is_file())
            self.assertTrue((outputs[0] / 'RESUMEN_FUSIONES.json').is_file())
            self.assertTrue((outputs[0] / 'PROPUESTA_AGRUPACION.html').is_file())
            self.assertTrue((outputs[0] / 'PROPUESTA_AGRUPACION.json').is_file())
            plan = json.loads((outputs[0] / 'PROPUESTA_AGRUPACION.json').read_text())
            self.assertEqual(len(plan['groups']), 1)
            self.assertEqual(len(plan['groups'][0]['member_ids']), 2)
            self.assertIn('Aurora', plan['groups'][0]['label'])
            self.assertFalse(list(outputs[0].glob('PAQUETES_AGRUPADOS*')))
            reader = terminal.reports_folder(base) / 'ULTIMA_AGRUPACION.html'
            self.assertEqual(terminal.find_report(base), (reader, False))
            summary_reader_before = reader.read_bytes()
            no_zips = Path(tmp) / 'Vacia'
            no_zips.mkdir()
            self.assertEqual(terminal.analyze(base, no_zips, no_open=True), 2)
            self.assertEqual(reader.read_bytes(), summary_reader_before)
            self.assertEqual(len(list(terminal.reports_folder(base).glob('INFORME_*'))), 1)
            inventory = (outputs[0] / 'inventory.csv').read_text(encoding='utf-8-sig')
            self.assertIn('nombre_cualquiera.zip', inventory)
            self.assertIn('descarga_con_otro_nombre漢.zip', inventory)
            self.assertTrue((outputs[0] / 'report.html').is_file())
            after = input_hashes(inputs)
            self.assertEqual(before, after)
            self.assertEqual(terminal.verify_program(base, verbose=False), 0)
            self.assertFalse(list(base.rglob('__pycache__')))

    def test_explicit_cli_acceptance_copies_exact_zip_bytes(self):
        with long_path_temporary_directory(prefix='zipa_accept_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = make_inputs(tmp)
            before = input_hashes(inputs)
            with mock.patch('builtins.input', side_effect=AssertionError('La CLI no debe preguntar.')):
                result = terminal.main(['--analizar', str(inputs), '--recursive', '--no-open',
                                        '--aceptar-agrupacion'], root=root)
            self.assertEqual(result, 0)
            output = report_outputs(base)[0]
            state = json.loads((output / 'INTERFAZ.json').read_text())
            self.assertEqual(state['grouping_state'], 'APPLIED')
            self.assertEqual(state['copied_count'], 2)
            self.assertEqual(state['grouping_acceptance']['mode'], 'CLI_FLAG')
            copied = list(Path(state['copy_output']).rglob('*.zip'))
            self.assertEqual(len(copied), 2)
            self.assertEqual(len({p.parent for p in copied}), 1)
            self.assertEqual(sorted(terminal.file_sha256(p) for p in copied), sorted(before.values()))
            self.assertEqual(input_hashes(inputs), before)

    def test_deferred_acceptance_shows_exact_plan_and_does_not_duplicate_applied_copy(self):
        with long_path_temporary_directory(prefix='zipa_review_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = make_inputs(tmp)
            self.assertEqual(terminal.main(['--analizar', str(inputs), '--recursive', '--no-open'], root=root), 0)
            output = report_outputs(base)[0]
            plan = json.loads((output / 'PROPUESTA_AGRUPACION.json').read_text())
            declined = ConfirmConsole(False)
            self.assertEqual(terminal.review_latest_grouping(base, declined), 0)
            self.assertFalse(list(output.glob('PAQUETES_AGRUPADOS*')))
            accepted = ConfirmConsole(True)
            self.assertEqual(terminal.review_latest_grouping(base, accepted), 0)
            title, preview, default = accepted.confirmations[0]
            self.assertIn('copiar', title)
            self.assertIs(default, False)
            self.assertIn(plan['plan_sha256'], preview)
            for archive in plan['archives']:
                self.assertIn(terminal.safe_display(archive['relative_path']), preview)
                self.assertIn(str(archive['size_bytes']), preview)
            for group in plan['groups']:
                self.assertIn(terminal.safe_display(group['directory_name']), preview)
            state = json.loads((output / 'INTERFAZ.json').read_text())
            self.assertEqual(state['grouping_state'], 'APPLIED')
            never_asked = ConfirmConsole(True, hook=lambda: self.fail('No debe repetir una copia ya aplicada.'))
            self.assertEqual(terminal.review_latest_grouping(base, never_asked), 0)
            self.assertEqual(len(list(output.glob('PAQUETES_AGRUPADOS*'))), 1)

    def test_modified_proposal_is_rejected_before_acceptance(self):
        with tempfile.TemporaryDirectory(prefix='zipa_digest_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = make_inputs(tmp)
            self.assertEqual(terminal.main(['--analizar', str(inputs), '--recursive', '--no-open'], root=root), 0)
            output = report_outputs(base)[0]
            path = output / 'PROPUESTA_AGRUPACION.json'
            plan = json.loads(path.read_text())
            plan['groups'][0]['label'] += ' alterada'
            path.write_text(json.dumps(plan), encoding='utf-8')
            console = ConfirmConsole(True, hook=lambda: self.fail('No debe pedir aceptar un plan alterado.'))
            self.assertEqual(terminal.review_latest_grouping(base, console), 5)
            self.assertFalse(list(output.glob('PAQUETES_AGRUPADOS*')))

    def test_newer_report_blocks_application_of_the_previous_plan(self):
        with tempfile.TemporaryDirectory(prefix='zipa_newer_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = make_inputs(tmp)
            command = ['--analizar', str(inputs), '--recursive', '--no-open']
            self.assertEqual(terminal.main(command, root=root), 0)
            old = report_outputs(base)[0]
            def newer_analysis_during_confirmation():
                self.assertEqual(terminal.main(command, root=root), 0)
            console = ConfirmConsole(True, hook=newer_analysis_during_confirmation)
            self.assertEqual(terminal.review_latest_grouping(base, console), 5)
            self.assertFalse(list(old.glob('PAQUETES_AGRUPADOS*')))
            state = json.loads((old / 'INTERFAZ.json').read_text())
            self.assertEqual(state['grouping_state'], 'FAILED')

    def test_no_eligible_zip_does_not_ask_to_accept_an_empty_operation(self):
        with tempfile.TemporaryDirectory(prefix='zipa_empty_plan_') as tmp:
            root, base = make_app_fixture(tmp)
            inputs = Path(tmp) / 'Solo ZIP corrupto'
            inputs.mkdir()
            (inputs / 'corrupto.zip').write_bytes(b'not a ZIP archive')
            console = ConfirmConsole(True, hook=lambda: self.fail('No se acepta una operacion vacia.'))
            self.assertEqual(terminal.analyze(base, inputs, no_open=True, console=console), 1)
            output = report_outputs(base)[0]
            state = json.loads((output / 'INTERFAZ.json').read_text())
            self.assertEqual(state['grouping_state'], 'PROPOSED')
            self.assertFalse(state['grouping_apply_available'])
            self.assertEqual(state['copied_count'], 0)
            self.assertFalse(list(output.glob('PAQUETES_AGRUPADOS*')))
            self.assertEqual(terminal.review_latest_grouping(base, console), 0)
            self.assertFalse(console.confirmations)


class RemovedExamplesTests(unittest.TestCase):
    def test_demo_flag_and_acceptance_without_analysis_are_rejected(self):
        for arguments in (['--demo'], ['--aceptar-agrupacion']):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    terminal.main(arguments)
                self.assertEqual(raised.exception.code, 2)

    def test_menu_contains_no_examples_action(self):
        console = ScriptedConsole([lambda options: self.assertFalse(any('ejemplo' in p.label.lower() for p in options))])
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(terminal.menu(tmp, console, no_open=True), 0)


if __name__ == '__main__':
    unittest.main()
