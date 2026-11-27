---
name: bago5-ejecucion-tareas
description: "Implementa tareas asignadas y cambios mecánicos con alcance autorizado, criterios definidos y evidencia de resultado."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

[Aplicar requisitos del procedimiento 3](../bago5/references/controles-especialistas.md#control-3).

# BAGO Workers

Cuando la tarea pertenezca a una fase, comprobar su [preflight vigente](../bago5-plan-por-fases/references/phase-preflight.md) antes de aceptar la asignación operativa o modificar recursos. Debe cubrir también las pruebas y la entrega exigidas a la fase. Un recibo heredado no acredita las herramientas, accesos ni permisos del agente receptor: revalidar en su entorno y comunicar antes cualquier cambio de host o intervención humana pendiente. Una tarea independiente sin plan por fases conserva los controles ordinarios del proyecto.

Si la aceptación humana corresponde al cierre, preparar solo los pasos que el contrato habilite explícitamente con `can_prepare`, bajo autorización vigente y aviso previo. Entregar el resultado revisable y detenerse ante el punto de decisión pendiente; no asumir aceptación, ejecutar efectos que dependan de ella ni cerrar la fase por haber completado la preparación.

Implementation skill for the selected repository. Choose the mode from the first argument.

## Modes

### `implement`

Implement only the approved scope.

- Make the smallest defensible change.
- Preserve contracts unless explicitly instructed.
- Avoid collateral refactors.
- Run the repository-defined tests that cover the change.
- Before finishing, show the diff, tests executed, results, and anything not verified.
- Do not declare `VALIDATED` on your own authority.

### `mechanical`

Execute only clear, repetitive transformations with objective criteria.

- Do not make architectural decisions.
- If ambiguity appears, stop and return a BLOCK.
- Keep the scope minimal and run the relevant mechanical checks.

If no argument is given, default to `mechanical` and ask for confirmation before large edits.

## Common rules

- Load `bago5` at the start of any non-trivial task to read `.bago/` state and canon.
- Use `git status` before and after to show what changed.
- Never overwrite repository manifests, lockfiles, or source config unless the task explicitly authorizes it.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
