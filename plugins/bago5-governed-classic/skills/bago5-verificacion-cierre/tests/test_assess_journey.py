"""Regresión sobre recibos ficticios. Estas pruebas no acceden a una web."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/assess_journey.py"
spec = importlib.util.spec_from_file_location("journey", SCRIPT)
journey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(journey)


def example(persistence=False):
    milestones = [
        ("portada", "visitor", "inicio", "page", "portada visible"),
        ("identidad", "member", "sesión de ensayo", "action", "identidad de prueba confirmada"),
        ("entrar", "member", "memoria de ensayo", "action", "memoria elegida abierta"),
        ("navegar", "member", "memoria de ensayo", "action", "segundo recuerdo visible en esa memoria"),
    ]
    if persistence:
        milestones.extend([
            ("guardar", "member", "recuerdo de ensayo", "write", "cambio de prueba guardado"),
            ("releer", "member", "recuerdo de ensayo", "reread", "valor guardado visible tras recargar"),
        ])
    plan = {"destination": "producción de ejemplo", "candidate": "candidata de ejemplo", "steps": []}
    receipts = []
    for key, role, resource, kind, expectation in milestones:
        step = {"step": key, "role": role, "resource": resource, "kind": kind, "expect": expectation}
        receipt = {"step": key, "id": "recibo-" + key, "destination": plan["destination"],
                   "candidate": plan["candidate"], "role": role, "resource": resource,
                   "operation": kind, "result": "PASS", "observed": expectation,
                   "evidence": "fuente de ensayo/" + key, "run": "recorrido de ensayo",
                   "mode": "live_http" if kind == "page" else "live_interaction"}
        if receipts:
            step["after"] = receipts[-1]["step"]
            receipt["previous_receipt"] = receipts[-1]["id"]
        if kind == "write":
            step["write_authorized"] = True
        plan["steps"].append(step)
        receipts.append(receipt)
    return plan, receipts


class JourneyReceiptTests(unittest.TestCase):
    def test_public_page_only_leaves_private_journey_open(self):
        plan, receipts = example()
        result = journey.assess(plan, receipts[:1])
        self.assertEqual(result["state"], "PARCIAL")
        self.assertEqual(result["unmet"], ["identidad", "entrar", "navegar"])

    def test_login_does_not_prove_entry_or_navigation(self):
        plan, receipts = example()
        self.assertEqual(journey.assess(plan, receipts[:2])["unmet"], ["entrar", "navegar"])
        self.assertEqual(journey.assess(plan, receipts[:3])["unmet"], ["navegar"])

    def test_private_steps_require_matching_live_context(self):
        plan, valid = example()
        for field, value in [("mode", "mock"), ("mode", "simulation"), ("mode", "live_http"),
                             ("destination", "local"), ("candidate", "otra"), ("operation", "page"),
                             ("role", "visitor"), ("resource", "otra memoria"), ("evidence", "")]:
            with self.subTest(field=field, value=value):
                receipts = deepcopy(valid)
                receipts[2][field] = value
                result = journey.assess(plan, receipts)
                self.assertEqual(result["state"], "PARCIAL")
                self.assertEqual(result["unmet"], ["entrar", "navegar"])

    def test_sequence_cannot_splice_visits(self):
        plan, valid = example()
        for field, value in [("run", "otra visita"), ("previous_receipt", "recibo-portada")]:
            with self.subTest(field=field):
                receipts = deepcopy(valid)
                receipts[-1][field] = value
                self.assertEqual(journey.assess(plan, receipts)["unmet"], ["navegar"])

    def test_wrong_result_fails_the_actual_milestone(self):
        plan, receipts = example()
        receipts[-1]["observed"] = "primer recuerdo aún visible"
        self.assertEqual(journey.assess(plan, receipts)["steps"]["navegar"]["state"], "FAIL")

    def test_read_only_journey_closes_without_writing(self):
        plan, receipts = example()
        result = journey.assess(plan, receipts)
        self.assertEqual(result["state"], "VERIFIED")
        self.assertEqual(result["scope"], "receipt_consistency_only")

    def test_persistence_requires_an_authorized_write_and_readback(self):
        plan, receipts = example(persistence=True)
        self.assertEqual(journey.assess(plan, receipts[:-1])["unmet"], ["releer"])
        self.assertEqual(journey.assess(plan, receipts)["unmet"], [])
        plan["steps"][-2]["write_authorized"] = False
        result = journey.assess(plan, receipts[:-2])
        self.assertEqual(result["steps"]["guardar"]["state"], "NOT_RUN")
        self.assertEqual(result["unmet"], ["guardar", "releer"])
        self.assertEqual(journey.assess(plan, receipts)["steps"]["guardar"]["state"], "OUT_OF_SCOPE")

    def test_missing_destination_evidence_blocks_global_closure(self):
        plan, receipts = example()
        for receipt in receipts:
            receipt["destination"] = "entorno de desarrollo"
        self.assertEqual(journey.assess(plan, receipts)["state"], "BLOQUEADO")
        self.assertEqual(journey.assess(plan, [])["state"], "BLOQUEADO")

    def test_ambiguous_reused_receipt_is_rejected(self):
        plan, receipts = example()
        receipts[1]["id"] = receipts[0]["id"]
        with self.assertRaises(ValueError):
            journey.assess(plan, receipts)


if __name__ == "__main__":
    unittest.main()
