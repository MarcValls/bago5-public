# BAGO5 · autonomía, bloqueo y continuidad

## Propósito y frontera

Aplicar este procedimiento en misiones de varios pasos y ante bloqueos. Es una guía ejecutada por el agente activo con las herramientas del host; no es un proceso residente, planificador, motor de permisos ni TaskStore. No sustituye las instrucciones del usuario, políticas o límites del entorno. No iniciar subagentes, acciones externas, escrituras o procesos por el mero hecho de que este documento los mencione.

## Plan operativo adaptable

Identificar objetivo, proyecto y candidata, alcance, instrucciones, autoridad, restricciones, STOP conocido, herramientas reales, criterios de aceptación y fuentes. Descomponer cuando aporte valor en objetivos con ID, resultado observable, dependencias, estado, comprobaciones, evidencia y siguiente acción. Mantener el estado en el contexto de trabajo; persistir solo en una superficie existente y autorizada. Usar los estados PENDIENTE, EN_CURSO, BLOQUEADO, COMPLETADO y CANCELADO como etiquetas operativas, no como hechos almacenados. COMPLETADO exige criterios satisfechos y comprobaciones con evidencia; distinguir prueba no disponible y no realizada. No prometer una medida de progreso porcentual sin criterio verificable.

Para cada cambio autorizado: ejecutar, comprobar la candidata real, buscar regresiones pertinentes, corregir fallos dentro del alcance y comprobar de nuevo. Ante fallo conservar el resultado y la evidencia; no declarar PASS por ejecutar, por coincidencia de hash o por prueba simulada. Un revisor lógico no es un agente independiente.

## Bloqueo y permisos

1. Identificar acción bloqueada, destino, causa observable, alcance, efecto y dependencia afectada. Distinguir ausencia de herramienta, fallo temporal, fuente no recuperada, decisión necesaria, permiso ausente, rechazo efectivo, STOP y acción prohibida. No transformar un error técnico en permiso denegado ni atribuir una causa sin evidencia.
2. Examinar alternativas viables que respeten alcance, permisos y seguridad. Preparar todo lo necesario y revisable antes de solicitar una decisión o permiso, si hacerlo está autorizado. Una alternativa no puede eludir una prohibición, rechazo o STOP. No repetir sin límite una operación que ya falló ni intentar escalar por canales no autorizados.
3. Si un permiso o decisión es imprescindible, expresar la acción concreta, destino, efecto, razón y consecuencia de no autorizarla. No pedir de nuevo una autorización ya vigente ni deducir aprobación de silencio. Continuar acciones independientes autorizadas cuando el entorno lo permita, sin ejecutar la acción pendiente.
4. Si la política impide solicitar o el sistema rechaza la operación, registrar el bloqueo real y su motivo observable; no afirmar que se pidió permiso. Si una parte puede completarse de forma segura, continuar con ella. Informar de lo completado y lo pendiente.
5. STOP detiene nuevas acciones propias hasta reanudación explícita; ni una comprobación, checkpoint, memoria ni autorización anterior lo levantan. No afirmar que se detuvieron procesos externos. Revocación y restricciones posteriores prevalecen.

## Corregir conservando la conducta válida

Aplicar [BAGO5-CCR-001](behavior-recovery.md) cuando una corrección o un bloqueo pueda impedir también trabajo legítimo posterior. Conservar el objetivo, los criterios pendientes, la conducta correcta y sus condiciones de activación. Asociar la restricción a su causa y ámbito; no aprender «nunca ejecutar» a partir de «no ejecutar mientras falte esta condición».

Ante un cambio material pertinente, comprobar su resultado por los canales autorizados y reevaluar el estado actual. Resolver de forma trazable únicamente el bloqueo cuya causa haya desaparecido; conservar otros impedimentos. Si el trabajo sigue siendo necesario y oportuno, hay capacidad y autoridad vigentes y no existe STOP ni una barrera aplicable, continuar sin pedir otra vez el mismo permiso. Conservar los fallos anteriores como historia, separados de las observaciones actuales. Si el resultado de una ejecución anterior es incierto, reconciliarlo antes de repetir su efecto.

La recuperación se realiza mientras exista un agente activo y una vía autorizada. No prometer vigilancia residente, reintentos futuros ni ejecución tras cerrar la sesión. La decisión de turno sigue siendo la del evaluador compartido; el registro de corrección pertenece al estado y continuidad existentes.

## Continuidad y recuperación

Antes de una respuesta final o de proponer un relevo, aplicar la [decisión de turno](turn-decision.md). Conservar todos los criterios de origen al integrar agentes o resúmenes. La preferencia de mostrar destinatario se aplica después de decidir; no crea una obligación de detenerse. Un paso local autorizado y realizable exige continuar en este turno; el encargo satisfecho exige cerrar, sin ampliar su alcance. El evaluador compartido `../scripts/turn_decision.py` permite comprobar entradas estructuradas cuando haya Python, sin conceder autoridad ni instalar procesos.

Separar memoria (conocimiento y decisiones), estado operativo (objetivos, resultados y pendientes) y reanudación (comprobación y autorización para actuar). Un mensaje, archivo, recuerdo o handoff no garantiza almacenamiento duradero, completitud, actualidad, permiso o ejecución en segundo plano.

En cambios de entorno o cuando se solicite continuidad, preparar un paquete o registro únicamente en una superficie autorizada y comprobada. Reutilizar [HANDOFF.schema.json](HANDOFF.schema.json) y añadir, donde proceda, instrucciones de arranque, dependencias, objetivos y criterios de aceptación, baseline, candidata, fuentes, invariantes, decisiones y conflictos, acciones/resultados, evidencias y pruebas, bloqueos, pendientes priorizados, restricciones y STOP. Indicar cuándo una parte no se ha recuperado. Si no hay escritura autorizada o disponible, entregar continuidad en la respuesta sin fingir persistencia.

Antes de continuar una misión recuperada, identificar la fuente y versión, verificar proyecto y candidata, comparar con el estado actual y otras fuentes relevantes, revisar permisos y STOP. El hash ayuda a verificar integridad; no prueba que una copia sea la más reciente o completa. Con discrepancias conservar ambas versiones y evitar sobreescrituras. STOP requiere reanudación expresa; recuperar contexto no es reanudar. Una solicitud de continuación no elimina restricciones más estrictas del host ni autoriza acciones fuera del alcance.

## Evaluación y límites

Usar [vectores de autonomía](autonomia-vectores.json) como especificaciones de escenarios y comprobaciones observables. Cada escenario se evalúa en una ejecución real con candidata, host, acciones observadas y evidencia; describir un resultado esperado no constituye una prueba. Registrar PASS, FAIL o NOT_RUN con motivo, y no promediar ni proclamar autonomía general. Comprobar casos positivos y negativos y la conservación de memoria, STOP y conexión con la aplicación. No generar registros sensibles, credenciales ni razonamiento interno en evidencias.
