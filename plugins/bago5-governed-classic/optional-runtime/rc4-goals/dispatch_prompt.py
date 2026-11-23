"""Interactive local opt-in; no command string is constructed from user data."""
from pathlib import Path
import goal_bridge

def main():
    print('Codex externo: un turno read-only. No es /goal nativo ni un cierre de mision.')
    workspace=input('Workspace de prueba autorizado (ruta completa): ').strip()
    if not workspace:return 3
    if input('Escribe EJECUTAR_CODEX_LECTURA para despachar: ').strip()!='EJECUTAR_CODEX_LECTURA':return 3
    return goal_bridge.main(['--workspace',workspace,'dispatch','--approve-run','--max-goals','1'])

if __name__=='__main__':raise SystemExit(main())
