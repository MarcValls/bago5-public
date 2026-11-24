---
name: bago5-demostracion-capacidades
description: "Define, integra y demuestra capacidades mediante recorridos reproducibles y resultados observados."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# Demostración progresiva de capacidades

Aplica este procedimiento a cambios materiales de software, agentes, motores, API, automatización, interfaces, datos o juegos. En lectura, consulta o cambios menores no fuerces una ejecución ni un artefacto irrelevante. Diseña el recorrido de demostración junto con la capacidad; no esperes a que termine toda la plataforma.

Define una ficha comprobable, con o sin archivo:

- proyecto, capability_id, afirmación y candidate_id (o NOT_BUILT);
- frontera declarada, punto de entrada real, dependencias esenciales y límites;
- criterios de aceptación, casos positivos y negativos pertinentes;
- recorrido reproducible, entradas, resultados esperados y observables;
- capacidades protegidas que deben conservarse y evidencia diferencial aplicable.

Construye una unidad útil e intégrala con el punto de entrada real. Una pantalla desconectada, mock, scaffold, build o esquema válido no prueba el comportamiento declarado. Si la capacidad es de UI, demuestra su conexión real al comportamiento. No ejecutes checks salvo que el usuario lo solicite o el alcance vigente lo autorice. Si falta permiso o dependencia, mantén PREPARED/PROPOSED/BLOCKED y registra NOT_RUN con el motivo.

Distingue el estado de capacidad —PROPOSED, IMPLEMENTED, VERIFIED, DEMONSTRABLE, BLOCKED— de los estados de acción —PROPOSED, PREPARED, EXECUTED, VERIFIED, VALIDATED—. No promociones uno por evidencia del otro. VERIFIED exige checks con resultado, candidata y alcance ligados. DEMONSTRABLE exige además una ruta real y reproducible en la frontera declarada, observables contrastables, límites y dependencias conocidos, conservación revisada cuando corresponda, y pasos que otra persona pueda seguir. Una comprobación estructural o un resultado de demo sintética no supera este gate.

Registra la afirmación → comprobación → evidencia → frontera/candidata → conclusión. Indica cobertura, fallos, límites y cualquier paso NOT_RUN. La aceptación de un recorrido no prueba funcionalidades ajenas ni la plataforma completa.

El esquema de references/capability-record.schema.json es una plantilla local de registro; este plugin no incluye un validador automático ni un motor BAGO-CDP-001.
