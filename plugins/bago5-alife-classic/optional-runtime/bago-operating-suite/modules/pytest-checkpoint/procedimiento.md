# Pytest checkpoint companion (opt-in)

Use only for explicitly requested Python test execution/recovery. A checkpoint is an
execution-result cache, not permission, process continuation, a verified release
or an agent handoff. For governed work, invoke the CLI via the host-authorized
`task run-check` path, retain its receipt, and consume evidence separately.

Entry: `scripts/suite_orchestrator.py pytest-checkpoint {doctor,status,run,resume,demo}`.
The installed `scripts/pytest_checkpoint.py` is also a normal pytest plugin.
Read [README.md](README.md) before using it with a real workspace.

The independent demonstration route is `pytest-checkpoint demo --output NEW_FOLDER`.
A sandboxed/synthetic PASS is not a LIVE ADL/Windows PASS. No tests are started
by installation, by `status` or by `doctor`.
