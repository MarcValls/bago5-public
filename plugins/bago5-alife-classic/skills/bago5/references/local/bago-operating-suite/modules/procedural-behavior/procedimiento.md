# Procedural Behavior — BPBR v0.1 (motor de referencia)

**Tipo:** ejecutable independiente de referencia, CPU/local, no conexión a BAGO/ADL.
**Origen:** `../../integrations/source-packs/BPBR_v0.1_REFERENCE_20261011.zip`.

El compositor del BPBR NO es fuente de autoridad de ejecución. Su bandera de efectos local sirve solo para el entorno de demostración. Si una tarea usa un efecto material del proyecto, exige el ExecutionGateway/AuthorizationBoundary real, objetivo exacto, permiso verificable y recibo; nunca suplantar permisos por `allowed_effects`. No modificar SPBE ni el kernel legacy por copiar este motor.

**Orquestador:** `python scripts/suite_orchestrator.py verify --modules bpbr`; prueba aislada optativa `python scripts/suite_orchestrator.py bpbr-test`; demo explícita en fixture nueva `python scripts/suite_orchestrator.py bpbr-demo --output RUTA_NUEVA`.

**GATE:** reference PASS no implica host runtime PASS. Integración real NO_GO hasta pruebas de permisos, Windows y evaluación independiente.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
