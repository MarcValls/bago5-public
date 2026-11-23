"""Bounded ZIP Auditor specialist bridge. No import or execution of ZIP members."""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

SKILL = Path(__file__).resolve().parents[1]
MODULE = SKILL / 'modules' / 'zip-auditor' / 'engine'
TERMINAL = MODULE / 'control' / 'terminal.py'


def report_directory() -> Path:
    """Externally stored reports: never mutate installed, identity-controlled Suite."""
    override = os.getenv('BAGO_ZIPA_REPORTS_DIR')
    if override:
        path = Path(override).expanduser().resolve()
    elif os.name == 'nt':
        local = os.getenv('LOCALAPPDATA') or str(Path.home() / 'AppData' / 'Local')
        path = Path(local) / 'BAGO5os' / 'ZIP_AUDITOR_INFORMES'
    else:
        data = os.getenv('XDG_DATA_HOME') or str(Path.home() / '.local' / 'share')
        path = Path(data) / 'BAGO5os' / 'ZIP_AUDITOR_INFORMES'
    # Refuse accidental writes inside strict skill identity root.
    if path == SKILL or path.is_relative_to(SKILL):
        raise ValueError('La salida de ZIP Auditor debe estar fuera del paquete BAGO5os')
    return path


def run(argv: list[str] | None = None) -> int:
    if not TERMINAL.is_file():
        raise FileNotFoundError('Falta ZIP Auditor: ' + str(TERMINAL))
    output = report_directory()
    env = dict(os.environ)
    env.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
               BAGO_ZIPA_REPORTS_DIR=str(output))
    argv = argv or []
    proc = subprocess.run([sys.executable, '-I', '-B', '-X', 'utf8', str(TERMINAL), *argv],
                          cwd=MODULE, env=env)
    return proc.returncode


if __name__ == '__main__':
    try:
        raise SystemExit(run(sys.argv[1:]))
    except (OSError, ValueError) as exc:
        print('ZIP Auditor no disponible: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
