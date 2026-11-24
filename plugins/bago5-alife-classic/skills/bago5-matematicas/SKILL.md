---
name: bago5-matematicas
description: Resolver un cálculo con las herramientas disponibles.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# BAGO5 · Cliente de servicios matemáticos Alife

## Propósito y autoridad

Integra el recorrido mensaje original → interpretación LSI → representación MAT/VAC → modelo explícito → comprobación → contrato/código y evidencias. No sustituye al coordinador BAGO5 ni las restricciones del proyecto. Conserva el objetivo y las fuentes; una representación consistente no demuestra intención correcta ni concede permisos.

**Regla comercial obligatoria:** los servicios avanzados de Alife, incluidos catálogo operativo y verificadores, requieren identidad autenticada, Memoria Viva vinculada y derecho de uso vigente para la capacidad concreta. Esta regla se aplica a todos los consumidores remotos, incluido un administrador salvo concesión explícita del servicio. La instalación del plugin, un alias, un resultado anterior o un campo `paid`, `owner` o `authorized` suministrado por el modelo nunca conceden acceso. El servidor vuelve a comprobarlo en cada operación.

## Recorrido

1. Identifica el proyecto y la petición; conserva el original, su finalidad, restricciones y fuentes. No presupongas que se solicita escribir recuerdos, desplegar o cambiar el objetivo.
2. Comprueba las herramientas realmente disponibles del servicio Alife y su identidad/versión. No construyas un endpoint por concatenar `/mcp` al dominio, ni reutilices otra memoria o el Site del autor. El contrato de interfaces de [servicio](references/service-contract.json) describe la candidata, no acredita herramientas conectadas.
3. Resuelve la cuenta y el vínculo de memoria por el canal autenticado del host. Para activar servicios, completar autenticación/vinculación con consentimiento; no pedir tokens, cookies, cabeceras ni callbacks en el chat. Las comprobaciones de suscripción, cuotas y revocación corresponden al servidor. Si no hay una ruta comprobada, indicar `ALIFE_SERVICE_NOT_CONNECTED` o el rechazo real; la petición sigue pendiente, no fingir resultados.
4. El catálogo y los perfiles LSI operativos se obtienen del servicio protegido. LSI examina el mismo mensaje original desde perspectivas complementarias, no traducciones encadenadas ni mayorías. Mantén agencia/relaciones (euskera), procedencia/evidencialidad (incluido turco), negación, referentes, tiempo y las demás perspectivas pertinentes del catálogo. Son heurísticas, no agentes independientes ni propiedades exclusivas de hablantes. El modelo del host produce observaciones trazables; el verificador solo comprueba su estructura y modelos explícitos, no comprende por sí solo la intención.
5. Conserva citas literales, contexto, procedencia y alternativas. Reconciliar por dimensión, referente, tiempo y ámbito. No elimines una restricción explícita porque otras interpretaciones la contradigan. Usa `UNKNOWN`, `DISPUTED` y `NO_RECUPERADO` cuando proceda.
6. Selecciona MAT por Dominio → Sistema → Representación → Expresión; VAC permanece provisional. Devuelve la formalización a lenguaje natural y contrástala con la petición. Antes de enviar contenido al servicio, comprobar que el usuario autorizó ese tratamiento y enviar solo lo necesario. Tener una suscripción no concede permiso de lectura a recuerdos ajenos.
7. Invoca únicamente herramientas expuestas y autorizadas. Los argumentos llevan identificadores de solicitud/vínculo y modelos, no decisiones comerciales. No incluir credenciales. El servidor verifica la identidad del transporte y derechos desde sus sistemas autoritativos. Las cuotas y deduplicación de consumo son de servidor.
8. Interpreta resultados según su alcance: SAT/UNSAT en modelos finitos, contraejemplo en traza suministrada o álgebra exacta acotada. No es una prueba general del programa, de la autorización o de la interpretación. La generación de un predicado puro no ejecuta aplicaciones ni autoriza cambios.
9. Para implementar código, coordina el especialista de desarrollo existente conservando original → observación → modelo → contrato → pruebas. Para guardar en Memoria Viva o GitHub usa solo las herramientas y permisos propios del proyecto. No copiar conversaciones o secretos por defecto.

## Sin acceso comercial

No sustituir un servicio Alife denegado por una llamada directa al kernel, un servidor de desarrollo, otra cuenta o una supuesta excepción de propietario. No descargues ni instales el motor para evitar el gate. **El plugin distribuible no contiene ese motor.** Puedes explicar el bloqueo o atender una consulta matemática general fuera del producto, sin presentarla como ejecución del servicio, sin usar sus activos protegidos y sin declarar sus comprobaciones como realizadas.

Un Site o página de documentación no autoriza servicios. La UI futura utilizará el mismo servidor y el mismo control comercial; no existirá una segunda API abierta. El código de desarrollo del propietario está separado de esta distribución y no es una vía de ejecución para terceros.

## Estado de esta versión

Cliente e interfaces empaquetados; núcleo y frontera de acceso comprobados en entorno aislado con adaptadores de prueba. **Endpoint de producción, OAuth Alife, backend de suscripciones, cuotas duraderas y prueba ChatGPT/Codex con terceros: NOT_RUN.** No hay MCP nuevo conectado por esta actualización. La disponibilidad de la skill depende de que el host cargue la nueva release; no afirmar invocación host probada por guardar el paquete.

Las funciones de memoria y auditoría semántica ya existentes se conservan; esta ampliación no las reetiqueta retroactivamente como servicios de pago. ADL y Copilot continúan fuera de esta fase.

## Cierre y parada

No hay una parada global implícita al terminar una llamada o una consulta. Aplica STOP únicamente cuando exista una orden STOP vigente, una revocación, una denegación aplicable, un riesgo que exija detener esa acción o un resultado incierto que requiera reconciliación. Una denegación de servicio comercial bloquea únicamente las operaciones que dependan de ese servicio; permite continuar consultas matemáticas generales independientes, sin presentarlas como uso del servicio Alife. Al cerrar, distingue lo formalizado, calculado, ejecutado, comprobado y bloqueado.
