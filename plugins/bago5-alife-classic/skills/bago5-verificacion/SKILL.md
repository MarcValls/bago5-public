---
name: bago5-verificacion
description: Comprobar el resultado y emitir un dictamen con evidencia.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

# #BAGO5-verification · Comprobación separada

Fijar identidad exacta de candidata, requisitos, base previa, fuentes y aceptación. Si la candidata integral es inaccesible, declarar `BLOQUEADO` para su verificación, no inventar conformidad desde resúmenes.

Ejecutar (solo cuando esté autorizado y haya herramientas) pruebas positivas, negativas, de regresión, funcionales, visuales, procedurales y contractuales pertinentes. Distinguir inspección estática, simulación, HTTP real, UI real y host del usuario. No atribuir independencia técnica por adoptar un rol lógico diferente.

Para cada afirmación: AFIRMACIÓN → COMPROBACIÓN → EVIDENCIA → RESULTADO → CONCLUSIÓN. `GO/NO_GO` solo dentro del alcance probado; `NOT_RUN` si no se ejecutó. Hash e integridad no prueban actualidad o funcionamiento.

No reparar la candidata ni sobrescribir evidencias previas. Entregar dictamen, fallos reproducibles, límites y acciones pendientes.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Contrasta una instalación con su contrato canónico](../bago5-contrato-canonico/procedimiento.md).
- [Demuestra capacidades con resultados observados](../bago5-demostracion-capacidades/procedimiento.md).
- [Comprueba el cierre y el resultado en el destino real](../bago5-verificacion-cierre/procedimiento.md).
- [Verifica el inspector de decisiones y sus contratos](../bago5-verificacion-decisiones/procedimiento.md).

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
