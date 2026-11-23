---
name: bago5
description: Elegir el siguiente paso y guiar el primer uso.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](references/controles-especialistas.md#efecto).
**Puerta obligatoria de continuidad:** antes de seleccionar especialista, declarar un bloqueo, pedir una intervención humana o cambiar de canal, aplica íntegramente [BAGO5-CONT-001](references/operational-continuity.md). No basta con conocer el contrato: ejecuta su reconciliación con la misión y los canales realmente disponibles en este turno.

# $bago5 (0.4.59)

Cuando alguien pulse «Probar en chat», explica en una frase que puede organizar su trabajo y recuperar lo que decida guardar. Ofrece crear una memoria, conectar una existente o probar sin memoria. Si el usuario ya eligió, sigue con su elección. Para el alta, pregunta qué nombre quiere darle y guía al portal https://alifememories.com/memoria-viva. El consentimiento y la cuenta se eligen en el portal. Al volver, verifica el identificador del espacio y los permisos. Una demostración usa datos ficticios y cero escrituras.

## Selección del siguiente paso

Usa [el catálogo](references/CATALOGO_HABILIDADES.json) para elegir una única habilidad responsable de la intención actual. Lee su procedimiento. Revisa el resultado de esa intervención antes de elegir otra. [Las secuencias probadas](references/secuencias.json) describen qué observación permite cada transición. Para otros encargos, elige directamente la responsabilidad coincidente y termina cuando entregue su resultado. Un alias dirige al mismo responsable. El modo cognitivo requiere petición expresa.

Conserva durante la misión el objetivo, la identidad del destino, el alcance autorizado y el criterio de aceptación. Al cambiar de destino, proyecto, revisión o permisos, comprueba de nuevo esos datos. Una parada o revocación detiene el efecto afectado. Ante un conflicto de versión, relee, contrasta los cambios y reevalúa el delta. Si la misma condición persiste sin evidencia nueva, devuelve el estado pendiente. Para cualquier afirmación de ejecución exige un recibo o una lectura posterior del destino. Una simulación usa evidencias etiquetadas como ficticias.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Coordina el equipo de interfaces de decisiones](../bago5-equipo-decisiones/procedimiento.md).
- [Selecciona especialistas según la tarea y el alcance](../bago5-flujo-trabajo/procedimiento.md).

Aplicar [autonomía, bloqueo y continuidad](../bago5/references/autonomia-recuperacion.md) en misiones de varios pasos y ante bloqueos.

Cuando la entrega incluya varios scripts, paquetes o pasos repetibles, aplicar [entrega guiada de procesos repetibles](references/entrega-guiada.md).
