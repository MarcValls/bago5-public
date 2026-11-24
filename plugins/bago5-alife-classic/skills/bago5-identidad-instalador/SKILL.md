---
name: bago5-identidad-instalador
description: "Corrige versiones e identidades desfasadas del instalador BAGO y las comprueba en una instalación temporal."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato de adaptacion GPT Classic

[Aplicar requisitos del procedimiento 4](../bago5/references/controles-especialistas.md#control-4).

# BAGO5os manifest installer repair

## When to use

Use when a BAGO5os package verifier recognizes the package candidate but `install.ps1` rejects it, or `BAGO_CLI.ps1` shows an older fixed version/candidate such as `1.4.5 - RELAY RC1`.

Do not use it to claim a real `CODEX_HOME` installation, publisher authenticity, or host integration from a temporary smoke test. For ordered payload inventory failures, compare package file ordering, hashes and provenance using the package verifier actually present; the historical portable-payload-identity helper is not bundled as a callable tool.

## Inputs / context to gather

1. Confirm the exact suite root, package `MANIFEST.json`, package ID, version, candidate, verifier, installer, and CLI/banner script.
2. Reproduce with `python -B verify_package.py --root .` and inspect the legacy identity checks/messages before editing.
3. Find the frozen-derivative approval/provenance mechanism and every manifest/hash pointer it requires.
4. Confirm a disposable installation root under `%TEMP%`; do not use `CODEX_HOME` for diagnosis.

## Procedure

1. Compare `MANIFEST.json`, any `PACKAGE_IDENTITY.json`, verifier output, `install.ps1`, and `BAGO_CLI.ps1`. Identify exact hard-coded legacy strings or exact-version checks.
2. Make the smallest manifest-driven repair: validate the expected package ID plus non-empty manifest version, and render installer/banner version/candidate text from manifest data.
3. In a frozen derivative, record each changed legacy file in the approved differential provenance (for example `modified_baseline_paths`), update the relevant provenance pointer hash (for example `lifecycle_update`), then update all affected `MANIFEST.json` hashes.
4. Run the focused package verifier. If it reports `legacy file altered outside approved scope`, stop editing code and repair the declared provenance scope/hashes.
5. Run `python -B verify_package.py --root .` again and retain version/candidate/file-count output.
6. Run the installer only into a unique temporary directory, for example `& .\install.ps1 -InstallPath (Join-Path $env:TEMP 'bago-installer-smoke')`; record exit code and success text.
7. Remove only the exact smoke directory after confirming it is the disposable target. State that persistent installation remains `NOT_RUN` unless it was explicitly authorized and verified.

## Efficiency plan

1. Start with manifest versus installer strings; this distinguishes stale identity from payload-integrity failures without broad test runs.
2. Treat verifier scope failures as provenance work, not failed logic repair.
3. Validate package integrity before any installation, then use one disposable install. Cache the exact package version/candidate and test destination for the receipt.

## Pitfalls and fixes

- Symptom: verifier accepts the package but installer rejects a newer release.
  - Likely cause: an exact legacy version comparison in `install.ps1`.
  - Fix: validate package ID plus non-empty manifest version; render messages from the manifest.
- Symptom: menu still displays an old candidate after installer repair.
  - Likely cause: `BAGO_CLI.ps1` has a fixed banner.
  - Fix: derive its version/candidate display from manifest data and include it in provenance/manifest updates.
- Symptom: `legacy file altered outside approved scope`.
  - Likely cause: changed files or lifecycle/provenance hash were not declared in the frozen derivative.
  - Fix: add every modified baseline path to approved provenance, update its pointer/hash and `MANIFEST.json`, then rerun the verifier.
- Symptom: a temporary smoke is described as an installed Codex suite.
  - Likely cause: the `%TEMP%` test target was conflated with `CODEX_HOME`.
  - Fix: explicitly state the temporary target was removed and live installation was not run.

## Verification checklist

1. Package ID, manifest version, and candidate match verifier output.
2. Installer validation/messages and CLI banner no longer contain fixed legacy identity where manifest data should be used.
3. All modified frozen-baseline files, provenance pointers, and manifest hashes are current.
4. `python -B verify_package.py --root .` passes.
5. A disposable temporary installation succeeds and its exit code is recorded.
6. `CODEX_HOME`/persistent installation and any untested host surfaces are explicitly scoped as `NOT_RUN`.
