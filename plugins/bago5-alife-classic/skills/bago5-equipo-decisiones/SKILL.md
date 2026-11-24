---
name: bago5-equipo-decisiones
description: "Coordina especialistas, tareas y relevos para construir interfaces de decisiones con alcance y evidencias compartidos."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato del complemento unificado

Aplicar bago5 y su contrato GPT Classic. Las rutas locales y comandos siguientes requieren acceso real al proyecto identificado. No crear ni inicializar la mision ADL de ejemplo por defecto. Usar solo la mision expresamente seleccionada y sus criterios. El controlador portable se incluye en optional-runtime/team-controller/scripts/teamctl.py, relativo a la raiz del plugin. Usar --root <proyecto-autorizado> y la mision seleccionada. Requiere Python y jsonschema accesibles; GPT Classic necesita una herramienta de ejecucion real. Sin ella preparar handoff y marcar ejecucion NOT_RUN. Los roles son perspectivas de trabajo: solo un agente realmente distinto puede producir verificacion independiente. No lanzar agentes sin autorizacion y capacidad del host.


Operate as the root coordinator, not as a generic implementer.

Start by reading `AGENTS.md`, `../../optional-runtime/team-controller/protocol/TEAM_PROTOCOL.md`, `../../optional-runtime/team-controller/protocol/COMMUNICATION.md`, the selected mission, and `.bago5-team/runtime/state.json` if it exists.

La mision agent-decision-inspector es un ejemplo especifico de ADL, no la mision predeterminada del complemento.

Antes del algoritmo, comprobar que la operación corresponde al contrato del controlador elegido. El teamctl incluido solo admite `AUDIT`, `REPAIR`, `VERIFICATION` y `PROMOTION`; no admite una operación genérica `DEVELOPMENT` o `INTEGRATION`. No renombrar el trabajo ni inicializar un controlador adicional para eludir esa limitación. Para un plan agéntico de integración, aplicar [bago5-plan-por-fases](../bago5-plan-por-fases/SKILL.md) y [selección del controlador](../bago5/references/controller-selection.md). Los pasos `verify`, `pair`, `claim` y `handoff` siguientes se aplican únicamente a una misión teamctl válida y autorizada.

Execution algorithm:

Para cada fase, completar primero el [preflight de fase](../bago5-plan-por-fases/references/phase-preflight.md). La inspección de solo lectura puede precederlo; `init`, `pair` con asignación operativa, `claim`, spawn y cambios requieren GO vigente o estar incluidos expresamente en los pasos que `can_prepare` habilite para producir un resultado revisable, sin cruzar el gate humano pendiente. Comprobar ejecución, verificación independiente cuando sea requerida y entrega; anunciar de antemano relevo Codex↔Work e intervención humana. Revalidar al recibir un handoff o cambiar condiciones, sin reiniciar el controlador ni repetir permisos vigentes.

1. Inspect the selected project controller and mission. Initialize only the explicitly authorized mission if state does not exist; no default ADL initialization.
2. Run `python <plugin-root>/optional-runtime/team-controller/scripts/teamctl.py --root <proyecto-autorizado> verify` before scheduling work.
3. Run `python <plugin-root>/optional-runtime/team-controller/scripts/teamctl.py --root <proyecto-autorizado> pair` to compute READY work that is safe to execute together.
4. If native multi-agent collaboration actions are available, spawn one subagent per work item in the first safe batch, up to mission concurrency. Give each subagent the work item id, role skill name, dependency handoff paths and exact writable scopes. Do not spawn two agents onto overlapping scopes.
5. If native collaboration actions are unavailable, execute the same batch sequentially. Do not pretend sequential execution was parallel.
6. Before a specialist edits files, require `python <plugin-root>/optional-runtime/team-controller/scripts/teamctl.py --root <proyecto-autorizado> claim <WORK_ID> --agent <agent-id>`.
7. Require specialists to finish with `python <plugin-root>/optional-runtime/team-controller/scripts/teamctl.py --root <proyecto-autorizado> handoff <WORK_ID> --file <handoff-draft.json>`. A conversational message is not a handoff.
8. During native parallel work, relay cross-cutting discoveries with live agent messages and require durable `teamctl.py note` events for blockers, risks and contract-impacting information.
9. After each handoff run `python <plugin-root>/optional-runtime/team-controller/scripts/teamctl.py --root <proyecto-autorizado> verify` and recompute `pair`.
10. If a frozen contract must change, stop affected consumers and create an explicit change request. Never silently mutate a consumed contract.
11. Do not let the verification engineer implement the surfaces it verifies.
12. Closure requires the selected mission acceptance criteria; W12 applies only when that actual mission defines it. Compilation alone is not completion.

Routing:

- Decision flow, information architecture, accessibility, uncertainty presentation -> `bago5-diseno-revision-decisiones`.
- Conclusion/claim/evidence/provenance/snapshot identity -> `bago5-procedencia-evidencias`.
- Agent traces, tool calls, correlation, chronology/causality -> `bago5-trazas-ejecucion`.
- Proposed actions, authorization, approval/rejection, receipts -> `bago5-control-acciones`.
- React/TypeScript inspection surfaces -> `bago5-interfaz-decisiones`.
- Independent tests, adversarial cases, P0/P1/P2 verdict -> `bago5-verificacion-decisiones`.

Keep work bounded by existing architecture. Reuse before extend; extend before new.


Antes de inicializar estado, aplicar [seleccion exclusiva del controlador](../bago5/references/controller-selection.md).
