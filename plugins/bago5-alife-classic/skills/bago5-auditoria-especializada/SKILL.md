---
name: bago5-auditoria-especializada
description: "Aplica auditorías de código, contratos, seguridad, rendimiento y pruebas sobre el repositorio seleccionado."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

[Aplicar requisitos del procedimiento 3](../bago5/references/controles-especialistas.md#control-3).

# BAGO Auditors

Read-only audit skill for the selected repository. Map the first argument to an audit mode and follow the corresponding discipline.

## Modes

| Argument | Focus |
|----------|-------|
| `architecture` | ownership, dependency direction, sources of truth, contracts, invariants, domain boundaries, God Components/Modules |
| `backend` | endpoints, handlers, validation, persistence, subprocess, trust boundaries |
| `frontend` | React state, effects, navigation, panels, composition, render ownership |
| `contracts` | frontend → backend call chains, types, route compatibility, obsolete methods |
| `security` | filesystem, subprocess, credentials, Electron/IPC, tools/plugins, destructive actions |
| `performance` | renders, effects, IO, trees, parsing, listeners, timers, caches |
| `tests` | CI, build, runtime checks, coverage vs real capabilities |
| `hygiene` | dead code, legacy, dependencies, CSS, divergent docs |
| `truth` | state/evidence separation, false closures, UI claims without evidence |
| `code-map` | flow reconstruction, ownership, API calls, tests, cross-dependencies |

If no argument is given, default to `architecture`.

## Universal rules

- Inspect before concluding. Trace from real entrypoints to real effects/persistence.
- Distinguish `HECHO`, `INFERENCIA`, `HIPÓTESIS`, and `RECOMENDACIÓN`.
- Distinguish a legitimate large dispatcher/orchestrator from a real God Module; require evidence of responsibility concentration.
- Do not edit files. Do not declare `VERIFIED` without executed evidence.
- Use `bago5` first for lifecycle and state context if the task is continuation, conflict, or closure work.
- Return findings with file paths, symbols, and line numbers when possible.


## Pipeline completo

Una auditoria integral usa un RunId y una baseline HEAD; registrar estado antes/despues de pruebas. Los informes de otros RunId no se mezclan. Ejecutar secuencialmente si no hay delegacion real autorizada. Auditores no editan fuentes; una peticion de auditoria no autoriza las tareas de implementacion 20/21. La tarea 22 requiere el alcance de verificacion seleccionado. La sintesis vuelve a comprobar hallazgos criticos/altos, no concatena conclusiones sin evidencia.

- [00-preflight](references/tasks/00-preflight.md)
- [01-inventory](references/tasks/01-inventory.md)
- [02-architecture](references/tasks/02-architecture.md)
- [03-frontend](references/tasks/03-frontend.md)
- [04-backend](references/tasks/04-backend.md)
- [05-contracts](references/tasks/05-contracts.md)
- [06-workspace](references/tasks/06-workspace.md)
- [07-features](references/tasks/07-features.md)
- [08-security](references/tasks/08-security.md)
- [09-tests-ci](references/tasks/09-tests-ci.md)
- [10-hygiene](references/tasks/10-hygiene.md)
- [11-performance](references/tasks/11-performance.md)
- [12-truth-authority](references/tasks/12-truth-authority.md)
- [13-synthesis](references/tasks/13-synthesis.md)
- [14-refactor-plan](references/tasks/14-refactor-plan.md)
- [20-implement-approved-pr](references/tasks/20-implement-approved-pr.md)
- [21-mechanical-approved](references/tasks/21-mechanical-approved.md)
- [22-verify-change](references/tasks/22-verify-change.md)

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
