# BAGO5os pytest checkpoint companion — candidate 1.4.4

## Function and explicit execution

An **opt-in** Python/pytest 9.x companion, ported from the ADL v0.1 candidate.
Each test is committed to a SQLite ledger **only once its setup, call and teardown
reports are available**. Only the last **PASSED** result of each node ID is reused
on resume; failed/skipped/incomplete cases run again. Metadata binds root,
selected arguments, the complete collection, Git-tracked and visible untracked
workspace files, installed distribution versions, Python/pytest versions,
interpreter location, the **plugin's own SHA-256**, and a caller-supplied external
fixture identity. Any mismatch rejects the resume rather than reusing stale PASS.

From the **installed** skill (path `INSTALACION`):

```sh
python -B INSTALACION/scripts/suite_orchestrator.py pytest-checkpoint doctor
python -B INSTALACION/scripts/suite_orchestrator.py pytest-checkpoint run --workspace RUTA_REPO --checkpoint RUTA_REPO/.pytest_cache/bago.sqlite3 --evidence EVIDENCIA_NUEVA_1 -- tests -q
# After an interruption, with unchanged project/tests/dependencies/selector/context:
python -B INSTALACION/scripts/suite_orchestrator.py pytest-checkpoint status --checkpoint RUTA_REPO/.pytest_cache/bago.sqlite3
python -B INSTALACION/scripts/suite_orchestrator.py pytest-checkpoint resume --workspace RUTA_REPO --checkpoint RUTA_REPO/.pytest_cache/bago.sqlite3 --evidence EVIDENCIA_NUEVA_2 -- tests -q
```

Python 3.11+, `pytest` and Git must already exist in the Python/host selected.
The suite does **not** install them; use the same interpreter and unchanged
selection on run/resume. Use `--context ID` on both invocations for externally
managed datasets, services or environment fixtures and change it whenever the
external inputs change. This must be done by the caller; the plugin cannot
inspect those systems. Evidence directories are exclusive/new and outside the
workspace and installed skill.

When operating under a governed mission, call `task run-check` with the **exact
command** and a valid host permission, then verify and consume the process
receipt; a checkpoint is not itself a mission/handoff receipt. Do not treat
it as a replacement for `suite_control`'s STOP/RESUME or for ADL `teamctl`.

## Independent demonstration (BAGO-CDP-001)

```sh
python -B INSTALACION/scripts/suite_orchestrator.py pytest-checkpoint demo --output EVIDENCIA_DEMO_NUEVA
```

The demo creates temporary Git fixtures and invokes **9 real subprocess tests**
that cover hard process termination between cases, resume, stale source/selector/
context refusal, teardown failure, skipped test, lock collision and collection
error. It saves `stdout.log`, `stderr.log`, and `result.json` with hashes under
`EVIDENCIA_DEMO_NUEVA`. The reproduction needs only the installed skill, Python,
pytest and Git; ADL or a complete frontend are not required.

## Material limits

- Checkpoints store **completed test case results**, not the stack, fixture
  state, database snapshot or process memory; an interrupted test restarts.
- A killed test may have executed side effects before its final teardown. There
  is **no exactly-once guarantee**; tests must own cleanup or idempotence.
- No implicit execution or authorization. Calling tests launches project Python
  code with the caller's permissions. This is **not an OS sandbox**.
- Local SQLite integrity is not identity authentication. Data/inputs outside
  visible Git files and Python distributions (ignored files, services, secrets,
  hardware, environment variables) require an explicit external context ID and
  cannot be automatically verified.
- Supports only **sequential** pytest. Not xdist, parallel agents writing one
  ledger, cross-machine/changed-interpreter resumption, or combination with
  `--lf`, `--ff`, `--sw`, and cache clearing.
- This capability is for pytest execution, not a long-cycle autonomous agent
  scheduler or collaborative handoff orchestrator.
- The synthetic demo cannot establish Windows/NTFS, live ADL integration,
  reliable power-loss recovery, system-wide regression freedom, or production
  performance. Keep these as `NOT_RUN` until exercised in the actual host.

## Conservation

Existing Suite `task`, `cognitive`, `spiral`, `adaptation`, `editorial`, source
packs and runtime are kept distinct. The default `python -m pytest tests -q`
in ADL stays unchanged. Only explicit `pytest-checkpoint run`/`resume` or
`-p scripts.pytest_checkpoint` invocation engages the companion.
