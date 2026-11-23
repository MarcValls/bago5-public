---
name: bago5-control-acciones
description: Resolver alcance, autorización y parada antes de un efecto.
---

Antes de actuar, aplica el [control de permiso, revisión y STOP](../bago5/references/controles-especialistas.md#efecto).

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

[Aplicar requisitos del procedimiento 5](../bago5/references/controles-especialistas.md#control-5).


Your boundary is governed action state.

Never collapse these states:
CAPABILITY -> ELIGIBILITY -> AUTHORIZATION -> AVAILABILITY -> EXECUTION -> RECEIPT.

Required invariants:
- A proposed action is not authorization.
- Authorization is not proof of execution.
- Execution without a receipt is represented as unverified execution state, not success.
- Approval and rejection record actor/reason when available.
- Risk and required approval level are inspectable.
- Expired/revoked authorization is distinguishable from never-authorized.

Reuse existing BAGO authorization and receipt vocabulary when present.

## Corrección y recuperación de elegibilidad

Aplicar [BAGO5-CCR-001](../bago5/references/behavior-recovery.md). Distinguir condición temporal incumplida, prohibición vigente, resultado incierto y acción que ya dejó de ser necesaria. Conservar objetivo y criterios; mantener el bloqueo únicamente en las acciones afectadas y sus dependencias, salvo barreras globales del host, PRIVATE o STOP.

Resolver un bloqueo con evidencia actual de su causa y volver a evaluar el recibo vigente mediante `turn_decision.assess`. Recuperar elegibilidad no crea autorización. Reutilizar la autorización que siga vigente y cubra la acción; no pedirla de nuevo ni restaurar una caducada o revocada. Si la decisión es CONTINUE, el agente activo ejecuta el trabajo autorizado mediante los controles ordinarios del host; el adaptador de recuperación no ejecuta herramientas. Una prohibición requiere resolución por su autoridad competente, y un resultado incierto requiere reconciliación antes de cualquier repetición.

Test unauthorized proposal, expired authorization, rejected action, execution failure, missing receipt and receipt mismatch.

Aplicar la [decisión de turno](../bago5/references/turn-decision.md): continuar el trabajo local autorizado, cerrar el encargo satisfecho o comunicar el impedimento concreto. Validar un handoff únicamente cuando corresponda un relevo real o solicitado; no convertirlo en un requisito adicional para cerrar.

## Procedimientos según el encargo

Elige únicamente el procedimiento correspondiente al objeto y al resultado pedido.

- [Delimita el impacto de paradas y desviaciones](../bago5-impacto-parada/procedimiento.md).
