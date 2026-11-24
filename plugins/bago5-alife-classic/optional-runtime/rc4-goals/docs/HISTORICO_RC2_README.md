# BAGO5os 1.4.7 — GOALS + Codex RC2 reparada (capa externa)

**Base inmutable:** `BAGO5os_1.4.7_CONTEXT_LIFECYCLE_NATIVE_RC2_INSTALLED.zip`.
La carpeta `bago-operating-suite/` contiene sus bytes originales sin añadir, retirar o modificar ningún archivo. El verificador de identidad original exige exactamente **600 archivos de payload**; por tanto, el puente está **fuera** de la carpeta de la skill.

**Entrada:** `GOALS_RESUME.cmd` desde la raíz del paquete (Windows; pregunta por la carpeta del proyecto y realiza solo lectura). Para probar la batería, `GOALS_VERIFICAR.cmd`. Estas pruebas no instalan ni sustituyen la skill de Codex.

## Interpretación de GOALS

Un GOAL es un documento en `<proyecto>/.bago/goals/*.goal.json`. El valor de `task_dir` vincula el documento a una misión ya inicializada en `<proyecto>.bago_tasks/<task_dir>/control.sqlite3` (estado separado del workspace, como exige TaskStore). El valor `goal_id` debe coincidir con el `mission_id` real del TaskStore y `check_id` con un check explícito del plan. Modelo de documento: `ejemplo.goal.json`.

`goal resume` se implementa como **resumen de TODOS los GOALS y TaskStores**, no como reanudación de una única misión. Examina **también TaskStores huérfanos**, sin documento. El orden de autoridad es:

**STOP persistido en TaskStore > estado OPEN/CLOSED en TaskStore > estado documental GOAL > presentación de pendientes.**

- Documento `DONE` pero TaskStore `OPEN` => **DESAJUSTE/BLOQUEADO**, nunca se pierde un pendiente.
- Documento `PAUSED` pero TaskStore `OPEN` => **PENDIENTE**, aunque no se permite ejecutar hasta revisión de estado.
- STOP en un TaskStore huérfano => bloquea la admisión de ejecuciones de cualquier GOAL conocido.
- Documento `.md` no migrado => **UNINDEXED_DOCUMENT/BLOQUEADO**, conserva el original, no inventa una asociación.
- `task-resume` requiere nombre de GOAL y motivo explícitos; no altera el documento, no borra el STOP de otros TaskStores.

## Comandos equivalentes

Desde la carpeta `GOALS_CODEX_RC2_REPARADA`, con Python 3.11+ y el RC2 original en la carpeta hermana:

```powershell
python -B .\goal_bridge.py --workspace "C:\Proyectos\MI_APP" resume
python -B .\goal_bridge.py --workspace "C:\Proyectos\MI_APP" doctor
python -B .\goal_bridge.py --workspace "C:\Proyectos\MI_APP" stop --reason "Parada solicitada"
python -B .\goal_bridge.py --workspace "C:\Proyectos\MI_APP" task-resume --goal G1 --reason "Continuación explícitamente autorizada"
# Efecto material, requiere además un TaskStore ACTIVE, ROUND abierta, check de ejecución y autorización del host:
python -B .\goal_bridge.py --workspace "C:\Proyectos\MI_APP" run --goal G1 --approve-run --codex codex
```

**Codex real:** el worker ejecuta `codex exec --skip-git-repo-check -` con el prompt por entrada estándar y `shell=False`, mediante `TaskStore.run_check`; guarda recibos en el ledger. Las pruebas ejecutan exclusivamente una CLI **simulada**, no Codex real ni una misión real. `run` **no** abre rondas, no autoriza herramientas del host, no cierra objetivos ni declara cumplimiento por un código cero aislado.

### Cinco incidencias tratadas

| ID | Prioridad | Cambio | Evidencia local |
|---|---|---|---|
| F01 | P0 | GOAL documental DONE/PAUSED no oculta TaskStore OPEN | Dos casos positivos/negativos |
| F02 | P0 | STOP huérfano consultado antes de admitir ejecución; STOP funciona incluso con GOAL ilegible | Dos casos y no ejecución |
| F03 | P1 | Lista `argv` separada y prompt por `stdin`, ruta con espacios y caracteres especiales | Mock de CLI ejecutado; prueba del constructor Windows |
| F04 | P1 | `.cmd` conserva `%ERRORLEVEL%` del proceso en vez de devolver éxito falso | Inspección de ambos launchers; ejecución en Windows condicionada |
| F05 | P1 | Conexiones SQLite cerradas de forma explícita; 4 escenarios repetidos sin retener manejadores | `quick_check`, renombrado bidireccional; Windows real pendiente |

## Límites y criterios de liberación

1. **No se pudo recuperar el código binario exacto de `BAGO5os_1.4.7_GOALS_CODEX_CLI_CONECTADO_RC1.zip` ni `GOALS_BRIDGE_RC1_TESTED.zip`**. Esta es una implementación reparada y **aislada** de la interfaz, no una afirmación de equivalencia con todas las funciones de RC1. La semántica real de documentos históricos no se reconstruye: los `.md` se señalan como pendientes de migración.
2. Ejecución local de pruebas: **Linux**; la CLI Codex real, rutas `.cmd`, creación de Job Objects en Windows y reproducción de los **4 fallos originales** de limpieza en Windows están **NOT_RUN**. La prueba de código Windows no equivale a prueba de extremo a extremo.
3. El STOP nativo del TaskStore puede pedir interrupción de procesos propios supervisados; no detiene agentes/host externos. Los TaskStores de otras ubicaciones que no pertenecen al `--state-root` indicado no quedan gobernados.
4. La identidad preservada de RC2 es una comprobación de bytes sin firma de editor. No es prueba de funcionamiento de todos sus módulos.
5. **NO_GO para reintentar orquestación completa** hasta repetir en Windows real las pruebas F03–F05, contrastar el puente con los paquetes RC1 originales y ejecutar una aceptación funcional con Codex CLI real.

### Notas de conservación

El paquete deja intactos el ZIP original y los archivos de skill, así como su `PACKAGE_IDENTITY.json`. Los tests operan sobre proyectos efímeros separados y cierran SQLite antes de borrar esas carpetas. No instala paquetes, no ejecuta un runtime del sistema ni modifica el Codex configurado en el equipo.
