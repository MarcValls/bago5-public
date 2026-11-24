[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Misión cognitiva acotada

Parte de un objetivo explícito, candidata, fuentes disponibles y criterios de aceptación. Separa hechos, hipótesis, propuestas, acciones y resultados. En cada ciclo formula una propuesta comprobable, define qué evidencia la refutaría, ejecuta solo si se autorizó y reflexiona sobre el resultado observado.

El host model puede proponer y revisar razonamiento; eso no prueba aprendizaje, memoria persistente ni mejora de modelo. Los modos LIVE/REPLAY, SessionManager, Spiral y gateway pertenecen a la Suite incluida bajo optional-runtime/bago-operating-suite; el acceso de ejecucion desde el host debe comprobarse. Úsalos solo si el host expone una instalación identificada y sus herramientas; de lo contrario, completa el ciclo conversacional acotado y declara cualquier operación runtime NOT_RUN.

Aplicar la [decisión de turno](../bago5/references/turn-decision.md) antes del final: continuar con el siguiente paso local elegible, cerrar cuando se cumpla la aceptación o identificar el impedimento concreto. Separar actualización de interpretación, propuesta de procedimiento y adopción autorizada y comprobada. Conserva revisiones anteriores y no reescribas una hipótesis histórica para hacerla parecer verificada.

El entrypoint cognitivo incluido conserva un laboratorio específico de ConfigManager con ciclos acotados; no usarlo como controlador general de turnos ni sustituir su objetivo hardcodeado por el del usuario sin desarrollar y verificar un contrato de generalización. La política de decisión se ejecuta por el ayudante compartido de gobierno, fuera del payload congelado de la Suite.

Para la implementacion incluida, aplicar [puente de runtime](../bago5-acceso-motor-local/SKILL.md) y conservar candidata y controlador de mision.
