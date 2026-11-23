# BAGO5-CRED-001 v1 · Entrada local y enmascarada de credenciales

## Intención y ámbito

Cuando una tarea autorizada requiera usuario y contraseña (por ejemplo, MariaDB), BAGO5 debe ofrecer, **si la superficie y el cliente lo permiten**, un diálogo local de autenticación que muestre el usuario y enmascare la contraseña. La contraseña nunca se solicita en un chat ni se transfiere al modelo. Preferencia de interacción: ventana nativa; si no está disponible, prompt nativo de terminal con eco desactivado. BAGO5 no fabrica una ventana en ChatGPT o Work si carece de un ejecutor local de confianza.

Esta preferencia es de **entrada enmascarada**, NO una declaración de *modo privado* o de aislamiento global. El contrato `bago5-modo-privado` y su `HOST_CONTRACT.md` siguen siendo obligatorios en los casos que exigen suspensión de observadores. Enmascarar una caja de texto no evita capturas de teclado, lectura de memoria, instrumentación del proceso, malware, registros no controlados ni que el propio anfitrión lea el secreto.

## Selección vinculante de la ruta

Antes de seleccionar GUI o TTY, aplicar [continuidad operativa](operational-continuity.md): comprobar si la operación inmediata requiere autenticación nueva. Si un canal ya autenticado, autorizado y comprobado cubre esa operación, continuar por él sin pedir otra contraseña o conexión. Conservar canal, operador, destino y alcance; una sesión del panel no acredita autenticación SSH ni de la base, y una terminal abierta por el usuario no está bajo control del agente.

1. Identificar **host actual**, operación, superficie, servicio que requiere autenticación, titular de las credenciales y destino (local, SSH, staging, producción) con datos no secretos. Resolver STOP, autorización y preflight antes de abrir nada. Aplicar los pasos de entrada siguientes solo si esa nueva autenticación es necesaria.
2. Si existe **cliente nativo de confianza con diálogo de autenticación** (por ejemplo Windows PowerShell `Get-Credential` o GUI de la propia aplicación), preferirlo, siempre que el secreto permanezca en el cliente o en un proceso local confiable que lo consume directamente y no vuelva al agente.
3. Si no existe diálogo, pero sí **TTY interactivo de confianza**, usar el prompt enmascarado del cliente (`mariadb --user <usuario> --password --database <bd>`, `ssh`, etc.), sin poner la contraseña en argumentos. En PowerShell `Read-Host -AsSecureString` evita eco en terminal; no convertirla luego a texto para imprimirla o pasarla por argv.
4. Si el ejecutor requiere recibir la contraseña por JSON, shell command, argumento, log, stdout, resultado MCP, prompt, memoria o fichero sin gestor seguro, **BLOQUEAR** esa ruta. No usar una variable de entorno temporal como si fuera un canal inaccesible al agente. No ejecutar `mariadb --password=secreto`, `mysql -pSECRETO`, `echo secreto | ...` ni publicar configuraciones con claves embebidas.
5. Si la nueva autenticación necesaria carece de ventana o TTY de confianza (por ejemplo Chat/Work sin adaptador), explicar la operación afectada y esa limitación, y transferir solo ese tramo al ejecutor local autorizado. Conservar tarea, fase, permisos y evidencias, sin solicitar la contraseña en el chat. La transferencia no certifica una entrada realizada ni bloquea operaciones independientes cubiertas por otro canal vigente. Resolver expresamente cualquier instrucción anterior que sustituya este relevo.
6. La operación de base de datos debe usar la credencial **en el cliente confiable**; la respuesta para BAGO5 solo contiene estado de conexión/operación y una evidencia no sensible. No conservar usuario si se trata como identificador confidencial; no imprimir DSN con credenciales, command line, stacktrace o respuestas SQL con secretos.
7. Autorización de conexión no equivale a autorización de escritura, migración o despliegue. Cada efecto de BD conserva su puerta y estado.

Ante «permiso denegado», conservar el servicio y canal afectados. Ese texto por
sí solo no prueba contraseña incorrecta ni permite diagnosticar credenciales
de otro servicio. Pedir solo evidencia no secreta que sea necesaria para el
paso vigente; si ese acceso dejó de ser necesario, explicar su sustitución en
vez de seguir solicitando diagnósticos. Un rechazo de autorización no se elude
por otro canal, y la entrada enmascarada no permite abrir una barrera PRIVATE.

## Windows / PowerShell

- Preferencia GUI: `Get-Credential -Message 'Acceso a la base de datos'` ejecutado **localmente** y por el usuario en una sesión confiable. El `PSCredential` debe consumirse en la misma operación autorizada, sin volcarlo a consola, archivos ni variables controladas por el modelo.
- Si la herramienta cliente tiene su propia ventana de credenciales, preferir esa interfaz. Para MariaDB CLI, el prompt nativo `mariadb --user NOMBRE --password --database NOMBRE_BD` no muestra los caracteres, pero es una **entrada de terminal**, no una ventana GUI.
- Evitar hacer que PowerShell capture un secreto si después se va a pasar por parámetros a un programa externo: en ese caso, usar el prompt del cliente externo. La GUI solo es viable cuando un cliente local confiable consume directamente el objeto de credenciales.

## Invariantes de seguridad

- NEVER_CHAT_SECRET: la contraseña no aparece en Chat, Work, Codex prompts, memorias, Vault, logs, pantallas observadas ni recibos.
- NO_ARGUMENT_SECRET: nunca en línea de comandos, URL ni argumentos MCP.
- NO_ECHO: la entrada oculta cumple su cometido visual, pero no prueba privacidad frente al host.
- FAIL_CLOSED: sin adaptador local confiable, TTY o diálogo real, no se simula que existe.
- USER_CONTROLLED: el usuario introduce las credenciales; los agentes no las inventan, buscan ni recuperan sin autorización.
- STOP_PRESERVED: STOP bloquea aperturas y acciones posteriores.
- REUSABLE: esta regla se aplica a cualquier servicio con usuario/contraseña, no solo MariaDB, conservando el método de autenticación propio del proveedor.

## Aceptación / vectores

| ID | Caso | Resultado exigido |
| --- | --- | --- |
| C01 | Windows con cliente GUI confiable | Diálogo local con usuario visible y contraseña enmascarada; secreto no sale del proceso que lo consume. |
| C02 | Terminal MariaDB interactivo sin GUI | Prompt `--password` sin eco; no contraseña en argv. |
| C03 | Nueva autenticación imprescindible y ChatGPT sin entrada local confiable | `BLOCKED_LOCAL_INPUT` solo para ese tramo; relevo sin pedir contraseña. |
| C04 | Intento de pasar `--password=xxx` | FAIL cerrado. |
| C05 | Intento de escribir secreto en Memoria Viva, Vault o logs | FAIL cerrado. |
| C06 | STOP activo | No abrir diálogo, no lanzar operación. |
| C07 | Ventana con caracteres ocultos pero observación del host no controlada | No declarar PRIVATE, VERIFICADO ni aislamiento. |
| C08 | Autenticación válida y escritura no autorizada | Solo validar conexión; no escribir en BD. |
| C09 | Canal autenticado y comprobado cubre la operación inmediata | Continuar por él sin pedir otra conexión ni contraseña. |
| C10 | SSH rechaza conexión y el panel conserva un acceso distinto | Acotar el error a SSH; no atribuir contraseña incorrecta ni capacidad de consola al panel sin prueba. |
| C11 | «Conectado» desde una terminal del usuario | Conservarlo como declaración de esa intervención; no afirmar control de la terminal ni conexión observada por el agente. |

La existencia de este contrato no implementa por sí misma un adaptador local, integración de BD o UI en el host. Aceptación de casos reales: NOT_RUN hasta pruebas en Windows y el destino del servicio.
