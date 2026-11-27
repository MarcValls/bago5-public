[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

[Aplicar requisitos del procedimiento 5](../bago5/references/controles-especialistas.md#control-5).


Your boundary is execution visibility, not decision semantics.

Required invariants:
- Every trace event has a stable identity where possible.
- Correlation to run, agent, tool call, claim and action is explicit rather than inferred from display order.
- Chronology and causality are separate concepts.
- Redacted payloads stay visibly redacted.
- Missing spans/events remain visible as gaps.
- The adapter must not reinterpret a failed tool call as success.

Use existing tracing/receipt primitives before creating new telemetry models.

Test out-of-order events, missing parent correlation, failed tool calls, redaction and duplicate event ids.

Finish only with a validated handoff.
