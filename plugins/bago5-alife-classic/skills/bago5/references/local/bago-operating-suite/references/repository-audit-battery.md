# Hybrid repository audit battery

Use this workflow when the user requests a repository audit for orphaned or
duplicate files, code/documentation contradictions, conflicting requirements,
or language that blocks implementation. Bind the audit to the selected
repository and its own instructions before scanning.

## Combine deterministic scripts with model review

1. **Run applicable static checks.** Use repository-native tests, inventories,
   hashes, import/reference searches, AST or token similarity tools when
   available. For a BAGO backend repository, if the user-provided auditor is
   present at `C:\Program Files\BAGO\tools\audit_orphans_and_duplicates.py`,
   run it against the backend root, for example:

   ```powershell
   python "<suite-skill>\runtime\BAGO-4.11.10\backend\tools\audit_orphans_and_duplicates.py" --root "<BAGO-repo>\backend" --json
   ```

   This particular script classifies tools as wired/support-only/orphan
   candidates and checks the `manager/` mirror. It does not detect all source
   duplicates, semantic contradictions, or linguistic blockers. Use it only
   with a BAGO-shaped backend root; do not point it at an arbitrary project.

2. **Review meaning across artifacts.** Compare the authoritative requirement
   or decision with code, tests, config, prompts, and docs. Look for opposing
   obligations, scope or permission mismatches, undefined pronouns/referents,
   unresolved placeholders, missing owners/deadlines/acceptance conditions,
   and circular or mutually exclusive instructions. Treat model findings as
   candidates that need source evidence.

3. **Keep the evidence streams distinct.** For every finding, record category,
   exact file and line, short source excerpt, detector (`script` or `model`),
   why it may block work, confidence, and a concrete verification step. A
   script result is limited to its implemented checks. A model review is
   interpretive, may miss issues, and does not establish project authority.

4. **Include clean controls and false-positive review.** Search for a clear,
   consistent neighboring case before concluding that a finding is real.
   Report suspected conflicts as unresolved when authority or intended scope
   cannot be established. Do not delete, rewrite, or resolve findings unless
   the user requested that action and project authority supports it.

## Scenario battery

Use these synthetic cases to check that the combined workflow catches distinct
failure types without treating every similarity as a defect:

| Case | Input pattern | Expected behavior |
|---|---|---|
| Duplicate source | Two functions have identical bodies under different names or paths. | Static hash/token/AST checks identify the pair and cite both paths; model may explain likely relationship but does not declare either safe to delete. |
| Consistent mirror | A generated copy matches its declared source. | Static comparison reports equality; no duplicate defect is inferred from the pair alone. |
| Requirement conflict | A policy says `guest users must export` while code or another current rule says `guest users must not export`. | Script evidence locates both statements when supported; model explains the incompatible scope/action and marks authority unresolved if precedence is unknown. |
| Language blocker | `Move it there after that` has no clear referents, or a requirement says `improve sync` without scope or acceptance criteria. | Model flags the exact wording and identifies what information blocks implementation; do not invent the missing decision. |
| Explicit placeholder | A current instruction contains `TODO`, `TBD`, or an undefined owner/metric. | Static search finds the marker; model classifies its impact and quotes the source. |
| Clean control | Similar names or adjacent requirements have different purposes and no conflict. | Report no defect, or label a similarity as informational with the reason it is not a contradiction. |

In the final report, separate deterministic findings, model candidates, false
positives rejected, and checks not run. Never present the battery as exhaustive
proof that a repository has no duplicates, contradictions, or language blocks.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
