---
name: bago5-contrato-canonico
description: "Compara una instalación BAGO con su contrato canónico y prepara o aplica correcciones autorizadas."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato de adaptacion GPT Classic

[Aplicar requisitos del procedimiento 4](../bago5/references/controles-especialistas.md#control-4).

# BAGO canon contract audit

## When to use

Use for requests such as “BAGO cumple este canon”, RC6/canonical DTO compliance, `CANON ABIERTO`, or an explicitly authorized foundation-contract phase in an installed BAGO runtime.

Do not use this as a release/installer workflow without a canon comparison, or to modify `C:\Program Files\BAGO` without explicit authorization.

## Inputs / context to gather

1. Identify the effective runtime, writable source mirror, supplied canon, and state roots. Do not assume the runtime is a Git checkout.
2. Record the canon line count and SHA256, installed canon location/hash, BAGO version, and paths to relevant implementation/tests.
3. Confirm whether commands will write state. If yes, choose a temporary project and isolated `BAGO_STATE_ROOT` / `BAGO_USER_ROOT`.
4. Before any protected write or mirror sync, obtain the exact authorized file list and backup target.

## Procedure

1. Separate evidence surfaces: runtime, source mirror, mutable state, and client/distribution layout.
2. Compare canon text/hash with the installed canon and search for executable DTOs, integration points, and tests. Treat documentation or prompt names as non-evidence.
3. Run `python bago_core\cli.py validate`; run a focused no-cache pytest suite for the contracts in scope. Record full-suite failures separately when layout-dependent tests are present.
4. Report either certification evidence or the bounded verdict `CANON ABIERTO`; enumerate implemented, missing, and unverified areas without conflating them.
5. For an authorized phase, patch the smallest contract seam, preserve original request/provenance, and add focused regression coverage. Validate source/runtime behavior before synchronization.
6. If synchronization is authorized, create a backup outside the source tree, copy only the approved files, compare SHA256 per file, and rerun the focused validation in the target.

## Efficiency plan

1. Hash and inventory canon/runtime/source first; this quickly stops version-name assumptions.
2. Use focused suites to prove the bounded phase; do not spend the whole run chasing installed-distribution failures unrelated to its contract.
3. Cache the exact file list, hashes, validation totals, and unresolved canon gaps for the final verdict.
4. Stop after the approved phase and validation; a plan for later phases is not authorization to implement them.

## Pitfalls and fixes

- Symptom: diagnostics fail with `BAGO no puede utilizar una ruta protegida del sistema como proyecto` or `PermissionError`.
  - Cause: `C:\Program Files\BAGO` is being used as a writable project/state root.
  - Fix: run against a temporary project with isolated `BAGO_STATE_ROOT` and `BAGO_USER_ROOT`.
- Symptom: installed full pytest fails around missing monorepo/frontend/distribution paths.
  - Cause: installed layout differs from the test's expected checkout.
  - Fix: report it as layout/distribution failure and use an explicitly focused contract suite for the bounded assertion.
- Symptom: writes beneath `.bago/core` are denied.
  - Cause: TrustedInstaller ACL.
  - Fix: request limited UAC authorization; back up and synchronize only the explicitly approved files.
- Symptom: canon claims are inferred from names in prompts/docs.
  - Cause: documentation was treated as implementation evidence.
  - Fix: require executable contract code and tests before asserting coverage.

## Verification checklist

1. Runtime, source mirror, supplied canon, and state roots are explicit.
2. Canon comparison includes a hash/content distinction and an honest verdict.
3. Contract assertions are supported by code plus focused tests, not names alone.
4. State-writing diagnostics did not use the protected runtime as their project root.
5. Any protected change had explicit authorization, recoverable backup, exact file list, and post-copy SHA256 comparison.
6. The final report names what passed and the remaining gate required before certification.
