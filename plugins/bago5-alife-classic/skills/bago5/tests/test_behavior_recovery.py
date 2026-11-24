"""Acceptance tests for CCR-001; synthetic metadata and isolated local effects.

These tests do not establish host hook activation, remote permissions, a live
database connection, or autonomous execution by an LLM.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SKILL = Path(__file__).resolve().parents[1]
MODULE = SKILL / "scripts/behavior_recovery.py"
spec = importlib.util.spec_from_file_location("ccr_acceptance", MODULE)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


def fixture():
    return json.loads((SKILL / "tests/fixtures/behavior-recovery/ccr-001.json").read_text(encoding="utf-8"))


def satisfied(receipt):
    result = deepcopy(receipt)
    result["evidence"] = []
    for criterion in result["criteria"]:
        eid = "synthetic-complete-" + criterion["id"]
        criterion.update(status="PASS", evidence_ids=[eid])
        result["evidence"].append({"id": eid, "criterion_id": criterion["id"],
                                   "binding": deepcopy(result["binding"]), "kind": "OBSERVATION",
                                   "outcome": "PASS", "source_ref": "fixture:" + eid,
                                   "origin_id": eid, "derived_from": []})
    return result


class BehaviorRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.f = fixture()
        self.receipt = self.f["receipt"]
        self.obs = self.f["observation"]
        self.now = self.f["now"]
        self.record = recovery.register(self.receipt, self.f["spec"], self.f["registered_at"])
        self.ready = deepcopy(self.receipt)
        self.ready["actions"][0]["preconditions"] = "SATISFIED"

    def result(self, record=None, receipt=None, obs=None, now=None):
        return recovery.reassess(record or self.record, receipt or self.ready,
                                 obs or self.obs, now or self.now)

    def test_negative_then_positive_preserves_goal_and_current_permission(self):
        guarded = recovery.guard_receipt(self.receipt, [self.record], self.now)
        self.assertEqual(recovery.policy.assess(guarded)["decision"], "BLOCKED")
        result = self.result()
        self.assertEqual(result["policy_result"]["decision"], "CONTINUE")
        self.assertEqual(result["record"]["state"], "RESOLVED")
        self.assertIsNone(result["receipt"]["actions"][0]["blocker"])
        for key in ("goal", "baseline_criteria", "criteria", "evidence"):
            self.assertEqual(result["receipt"][key], self.ready[key])
        self.assertEqual(result["receipt"]["actions"][0]["authorization"], self.ready["actions"][0]["authorization"])
        self.assertEqual(result["record"]["initial_blocker"], self.receipt["actions"][0]["blocker"])

    def test_local_effect_harness_executes_only_after_recovery_then_closes(self):
        with tempfile.TemporaryDirectory() as folder:
            artifact = Path(folder) / "synthetic-result.txt"
            before = recovery.policy.assess(recovery.guard_receipt(self.receipt, [self.record], self.now))
            if before["decision"] == "CONTINUE":
                artifact.write_text("unexpected", encoding="utf-8")
            self.assertFalse(artifact.exists())
            after = self.result()
            if after["policy_result"]["decision"] == "CONTINUE":
                artifact.write_text("synthetic-db-verified", encoding="utf-8")
            self.assertEqual(artifact.read_text(), "synthetic-db-verified")
            final = satisfied(after["receipt"])
            final["evidence"][0]["source_ref"] = "isolated-harness:read-result-file"
            self.assertEqual(recovery.policy.assess(recovery.guard_receipt(final, [after["record"]], self.now))["decision"], "CLOSE")
            self.assertEqual(len(list(Path(folder).iterdir())), 1)

    def test_erasing_blocker_does_not_bypass_waiting_record(self):
        self.ready["actions"][0]["blocker"] = None
        result = recovery.guard_receipt(self.ready, [self.record], self.now)
        self.assertEqual(recovery.policy.assess(result)["decision"], "BLOCKED")
        self.assertEqual(result, recovery.guard_receipt(result, [self.record], self.now))

    def test_unsatisfied_or_unknown_condition_stays_blocked(self):
        for state in ("UNSATISFIED", "UNKNOWN"):
            with self.subTest(state=state):
                obs = deepcopy(self.obs)
                obs["conditions"][0]["state"] = state
                result = self.result(obs=obs)
                self.assertEqual(result["record"]["state"], "WAITING_CONDITIONS")
                self.assertEqual(result["policy_result"]["decision"], "BLOCKED")

    def test_current_revocation_is_preserved_after_dependency_recovers(self):
        self.ready["actions"][0]["authorization"]["state"] = "REVOKED"
        result = self.result()
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")
        self.assertEqual(result["receipt"]["actions"][0]["authorization"]["state"], "REVOKED")

    def test_expired_current_authority_never_becomes_allowed(self):
        self.ready["actions"][0]["authorization"]["current"] = False
        result = self.result()
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")
        self.assertFalse(result["receipt"]["actions"][0]["authorization"]["current"])

    def test_historical_denial_requires_current_new_authority_reference(self):
        for old_state in ("DENIED", "REVOKED"):
            with self.subTest(old_state=old_state):
                before = deepcopy(self.receipt)
                before["actions"][0]["authorization"]["state"] = old_state
                record = recovery.register(before, self.f["spec"], self.f["registered_at"])
                bad = self.result(record=record)
                self.assertEqual(bad["policy_result"]["decision"], "BLOCKED")
                current = deepcopy(self.ready)
                current["actions"][0]["authorization"]["source_ref"] = "synthetic:new-current-permission"
                good = self.result(record=record, receipt=current)
                self.assertEqual(good["policy_result"]["decision"], "CONTINUE")

    def test_stop_short_circuits_without_mutation_or_observation_processing(self):
        stopped = deepcopy(self.ready)
        stopped["control"]["state"] = "STOP"
        result = recovery.reassess(self.record, stopped, None, self.now)
        self.assertEqual(result["policy_result"]["decision"], "STOP")
        self.assertEqual(result["record"], self.record)
        self.assertEqual(result["receipt"], stopped)
        self.assertFalse(result["changed"])
        with self.assertRaises(recovery.RecoveryError):
            recovery.register(stopped, self.f["spec"], self.now)

    def test_unknown_control_does_not_recover(self):
        self.ready["control"]["state"] = "UNKNOWN"
        result = self.result()
        self.assertEqual(result["record"]["state"], "WAITING_CONDITIONS")
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")

    def test_prohibition_requires_exact_restriction_and_current_authority(self):
        config = deepcopy(self.f["spec"])
        config["cause_kind"] = "PROHIBITION"
        config["restriction_source_type"] = "USER_INSTRUCTION"
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        self.assertEqual(self.result(record=record)["record"]["state"], "PROHIBITED")
        obs = deepcopy(self.obs)
        obs["restriction_resolution"] = {"restriction_ref": config["source_ref"],
                                          "authority": deepcopy(self.ready["actions"][0]["authorization"])}
        obs["restriction_resolution"]["authority"]["source_ref"] = "synthetic:explicit-lift-of-this-restriction"
        self.assertEqual(self.result(record=record, obs=obs)["policy_result"]["decision"], "CONTINUE")
        for change in ("other-restriction", "old-authority", "wrong-authority-type"):
            with self.subTest(change=change):
                invalid = deepcopy(obs)
                if change == "other-restriction":
                    invalid["restriction_resolution"]["restriction_ref"] = "synthetic:other"
                elif change == "old-authority":
                    invalid["restriction_resolution"]["authority"]["current"] = False
                else:
                    invalid["restriction_resolution"]["authority"]["source_type"] = "HOST_PERMISSION"
                self.assertEqual(self.result(record=record, obs=invalid)["record"]["state"], "PROHIBITED")

    def test_another_current_blocker_survives_resolution(self):
        self.ready["actions"][0]["blocker"] = {"reason": "La candidata cambió en el servidor.",
                                                "source_ref": "synthetic:different-blocker",
                                                "intervention": "Contrastar la candidata actual.",
                                                "basis": "OBSERVATION", "current": True}
        result = self.result()
        self.assertEqual(result["receipt"]["actions"][0]["blocker"], self.ready["actions"][0]["blocker"])
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")

    def test_independent_branch_continues_while_corrected_branch_waits(self):
        current = deepcopy(self.ready)
        definition = deepcopy(current["baseline_criteria"][0])
        definition.update(id="independent", description="Verify independent static asset.")
        current["baseline_criteria"].append(definition)
        current["criteria"].append({**definition, "status": "PENDING", "evidence_ids": [], "waiver": None})
        action = deepcopy(current["actions"][0])
        action.update(id="independent-action", criterion_ids=["independent"], blocker=None)
        current["actions"].append(action)
        record = recovery.register(current, self.f["spec"], self.f["registered_at"])
        result = recovery.policy.assess(recovery.guard_receipt(current, [record], self.now))
        self.assertEqual(result["decision"], "CONTINUE")
        self.assertEqual(result["eligible_actions"], ["independent-action"])

    def test_renaming_action_or_switching_tool_does_not_escape_correction(self):
        self.ready["actions"][0].update(id="different-tool-same-effect", blocker=None)
        result = recovery.policy.assess(recovery.guard_receipt(self.ready, [self.record], self.now))
        self.assertEqual(result["decision"], "BLOCKED")

    def test_explicit_correct_replacement_preserves_obligations(self):
        self.ready["actions"][0].update(id="corrected-inspection", blocker=None)
        self.obs["action_id"] = "corrected-inspection"
        result = self.result()
        self.assertEqual(result["policy_result"]["eligible_actions"], ["corrected-inspection"])
        self.assertEqual(result["record"]["action_id"], "inspect-application-db")
        self.assertEqual(result["record"]["target_action_id"], "corrected-inspection")

    def test_replacement_cannot_leave_original_action_in_receipt(self):
        replacement = deepcopy(self.ready["actions"][0])
        replacement["id"] = "replacement"
        self.ready["actions"].append(replacement)
        self.obs["action_id"] = "replacement"
        with self.assertRaises(recovery.RecoveryError):
            self.result()

    def test_scope_and_candidate_and_revision_mismatches_are_rejected(self):
        for key in ("project_id", "mission_id", "candidate_id", "session_id", "scope_id", "goal_revision"):
            with self.subTest(key=key):
                obs = deepcopy(self.obs)
                obs["binding"][key] = 2 if key == "goal_revision" else "other"
                with self.assertRaises(recovery.RecoveryError):
                    self.result(obs=obs)

    def test_goal_or_criterion_loss_is_rejected(self):
        current = deepcopy(self.ready)
        current["goal"]["current"] = "Different goal"
        with self.assertRaises(recovery.RecoveryError):
            self.result(receipt=current)
        current = deepcopy(self.ready)
        current["criteria"] = []
        with self.assertRaises(recovery.RecoveryError):
            self.result(receipt=current)

    def test_stale_future_or_historical_observation_cannot_recover(self):
        for change in ("stale", "future", "not-current", "before-registration", "same-source"):
            with self.subTest(change=change):
                obs = deepcopy(self.obs)
                if change == "stale":
                    obs.update(observed_at="2026-11-20T11:59:00+00:00", valid_until="2026-11-20T12:00:00+00:00")
                elif change == "future":
                    obs["observed_at"] = "2026-11-20T12:01:00+00:00"
                elif change == "not-current":
                    obs["current"] = False
                elif change == "before-registration":
                    obs["observed_at"] = "2026-11-20T11:59:59+00:00"
                else:
                    obs["source_ref"] = self.record["source_ref"]
                self.assertEqual(self.result(obs=obs)["policy_result"]["decision"], "BLOCKED")

    def test_expiry_or_obsolescence_does_not_revive_command(self):
        config = deepcopy(self.f["spec"])
        config["expires_at"] = "2026-11-20T12:00:02+00:00"
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        self.assertEqual(self.result(record=record)["record"]["state"], "EXPIRED")
        obs = deepcopy(self.obs)
        obs["relevance"] = "OBSOLETE"
        obsolete = self.result(obs=obs)
        self.assertEqual(obsolete["record"]["state"], "OBSOLETE")
        self.assertEqual(obsolete["policy_result"]["decision"], "BLOCKED")
        fresh = deepcopy(self.obs)
        fresh["id"] = "attempt-to-revive"
        self.assertEqual(self.result(record=obsolete["record"], obs=fresh)["record"]["state"], "OBSOLETE")

    def test_completed_goal_closes_without_replaying_old_action(self):
        done = satisfied(self.ready)
        result = recovery.policy.assess(recovery.guard_receipt(done, [self.record], self.now))
        self.assertEqual(result["decision"], "CLOSE")
        self.assertEqual(result["eligible_actions"], [])

    def test_uncertain_effect_requires_reconciliation_before_retry(self):
        config = deepcopy(self.f["spec"])
        config["prior_execution"] = "UNCERTAIN"
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        result = self.result(record=record)
        self.assertEqual(result["record"]["state"], "RECONCILE")
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")
        obs = deepcopy(self.obs)
        obs["prior_result"] = "RECONCILED_NOT_EXECUTED"
        self.assertEqual(self.result(record=record, obs=obs)["policy_result"]["decision"], "CONTINUE")

    def test_verified_effect_is_not_replayed_with_pending_acceptance(self):
        obs = deepcopy(self.obs)
        obs["prior_result"] = "VERIFIED_COMPLETE"
        result = self.result(obs=obs)
        self.assertEqual(result["record"]["state"], "RECONCILE")
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")
        self.assertEqual(self.result(receipt=satisfied(self.ready), obs=obs)["policy_result"]["decision"], "CLOSE")

    def test_duplicate_event_is_idempotent_with_input_or_resolved_receipt(self):
        result = self.result()
        for receipt in (self.ready, result["receipt"]):
            duplicate = self.result(record=result["record"], receipt=receipt)
            self.assertFalse(duplicate["changed"])
            self.assertEqual(duplicate["record"], result["record"])
            self.assertEqual(duplicate["policy_result"]["decision"], "CONTINUE")
        mutated = deepcopy(self.obs)
        mutated["conditions"][0]["state"] = "UNKNOWN"
        with self.assertRaises(recovery.RecoveryError):
            self.result(record=result["record"], obs=mutated)

    def test_old_resolution_does_not_cover_changed_receipt_or_time(self):
        result = self.result()
        changed = deepcopy(result["receipt"])
        changed["actions"][0]["capability"]["source_ref"] = "synthetic:new-state"
        self.assertEqual(recovery.policy.assess(recovery.guard_receipt(changed, [result["record"]], self.now))["decision"], "BLOCKED")
        expired = recovery.guard_receipt(result["receipt"], [result["record"]], "2026-11-20T12:05:00+00:00")
        self.assertEqual(recovery.policy.assess(expired)["decision"], "BLOCKED")

    def test_material_change_invalidation_requires_observation_after_change(self):
        result = self.result()
        invalidated = recovery.invalidate(result["record"], "synthetic:service-changed", "2026-11-20T12:00:03+00:00")
        self.assertEqual(invalidated["state"], "WAITING_CONDITIONS")
        self.assertEqual(invalidated["events"], result["record"]["events"])
        self.assertEqual(recovery.policy.assess(recovery.guard_receipt(result["receipt"], [invalidated], self.now))["decision"], "BLOCKED")
        obs = deepcopy(self.obs)
        obs["id"] = "new-event-old-observation"
        self.assertEqual(self.result(record=invalidated, receipt=result["receipt"], obs=obs)["policy_result"]["decision"], "BLOCKED")
        obs.update(id="new-current-observation", observed_at="2026-11-20T12:00:04+00:00")
        good = self.result(record=invalidated, receipt=result["receipt"], obs=obs, now="2026-11-20T12:00:05+00:00")
        self.assertEqual(good["policy_result"]["decision"], "CONTINUE")

    def test_multiple_corrections_must_each_resolve(self):
        second_spec = deepcopy(self.f["spec"])
        second_spec.update(id="CCR-002", source_ref="synthetic:other-condition")
        second = recovery.register(self.receipt, second_spec, self.f["registered_at"])
        first = self.result()
        guarded = recovery.guard_receipt(first["receipt"], [first["record"], second], self.now)
        self.assertEqual(recovery.policy.assess(guarded)["decision"], "BLOCKED")
        obs = deepcopy(self.obs)
        obs.update(id="other-restored", correction_id="CCR-002")
        next_result = recovery.reassess(second, first["receipt"], obs, self.now)
        both = recovery.guard_receipt(next_result["receipt"], [first["record"], next_result["record"]], self.now)
        self.assertEqual(recovery.policy.assess(both)["decision"], "CONTINUE")

    def test_multiple_correction_projection_is_order_independent(self):
        second_spec = deepcopy(self.f["spec"])
        second_spec.update(id="CCR-002", source_ref="synthetic:other-condition")
        second = recovery.register(self.receipt, second_spec, self.f["registered_at"])
        first = self.result()
        projected = deepcopy(first["receipt"])
        projected["actions"][0]["blocker"] = recovery._guard(first["record"])
        for records in ([second, first["record"]], [first["record"], second]):
            guarded = recovery.guard_receipt(projected, records, self.now)
            self.assertEqual(recovery.policy.assess(guarded)["decision"], "BLOCKED")
            self.assertEqual(guarded["actions"][0]["blocker"]["source_ref"], "bago5:correction:CCR-002")

    def test_newly_observed_revocation_cannot_be_overwritten_by_old_grant(self):
        current = deepcopy(self.ready)
        current["actions"][0]["authorization"]["state"] = "REVOKED"
        current["actions"][0]["authorization"]["source_ref"] = "synthetic:revocation-not-the-original-grant"
        revoked = self.result(receipt=current)
        obs = deepcopy(self.obs)
        obs["id"] = "retry-with-old-grant"
        retried = self.result(record=revoked["record"], obs=obs)
        self.assertEqual(retried["policy_result"]["decision"], "BLOCKED")
        renewed = deepcopy(self.ready)
        renewed["actions"][0]["authorization"]["source_ref"] = "synthetic:grant-after-revocation"
        self.assertEqual(self.result(record=revoked["record"], receipt=renewed, obs=obs)["policy_result"]["decision"], "CONTINUE")

    def test_newly_observed_uncertainty_cannot_be_reset_to_not_run(self):
        obs = deepcopy(self.obs)
        obs["prior_result"] = "UNCERTAIN"
        uncertain = self.result(obs=obs)
        retry = deepcopy(self.obs)
        retry["id"] = "retry-without-reconciliation"
        self.assertEqual(self.result(record=uncertain["record"], obs=retry)["policy_result"]["decision"], "BLOCKED")
        retry["prior_result"] = "RECONCILED_NOT_EXECUTED"
        self.assertEqual(self.result(record=uncertain["record"], obs=retry)["policy_result"]["decision"], "CONTINUE")

    def test_material_change_while_waiting_blocks_older_observation_and_is_idempotent(self):
        changed = recovery.invalidate(self.record, "synthetic:changed", "2026-11-20T12:00:04+00:00")
        duplicate = recovery.invalidate(changed, "synthetic:changed", "2026-11-20T12:00:04+00:00")
        self.assertEqual(changed, duplicate)
        self.assertEqual(len(changed["invalidations"]), 1)
        old = self.result(record=changed, now="2026-11-20T12:00:05+00:00")
        self.assertEqual(old["policy_result"]["decision"], "BLOCKED")
        fresh = deepcopy(self.obs)
        fresh.update(id="fresh-after-change", observed_at="2026-11-20T12:00:05+00:00")
        self.assertEqual(self.result(record=changed, obs=fresh, now="2026-11-20T12:00:06+00:00")["policy_result"]["decision"], "CONTINUE")

    def test_older_positive_observation_cannot_override_newer_failure(self):
        failed = deepcopy(self.obs)
        failed.update(id="new-failure", observed_at="2026-11-20T12:00:04+00:00")
        failed["conditions"][0]["state"] = "UNSATISFIED"
        known = self.result(obs=failed, now="2026-11-20T12:00:05+00:00")
        old = self.result(record=known["record"], now="2026-11-20T12:00:06+00:00")
        self.assertEqual(old["policy_result"]["decision"], "BLOCKED")
        fresh = deepcopy(self.obs)
        fresh.update(id="new-restoration", observed_at="2026-11-20T12:00:06+00:00")
        self.assertEqual(self.result(record=known["record"], obs=fresh, now="2026-11-20T12:00:07+00:00")["policy_result"]["decision"], "CONTINUE")

    def test_future_rejected_observation_does_not_poison_freshness_watermark(self):
        future = deepcopy(self.obs)
        future.update(id="future-time", observed_at="2026-11-20T13:00:00+00:00", valid_until="2026-11-20T13:05:00+00:00")
        known = self.result(obs=future)
        self.assertEqual(known["policy_result"]["decision"], "BLOCKED")
        self.assertEqual(self.result(record=known["record"])["policy_result"]["decision"], "CONTINUE")

    def test_invalidation_records_revocation_and_all_prior_grant_references(self):
        resolved = self.result()
        revoked = deepcopy(resolved["receipt"])
        revoked["actions"][0]["authorization"].update(state="REVOKED", source_ref="synthetic:permission-revoked-now")
        changed = recovery.invalidate(resolved["record"], "synthetic:new-receipt", self.now, receipt=revoked)
        obs = deepcopy(self.obs)
        obs.update(id="after-revocation", observed_at=self.now)
        self.assertEqual(self.result(record=changed, obs=obs)["policy_result"]["decision"], "BLOCKED")
        renewed = deepcopy(self.ready)
        renewed["actions"][0]["authorization"]["source_ref"] = "synthetic:current-new-grant"
        permitted = self.result(record=changed, receipt=renewed, obs=obs)
        self.assertEqual(permitted["policy_result"]["decision"], "CONTINUE")
        obs["id"] = "reuse-current-new-grant"
        self.assertEqual(self.result(record=permitted["record"], receipt=renewed, obs=obs)["policy_result"]["decision"], "CONTINUE")

    def test_prohibition_uses_restriction_authority_separate_from_action_permission(self):
        config = deepcopy(self.f["spec"])
        config.update(cause_kind="PROHIBITION", restriction_source_type="HOST_PERMISSION")
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        obs = deepcopy(self.obs)
        authority = deepcopy(self.ready["actions"][0]["authorization"])
        authority["source_ref"] = "synthetic:restriction-lift"
        obs["restriction_resolution"] = {"restriction_ref": config["source_ref"], "authority": authority}
        self.assertEqual(self.result(record=record, obs=obs)["record"]["state"], "PROHIBITED")
        authority["source_type"] = "HOST_PERMISSION"
        self.assertEqual(self.result(record=record, obs=obs)["policy_result"]["decision"], "CONTINUE")
        config["restriction_source_type"] = "USER_INSTRUCTION"
        user_record = recovery.register(self.receipt, config, self.f["registered_at"])
        authority["source_type"] = "EXPLICIT_APPROVAL"
        self.assertEqual(self.result(record=user_record, obs=obs)["policy_result"]["decision"], "CONTINUE")
        del config["restriction_source_type"]
        with self.assertRaises(recovery.RecoveryError):
            recovery.register(self.receipt, config, self.f["registered_at"])

    def test_uncertainty_observed_during_prohibition_survives_lifting(self):
        config = deepcopy(self.f["spec"])
        config.update(cause_kind="PROHIBITION", restriction_source_type="USER_INSTRUCTION")
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        obs = deepcopy(self.obs)
        obs["prior_result"] = "UNCERTAIN"
        uncertain = self.result(record=record, obs=obs)
        self.assertEqual(uncertain["record"]["state"], "PROHIBITED")
        lifted = deepcopy(self.obs)
        lifted["id"] = "prohibition-lifted"
        authority = deepcopy(self.ready["actions"][0]["authorization"])
        authority["source_ref"] = "synthetic:explicit-lift"
        lifted["restriction_resolution"] = {"restriction_ref": record["source_ref"], "authority": authority}
        self.assertEqual(self.result(record=uncertain["record"], obs=lifted)["record"]["state"], "RECONCILE")
        lifted["prior_result"] = "RECONCILED_NOT_EXECUTED"
        self.assertEqual(self.result(record=uncertain["record"], obs=lifted)["policy_result"]["decision"], "CONTINUE")

    def test_verified_complete_effect_cannot_be_reset_to_not_run(self):
        obs = deepcopy(self.obs)
        obs["prior_result"] = "VERIFIED_COMPLETE"
        completed = self.result(obs=obs)
        retry = deepcopy(self.obs)
        retry["id"] = "retry-completed"
        for prior in ("NOT_RUN", "RECONCILED_NOT_EXECUTED"):
            retry["prior_result"] = prior
            self.assertEqual(self.result(record=completed["record"], obs=retry)["record"]["state"], "RECONCILE")

    def test_replacements_cannot_leave_an_intermediate_action_executable(self):
        one = deepcopy(self.ready)
        one["actions"][0]["id"] = "replacement-one"
        obs = deepcopy(self.obs)
        obs["action_id"] = "replacement-one"
        first = self.result(receipt=one, obs=obs)
        two = deepcopy(first["receipt"])
        added = deepcopy(two["actions"][0])
        added["id"] = "replacement-two"
        two["actions"].append(added)
        obs.update(id="second-replacement", action_id="replacement-two")
        with self.assertRaises(recovery.RecoveryError):
            self.result(record=first["record"], receipt=two, obs=obs)
        two["actions"] = [added]
        self.assertEqual(self.result(record=first["record"], receipt=two, obs=obs)["policy_result"]["decision"], "CONTINUE")

    def new_binding(self, receipt):
        result = deepcopy(receipt)
        old = result["binding"]
        new = {**old, "candidate_id": "synthetic-new-candidate", "session_id": "synthetic-new-session"}
        def replace(value):
            if isinstance(value, dict):
                if value == old:
                    return deepcopy(new)
                return {k: replace(v) for k, v in value.items()}
            if isinstance(value, list):
                return [replace(v) for v in value]
            return value
        return replace(result)

    def test_rebind_preserves_prohibition_without_reusing_old_proof_or_permission(self):
        config = deepcopy(self.f["spec"])
        config.update(cause_kind="PROHIBITION", restriction_source_type="HOST_PERMISSION")
        record = recovery.register(self.receipt, config, self.f["registered_at"])
        new = self.new_binding(self.ready)
        rebound = recovery.rebind(record, new, self.now)
        self.assertEqual(rebound["state"], "PROHIBITED")
        self.assertIsNone(rebound["resolution"])
        self.assertEqual(rebound["criterion_ids"], record["criterion_ids"])
        self.assertEqual(recovery.policy.assess(recovery.guard_receipt(new, [rebound], self.now))["decision"], "BLOCKED")
        with self.assertRaises(recovery.RecoveryError):
            self.result(record=rebound, receipt=new)
        obs = deepcopy(self.obs)
        obs.update(binding=deepcopy(new["binding"]), observed_at=self.now)
        authority = deepcopy(new["actions"][0]["authorization"])
        authority.update(source_type="HOST_PERMISSION", source_ref="synthetic:host-lift-new-scope")
        obs["restriction_resolution"] = {"restriction_ref": record["source_ref"], "authority": authority}
        restored = self.result(record=rebound, receipt=new, obs=obs)
        self.assertEqual(restored["policy_result"]["decision"], "CONTINUE")
        self.assertEqual(restored["receipt"]["actions"][0]["authorization"], new["actions"][0]["authorization"])

    def test_rebind_carries_negative_authority_refs_and_rejects_other_goals(self):
        denied = deepcopy(self.ready)
        denied["actions"][0]["authorization"].update(state="DENIED", source_ref="synthetic:explicit-denial")
        changed = recovery.invalidate(self.record, "synthetic:denial-observed", self.now, receipt=denied)
        new = self.new_binding(self.ready)
        rebound = recovery.rebind(changed, new, self.now)
        self.assertIn(self.record["initial_authorization"]["source_ref"], rebound["invalidated_authority_refs"])
        obs = deepcopy(self.obs)
        obs.update(binding=deepcopy(new["binding"]), observed_at=self.now)
        self.assertEqual(self.result(record=rebound, receipt=new, obs=obs)["policy_result"]["decision"], "BLOCKED")
        new["actions"][0]["authorization"]["source_ref"] = "synthetic:new-candidate-permission"
        self.assertEqual(self.result(record=rebound, receipt=new, obs=obs)["policy_result"]["decision"], "CONTINUE")
        bad = deepcopy(new)
        old_binding = deepcopy(bad["binding"])
        for key in ("project_id", "mission_id", "goal_id", "goal_revision"):
            modified = deepcopy(bad)
            replacement = "different" if key != "goal_revision" else old_binding[key] + 1
            def swap(value):
                if isinstance(value, dict):
                    if value == old_binding:
                        value[key] = replacement
                    else:
                        for child in value.values():
                            swap(child)
                elif isinstance(value, list):
                    for child in value:
                        swap(child)
            swap(modified)
            with self.assertRaises(recovery.RecoveryError):
                recovery.rebind(changed, modified, self.now)

    def test_rebind_without_action_retains_correction_until_explicit_future_route(self):
        new = self.new_binding(self.ready)
        later = deepcopy(new)
        new["actions"] = []
        rebound = recovery.rebind(self.record, new, self.now)
        self.assertEqual(rebound["initial_authorization"]["state"], "UNKNOWN")
        later["actions"][0]["id"] = "new-explicit-route"
        guarded = recovery.guard_receipt(later, [rebound], self.now)
        self.assertEqual(recovery.policy.assess(guarded)["decision"], "BLOCKED")
        obs = deepcopy(self.obs)
        obs.update(binding=deepcopy(later["binding"]), action_id="new-explicit-route", observed_at=self.now)
        self.assertEqual(self.result(record=rebound, receipt=later, obs=obs)["policy_result"]["decision"], "CONTINUE")

    def test_rebind_does_not_claim_ownership_of_an_independent_new_blocker(self):
        new = self.new_binding(self.ready)
        other = {"reason": "Another independent restriction.", "source_ref": "synthetic:other-restriction",
                 "intervention": "Resolve this distinct restriction.", "basis": "INSTRUCTION", "current": True}
        new["actions"][0]["blocker"] = deepcopy(other)
        rebound = recovery.rebind(self.record, new, self.now)
        self.assertEqual(rebound["initial_blocker"], self.record["initial_blocker"])
        obs = deepcopy(self.obs)
        obs.update(binding=deepcopy(new["binding"]), observed_at=self.now)
        result = self.result(record=rebound, receipt=new, obs=obs)
        self.assertEqual(result["receipt"]["actions"][0]["blocker"], other)
        self.assertEqual(result["policy_result"]["decision"], "BLOCKED")

    def test_rebind_preserves_expired_obsolete_and_uncertain_states(self):
        new = self.new_binding(self.ready)
        for state in ("EXPIRED", "OBSOLETE", "RECONCILE"):
            record = deepcopy(self.record)
            record["state"] = state
            if state == "RECONCILE":
                record["prior_execution"] = "UNCERTAIN"
            rebound = recovery.rebind(record, new, self.now)
            self.assertEqual(rebound["state"], state)
            self.assertEqual(recovery.policy.assess(recovery.guard_receipt(new, [rebound], self.now))["decision"], "BLOCKED")

    def test_inputs_are_not_mutated_and_history_is_separate_from_current_evidence(self):
        before = deepcopy((self.record, self.ready, self.obs))
        result = self.result()
        self.assertEqual((self.record, self.ready, self.obs), before)
        self.assertEqual(result["receipt"]["evidence"], [])
        self.assertEqual(len(result["record"]["events"]), 1)

    def test_strict_boolean_and_condition_conservation(self):
        for value in (1, "true", None):
            obs = deepcopy(self.obs)
            obs["current"] = value
            with self.assertRaises(recovery.RecoveryError):
                self.result(obs=obs)
        obs = deepcopy(self.obs)
        obs["conditions"] = []
        with self.assertRaises(recovery.RecoveryError):
            self.result(obs=obs)

    def test_malformed_control_and_unrepresentable_timestamp_use_recovery_error(self):
        for state in ([], {}, 1, None):
            invalid = deepcopy(self.ready)
            invalid["control"]["state"] = state
            with self.assertRaises(recovery.RecoveryError):
                self.result(receipt=invalid)
        obs = deepcopy(self.obs)
        obs["observed_at"] = "0001-01-01T00:00:00+14:00"
        with self.assertRaises(recovery.RecoveryError):
            self.result(obs=obs)

    def test_packaged_schema_matches_spec_observation_and_records(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema unavailable; runtime remains stdlib-only")
        schema = json.loads((SKILL / "references/behavior-recovery.schema.json").read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        jsonschema.Draft202012Validator.check_schema(schema)
        invalidated = recovery.invalidate(self.record, "synthetic:change", self.now, receipt=self.ready)
        rebound = recovery.rebind(invalidated, self.new_binding(self.ready), self.now)
        prohibited = {**self.f["spec"], "cause_kind": "PROHIBITION", "restriction_source_type": "HOST_PERMISSION"}
        prohibited_record = recovery.register(self.receipt, prohibited, self.f["registered_at"])
        for value in (self.f["spec"], self.obs, self.record, self.result()["record"], invalidated,
                      rebound, prohibited, prohibited_record):
            validator.validate(value)
        del prohibited["restriction_source_type"]
        self.assertFalse(validator.is_valid(prohibited))

    def test_maximum_length_identifiers_still_generate_valid_v1_guards(self):
        config = deepcopy(self.f["spec"])
        config.update(id="c" * 10000, reason="r" * 10000)
        record = recovery.register(self.ready, config, self.f["registered_at"])
        current = deepcopy(self.ready)
        current["actions"][0]["blocker"] = None
        guarded = recovery.guard_receipt(current, [record], self.now)
        result = recovery.policy.assess(guarded)
        self.assertNotEqual(result.get("validation"), "INVALID")
        self.assertEqual(result["decision"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
