# Primer uso, configuración y recuperación de ALIFE

Guiar todo el recorrido desde la conversación y ejecutar los pasos autorizados que el anfitrión permita. Reservar las pantallas oficiales para identificar al titular, confirmar su correo, aceptar las condiciones aplicables o conceder permisos que el agente no puede otorgarse. Dar el siguiente paso útil, comprobar su resultado y continuar; no sustituir el encargo por una lista de enlaces.

## Contenido

- [Entrada y continuidad](#entrada-y-continuidad).
- [Cuenta y memoria](#cuenta-y-memoria).
- [Permisos y conexión](#permisos-y-conexión).
- [Comprobación de memoria y Vault](#comprobación-de-memoria-y-vault).
- [Uso habitual y conservación](#uso-habitual-y-conservación).
- [Interrupciones, privacidad y recuperación](#interrupciones-privacidad-y-recuperación).
- [Cierre de la configuración](#cierre-de-la-configuración).

## Entrada y continuidad

Aplicar [continuidad operativa](operational-continuity.md), [ámbito de memoria](memory-scope.md) y [configuración por anfitrión](host-setup.md). Identificar el cliente actual, el encargo, la memoria elegida y cualquier paso pendiente. Las preferencias y los permisos ya vigentes no se preguntan otra vez. La instalación del paquete no demuestra cuenta, conexión, escritura ni ejecución automática de su guía.

Para un primer uso sin tarea ni elección previa, ofrecer «Crear mi primera memoria», «Conectar una que ya tengo» y «Continuar sin memoria». Usar `alife_empezar` si está expuesta y procede; ofrecer las mismas opciones en texto si no lo está. Aceptar respuestas naturales. Con una tarea concreta o una elección ya hecha, empezar por esa vía; no reiniciar el menú al cambiar de especialista, turno o herramienta.

Si la persona elige continuar sin memoria, atender la tarea sin consultar ALIFE ni solicitar correo o permisos. Si más adelante pide conectarla, retomar entonces. Si pide configurar ALIFE por completo, conducir las etapas siguientes y presentar únicamente la decisión necesaria para el próximo paso. Una configuración completa puede incluir capacidades que la persona decida dejar desactivadas.

Mantener el progreso en el contexto de la operación existente: cliente y versión cuando se conozcan, elección, cuenta comprobada, `memory_id`, proyecto si procede, permisos efectivos, última comprobación, intervención pendiente y siguiente acción. No crear otro motor, registro local, archivo de configuración o recuerdo por el mero hecho de empezar. Guardar continuidad en ALIFE solo dentro del alcance autorizado.

## Cuenta y memoria

### Crear la primera memoria

Usar [Activar mi memoria en ALIFE](https://alifememories.com/bago5/activar). Explicar que el correo se introduce y confirma en el servicio, no en la conversación. La persona decide el registro y acepta las condiciones aplicables en su pantalla oficial. La aceptación del aviso de pruebas, la analítica opcional y la autorización del conector son decisiones diferentes; no seleccionar opciones sin una elección aplicable ni presentar controles opcionales como obligatorios.

La solicitud de correo y el enlace de un uso no prueban entrega ni conexión. Dejar la confirmación en manos del titular. No pedir contraseñas, enlaces privados, códigos, cookies, tokens, cabeceras de autorización o callbacks en el chat. Si ya hay una sesión válida de esa cuenta, reutilizar el flujo de activación que ofrezca ALIFE sin solicitar otro correo innecesariamente. No enviar un correo ni activar un registro sin la elección expresa de esa persona.

Después de la confirmación, comprobar qué memoria se creó o reutilizó. La activación puede reutilizar una existente o pedir selección entre varias; no crear otra por un reintento ni elegir la primera por su nombre. Pedir el nombre solo si el flujo actual permite nombrar una memoria que realmente deba crearse. Si el resultado de la creación es incierto, consultar el estado antes de repetir el efecto.

### Conectar una existente o administrar espacios

Comprobar primero la identidad de la conexión actual, si la persona autoriza ese acceso. Si cuenta y memoria corresponden a su elección, seguir con los permisos necesarios. Si todavía no hay conexión, guiar la selección en el consentimiento oficial. En la web, usar [Memoria Viva](https://alifememories.com/memoria-viva) para abrir o elegir el espacio. Un usuario nuevo no necesita recuperar datos de Sites ni de versiones internas del producto.

Cuando el anfitrión exponga el gestor autenticado y sus herramientas reales, se pueden usar `alife_get_onboarding_status` y `alife_list_memories`. Crear con `alife_create_memory` solo por petición válida, con su esquema vigente, `confirm_create_memory:true` y un `request_id` estable para la misma intención. Seleccionar con `alife_select_memory` y la versión actual. Releer el resultado; ante conflicto, conciliar antes de reintentar. No confundir `create_project` con creación de una Memoria Viva.

El borrador de ChatGPT/Platform con un único MCP de contenido en `/mcp` no expone por ello las operaciones del gestor de `/mcp/gestor`. Si faltan, completar la gestión de espacios en la web de ALIFE y retomar aquí. No inventar una herramienta, pedir scopes administrativos a un recurso que no los admite ni exigir complementos privados del autor. Una selección de cuenta no cambia la memoria vinculada a un grant OAuth existente: para cambiarla, autorizar la conexión correspondiente y verificar el nuevo `memory_id`.

## Permisos y conexión

Explicar el permiso concreto cuando haga falta y solicitarlo mediante el flujo oficial del cliente. «Configurar todo» permite guiar esas decisiones; no sustituye la identidad, la aceptación humana ni el consentimiento efectivo. Comprobar separadamente estas capas:

| Capa | Qué comprobar | Qué no concede por sí sola |
|---|---|---|
| Cuenta y espacio | Titular autenticado, espacio seleccionado y pertenencia | Acceso del anfitrión al contenido |
| Permisos de acceso de la memoria | Lectura y escritura habilitadas por el titular; control de escritura vigente | Scopes OAuth nuevos |
| Concesión del cliente | Recurso, memoria, scopes, vigencia y revocación | Permisos que el espacio mantiene desactivados |
| Encargo actual | Acción, datos y destino autorizados, sin STOP | Permiso permanente para otras operaciones |

Una memoria nueva puede tener `allow_read=false` y `allow_write=false`. En «Permisos de acceso», el titular debe habilitar lectura y, si desea guardar, escritura, y guardar su decisión. El conector no puede abrirse esos controles. La escritura también depende del control `write_enabled` cuando el servicio lo declare. Distinguir acceso OAuth denegado de controles del espacio cerrados; pedir únicamente la corrección que corresponda.

Solicitar permisos por capacidad, sin exigir todos para comenzar:

| Capacidad elegida | Scopes del recurso y condición |
|---|---|
| Consultar proyectos y recuerdos | `/mcp`: `memory.read`, sujeto a permisos actuales del espacio |
| Guardar o actualizar recuerdos, decisiones u objetivos | `/mcp`: `memory.read` y `memory.write`, escritura del espacio y encargo válido |
| Leer archivos | `/mcp`: `memory.read` y `vault.read` |
| Cargar archivos | `/mcp`: `memory.read` y `vault.write`; añadir lectura solo si se quiere recuperar y verificar los bytes |
| Publicar archivo con documentación y relación | Los scopes que exija el contrato real de publicación; comprobar memoria y Vault por separado |
| Listar o crear memorias mediante gestor disponible | `/mcp/gestor`: `manager.read`; para creación/selección, `manager.memories` consentido |

`vault.write` no implica `vault.read` ni `memory.write`. Una cuenta web conectada no autoriza automáticamente el cliente. No pedir `catalog.admin` para el uso personal ordinario. Conservar los clientes y recursos existentes; no cambiar de audiencia, utilizar credenciales de otro conector ni copiar tokens entre ChatGPT, Codex o Copilot.

Si existe `alife_conectar_memoria`, usarla para el flujo de conexión solicitado. Si no, usar la acción oficial del anfitrión y después `get_memory_identity`. Para Vault, usar `alife_conectar_vault` únicamente cuando esté expuesta y corresponda al consentimiento faltante. Los botones reales y los desafíos del servidor gobiernan el siguiente paso; no construir manualmente `state`, PKCE, redirecciones o enlaces de autorización.

## Comprobación de memoria y Vault

### Memoria utilizable

Tras volver al chat, releer `get_memory_identity` por la conexión que vaya a operar. Contrastar `memory_id`, identidad cuando se exponga, estado del almacén, autorización y permisos efectivos. Resolver cualquier discrepancia antes de mostrar contenido o escribir. No confundir la identidad de cuenta del gestor con la identidad de una memoria.

Ejecutar una lectura inocua y necesaria, como `list_projects`. Una lista vacía es un resultado válido de una memoria nueva. Identificar el proyecto cuando la tarea lo requiera; no imponer crear uno durante el alta. Usar un proyecto existente elegido o crear uno con `create_project` cuando la persona lo pida. Mantener el filtro de proyecto al buscar y recuperar por ID y revisión cuando sea necesario.

Comprobar escritura usando una acción real ya autorizada. Si no la hay y la persona quiere ensayar, acordar un texto inocuo y su destino antes de crear el recuerdo. Una lectura de identidad con escritura habilitada no prueba que se haya guardado nada. Para editar, leer la versión actual, usar la versión esperada, conservar contenido y fuentes previas y releer los campos de la nueva revisión. No crear ni borrar recuerdos de prueba de forma automática; su eliminación requiere el permiso correspondiente.

### Vault utilizable

Descubrir las herramientas de archivos en todo el catálogo del anfitrión antes de concluir que faltan. Elegir una única conexión operadora para la transferencia y comprobar su propia `get_memory_identity` y `get_vault_identity`. Cotejar el mismo `memory_id`, sujeto cuando esté disponible, contrato, disponibilidad de almacenamiento, límites y permisos. Una identidad válida de otra conexión no presta su autorización a Vault. `Authentication required` indica autenticación pendiente; no demuestra ausencia de herramientas.

Aplicar [Vault](../../bago5-alife-vault/SKILL.md) para el contrato y los detalles de transferencia. Para lectura, elegir un archivo autorizado y recuperar su revisión exacta y todos los fragmentos; cotejar tamaño y SHA-256 cuando el contrato los proporcione. Si está vacío, informar que no se ha probado descarga; no fabricar un archivo para aparentar verificación.

Para carga, usar un archivo que la persona haya autorizado y confirmar memoria/proyecto. Conservar `request_id`, revisión y los recibos de inicio, fragmentos y finalización. Resolver un acuse perdido consultando el estado disponible antes de duplicar la solicitud. Si también se concede lectura, recuperar todos los bytes de la revisión final y comparar tamaño y hash con el original. Sin lectura, informar «carga aceptada; relectura de bytes pendiente», sin solicitar más acceso si no lo necesita la tarea. Una transferencia no ejecuta ni extrae el archivo.

Si se solicita publicación documentada, usar las operaciones expuestas de preparación/publicación y comprobar archivo, recuerdo canónico y relación conforme al contrato. No inferir que esos tres elementos existen por haber subido los bytes. La identidad, la carga, la documentación y la relectura son comprobaciones distintas.

## Uso habitual y conservación

Antes de conservar datos de forma recurrente, resolver la política que la persona quiere dentro del proyecto: guardar solo lo que pida, o conservar también categorías concretas acordadas —por ejemplo decisiones y continuidad del trabajo—. Precisar alcance, destino, exclusiones y posibilidad de suspenderla. Reutilizar una política vigente y explícita; si no existe, guardar solo lo solicitado. Conceder OAuth no constituye una política de conservación ni autoriza copiar la conversación completa.

La memoria aportada por el anfitrión, los resúmenes y el contexto local pueden ser parciales o estar desactualizados. ALIFE conserva lo efectivamente guardado y recuperable, no una copia garantizada de todos los chats. Indicar cobertura y fuentes; no prometer eliminar los límites de contexto del modelo, acceder al historial completo o actuar cuando el anfitrión no ejecuta BAGO5. La continuidad entre sesiones se acredita recuperando registros, no recordándolos de forma plausible.

Guiar estas capacidades cuando el encargo las necesite, sin convertirlas en pasos obligatorios para una primera lectura:

| Necesidad | Procedimiento y resultado comprobable |
|---|---|
| Recuerdos e historial | [Memoria Viva](../../bago5-memoria-viva/SKILL.md): búsqueda acotada, versión y relectura de cambios |
| Decisiones y objetivos | Conservar tipo, estado, criterio y evidencia del registro; no cerrar ni completar por inferencia |
| Planes, fases y tareas | [Plan por fases](../../bago5-plan-por-fases/SKILL.md): conservar el objetivo distinto del plan, texto literal y evidencias por tarea |
| Relaciones y archivos documentados | [Espacio y evidencias](workspace-evidence.md) y contratos expuestos: extremos autorizados, revisiones, contexto y decisiones explícitas; una propuesta no se autoacepta |
| Procedencia | [Conversación y mensajes](conversation-trace.md): referencia durable de conversación; etiquetas declaradas cuando falten IDs internos; preservar fuentes anteriores |
| Relevo a otro chat o cliente | [Continuidad](operational-continuity.md): objetivo, restricciones, estado real, fuentes versionadas, pendientes y próximo paso; el receptor comprueba su propio acceso |

Registrar resultados donde ya corresponda, sin crear un segundo almacén o notas duplicadas para completar la guía. No prometer servicios semánticos, reglas de conducta activas, guardias o automatizaciones porque existan textos, pantallas o habilidades con esos nombres. Comprobar capacidad, activación y permiso antes de usarlos.

## Interrupciones, privacidad y recuperación

| Situación | Siguiente actuación |
|---|---|
| Vuelve tras confirmar el correo o autorizar | Retomar el paso guardado en contexto y comprobar el resultado; no empezar otra alta |
| Sesión o permiso aún válidos | Ejecutar la operación elegible sin repetir el consentimiento |
| Token ausente, caducado o revocado | Usar reconexión oficial de ese cliente y recurso; releer identidad y permisos al volver |
| Permiso insuficiente | Explicar la capacidad concreta y dejar que el titular la conceda si la necesita; conservar el trabajo independiente |
| Herramienta no expuesta | Comprobar el catálogo y la variante del anfitrión; usar la web para gestión disponible allí sin afirmar acceso MCP |
| Cuenta o `memory_id` distintos | Detener la operación dependiente; resolver la selección antes de consultar contenido o escribir |
| Conflicto o resultado incierto | Releer versión, recibo o estado; conciliar, sin cambiar automáticamente la clave idempotente |
| Cambio de cliente | Aplicar [configuración por anfitrión](host-setup.md); no heredar identidad, tokens ni permisos de la sesión anterior |
| Sin memoria, «no guardes esto» o exclusión privada de un tramo | Aplicar la exclusión exacta: sin memoria impide acceso a ALIFE; no guardar impide la conservación indicada. No abrir otro almacén para eludirla. Pedir una memoria privada no equivale a desconectarla. Estas decisiones no borran datos anteriores ni modifican las políticas del anfitrión |
| STOP | Detener nuevas acciones hasta reanudación explícita; conservar el objetivo y la incertidumbre sobre efectos ya iniciados |
| Revocar o desconectar | Guiar la acción solicitada en [Conexiones de ALIFE](https://alifememories.com/oauth/connections) y en el cliente según su alcance; comprobar el resultado permitido. No confundir revocar una concesión, desinstalar un paquete y borrar una memoria |

La pregunta «¿por qué?» y una consulta lateral no cancelan el objetivo. Resolverlas y volver al paso elegible. Si se necesita una intervención humana, explicar la dependencia concreta y conservar los pasos independientes que puedan ejecutarse. No insistir con la misma reconexión sin evidencia nueva.

## Cierre de la configuración

Informar de la memoria y el cliente comprobados, capacidades activas, decisiones de conservación y siguiente uso concreto. Distinguir «concedido», «ejecutado», «verificado», «pendiente» y «desactivado por elección». Una instalación de solo lectura puede quedar lista para consultar aunque escritura y Vault permanezcan desactivados. Para declarar comprobada la configuración completa acordada, exigir los recibos de cada capacidad elegida y señalar cualquier ensayo real todavía `NOT_RUN`.

Volver al trabajo de la persona cuando las condiciones de ese trabajo estén cubiertas. No presentar esta guía, una lista de herramientas o una prueba sintética como aceptación de todos los anfitriones.

Fuentes del servicio: contratos `BAGO5-ONBOARDING-002`, `NATIVE-TOOLS-001`, `VAULT-OAUTH`, `ALIFE-WORKSPACE-EVIDENCE-001` y sus descriptores desplegados. Consultar [ALIFE](https://alifememories.com/), [soporte](https://alifememories.com/soporte) y las fuentes del anfitrión enlazadas en [host-setup.md](host-setup.md); una ruta documentada no acredita el estado actual del servicio.
