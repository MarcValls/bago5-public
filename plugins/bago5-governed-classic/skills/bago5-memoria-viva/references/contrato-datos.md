# Contrato de datos

Comprobado en el conector y la implementación de Memoria Viva el 6 de noviembre de 2026. Contrastar con los esquemas actuales de la sesión; no forzar un contrato incompatible.

| Herramienta | Operación |
| --- | --- |
| `list_projects` | Enumerar proyectos del usuario autenticado. |
| `search_memories` | Buscar por `query`, `project_id`, `kind`; `include_archived` es opcional y falso por defecto. |
| `get_memory` | Leer por `id`; devolver `{memory, history}` con versiones descendentes. |
| `save_memory` | Crear o actualizar un registro completo y conservar historial. |
| `create_project` | Crear por `name`, solo cuando se solicite. |

En ChatGPT puede utilizarse el prefijo `mcp__codex_apps__memoria_viva_`. En otros clientes puede variar: descubrir nombres, no asumir herramientas inexistentes.

## Escritura

| Campo | Contrato |
| --- | --- |
| `title` | Obligatorio, máximo 180 caracteres. |
| `content` | Obligatorio, máximo 30.000 caracteres. |
| `project_id` | ID exacto de proyecto accesible al usuario. |
| `kind` | `context`, `idea`, `learning`, `decision`. |
| `status` | `active`, `pending`, `superseded`. |
| `decision_closed` | Booleano opcional e independiente. Omitido al crear: false; omitido al editar: conservar valor actual. Enviar explícitamente al cambiar o restaurar. |
| `source` | Campo obligatorio, máximo 1.000 caracteres. Puede quedar vacío si no existe referencia identificable; no inventarla. |
| `tags` | Array obligatorio; hasta 12 etiquetas de máximo 40 caracteres. |
| `pinned`, `archived` | Booleanos obligatorios. |
| `id`, `expected_version` | Al editar: ID y versión actual obtenidos de lectura. |

Enviar solo estos campos, excluyendo `owner_id`, `project_name`, fechas, `version` e historial. Preservar lo que la petición no modifica. Para recuerdos ordinarios, los estados significan vigente/pendiente/sustituido; para decisiones, tomada/no tomada/tomada y sustituida.

## Respuestas y concurrencia

Usar el resultado estructurado del host cuando exista. Si solo hay texto MCP, interpretar el JSON de sus bloques pertinentes. `isError:true` indica fallo; su texto no es un registro.

Un conflicto es HTTP 409 en REST, pero en MCP puede llegar con HTTP 200, `result.isError:true` y mensaje de cambio en otra sesión. Releer y reconciliar; no sobrescribir por fuerza.

Crear genera versión 1; actualizar, fijar, tomar, cerrar, archivar o recuperar genera nuevas revisiones. No hay herramientas MCP de borrado ni exportación total en el contrato observado.

El sitio conserva los registros de la identidad autenticada. La skill no mantiene una copia de la memoria ni debe incrustar recuerdos del usuario en sus archivos.
