# Capacidades reales antes de empezar o declarar un bloqueo

Aplicar al inicio de un encargo que dependa de herramientas, tras un cambio de superficie o conexión y cuando aparezca evidencia de un catálogo desactualizado. Reutilizar comprobaciones vigentes dentro del mismo alcance; no hacer un inventario completo por cada turno. La elección explícita «sin memoria» impide consultar ALIFE incluso para esta comprobación.

## Descubrir y comprobar

1. Identificar el resultado solicitado, proyecto, superficie y operación siguiente. Separar habilidad, herramienta visible, permiso efectivo y ejecución comprobada.
2. Consultar el catálogo documentado del anfitrión, incluidas herramientas diferidas y dependencias cuando exista esa capacidad. Buscar por función y servicio, sin enumerar ni exponer datos personales ajenos al encargo. En un cliente local, comprobar la instalación y versión reales antes de dar comandos dependientes de ellas.
3. Leer el esquema de la herramienta concreta. No inventar nombres, parámetros, prefijos MCP ni modos del CLI. Una herramienta mencionada por el paquete puede no estar cargada en esta conversación.
4. Comprobar la identidad del recurso y el alcance autorizado con la operación de lectura adecuada. Distinguir la cuenta de ALIFE, la memoria seleccionada y Vault. No usar la identidad del gestor como evidencia de acceso al contenido.
5. Si falta una capacidad, localizar su conexión existente antes de pedir otra instalación. Si hay un error de autenticación, usar la reconexión oficial con los identificadores que devuelve el anfitrión. No interpretar `Authentication required` como ausencia de herramientas, ni reconstruir un `link_id` o token.
6. Después del consentimiento, volver a consultar la identidad. Si falta la nueva herramienta en una sesión antigua, comprobar catálogo y versión; una actualización de paquete no actualiza retroactivamente todas las sesiones.

## Familias de operaciones

| Intención | Evidencia mínima necesaria |
| --- | --- |
| Consultar recuerdos | `get_memory_identity`, lectura efectiva y consulta del proyecto elegido |
| Guardar o corregir | Herramienta real de escritura, autorización del cambio, versión vigente cuando corresponda y relectura |
| Usar archivos | `get_vault_identity`, mismo espacio, almacenamiento y permiso de la operación; comprobar sus bytes cuando se afirme transferencia |
| Crear una memoria | Operación real del gestor o portal oficial; `create_project` no crea una memoria |
| Seleccionar otro espacio | Selección del titular y nueva comprobación del grant de contenido; una preferencia del gestor no redirige el token actual |
| Relacionar entidades | Contrato real y revisiones de extremos, contexto y evidencia; no confundir similitud con aceptación o causalidad |
| Guardia o ejecución local | Receptor, canal, permisos y estado de STOP comprobados; la conexión de memoria no los activa |

El servidor de contenido de Platform es `/mcp`. El gestor de cuentas es `/mcp/gestor`; sus tokens y audiencias son distintos. No reenviar tokens entre ambos ni añadir scopes de gestor al recurso de contenido para intentar salvar una limitación del anfitrión.

## Resolver el resultado

Usar una descripción precisa: herramienta no expuesta, conexión sin autenticar, permiso insuficiente, almacenamiento no disponible, revisión en conflicto o transferencia sin probar. Detener únicamente el efecto afectado, conservar el objetivo y avanzar en trabajo independiente autorizado. Reintentar cuando exista una condición nueva; no repetir errores idénticos ni cambiar de canal para eludir un rechazo. Al desaparecer la causa, revalidar y recuperar la acción correcta sin ampliar su autorización.

Estas instrucciones guían al agente. No cargan por sí solas herramientas, no instalan software y no constituyen una barrera de permisos del anfitrión.
