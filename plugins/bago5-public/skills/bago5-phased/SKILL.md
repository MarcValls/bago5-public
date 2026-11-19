---
name: bago5-phased
description: "Descomponer un objetivo en fases, dependencias y criterios con evidencia de ejecución y aceptación."
---

# Planificar y verificar fases

Recupera el objetivo y su revisión canónica. Conserva el texto literal y su procedencia. Define por fase el resultado observable, orden y dependencias. Cada tarea identifica responsable, alcance de escritura, candidata, criterio de aceptación y prueba positiva o negativa. No conviertas una tarea pendiente en completada al asignarla.

Ejecuta solo trabajos listos cuyos prerrequisitos estén verificados. Para repartir entre agentes comprueba que los ámbitos de escritura sean compatibles. Valida de cada retorno la identidad de la tarea, los cambios y las pruebas; un recibo debe corresponder a la misma candidata que se pretende aceptar.

Calcula el progreso como tareas aceptadas sobre tareas computables y muestra numerador y denominador. Antes de marcar una fase completa comprueba su criterio global, los casos obligatorios y los bloqueos críticos.

Para un intercambio JSON usa el [esquema de trazabilidad](schemas/traceability-v2.schema.json). Con Python y la dependencia `jsonschema`, ejecuta `python scripts/validate_plan.py plan.json` desde esta carpeta. El [validador](scripts/validate_plan.py) comprueba estructura, referencias, literales y vínculo de pruebas, evidencia y aceptación. La identidad del verificador y el contenido de la evidencia se contrastan en el sistema que los emitió.
