# Procedencia, reutilización y límites

Esta skill adapta protocolos recuperados y un componente concreto de ADL. No incluye memorias privadas, conversaciones históricas completas, credenciales ni copias de runtimes. Los documentos de referencia son antecedentes versionados; su estado no se extiende a este paquete.

## Código reutilizado

`scripts/adl_focus.py` reproduce byte por byte `src/cognition/bago5_chat.py` de **MarcValls/BAGO_AGENTIC_DATA_LAB**, commit **fb81877d35a80dabe37fefd5fdb1f643190c6a24**, recuperado por el agente coordinador el 20 de noviembre de 2026. Ver [procedencia legible por máquina](source-provenance.json).

Fuente: [ADL · foco cognitivo](https://github.com/MarcValls/BAGO_AGENTIC_DATA_LAB/blob/fb81877d35a80dabe37fefd5fdb1f643190c6a24/src/cognition/bago5_chat.py).

Licencia del componente: [MIT, Copyright (c) 2026 MarcValls](ADL-LICENSE.txt), conservada íntegra desde el mismo commit; Git blob `8915d998230828562fa50af956cf76715129d713`.

Se conserva su algoritmo de pistas léxicas, unidades tipadas, pesos fijos y activación acotada: seis unidades de foco, dos saltos, 32 expansiones y lectura de pistas en los primeros 8.000 caracteres. `cognitive_mode.py` añade únicamente selección explícita, modo ordinario predeterminado y metadatos honestos de alcance. No añade aprendizaje, inferencia remota, persistencia, permisos o efectos.

Los tests locales cubren ese adaptador y el foco reutilizado; no certifican el servidor ADL, la conexión ChatGPT, semántica general, autorización productiva ni el comportamiento del modelo.

## Contratos y capacidades adaptados

| Fuente recuperada | Uso aquí | Estado/límite conservado |
| --- | --- | --- |
| Motor de Improvisación Cognitiva v0.1 y CCA v0.2, textos aportados en MOTOR_IMPROVISACION_CCA_CONTRATOS_v0.3_CANDIDATA (4 nov 2026) | Diez capacidades, siete responsabilidades, ocho mecanismos, cinco operadores opcionales y cinco dimensiones CCA | Arquitecturas propuestas; v0.3 formaliza contratos y tests sintéticos, no demuestra motor generativo. |
| BAGO5_LSI_001 v0.2 (8 nov 2026) | Perspectivas sobre el original, dimensiones/anclajes, desacuerdo e incertidumbre | Diseño propuesto; comparador de referencia no es intérprete multilingüe ni prueba de comprensión. No se copia su motor en esta skill. |
| BAGO5_ADL_PLAN_MAESTRO v0.1.0 (24 oct 2026) | Chat permanente, foco sin autoridad, catálogo efectivo y conservación | Plan propuesto; no sustituye el código ADL vigente ni la petición actual. |
| ADL GEX_V1_NORMATIVE_CONTRACT.md en commit fb81877… | Separación propuesta/autoridad/gateway/recibo/verificación | El documento conserva estado PREPARED y baseline histórico bdf2be8…; no acredita servicio desplegado. |
| CognitiveGraph v0.6-FIX5 CONSOLIDATED | Revisión/validez, elegibilidad antes de ranking, linaje | RETEST_READY; contrato, no motor instalado. |
| SPBE v0.5-FIX5 y CRIT-SPBE-RUNTIME-01 | IntentRoot, CapabilityRef, incertidumbre y salida Terminal | Auditoría histórica mantiene runtime incompleto y PEC no vinculado; no atribuir paridad actual. |
| PEC v0.2-FIX1 | Continuidad por necesidad, elegibilidad, autorización satisfecha y presupuesto | No reemplaza AuthorizationBoundary/ExecutionGateway ni crea permisos adicionales. |
| BPBR v0.1 REFERENCE | Composición de capacidades registradas, evaluación y reutilización | Referencia acotada; flags de demo no son permiso real. |
| BAGO5_VSCODE_SEMANTICS_RETEST1 (11 oct 2026) | Atención entre elegibles, expectativas, contraste y plasticidad como patrones | Integridad de manifiestos; NO_GO_WINDOWS/PRODUCTION. No se copia el kernel ni FixtureGrantStore. |
| COG-MISSION-001, complemento 0.1 (22 oct 2026) | Propuesta, host explícito, efecto observado, reflexión y recuperación | Misión local demostrada históricamente; aprendizaje no evaluado. No activa Spiral ni laboratorio ConfigManager. |
| BAM base v0.3; BAM-OBJ-001/BAM-CAT-001 | Objetivo inicial, revisiones, genealogía y superficies como enlaces | Laboratorio local; no presume HTTP/OAuth/MCP o cuentas reales. |
| MEO_INVENTARIO_PIEZAS_20261022 | Predicción previa, oráculos separados y evidencia vinculada | Inventario histórico; evidencia presente no prueba soporte semántico. |
| BAGO_NEURAL_FABRIC, commit 7c966664b7b01a0ccdf0c5c1b22333cc5ef1959d | Contexto→candidatos de herramientas, correlación de eventos y revisión por resultado | Código recuperado y leído; no ejecutado ni instalado. Su ranking léxico y feedback no demuestran comprensión ni aprendizaje general. Ver [alcance exacto](neural-fabric.md). |

## Conflictos y elementos no recuperados

El paquete de ablación CAUSAL_INTERVENTION_001 inspeccionó un snapshot donde la atención era posterior a la selección; el RETEST1 semántico recuperado incorpora SemanticSelector. No son el mismo candidato ni una prueba universal de causalidad.

La edición CCA v0.2 titulada ORIGINAL_EDICION se declara reconstrucción. El paquete posterior conserva textos completos aportados; eso no autentica una versión histórica instalada. La referencia cognitiva de outputs v2 DRAFT y el binding de outputs v1 a eventos v2 conservan fronteras distintas; no migrar schemas por el nombre.

Neural Fabric se recuperó también como código fuente directo, con el alcance concreto documentado en [su referencia](neural-fabric.md); permanece como antecedente, sin servicio nuevo instalado. La continuidad histórica menciona ISPI (Inferencia Semántico-Procedimental de Intenciones) como propuesta relacionada con el ejemplo canino. Su implementación y fuente original versionada son NO_RECUPERADO; no se promueve a motor por esa mención. Tampoco se recuperó un motor de intuición independiente. Las hipótesis, analogías o mecanismos disponibles no acreditan recuperación total de esos sistemas.

## Estado de esta entrega

IMPLEMENTADO: instrucciones operativas de modalidad explícita, referencias de fronteras y selector/foco local puro. La ejecución de tests del paquete acredita solo los casos que se hayan ejecutado sobre esa revisión.

NO COMPROBADO por esta skill: activación nativa del host después de publicar, comportamiento semántico general, integración ADL remota, aprendizaje autónomo/persistente, pesos entrenados, autoridad productiva y memoria conectada. Conservar siempre el estado real observado.
