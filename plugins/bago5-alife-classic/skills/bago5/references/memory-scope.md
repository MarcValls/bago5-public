# Contexto de memoria de la mision

En [BAGO5-GCC-001](context-governance.md), distinguir la identidad del almacén del ámbito de la afirmación. Si la lectura depende de un proyecto, verifica su identidad y aplica `project_id` cuando el conector lo admita. Evalúa los fragmentos materiales antes de usar sus conclusiones.

Resolver proyecto y almacen una vez, antes de cualquier ciclo. La seleccion explicita del usuario prevalece; usar la memoria elegida conforme a [onboarding](onboarding.md) y comprobar su identidad y permisos. Si no hay seleccion inequivoca, resolverla antes de leer o escribir. No inferir destino por nombres, alias historicos ni coincidencias tematicas en documentos.

El ciclo compartido es [memory-cycle.md](memory-cycle.md) y el operador es [bago5-memoria-viva](../../bago5-memoria-viva/SKILL.md). bago5-memoria, bago5 y los especialistas conservan el proyecto y almacen seleccionados: derivar una tarea no reinicia el ciclo ni el onboarding. Para varios almacenes, aplicar [federacion](../../bago5-memoria-viva/SKILL.md), con identidad, alcance y permisos separados por destino.

Si falla el conector seleccionado, declarar NOT_RUN y continuar trabajo independiente; nunca cambiar de almacen para completar una lectura o escritura. El cambio explicito de contexto termina el ciclo anterior y requiere verificar identidad y permisos del destino nuevo. No copiar datos entre destinos por cambiar de contexto.

Una derivacion a especialista no inicia otro ciclo ni concede permisos. Registrar en el handoff el contexto seleccionado, identidad observada, proyecto, restricciones y estado de lectura/escritura, sin credenciales. STOP impide lecturas y escrituras nuevas. Un alias y este contrato son instrucciones del agente, no aislamiento tecnico del servidor.

## Selección múltiple y cambios durante la tarea

Aplica [workspace-evidence.md](workspace-evidence.md). Conserva por separado el conjunto de memorias elegido para consultar, el destino explícito para crear y el origen con versión de cada edición. Una elección previa inequívoca sigue vigente hasta cambio, revocación o contradicción comprobada; no reinicies preguntas por derivar a otro especialista. El selector web no modifica el alcance autenticado de un conector. El acceso múltiple solo existe cuando el canal expone esa capacidad y verifica cada destino.


## Procedencia durable

Aplicar [BAGO5-CONV-001](conversation-trace.md) a cada guardado autorizado. Mantener la referencia de conversación dentro del recuerdo aunque el chat no esté disponible, y preservar las procedencias anteriores en cualquier actualización o relevo.
