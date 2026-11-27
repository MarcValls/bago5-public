# ALIFE: interacción de memorias, relaciones y evidencias

Contrato de comportamiento del complemento. Revisión 2026-11-26.
No declara desplegada ninguna pantalla ni amplía los permisos de un servicio.

## Objetivo y público

Ayudar a cualquier usuario a operar su contexto desde ALIFE, elegir una o varias memorias, visualizar el origen de cada elemento y relacionar recuerdos, conversaciones o respuestas recuperables, objetivos, artefactos, evidencias y relaciones. La capacidad de relación es general; cada fuente requiere su adaptador y su autorización. No reducirla a encontrar archivos, ni presumir acceso automático al historial de conversaciones.

La experiencia prevista tiene una entrada de producto y distingue configuración, operación, seguimiento y evidencias. El estado privado o público de distribución del complemento no cambia este comportamiento. No codificar la cuenta, los IDs ni las decisiones personales del autor como valores generales.

## Contexto operativo mínimo

Conservar dentro de la misión:
- Cuenta y proyecto identificados, o NO_RECUPERADO donde falten.
- Identidad y permisos efectivos por memoria y por canal.
- Memorias elegidas para consultar y cobertura realmente recuperada.
- Destino explícito de creación cuando haya varios posibles.
- Origen, ID y versión esperada de cada registro que se edita.
- Propósito de las relaciones, evidencia disponible y decisiones pendientes.
- Capacidades visibles y comprobadas, fuente de su comprobación y cambios posteriores.

Un color ayuda a reconocer una memoria; acompañarlo de nombre y, ante nombres iguales, identificador. El color no identifica por sí solo, ni indica permiso, veracidad o cumplimiento.

Seleccionar varias memorias para lectura no concede acceso ni decide dónde escribir. Cambiar la selección no mueve un recuerdo, no cambia el origen de un editor abierto ni copia su contenido. Las referencias conservan fuente, espacio de nombres/proyecto, memoria o ámbito, ID y revisión.

## Interacción adaptable

1. Reconstruir el encargo y lo ya elegido. Distinguir exploración de opciones, decisión del usuario y acción autorizada. Continuar las acciones concretas permitidas; no abrir un menú de primer uso en mitad de una tarea.
2. Comprobar las capacidades reales del canal y las identidades pertinentes. Usar herramientas del servicio cuando existan. No reconectar por un error aislado si la identidad vigente permite la operación.
3. Resolver ambigüedades menores. Preguntar únicamente por una decisión esencial que siga abierta, por ejemplo el destino de creación entre varias memorias. Una elección inequívoca previa sigue vigente.
4. Mostrar una consecuencia comprensible antes de una decisión: nombre del destino, elementos afectados, relación propuesta y fuente. No pedir aprobación abstracta de un trabajo todavía no preparado.
5. Ejecutar lo autorizado; releer el resultado y comparar el delta solicitado. Ante conflicto de versión, releer y conciliar sin sobrescribir cambios ajenos.
6. Si el usuario corrige el objetivo, actualizar alcance, aceptación y relevo. Mantener el trabajo independiente y señalar exactamente lo que aún requiere otro entorno.

No fijar una secuencia de pantallas o preguntas cuando la intención ya está resuelta. No confundir una muestra con una prueba del despliegue.

## Memorias múltiples y límites del conector

Si la web permite varias memorias y el conector autentica una sola, conservar ambos estados por separado. No usar IDs de otra memoria como parámetros de una herramienta que no los admite ni asumir federación por tener enlaces.

Agregar únicamente resultados obtenidos por canales autorizados para cada memoria. Conservar procedencia, revisiones, errores parciales, revocaciones y cobertura. Un fallo en una memoria no demuestra fallo de todas; una lectura satisfactoria no acredita cobertura completa. Descartar respuestas de lecturas obsoletas después de cambiar el contexto.

Para crear, usar el destino elegido; para editar, el origen capturado y la versión esperada. Para relacionar, comprobar acceso a ambos extremos y permiso de escritura del lugar donde se guardará la relación. Las referencias no comparten automáticamente contenido ni deben revelar datos de extremos inaccesibles. La visibilidad compartida, la invalidación de caché y las relaciones entre relaciones requieren controles de servicio, no solo instrucciones del complemento.

## Relaciones

Distinguir coincidencia de referencia, igualdad textual, afinidad léxica, propuesta semántica y relación declarada por el usuario. Ninguna similitud equivale automáticamente a identidad, causalidad, verdad o aceptación.

Conservar los elementos y la relación como objetos localizables con su procedencia. Una relación puede ser extremo de otra. Registrar propósito, método o productor, fuentes, revisión y límites. Las propuestas permanecen propuestas hasta la decisión que corresponda al contrato. No deduplicar por título, texto o ID local.

Antes de automatizar un detector, comprobar que existe, su alcance, límites y evidencia de ejecución. Una configuración o un nombre de módulo no instala ese detector. Sin adaptador semántico ejecutado, declarar NOT_RUN para análisis semántico.

Si el catálogo ofrece el contrato de relaciones generales, utilizar sus operaciones nativas: contexto con propósito, propuesta, lectura exacta, historial y decisión. Descubrir sus esquemas antes de llamarlas; conservar `request_id`, revisiones y el cierre de acceso a extremos y fuentes. `propose_general_relation` crea una propuesta, no una relación aceptada. `decide_general_relation` requiere una decisión autorizada y su versión vigente. Ante respuesta incierta, consultar `get_general_request` cuando esté disponible antes de repetir un efecto. No introducir estas operaciones como si estuvieran cargadas en un conector que solo expone recuerdos.

## Evidencias

La vista de Evidencias debe permitir localizar una afirmación, su comprobación y sus vínculos a recuerdos, objetivos, artefactos y relaciones. Registrar:
- Afirmación concreta y alcance.
- Método y acción ejecutada o pendiente.
- Entorno: real, fixture, simulación o desconocido.
- Resultado observado, fecha cuando conste y límites.
- Fuentes o recibos recuperables con sus referencias exactas.
- Autor o ejecutor consignado, revisión realizada y criterio de aceptación cuando exista.

Separar datos declarados, comprobación registrada, verificación sustentada y aceptación del usuario. Guardar una ficha, comparar una huella, relacionar un objetivo o marcar una tarea no convierte automáticamente la afirmación en verificada ni el objetivo en cumplido. Un productor consignado no equivale a autoría autenticada.

Si falta una fuente necesaria, marcar NO_RECUPERADO y conservar la referencia. No reemplazar una revisión por la última disponible. Los documentos inválidos o con versión no admitida se conservan y se muestran como tales; no reserializarlos con pérdida de campos.

Usar únicamente el schema y operaciones anunciados por el servicio. Si el incremento usa un sobre versionado dentro de un recuerdo nativo, identificarlo como adaptación de contenido, conservar los campos existentes y no afirmar que el servidor ya incorpora una entidad o API de evidencias. Una futura integración de Vault debe verificar identidad, permiso y revisión del artefacto; una URL no basta.

## Concurrencia y continuidad

Un responsable por destino de escritura. Se pueden paralelizar lecturas independientes o archivos distintos; no controlar a la vez las mismas pantallas del usuario. Ante aviso de concurrencia, terminar la inspección pendiente, conservar el contexto y serializar los cambios.

Antes de una escritura, comprobar la versión vigente, el alcance y los cambios de otro actor. Usar expected_version o el mecanismo de comparación disponible. Una respuesta tardía de una memoria no puede cambiar los permisos o el contenido mostrado para otra. No afirmar que una escritura ya confirmada se canceló porque cambió la selección.

El relevo en el mismo recuerdo debe incluir objetivo detallado, decisiones, contrato, archivos y versiones, cambios efectivos, pruebas y evidencias, pendientes priorizados, arranque ejecutable y aceptación. Preparar un relevo no acredita que Work o Codex lo haya recibido o ejecutado.

## Evolución previa al lanzamiento

No incluir en el primer uso pasos de migración cuya necesidad no esté acreditada para la cuenta y la versión elegidas. Si un encargo autorizado pide retirar referencias obsoletas, inventariar primero rutas, configuración, dependencias y usuarios afectados en la fuente desplegada. Conservar el historial real de registros, archivos, copias de seguridad y recuperación operativa. No borrar datos ni retirar referencias por inferir que son antiguos.

La ruta de entrada, el selector y el estado de memoria deben converger en el producto desplegado. Una candidata de repositorio o una revisión del complemento no equivalen a publicar el sitio. La publicación del complemento y el despliegue de ALIFE se verifican y autorizan como acciones identificables.

## Cierre

Informar por separado diseño, código implementado, pruebas ejecutadas, actualización efectiva del complemento, despliegue y aceptación. Para cada límite, indicar la siguiente tarea concreta y el responsable posible. No etiquetar un comportamiento como verificado solo por haber escrito estas instrucciones.

## Comparación contextual

Aplica [BAGO5-GCC-001](context-governance.md) al comparar elementos y relaciones. Conserva origen, aplicación, revisiones y cobertura. Revalida el acceso de los extremos y de la evidencia antes de usar el resultado. La propuesta contextual conserva su carácter de hipótesis.
