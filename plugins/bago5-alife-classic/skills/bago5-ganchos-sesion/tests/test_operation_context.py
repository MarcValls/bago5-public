"""Operational continuity regression scenarios over the real engine and local CLI.

The sources and observations below are synthetic. These tests establish local
state/adapter behavior, not authenticated panel access or live host delivery.
"""
from copy import deepcopy
import importlib
import json
from pathlib import Path
import sys
import unittest


TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
import test_session_acceptance as acceptance
import test_session_storage as storage

NOW = acceptance.NOW


class OperationContextTests(unittest.TestCase):
    # Reuse fixtures/helpers, without inheriting and rerunning unrelated tests.
    setUpClass = classmethod(acceptance.SessionControlAcceptance.setUpClass.__func__)
    setUp = acceptance.SessionControlAcceptance.setUp
    command = acceptance.SessionControlAcceptance.command
    event = acceptance.SessionControlAcceptance.event
    authority = acceptance.SessionControlAcceptance.authority
    continuity_command = acceptance.SessionControlAcceptance.continuity_command

    def context(self, *, panel=False):
        return {
            "schema": "bago5.operation-context.v1",
            "binding": deepcopy(self.state["binding"]),
            "phase_id": "phase-verify", "action_id": self.receipt["actions"][0]["id"],
            "operation": "Read the selected application's database identity.",
            "route": {
                "channel": "PANEL_CONSOLE" if panel else "SSH_USER",
                "operator": "AGENT" if panel else "USER", "target": "synthetic-host",
                "operation_scope": "Read-only identity query for the selected candidate.",
                "state": "OBSERVED" if panel else "UNKNOWN",
                "covers_operation": panel, "current": panel,
                "source_ref": "fixture:observed-panel-query" if panel else "fixture:requested-ssh",
            },
            "intervention": None if panel else {
                "id": "phase-intervention-ssh",
                "instruction": "Open the authorized SSH session and report that it is connected.",
                "status": "PENDING", "basis": "NONE", "source_ref": "fixture:asked-user",
                "evidence_ref": None, "reason": None,
            },
            "last_result": {
                "status": "OBSERVED" if panel else "NOT_RUN",
                "summary": "Panel identity query returned metadata." if panel else "SSH connection has not been observed.",
                "source_ref": "fixture:panel-output" if panel else "fixture:previous-turn",
            },
            "next_step": "Read only the selected identity metadata; retain remaining checks.",
            "source_ref": "fixture:operation-record",
        }

    def registered(self, context=None):
        return self.command(self.state, "SET_OPERATION_CONTEXT",
                            operation_context=context or self.context())["state"]

    def transition(self, **fields):
        return {"reason": "A read-only panel console was observed to cover this operation.",
                "source_ref": "fixture:panel-console-observation", **fields}

    def independent_context(self):
        context = self.context(panel=True)
        context["action_id"] = self.receipt["actions"][1]["id"]
        context["operation"] = "Preserve the already collected evidence while the connection is pending."
        context["route"]["operation_scope"] = "Preserve existing nonsecret evidence."
        return context

    def active_assignment(self, context_text):
        prefix = "Active assignment: "
        lines = [line[len(prefix):] for line in context_text.splitlines() if line.startswith(prefix)]
        self.assertEqual(len(lines), 1, "One parseable active-assignment preview must precede operation details.")
        return json.loads(lines[0])

    def test_active_assignment_precedes_operation_and_keeps_exact_short_identity(self):
        state = self.registered()
        result = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="¿qué escribo?"), now=NOW)["result"]
        text = result["context"]
        assignment = self.active_assignment(text)
        self.assertLess(text.index("Active assignment: "), text.index("Operation context: "))
        for key in ("project_id", "mission_id", "candidate_id"):
            self.assertEqual(assignment[key], state["binding"][key])
        self.assertEqual(assignment["goal"], state["anchor"]["goal"]["current"])
        self.assertEqual(assignment["control"], "RUNNING")
        self.assertLessEqual(len(text), 6000)

    def test_short_messages_recover_pending_step_without_completing_or_granting(self):
        state = self.registered()
        before = deepcopy(state)
        for prompt in ("conectado", "hecho", "¿por qué?", "¿qué escribo?"):
            with self.subTest(prompt=prompt):
                outcome = self.engine.handle_event(state, self.event("USER_PROMPT", prompt=prompt), now=NOW)
                after, result = outcome["state"], outcome["result"]
                self.assertEqual(after["operation_context"], before["operation_context"])
                self.assertEqual(after["receipt"], before["receipt"])
                self.assertEqual(after["control"], before["control"])
                self.assertEqual(after["operation_context"]["intervention"]["status"], "PENDING")
                self.assertTrue(after["receipt_stale"])
                self.assertEqual(result["action"], "NOTICE")
                self.assertIn("SSH_USER", result["context"])
                self.assertIn("phase-intervention-ssh", result["context"])
                self.assertIn("report that it is connected", result["context"])
                self.assertIn("DATA_ONLY", result["context"])
        self.assertEqual(state, before, "An event mutated its caller's snapshot.")

    def test_user_connection_declaration_remains_user_operated_and_unverified(self):
        state = self.registered()
        reported = self.context()
        reported["route"].update(state="REPORTED", current=True, source_ref="fixture:user-connected")
        reported["intervention"].update(status="REPORTED_DONE", basis="DECLARATION",
                                         source_ref="fixture:user-connected")
        reported["last_result"].update(status="REPORTED", summary="User reports connected.",
                                        source_ref="fixture:user-connected")
        outcome = self.command(state, "SET_OPERATION_CONTEXT", operation_context=reported)
        actual = outcome["state"]["operation_context"]
        self.assertEqual(actual["route"]["operator"], "USER")
        self.assertFalse(actual["route"]["covers_operation"])
        self.assertIsNone(actual["intervention"]["evidence_ref"])
        self.assertEqual(outcome["state"]["receipt"], state["receipt"])

    def test_declaration_cannot_claim_verified_intervention(self):
        value = self.context()
        value["intervention"].update(status="VERIFIED", basis="DECLARATION",
                                     evidence_ref="fixture:user-said-done")
        with self.assertRaisesRegex(self.engine.HookError, "VERIFICATION_REQUIRES_OBSERVATION"):
            self.registered(value)

    def test_observation_without_reference_cannot_verify_intervention(self):
        value = self.context()
        value["intervention"].update(status="VERIFIED", basis="OBSERVATION")
        with self.assertRaisesRegex(self.engine.HookError, "VERIFICATION_REQUIRES_OBSERVATION"):
            self.registered(value)

    def test_recorded_verification_requires_observation_and_does_not_change_receipt(self):
        value = self.context()
        value["intervention"].update(status="VERIFIED", basis="OBSERVATION",
                                     evidence_ref="fixture:identity-command-output")
        state = self.registered(value)
        self.assertEqual(state["operation_context"]["intervention"]["status"], "VERIFIED")
        self.assertEqual(state["receipt"], self.state["receipt"])
        self.assertEqual(state["receipt"]["criteria"][0]["status"], "PENDING")

    def test_reported_route_cannot_claim_observed_operation_coverage(self):
        value = self.context()
        value["route"].update(state="REPORTED", covers_operation=True)
        with self.assertRaisesRegex(self.engine.HookError, "COVERAGE_REQUIRES_OBSERVATION"):
            self.registered(value)

    def test_route_change_requires_reason_and_source(self):
        state = self.registered(self.context(panel=True))
        value = self.context(panel=True)
        value["route"]["channel"] = "API"
        with self.assertRaisesRegex(self.engine.HookError, "ROUTE_CHANGE_REQUIRES_REASON_AND_SOURCE"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=value)

    def test_operator_change_is_route_change(self):
        state = self.registered(self.context(panel=True))
        value = self.context(panel=True)
        value["route"]["operator"] = "USER"
        with self.assertRaisesRegex(self.engine.HookError, "ROUTE_CHANGE_REQUIRES_REASON_AND_SOURCE"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=value)

    def test_pending_intervention_cannot_be_dropped_on_same_route(self):
        state = self.registered()
        value = self.context()
        value["intervention"] = None
        with self.assertRaisesRegex(self.engine.HookError, "PENDING_INTERVENTION_CANNOT_DISAPPEAR"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=value)

    def test_route_change_cannot_silently_drop_previous_human_request(self):
        state = self.registered()
        with self.assertRaisesRegex(self.engine.HookError, "PENDING_INTERVENTION_CANNOT_DISAPPEAR"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                         transition=self.transition())

    def test_valid_replacement_preserves_exact_request_and_resolution(self):
        state = self.registered()
        transition = self.transition(previous_intervention_status="SUPERSEDED")
        outcome = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                               transition=transition)
        after = outcome["state"]
        self.assertEqual(after["operation_history"][0]["context"], state["operation_context"])
        self.assertEqual(after["operation_history"][0]["transition"], transition)
        self.assertEqual(after["operation_history"][0]["authority"], "DATA_ONLY")
        self.assertEqual(after["operation_context"]["route"]["channel"], "PANEL_CONSOLE")
        self.assertEqual(after["receipt"], state["receipt"])
        self.assertEqual(after["control"], state["control"])

    def test_same_intervention_explicitly_cancelled_can_accompany_route_change(self):
        state = self.registered()
        value = self.context(panel=True)
        value["intervention"] = deepcopy(state["operation_context"]["intervention"])
        value["intervention"].update(status="CANCELLED", reason="The observed console covers this step.")
        outcome = self.command(state, "SET_OPERATION_CONTEXT", operation_context=value,
                               transition=self.transition())
        self.assertEqual(outcome["state"]["operation_context"]["intervention"]["status"], "CANCELLED")
        self.assertEqual(outcome["state"]["operation_history"][0]["context"]["intervention"]["status"], "PENDING")

    def test_transition_verification_cannot_use_a_declaration_as_evidence(self):
        state = self.registered()
        transition = self.transition(previous_intervention_status="VERIFIED",
                                     intervention_evidence_ref="fixture:user-said-done",
                                     intervention_evidence_basis="DECLARATION")
        with self.assertRaisesRegex(self.engine.HookError, "VERIFICATION_REQUIRES_OBSERVATION"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                         transition=transition)

    def test_conflicting_resolutions_of_the_same_request_are_rejected(self):
        state = self.registered()
        value = self.context(panel=True)
        value["intervention"] = deepcopy(state["operation_context"]["intervention"])
        value["intervention"].update(status="CANCELLED", reason="Console covers the step.")
        transition = self.transition(previous_intervention_status="VERIFIED",
                                     intervention_evidence_ref="fixture:observation",
                                     intervention_evidence_basis="OBSERVATION")
        with self.assertRaisesRegex(self.engine.HookError, "CONFLICTING_INTERVENTION_RESOLUTION"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=value, transition=transition)

    def test_pending_instruction_cannot_be_overwritten_using_same_id(self):
        state = self.registered()
        value = self.context()
        value["intervention"]["instruction"] = "Perform an unrelated operation."
        with self.assertRaisesRegex(self.engine.HookError, "INSTRUCTION_CHANGED_REQUIRES_NEW_ID"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=value)

    def test_independent_branch_keeps_original_intervention_pending_and_visible(self):
        state = self.registered()
        after = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.independent_context(),
                             transition=self.transition(previous_intervention_status="STILL_REQUIRED"))["state"]
        pending = self.engine.summary(after)["pending_interventions"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["id"], "phase-intervention-ssh")
        self.assertEqual(pending[0]["status"], "PENDING")
        self.assertEqual(pending[0]["action_id"], self.receipt["actions"][0]["id"])
        self.assertEqual(pending[0]["instruction"], state["operation_context"]["intervention"]["instruction"])
        result = self.engine.handle_event(after, self.event("USER_PROMPT", prompt="¿qué escribo?"), now=NOW)["result"]
        self.assertIn("Other pending interventions (1", result["context"])
        self.assertIn("phase-intervention-ssh", result["context"])
        self.assertEqual(after["receipt"], state["receipt"])

    def test_still_required_cannot_hide_request_for_the_same_action(self):
        state = self.registered()
        with self.assertRaisesRegex(self.engine.HookError, "PENDING_INTERVENTION_CANNOT_DISAPPEAR"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                         transition=self.transition(previous_intervention_status="STILL_REQUIRED"))

    def test_return_to_pending_action_and_observed_resolution_clear_pending_summary(self):
        state = self.registered()
        state = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.independent_context(),
                             transition=self.transition(previous_intervention_status="STILL_REQUIRED"))["state"]
        resumed = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(),
                               transition=self.transition(reason="Return to the original connection check."))["state"]
        self.assertEqual(self.engine.summary(resumed)["pending_interventions"][0]["status"], "PENDING")
        verified = self.context()
        verified["intervention"].update(status="VERIFIED", basis="OBSERVATION",
                                         evidence_ref="fixture:observed-selected-connection")
        after = self.command(resumed, "SET_OPERATION_CONTEXT", operation_context=verified)["state"]
        self.assertEqual(self.engine.summary(after)["pending_interventions"], [])
        self.assertEqual(after["operation_history"][0]["transition"]["previous_intervention_status"], "STILL_REQUIRED")
        self.assertEqual(after["operation_context"]["intervention"]["status"], "VERIFIED")
        self.assertEqual(after["receipt"], self.receipt)

    def test_terminal_historical_intervention_cannot_be_reopened_after_branch_switch(self):
        cancelled = self.context()
        cancelled["intervention"].update(status="CANCELLED", reason="User withdrew this connection request.")
        state = self.registered(cancelled)
        state = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.independent_context(),
                             transition=self.transition(reason="Continue independent authorized work."))["state"]
        self.assertEqual(self.engine.summary(state)["pending_interventions"], [])
        with self.assertRaisesRegex(self.engine.HookError, "RESOLVED_INTERVENTION_CANNOT_REOPEN"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(),
                         transition=self.transition(reason="Attempt to reuse the old request."))

    def test_individually_bounded_fields_with_many_escapes_exceed_total_limit(self):
        value = self.context()
        for field in ("operation", "next_step"):
            value[field] = "\u0001" * 360
        value["intervention"]["instruction"] = "\u0001" * 360
        self.engine._validate_schema(value, self.engine.OPERATION_SCHEMA, "TEST_INDIVIDUAL_FIELDS")
        self.assertGreater(len(self.engine.canonical(value).decode("utf-8")), 4200)
        with self.assertRaisesRegex(self.engine.HookError, "OPERATION_CONTEXT_SERIALIZED_LIMIT"):
            self.registered(value)

    def test_large_goal_does_not_truncate_operation_or_exceed_context_limit(self):
        init = deepcopy(self.init)
        init["receipt"]["goal"].update(baseline="G" * 9900, current="G" * 9900)
        state = self.engine.apply_command(None, init, now=NOW)["state"]
        context = self.context()
        context["operation"] = "O" * 360
        context["next_step"] = "\u0001" * 130
        context["last_result"]["summary"] = "R" * 360
        context["intervention"]["instruction"] = "\u0001" * 200
        context["route"]["operation_scope"] = "S" * 240
        context["route"]["target"] = "T" * 160
        context["route"]["source_ref"] = "E" * 200
        self.assertGreater(len(self.engine.canonical(context).decode("utf-8")), 4000)
        self.assertLessEqual(len(self.engine.canonical(context).decode("utf-8")), 4200)
        state = self.command(state, "SET_OPERATION_CONTEXT", operation_context=context)["state"]
        result = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="¿por qué?"), now=NOW)["result"]
        self.assertLessEqual(len(result["context"]), 6000)
        self.assertIn(context["operation"], result["context"])
        operation_line = next(line[len("Operation context: "):] for line in result["context"].splitlines()
                              if line.startswith("Operation context: "))
        rendered_operation = json.loads(operation_line)
        self.assertEqual(rendered_operation["intervention"]["instruction"], context["intervention"]["instruction"])
        self.assertEqual(rendered_operation["next_step"], context["next_step"])
        assignment = self.active_assignment(result["context"])
        self.assertEqual(assignment["project_id"], state["binding"]["project_id"])
        self.assertEqual(assignment["mission_id"], state["binding"]["mission_id"])
        self.assertLessEqual(len(assignment["goal"]), 320)
        self.assertTrue(assignment["goal"].startswith("G" * 80))
        self.assertIn("goal", assignment["truncated_fields"])
        self.assertEqual(assignment["full_assignment_ref"], "STATUS.binding and STATUS.current_goal")
        self.assertLess(result["context"].index("Active assignment: "), result["context"].index("Operation context: "))
        self.assertEqual(state["anchor"]["goal"]["baseline"], "G" * 9900)
        self.assertEqual(state["receipt"]["goal"], init["receipt"]["goal"])
        status = self.command(state, "STATUS")["result"]["data"]
        self.assertEqual(status["goal"], "G" * 9900)
        self.assertEqual(status["current_goal"], "G" * 9900)

    def test_long_unicode_and_control_character_identifiers_keep_bounded_parseable_preview(self):
        for character in ("é", "\u0001"):
            with self.subTest(character=repr(character)):
                receipt = deepcopy(self.receipt)
                binding = deepcopy(receipt["binding"])
                for key in ("project_id", "mission_id", "candidate_id"):
                    binding[key] = key + ":" + character * 190

                def rebind(value):
                    if isinstance(value, dict):
                        if set(value) == set(binding):
                            return deepcopy(binding)
                        return {key: rebind(item) for key, item in value.items()}
                    if isinstance(value, list):
                        return [rebind(item) for item in value]
                    return value

                receipt = rebind(receipt)
                full_goal = "Objective:" + character * 9800
                receipt["goal"].update(baseline=full_goal, current=full_goal)
                init = deepcopy(self.init)
                init["receipt"] = receipt
                state = self.engine.apply_command(None, init, now=NOW)["state"]
                result = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="¿por qué?"), now=NOW)["result"]
                self.assertLessEqual(len(result["context"]), 6000)
                assignment = self.active_assignment(result["context"])
                self.assertLessEqual(len(self.engine.canonical(assignment).decode("utf-8")), 1100)
                for key in ("project_id", "mission_id", "candidate_id"):
                    self.assertLessEqual(len(assignment[key]), 160)
                    self.assertTrue(assignment[key].startswith(key + ":"))
                    self.assertIn(key, assignment["truncated_fields"])
                self.assertLessEqual(len(assignment["goal"]), 320)
                self.assertTrue(assignment["goal"].startswith("Objective:"))
                self.assertIn("goal", assignment["truncated_fields"])
                self.assertEqual(assignment["full_assignment_ref"], "STATUS.binding and STATUS.current_goal")
                status = self.command(state, "STATUS")["result"]["data"]
                self.assertEqual(status["binding"], binding)
                self.assertEqual(status["goal"], full_goal)
                self.assertEqual(status["current_goal"], full_goal)

    def test_elliptical_migration_request_keeps_goal_and_permissions_pending_reassessment(self):
        state = self.registered()
        before = deepcopy(state)
        outcome = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="migra ya"), now=NOW)
        after, result = outcome["state"], outcome["result"]
        self.assertEqual(after["binding"], before["binding"])
        self.assertEqual(after["anchor"], before["anchor"])
        self.assertEqual(after["receipt"], before["receipt"])
        self.assertEqual(after["control"], before["control"])
        self.assertTrue(after["receipt_stale"])
        self.assertTrue(after["operation_context_stale"])
        self.assertEqual(result["action"], "NOTICE")
        self.assertEqual(self.active_assignment(result["context"])["goal"], before["anchor"]["goal"]["current"])

    def test_side_question_keeps_active_assignment_and_pending_intervention(self):
        state = self.registered()
        outcome = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="¿Qué significa localhost?"), now=NOW)
        after, result = outcome["state"], outcome["result"]
        assignment = self.active_assignment(result["context"])
        self.assertEqual(assignment["mission_id"], state["binding"]["mission_id"])
        self.assertEqual(assignment["goal"], state["anchor"]["goal"]["current"])
        self.assertEqual(after["operation_context"], state["operation_context"])
        self.assertEqual(after["receipt"], state["receipt"])
        self.assertEqual(after["control"]["state"], "RUNNING")

    def test_exact_stop_preserves_assignment_and_later_elipsis_cannot_resume(self):
        state = self.registered()
        stopped = self.engine.handle_event(state, self.event("USER_PROMPT", prompt="STOP"), now=NOW)
        self.assertEqual(stopped["result"]["action"], "STOP")
        self.assertEqual(stopped["state"]["control"]["state"], "STOP")
        self.assertEqual(stopped["state"]["anchor"], state["anchor"])
        self.assertEqual(stopped["state"]["binding"], state["binding"])
        outcome = self.engine.handle_event(stopped["state"], self.event("USER_PROMPT", prompt="migra ya"), now=NOW)
        self.assertEqual(outcome["state"]["control"]["state"], "STOP")
        self.assertEqual(outcome["state"]["receipt"]["control"]["state"], "STOP")
        assignment = self.active_assignment(outcome["result"]["context"])
        self.assertEqual(assignment["goal"], state["anchor"]["goal"]["current"])
        self.assertEqual(assignment["control"], "STOP")

    def test_postcompact_retains_assignment_identity_and_goal_without_refreshing_authority(self):
        state = self.registered()
        outcome = self.engine.handle_event(state, self.event("AFTER_COMPACT"), now=NOW)
        after, result = outcome["state"], outcome["result"]
        assignment = self.active_assignment(result["context"])
        for key in ("project_id", "mission_id", "candidate_id"):
            self.assertEqual(assignment[key], state["binding"][key])
        self.assertEqual(assignment["goal"], state["anchor"]["goal"]["current"])
        self.assertEqual(after["anchor"], state["anchor"])
        self.assertEqual(after["receipt"], state["receipt"])
        self.assertTrue(after["receipt_stale"])
        self.assertTrue(after["operation_context_stale"])
        self.assertFalse(after["scope_current"])

    def test_authorized_current_goal_is_previewed_without_overwriting_original_baseline(self):
        init = deepcopy(self.init)
        baseline = init["receipt"]["goal"]["baseline"]
        current = "Verify the selected database identity and preserve the approved evidence."
        authority = self.authority()
        authority["source_ref"] = "fixture:explicit-scoped-goal-change"
        init["receipt"]["goal"].update(current=current, change_authority=authority)
        state = self.engine.apply_command(None, init, now=NOW)["state"]
        state = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context())["state"]
        for event in (self.event("USER_PROMPT", prompt="migra ya"), self.event("AFTER_COMPACT")):
            with self.subTest(event=event["event"]):
                outcome = self.engine.handle_event(state, event, now=NOW)
                after, result = outcome["state"], outcome["result"]
                assignment = self.active_assignment(result["context"])
                self.assertEqual(assignment["goal"], current)
                self.assertNotEqual(assignment["goal"], baseline)
                self.assertEqual(assignment["full_assignment_ref"], "STATUS.binding and STATUS.current_goal")
                self.assertEqual(after["anchor"]["goal"]["baseline"], baseline)
                self.assertEqual(after["anchor"]["goal"]["current"], current)
                self.assertEqual(after["receipt"], init["receipt"])
                status = self.command(after, "STATUS")["result"]["data"]
                self.assertEqual(status["goal"], baseline, "Legacy baseline field must remain intact.")
                self.assertEqual(status["current_goal"], current)
        unauthorized = deepcopy(init)
        unauthorized["receipt"]["goal"]["change_authority"] = None
        with self.assertRaisesRegex(self.engine.HookError, "INVALID_TURN_RECEIPT"):
            self.engine.apply_command(None, unauthorized, now=NOW)

    def test_uncertain_result_cannot_be_cleared_without_reconciliation(self):
        value = self.context(panel=True)
        value["last_result"].update(status="UNCERTAIN", summary="Tool returned no receipt.")
        state = self.registered(value)
        with self.assertRaisesRegex(self.engine.HookError, "UNCERTAIN_RESULT_REQUIRES_RECONCILIATION"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                         transition=self.transition())
        after = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                             transition=self.transition(reconciled_result_ref="fixture:read-only-reconciliation"))["state"]
        self.assertEqual(after["operation_history"][0]["context"]["last_result"]["status"], "UNCERTAIN")

    def test_uncertain_operation_cannot_retry_on_another_channel(self):
        value = self.context(panel=True)
        value["last_result"].update(status="UNCERTAIN", summary="Tool outcome unknown.")
        state = self.registered(value)
        changed = deepcopy(value)
        changed["route"]["channel"] = "SSH_AGENT"
        with self.assertRaisesRegex(self.engine.HookError, "UNCERTAIN_RESULT_REQUIRES_RECONCILIATION"):
            self.command(state, "SET_OPERATION_CONTEXT", operation_context=changed, transition=self.transition())

    def test_tool_block_after_success_preserves_both_observations(self):
        state = self.registered(self.context(panel=True))
        blocked = self.context(panel=True)
        blocked["route"].update(state="UNAVAILABLE", covers_operation=False,
                                 source_ref="fixture:host-tool-denied")
        blocked["last_result"].update(status="UNCERTAIN", summary="Host denied the tool; no command output received.",
                                       source_ref="fixture:host-tool-denied")
        blocked["next_step"] = "Resolve the applicable host denial, then reconcile before any repeat."
        after = self.command(state, "SET_OPERATION_CONTEXT", operation_context=blocked)["state"]
        result = self.engine.handle_event(after, self.event("USER_PROMPT", prompt="¿por qué?"), now=NOW)["result"]
        self.assertEqual(after["operation_history"][0]["context"]["route"]["state"], "OBSERVED")
        self.assertEqual(after["operation_context"]["route"]["state"], "UNAVAILABLE")
        self.assertIn("host-tool-denied", result["context"])
        self.assertIn("UNCERTAIN", result["context"])

    def test_compaction_retains_context_as_data_requiring_revalidation(self):
        state = self.registered(self.context(panel=True))
        outcome = self.engine.handle_event(state, self.event("AFTER_COMPACT"), now=NOW)
        after = outcome["state"]
        self.assertEqual(after["operation_context"], state["operation_context"])
        self.assertTrue(after["operation_context_stale"])
        self.assertTrue(after["receipt_stale"])
        self.assertFalse(after["scope_current"])
        self.assertTrue(self.engine.summary(after)["operation_context"]["revalidation_required"])
        self.assertIn("PANEL_CONSOLE", outcome["result"]["context"])

    def test_context_update_does_not_refresh_stale_receipt_or_scope(self):
        state = self.engine.handle_event(self.state, self.event("AFTER_COMPACT"), now=NOW)["state"]
        after = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context())["state"]
        self.assertTrue(after["receipt_stale"])
        self.assertFalse(after["scope_current"])
        self.assertEqual(after["receipt"], state["receipt"])

    def test_continuity_exports_current_context_and_history_without_authority(self):
        state = self.registered()
        state = self.command(state, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True),
                             transition=self.transition(previous_intervention_status="SUPERSEDED"))["state"]
        packet = self.engine.apply_command(state, self.continuity_command(), now=NOW)["state"]["continuity"]
        self.assertEqual(packet["operation_context"], state["operation_context"])
        self.assertEqual(packet["operation_history"], state["operation_history"])
        self.assertEqual(packet["binding"], self.receipt["binding"])
        self.assertEqual(packet["baseline_criteria"], self.receipt["baseline_criteria"])
        self.assertTrue(packet["operation_context_requires_revalidation"])
        self.assertFalse(packet["handoff"]["resumption_authorized"])
        self.assertEqual(packet["execution"], "NOT_RUN_AT_RECIPIENT")

    def test_stopped_mission_cannot_record_or_resume_through_context(self):
        stopped = self.command(self.registered(), "STOP")["state"]
        before = deepcopy(stopped)
        with self.assertRaisesRegex(self.engine.HookError, "CONTROL_NOT_RUNNING"):
            self.command(stopped, "SET_OPERATION_CONTEXT", operation_context=self.context(panel=True))
        self.assertEqual(stopped, before)
        outcome = self.engine.handle_event(stopped, self.event("USER_PROMPT", prompt="hecho"), now=NOW)
        self.assertEqual(outcome["state"]["control"]["state"], "STOP")
        self.assertEqual(outcome["state"]["operation_context"], stopped["operation_context"])

    def test_wrong_project_candidate_or_action_is_rejected(self):
        for key in ("project_id", "candidate_id", "session_id"):
            value = self.context()
            value["binding"][key] = "other-scope"
            with self.subTest(key=key), self.assertRaisesRegex(self.engine.HookError, "BINDING_MISMATCH"):
                self.registered(value)
        value = self.context()
        value["action_id"] = "unknown-action"
        with self.assertRaisesRegex(self.engine.HookError, "ACTION_NOT_IN_RECEIPT"):
            self.registered(value)

    def test_no_extra_authority_fields_or_unbounded_instruction(self):
        value = self.context()
        value["authorization"] = {"state": "ALLOWED"}
        with self.assertRaisesRegex(self.engine.HookError, "SCHEMA_EXTRA_FIELDS"):
            self.registered(value)
        value = self.context()
        value["intervention"]["instruction"] = "x" * 361
        with self.assertRaisesRegex(self.engine.HookError, "SCHEMA_LENGTH"):
            self.registered(value)

    def test_legacy_session_without_operation_context_still_continues(self):
        self.assertNotIn("operation_context", self.state)
        self.assertIsNone(self.engine.summary(self.state)["operation_context"])
        result = self.engine.handle_event(self.state, self.event("BEFORE_TURN_CLOSE"), now=NOW)["result"]
        self.assertEqual(result["action"], "CONTINUE")
        packet = self.engine.apply_command(self.state, self.continuity_command(), now=NOW)["state"]["continuity"]
        self.assertIsNone(packet["operation_context"])
        self.assertEqual(packet["operation_history"], [])

    def test_project_switch_archives_without_inheriting_active_route(self):
        state = self.registered()
        binding = deepcopy(state["binding"])
        binding.update(project_id="another-project", mission_id="another-mission", goal_id="another-goal",
                       candidate_id="another-candidate", scope_id="another-scope")

        def rebind(value):
            if isinstance(value, dict):
                if set(value) == set(binding):
                    return deepcopy(binding)
                return {key: rebind(item) for key, item in value.items()}
            if isinstance(value, list):
                return [rebind(item) for item in value]
            return value

        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority(), receipt=rebind(self.receipt),
                      workspace_root=str(self.workspace.parent / "another-project"))
        after = self.engine.apply_command(state, switch, now=NOW)["state"]
        self.assertIsNone(after.get("operation_context"))
        self.assertEqual(after["operation_history"][-1]["context"], state["operation_context"])
        self.assertEqual(after["operation_history"][-1]["authority"], "DATA_ONLY")

    def test_cli_persists_context_across_processes_and_codex_delivers_it(self):
        fixture = storage.SessionStorageTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.initialize()
        context = self.context()
        context["binding"] = deepcopy(fixture.context)
        context["action_id"] = fixture.receipt["actions"][0]["id"]
        code, saved = fixture.command("SET_OPERATION_CONTEXT", operation_context=context)
        self.assertEqual((code, saved["action"]), (0, "NOTICE"))
        code, status = fixture.command("STATUS")
        self.assertEqual(code, 0)
        self.assertEqual(status["data"]["operation_context"]["intervention"], context["intervention"])
        self.assertEqual(fixture.read_state()["operation_context"], context)
        native = fixture.native("UserPromptSubmit", prompt="conectado")
        output = native["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "UserPromptSubmit")
        self.assertIn("SSH_USER", output["additionalContext"])
        self.assertIn("phase-intervention-ssh", output["additionalContext"])
        self.assertEqual(fixture.read_state()["operation_context"], context)
        self.assertTrue(fixture.read_state()["receipt_stale"])

    def test_copilot_does_not_gain_an_unsupported_user_prompt_event(self):
        native = importlib.import_module("native_hooks")
        output, notice = native.dispatch(b"{}", "COPILOT", "UserPromptSubmit")
        self.assertEqual(output, {})
        self.assertIn("UNSUPPORTED_HOST_EVENT", notice)


if __name__ == "__main__":
    unittest.main()
