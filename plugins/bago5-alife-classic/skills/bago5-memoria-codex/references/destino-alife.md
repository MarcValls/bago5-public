# Conexión de ALIFE Memoria Viva nativa

| Aplicación | Servicio MCP y recurso OAuth | Plugin privado |
| --- | --- | --- |
| ALIFE Memoria Viva nativa | https://alifememories.com/mcp | `plugin_asdk_app_6b0339c22c3481919cce222512431e0e` |

Al utilizar el plugin de ChatGPT o Codex, selecciona la aplicación `asdk_app_6b0339c22c3481919cce222512431e0e`. Consulta `get_memory_identity` y compara el campo `memory_id` con el espacio elegido por el usuario. Comprueba `contracts.memory_api`, los permisos efectivos y el proyecto devuelto por la app. Para el alias local se sugiere `alife-memoria-nativa`. Cada cliente acredita su propio acceso mediante OAuth.
