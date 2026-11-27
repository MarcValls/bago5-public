# Capability development and demonstration - BAGO-CDP-001

## Principle

Building a capability and progressively demonstrating that it works are inseparable responsibilities. Demonstrability is designed with the capability, not postponed until the whole system is complete.

A capability must have a bounded, observable behavior and a reproducible route that allows a reviewer to inspect what it does, check its result, and consult the supporting evidence. It can be demonstrated independently of platform completion.

## Capability cycle

Use the cycle as a planning and evidence sequence, adapting steps that do not apply to a change:

**DEFINE -> BUILD -> INTEGRATE -> OBSERVE -> TEST -> VERIFY -> DEMONSTRATE -> PRESERVE**

The original Spanish labels are: **DEFINIR -> CONSTRUIR -> INTEGRAR -> OBSERVAR -> PROBAR -> VERIFICAR -> DEMOSTRAR -> CONSERVAR**.

1. **Define:** identify the user-visible capability, preconditions, expected behavior, failure conditions, boundaries, and acceptance criteria.
2. **Build:** implement the smallest useful slice that realizes that behavior.
3. **Integrate:** connect it to its real entry point, domain logic, persistence or service boundary as in scope.
4. **Observe:** provide an appropriate way to see decisions and outcomes, such as UI feedback, CLI output, state inspection, structured trace, or artifact. A visual interface alone is not proof.
5. **Test:** run the narrowest authorized behavioral check that exercises the capability and its relevant failure path. State what it does not cover.
6. **Verify:** bind evidence to the candidate and confirm the stated result at the relevant source, build, runtime, gameplay, or release boundary.
7. **Demonstrate:** provide reproducible steps and evidence so another person can observe the real behavior and check the result under stated conditions.
8. **Preserve:** compare prior protected properties and retain the demonstration recipe and evidence for future regression checks.

## Plan record

For material changes, record one entry per capability under `plan.extensions.capability_demonstrations` (the change-plan schema already permits extension data). Recommended shape:

```json
{
  "capability_id": "CAP-001",
  "state": "PROPOSED",
  "preconditions": ["..."],
  "steps": ["..."],
  "observable": "...",
  "expected_result": "...",
  "check_refs": ["..."],
  "evidence_refs": ["..."],
  "limits": ["..."]
}
```

Update the state and evidence as work progresses. Keep demonstration instructions and evidence in the change's evidence folder or a stable project location. Use fixed inputs/fixtures or record seeds and environment when they affect reproducibility. Do not claim that evidence exists before it is produced.

## State distinctions

- **PROPOSED:** described but not implemented.
- **IMPLEMENTED:** built and integrated to the stated boundary; this alone does not mean tested or verified.
- **VERIFIED:** the stated behavior passed checks supported by evidence tied to the candidate and explicit scope.
- **DEMONSTRABLE:** a reproducible route lets another person observe real behavior, check its result, and consult the evidence and limitations. This is a capability-level acceptance state, not a claim that the whole platform is complete.

These capability states supplement, and do not replace, BAGO task/action states such as `PREPARED`, `EXECUTED`, `VERIFIED`, and `VALIDATED`. In reports, state both dimensions when useful; never infer one from the other.

## Invariants

- INV-CDP-01: A capability can be demonstrated before the complete system is finished.
- INV-CDP-02: A visual interface alone is not a functional test.
- INV-CDP-03: A passing check proves only the behavior and boundary it covers.
- INV-CDP-04: New capabilities must not remove or degrade prior capabilities without an explicit, justified decision and the applicable authorization.
- INV-CDP-05: The demonstration route is designed with the capability.
- INV-CDP-06: Missing verification for one system area does not erase independently verified capabilities.

## Acceptance gate: DEMONSTRABLE

Mark a capability `DEMONSTRABLE` only when all applicable items hold:

- A reviewer can reproduce the route from documented preconditions and steps.
- The route exercises the real capability at the claimed boundary; mocks or simulations are labelled.
- Observable behavior and expected results are stated and can be checked.
- Candidate identity, environment/conditions, checks, evidence locations, and known limits are recorded.
- Evidence supports the exact claim; UI observation, test pass, build, runtime observation, and gameplay evidence are not treated as interchangeable.
- Previously protected capabilities were checked where the change could affect them.

If any item is unavailable, report the achieved state precisely (`IMPLEMENTED`, `VERIFIED`, or `NOT DEMONSTRATED`) and identify the missing evidence. One unverified subsystem does not invalidate independent capability demonstrations.


Esta operación necesita el motor local indicado, instalado y autorizado por separado en el equipo del usuario.
