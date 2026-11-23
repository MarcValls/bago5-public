# Contexto de memoria de la mision

Resolver proyecto y almacen una vez, antes de cualquier ciclo. La seleccion explicita del usuario prevalece; usar la memoria elegida conforme a [onboarding](onboarding.md) y comprobar su identidad y permisos. Si no hay seleccion inequivoca, resolverla antes de leer o escribir. No inferir destino por nombres, alias historicos ni coincidencias tematicas en documentos.

El ciclo compartido es [memory-cycle.md](memory-cycle.md) y el operador es [bago5-memoria-viva](../../bago5-memoria-viva/SKILL.md). bago5-memoria, bago5 y los especialistas conservan el proyecto y almacen seleccionados: derivar una tarea no reinicia el ciclo ni el onboarding. Para varios almacenes, aplicar [federacion](../../bago5-memoria-viva/SKILL.md), con identidad, alcance y permisos separados por destino.

Si falla el conector seleccionado, declarar NOT_RUN y continuar trabajo independiente; nunca cambiar de almacen para completar una lectura o escritura. El cambio explicito de contexto termina el ciclo anterior y requiere verificar identidad y permisos del destino nuevo. No copiar datos entre destinos por cambiar de contexto.

Una derivacion a especialista no inicia otro ciclo ni concede permisos. Registrar en el handoff el contexto seleccionado, identidad observada, proyecto, restricciones y estado de lectura/escritura, sin credenciales. STOP impide lecturas y escrituras nuevas. Un alias y este contrato son instrucciones del agente, no aislamiento tecnico del servidor.
