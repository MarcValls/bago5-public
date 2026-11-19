---
name: bago5-math
description: "Formalizar una consulta y emplear verificadores matemáticos autorizados con condiciones de validez explícitas."
---

# Consultar un servicio matemático

El [esquema de solicitud](schemas/service-request.schema.json) permite comprobar qué campos y operaciones acepta el formato del cliente. Verifica la compatibilidad con la versión anunciada por el servicio.

Conserva la petición original, las restricciones, el dominio y las cantidades. Identifica ambigüedades de agente, negación, tiempo o referencia. Si el servicio ofrece perfiles LSI, aplica las perspectivas al mismo texto y conserva las interpretaciones en conflicto.

Elige dominio, sistema, representación y expresión (MAT). Explica en lenguaje natural qué afirma tu modelo y compruébalo contra las restricciones originales. Marca como provisional una abstracción VAC pendiente de contraste.

Descubre las herramientas del proveedor en el host y comprueba identidad, capacidad, vínculo con la memoria cuando sea necesario, cuotas y consentimiento para enviar los datos mínimos. La decisión de acceso pertenece al servicio. Envía el modelo y conserva identificador y respuesta de la ejecución. Si falta acceso, informa de formalización preparada y cálculo pendiente.

Entrega hipótesis, modelo, resultado y alcance de la prueba. Un contraejemplo sobre una traza o un resultado SAT en un dominio finito se interpreta únicamente dentro de ese modelo.
