# Context Lifecycle · capacidad nativa, opt-in

Propietario: **Operating Layer BAGO5os**, no segundo orquestador. La antigua
`session-context` 1.4.6 (solo inventario del cwd) permanece instalada sin editar.

## Entrada de lectura y recuperación

`context-lifecycle inspect --root <ruta-absoluta>` realiza descubrimiento
ascendente acotado (máximo ocho), se detiene ante un `.git` intermedio sin
marcador y presenta un resumen acotado **DATA_ONLY** de los tres artefactos.
No concede permisos, no valida la verdad del contenido ni reanuda STOP.
El resultado se incorpora al razonamiento de BAGO-CORE solo como **dato**.

`context-lifecycle hook-config` emite un borrador de `SessionStart` V2.
El hook V2 verifica la identidad exacta de la skill antes de leer el contexto,
no crea archivos ni ejecuta acciones; se activa solo tras revisión/confianza
expresa en Codex `/hooks`. **No instalar dos hooks SessionStart BAGO5os.**

## Gestión mediante la misma autoridad

`plan-bootstrap` y `plan-update` son lectura. `apply-bootstrap` usa
creación exclusiva, requiere digest de plan y aprobación literal; solo crea
los cuatro archivos que falten (estructura + 3 artefactos). `apply-update`
requiere aprobación literal, snapshot vigente, directorio TaskStore existente
vinculado a la raíz y suite instalada/verificada. Dentro de `BEGIN IMMEDIATE`
comprueba STOP y candidatura congelada, rechaza run/assignment activos,
Relay no ocioso y conflictos con el scope congelado. Conserva información
manual, campos desconocidos y verified_state; un objetivo nuevo es PROPOSED.

No hay ledger o permiso nuevo. Los flags CLI NO reemplazan autorizaciones de
host; quien ejecuta debe contar con permiso efectivo. Un fallo entre los dos
reemplazos de archivos puede provocar PARTIAL_UNCERTAIN: **no es transacción
multiarchivo**. Revisar diffs y evidencias antes de volver a intentar.

## Secuencia CLI

```powershell
python -B scripts/suite_orchestrator.py context-lifecycle doctor
python -B scripts/suite_orchestrator.py context-lifecycle inspect --root <ruta-absoluta>
python -B scripts/suite_orchestrator.py context-lifecycle plan-bootstrap --root <ruta-absoluta>
python -B scripts/suite_orchestrator.py context-lifecycle hook-config
python -B scripts/suite_orchestrator.py context-lifecycle hook-demo
```

Para `apply-update` añadir `--task-state-dir <ruta-control-existente>`,
`--expected <snapshot_sha256>` y `--approve APROBAR_ACTUALIZACION_CONTEXTO`,
además de `--objective` y `--next-action`. No ejecutar sin validación humana
real de plan y política del host.

Consulta [contrato](docs/CONTRATO_Y_CONTINUIDAD.md) y
[continuidad de integración](README.md). El origen congelado se distribuye por
separado con sus hashes, y este módulo declara sus modificaciones.


## RC2 — Carpeta de continuidad propia de la Suite (.bago_skill)

Desde esta candidata, la continuidad **gestionada por BAGO5os Context Lifecycle V2** se guarda exclusivamente bajo la raíz autorizada del proyecto en `.bago_skill/`. El marcador es `.bago_skill/CONTEXT_STRUCTURE.json`, con `context/PROJECT_CONTEXT.md`, `state/PROJECT_STATE.json` y `runtime/ACTIVE_HANDOFF.md`.

**No se cambia ni se lee automáticamente** `.bago/` de ADL, la configuración `.codex/`, los handoffs de `teamctl` ni el runtime legado de BAGO. El hook V1 se conserva intacto únicamente por compatibilidad; usar V2 para el nuevo directorio. No hay migración silenciosa desde `.bago/`.

`TaskStore` y Relay siguen usando la ruta de estado explícita y externa al workspace exigida por su contrato; `.bago_skill` NO concede permisos, no contiene el ledger y no elude STOP. Inicializar/actualizar requiere el mismo plan, digest, aprobación y permisos efectivos que antes.

**Privacidad y Git:** el usuario debe decidir si excluye `.bago_skill/` en `.gitignore`. La Suite no modifica `.gitignore` por sí sola. El almacenamiento del worktree es local, no garantiza transferencia automática entre worktrees.
