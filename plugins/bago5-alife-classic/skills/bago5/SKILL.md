---
name: bago5
description: Elegir el siguiente paso y guiar el primer uso.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](references/controles-especialistas.md#efecto).
**Puerta obligatoria de continuidad:** antes de seleccionar especialista, declarar un bloqueo, pedir una intervención humana o cambiar de canal, aplica íntegramente [BAGO5-CONT-001](references/operational-continuity.md). No basta con conocer el contrato: ejecuta su reconciliación con la misión y los canales realmente disponibles en este turno.

# $bago5 (0.4.60-rc.5)

En el chat Classic, utiliza las aplicaciones registradas ALIFE Memoria Viva nativa y ALIFE Gestor nativo. Si la persona quiere instalar BAGO5, guíala desde [Plugins de ChatGPT](https://chatgpt.com/plugins) y la ficha BAGO5 Gobernado Classic disponible en su cuenta. Si ya está usando la habilidad, continúa en esta conversación.

Al empezar, ofrece «Crear mi primera memoria», «Conectar una que ya tengo» y «Continuar sin memoria». Da un paso y espera su respuesta. Si el servidor ofrece la tarjeta alife_empezar, puedes mostrarla. En su ausencia presenta la misma elección en texto. Para crear una memoria, usa [Memoria Viva](https://alifememories.com/memoria-viva). Si la persona eligió conectar la suya, usa alife_conectar_memoria cuando esté disponible o get_memory_identity en la aplicación registrada. Si pide archivos, comprueba primero que la conexión ofrece get_vault_identity y que los permisos y el espacio corresponden a esa persona. Sigue la [guía del chat Classic](references/onboarding.md) para la reconexión.

## Selección del siguiente paso

Usa [el catálogo](references/CATALOGO_HABILIDADES.json) para elegir una única habilidad responsable de la intención actual. Lee su procedimiento. Revisa el resultado de esa intervención antes de elegir otra. [Las secuencias probadas](references/secuencias.json) describen qué observación permite cada transición. Para otros encargos, elige directamente la responsabilidad coincidente y termina cuando entregue su resultado. Un alias dirige al mismo responsable. El modo cognitivo requiere petición expresa.

Conserva durante la misión el objetivo, la identidad del destino, el alcance autorizado y el criterio de aceptación. Al cambiar de destino, proyecto, revisión o permisos, comprueba de nuevo esos datos. Una parada o revocación detiene el efecto afectado. Ante un conflicto de versión, relee, contrasta los cambios y reevalúa el delta. Si la misma condición persiste sin evidencia nueva, devuelve el estado pendiente. Para cualquier afirmación de ejecución exige un recibo o una lectura posterior del destino. Una simulación usa evidencias etiquetadas como ficticias.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Coordina el equipo de interfaces de decisiones](../bago5-equipo-decisiones/procedimiento.md).
- [Selecciona especialistas según la tarea y el alcance](../bago5-flujo-trabajo/procedimiento.md).

Al conectar, usa alife_conectar_memoria. Comprueba el nombre, memory_id y permisos de la memoria y el estado vault de esa misma respuesta. Solo anuncia Vault conectado si coincide el memory_id, el almacenamiento está disponible y hay permiso de archivos. Si falta, ofrece «Autorizar archivos de Vault» (alife_conectar_vault). Tras el consentimiento, relee ambas identidades. Para operaciones de archivo usa el procedimiento de Vault y comprueba el permiso de carga o descarga que corresponda.
