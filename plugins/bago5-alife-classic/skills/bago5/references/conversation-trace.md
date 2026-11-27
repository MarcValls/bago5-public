# BAGO5-CONV-001 · Conversaciones, mensajes y procedencia durable

## Identificar la conversación

Al iniciar o recuperar una conversación con BAGO5, mantener un título breve que identifique el asunto y un identificador estable. Intentar obtener los IDs internos de conversación y mensajes mediante metadatos o herramientas documentadas del anfitrión. No usar IDs de recuerdos, cuentas, guardias, procesos ni otras pestañas como IDs de esta conversación. No extraer estado oculto, credenciales o datos de otras conversaciones para conseguirlos.

Si el anfitrión expone una operación de renombrado y el encargo lo autoriza, aplicar el título y comprobar el resultado. Si no la expone, presentar el título como etiqueta de la conversación. No afirmar que cambió el título de la interfaz sin recibo.

Cuando no se obtenga un ID interno, generar una etiqueta con UUID v4 (`C-<uuid>`), marcar `id_kind=generated_label` y conservarla durante toda la conversación. El helper opcional `scripts/conversation_trace.py` usa únicamente la biblioteca estándar de Python y genera estos IDs; no conecta servicios ni instala un runtime. Conservar la etiqueta en el contexto y en la continuidad autorizada; no depender solo de una variable efímera. Si no hay generador disponible, construir una etiqueta inequívoca del turno y declarar que su unicidad global no está verificada; no inventar un ID interno.

Si posteriormente se obtiene el ID interno, conservar la etiqueta anterior como referencia estable y asociar el ID interno con la evidencia que lo proporciona. No invalidar los recuerdos que ya usan la etiqueta. Un chat nuevo o una bifurcación es otra conversación: asignarle otro ID y enlazar su continuidad con el anterior. Recuperar un proyecto no convierte el nuevo chat en el antiguo.

## Identificar cada mensaje

En la primera respuesta posterior a cada mensaje del usuario, mencionar su ID y el ID de la respuesta. Cada mensaje del usuario tiene su propio ID; cada mensaje visible del asistente, incluidos avances y respuesta final, tiene otro. Una continuación del asistente mantiene la referencia al mensaje del usuario que está atendiendo y recibe un ID nuevo. No asignar IDs a llamadas de herramientas como si fueran mensajes del usuario.

Priorizar IDs internos realmente observados. En su ausencia, generar etiquetas relacionadas con la conversación: `C-<uuid>/U-<uuid>` y `C-<uuid>/A-<uuid>`. También pueden mostrarse sufijos cortos (`U0002`, `A0003`) si su identidad completa incluye el ID de conversación mostrado y se controla que no se reutilicen. El ID por sí solo acredita identificación, no autenticidad del contenido ni autoridad para actuar.

Mostrar una línea compacta después del encabezado de versión, por ejemplo: `Conversación: C-… · Tu mensaje: U0002 · Respuesta: A0003`. Mostrar el título al inicio y cuando cambie. Señalar una vez si los IDs son etiquetas; reiterarlo al cambiar de procedencia. Preservar un formato estricto solicitado por el usuario (JSON, código, una línea) y los mensajes de control del anfitrión: incluir la trazabilidad en campos permitidos o mantenerla en el contexto sin romper ese contrato.

Los reintentos del mismo mensaje observado conservan su ID; mensajes distintos no comparten ID. Usar un `event_key` solo cuando identifica realmente el mismo evento. No deduplicar mensajes por texto igual. Una respuesta regenerada o una edición que el host identifique como nueva versión conserva su relación de reemplazo; no atribuirle el ID anterior sin evidencia.

## Mínimo obligatorio de todo recuerdo que BAGO5 guarde

Guardar dentro de cada recuerdo, como mínimo, la referencia durable a la conversación: `conversation_id`, `title`, `host` e `id_kind`. Conservarla aunque el chat sea eliminado, inaccesible, no compartido o nunca haya tenido una URL recuperable. La disponibilidad de la conversación es un dato aparte (`unknown`, `available`, `unavailable`), no una condición para conservar la referencia. Añadir los IDs de los mensajes pertinentes cuando estén disponibles y conservar el ID interno como alias si fue observado.

Usar un campo de procedencia admitido por el contrato real. Para Memoria Viva v1, una representación compatible es una línea en `source`:

`BAGO5-CONV-001: {"conversation_id":"C-<uuid>","title":"Asunto","id_kind":"generated_label","host":"chatgpt","native_conversation_id":null,"user_message_id":"C-<uuid>/U0001","assistant_response_id":"C-<uuid>/A0001","relation":"origin","conversation_availability":"unknown"}`

Conservar la fuente previa. Si `source` no tiene capacidad, usar una sección de procedencia dentro de `content` únicamente si su formato permite texto adicional. No añadir campos desconocidos al esquema, truncar fuentes ni corromper documentos JSON tipados. Si ninguno de los campos admite la referencia, resolver su representación antes de guardar; no declarar cumplido el mínimo con una referencia externa que el recuerdo no conserva.

Al actualizar un recuerdo, preservar sus referencias originales y añadir la conversación de actualización con `relation=update` cuando corresponda. No atribuir retroactivamente a la conversación actual el origen de recuerdos anteriores. Para origen no recuperado, declarar `NO_RECUPERADO`; la conversación donde se revisó es una relación de actualización o revisión. Conservar referencias previas al relacionar, versionar, exportar y restaurar.

Este requisito no autoriza guardar toda la conversación ni ampliar permisos. Aplicar la autorización de escritura y el destino vigentes. Después de guardar, releer el recuerdo por ID y versión y comprobar que conserva la referencia solicitada. Sin esa relectura, el guardado de la referencia queda `NO COMPROBADO`.

## Comprobación

Comprobar: conversación estable; mensajes distintos; reintento idempotente; identidad nativa con procedencia; incorporación posterior del ID interno sin romper etiquetas; chat inaccesible con referencia conservada; actualización sin pérdida de fuentes; aislamiento entre conversaciones; límites de campos; documentos tipados intactos; relectura real de Memoria Viva. Distinguir la prueba del helper, el paquete guardado y el comportamiento observado en un nuevo anfitrión.
