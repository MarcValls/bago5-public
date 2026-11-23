---
name: bago5-ingenieria-repositorios
description: Aplicar cambios de repositorio y reparar defectos en el alcance autorizado.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato GPT Classic del complemento

[Aplicar requisitos del procedimiento 6](../bago5/references/controles-especialistas.md#control-6).

Las ocho operaciones repo.* son procedimientos para el asistente, no endpoints MCP ni comandos registrados. Los bindings de las referencias se deben resolver contra herramientas disponibles. No se transfiere una declaracion de conformidad de versiones anteriores.


# Repository Engineering

Use this skill for non-trivial repository operations where attribution, scope, authority and verification matter.

## Source status

The bundled `repository.engineering v0.1.1` source is `PREPARED`; its domain lifecycle is `PROPOSED`; DCT v1.2 conformance is `NOT_RUN`. Do not call this version CONFORMANT or VALIDATED. The v0.1.0 conformance report bundled elsewhere is historical and does not transfer to v0.1.1.

## Operation routing

Route the task to the smallest applicable candidate operation defined in `references/DOMAIN_OPERATIONS.md`:
- `repo.resolve_baseline`
- `repo.audit`
- `repo.plan_change`
- `repo.apply_change`
- `repo.verify_change`
- `repo.govern_change`
- `repo.contain_or_rollback`
- `repo.prepare_handoff`

Use the matching procedure in `references/DOMAIN_PROCEDURES.md`. Load only the references needed for the active operation.

## Required discipline

Before mutation, establish repository identity, HEAD, branch, worktree/index status, pre-existing changes, exact authorized target paths/effects and required capabilities.

Trace material claims as:
`claim -> repository source/action -> evidence reference -> verification scope -> conclusion`

Do not absorb unrelated pre-existing changes into the current change set. Do not infer that a build verifies tests, a diff verifies behavior, or an old CI run verifies a later HEAD.

A governance/canon mutation requires explicit mutation authority and before/after/supersession evidence. A task-specific override is not by itself a canon mutation.

If authority, capability, identity or sufficient evidence is missing, use `BLOCKED`; if incompatible competing state prevents safe attribution, use `CONFLICT`; if an executed acceptance check fails, use `FAILED`.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Corrige defectos demostrados y comprueba regresiones](../bago5-reparacion/procedimiento.md).
- [Diagnostica y repara la instalación BAGO efectiva](../bago5-diagnostico-reparacion/procedimiento.md).
- [Implementa tareas asignadas con alcance y criterios](../bago5-ejecucion-tareas/procedimiento.md).
