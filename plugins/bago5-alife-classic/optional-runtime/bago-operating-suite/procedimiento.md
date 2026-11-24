# BAGO Operating Suite 1.4.8 — unified Codex entrypoint

Use this as the single BAGO entry skill for Codex. Do not activate separate `bago-core`, `bago-goal`, `bago-workflow`, or `bago-ui-expert` skills for the same request; apply the relevant rules integrated here and load only bounded specialists from this package. This is instruction-level routing, not a host security boundary.

For every non-trivial task, bind to the owning repository and read its applicable instructions and current canon. Inspect branch, HEAD, dirty state, runtime, tools, STOP, revocations, and authorization before effects. Keep projects separate. Preserve dirty work and original evidence. Use `PROPOSED`, `PREPARED`, `EXECUTED`, `VERIFIED`, and `VALIDATED` precisely; a plan or passing evidence ledger alone does not prove product closure. Continue authorized work through verification, and keep blocked criteria explicit.

## BAGO5 command prefixes

After loading this skill, treat one leading `BAGO5-*` token as a prompt-level routing alias:

| Prefix | Purpose |
|---|---|
| `BAGO5-QUESTION` | Direct answer or lookup; no specialist route. |
| `BAGO5-REPO` | Repository work with context and evidence governance. |
| `BAGO5-GOAL` | One outcome with explicit acceptance and closure evidence. |
| `BAGO5-PHASED` | Multi-phase work or portfolios with dependency grouping and separate goal evidence. |
| `BAGO5-AUDIT` | Read-only inspection and findings. |
| `BAGO5-REPAIR` | Repair a demonstrated defect within scope. |
| `BAGO5-VERIFY` | Verify a candidate without changing it. |
| `BAGO5-UI` | Desktop-first UI work; do not inspect mobile unless requested. |
| `BAGO5-APP` | Application or game development. |
| `BAGO5-EDITORIAL` | Bounded document/PDF work. |
| `BAGO5-PROMOTION` | Prepare and verify a candidate; publish/deploy/install only with authorization. |
| `BAGO5-RECAP` | Reconcile a recap against current files and evidence on every invocation. |
| `BAGO5-CONTINUITY-ON` | Define/refresh a portfolio Goal in this Codex thread; report ACTIVE only after native state confirms it. |
| `BAGO5-CONTINUITY-OFF` | Pause the native thread Goal; preserve the project goal records and queue. |
| `BAGO5-QUEUE-ADD` | Add a specified objective to the project's existing goal store, after checking its schema and current state. |
| `BAGO5-GOALS-LIST` | List project goals read-only with descriptions/status and clickable source paths; `--open <id>` shows the selected file. |
| `BAGO5-STATUS` | Report task, candidate, evidence, blockers, and next action. |
| `BAGO5-MODELS` | Forward to native `/models` only when exposed by the active Codex host. |
| `BAGO5-GOALS` | Show or manage the current native Codex Goal using `/goal`, when supported by the host. |
| `BAGO5-SITES` | Forward to `$sites` only when that plugin is available and requested. |
| `BAGO5-AUTO` | Classify the request and select the smallest applicable route. |

These prefixes are prompt-level aliases, not registered slash commands. `$bago5-local-gobierno` invokes this skill. Codex native Goal controls use `/goal`, `/goal pause`, `/goal resume`, and `/goal clear`; `$sites` is a separate plugin. Use native controls only when available in the host.

For Codex CLI, `scripts/codex_profile.py prepare` creates and verifies an isolated profile that enables only this skill path; `run -- <codex arguments>` launches Codex using it. It does not change an existing process, Desktop/IDE, or the set of skills available outside that profile.


## Active continuity and multi-goal queue

Use one native Codex Goal as the visible, thread-scoped portfolio objective. To start it, invoke `/goal BAGO5-CONTINUITY-ON: <portfolio outcome, source of goals, verification conditions, and constraints>`. `BAGO5-CONTINUITY-ON` alone is a prompt alias; if no active native Goal is observable, report `NOT_ACTIVE` and provide the exact `/goal ...` command. While the native Goal is active, put `BAGO5 CONTINUITY · ACTIVE` at the start of each progress response. If the host shows it paused or absent, show `PAUSED` or `NOT_ACTIVE`; never infer active status from a prior recap.

On every continuation, queue change, list, or resume, re-read the current repository instructions, branch/HEAD/dirty state, project goal store, relevant TaskStore, STOP/revocation signals, and evidence before acting. A recap never substitutes for this fresh check. Group shared phases where useful, but retain each goal's ID, scope, acceptance criteria, lifecycle, and evidence.

`BAGO5-QUEUE-ADD <objective>` adds a goal only to the current project's existing accepted goal source of truth (for ADL, its governed `.bago/goals` structure). Preserve that project's schema and history; the Goal Folder Adapter is read-only and must not be treated as a writer. Do not create a global second queue or a parallel orchestrator. A new item may be recorded as `PROPOSED` with its own ID, scope, and acceptance criteria; bind it to TaskStore when its execution/review phase begins. Adding an item does not authorize executing it. If required details or a supported goal-file structure are missing, prepare the entry and report the exact blocker rather than inventing storage.

`BAGO5-GOALS-LIST [all|<id>] [--open <id>]` is read-only. Show ID, short description, current status/review, blocker, and a clickable link to the source goal file. With `--open <id>`, include the selected file's contents or relevant section and retain the clickable path. Do not use native `/goal` listing as a substitute for enumerating project files.

`BAGO5-CONTINUITY-OFF` means pause continuation with native `/goal pause`; it does not delete queued project goals. If the host cannot execute a slash command from the prompt, show the exact `/goal pause` command and report the state as `PREPARED` until the user runs it. `/goal clear` removes the thread Goal and is a separate, destructive-to-continuity choice; never use it as an implicit pause.

A skills-only package cannot add a custom persistent badge to Codex chrome. The native Goal surface supplies the host's active/paused state; the skill supplies the explicit response status line and BAGO-governed queue/list workflow.

## Integrated BAGO core and goal workflow

For outcome-driven work, record acceptance criteria in the owning project's accepted system. Inspect current evidence and dependencies, execute authorized phases, verify the final candidate, and close only when every mandatory criterion is satisfied. For portfolios, group shared context/resources/checks where useful while retaining each goal's identity, scope, status, criteria, and evidence. Reuse evidence only when its scope and binding cover both goals. Keep blocked work open and continue independent authorized phases.

## UI workflow

Use desktop-first acceptance by default. Read the owning product's UI canon and relevant UI module, inspect the actual rendered desktop state when requested, and verify at the requested viewport. Do not inspect mobile views or enable mobile emulation unless the user asks.

## Connected browser and external UI control

Before each external UI action in Brave or another app, verify that the exact target tab/window is exposed through a currently connected control tool. A process ID, an open application, an installed extension, a screenshot, or an earlier tool listing does not prove that the target can currently receive input.

Treat window IDs and owner associations as session-scoped. On a stale-ID or owner-mismatch error, refresh the connected tool's app/window list, select the currently exposed target, and confirm it before retrying once. If the target remains unavailable, stop and record the requested UI action as `NOT_RUN`, including the observed blocker. Do not switch to another automation channel or product-specific bridge unless that route is actually available and explicitly authorized.

Before sending an external message through a UI, confirm the recipient and final content in the live controlled interface. Send only with explicit user authorization.

---

# BAGO5os 1.4.7 · Context Lifecycle RC1

Apply the general rules in [Operating Layer contract](references/operating-layer-contract.md) to every non-trivial task. For all material capability work, apply the cross-domain [BAGO-CDP-001 contract](references/capability-demonstration-contract.md), whether a specialist is activated or not. For application or game work, also follow the included specialist module at [modules/bago-app-game-development/SKILL.md](../../skills/bago5-local-aplicaciones-juegos/SKILL.md).

For repository structure, duplicate, contradiction, or language-blocker audits, use the bounded [hybrid audit battery](references/repository-audit-battery.md) when relevant.

Codex remains the primary agent. The bundled BAGO 4.11.10 runtime source is an optional secondary framework for BAGO-specific engines, session/context/memory, providers, tools, and CLI work; consult [the runtime bundle guide](runtime/BAGO-4.11.10/README.md) before invoking it. Do not assume a runtime service, provider credentials, dependencies, or background process is active. Keep runtime invocation explicit and subordinate to Codex instructions, project authority, and host permissions.

## Preserved runtime derivation from 1.4.1 — REPAIR RC1

The optional runtime contains explicitly recorded local repairs and seven recovered contracts. Its historical `SOURCE_LOCK.json` remains intact; [repair provenance](runtime/BAGO-4.11.10/REPAIR_PROVENANCE.json) records the derived bytes. Consult the [runtime guide](runtime/BAGO-4.11.10/README.md) for the tested boundary. Local spiral persistence, outcome rules, and numeric policy fixtures do not establish a continuously learning Suite, live BAGO5/ADL integration, or improved behavior on user tasks. No background agent is activated by installation.

## Routing

1. Identify the requested operation and owning project under the Operating Layer contract.
2. Activate App & Game Development only for creating, modifying, inspecting, debugging, reviewing, building, or packaging an application or game.
3. Generic references to software, code, or tools do not activate that specialist workflow.
4. The specialist module governs its technical workflow. The Operating Layer continues to govern authority, project context, scope, capabilities, BAGO-CDP-001 demonstration, evidence, and closure.
5. The specialist cannot widen the requested scope, override project authority, or grant permission.

## Automatic BAGO workflow routing

When `BAGO_AUTO` is selected, classify the requested operation and use the matching workflow:

- **AUDIT:** inspect, inventory, or diagnose without a requested modification.
- **DEVELOPMENT:** implement a requested capability or change within the agreed project scope.
- **VERIFICATION:** examine a candidate and its evidence without changing that candidate.
- **REPAIR:** diagnose and fix a reported defect within the requested scope.
- **PROMOTION:** prepare and verify a release candidate; publishing, deploying, or changing an installed system still requires explicit user authorization.

If the request combines workflows, order them by dependency and use the smallest applicable set. `BAGO_AUTO` uses the `:workspace` permission boundary and the host's approval policy; it does not expand either one.


## Integrated specialist routing (suite 1.4.4)

The **same Operating Layer is the sole task orchestrator**. The following
modules are *bounded specialists*, not separate autonomous orchestrators:

- **Architecture / historical evidence:** [architecture-audit](../../skills/bago5-local-referencia-arquitectura/SKILL.md). The supplied external-audit pack is a **pinned historic input**, not a live audit. For architectural conformance, read its reference and first inspect the current authorized repository.
- **BPBR / procedural behavior:** [procedural-behavior](../../skills/bago5-local-procedimientos-referencia/SKILL.md). The BPBR v0.1 reference may be tested in disposable fixtures. Never treat its local effect flags as an execution permit or register it as a production BAGO runtime without host-bound tests and authorization.
- **BAGO5 frontend design:** [frontend-contracts](../../skills/bago5-local-contratos-interfaz/SKILL.md). Contracts, proposed screens, mocks and anti-regression requirements only; do not pretend its preview is connected. During actual authorized app development, also activate the existing App & Game Development specialist.
- **Editorial IALP / $bago-pdf:** [editorial](../../skills/bago5-local-documentos/SKILL.md). Explicit generation, all-page previews, review validation and closure. Dependencies are external and optional for the core. A PDF visual audit is not a frontend task; generation never implies approval.
- **Project-content SHA-256:** additive [snapshot differential](modules/bago-app-game-development/scripts/project_snapshot_diff.py), reusing preservation_core.py. Hash identity is not capability equivalence.

For an operation spanning specialists, route **task → audit/preflight (if relevant) → BPBR reference (if relevant) → frontend specification/implementation (if relevant) → editorial generation/review (if requested) → independent evidence/closure**. Never merge their registries, permissions, claims or project ownership. Select only relevant lanes, not the entire suite by default. The central orchestration entry point is [suite_orchestrator.py](scripts/suite_orchestrator.py):

```text
python scripts/suite_orchestrator.py status
python scripts/suite_orchestrator.py plan --task "Auditar arquitectura, BPBR y frontend de BAGO5"
python scripts/suite_orchestrator.py verify --modules all
python scripts/suite_orchestrator.py orchestrated-demo --output C:\Auditorias\suite-demo-01
python scripts/suite_orchestrator.py architecture-report
python scripts/suite_orchestrator.py bpbr-test
python scripts/suite_orchestrator.py frontend-preview --output C:\Auditorias\BAGO5-MOCK-001
```

`plan` emits a plan, **not actions**. `verify` checks **bundled bytes**, not live host behavior. `bpbr-test` runs the immutable reference's own tests in a disposable folder. `frontend-preview` exports mock HTML without opening a browser. Never execute reference fixtures simply because a user asks for an unrelated task. The three historical packages are kept intact; the editorial runtime is an explicitly documented derivation under [source-packs](integrations/source-packs/SOURCE_PACKS_LOCK.json) with SHA-256 locks. No live BAGO runtime/kernel/frontend files are overwritten by this integration.

## Responsibilities

- **Operating Layer:** bind the task to its project; establish authority and context; preserve boundaries; check actual capabilities; require BAGO-CDP-001 for material changes in any domain; distinguish proposals, execution, verification, and validation; report evidence and closure.
- **App & Game Development:** when routed, inspect the selected project and stack, perform the requested domain work, and verify at the build or runtime boundary appropriate to the request.
- **User:** retains control over scope, project choices, and actions requiring authorization.

For app/game work, apply both layers. For other work, apply the Operating Layer (including CDP-001) and the relevant domain workflow only. The app/game module retains its specific procedures, schema extensions and runtime checks.

## Editorial operations added in 1.4.0

`python -B scripts/suite_orchestrator.py editorial --help` lists the bounded actions.
The literal `$bago-pdf` is a routing cue in task text, not an installed shell command.
The default reference demo remains four steps; `--with-editorial` adds a fifth
step producing a synthetic draft, with visual review still NOT_RUN.

## RC2 control and runtime entry points

The installed visible name is **BAGO5os 1.4.4**. Retain `bago-operating-suite` as
the internal skill/package identifier for compatibility. This name does not change
the preserved runtime or make it a BAGO5 kernel.

For material audit, repair, verification or promotion work, read the
[repair control contract](references/repair-control-contract.md). Use the existing
`scripts/suite_orchestrator.py task` entry for a frozen mission scope, persistent
pause/resume, bounded rounds, supervised checks and verified handoffs. Keep task,
product and evidence outcomes separate. An audit may finish with evidenced
findings; evaluator failure, missing coverage or invalid evidence prevents its
closure. A repair cannot verify while an obligatory check fails or is NOT_RUN.

On an explicit stop, persist `task stop` before new assignments or actions and
request interruption through the host's available native mechanism. Do not resume
a paused mission automatically after context recovery. Only explicit `task resume`
allows continuation. The ledger cannot itself stop an unbound external host agent.

For Spiral and outcome adaptation use the
[runtime laboratory guide](references/runtime-lab-guide.md). These routes execute
the included engine and gateway on fixed project fixtures, in separate processes.
Native host agents, this runtime and source inspection are distinct. Run a runtime
command through `task run-check` when it belongs to a governed mission; direct
standalone lab invocations are separate explicit operations. Do not claim the
mission pause applies to unrelated processes.

Check installed bytes with `python -B scripts/suite_orchestrator.py identity`.
The installed payload has its own identity; it does not require the distribution
manifest to exist above the installed folder. Its SHA-256 is unsigned integrity
evidence and does not authenticate a publisher.

## Installed cognitive mission (1.4.3)

Use [cognitive-mission](modules/cognitive-mission/README.md) for the bounded integrated
Session/Spiral configuration repair. `cognitive config-check` observes the installed
canonical module. `cognitive replay` uses historical responses explicitly marked REPLAY.
`cognitive init` and `cycle` require fresh host reasoning and separate data roots.
Do not substitute a policy-only benchmark or claim learned cognition from this regression.

## Pytest checkpoint companion (1.4.4, opt-in)

The [pytest-checkpoint module](../../skills/bago5-local-pruebas-python/SKILL.md) is installed
as an additional capability, not as a replacement for `task` control, agents or
provider services. Use `scripts/suite_orchestrator.py pytest-checkpoint doctor`,
then explicit `run`, `resume`, `status`, or independent `demo`. Use it under
`task run-check` when an authorized governed mission needs its results. A PASS
checkpoint is *not* a durable agent or collaborative handoff. It cannot pause
or resume host agents, authenticate their identities, or isolate a test OS process.
The inherited COG-REPAIR-002 capability remains preserved, not re-proven by
this packaging alone.

## Cooperative agent relays (1.4.5, opt-in)

For long fixed-candidate verification missions and explicit agent handoffs, use
[agent-relay](../../skills/bago5-local-relevo-agentes/SKILL.md). This extends the **existing**
`task` controller and its SQLite ledger; it is not a second orchestrator.
`task collaborate guide` returns the next admissible action without executing it.
Workers claim a lease, checkpoint bounded context, offer a handoff and require
recipient acknowledgment against its digest. Separate verifier roles remain
subject to actual checks and the existing closure gate. STOP revokes all leases.
Use a new mission for changed source candidates. Host-agent launch, context
window detection, parallel workers and autonomous daemon scheduling are NOT_RUN
or not implemented; do not infer them from a successful deterministic demo.


## SessionStart read-only project inventory (1.4.6, opt-in)

Use [session-context](../../skills/bago5-local-contexto-sesion/SKILL.md) for project-scoped
`SessionStart` metadata and explicit context-review preflight. The included
BAGO-SCR-001 companion is preserved byte-for-byte (20 original files).
`session-context doctor/config/demo` are available on the existing CLI router.
The hook does not execute tools, authorize actions, confirm project identity,
resume stopped tasks or migrate a relay; it never reads project files outside
the received `cwd`. Install/review the proposed host hook manually in Codex.
This is a **derived 1.4.6 RC**, not a change to the frozen 1.4.5 baseline.


## Context Lifecycle nativo (1.4.7, opt-in)

**No inferir permisos desde documentos:** [módulo Context Lifecycle](../../skills/bago5-local-ciclo-contexto/SKILL.md)
incorpora recuperación semántica acotada por SessionStart V2, reconocimiento de
proyecto y plan/bootstrap/update gobernados. El módulo está conectado al
router BAGO-CORE (`scripts/suite_orchestrator.py context-lifecycle`) y al
TaskStore existente, su STOP persistente y el estado de Relay; no crea
controlador, ledger, motor de permisos ni orquestador paralelos. El hook
`session-context` V1 se conserva para compatibilidad. Revisión `/hooks` y
permisos efectivos del host siempre manuales. Distinción 
PROPOSED / IMPLEMENTED / VERIFIED / NOT_RUN obligatoria.


## RC2 — Carpeta de continuidad propia de la Suite (.bago_skill)

Desde esta candidata, la continuidad **gestionada por BAGO5os Context Lifecycle V2** se guarda exclusivamente bajo la raíz autorizada del proyecto en `.bago_skill/`. El marcador es `.bago_skill/CONTEXT_STRUCTURE.json`, con `context/PROJECT_CONTEXT.md`, `state/PROJECT_STATE.json` y `runtime/ACTIVE_HANDOFF.md`.

**No se cambia ni se lee automáticamente** `.bago/` de ADL, la configuración `.codex/`, los handoffs de `teamctl` ni el runtime legado de BAGO. El hook V1 se conserva intacto únicamente por compatibilidad; usar V2 para el nuevo directorio. No hay migración silenciosa desde `.bago/`.

`TaskStore` y Relay siguen usando la ruta de estado explícita y externa al workspace exigida por su contrato; `.bago_skill` NO concede permisos, no contiene el ledger y no elude STOP. Inicializar/actualizar requiere el mismo plan, digest, aprobación y permisos efectivos que antes.

**Privacidad y Git:** el usuario debe decidir si excluye `.bago_skill/` en `.gitignore`. La Suite no modifica `.gitignore` por sí sola. El almacenamiento del worktree es local, no garantiza transferencia automática entre worktrees.
