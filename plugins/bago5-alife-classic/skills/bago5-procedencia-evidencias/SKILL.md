---
name: bago5-procedencia-evidencias
description: "Define contratos que vinculan conclusiones y afirmaciones con sus evidencias, fuentes y versiones."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

[Aplicar requisitos del procedimiento 5](../bago5/references/controles-especialistas.md#control-5).


Your boundary is epistemic traceability.

Required invariants:
- A conclusion is not evidence.
- A claim explicitly declares which evidence supports, contradicts or fails to support it.
- Evidence carries source identity and retrieval/snapshot identity where available.
- Confidence is metadata about a conclusion/claim and is never a substitute for evidence.
- Missing provenance remains missing; do not fabricate it.
- Stale evidence can be represented and rejected by consumers.
- Contract serialization must be deterministic enough to fingerprint.

Prefer repository-native schemas and receipt/evidence primitives. Adapt rather than duplicate.

Add tests for unsupported claims, multiple evidence items, contradictory evidence, stale snapshot identity and missing provenance.

Finish only with a validated handoff.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
