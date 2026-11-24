# Sesión y contexto — integración aditiva BAGO5os

Se incorpora literalmente el acompañante BAGO-SCR-001 de 20 entradas, sin tocar
su contrato original. Esta skill y `suite_context.py` son adaptadores **nuevos**.
El módulo no modifica `suite_control`, `agent-relay`, Spiral, el kernel incluido,
ni el perfil de permisos de Codex.

**Contratos no equivalentes:** SessionStart = inventario; contexto revisado = datos;
TaskStore = misión/STOP/ledger; autorización = host/política efectiva.

Para activar el hook, usar `session-context config`, copiar la propuesta a la
configuración confiable del proyecto, revisar el diff y abrir `/hooks` en Codex.
No se instala al ejecutar `suite/install.py`. Un inicio de Codex sin origen de
confianza no prueba que el hook haya corrido.
