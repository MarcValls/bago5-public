from bago_spbe import (
    CapabilityCandidate, CapabilityRef, IntentRoot, ProceduralStepCandidate,
    Requirement, ResolutionMode, SemanticBasisRef, SemanticProceduralBehaviorEngine,
    SemanticTask,
)

intent = IntentRoot.create("intent-1", "Genera un informe reutilizando lo que ya existe")
req = Requirement("REQ-1", "provides", {"capability": "report.compose"}, hard=True)
ref = CapabilityRef("report.compose", "1", "local", "contract-fingerprint-1")
step = ProceduralStepCandidate(
    step_id="compose-report",
    operation_class="REPORT_COMPOSE",
    capability_ref=ref,
    semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),),
)
candidate = CapabilityCandidate(ref=ref, mode=ResolutionMode.REUSE, provides=frozenset({"report.compose"}), proposed_steps=(step,))
task = SemanticTask(
    task_id="task-1",
    intent_root=intent,
    objective="generar informe",
    requirements=(req,),
    candidates=(candidate,),
    completion_conditions=("report_ready",),
    semantic_artifact_ids=frozenset({"REQ-1"}),
)

engine = SemanticProceduralBehaviorEngine()
result = engine.compile(task)
print(result)
if result.kind.value == "PROPOSAL_READY":
    print(engine.to_pec_envelope(result))
