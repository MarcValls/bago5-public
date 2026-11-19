---
name: bago5-memory-federation
description: "Seleccionar memorias independientes, comprobar concesiones y trasladar datos mediante exportaciones verificables."
---

# Federar memorias

Consulta los formatos de [conexión](schemas/connection.schema.json), [invitación](schemas/invitation.schema.json) y [manifiesto de exportación](schemas/pack-manifest.schema.json). Valida los metadatos antes del intercambio y comprueba las concesiones en el proveedor.

Enumera únicamente las conexiones autorizadas. Para cada una registra alias local, identidad devuelta, tipo de transporte y permisos efectivos. Comprueba la identidad y el recurso tras una reconexión. Mantén separadas las concesiones de cada usuario, cliente, proyecto y memoria.

Para una invitación, fija destinatario, objeto, alcance, lectura o escritura, vencimiento y modo de revocación. El destinatario debe aceptar por su canal autenticado. Verifica lectura permitida y denegación fuera de alcance con datos sintéticos autorizados. Al revocar, comprueba el cliente afectado y otro independiente.

Para una transferencia, fija origen, revisiones y destino antes de exportar. Incluye manifiesto de tipos, cantidades, hashes y versión de contrato. Comprueba integridad antes de importar; detecta duplicados y conflictos de revisión. Realiza un ensayo y conserva el mapa de identificadores. Relee en destino una muestra acordada y las relaciones críticas. Un ZIP exportado no acredita una importación.

Entrega estado de cada conexión, consentimiento y verificaciones por destino. Los datos de autenticación permanecen bajo control del host.
