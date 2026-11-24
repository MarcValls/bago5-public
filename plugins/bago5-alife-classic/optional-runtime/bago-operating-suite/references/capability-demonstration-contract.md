# BAGO-CDP-001 — Construcción y demostrabilidad progresiva

**Estado del documento:** contrato operativo transversal de BAGO Operating Suite 1.1.0.
**Ámbito:** cualquier capacidad material (agentes, motores, API, automatización, interfaces, datos, juegos y otros dominios). Esta norma no confiere permisos, no ejecuta proyectos y no promociona automáticamente evidencias.

## Principio y obligaciones inseparables

**Construir capacidades y demostrar progresivamente su funcionamiento son responsabilidades inseparables del desarrollo.**

1. **Materialización observable:** una capacidad debe convertirse en un comportamiento funcional, observable y comprensible en la frontera declarada. Los mecanismos de observación apropiados pueden ser interfaz gráfica, CLI, API, registros estructurados, trazas, estado o artefactos; elegir uno no prueba automáticamente los demás. Si la capacidad está destinada a una interfaz, probar también su conexión real con el comportamiento, no solo su aspecto visual.
2. **Demostrabilidad incremental:** cada capacidad debe tener un recorrido acotado y reproducible, independiente de la **finalización** de funciones no relacionadas de la plataforma. Esto no significa independiente de las dependencias necesarias para ejecutarse; las dependencias esenciales se declaran, y las no disponibles se registran como bloqueo. Una simulación o mock debe identificarse y nunca presentarse como prueba del entorno real.

No convertir BAGO5, ADL ni otra plataforma en requisito universal del método. Su adopción es específica del proyecto: un sistema productor puede ofrecer observabilidad y un evaluador independiente comprobar los resultados mediante la interfaz adecuada.

## Ciclo de capacidad

**DEFINIR → CONSTRUIR → INTEGRAR → OBSERVAR → PROBAR → VERIFICAR → DEMOSTRAR → CONSERVAR**.

- **DEFINIR:** alcance, identidad, demanda, frontera, aceptación, fallos, límites, dependencias y recorrido de demostración.
- **CONSTRUIR:** implementar una unidad útil sin incorporar funcionalidades ajenas para declarar éxito.
- **INTEGRAR:** conectar la unidad con el punto de entrada real en la frontera prevista.
- **OBSERVAR:** exponer la respuesta o cambio de estado real y las decisiones relevantes, sin confundir visibilidad con funcionamiento.
- **PROBAR:** ejecutar rutas nominales y negativas autorizadas; registrar NOT_RUN si faltan recursos.
- **VERIFICAR:** asociar resultados a la identidad exacta de la versión/candidato, entorno, pruebas y evidencias; delimitar cobertura.
- **DEMOSTRAR:** entregar a terceros los pasos reproducibles, entradas, resultados esperados, observables y evidencias contrastables.
- **CONSERVAR:** comparar los comportamientos protegidos antes/después; no perder capacidad por incorporar otra.

En tareas de lectura, consulta o cambios no materiales, no imponer ejecuciones o artefactos irrelevantes. Para cambios materiales, diseñar la demostración desde el inicio, aunque quede en estado PROPUESTO o BLOQUEADO.

## Contrato mínimo del recorrido

Cada capacidad material afectada tendrá una ficha (no necesariamente un archivo independiente) que registre:

1. `project_id`, `capability_id`, `claim` y `candidate_id` (o `NOT_BUILT` mientras sea propuesta).
2. Frontera mínima, punto de entrada y dependencias imprescindibles; indicar si depende de trabajo incompleto no relacionado.
3. Precondiciones, pasos concretos, entrada/recurso de prueba y resultado esperado.
4. Observable y canal apropiado (`ui`, `cli`, `api`, `trace`, `state`, `artifact`, `hardware` u `other`), más una ruta negativa o explicación de su ausencia.
5. Comprobaciones ejecutables/autorizadas, referencias de evidencia, identidad de versión, condiciones y límites.
6. Estado de la **capacidad** separado del estado de la **acción/tarea**.

El formato genérico recomendado se documenta en [`../schemas/capability-demonstration.schema.json`](../schemas/capability-demonstration.schema.json). El comprobador [`../scripts/verify_cdp_record.py`](../scripts/verify_cdp_record.py) valida fichas, referencias locales y sus hashes de forma **estática**: PASS no significa que se haya ejecutado el recorrido ni que la afirmación sea verdadera. Se pueden usar esquemas y registros específicos del dominio si contienen información equivalente y son comprobables. No imponer una única infraestructura de evaluación.

## Estados y promoción

Estados de capacidad: `PROPOSED`, `IMPLEMENTED`, `VERIFIED`, `DEMONSTRABLE`, `BLOCKED`.

- `PROPOSED`: ruta definida; todavía no se demuestra ejecución.
- `IMPLEMENTED`: existe comportamiento e integración declarada; no implica que se haya comprobado.
- `VERIFIED`: comprobaciones con resultados y evidencias delimitadas; no implica demostración reproducida por terceros.
- `DEMONSTRABLE`: además, hay ruta reproducible observada en la frontera real reclamada, evidencia contrastable y límites explícitos.
- `BLOCKED`: ruta necesaria identificada, pero una dependencia, permiso o prueba crítica impide demostrarla; registrar condición de desbloqueo.

Estados de acción (`PROPOSED`, `PREPARED`, `EXECUTED`, `VERIFIED`, `VALIDATED`) conservan su semántica de la Operating Layer. **No inferir** estado de capacidad a partir de un estado de acción ni a la inversa. En ausencia de prueba, indicar `NOT_RUN`; una ficha válida no promueve una capacidad a VERIFICADO o DEMOSTRABLE.

## Invariantes

- **INV-CDP-01:** una capacidad no necesita que toda su plataforma esté terminada para ser demostrable.
- **INV-CDP-02:** una interfaz visual por sí sola no constituye una prueba de funcionamiento.
- **INV-CDP-03:** las pruebas demuestran únicamente comportamientos, condiciones y fronteras cubiertas.
- **INV-CDP-04:** agregar una capacidad no debe eliminar ni degradar las anteriores sin justificación, autorización aplicable y verificación diferencial.
- **INV-CDP-05:** la demostración se diseña junto con la capacidad, no solo al finalizar la plataforma.
- **INV-CDP-06:** una parte no verificada no invalida automáticamente capacidades verificadas independientemente.

## Gate DEMONSTRABLE

No declarar `DEMONSTRABLE` hasta demostrar con evidencia **real y reproducible**, para esa capacidad y versión:

- Recorrido y condiciones de ejecución documentados, sin depender de funcionalidades incompletas ajenas al recorrido.
- Punto de entrada conectado a la capacidad y resultados observados, no solo una maqueta, mock no declarado o build exitoso.
- Checks positivos/negativos pertinentes y evidencias contrastables con procedencia e identidad.
- Límites y dependencias conocidos; las comprobaciones y evidencias de conservación correspondientes a cambios materiales.
- Un tercero puede seguir el recorrido. Si no puede, indicar exactamente qué falla o qué está pendiente.

Que una ficha pase un verificador **estructural** no equivale a superar este gate operativo. Un evaluador independiente y/o ejecución real deben confirmar el comportamiento. Los resultados de una plataforma completa no son requisito para declarar la capacidad individual cuando el alcance está cerrado.

## Especializaciones

Las especializaciones pueden detallar canales de observación, pruebas, formatos y herramientas. No pueden relajar estos invariantes ni ampliar permisos. El módulo `bago-app-game-development` conserva su [guía de demostración](../modules/bago-app-game-development/references/capability-demonstration.md), junto con sus workflows de aplicación, juego y conservación diferencial. En caso de ambigüedad, **este contrato general es la fuente normativa** y los módulos añaden restricciones de dominio.
