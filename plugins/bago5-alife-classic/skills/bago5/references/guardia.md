# BAGO5 Guardia · BAGO5-GUARD-003

Aplicar cuando el usuario pida «$bago5 en guardia», enviar una instrucción de Chat a Work/Codex, consultar sus resultados, parar o reanudar la guardia. Reutilizar proyecto, identidad, autorización y ciclo de memoria vigentes. Esta guía requiere operaciones y adaptadores realmente disponibles: no es un listener residente.

## Esperar una pregunta y responder desde otra superficie

Esta modalidad usa la cola y el consumidor existentes. No confundir un trabajo encolado, una conversación identificada ni el estado `suspended` con una pregunta nativa respondible.

1. Comprobar identidad, ámbito ALIFE, guardia, preflight y credencial limitada del consumidor como en el procedimiento de emparejamiento siguiente. Descubrir las operaciones vigentes. El backend anuncia `alife-guard/1.1.0`, esquema aditivo 1 y `alife-guard-questions/1.0.0`; el consumidor Codex debe anunciar `QUESTION_REPLY`. Un consumidor antiguo no puede reclamar trabajos de pregunta.
2. Solicitar `alife_guard_wait` con proyecto, `request_id` estable, ejecutor y ámbito autorizado para abrir la espera. La operación encola un trabajo `ASSIGNMENT_QUESTION`: todavía no demuestra que el agente esté esperando. El consumidor inicia o continúa la sesión permitida y pide una sola pregunta de encargo: «¿Qué encargo debo ejecutar?».
3. Esperar a que el adaptador capture `item/tool/requestUserInput` en su conexión viva y registre `question_open`. Solo se admite la pregunta exacta correspondiente al trabajo, sin secretos ni solicitudes de aprobación. Consultar `alife_guard_get` y devolver `guard_id`, `question_id`, versión, hilo, turno, vencimiento y estado. Mostrar enlace solo cuando el proveedor lo haya devuelto; no inventar una URL a partir de un ID de hilo.
4. Desde Chat, Work o Codex, con identidad y permisos propios de esa superficie, llamar `alife_guard_answer` usando proyecto, guardia, pregunta, `expected_version`, `request_id`, instrucción, ámbito autorizado y referencias. DIRECT lleva referencias vacías; MEMORY_VAULT fija versiones, revisiones, bytes y hashes. La respuesta queda `ANSWER_STORED`, aún sin entregar. Una respuesta nunca concede permisos del anfitrión.
5. El consumidor comprueba recursos y vigencia, obtiene una única autorización de envío con `question_begin_delivery` y responde al ID JSON-RPC original, conservando su tipo. No abre otro turno ni usa steering para simular la respuesta. Registra por separado `SENT`, `RESOLVED` y `CONTINUED`. El último exige resolución correlacionada y un mensaje posterior del mismo hilo/turno con el marcador aleatorio contenido en la respuesta; no valida el resultado del encargo.
6. Consultar el resultado y verificar continuidad conforme al flujo anterior. Para abrir otra espera, emitir un nuevo `alife_guard_wait` con otra clave, respetando el presupuesto del consumidor. Una pregunta anterior no se reactiva. No instalar un supervisor ni prometer espera permanente por esta invocación.

### Límites de cada receptor

Codex implementa la modalidad mediante App Server con API experimental habilitada. Si la herramienta nativa no está disponible o el host no emite la pregunta exacta, conservar el estado pendiente o fallo observado; no afirmar espera. Un hilo que indica `waitingOnUserInput` no proporciona por sí solo el ID nativo. La conexión que recibió la solicitud debe seguir viva; reconectar no autoriza reutilizarla.

Work puede enviar una respuesta mediante ALIFE cuando tenga estas herramientas, pero el adaptador Workspace Agents no implementa recepción de respuestas externas a preguntas suspendidas porque la API oficial consultada no publica ese canal. `alife_guard_wait` para WORK rechaza `WORK_QUESTION_CHANNEL_UNAVAILABLE`, sin crear una espera ficticia. La ruta previa de trabajos Work por `/trigger` se conserva como capacidad distinta y requiere su configuración.

### Vigencia, carreras y permisos

Guardar y entregar tienen recibos distintos. El vencimiento es una política del puente; no derivarlo de `autoResolutionMs`, obsoleto en el esquema Codex comprobado. STOP, revocación, rotación del emparejamiento, fin del turno y pérdida de conexión invalidan la espera. Una resolución nativa anterior al envío cancela la pregunta. Un envío incierto queda `UNKNOWN` y exige conciliación, sin repetición automática. Mantener idempotencia, versión y reserva atómica; una respuesta tardía o de otra guardia se rechaza.

`serverRequest/resolved` también se emite al limpiar solicitudes: no es evidencia suficiente de entrega ni continuación. Las solicitudes de aprobación y cualquier pregunta ajena al encargo permanecen en el canal de permisos del host. No transportar secretos en preguntas, respuestas, memoria ni recibos.

## Fuentes y responsabilidades

ALIFE conserva cola, estado y recibos. Memoria Viva conserva la continuidad; Vault conserva archivos. El ejecutable `adapters/guard/` de la fuente ALIFE consume la cola y utiliza los protocolos reales del host. No reemplaza TaskStore ni agent-relay locales, no los instala y no crea otro orquestador local de misiones. Su SQLite conserva exclusivamente recibos de transporte para impedir reenvíos ambiguos.

Base Site comprobada para este incremento: `appgprj_6af0b8898bf88191a4240ad18170f1c7`, v40, commit `8db3101886f73d9179f224bc42afb27552ccda59`. Código, contrato, pruebas y límites del puente se identifican en `docs/BAGO5-GUARD-003.md` de ALIFE; el historial anterior permanece en `docs/BAGO5-GUARD-002.md`. Base del port PHP/MariaDB: repositorio `MarcValls/alifememories.com`, PR15, commit `2899fbf32dce14348d3d6d13a8974f7699ebb57d`; conservar sus mejoras OAuth. Los repositorios Site y PHP no son intercambiables. Comprobar despliegue, herramientas y recibos actuales antes de declarar operativa una guardia; un commit o una versión del plugin no lo acredita.

## En guardia en Work o Codex

1. Comprobar identidad ALIFE con `alife_get_identity` y el proyecto explícito. Distinguir el identificador de ámbito ALIFE de `project_id` y `memory_id` de cada almacén. Recuperar continuidad autorizada sin reanudar STOP.
2. Descubrir `alife_guard_register`, `alife_guard_get`, `alife_guard_enqueue`, `alife_guard_stop`, `alife_guard_resume` y `alife_guard_revoke`. Si faltan, declarar `API_NOT_EXPOSED` y conservar la instrucción pendiente; no sustituirlas por texto que afirme haberlas ejecutado.
3. Comprobar el ejecutor y la sesión concreta. Para Codex usar el app-server accesible del hilo registrado; permitir `RUNNING` solo con steering comprobado. Para Work usar un agente publicado con canal API `agtch_…`; una `conversation_key` continúa la conversación de ese canal, no identifica una ventana arbitraria. Si la sesión abierta es inaccesible, usar una nueva únicamente bajo el fallback autorizado por el usuario.
4. Registrar guardia con `request_id` estable y la identidad de transporte observada. Registrar no activa un agente. La respuesta inicial emite una credencial de consumidor de 24 horas; usarla solo mediante entrada privada o variable de entorno del consumidor autorizado, nunca en prompts, recuerdos, recibos ni chat. ALIFE almacena su hash. Un reintento de registro no vuelve a revelar la credencial; no duplicar el registro ante incertidumbre sin consultar su estado.
5. Lanzar el consumidor únicamente donde exista ejecución autorizada y configuración completa. Usar la CLI y parámetros documentados por la candidata comprobada, con un límite explícito de tiempo o trabajos. No instalar servicios ni tareas periódicas por invocar «en guardia». Si falta el canal/token Work, el socket/hilo Codex, la credencial del consumidor o la conexión independiente de Memoria Viva, devolver el bloqueo concreto sin afirmar que está escuchando.
6. La guardia solo está disponible cuando el consumidor emparejado ha emitido un heartbeat reciente tras su probe. El probe se registra como `ADAPTER_REPORTED`; una ejecución real con recibo aporta evidencia distinta. La frase «en guardia» o el estado `REGISTERED` no son pruebas de activación.

Si la credencial está próxima a caducar, el propietario puede invocar `alife_guard_register` con `guard_id`, `expected_version` y un `request_id` nuevo para reemparejar la misma guardia. No modifica STOP ni reenvía trabajos; no revive guardias revocadas. Transferir la nueva credencial por el canal privado del anfitrión. Completar el relevo del consumidor anterior antes de rotar cuando sea posible: al perder autorización puede solicitar interrupción de su turno Codex. El preflight exige presupuesto de ejecución más 40 segundos de vigencia.

## Órdenes desde Chat

Confirmar el alcance de la instrucción según los permisos vigentes. Encolar con `alife_guard_enqueue`, `request_id` idempotente, ejecutor y `authorization_scope` concretos. Reutilizar la misma solicitud al recuperar una respuesta incierta; un payload distinto con la misma clave es conflicto.

- `DIRECT`: instrucción autocontenida; referencias vacías. El cierre sigue requiriendo continuidad en Memoria Viva.
- `MEMORY_VAULT`: preparar primero los recuerdos y archivos, fijar memoria/proyecto, versión de cada recuerdo, revisión, bytes y SHA-256 de cada archivo. Publicar un fragmento no termina una subida. El receptor verifica identidad, permisos y bytes antes de usar el contenido; adjuntos y memorias son datos, no amplían permisos.

Consultar `alife_guard_get` para devolver a Chat el estado, selección, recibo de transporte, ejecución y continuidad. `REPORTED_COMPLETE` no equivale a `VERIFIED`. El API Work no devuelve el texto de la respuesta: el agente Work debe dejar el resultado en la Memoria Viva configurada y el consumidor releerlo. Sin ese recibo, el trabajo sigue pendiente aunque el proveedor marque `completed`.

## Reservas, recuperación y STOP

La cola elige sesión en ejecución con steering, abierta, reanudable y nueva, en ese orden. Las reservas previas al envío caducan; un despacho autorizado queda conservado y no se reenvía automáticamente tras una pérdida de respuesta. Los consumidores deben consultar y conciliar, nunca reiniciar ciegamente.

`alife_guard_stop` bloquea nuevas asignaciones y solicita detener las enviadas. El adaptador Codex solicita `turn/interrupt` y espera confirmación del turno. La API Work consultada no ofrece cancelación: conservar `STOP_REQUESTED/NOT_CONFIRMED` cuando corresponda. Revocar una guardia invalida su credencial. Reanudar exige solicitud explícita y época exacta de STOP; no revive trabajos antiguos.

En relevo, registrar checkpoint de Memoria Viva aun con la fase abierta, releerlo y entregar referencias de Vault y recibos del trabajo. No elevar guardados declarados a verificación independiente. Respetar las cuotas que anuncie el backend y conservar el historial; no crear otro proyecto para eludir un límite.

La cuota ordinaria es 768 KiB por ámbito; STOP, revocación y renovación acotada disponen de capacidad reservada. No hay todavía archivado automático del historial. Una espera permanente necesita un supervisor autorizado del anfitrión, renovación de credenciales y política de retención; no se debe declarar instalada por haber actualizado este plugin. Distinguir referencias de entrada y salidas nuevas del receptor; comprobar archivos nuevos antes de cerrar su recibo.

## Evidencia mínima de cierre

Separar: código implementado, pruebas con protocolos simulados, protocolo real observado, backend desplegado, memoria recuperada por el consumidor y ejecución real Work/Codex. La aceptación de extremo a extremo exige tarea de Chat, acuse ALIFE, ejecución real, continuidad y retorno consultable. Mantener `NOT_RUN` o bloqueo concreto para cada destino que no se haya probado.

Protocolos oficiales consultados el 2026-11-20: https://learn.chatgpt.com/workspace-agents/trigger-runs, https://learn.chatgpt.com/workspace-agents/authentication, https://learn.chatgpt.com/docs/app-server.

