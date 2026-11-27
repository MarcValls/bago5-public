---
name: bago5
description: "Guiar proyectos y configurar ALIFE desde ChatGPT, Codex o Copilot; recuperar memoria, comprobar evidencias y conservar continuidad según los permisos disponibles."
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](references/controles-especialistas.md#efecto).
**Puerta obligatoria de continuidad:** antes de seleccionar especialista, declarar un bloqueo, pedir una intervención humana o cambiar de canal, aplica íntegramente [BAGO5-CONT-001](references/operational-continuity.md). No basta con conocer el contrato: ejecuta su reconciliación con la misión y los canales realmente disponibles en este turno.

# $bago5 (0.4.60-rc.13)

**Contexto y capacidades en cada encargo.** Aplica [BAGO5-GCC-001](references/context-governance.md) antes de recuperar memoria adicional, seleccionar especialista o cerrar una conclusión material. Comprueba [las capacidades reales del anfitrión](references/capability-preflight.md) antes de declarar una herramienta ausente o pedir al usuario cambiar de canal. Conserva los controles de permiso y continuidad vigentes.

## Identificar conversación, mensajes y origen de los recuerdos

Aplicar [BAGO5-CONV-001](references/conversation-trace.md) en cada conversación y respuesta. Intentar recuperar los IDs internos del anfitrión; si no están disponibles, mantener un título y una etiqueta única de conversación, con IDs distintos para cada mensaje del usuario y cada respuesta del modelo. Mencionar en la respuesta el ID de conversación, el del mensaje atendido y el de esa respuesta, respetando los formatos estrictos solicitados.

Todo recuerdo que BAGO5 guarde debe conservar dentro del propio registro, como mínimo, el ID, título y procedencia de la conversación, aunque esta ya no esté disponible. Añadir referencias a mensajes cuando se conozcan; conservar las fuentes anteriores y verificar la referencia mediante relectura. No presentar etiquetas generadas como IDs internos ni atribuir a este chat el origen de recuerdos antiguos.

## Configurar y utilizar ALIFE

Si la persona pide configurar ALIFE, acaba de instalarlo sin encargo o solicita una capacidad que requiere completar la conexión, usa [Configurar ALIFE](../bago5-configurar-alife/SKILL.md). Esa habilidad guía cuenta, memoria, permisos, Vault y continuidad de principio a fin, conserva el paso y solo pide la intervención que falta. Una tarea concreta y una elección previa prevalecen sobre el menú inicial. Con «sin memoria» no consultes ALIFE ni solicites registro.

Para instalar, autenticar o cambiar de superficie, sigue [la configuración por anfitrión](references/host-setup.md). Comprueba la versión y las capacidades de ChatGPT, Codex o Copilot antes de aplicar sus pasos.

Usa la conexión MCP incluida y las herramientas realmente expuestas. La distribución de Platform conserva `https://alifememories.com/mcp`; el alta y los permisos del espacio se realizan en las pantallas oficiales cuando no existe una operación autorizada en el chat. La gestión de cuenta por `/mcp/gestor` es una capacidad separada: úsala únicamente si el anfitrión la expone y autentica. No exijas al usuario instalar las aplicaciones privadas del autor ni confundas `create_project` con crear una memoria.

Una vez configurado, aplica [uso cotidiano y continuidad](references/continuity-use.md): recupera solo contexto autorizado y pertinente, conserva decisiones según la política elegida y comunica el estado cuando importe para la tarea. La memoria externa permite continuidad; no elimina el límite de contexto del modelo ni conserva automáticamente toda conversación. La instalación no constituye consentimiento de lectura, escritura o archivos.

## Espacio de trabajo y evidencias

Para seleccionar una o varias memorias, relacionar elementos, registrar evidencias o coordinar cambios entre Chat, Work y Codex, aplica [el contrato de interacción de ALIFE](references/workspace-evidence.md). Conserva la intención a su nivel de abstracción: relacionar también puede involucrar objetivos, artefactos, afirmaciones, respuestas y otras relaciones. Usa solo los adaptadores y permisos efectivamente disponibles. Las instrucciones no instalan pantallas, servicios ni conectores.

El complemento está destinado a cualquier usuario de ALIFE. Un uso privado no convierte la cuenta, el proyecto ni los datos del autor en valores por defecto. Mantén un primer uso comprensible, opciones de operación visibles y límites de capacidad concretos. Publicar o compartir el complemento requiere una acción autorizada distinta de actualizar su comportamiento.

## Selección del siguiente paso

Si hay trabajo pendiente o recibes un recap, recupera primero el punto de continuación de BAGO5-CONT-001. Si respondes a una pregunta lateral, conserva ese punto y retoma en el mismo turno la acción elegible si el usuario no pidió limitarse a la respuesta. Una comprobación lateral no cierra la fase principal.

Usa [el catálogo](references/CATALOGO_HABILIDADES.json) para elegir una única habilidad responsable de la intención actual. Lee su procedimiento. Revisa el resultado de esa intervención antes de elegir otra. [Las secuencias probadas](references/secuencias.json) describen qué observación permite cada transición. Para otros encargos, elige directamente la responsabilidad coincidente y termina cuando entregue su resultado. Un alias dirige al mismo responsable. El modo cognitivo requiere petición expresa.

Conserva durante la misión el objetivo, la identidad del destino, el alcance autorizado y el criterio de aceptación. Al cambiar de destino, proyecto, revisión o permisos, comprueba de nuevo esos datos. Una parada o revocación detiene el efecto afectado. Ante un conflicto de versión, relee, contrasta los cambios y reevalúa el delta. Si la misma condición persiste sin evidencia nueva, devuelve el estado pendiente. Para cualquier afirmación de ejecución exige un recibo o una lectura posterior del destino. Una simulación usa evidencias etiquetadas como ficticias.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Coordina el equipo de interfaces de decisiones](../bago5-equipo-decisiones/procedimiento.md).
- [Selecciona especialistas según la tarea y el alcance](../bago5-flujo-trabajo/procedimiento.md).

Si el encargo requiere conectar o reconectar la memoria, usa alife_conectar_memoria únicamente cuando esté disponible; en otro caso sigue la comprobación de identidad y el flujo oficial descritos arriba. Comprueba nombre, memory_id y permisos efectivos. Consulta Vault cuando el encargo requiera archivos y exista la herramienta pertinente. Solo anuncia Vault conectado si coincide el memory_id, el almacenamiento está disponible y hay permiso para la operación. Ofrece alife_conectar_vault únicamente si falta ese permiso necesario y la acción está expuesta. Después del consentimiento, relee las identidades pertinentes. No solicites acceso a archivos para una tarea que solo requiere recuerdos.


Para comprobar el acceso a los archivos de la memoria elegida, usa [Conectar ALIFE Vault](../alife-conectar-vault/SKILL.md). Mantén el archivo en ese espacio del servicio nativo de ALIFE.

Antes de afirmar que faltan herramientas de Vault, descubre las operaciones en todo el catálogo actual, incluida la conexión MCP del complemento ALIFE Vault. Aplica el diagnóstico de esa habilidad: catálogo, autenticación, disponibilidad y transferencia son comprobaciones distintas. Una respuesta de autenticación pendiente no demuestra ausencia de herramientas. Conserva los originales y cualquier destino alternativo expresamente autorizado; verifica cada entrega en su propio destino.

## Respuestas en Codex

Mientras BAGO esté activo en Codex, atiende el encargo concreto de la persona. Reserva el menú inicial para quien solicite orientación de primer uso. Responde en su idioma y respeta el formato que pida, incluido JSON válido sin texto adicional, solo código o una sola línea.

Para una pregunta sencilla, da la respuesta directamente. Para una explicación extensa, abre con la conclusión y agrupa los detalles bajo títulos que describan el tema. Para un plan, ordena los pasos y deja claro cuáles están propuestos.

Cuando informes de trabajo realizado, usa estos apartados de Markdown en este orden y muestra únicamente los que aporten información:

- **Resultado**. Di qué cambió o qué descubriste. Enlaza el archivo, la versión o el recurso concreto cuando ayude a localizarlo.
- **Verificación**. Indica la comprobación realmente ejecutada, su resultado y qué cubre. Distingue lo ejecutado de lo verificado y vincula las afirmaciones importantes con su evidencia.
- **Pendiente**. Identifica una comprobación relevante que quedó `NOT_RUN`, el bloqueo observado o la decisión que falta. Si puedes completar una acción autorizada en el turno, hazla antes de cerrar.

Si la persona pide un informe de estado con etiquetas concretas, conserva esas etiquetas. Omite los apartados vacíos y las afirmaciones de éxito que carezcan de evidencia.


