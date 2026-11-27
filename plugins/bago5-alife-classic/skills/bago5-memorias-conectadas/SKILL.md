---
name: bago5-memorias-conectadas
description: "Gestiona la selección, conexión e intercambio entre memorias, verificando identidad, permisos y compatibilidad."
---

Aplicar una sola vez por misión el ciclo vigente de [bago5-ganchos-sesion](../bago5-ganchos-sesion/SKILL.md) y su [contrato de continuidad](../bago5-ganchos-sesion/references/lifecycle.md); en las derivaciones, reutilizar el binding y estado actuales de proyecto, sesión y memoria. Revisar después únicamente los controles pertinentes al evento y a la tarea, sin reinicializar el ciclo ni recorrer dependencias recursivas. Este enlace no activa todos los especialistas ni autoriza efectos, archivos, persistencia o instalación de hooks; cada operación conserva sus requisitos de alcance, herramientas y autorización vigentes.

Antes de fijar o preparar una versión, runtime o configuración para un destino, o ejecutar una acción que dependa de ellos, aplicar la [comprobación previa del destino](../bago5/references/target-preflight.md); si falta evidencia actual, bloquear solo el trabajo dependiente y continuar lo independiente.

# $memorias · gestor federado de Memoria Viva (BAGO5 general)

## Entrada y autoridad

Esta capacidad es **general**, no está restringida a el proyecto elegido. Conserva el ciclo [BAGO5](../bago5/references/memory-cycle.md) y su [onboarding](../bago5/references/onboarding.md). **No usar el Site del autor ni el proyecto elegido como memoria personal de otro usuario**. Un endpoint conocido, una URL compartida o un registro local no conceden acceso. STOP y «no uses memoria» prevalecen.

Distingue los siguientes planos:

1. **Conectores MCP del host**: lectura/escritura real únicamente cuando el host exponga herramientas, identidad verificada y permisos efectivos.
2. **Gestor local opcional**: `scripts/mv_hub.py` ofrece implementación reproducible de registro SQLite persistente, roles, invitaciones y paquetes. No es el Site, no se inicia automáticamente al instalar el plugin, ni conecta las herramientas de ChatGPT Classic. Funciona sin dependencias de terceros en Python 3.10+; requiere host Windows/Codex con acceso a Python y ejecución autorizada.
3. **Servicios remotos opcionales**: el destino principal es ALIFE PHP. Descubrir operaciones y esquemas en cada servicio; las invitaciones, exportación completa o federación requieren endpoints efectivos y permisos. Si faltan, bloquear solo esas operaciones. Sites conserva únicamente compatibilidad expresamente elegida; BAGO5 no depende de él ni lo usa como fallback.

## Operación interactiva de ALIFE

Usa [workspace-evidence.md](../bago5/references/workspace-evidence.md) para distinguir selección de consulta, origen de edición y destino de creación. Puedes agregar resultados de memorias independientemente autorizadas conservando su procedencia; no los fusiones ni copies por coincidencias. Si el conector actual cubre una sola memoria, declara ese alcance aunque la web permita seleccionar varias. Una elección explícita ya vigente satisface la elección requerida: no vuelvas a pedirla sin un cambio material.

Los flujos de compatibilidad siguientes son opcionales y solo corresponden a un encargo explícito sobre ese origen. No forman parte del alta ordinaria de nuevos usuarios, no se ofrecen como recuperación de versiones de desarrollo y no sustituyen el servicio ALIFE actual.

## Resolver una memoria

- Descubrir los conectores disponibles en la sesión. Buscar identidad efectiva del servicio y los permisos, no inferirla del nombre; separar almacén remoto de proyecto interno del almacén.
- Mostrar nombre, servicio/endpoint cuando proceda, ámbito, propietario comprobado o desconocido, permisos, estado y última evidencia. Una URL histórica o el registro SQLite de alias solo representan *candidatos*.
- Si solo hay un destino **verificado y autorizado**, puede usarse para la petición delimitada. Si hay varios destinos capaces de servirla, exigir elección explícita antes de compartir, exportar, importar, escribir o preparar un handoff definitivo hacia Codex. El `selected` del registro de conexiones es preferencia, no autorización persistente ni selección tácita ante ambigüedad de escritura.
- No mezclar resultados ni arrastrar automáticamente recuerdos. En búsquedas multialmacén, conservar procedencia y acceso independiente, etiquetando cada respuesta.

## `$memoria-codex` · habilidad independiente

Para esta petición, aplicar [bago5-memoria-codex](../bago5-memoria-codex/SKILL.md), invocable directamente como `$bago5-memoria-codex`. Esta federación conserva el registro y las operaciones múltiples; el especialista prepara la selección y el prompt sin duplicar el ciclo de memoria.

Determinar primero el host de esta sesión y el host donde debe ocurrir la operación. En GPT, si el destino es Codex, aplicar `bago5-memoria-codex` y preparar un prompt para Codex. En Codex, si la conexión es para esta misma sesión, continuar aquí con herramientas/CLI disponibles; no entregar un prompt de Codex a Codex. Si el usuario pide el camino inverso, Codex→GPT, preparar un prompt dirigido a GPT mediante `bago5-relevo-agentes`. El prompt es user-mediated, no ejecuta la conexión y no concede permisos.

Preparar la conexión solo para **un almacén seleccionado**. No compartir datos ni incluir credenciales. Si hay varias memorias verificadas y todavía no existe un destino inequívoco vigente, mostrar las candidatas y pedir esa elección antes de preparar un prompt o cambiar una conexión. Reutilizar una elección explícita previa cuando siga siendo válida; derivar a otro especialista no la invalida.

Solo al preparar un relevo GPT→Codex, el prompt debe indicar nombre y endpoint MCP exactos, identidad esperada del servicio y alias no conflictivo. Instruir a Codex a inspeccionar `codex mcp --help`, `codex mcp add --help`, `codex mcp login --help` y servidores existentes. Verificar el alias antes de modificarlo; no sobrescribir destinos diferentes. Ejecutar `codex mcp add <ALIAS> --url <ENDPOINT>` y, **solo si existe soporte y recurso OAuth comprobado**, `--oauth-resource <URL_RECURSO>`; tras consentimiento del usuario, completar OAuth desde el cliente autorizado. Verificar `codex mcp list`, herramientas expuestas, identidad y lectura `get_memory_identity`/`list_projects`. Empezar sin escrituras. Declarar estado `NOT_RUN` hasta que Codex demuestre conexión; el prompt no acredita acceso. No prometer aislamiento de un proyecto cuando MCP concede acceso más amplio.

## Conexiones múltiples persistentes

Cuando exista el **gestor local realmente ejecutable**, puede registrar varios servicios por actor con `alias`, `endpoint MCP`, `expected_identity` y selección de preferencia. `connection_add` valida URLs HTTPS sin credenciales ni query; no contacta al servicio: estado `UNVERIFIED`. `connection_select` persiste la preferencia, **nunca eleva el estado a verificado**. La persistencia es SQLite local, no una configuración sincronizada de ChatGPT, OAuth, Codex ni un hook de inicio. En ChatGPT sin gestor local expuesto, solo descubrir herramientas ya instaladas y no declarar persistencia.

## Invitar y compartir

- Separar **invitación** de **permiso ya otorgado**. El propietario elige almacén/proyecto, destinatario, rol (`viewer`/`editor`) y caducidad. La aceptación requiere identidad autenticada del destinatario y secreto aleatorio de invitación. El servidor es quien impone ACL; revocar la invitación revoca también el permiso procedente de ella.
- La implementación local comprueba esto en su backend SQLite y HTTP de bucle local con bearer tokens. Los secretos se generan una sola vez y se almacenan solamente como SHA-256; no ponerlos en memoria, logs, prompts, paquetes ni enlaces públicos. El servicio local está limitado a `127.0.0.1`/`::1` y **no debe publicarse directamente en Internet**. Desplegarlo en red requeriría revisión de seguridad, autenticación y TLS del operador, fuera de este incremento.
- Para un Site de otra persona, un enlace solo identifica una ubicación. Sin API del servidor para invitación, concesión y revocación, devolver `BLOQUEADO/NO_GO` y no sustituirlo con instrucciones que simulen permisos. Nunca compartir el Site propio completo si solo se ha solicitado un proyecto.

## Exportar / importar paquete

- La implementación local permite exportar un almacén propio o **solo** el proyecto compartido que el usuario pueda leer. Produce ZIP independiente con `manifest.json`, `projects.json`, `memories.json`, `revisions.json`, `SHA256SUMS.txt`, `LEEME.md`. Conserva contenido, estados, fuente, etiquetas, cierre, archivo, fijado, versiones e identidad de procedencia. No exporta tokens ni ACL.
- Verificar estructura cerrada, límites de tamaño, SHA, continuidad de revisiones y consistencia de snapshot. SHA demuestra integridad accidental, **no** autenticidad del emisor. Exigir revisión explícita del contenido importado si la fuente no es confiable.
- Importar realiza **vista previa sin escribir** por defecto; `--commit` escribe atómicamente sobre otro almacén del que el actor sea propietario. Conserva `origin_key` y mapea proyectos. Reimportar sin cambios es idempotente; conflictos de contenido no se sobrescriben (`IMPORT_CONFLICT`), sin corregir automáticamente decisiones ni canon.
- No confundir un paquete local con una exportación completa de un Site remoto: las herramientas MCP actuales no permiten enumerar todos sus registros. Si la fuente es solo `search_memories`, la cobertura completa es `NO_COMPROBADO` y no se produce exportación supuestamente integral.

## Procedimiento de ejecución y comprobación

Leer [contrato de servicio](references/federation-contract.md), [uso local](references/quickstart.md) y estados y cobertura cuando corresponda. En un host con Python disponible y autorización para usar el gestor, ejecutar el flujo real; sin esas capacidades, preparar solo conexión/handoff gobernado y marcar operaciones reales `NOT_RUN` o `BLOQUEADO`.

Pruebas independientes del nuevo código: `python -m unittest discover -s skills/bago5-memorias-conectadas/tests -v`. El éxito de las pruebas en entorno local no acredita acceso a Sites externos, ejecución del nuevo comportamiento desde ChatGPT ni seguridad de un despliegue a Internet.

**Nunca** modificar memoria el proyecto elegido, su plugin, sus Site permissions ni las versiones conservadas por introducir esta capacidad general. En el cierre presentar trabajo, evidencia positiva y negativa, límites y NOTA FINAL.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.

