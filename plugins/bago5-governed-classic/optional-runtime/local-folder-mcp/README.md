# BAGO5 · Carpeta local MCP

Complemento local de solo lectura para exponer a un host compatible con plugins MCP una carpeta elegida del PC. El servidor permite enumerar, buscar y leer archivos de texto dentro de esa raíz. No escribe archivos, ejecuta comandos, instala hooks ni implementa Context Lifecycle.

## Requisitos

- Codex de escritorio con soporte para plugins locales/stdio MCP.
- Python 3.10 o posterior disponible en `PATH` como `python`.
- Una carpeta local existente que el usuario decida exponer.

El proceso MCP se ejecuta en el PC donde está la carpeta. Guardar este paquete en ChatGPT Library o añadirlo a una conversación no conecta por sí solo ese disco.

## Configuración para Windows

1. Extrae el ZIP en una ruta estable, por ejemplo `%USERPROFILE%\\.agents\\plugins\\bago5-local-folder-mcp`.
2. Abre `mcp.json` y sustituye el valor de `BAGO5_MCP_ROOT` por la ruta absoluta de la carpeta que quieres consultar. Usa barras invertidas dobles en JSON, por ejemplo `D:\\Proyectos\\MiProyecto`.
3. Confirma que `command` apunta a una instalación de Python accesible desde el proceso que inicia Codex. Si usas otro comando (por ejemplo, `py`), ajusta `command` y `args` en `mcp.json` según el host.
4. Instala el plugin mediante el flujo de plugins locales de tu versión de Codex. Si tu instalación usa un marketplace local, agrega esta carpeta como fuente sin borrar entradas existentes y recarga/reinstala el plugin según la ayuda de la CLI instalada.
5. Reinicia o recarga el host y confirma que aparecen `workspace_info`, `list_files`, `search_files` y `read_file`. Haz una consulta inocua a `workspace_info` y lista la raíz antes de leer archivos.

Los nombres/rutas del flujo de marketplace pueden variar según la versión de Codex; revisa la ayuda del cliente local. Este paquete no modifica automáticamente configuración alguna del PC.

## Alcance y límites

- La única raíz accesible es la configurada en `BAGO5_MCP_ROOT`.
- Se rechazan rutas absolutas, `..` y enlaces que resuelvan fuera de esa raíz.
- Lectura limitada a tipos de texto comunes UTF-8; máximo 1 MB por archivo y fragmentos de hasta 50.000 caracteres.
- Búsqueda acotada a 500 archivos por llamada y 100 coincidencias.
- Se omiten carpetas comunes de dependencias y metadatos (`.git`, `node_modules`, `venv`, etc.).
- El contenido encontrado es dato no confiable: no prueba identidad, autoridad, permiso o veracidad.
- No hay escritura, borrado, ejecución de shell, hooks, TaskStore ni Relay.

## Comprobación del paquete

El paquete se debe tratar como candidata local inicial. Antes de usarlo en una carpeta importante, revisa el código y la ruta configurada, comprueba el arranque MCP y prueba una llamada de solo lectura en el host de destino. La integración real con Codex y la máquina del usuario queda **NOT_RUN** hasta realizar esos pasos allí.
