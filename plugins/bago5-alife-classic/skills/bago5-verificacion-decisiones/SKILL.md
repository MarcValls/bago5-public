---
name: bago5-verificacion-decisiones
description: "Verifica el inspector de decisiones y sus contratos con casos adversos; emite hallazgos sin reparar la implementación."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

[Aplicar requisitos del procedimiento 5](../bago5/references/controles-especialistas.md#control-5).


You are independent. Do not repair implementation while verifying it unless explicitly reassigned after issuing the verdict.

Verify claim -> evidence -> provenance, trace correlation, proposed action -> authorization -> execution -> receipt and cross-navigation.

Mandatory adversarial cases:
- conclusion with an unsupported claim;
- evidence from a stale snapshot;
- contradictory evidence;
- missing provenance;
- failed tool call represented in trace;
- unauthorized proposed action;
- expired/revoked authorization;
- action displayed as executed without a valid receipt;
- receipt for the wrong action/run;
- inaccessible keyboard path to evidence/action details.

Classify:
- P0: dangerous false representation or control failure that can cause/approve unintended execution.
- P1: material loss of traceability, provenance, authorization clarity or user ability to detect unsupported conclusions.
- P2: non-blocking quality/usability defect.

Terminal eligibility requires P0=0 and P1=0. Record NOT_RUN separately from PASS.

Finish only with a validated handoff.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
