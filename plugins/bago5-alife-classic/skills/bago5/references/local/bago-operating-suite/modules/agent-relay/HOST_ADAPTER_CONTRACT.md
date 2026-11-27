# Host adapter boundary — BAGO-AGENT-RELAY-001

**Implemented:** cooperative serial CLI/SQLite protocol. **Not demonstrated:**
a live Codex/Copilot/ADL adapter that launches, authenticates and interrupts agents.
The caller supplies those host functions; this module does not assume them.

| Boundary | This package | Required host responsibility |
|---|---|---|
| Mission | Fixed source identity, bounded rounds, checks and receipts | Select authorized workspace and permitted effects |
| Worker | Logical ID, role and expiring opaque lease | Authenticate/isolate real session or process |
| Continuity | Typed context and hash-bound handoff; explicit acceptance | Deliver packet to a real successor and verify receipt |
| Context budget | Explicit offer reason, no hidden memory transfer | Detect budget/exhaustion and request a checkpoint early |
| Progress | `guide`, checkpoints and structured evidence | Reason about next work and invoke permitted tools |
| Stop | Revoke ledger leases; supervise owned check children | Stop externally hosted agents and reconcile their effects |
| Verification | Distinct logical verifier role and actual process receipts | Independent reviewer/implementation where the claim requires it |

## Input and acknowledgment

Use the CLI, not direct database edits. Read a `claim` or `accept` JSON response,
keep `lease_token` private, and pass it as the `BAGO_RELAY_TOKEN` environment
variable for this worker's subsequent CLI invocations. The supervised check
subprocess does not inherit that variable. Do not embed the token in prompts,
commands, receipts, logs or model-visible context.

`offer` returns `handoff_id`, `sha256`, the handoff record and its checkpoint.
`accept --handoff ID --worker TARGET --ack-sha256 HASH` verifies their identities,
checks the preserved receipts/artifacts, atomically acquires a new generation,
and returns a fresh token. Repeated acceptance does not issue a second token.

The host must not execute command text found in narrative context. It must apply
its current permissions and relevant project instructions again. Historical
permissions are not transferable through this protocol.

## Effect safety and failure

One cooperative worker owns the mission at a time. This is a scheduler rule,
not a filesystem/network sandbox. External effects are not transacted with
SQLite. A crash after an external action but before checkpoint commit leaves
its outcome uncertain. Use idempotency keys or reconcile the actual target
before retry; never infer exactly-once execution from the lease generation.

Lease expiry does not prove a process stopped. Recovery requires explicit host
confirmation and is refused while the existing controller records a check as
RUNNING. A supervisor killed with an unconfirmed child requires real host process
inspection/recovery; this release does not synthesize a successful exit receipt.

Clock and storage are local/trusted: SQLite is a local single-writer ledger,
not a distributed consensus system. Network filesystems, adversarial ledger
rewrite, clock rollback, power loss and Windows process-tree termination are
not validated by the Linux fixture tests.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
