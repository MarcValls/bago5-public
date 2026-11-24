---
name: bago5-sincronizacion-instalador
description: "Alinea cambios autorizados entre las fuentes, la instalación BAGO y los archivos de distribución."
---

[Aplicar ciclo de sesión](../bago5/references/controles-especialistas.md#control-1).

[Aplicar destino de la operación](../bago5/references/controles-especialistas.md#control-2).

## Contrato de adaptacion GPT Classic

[Aplicar requisitos del procedimiento 4](../bago5/references/controles-especialistas.md#control-4).

# bago-install-runtime-sync

## When to use

Use this skill for Windows BAGO installer or release-line work involving `install-v4.ps1`, `install-remote.ps1`, `bago install`, `bago uninstall`, `install_config.json`, `electron-viewer`, NSIS, or `C:\Program Files\BAGO`.

Do not use it for generic repo work that never touches the installed runtime or published installer assets.

## Inputs / context to gather

1. Identify the writable source or staging tree.
2. Confirm the installed runtime target, usually `C:\Program Files\BAGO`, and whether it is writable for this run.
3. Check the current release tag/asset and the version string inside `install-remote.ps1`.
4. Locate the relevant files: `install-v4.ps1`, `install-remote.ps1`, `bago_core\launcher.py`, the canonical installer scripts/NSIS file for the checkout, and any packaging tests.
5. Decide whether the issue is source-only, installed-runtime-only, or release drift across source, installed runtime, and published installer surfaces.

## Procedure

1. Verify the writable implementation target first.
   - Do not start editing `C:\Program Files\BAGO` unless you have confirmed it is writable for this run.
   - If `Program Files` is blocked, move immediately to the staging or source tree.
2. Patch the source tree.
   - Make the code or script changes in the writable source.
   - For installer noise, check both `install-v4.ps1` and `launcher.py --test`.
   - For install/uninstall failures, inspect `cmd_install`, `cmd_uninstall`, same-path handling, and any elevation/delete helpers.
3. Validate in source before redeploy.
   - Run lightweight syntax validation such as `python -m py_compile bago_core\launcher.py` when relevant.
   - Run `python bago_core\launcher.py --test`.
   - If the change touches version, claims, or installer/runtime alignment, run the checkout's relevant release/security tests before redeploy.
   - Run a temporary install from the patched source into a non-privileged temp directory and inspect the output.
   - For `install-embedded-payload.ps1`, run the rollback contracts under the same `powershell.exe` used by tests. Validate ZIP structure and required `BAGO.exe` before moving/removing the current target; preserve `.BAGO-rollback` until explicit finalization. Use .NET `System.Security.Cryptography.SHA256` stream hashing when PowerShell 5.1 compatibility is required.
4. Redeploy to the installed runtime.
   - Reinstall or copy into `C:\Program Files\BAGO` as needed, with admin rights for `Program Files`.
   - Treat source validation and Program Files deployment as separate checkpoints.
5. Validate the real runtimes.
   - Re-run the failing installed command from the real installed path.
   - Prefer direct checks such as `bago install --dry-run`, `bago install --skip-tests`, `bago uninstall --dry-run`, `python bago_core\cli.py validate`, and `bago exec /doctor`.
   - If runtime behavior still looks old, compare file hashes or timestamps before assuming the patch landed.
6. Sync the release line if the change affects installers or public claims.
   - Update `install-remote.ps1` when the release tag or asset name changes.
   - Build or inspect the ZIP and confirm that uninstall scripts are present while `install_config.json`, `.bago/config.json`, and credentials are absent.
   - If a release was superseded during validation, propose exact stale intermediate tags/releases for removal after verifying the final line; execute removal only within explicitly authorized scope.
7. For Electron/NSIS installer changes, prove the packaged payload is current.
   - Run `node --check electron-viewer/main.cjs`, validate the PowerShell script parses, then build with `npm install --no-fund --no-audit`, `npm run build`, and `npm run dist --workspace electron-viewer` as applicable.
   - Make the release workflow replace `compiled/electron-viewer` from that checkout-built distribution before NSIS assembly; never reuse a published ZIP as proof that the payload includes the source fix.
   - Smoke the installed `BAGO.exe` from a cold start and record process health/exit behavior. A tag-only E2E job skipped on `main` is not equivalent to a real installer E2E pass.
   - For a manager/Electron smoke, target the packaged `win-unpacked` runtime with `BAGO_MANAGER_EXE`; do not use the NSIS setup wizard as the manager target.
8. If this is audit/release closure, bind evidence to the final candidate.
   - Re-run and record all required gates after every commit/SHA change; earlier candidate-bound receipts are stale.
   - Confirm clean-worktree identity is non-empty and stable (never the empty-string SHA-256 `e3b0c442...`).
   - Before tag/release, run the exact version-consistency check across installer scripts, NSIS, root/frontend/Electron/backend/UI metadata, generated version, and distribution ZIP.
   - Derive final commit, tag, PR, and asset digests directly from Git and GitHub, not manually typed handoff metadata.

## Efficiency plan

1. Separate the three surfaces early: writable source, installed runtime, published release.
2. Reproduce in the installed runtime, but implement in the writable tree.
3. Cache the exact failing command plus the exact validated source, active-runtime, and Program Files checks so you can compare pre/post behavior quickly.
4. Use ZIP inspection and `install-remote.ps1` string checks before doing broader release cleanup.
5. Stop once source validation, installed-runtime validation, and release/installer sync all agree.

## Pitfalls and fixes

- Symptom: `PermissionError` or `Access denied` under `C:\Program Files\BAGO`.
  - Likely cause: install-root ACLs/UAC.
  - Fix: validate in staging first, then redeploy with elevation and re-check the installed runtime separately.
- Symptom: `SourceRoot and InstallDir cannot be the same path`.
  - Likely cause: installed CLI is trying to install over itself.
  - Fix: route same-path installs into repair mode and verify `bago install --dry-run` shows `Modo: repair`.
- Symptom: installer code works on one machine but fails on older PowerShell.
  - Likely cause: PowerShell 5.1 compatibility gaps.
  - Fix: avoid raw `GetRelativePath`, wrap `Get-ChildItem` in `@(...)`, and use `.Contains()` with `OrderedDictionary` in this script context.
- Symptom: install succeeds but prints a wall of internal test output.
  - Likely cause: `install-v4.ps1` and `launcher.py --test` are both writing uncaptured stdout/stderr.
  - Fix: capture output in both places and print the details only on failure.
- Symptom: repo, installed runtime, and remote installer disagree on the active version.
  - Likely cause: release tag changed without updating `install-remote.ps1` or reinstalling the runtime.
  - Fix: sync the tag, asset name, remote installer string, and installed runtime in one pass.
- Symptom: release asset hash is correct but installed `BAGO.exe` still fails on cold start.
  - Likely cause: NSIS packaged an older Electron payload from a previously published ZIP.
  - Fix: rebuild Electron from the checkout, explicitly replace `compiled/electron-viewer`, then smoke the installed binary; do not rely on asset existence, hash, or a skipped non-tag E2E job.
- Symptom: rollback test fails only in CI or `powershell.exe`.
  - Likely cause: the script removes the target before validating the ZIP, or uses `Get-FileHash`/single-line `Get-Content` behavior not supported by the test host.
  - Fix: validate ZIP and `BAGO.exe` first, use .NET stream SHA256, and read a one-line sidecar with `[System.IO.File]::ReadAllText()` before parsing.
- Symptom: a release closes with passing gates from an earlier commit.
  - Likely cause: candidate-bound evidence was not regenerated after a SHA/version change.
  - Fix: re-record the full required gate set on the final SHA and verify receipt identity/fingerprint before tagging.

## Verification checklist

1. The writable source tree and installed runtime path are explicitly identified.
2. The patch is validated in source before redeploy.
3. The installed runtime is re-tested from the real installed path.
4. If runtime deployment was attempted, there is evidence it actually landed or explicit evidence it did not for the installed target.
5. `install-remote.ps1`, the release tag, and the release asset name match when installer distribution is involved.
6. ZIP/package inspection confirms uninstall scripts are included and per-install config/secrets are excluded.
7. When audit closure is in scope, every required receipt is fresh for the final candidate SHA and carries a valid non-empty worktree fingerprint.
