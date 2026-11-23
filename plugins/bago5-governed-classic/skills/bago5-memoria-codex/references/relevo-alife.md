# $memoria-codex — entrega de conexión controlada a Codex

## Objetivo y límites

Crear un **prompt textual, listo para pegar en Codex**, que permita al usuario enlazar **el espacio nativo de ALIFE seleccionado** por MCP autenticado. La generación NO conecta a Codex, NO configura su entorno, NO comparte recuerdos y NO concede permisos. No transferir tokens, cookies, sesiones, claves, encabezados de identidad ni datos de recuerdos al prompt. Conservar los datos, la configuración y el alcance de acceso durante el relevo.

## Resolver memoria disponible y activa

1. Identificar la app «ALIFE Memoria Viva nativa» mediante la [referencia del servicio](destino-alife.md). Utilizar únicamente ese conector para el relevo.
2. Consultar `get_memory_identity` con autenticación y `list_projects` cuando proceda. Contrastar el espacio pedido con `memory_id` y el contrato con `alife-native-memory/1`. Registrar lectura y escritura por separado.
3. Reutilizar la selección explícita del usuario. Si faltan datos para distinguir dos espacios nativos, solicitar únicamente esa elección.
4. Transmitir la identidad del espacio autorizado al cliente receptor. Si el servicio o la identidad difieren, detener el relevo y comunicar el resultado observado.
5. Si el usuario habla de «compartir el proyecto X», distinguir proyectos internos de servicios: MCP puede exponer todos los proyectos que autorice el servidor. Una regla textual dentro del prompt NO aísla técnicamente proyectos; describir ese límite y solicitar un servidor/permiso segregado si necesita aislamiento efectivo.

## Prompt definitivo para Codex

Sustituir `<NOMBRE>`, `<ALIAS>`, `<ENDPOINT_MCP>`, `<RECURSO_OAUTH>` y `<IDENTIDAD_ESPERADA>` solamente por valores comprobados del servicio elegido. Si el recurso OAuth no está verificado, omitir `--oauth-resource` y dejar que el cliente descubra metadatos oficiales. Enviar el siguiente texto como prompt copiable (no ejecutar desde ChatGPT):

> Quiero conectar esta sesión de Codex exclusivamente con la memoria `<NOMBRE>`, mediante el servidor MCP `<ENDPOINT_MCP>`. La identidad esperada es `<IDENTIDAD_ESPERADA>`. No conectes ninguna otra memoria ni transfieras registros desde otro almacén. Inspecciona tu versión real (`codex mcp --help`, `codex mcp add --help`, `codex mcp login --help`) y los servidores ya configurados sin mostrar credenciales. Si ya existe el alias `<ALIAS>`, compara su destino; **no lo sobrescribas** si es diferente: detente y pide elección de alias. Si el cliente admite los flags necesarios, propone y ejecuta la conexión usando `codex mcp add <ALIAS> --url <ENDPOINT_MCP>` y añade `--oauth-resource <RECURSO_OAUTH>` solamente cuando tu CLI lo soporte. Obtén aprobación del usuario antes de cualquier configuración que amplíe acceso o modifique un servidor existente. Completa OAuth por el navegador autorizado y, si hace falta, `codex mcp login <ALIAS>`; nunca pidas que se copien tokens, cookies o URLs de callback al chat. Comprueba `codex mcp list`, descubrimiento de herramientas y realiza una lectura de prueba inocua (`get_memory_identity` si existe; `list_projects` si existe). Exige que la identidad observada coincida con el destino seleccionado. No llames a `save_memory`, `create_project` ni a herramientas de escritura, archivo o borrado sin una orden posterior explícita; establece el uso inicial como lectura. Ten presente que esta prohibición textual no sustituye permisos de servidor. Devuelve PASS/FAIL/NOT_RUN de configuración, autenticación, identidad y lectura, con evidencia sin secretos. Ante incompatibilidad OAuth, detente sin desactivar la autenticación ni falsificar cabeceras.

Cuando el cliente acepte otra sintaxis, adaptar los comandos tras leer su ayuda; no prometer que los flags de una versión están disponibles en todas las versiones. Poner la URL del destino **una sola vez en la orden de conexión** y no incluir resúmenes de recuerdos ni IDs de proyectos innecesarios.

## Validación al entregar

- La salida indica nombre, sitio y ámbito de la memoria elegida; si existen varias, registra elección expresa del usuario.
- La URL MCP es específica del servicio, no la URL raíz del website ni una conjetura; no mezclar URL e identidad de distintos almacenes.
- Un prompt no equivale a conexión Codex; marcar `NOT_RUN` hasta que el usuario o Codex ejecute y demuestre la prueba.
- Si hay rechazo OAuth o discrepancia de identidad, `NO_GO`; no pedir credenciales en el chat ni desactivar gates.
- La conexión no autoriza cambios en recuerdos ni transferencia entre memorias. Conservar audiencia y datos intactos.
