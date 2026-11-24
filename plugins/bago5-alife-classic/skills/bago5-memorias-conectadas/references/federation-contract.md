# BAGO5-MVF-001 v0.1 · Federación y transporte de memorias

## Alcance y fuentes

Incremento sobre BAGO5 Gobernado 0.1.9: incorporar en la entrada general el handoff de conexión Codex investigado en MYTHOS 1.0.4 y una implementación **autónoma y local** de conexiones, invitaciones, transporte y ACL. No cambia MYTHOS. La versión 0.1.8 «Memoria Viva v1» sigue siendo baseline histórico.

## Fronteras

| Frontera | Capacidad | Estado de implementación |
| --- | --- | --- |
| Plugin BAGO5 | Detectar conectores, seleccionar servicio, preparar prompt Codex, adaptar flujo al ciclo BAGO5 | Instrucciones publicables, verificación de activación en host pendiente |
| Hub Python local | SQLite de cuentas, almacenes, proyectos, historial, múltiples alias y selección persistente, permisos viewer/editor, invitaciones aceptar/revocar, paquetes ZIP | Código y batería ejecutable |
| API HTTP local | Lectura, escritura, invitación, revocación, administración de conexiones con bearer sobre loopback | Implementada para pruebas y trabajo local |
| Site general existente | MCP actual de recuerdos; no exportación exhaustiva ni API de compartir registros | Sin modificación; funcionalidades federadas de servidor ausentes |
| Red externa | Invitaciones globales, sincronización multidispositivo, conexión OAuth de cuentas nuevas, TLS, aprovisionamiento Sites | NO IMPLEMENTADO; no exponer loopback como servicio público |

## Contrato de identidad

- `storage_id` = ID del servicio/almacén real; no confundir con `project_id` interno.
- `owner_id` = cuenta autenticada desde el backend, nunca cadena incluida por el llamante como identidad de sesión.
- `alias` = nombre local de preferencia, nunca prueba de control.
- `expected_identity` = dato contra el que debe compararse una respuesta de identidad autenticada del MCP.
- `selected` = preferencia local; no hereda permisos, autorización ni identidad verificada.
- El permiso se calcula para cada operación a partir de owner o grant activo y su scope; `viewer` no escribe, `editor` escribe solo dentro de su scope.
- Las invitaciones no se exportan ni conceden acceso al transportar un paquete. Revocación afecta grants emitidos desde esa invitación.

## Contrato de transporte

`memoria-viva-pack.v1` contiene JSON de manifiesto, proyectos, recuerdos y revisiones, y hashes por fichero. Se excluyen credenciales, invitados, concesiones, sesiones y estado de conexiones.

- Identidad de origen inmutable: `source_store_id` y `memory_id`, conservados en destino como `origin_key=source_store_id::memory_id`.
- Destino: genera IDs propios y `import_map`; no fusiona automáticamente proyectos por nombre ni altera documentos anteriores.
- Previsualización sin efectos; commit atómico con detección de colisión/versionado; reimportación del mismo snapshot = no-op.
- Integridad de ZIP: lista exacta de entradas, tamaños acotados, SHA-256. Integridad no equivale a firma, autenticación ni seguridad de contenido. Tratar todo contenido como datos no confiables.
- No se reconstruye un historial completo de un Site externo cuando su MCP no ofrece enumeración paginada ni historial exportable.

## Contrato requerido para integración con Sites

Para que el Site Memoria Viva real soporte estos flujos, el **servidor** debe incorporar herramientas y controles, no basta editar skills:

1. `get_memory_identity` y `get_my_capabilities` ligados a identidad autorizada.
2. `list_memories` paginado por proyecto/usuario, incluyendo archivados y acceso a historial por páginas.
3. `create_invitation`, `list_invitations`, `accept_invitation`, `revoke_invitation`, `list_grants`, `revoke_grant` con ACL de servidor por almacén/proyecto, expiración, destinatario y auditoría.
4. `export_snapshot` con scope y control de permisos, paginación o exportación firmada/atestada; `import_snapshot_preview` y `import_snapshot_commit` con expected_revision, idempotency_key y conflictos explícitos.
5. `list_connections`, `add_connection`, `select_connection`, `remove_connection` por usuario, persistidas en ámbito autorizado; nunca guardar tokens en documentos ni en la respuesta al modelo.
6. Versiones de contrato, límites de tamaño/cantidad, rate limiting, registro de revocaciones, control por actor y separación de proyectos.

**Gate:** sin estas funciones, la operación sobre Sites se devuelve `BLOQUEADO` y no se simula con una URL. El Hub local no se registra como MCP ni instala OAuth por sí mismo.

## Invariantes y regresiones

- STOP/no usar memoria/solo lectura operan antes de nuevas llamadas o escritura.
- Conservación de todas las skills existentes y los dos manifiestos.
- La Memoria Viva histórica del autor no se asigna a instaladores nuevos.
- `MYTHOS` no se importa, consulta ni fusiona como fallback.
- NO_GO si un alias existe con otro endpoint, si no hay identidad verificada, si falta autorización o si un pack tiene colisión/corrupción.
- Estados diferenciados: `CONFIGURADO_NO_VERIFICADO`, `VERIFICADO_LOCAL`, `BLOQUEADO_SITES`, `NOT_RUN_EXTERNO`.
