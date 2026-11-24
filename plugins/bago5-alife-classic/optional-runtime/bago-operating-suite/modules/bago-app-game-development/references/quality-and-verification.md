# Quality and verification

Apply checks proportional to the requested change and the repository's own instructions. Do not run every available check by default.

## Cross-cutting quality

- Correct primary user flow, useful loading/empty/error states, input validation, persistence, and failure recovery.
- Accessibility for the target: semantic controls, keyboard/controller navigation, focus, contrast, text scaling, captions/subtitles, and reduced-motion/audio options where applicable.
- Security and privacy: least privilege, safe parsing, scoped filesystem/network/process access, secret handling, dependency provenance, and redacted diagnostics.
- Performance on the named target. Measure before claiming latency, frame rate, memory, or startup improvements.
- Maintainability: follow local architecture and avoid adding dependencies or abstraction without a demonstrated need.

## Evidence ladder

Report the boundary actually checked:

- **Source inspected:** static reasoning only.
- **Focused check passed:** named test/lint/typecheck, tied to the checked candidate.
- **Build passed:** exact target bundle/package was produced.
- **Runtime observed:** exact artifact launched and relevant flow inspected.
- **Release validated:** explicit release criteria passed on the specified target; build success alone is insufficient.

For UI apps, inspect the rendered route or served bundle when the claim concerns the live UI. For games, inspect the exported build and play through the requested slice when claiming playable behavior. Preserve failed checks and `NOT_RUN` results; do not silently replace them with a broader green check.

## Package and release boundaries

Keep signing keys and credentials outside the package and logs. Do not publish, upload, submit to a store, create a release, or change a deployed environment unless the user authorized that specific effect. Include artifact identity, target platform, version, and verification scope in release notes when a package is produced.


## v1.1 integration

An added PASS must never compensate for an old mandatory property REGRESSED. Missing evidence is UNKNOWN and blocks GO. Update the skill itself under the same rule.

## BAGO-CDP-001 integration

For each new or materially changed capability, plan a reproducible demonstration route with the capability. Record the capability, preconditions, steps, observable behavior/output, expected result, evidence location, and limits in `plan.extensions.capability_demonstrations`. Keep the slice independently runnable or inspectable where practical; do not make its demonstration wait for completion of the full platform.

A visual interface is an observation surface, not proof by itself. Pair it with the narrowest relevant behavioral check and retained evidence. A passing check proves only its stated scope. Record failed and NOT_RUN checks, preserve previously verified capability properties, and state explicitly when a capability is `DEMONSTRABLE` without claiming the whole platform is complete or validated.
