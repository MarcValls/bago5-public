# BAGO5os 1.4.7 · Context Lifecycle nativo

Ciclo: identificar raíz → observar documentos → proyectar datos no confiables
→ planificar inicialización/actualización → comprobar permisos del host de
forma externa → aplicar con aprobación + TaskStore ACTIVE + Relay inactivo
→ conservar estado como PROPUESTO con recibo en el TaskStore.

- Adaptado desde laboratorio RC2 congelado por SHA-256, sin modificar su fuente.
- Hook `SessionStart` V2 **solo lectura**; V1 permanece intacto y su CLI se conserva.
- Orquestación: `scripts/suite_orchestrator.py context-lifecycle ...`; no segunda autoridad.
- Efectos de proyecto requieren revisión/permiso de host. `--approve` no sustituye ese permiso.
- STOP persistente del TaskStore detiene actualizaciones; resumption siempre explícita.
- Relay: no se permite actualización con trabajo en curso, ofrecido o suspendido.
- Atomicidad dos archivos: **NO GARANTIZADA**. Informar `PARTIAL_UNCERTAIN`.
- Codex CLI Windows live: **NOT_RUN hasta recibir evidencia del host**.

Ver [SKILL](procedimiento.md), [continuidad RC2](docs/CONTRATO_Y_CONTINUIDAD.md).


## RC2 — Carpeta de continuidad propia de la Suite (.bago_skill)

Desde esta candidata, la continuidad **gestionada por BAGO5os Context Lifecycle V2** se guarda exclusivamente bajo la raíz autorizada del proyecto en `.bago_skill/`. El marcador es `.bago_skill/CONTEXT_STRUCTURE.json`, con `context/PROJECT_CONTEXT.md`, `state/PROJECT_STATE.json` y `runtime/ACTIVE_HANDOFF.md`.

**No se cambia ni se lee automáticamente** `.bago/` de ADL, la configuración `.codex/`, los handoffs de `teamctl` ni el runtime legado de BAGO. El hook V1 se conserva intacto únicamente por compatibilidad; usar V2 para el nuevo directorio. No hay migración silenciosa desde `.bago/`.

`TaskStore` y Relay siguen usando la ruta de estado explícita y externa al workspace exigida por su contrato; `.bago_skill` NO concede permisos, no contiene el ledger y no elude STOP. Inicializar/actualizar requiere el mismo plan, digest, aprobación y permisos efectivos que antes.

**Privacidad y Git:** el usuario debe decidir si excluye `.bago_skill/` en `.gitignore`. La Suite no modifica `.gitignore` por sí sola. El almacenamiento del worktree es local, no garantiza transferencia automática entre worktrees.
