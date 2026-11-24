#!/usr/bin/env python3
"""Decision and negative cases for declared phase preflight evidence."""
import copy
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "phase_preflight.py"
SPEC = importlib.util.spec_from_file_location("bago5_phase_preflight_test", SCRIPT)
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)
NOW = dt.datetime(2026, 11, 20, 12, 0, tzinfo=dt.timezone.utc)


def sample(now=NOW):
    context = {
        "project_id": "project:sample", "goal_id": "goal:1", "plan_id": "plan:1", "plan_version": "3",
        "phase_id": "phase:2", "phase_revision": "1", "session_id": "session:1", "host": "CODEX",
        "environment": "test", "candidate_ref": "source:revision-1", "scope_ref": "scope:1",
        "acceptance_ref": "acceptance:1", "attempt_id": "attempt:1",
    }
    stamp = now.isoformat()
    key = PREFLIGHT.context_key(context)
    areas = sorted(PREFLIGHT.AREAS)
    return {
        "schema_version": "bago5.phase-preflight.v1", "context": context, "captured_at": stamp,
        "max_age_seconds": 900, "stop": False,
        "requirements": [{"id": area, "area": area, "description": "Required " + area} for area in areas],
        "observations": [{"requirement_id": area, "status": "PASS", "source_ref": "observed:" + area,
                          "source_type": "USER_INSTRUCTION" if area == "authorization" else "HOST_TOOL",
                          "captured_at": stamp, "context_key": key, "detail": "Read-only capability check"} for area in areas],
        "environment_change": {"required": False}, "user_interventions": [],
        "required_target_actions": [], "target_preflights": [],
    }


def observation(receipt, area):
    return next(item for item in receipt["observations"] if item["requirement_id"] == area)


def pending_user(receipt):
    receipt["user_interventions"] = [{
        "id": "manual:1", "status": "PENDING", "stage": "BEFORE_COMPLETION", "who": "usuario", "action": "Confirmar publicación",
        "when": "al cerrar la fase", "reason": "La publicación contratada requiere confirmación manual",
    }]


def preparation(receipt):
    receipt["preparation"] = {
        "steps": ["Crear candidata local revisable", "Ejecutar pruebas y mostrar diff"],
        "authorization_ref": "observed:authorization", "authorization_source_type": "USER_INSTRUCTION",
        "notice_ref": "conversation:notice-before-work", "context_key": PREFLIGHT.context_key(receipt["context"]),
    }


class PhasePreflightTests(unittest.TestCase):
    def assess(self, receipt, current=None):
        return PREFLIGHT.assess(receipt, receipt["context"] if current is None and isinstance(receipt, dict) and "context" in receipt else current, now=NOW)

    def test_complete_phase_can_proceed_without_another_confirmation(self):
        actual = self.assess(sample())
        self.assertEqual(actual["decision"], "GO")
        self.assertTrue(actual["can_start"])
        self.assertIn("no host probe", actual["limit"])

    def test_can_edit_but_cannot_verify_does_not_start(self):
        data = sample()
        observation(data, "verification").update(status="FAIL", detail="Runtime de pruebas ausente")
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_unverified_delivery_does_not_start(self):
        data = sample()
        observation(data, "delivery")["status"] = "NO_COMPROBADO"
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_pending_human_at_the_end_requires_user_now(self):
        data = sample()
        pending_user(data)
        actual = self.assess(data)
        self.assertEqual(actual["decision"], "REQUIERE_USUARIO")
        self.assertFalse(actual["can_start"])
        self.assertFalse(actual["can_prepare"])
        self.assertEqual(actual["pending_interventions"][0]["when"], "al cerrar la fase")

    def test_announced_final_acceptance_allows_authorized_preparation_without_go(self):
        data = sample()
        pending_user(data)
        preparation(data)
        actual = self.assess(data)
        self.assertEqual(actual["decision"], "REQUIERE_USUARIO")
        self.assertFalse(actual["can_start"])
        self.assertTrue(actual["can_prepare"])
        self.assertEqual(actual["preparation_steps"], data["preparation"]["steps"])
        self.assertEqual(actual["pending_interventions"][0]["status"], "PENDING")

    def test_before_start_intervention_never_allows_preparation(self):
        data = sample()
        pending_user(data)
        preparation(data)
        data["user_interventions"][0]["stage"] = "BEFORE_START"
        actual = self.assess(data)
        self.assertEqual(actual["decision"], "REQUIERE_USUARIO")
        self.assertFalse(actual["can_prepare"])
        self.assertEqual(actual["preparation_steps"], [])

    def test_pending_action_cannot_be_listed_as_allowed_preparation(self):
        for step in ("Confirmar publicación", "  CONFIRMAR   PUBLICACIÓN. ", "confirmar publicacio\u0301n"):
            with self.subTest(step=step):
                data = sample()
                pending_user(data)
                preparation(data)
                data["preparation"]["steps"].append(step)
                actual = self.assess(data)
                self.assertEqual(actual["decision"], "REQUIERE_USUARIO")
                self.assertFalse(actual["can_start"])
                self.assertFalse(actual["can_prepare"])
                self.assertEqual(actual["preparation_steps"], [])
                self.assertIn("preparation_contains_pending_intervention", actual["preparation_reasons"])

    def test_preparation_without_notice_or_verified_authorization_is_not_allowed(self):
        data = sample()
        pending_user(data)
        preparation(data)
        del data["preparation"]["notice_ref"]
        self.assertFalse(self.assess(data)["can_prepare"])
        preparation(data)
        data["preparation"]["authorization_ref"] = "unverified:grant"
        self.assertFalse(self.assess(data)["can_prepare"])
        preparation(data)
        data["preparation"]["context_key"] = "0" * 64
        self.assertFalse(self.assess(data)["can_prepare"])

    def test_preparation_requires_all_areas_current_and_no_failure(self):
        for area in PREFLIGHT.AREAS:
            for status in ("FAIL", "NO_COMPROBADO"):
                with self.subTest(area=area, status=status):
                    data = sample()
                    pending_user(data)
                    preparation(data)
                    observation(data, area)["status"] = status
                    self.assertFalse(self.assess(data)["can_prepare"])
        data = sample()
        pending_user(data)
        preparation(data)
        observation(data, "tools")["captured_at"] = (NOW - dt.timedelta(hours=1)).isoformat()
        self.assertFalse(self.assess(data)["can_prepare"])

    def test_preparation_never_bypasses_stop_host_change_or_missing_target(self):
        data = sample()
        pending_user(data)
        preparation(data)
        data["stop"] = True
        self.assertFalse(self.assess(data)["can_prepare"])
        data["stop"] = False
        data["environment_change"] = {"required": True, "destination": "WORK", "reason": "Falta navegador", "handoff_ref": "conversation:handoff"}
        self.assertFalse(self.assess(data)["can_prepare"])
        data["environment_change"] = {"required": False}
        data["required_target_actions"] = [{"action_id": "action:publish", "target_id": "target:1", "environment": "test"}]
        self.assertFalse(self.assess(data)["can_prepare"])

    def test_memory_history_or_instruction_cannot_prove_capabilities(self):
        for source in ("MEMORY", "HISTORY", "USER_INSTRUCTION", "EXPLICIT_APPROVAL"):
            data = sample()
            observation(data, "access")["source_type"] = source
            self.assertNotEqual(self.assess(data)["decision"], "GO")
        for source in ("SOURCE_READ", "HOST_TOOL", "AUTHENTICATED_ACCESS", "TARGET_PROBE", "MEMORY"):
            data = sample()
            observation(data, "authorization")["source_type"] = source
            self.assertNotEqual(self.assess(data)["decision"], "GO")
            pending_user(data)
            preparation(data)
            self.assertFalse(self.assess(data)["can_prepare"])

    def test_user_available_does_not_count_as_completed_action(self):
        data = sample()
        pending_user(data)
        data["user_interventions"][0]["reason"] += "; el usuario está presente"
        self.assertEqual(self.assess(data)["decision"], "REQUIERE_USUARIO")

    def test_completed_action_requires_current_evidence(self):
        data = sample()
        pending_user(data)
        action = data["user_interventions"][0]
        action["status"] = "COMPLETED"
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")
        action.update(evidence_ref="receipt:manual", completed_at=NOW.isoformat(), captured_at=NOW.isoformat(), context_key=PREFLIGHT.context_key(data["context"]))
        self.assertEqual(self.assess(data)["decision"], "GO")
        action["completed_at"] = (NOW - dt.timedelta(hours=2)).isoformat()
        self.assertEqual(self.assess(data)["decision"], "GO")
        action["captured_at"] = (NOW - dt.timedelta(hours=2)).isoformat()
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
        action["captured_at"] = NOW.isoformat()
        action["context_key"] = "0" * 64
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_environment_change_requires_recheck_at_destination(self):
        data = sample()
        observation(data, "verification")["status"] = "FAIL"
        data["environment_change"] = {"required": True, "destination": "WORK", "reason": "Falta navegador comprobable", "handoff_ref": "conversation:handoff"}
        actual = self.assess(data)
        self.assertEqual(actual["decision"], "CAMBIO_ENTORNO")
        self.assertFalse(actual["can_start"])
        current = dict(data["context"], host="WORK", session_id="session:2")
        self.assertEqual(self.assess(data, current)["decision"], "NO_COMPROBADO")

    def test_transition_and_pending_human_are_both_visible(self):
        data = sample()
        data["environment_change"] = {"required": True, "destination": "WORK", "reason": "MFA interactivo", "handoff_ref": "conversation:handoff"}
        pending_user(data)
        actual = self.assess(data)
        self.assertEqual(actual["decision"], "REQUIERE_USUARIO")
        self.assertTrue(actual["environment_change"]["required"])

    def test_stop_dominates_human_and_environment(self):
        data = sample()
        pending_user(data)
        data["stop"] = True
        self.assertEqual(self.assess(data)["reasons"], ["STOP"])

    def test_denied_authorization_cannot_be_bypassed_by_handoff(self):
        data = sample()
        observation(data, "authorization").update(status="FAIL", detail="Permiso revocado")
        data["environment_change"] = {"required": True, "destination": "WORK", "reason": "Cambio de herramienta", "handoff_ref": "conversation:handoff"}
        pending_user(data)
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_read_denied_does_not_proceed(self):
        data = sample()
        observation(data, "access").update(status="FAIL", detail="READ_DENIED")
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_each_phase_attempt_and_context_are_bound(self):
        data = sample()
        for field in data["context"]:
            with self.subTest(field=field):
                current = dict(data["context"])
                current[field] += ":changed"
                self.assertEqual(self.assess(data, current)["decision"], "NO_COMPROBADO")

    def test_missing_current_context_is_not_inferred(self):
        self.assertEqual(PREFLIGHT.assess(sample(), None, now=NOW)["decision"], "BLOQUEADO")

    def test_observation_bound_to_other_context_is_rejected(self):
        data = sample()
        observation(data, "tools")["context_key"] = "0" * 64
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_preflight_and_each_observation_must_be_fresh(self):
        for delta in (-3601, 3601):
            data = sample()
            data["captured_at"] = (NOW + dt.timedelta(seconds=delta)).isoformat()
            self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
            data = sample()
            observation(data, "access")["captured_at"] = (NOW + dt.timedelta(seconds=delta)).isoformat()
            self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_missing_and_conflicting_observations_do_not_pass(self):
        data = sample()
        data["observations"].pop()
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
        data = sample()
        data["observations"].append(copy.deepcopy(data["observations"][0]))
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_all_required_areas_must_be_covered(self):
        data = sample()
        data["requirements"][0]["area"] = "execution"
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_invalid_inputs_and_boolean_types_fail_closed(self):
        for value in (None, [], "GO", 1, True):
            self.assertEqual(PREFLIGHT.assess(value, sample()["context"], now=NOW)["decision"], "BLOQUEADO")
        for key, value in (("stop", "false"), ("stop", 0), ("max_age_seconds", True), ("captured_at", "yesterday"), ("requirements", [])):
            data = sample()
            data[key] = value
            self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")
        data = sample()
        data["environment_change"]["required"] = "false"
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_missing_source_and_unknown_extra_fields_fail_closed(self):
        data = sample()
        observation(data, "tools")["source_ref"] = " "
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")
        data = sample()
        data["force_go"] = True
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_required_target_uses_existing_target_validator(self):
        data = sample()
        data["required_target_actions"] = [{"action_id": "action:publish", "target_id": "target:1", "environment": "test"}]
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
        data["target_preflights"] = [{
            "action_id": "action:publish", "target": {"id": "target:1", "environment": "test"},
            "required_facts": ["runtime"], "max_age_seconds": 900,
            "observations": [{"fact": "runtime", "action_id": "action:publish", "target_id": "target:1", "environment": "test",
                              "source_type": "target_probe", "source_ref": "probe:runtime", "observed": "Python 3", "captured_at": NOW.isoformat()}],
        }]
        self.assertEqual(self.assess(data)["decision"], "GO")
        data["target_preflights"][0]["observations"][0]["environment"] = "production"
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
        data["target_preflights"][0]["target"]["environment"] = "production"
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")
        data["required_target_actions"][0]["environment"] = "production"
        self.assertEqual(self.assess(data)["decision"], "GO")
        data["required_target_actions"][0]["target_id"] = "target:other"
        self.assertEqual(self.assess(data)["decision"], "NO_COMPROBADO")

    def test_duplicate_authorization_denial_is_not_hidden(self):
        data = sample()
        denial = dict(observation(data, "authorization"), status="FAIL", detail="Revocación actual")
        data["observations"].append(denial)
        pending_user(data)
        self.assertEqual(self.assess(data)["decision"], "BLOQUEADO")

    def test_cli_rejects_duplicate_stop_nonfinite_and_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_file = Path(tmp) / "receipt.json"
            context_file = Path(tmp) / "context.json"
            data = sample(now=dt.datetime.now(dt.timezone.utc))
            context_file.write_text(json.dumps(data["context"]), encoding="utf-8")
            base = json.dumps(data)
            for raw in (base.replace('"stop": false', '"stop": true, "stop": false').encode(), base.replace('"max_age_seconds": 900', '"max_age_seconds": Infinity').encode(), b'\xff', b'[' * 2000):
                receipt_file.write_bytes(raw)
                process = subprocess.run([sys.executable, str(SCRIPT), str(receipt_file), "--context", str(context_file)], capture_output=True, text=True)
                self.assertEqual(process.returncode, 2, process.stderr)
                self.assertEqual(json.loads(process.stdout)["decision"], "BLOQUEADO")

    def test_cli_returns_nonzero_for_blocked_and_zero_for_go(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt_file = Path(tmp) / "receipt.json"
            context_file = Path(tmp) / "context.json"
            data = sample(now=dt.datetime.now(dt.timezone.utc))
            context_file.write_text(json.dumps(data["context"]), encoding="utf-8")
            for stop, code, decision in ((False, 0, "GO"), (True, 2, "BLOQUEADO")):
                data["stop"] = stop
                receipt_file.write_text(json.dumps(data), encoding="utf-8")
                process = subprocess.run([sys.executable, str(SCRIPT), str(receipt_file), "--context", str(context_file)], capture_output=True, text=True)
                self.assertEqual(process.returncode, code, process.stderr)
                self.assertEqual(json.loads(process.stdout)["decision"], decision)


if __name__ == "__main__":
    unittest.main(verbosity=2)
