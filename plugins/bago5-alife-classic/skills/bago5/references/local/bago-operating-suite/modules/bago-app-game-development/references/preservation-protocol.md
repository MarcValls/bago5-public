# v1.1 Project baseline → change → differential verification

1. Identify project / scope / current host read authorization. Do not infer permission from a path.
2. Capture immutable scoped `baseline.json` outside the project using `scripts/project_baseline.py`.
   Scope globs must explicitly include source and test files. Input capability descriptors
   must separate DECLARED / OBSERVED / VERIFIED and have real baseline evidence for VERIFIED.
3. Define `plan.json` per `schemas/change_plan.schema.json` BEFORE implementation.
   Include all mandatory baseline properties unless a scoped approval applies; list
   acceptance tests for every new feature and old protected property.
4. Implement only the user-authorized change. Obtain explicit host permission before
   `run_checks.py` executes project commands; never use self-proclaimed permission.
5. Run listed checks, retaining every command result + hash in a NEW evidence folder.
6. Differential-verifier recomputes the candidate fingerprint; refuses mismatched
   baseline IDs, missing mandatory tests, invalid evidence and untrusted approvals.
7. Outcome GO / NO_GO / INCONCLUSIVE always limited to tests and platform actually run.
   NEVER imply successful build = runtime or screenshot = functional correctness.
8. Any sanctioned removal requires signed EXTERNAL_HOST attestation in
   `scripts/verify_change.py` with an externally controlled Ed25519 public key.
   Without optional `cryptography` support, approval is rejected (fail closed).
   The signer/key origin and host permission are out of scope of the skill.
9. Candidate baseline replacement, rollback/destructive operations and publishing are
   separate user-authorized tasks; verifier never performs them.

Example (replace paths and command lists; check user permissions first):

```powershell
$skill = Join-Path $env:CODEX_HOME 'skills\bago-app-game-development'
python "$skill\scripts\project_inventory.py" --root 'PATH'
python "$skill\scripts\project_baseline.py" --root 'PATH' --project-id PROJ --baseline-id BASE --include 'src/**' --include 'tests/**' --target 'source:local' --output 'evidence\baseline.json'
# Create plan.json and commands.json explicitly; then after the change:
python "$skill\scripts\run_checks.py" --root 'PATH' --baseline 'evidence\baseline.json' --plan plan.json --commands commands.json --evidence-dir 'evidence\checks'
python "$skill\scripts\verify_change.py" --root 'PATH' --baseline 'evidence\baseline.json' --plan plan.json --checks 'evidence\checks\checks.json' --evidence-dir 'evidence\checks' --baseline-evidence-dir 'evidence\before' --output 'evidence\report.json'
```

The three JSON Schemas are distributed under `schemas/`. Scripts use Python stdlib;
optional cryptography is needed ONLY to validate externally signed exceptions.
Run output and baseline output paths MUST be outside the inspected project scope.

## Optional Playwright (real browser required)

For a web UI property, capture a *pre-change* screenshot using the existing
Playwright project suite and keep it immutable. Run
`scripts/playwright_check.py --url http://localhost:PORT --input-selector '#text-input' --container-selector '#message-box' --baseline-png evidence/before.png --capture-png evidence/after.png`
when the browser, fixed data and environment are available. By design this
checks only the specified DOM/input scenario and screenshot against its exact
rendering context. Record browser version and stable data separately. Do not
use image differences alone to prove functional preservation. If it cannot run,
record NOT_RUN; no implicit dependency installation.

## BAGO-CDP-001 preservation addition

Before a material change, list each new capability's reproducible demonstration route in `plan.extensions.capability_demonstrations`, including preconditions, steps, observable, expected result, evidence, and limitations. Add existing verified capabilities to preservation properties when the change could affect them. After implementation, run only authorized checks and observe the exact demonstration route; retain separate check and observation evidence. A new PASS cannot compensate for a regressed prior property. Missing route evidence leaves the capability NOT DEMONSTRATED; it does not invalidate independently verified capabilities.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
