[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Revisión de comportamiento procedural

Sobre el código y contratos actuales, traza cada procedimiento desde su activador hasta el resultado: actor, estado inicial, precondiciones, decisión, efecto, autorización, recibo, error y STOP. Busca rutas que omitan un control, orden incorrecto de fases, transiciones imposibles y efectos sin evidencia.

Para corregir una conducta aprendida o el cierre prematuro, aplicar [decisión de turno y corrección del procedimiento](../bago5/references/turn-decision.md). Conservar condición de activación, objetivo y restricciones; comparar conducta anterior y candidata mediante casos positivos y contraejemplos ejecutados. Una corrección verbal no acredita cambio de conducta. Los recuerdos pueden orientar la propuesta, pero no conceden autoridad ni cambian el objetivo por sí mismos.

Aplicar [BAGO5-CCR-001 · conservación y recuperación](../bago5/references/behavior-recovery.md) al corregir una conducta: precisar qué ejecución se impide, qué conducta correcta se conserva y bajo qué condiciones vuelve a ser pertinente. Comprobar tanto el bloqueo del caso incorrecto como la recuperación del caso válido. Un fallo local no justifica convertir una regla condicionada en una prohibición general. Si la conducta válida exige sustituir la acción anterior, conservar el vínculo y los criterios originales sin reproducir su comando por inercia. Exigir también pruebas de STOP, revocación, obsolescencia y resultado incierto.

Un flag local, fixture, demo o allowlist no concede permiso para un efecto real. Los efectos materiales necesitan el ExecutionGateway o boundary real del proyecto, identidad de objetivo, autorización verificable y recibo observable. No los simules ni suplantes.

El modo BPBR requiere una Suite externa íntegra que incluya el paquete de referencia. Aplicar [runtime bridge](../bago5-acceso-motor-local/SKILL.md) para ejecutar, con herramientas reales, `python <suite-externa>/scripts/suite_orchestrator.py bpbr-test`; para demo explicita usar `bpbr-demo --output <ruta-nueva-autorizada>`. Las pruebas de referencia no acreditan permisos ni integracion BAGO/ADL. Su compositor/allowed_effects no sustituye al ExecutionGateway del proyecto.

El runtime congelado tambien conserva SPBE bajo runtime/BAGO-4.11.10/backend/.bago/core/bago_spbe; es una implementacion del runtime original. Usarlo solo a traves de su contrato comprobado; no afirmar instalacion o activacion en otro proyecto por empaquetarlo. Mantener distintos BPBR, SPBE y los controles reales del proyecto.

Para comprobar el compilador SPBE incluido sin duplicar su motor, usar [run_spbe.py](../../optional-runtime/spbe-reference/run_spbe.py) con test o example. El ejemplo compila un SemanticTask sintetico y produce una propuesta/envelope PEC; no ejecuta efectos ni concede autoridad. Para una tarea real, construir sus entradas segun el API y los contratos del proyecto autorizado, no reutilizar la identidad sintetica.
