---
name: bago5-verificacion-cierre
description: "Verifica cierre, regresiones y resultado en el destino real, sin reparar la candidata ni sustituir pruebas por recibos."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

[Aplicar requisitos del procedimiento 3](../bago5/references/controles-especialistas.md#control-3).

# BAGO Final Verifier

Independent verification pass for BAGO work. Use this skill after an implementation phase or before declaring a closure.

## Procedure

1. Review the current `git diff` or the relevant diff range.
2. Read `.bago/state/PROJECT_STATE.json`, `.bago/runtime/ACTIVE_HANDOFF.md`, and any acceptance criteria if they exist.
3. Check for:
   - Regressions in existing behavior.
   - Broken frontend/backend contracts.
   - Insufficient tests or checks.
   - Changes outside the authorized scope.
   - Unsupported claims in the prior output.
4. Run the repository's own verification commands where safe and relevant (tests, type checks, linters).

## Verdicts

- `PASS` — evidence supports the closure claim.
- `FAIL` — evidence contradicts the closure claim; list what failed.
- `BLOCKED` — missing information or material conflict prevents a verdict.

## Rules

- Do not fix code; only report.
- `VERIFIED` requires executed evidence.
- `VALIDATED` additionally requires satisfied closure criteria and defined validation authority.
- Never convert the absence of findings into proof beyond the verification scope.
- If the task is large or ambiguous, use `bago5` first for context and state.

## Evidencia para cerrar

Aplicar la [decisión de turno](../bago5/references/turn-decision.md#sustentar-el-cierre-y-retomar-el-encargo). NOT_RUN/NO_COMPROBADO no explican un bloqueo: cada comprobación pendiente requiere próxima operación o impedimento preciso, fuente actual y mínima intervención. No intentar acciones prohibidas para obtener evidencia ni repetir permisos vigentes. `closure.review_required=true` pide revisar la justificación, no ejecutar reparaciones ni ampliar el encargo.

Una declaración de «hecho», la configuración visible del panel y una conexión operativa son evidencias distintas; la memoria conserva observaciones históricas. Tras una intervención humana, comprobar el criterio restante por canales autorizados. Conservar STOP, permisos y modo privado: HOST_UNAVAILABLE bloquea la operación sensible y dependientes; trabajo independiente solo sin PRIVATE o gate cerrado y sin exposición de secretos. En Work es un procedimiento del agente, no un interceptor. Una verificación puede concluir al entregar su dictamen sustentado aunque el producto siga incompleto.

Para verificar una función publicada, aplica el [recorrido de usuario en destino](references/recorrido-en-destino.md) antes del dictamen.

En Codex, aplica el [formato de respuesta de BAGO](../bago5/SKILL.md#respuestas-en-codex) al comunicar el resultado.
