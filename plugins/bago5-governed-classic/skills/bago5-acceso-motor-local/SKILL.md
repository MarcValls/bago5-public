---
name: bago5-acceso-motor-local
description: Resolver el motor local autorizado y comprobar su disponibilidad.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Runtime opcional BAGO

El motor BAGO Operating Suite 1.4.8 es opcional. Si el usuario dispone de una copia íntegra y autoriza su uso, comprueba la identidad de esa copia antes de invocarla.

El punto de entrada de la Suite externa es `<suite>/scripts/suite_orchestrator.py`. Antes de usarlo verificar Python, acceso a esa ruta y permisos del host. Ejecutar `python -B <entrypoint> identity` y luego `python -B <entrypoint> --help` para identificar la candidata y los comandos. Una identidad fallida impide presentar el payload como integro.

En GPT Classic, una ruta local escrita en el chat no permite ejecutar Python. Hace falta una herramienta de ejecucion realmente disponible o una conexion autorizada que exponga el runtime. Sin ella, identificar la operacion y preparar el comando o el flujo conversacional equivalente; marcar ejecucion NOT_RUN. El MCP de carpeta de solo lectura no sirve para ejecutar.

Vincular cada operacion a proyecto, candidata, alcance, autorizacion y STOP. Las operaciones de TaskStore, Relay, hooks y perfiles mantienen sus contratos y dependencias; no iniciar servicios ni instalar hooks por cargar esta skill. Los scripts incluidos no prueban funcionamiento instalado, agentes independientes, persistencia en ChatGPT ni ejecucion en segundo plano.

Registrar comando, salida, codigo de retorno y alcance de la evidencia. Las pruebas locales de identidad o ayuda no validan la conexion GPT Classic.


Antes de inicializar estado, aplicar [seleccion exclusiva del controlador](../bago5/references/controller-selection.md).

## Decisión de turno conectada al runtime existente

Aplicar el contrato compartido de [decisión de turno](../bago5/references/turn-decision.md). Su implementación única es `skills/bago5/scripts/turn_decision.py`. El adaptador `skills/bago5/scripts/runtime_turn_decision.py` está fuera del payload Suite congelado y usa la misma función `assess`; no instala un segundo controlador ni modifica misiones existentes.

Con Python 3.11+ y SQLite con `deserialize`, usar el adaptador solo sobre el TaskStore existente seleccionado explícitamente. Primero ejecutar `python -B <plugin-root>/skills/bago5/scripts/runtime_turn_decision.py --suite-root <suite> --state-dir <estado-existente> --workspace-root <raíz-autorizada-de-la-candidata> --observe`. Leer `controller.database_sha256` y preparar el recibo de criterios/acciones con sus fuentes reales. Después ejecutar el mismo adaptador y las mismas rutas explícitas de Suite, estado y candidata con `--receipt <recibo.json> --expected-state-sha256 <digest-observado>` en lugar de `--observe`.

La lectura verifica los bytes fijados de la Suite y coteja misión, candidata y archivos del scope. Copia el SQLite a memoria para consultarlo sin abrir el original en modo escritura. Si hay WAL/journal/SHM, cambios concurrentes, ruta ausente o identidad distinta, devuelve bloqueo; no crea un ledger ni modifica/checkpointea una base para poder leerla. Un estado STOP observado no se levanta. Un STOP ya conocido por el agente impide iniciar incluso la observación.

Sin `--state-dir`, solo comprueba integridad de la Suite y el recibo: no acredita conexión con una misión. `task status`, checks consumidos y CLOSED registrados no se importan como nueva evidencia de aceptación. El adaptador no consume recibos, no cierra TaskStore, no verifica permisos del host y no declara admisible una operación nativa concreta. La admisión de cada efecto sigue pasando por el controlador existente; CONTINUE puede significar observar, abrir una ronda o completar una comprobación permitida, según su contrato actual.

Si un criterio del encargo exige cerrar una misión nativa, incluir ese cierre entre los criterios y acciones originales. El alcance predeterminado `--closure-scope MISSION` conserva ese gate: no presentar un CLOSE del evaluador como sustituto de `TaskStore.close()`. Para un subencargo legítimamente acotado por la petición original, usar `--closure-scope SUBTASK --closure-scope-ref <referencia-del-encargo-original>`; permite cerrar únicamente ese resultado satisfecho mientras la misión nativa puede seguir OPEN. La salida conserva ambos estados. No cambiar el alcance para eludir un criterio original. Una misión cerrada no se reanuda por un recibo de turno. Si el controlador es teamctl u otro, mantener sus mecanismos: este adaptador solo implementa observación de Suite TaskStore.

Las pruebas con un TaskStore temporal acreditan esta integración local. No acreditan instalación en Windows, conexión remota a ChatGPT, invocación automática en cada final ni funcionamiento de un servicio en segundo plano. La generalización del laboratorio cognitivo ConfigManager queda fuera de esta corrección; sus componentes se conservan.

Para [BAGO5-CCR-001](../bago5/references/behavior-recovery.md), conservar las correcciones en el estado de sesión existente. El puente admite `--corrections <registros.json>` junto con `--receipt`: el archivo contiene una lista de registros y el adaptador aplica sus bloqueos antes del mismo evaluador, sin resolverlos ni ejecutar acciones. La API equivalente es `evaluate(..., corrections=registros)`. No combinar ese archivo con `--observe`; STOP conocido evita leerlo. Las resoluciones se preparan mediante REASSESS_CORRECTION y nunca sustituyen la observación del TaskStore ni la admisión de efectos del controlador. El payload congelado de la Suite queda fuera de este cambio.
