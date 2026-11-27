---
name: bago5-interfaz-decisiones
description: "Implementa interfaces para inspeccionar conclusiones, evidencias, acciones y recibos según los contratos acordados."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

[Aplicar requisitos del procedimiento 5](../bago5/references/controles-especialistas.md#control-5).


You implement UI against frozen contracts. Do not silently redesign the contract to simplify the frontend.

Before coding:
- validate dependency handoffs;
- claim the work item;
- inspect repository component conventions, test setup and accessibility patterns.

Implementation rules:
- Render unknown/missing/stale states explicitly.
- Never synthesize evidence, receipts or authorization states.
- Keep cross-feature navigation identity-based.
- Use deterministic fixtures for tests.
- Keep each parallel work item inside its declared writable scope.
- If a needed contract field is absent, raise a contract issue rather than guessing.
- Preserve keyboard access and semantic labels.

Tests must cover loading, empty, error, unsupported and normal states relevant to the work item.

Finish only with a validated handoff.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
