---
name: bago5-memoria-viva
description: Leer o guardar recuerdos en el espacio nativo seleccionado.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).
Aplica la [continuidad operativa](../bago5/references/operational-continuity.md) antes de pedir reconexión, declarar pérdida de acceso o cambiar de canal. Recupera la misión, memoria y proyecto ya seleccionados, la última comprobación vigente y cualquier intervención pendiente.

# Operar la Memoria Viva de ALIFE

Usa la conexión autenticada de https://alifememories.com/mcp. Consulta get_memory_identity y coteja el identificador de espacio, el proyecto y los permisos efectivos. Antes de guiar una reconexión, comprueba las herramientas realmente expuestas y la identidad del espacio con el canal disponible. Distingue:
- autenticación ausente, caducada o revocada;
- permiso insuficiente para la operación concreta;
- herramienta o capacidad no expuesta en este anfitrión;
- fallo de una llamada con conexión aún vigente;
- proyecto o memoria seleccionados que no coinciden.

No conviertas un fallo de llamada o una herramienta ausente en pérdida de autenticación. No pidas reconectar si la identidad y el permiso vigentes ya cubren la operación. Si hace falta una nueva autorización, identifica el permiso y la acción exactos y guía al usuario por el flujo oficial; nunca solicites tokens, cookies, cabeceras ni callbacks en el chat. Un usuario nuevo elige o crea su espacio en https://alifememories.com/memoria-viva.

Para una consulta usa las operaciones disponibles de búsqueda y lectura. Verifica el ID antes de mostrar un registro. Para guardar, contrasta cuenta, espacio, autorización actual y permiso de escritura. Lee primero el registro actual si existe, preserva las modificaciones ajenas y usa la versión esperada que admita el contrato anunciado. Ante conflicto, relee y reconcilia antes de reintentar. Relee la versión guardada, compara los campos solicitados y devuelve ID, versión y enlace cuando esté disponible. Si solo hay lectura, entrega el borrador. Las tarjetas las gestiona [Plan por fases](../bago5-plan-por-fases/SKILL.md) y los archivos los gestiona [Vault](../bago5-alife-vault/SKILL.md).

Si una capacidad no está disponible, conserva la tarea y el contexto; declara `NOT_RUN` para esa operación y continúa las comprobaciones independientes autorizadas. Solicita únicamente la intervención imprescindible y comprueba su resultado antes de retomar.
