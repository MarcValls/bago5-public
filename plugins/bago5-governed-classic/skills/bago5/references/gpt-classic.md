# Compatibilidad con GPT Classic

GPT Classic es la plataforma principal de esta candidata. Antes de cada operación comprobar herramientas y fuentes realmente expuestas en la conversación.

- El análisis, la planificación, los contratos, la revisión y la preparación de entregas pueden realizarse con el contenido aportado y las herramientas disponibles.
- La memoria persistente necesita un conector autenticado y un almacén identificado. Preservar la separación entre proyectos y almacenes; una copia de instrucciones no conecta un servicio.
- Leer archivos locales requiere una conexión que exponga esa carpeta. BAGO5-LOCAL-FILES aplica la skill incluida bago5-lectura-carpeta. Sin conector, trabajar con adjuntos y declarar el acceso local NOT_RUN.
- Python, shell, Git, pytest, TaskStore, Relay y hooks solo se ejecutan si una herramienta real permite la operación. Empaquetar un script no lo convierte en herramienta de GPT Classic. Identificar entorno y límites antes de ejecutar.
- Los comandos nativos de Codex, incluidos /goal y /models, son extensiones opcionales del host. En GPT Classic usar seguimiento conversacional con evidencia y controles realmente disponibles; no simular procesos persistentes ni cambios de modelo.
- Los enlaces y alias de skills guían al agente; no registran herramientas MCP ni prueban carga en el host.

## Aceptación
La validación requiere observar en GPT Classic la carga del complemento, selección de rutas, recuperación de memoria autorizada, aislamiento entre proyectos y almacenes y comportamiento con y sin conectores. Las pruebas locales solo acreditan su alcance local. Hasta obtener esas observaciones: aceptación GPT Classic NOT_RUN.
