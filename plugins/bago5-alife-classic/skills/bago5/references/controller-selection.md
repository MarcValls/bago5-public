# Seleccion del controlador de mision

Elegir un solo controlador por mision. La existencia de dos motores opcionales no autoriza duplicar estado ni migrar una mision activa.

Para trabajo por fases, leer e inspeccionar los controladores candidatos sin efectos y completar primero el [preflight de la fase](../../bago5-plan-por-fases/references/phase-preflight.md). Seleccionar operativamente, inicializar, asignar o cambiar configuración solo con GO vigente o dentro de los pasos de preparación que ese contrato habilite expresamente mediante `can_prepare`, sin cruzar un gate pendiente. Explicitar antes cualquier cambio de host o intervención humana necesaria para completar la fase; la existencia de un controlador no acredita su disponibilidad ni autorización.

| Criterio | Suite TaskStore | teamctl portable |
|---|---|---|
| Contrato | plan con checks, dependencias, max_rounds y scope de archivos | mission con work_items, roles, write/output scopes y terminal_work_items |
| Registro | SQLite en --state-dir explicito externo | JSON/recibos en <root>/.bago5-team/runtime |
| Asignacion | assign por check y Relay opcional | claim por work item, pair por conflictos y max_concurrency |
| Evidencia | run-check, record-artifact, consume | run-check, handoff, verify |
| STOP | stop/resume con reason | pause/resume --explicit y ack-stop |
| Uso | Continuidad de una mision Suite o comprobaciones con rondas | Coordinacion de trabajos y entregas del equipo |

No son equivalentes intercambiables: no convertir un plan a una mision cambiando nombres de campos. Respetar el controlador existente. Para una mision nueva, elegir segun el contrato requerido y registrar la eleccion antes de init. BAGO5-TEAM usa teamctl; BAGO5-RUNTIME permite las operaciones de Suite solicitadas. No ejecutar ambos init sobre la misma mision. Si se necesita migracion, requiere alcance propio, conciliacion de evidencias y estados STOP; no implementada por esta integracion.

Ambos motores necesitan ejecucion real de Python. En GPT Classic, sin herramienta o conector de ejecucion, preparar los artefactos y declarar ejecucion NOT_RUN. No instalar servicios por cargar la skill. Ninguno autentica agentes del host ni garantiza interrumpir procesos externos no cooperativos.

Comparacion basada en suite_control.py validate_plan/add_parser/TaskStore y teamctl.py _mission/parser/_dispatch. El ciclo local teamctl tiene pruebas propias; la equivalencia funcional universal no se afirma.

## Compatibilidad de operación antes de asignar

El teamctl portable incluido admite únicamente `AUDIT`, `REPAIR`, `VERIFICATION` y `PROMOTION` en `protocol/mission.schema.json` y en `_mission`. No acepta una misión genérica `DEVELOPMENT` o `INTEGRATION`; no renombrar desarrollo como reparación para eludir el contrato. Para un plan mixto, separar trabajos por su naturaleza real y conservar sus IDs de origen; no afirmar que el plan completo ya está representado por ese runtime.

Comprobar primero el controlador existente y el schema del plan. Si una operación no es representable, bloquear solo su distribución técnica dependiente y conservar la planificación y los preparativos independientes autorizados mediante las herramientas reales del host. No inventar claims, recibos ni estados de teamctl/TaskStore, ni instalar un controlador adicional como fallback. Una nueva ruta de ejecución requiere contrato y aceptación propios; esta guía no la implementa.

Si la misión ya tiene controlador, STOP, claims o evidencias, no pasar a una ruta manual para evitar sus gates. La colaboración nativa del host puede ejecutar trabajos compatibles dentro de ese contrato, pero no lo sustituye ni transfiere permisos entre GPT Classic y Codex. Sin agentes nativos, aplicar secuencia autorizada o preparar handoff; la independencia del verificador requiere una instancia realmente distinta.
