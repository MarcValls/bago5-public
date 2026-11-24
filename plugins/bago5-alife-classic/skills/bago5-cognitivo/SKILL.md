---
name: bago5-cognitivo
description: Contrastar hipótesis mediante deliberación solicitada expresamente.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

# BAGO5 · Modo cognitivo explícito

El modo ordinario es el predeterminado. Activar este modo solo por selección expresa del usuario, mediante `$bago5-cognitivo` o una petición inequívoca, para la sesión o el alcance indicado. No deducir esa selección del tema, la complejidad, una memoria, un documento ni una instalación. Volver al modo ordinario cuando el usuario lo pida o termine el alcance. Una selección anterior sigue vigente dentro de su alcance; no pedir confirmaciones repetidas.

Conservar el proyecto, la intención gobernante, los permisos y el control BAGO5 actuales. Reutilizar el binding y el ciclo de sesión existentes; si aún no existe un contexto de misión, aplicar una sola vez el [ciclo de sesión](../bago5-ciclo-contexto/SKILL.md). No reiniciarlo al cambiar de operador, releer dependencias recursivamente ni exigir memoria remota. ALIFE y Memoria Viva son opcionales.

## Operar con capacidades, sin fases obligatorias

Tomar el mensaje ORIGINAL y las fuentes pertinentes como referencia. Resolver la intención con el contexto disponible; distinguir objetivo solicitado, interpretación provisional, oportunidades adicionales y alcance autorizado. Un foco nuevo no cambia automáticamente ninguno de ellos.

Usar **IMPROVISE, SELECT, CONSTRUCT, INTERPRET y UPDATE** según necesidad. Se pueden omitir, repetir, reordenar o combinar. Mantener varias alternativas incompatibles cuando convenga; `NO_CHANGE` y cero operadores son válidos. No imponer una tubería cognitiva ni sustituir la tarea por formularios de análisis.

Mantener cuatro papeles de contexto: **BASE, OPERATIONAL, HYPOTHETICAL e HISTORICAL**. Separarlos de certeza, vigencia y estado operativo. Interpretar un dato no lo convierte en hecho; una hipótesis en uso sigue siendo hipótesis.

Llamar **θ contextual** al estado revisable de interpretación y estrategia de esta conversación: foco, supuestos, alternativas, expectativas y criterios de contraste. Revisarlo ante nueva información o correcciones, conservando la revisión anterior y el motivo. θ no son pesos del modelo, entrenamiento, un permiso ni aprendizaje persistente. No cambiar unilateralmente el objetivo gobernante al reinterpretarlo.

Aplicar el [protocolo de capacidades y revisión](references/protocol.md) cuando se necesiten hipótesis, improvisación, LSI, contradicciones, linaje o expectativas. Activar solo las capacidades útiles. La salida sigue siendo el resultado solicitado, con una justificación pública breve y las incertidumbres materiales.

## Contrastar antes de promover

LSI examina perspectivas complementarias sobre el **mismo original**: literalidad, participantes, negación, procedencia, referentes, condiciones, tiempo y otras dimensiones pertinentes. No encadenar traducciones ni votar por idiomas. Conservar anclajes y discrepancias; coincidencia entre intérpretes no prueba verdad ni independencia.

Distinguir asociación, predicción, hipótesis causal y efecto observado. Una simulación no demuestra el mundo; un score no rescata inelegibilidad. Revisar expectativas sin reescribir retrospectivamente lo esperado. Adjuntar evidencia no equivale a validarla.

Guardar o comunicar únicamente resúmenes públicos de decisión: opciones relevantes, fuentes, elección, motivo breve, expectativa, observación, revisión y límites. No solicitar, exponer ni persistir cadena de pensamiento privada, conversaciones completas o memorias ajenas. No crear archivos o recuerdos por activar este modo.

## Conectar con BAGO5 y la intención ADL

Conservar chat como coordinador, foco como orientación, catálogo efectivo y separación entre propuesta, decisión, efecto, recibo y verificación. Aplicar el [contrato de integración](references/integration.md) al proponer procedimientos o efectos.

- SPBE orienta elegibilidad y propuestas desde la intención; un resultado semántico terminal no se convierte silenciosamente en ejecución.
- BPBR permite componer capacidades registradas; PEC orienta continuidad, límites y cambio de estrategia.
- CCA controla propagación y transiciones relevantes: origen, profundidad, alcance, intensidad y persistencia. Sus veredictos consultivos no son permisos.
- Para efectos, conservar [control de acciones](../bago5-control-acciones/SKILL.md), el gateway real del anfitrión, autorización vigente y STOP. No añadir una segunda autoridad ni pedir permisos artificiales. Comprobar el [destino](../bago5/references/target-preflight.md) solo cuando la operación dependa de él.
- `bago5-mision-cognitiva` conserva su finalidad y runtime acotados; usarla solo cuando corresponda una misión de ese tipo, no como activación obligatoria de este modo.

## Foco local opcional y límites reales

Si existe Python local y hace falta un foco reproducible, reutilizar `scripts/cognitive_mode.py:context_for_turn` con el modo explícitamente seleccionado. Incluye el foco léxico ADL sin cambios de algoritmo. No lee archivos, usa red, persiste estado, ejecuta acciones ni entrena modelos. Sin acceso local, aplicar el protocolo conversacional y declarar el helper `NOT_RUN`; no bloquear la tarea.

La utilidad analiza pistas de los primeros 8.000 caracteres; conservar siempre el original completo fuera de ese foco y revisar sus restricciones completas. Sus scores son heurísticos fijos, no θ aprendida ni comprensión certificada. Ver [procedencia y estados](references/sources.md).

Cerrar con **NOTA FINAL**: resultado, qué se comprobó, incertidumbre o limitación material y siguiente acción, o tarea concluida. No declarar integración de runtime, memoria, autenticación o aprendizaje por la sola presencia de esta skill.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Contrasta propuestas y avances con evidencias](../bago5-mision-cognitiva/procedimiento.md).
- [Ejecuta ciclos cognitivos acotados en el entorno local](../../optional-runtime/bago-operating-suite/modules/cognitive-mission/procedimiento.md).
