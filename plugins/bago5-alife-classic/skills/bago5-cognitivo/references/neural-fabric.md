# Intención, candidatos y revisión de resultados

## Fuente y comprobación

Repositorio `MarcValls/BAGO_NEURAL_FABRIC`, commit `7c966664b7b01a0ccdf0c5c1b22333cc5ef1959d` (11 mayo 2026), recuperado el 20 noviembre 2026 mediante lectura de GitHub. Se leyeron estos archivos de esa revisión, sin ejecutar su contenido:

| Archivo | Git blob | Qué acredita la lectura |
| --- | --- | --- |
| [core/neural_toolbox.py](https://github.com/MarcValls/BAGO_NEURAL_FABRIC/blob/7c966664b7b01a0ccdf0c5c1b22333cc5ef1959d/core/neural_toolbox.py) | `e98ce0444a5189490f3b30283d907f31d12ca591` | Señales por subcadenas, perfiles derivados del registro, puntuación normalizada, filtros y feedback de pesos por herramienta. |
| [core/bago_neural.py](https://github.com/MarcValls/BAGO_NEURAL_FABRIC/blob/7c966664b7b01a0ccdf0c5c1b22333cc5ef1959d/core/bago_neural.py) | `2c14f3d966bbbd6a78e1dd67f197e4c83f12ac60` | Bus HTTP/SSE, eventos con correlación, registro de nodos y persistencia JSONL. No es por sí mismo un motor semántico. |
| [docs/ARCHITECTURE.md](https://github.com/MarcValls/BAGO_NEURAL_FABRIC/blob/7c966664b7b01a0ccdf0c5c1b22333cc5ef1959d/docs/ARCHITECTURE.md) | `c2235d45798abc71ba80c9e3f03396f1d0cdec6a` | Describe SENSE/PLAN/ACT/OBSERVE/LEARN/DECIDE y routers; el diagrama no demuestra integración operativa. |

Estado: **fuente recuperada; revisión estática acotada; runtime NOT_RUN**. No se copian el bus, el bucle autónomo, el ejecutor ni la persistencia de pesos en esta skill. No se recuperó aquí todo el repositorio ni se verificaron todos sus controles.

## Adaptación útil dentro del modo

Relacionar señales del mensaje con capacidades existentes puede ayudar a proponer candidatos. Conservar el original, las restricciones, la incertidumbre y alternativas: una coincidencia léxica no resuelve negaciones, intención ni autoridad. La elegibilidad real precede al ranking y debe revisarse de nuevo al ejecutar si cambia el contexto.

La descripción del resultado de una herramienta puede orientar futuras propuestas. Separar utilidad para la tarea, corrección del resultado, fallo de infraestructura y coste. En el código recuperado, `run_dynamic_workflow` usa `rc != 0` como señal `found_issues`; no permite distinguir por sí sola un hallazgo válido de un fallo de la herramienta. No trasladar ese criterio como recompensa automática ni penalizar una verificación necesaria por no encontrar errores.

El registro de eventos puede inspirar correlación entre propuesta, operación, recibo y evidencia; un evento emitido o un registro durable no prueban la postcondición. Se reutilizan los mecanismos reales del anfitrión, sin arrancar otro bus ni conceder autoridad a una puntuación.

La referencia histórica ISPI orienta una pregunta útil: qué intención probable explica señales incompletas y qué observación permitiría distinguirla de otras. Tratar la respuesta como hipótesis revisable; pedir aclaración solo cuando el dato sea esencial. Una intención inferida no habilita efectos, instala BPBR ni constituye una implementación del sistema canino. La intuición, si se usa como término, describe una hipótesis inicial que debe contrastarse, no conocimiento adquirido sin evidencia.
