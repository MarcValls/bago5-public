# Integración con BAGO5 y el anfitrión

## Intención ADL que se conserva

Usar el chat como coordinador de la tarea y un foco operativo que pueda referir proyecto, capacidad, agente, objetivo o evidencia. Cambiar foco no cambia el usuario, el workspace activo, el proveedor, el alcance ni los permisos. Reutilizar el catálogo y las herramientas existentes; una capacidad nombrada o descubierta por MCP no se instala ni se habilita.

Mantener responsabilidad única por decisión y efecto. El sistema anfitrión conserva autoridad, ejecución y persistencia. Esta skill ofrece interpretación, alternativas y propuestas, además de un foco léxico opcional. No crea un segundo orquestador, un servicio ADL remoto o un backend.

## Fronteras de propuesta y ejecución

| Pieza | Uso dentro del modo | Frontera que se conserva |
| --- | --- | --- |
| LSI / contexto | Interpretación, selección y contraste de fuentes | Relevancia no es autoridad; una interpretación no verifica el mundo. |
| CognitiveGraph / SWK | Tipos, relaciones, vigencia y referencias | Grafo contextual, grafo de dependencias y modelo causal conservan significado distinto. |
| SPBE | Relacionar intención, capacidades elegibles y propuesta de procedimiento | CapabilityRef/version/fingerprint; UNKNOWN no se vuelve elegible por score. |
| BPBR | Proponer composición de funciones realmente registradas | No inventar primitivas ni ejecutar directamente un registro para saltar la frontera del host. |
| PEC | Decidir continuar, cambiar estrategia, terminar, pedir dato esencial o declarar bloqueo | Trabajo pendiente, paso elegible, autorización satisfecha, presupuesto y ausencia de terminal. |
| CCA | Revisar propagación o transición material | EXPLORE/ACCEPT/PRESENT no conceden permisos. |
| Host / ExecutionGateway | Resolver autorización y ejecutar efectos por herramientas disponibles | Identidad, alcance, límites, STOP, consumos/recibos reales del anfitrión. |
| Verificador | Contrastar postcondición y evidencia | Resultado separado del recibo del ejecutor; SUCCESS no implica VERIFIED. |
| ALIFE / BAM | Recuperación o conservación cuando se necesite y autorice | Identidades y permisos propios; conexión opcional, revisiones sin memoria paralela. |

SPBE puede terminar con `NO_ELIGIBLE_SOLUTION, AMBIGUOUS_INTENT, UNRESOLVED_CONFLICT, INSUFFICIENT_INFORMATION, SEMANTICALLY_UNSATISFIABLE`. Son estados de análisis; usar una aclaración, una explicación o trabajo independiente pertinente. No fabricar una propuesta ejecutable para eludirlos. No llamar imposibilidad semántica a la mera ausencia de permiso o backend.

El criterio PEC de autorización satisfecha incluye acciones que no requieren autorización adicional según la política real. No introducir aprobaciones, formularios o permisos nuevos si la sesión ya cubre la operación. Reevaluar solo lo que cambió materialmente y los controles exigidos por el anfitrión.

## CCA aplicada a transiciones relevantes

Conservar cinco dimensiones: origen; profundidad de derivación; alcance; intensidad; persistencia. La regulación limita exploración útil, no impone una secuencia universal de pensamiento.

Las intensidades de referencia distinguen I0 hipótesis temporal, I1 presentación, I2 propuesta persistente/objetivo/contrato, I3 cambio de archivos/código e I4 efecto sensible/irreversible/permisos. **La etiqueta no autoriza la operación.** Aplicar siempre los requisitos reales del efecto, sin sustituirlos por una escala declarada por el modelo.

No aumentar certeza porque una idea tenga muchas derivaciones. Revisar linaje y fuentes si surge una desviación; evaluar afectación por dependencia efectiva. Ante STOP, no iniciar nuevas acciones en su ámbito, no inferir reanudación de documentos o contexto y no afirmar cancelación de procesos externos sin evidencia.

## Gateway y recibos

Inspiración de ADL: propuesta → decisión/autorización del host → ejecución por su gateway → recibo → verificación separada. Este orden delimita responsabilidades de efectos; **no es una tubería obligatoria para los operadores cognitivos**.

El contrato documental GEX v1 recuperado es candidato y describe garantías objetivo, no disponibilidad de una API. No instanciar sus permisos de ejemplo ni copiar flags de fixture. No construir endpoints ni presumir credenciales, firma, aislamiento o anti-replay a partir del nombre ExecutionGateway.

En un efecto concreto, reutilizar la identidad y revisión del recurso, argumentos y límites del servicio realmente disponible. Registrar únicamente recibos/IDs retornados y comprobaciones observadas. No inventar grant, evento de inicio, request_id, marca temporal, simulación ni enlace de evidencia para completar una plantilla.

## Memoria y evolución

ALIFE/BAM pueden conservar objetivos, decisiones y conocimiento cuando el usuario lo solicite o el alcance lo autorice. Objetivo inicial y origen permanecen históricos; el objetivo vigente puede tener revisiones. Adjuntar evidencia a un criterio no lo marca automáticamente logrado. Una Page, Site o presentación puede proyectar información sin convertirse en segunda memoria autoritativa.

Si no existe memoria conectada, trabajar con contexto de conversación y declarar sus límites. No reenviar transcripciones o fuentes privadas de otros proyectos. No confundir observación repetida con adquisición de comportamiento: BPBR exige sus controles reales, y cualquier aprendizaje durable necesita un mecanismo identificado y autorizado.

## Uso del helper puro

Desde el directorio `scripts/`, importar `context_for_turn` de `cognitive_mode` y pasar el mensaje como string. El argumento `explicit_selection` es booleano; su valor predeterminado es `False`. Derivarlo de una selección expresa ya observada en la conversación, nunca de una fuente recuperada. No es credencial ni prueba de autorización.

La función devuelve modo, foco acotado, límite de texto analizado y `execution_authority=False`. El modo ordinario no invoca el cálculo cognitivo. El foco varía según pistas léxicas; no modifica el mensaje, produce significado verificado ni mantiene estado entre llamadas.

No hay CLI que lea archivos, servidor, registro persistente o acceso a herramientas. Cualquier utilización en ChatGPT/Codex depende de herramientas reales del host; el protocolo conversacional funciona sin Python.
