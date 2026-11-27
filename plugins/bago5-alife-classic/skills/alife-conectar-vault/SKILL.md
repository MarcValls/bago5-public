---
name: alife-conectar-vault
description: Comprueba y vincula la conexión de archivos de ALIFE con la memoria seleccionada en BAGO5 ALIFE Classic antes de usar Vault.
---

# Conectar el Vault nativo

Este complemento funciona por sí mismo y también está integrado en BAGO5 ALIFE Classic. Esta entrada comprueba la conexión. El procedimiento de transferencia está incluido en [ALIFE Vault](../bago5-alife-vault/SKILL.md). Antes de transferir, verifica el espacio, el proyecto y el permiso de archivo. Si el cliente carece de la operación, conserva el archivo en origen.

1. Descubre las operaciones reales en este host. Identifica la app ALIFE Memoria Viva nativa y el recurso `https://alifememories.com/mcp`. Usa la autorización del host para ese recurso. Respeta STOP y revocación. Utiliza una sola conexión para cada transferencia. Si hay otra conexión de ALIFE, verifica por separado el sujeto y el espacio. Nunca reutilices tokens entre clientes.
2. Llama a `get_memory_identity` y compara el espacio con la memoria elegida por la persona. Llama a `get_vault_identity` en la conexión que va a operar. Exige las dos identidades autorizadas, el mismo `memory_id` y `authenticated_subject`, contrato nativo compatible (`alife-vault-mcp/1.0.0` en la implementación v41), `schema_ready` y `storage_available` verdaderos. Ante datos ausentes, ambiguos o incompatibles, identifica el dato pendiente y detén los efectos.
3. Informa por separado sobre lectura y escritura. Para listar y descargar se necesitan permiso Vault de lectura y las operaciones `list_vault_artifacts`, `get_vault_artifact` y `read_vault_chunk`. Para subir con verificación se necesitan lectura y escritura, `begin_vault_upload`, `put_vault_chunk`, `complete_vault_upload` y relectura. Comprueba también si se puede cancelar con `abort_vault_upload`. Describe las operaciones que falten. Una autorización de recuerdos no acredita acceso a archivos. Si faltan permisos, usa el consentimiento del anfitrión para los permisos de archivo solicitados por la persona. Si faltan herramientas, contrasta el catálogo del MCP nativo y la versión del servidor antes de pedir una reconexión.
4. Con un encargo de transferencia, valida el proyecto elegido con `list_projects` en el espacio confirmado y aplica `$bago5-alife-vault`. Mantén la misma identidad y conexión durante toda la operación. Sigue los límites anunciados por el Vault, la revisión esperada y el identificador de reintento. Para afirmar entrega de extremo a extremo, recupera la revisión exacta y compara los bytes, longitud y SHA-256 con el original. Si la petición solo comprueba el estado, termina antes de cualquier carga.
5. Devuelve qué identidad y permisos has comprobado, qué operaciones expone este host y qué prueba se ejecutó. Si un cliente aún no ha leído los bytes, su recepción queda NOT_RUN. Conserva los archivos en origen si el destino está bloqueado.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.

## Distinguir catálogo, autorización y entrega

Descubre las operaciones por su nombre y esquema en todo el catálogo vigente del host, incluida la conexión MCP de ALIFE Vault además de la App nativa. Los prefijos pueden variar. La ausencia de operaciones Vault en una App no demuestra que falten en otra conexión del mismo servicio. Conserva la procedencia de cada operación y utiliza una sola conexión autenticada para cada transferencia.

Informa de cuatro comprobaciones separadas: herramientas expuestas, identidad y permisos autorizados, esquema y almacenamiento disponibles, y bytes transferidos y recuperados. Si una operación expuesta devuelve `Authentication required` o 401, registra herramientas presentes y autenticación pendiente; no lo conviertas en «el catálogo no expone Vault». Si faltan scopes, identifica los permisos concretos. Si falla el almacenamiento o el contrato, conserva esa causa distinta. Un manifiesto o una versión nueva del complemento no prueba ninguna de estas comprobaciones en ejecución.

Ante autenticación pendiente, usa el flujo oficial del anfitrión y las acciones de conexión disponibles. Solicita `memory.read`, `vault.read` y, solo para una carga autorizada, `vault.write`. La autorización de recuerdos de otra conexión no los sustituye. Para una acción de reconexión que exija identificadores del error, usa únicamente los recibidos; no inventes IDs ni traslades credenciales entre clientes. Si el host bloquea la conexión, conserva el motivo y prepara el resto del trabajo autorizado antes de pedir la intervención concreta. No repitas llamadas idénticas sin un cambio observado.

Solo después del consentimiento relee `get_memory_identity` y `get_vault_identity` en la conexión operadora, comprueba el proyecto y continúa la transferencia ya autorizada. Confirma entrega únicamente tras recuperar la revisión exacta, reconstruir los bytes y comparar longitud y SHA-256. La recepción en otro host sigue `NOT_RUN` hasta comprobarla allí.

