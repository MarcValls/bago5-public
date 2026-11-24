# Plan/Fase y trazabilidad

El objetivo describe el resultado. Cada plan propio del objetivo conserva el procedimiento literal, su fuente y versión. Cada fase pertenece a un plan y cada trabajo a una fase. Mantener los identificadores de los registros existentes y comprobar propietario, memoria, proyecto, objetivo y autorización efectiva antes de cualquier escritura.

Al inicio o reanudación de cada fase, aplicar el [preflight obligatorio](phase-preflight.md) antes de selección operativa, asignación o modificación. Conservar su dictamen y las referencias en el registro ya autorizado o la conversación; comprobar herramientas, accesos, permisos, ejecución, verificación, entrega y dependencias. Comunicar por adelantado cambios CODEX/WORK/CHAT e intervenciones humanas. El recibo local de preflight no añade campos ni estados a las fases v1 ni al contrato candidato v2: usar únicamente campos o anexos admitidos por el backend y no migrar ni guardar automáticamente para registrar el control.

## Leer y actualizar fases históricas

1. Inspeccionar la firma de lectura y escritura del conector activo. Si el esquema guarda fases en `goal.plans[]`, recuperar la revisión, el identificador estable de la fase y el contenido original. Si falta el literal del plan padre, marcar `NO_RECUPERADO`. Conservar en borrador cualquier plan nuevo cuyo backend solo admita fases.
2. Para una actualización autorizada, respetar el control de concurrencia real (`expected_version` cuando se admita), las dependencias y los campos que deban preservarse. Ante conflicto, releer la revisión antes de reconciliar. Si la herramienta admite fase v1 estructurada, usar esa representación.
3. Usar el sobre legado únicamente si el conector admite y normaliza ese formato. Mantener `id`, `title`, `status` y `version` tanto en el nivel exterior como dentro del objeto, con valores idénticos. El `content` exterior contiene el texto `PLAN_FASE_V1`, un salto de línea y la serialización JSON de la fase v1 íntegra. Esta conserva su `content` literal, `schema_version`, `phase_order`, `phase_goal`, `deliverable`, `acceptance_criteria`, `depends_on_phases` y `tasks`. Si no se puede conservar algún campo, dejar el cambio pendiente.
4. Releer después de guardar y cotejar la versión, el texto, los IDs y las dependencias. Comprobar que el servidor ha normalizado la fase y que conserva los demás registros. Las fases dependen únicamente de etapas anteriores del mismo plan. Los trabajos dependen de trabajos de su fase sin ciclos.

## Evaluar un contrato v2

El [esquema MV-TRACE-002 v2.0.0](../schemas/traceability-v2.schema.json) define un intercambio candidato. Comprueba por separado la persistencia y las operaciones que ofrece el backend seleccionado, incluidas sus ACL. En v2 cada plan mantiene una identidad propia y referencia el objetivo. Una conversión desde v1 exige fuente literal, correspondencia de IDs, autorización y ensayo reversible sobre una copia.

Relaciona cada trabajo con casos versionados, ejecución de una candidata exacta, recibos, verificación y aceptación por el actor autorizado. Distingue avance declarado, cobertura de pruebas, verificación y aceptación. Para este contrato, excluye del cálculo de avance los trabajos cancelados y presenta `N/A` cuando el denominador sea cero. Conserva revisiones y eventos con su procedencia, además de longitud en bytes UTF-8 y SHA-256 de los textos literales.

La [prueba local del contrato](../tests/verify_contract_v2.py) usa Python y `jsonschema` con datos sintéticos. Cubre estructura, enlaces, documentos literales y condiciones de aceptación. La autenticación, la autoridad de un actor y la existencia y validez de los recibos necesitan comprobación en el sistema correspondiente.
