import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bago_spbe import (  # noqa:E402
    BindingDecision, BoundResource, CapabilityCandidate, CapabilityRef,
    DependencyEdge, Eligibility, IntentRoot, ProceduralStepCandidate,
    ProposalReady, Requirement, ResolutionMode, SemanticBasisRef,
    SemanticCompilationKind, SemanticEntity, SemanticProceduralBehaviorEngine,
    SemanticTask, SemanticTerminalOutcome, Terminal, UncertaintyAssessment,
    UncertaintyDisposition, UncertaintyState,
)


def cref(name, fp=None):
    return CapabilityRef(name, "1", "local", fp or f"fp-{name}")


def base_task(candidates, requirements=None, **kwargs):
    intent = IntentRoot.create("intent-1", "haz la tarea")
    return SemanticTask(
        task_id="task-1",
        intent_root=intent,
        objective="hacer tarea",
        requirements=tuple(requirements or ()),
        candidates=tuple(candidates),
        completion_conditions=("done",),
        semantic_artifact_ids=frozenset({"REQ-1", "REQ-2"}),
        **kwargs,
    )


class SPBETests(unittest.TestCase):
    def setUp(self):
        self.engine = SemanticProceduralBehaviorEngine()

    def test_happy_path_proposal_and_pec_envelope(self):
        ref = cref("report")
        req = Requirement("REQ-1", "provides", {"capability": "report"})
        step = ProceduralStepCandidate("s1", "REPORT", ref, semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),))
        cand = CapabilityCandidate(ref, ResolutionMode.REUSE, frozenset({"report"}), proposed_steps=(step,))
        result = self.engine.compile(base_task([cand], [req]))
        self.assertIsInstance(result, ProposalReady)
        envelope = self.engine.to_pec_envelope(result)
        self.assertEqual(envelope["kind"], "SPBEtoPECEnvelope")

    def test_not_eligible_never_selected(self):
        req = Requirement("REQ-1", "provides", {"capability": "needed"})
        bad = CapabilityCandidate(cref("bad"), ResolutionMode.REUSE, frozenset({"other"}))
        good_ref = cref("good")
        good_step = ProceduralStepCandidate("s", "X", good_ref, semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),))
        good = CapabilityCandidate(good_ref, ResolutionMode.NEW, frozenset({"needed"}), proposed_steps=(good_step,))
        result = self.engine.compile(base_task([bad, good], [req]))
        self.assertIsInstance(result, ProposalReady)
        self.assertEqual(result.proposal.capability_refs[0], good_ref)

    def test_material_quality_can_override_reuse(self):
        req = Requirement("REQ-1", "provides", {"capability": "needed"})
        reuse_ref = cref("reuse")
        reuse_step = ProceduralStepCandidate("r", "X", reuse_ref, semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),))
        reuse = CapabilityCandidate(reuse_ref, ResolutionMode.REUSE, frozenset({"needed"}), semantic_loss=10, proposed_steps=(reuse_step,))
        new_ref = cref("new")
        new_step = ProceduralStepCandidate("n", "X", new_ref, semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),))
        new = CapabilityCandidate(new_ref, ResolutionMode.NEW, frozenset({"needed"}), semantic_loss=0, proposed_steps=(new_step,))
        result = self.engine.compile(base_task([reuse, new], [req]))
        self.assertEqual(result.proposal.capability_refs[0], new_ref)
        self.assertTrue(result.proposal.resolution_decision.override_of_default_preference)

    def test_ambiguous_binding_terminal(self):
        entity = SemanticEntity("E1", "file", ("config",), True)
        from bago_spbe import ResourceBindingAttempt
        attempt = ResourceBindingAttempt("B1", "E1", BindingDecision.AMBIGUOUS, ("a", "b"))
        result = self.engine.compile(base_task([], entities=(entity,), binding_attempts=(attempt,)))
        self.assertIsInstance(result, Terminal)
        self.assertEqual(result.terminal_result.outcome, SemanticTerminalOutcome.INSUFFICIENT_INFORMATION)
        with self.assertRaises(ValueError):
            self.engine.to_pec_envelope(result)

    def test_blocking_uncertainty_terminal(self):
        u = UncertaintyAssessment("U1", "REQ-1", UncertaintyState.BLOCKING, UncertaintyDisposition.BLOCK_SEMANTIC_COMPILATION)
        result = self.engine.compile(base_task([], uncertainties=(u,)))
        self.assertIsInstance(result, Terminal)
        self.assertEqual(result.terminal_result.outcome, SemanticTerminalOutcome.INSUFFICIENT_INFORMATION)

    def test_invalid_cycle_terminal(self):
        edges = (DependencyEdge("A", "B"), DependencyEdge("B", "A"))
        result = self.engine.compile(base_task([], dependency_edges=edges))
        self.assertIsInstance(result, Terminal)
        self.assertEqual(result.terminal_result.outcome, SemanticTerminalOutcome.SEMANTICALLY_UNSATISFIABLE)

    def test_orphan_step_terminal(self):
        ref = cref("report")
        req = Requirement("REQ-1", "provides", {"capability": "report"})
        step = ProceduralStepCandidate("s1", "REPORT", ref, semantic_basis=())
        cand = CapabilityCandidate(ref, ResolutionMode.REUSE, frozenset({"report"}), proposed_steps=(step,))
        result = self.engine.compile(base_task([cand], [req]))
        self.assertIsInstance(result, Terminal)
        self.assertEqual(result.terminal_result.outcome, SemanticTerminalOutcome.SEMANTICALLY_UNSATISFIABLE)

    def test_terminal_enum_excludes_proposal_ready(self):
        self.assertNotIn("PROPOSAL_READY", {x.value for x in SemanticTerminalOutcome})

    def test_bound_resource_does_not_set_authorization(self):
        entity = SemanticEntity("E1", "file", ("config",), True)
        from bago_spbe import ResourceBindingAttempt
        attempt = ResourceBindingAttempt("B1", "E1", BindingDecision.BOUND, ("config.json",), ("observed",))
        bound = BoundResource("BR1", "E1", "file", "config.json", "filesystem", "B1", ("observed",))
        result = self.engine.compile(base_task([], entities=(entity,), binding_attempts=(attempt,), bound_resources=(bound,)))
        self.assertIsInstance(result, Terminal)  # no eligible solution, but not authorization failure
        self.assertEqual(result.terminal_result.outcome, SemanticTerminalOutcome.NO_ELIGIBLE_SOLUTION)

    def test_pipeline_preserves_intent_root_and_compiles(self):
        from bago_spbe import SPBEPipeline, IdentityNormalizer, StaticCapabilityDiscovery, NoopResourceBinder, SemanticInterpretation
        ref = cref("report")
        req = Requirement("REQ-1", "provides", {"capability": "report"})
        step = ProceduralStepCandidate("s1", "REPORT", ref, semantic_basis=(SemanticBasisRef("REQUIREMENT_REF", "REQ-1", "SATISFIES"),))
        cand = CapabilityCandidate(ref, ResolutionMode.REUSE, frozenset({"report"}), proposed_steps=(step,))
        class Interpreter:
            def interpret(self, intent_root):
                return SemanticInterpretation(
                    intent_root=intent_root, objective="report", requirements=(req,),
                    completion_conditions=("done",), semantic_artifact_ids=frozenset({"REQ-1"})
                )
        pipe = SPBEPipeline(Interpreter(), IdentityNormalizer(), StaticCapabilityDiscovery((cand,)), NoopResourceBinder(), self.engine)
        result = pipe.compile_request("haz un informe", intent_id="intent-pipeline")
        self.assertIsInstance(result, ProposalReady)
        self.assertEqual(result.proposal.intent_root_ref, "intent-pipeline")


if __name__ == "__main__":
    unittest.main()
