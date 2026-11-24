"""Independent acceptance checks for the session-hook increment.

These assertions check the consolidated ALIFE inventory and exercise the
actual runtime observer against real package bytes. They do not authenticate a
host, install hooks, access memory services, or execute a mission. State,
permission, scope and closure scenarios exercise the agreed public engine API.
"""
from __future__ import annotations

from copy import deepcopy
from contextlib import ExitStack
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
BASELINE_PORTABLE_SKILLS = frozenset(['bago5', 'bago5-acceso-motor-local', 'bago5-alife-vault', 'bago5-aplicaciones-locales', 'bago5-auditoria', 'bago5-ciclo-contexto', 'bago5-cognitivo', 'bago5-control-acciones', 'bago5-dictamen-promocion', 'bago5-documentos', 'bago5-entrega-paquetes', 'bago5-espacio-m', 'bago5-ingenieria-repositorios', 'bago5-integridad-evidencias', 'bago5-interfaces', 'bago5-lectura-carpeta', 'bago5-locucion', 'bago5-matematicas', 'bago5-memoria-codex', 'bago5-memoria-viva', 'bago5-monitor-actividad', 'bago5-plan-por-fases', 'bago5-pruebas-python', 'bago5-repositorios-github', 'bago5-verificacion'])
RETIRED_PROJECT_SKILLS = frozenset({
    "mythos", "mythos-alife-memory", "codex-memory-handoff-mythos",
    "bago5-mythos", "bago5-mythos-alife-memory",
    "bago5-codex-memory-handoff-mythos",
})
GOVERNED_APP_BINDINGS = {'apps': {'alife-memoria-viva': {'id': 'asdk_app_6b0339c22c3481919cce222512431e0e'}, 'alife-gestor-nativo': {'id': 'asdk_app_6b033b078db08191bc467fb08c71189a'}}}
BRIDGE_REL = Path("skills/bago5/scripts/runtime_turn_decision.py")
SUITE_REL = Path("optional-runtime/bago-operating-suite")
NOW = "2026-11-19T12:00:00+00:00"


def session_receipt(host="CODEX"):
    """Two original obligations prevent an omission test being merely malformed."""
    fixture = ROOT / "skills/bago5/tests/fixtures/turn-decision/continue-work.json"
    receipt = json.loads(fixture.read_text())
    receipt["current_host"] = host
    receipt["actions"][0]["target_host"] = host
    baseline = deepcopy(receipt["baseline_criteria"][0])
    baseline.update(id="preserve-evidence", description="Preserve the requested evidence.")
    receipt["baseline_criteria"].append(baseline)
    criterion = deepcopy(receipt["criteria"][0])
    criterion.update(baseline)
    receipt["criteria"].append(criterion)
    action = deepcopy(receipt["actions"][0])
    action.update(id="preserve-requested-evidence", criterion_ids=["preserve-evidence"])
    receipt["actions"].append(action)
    return receipt


def completed_receipt(receipt):
    result = deepcopy(receipt)
    result["evidence"] = []
    for criterion in result["criteria"]:
        evidence_id = "observed-" + criterion["id"]
        criterion.update(status="PASS", evidence_ids=[evidence_id])
        result["evidence"].append({
            "id": evidence_id, "criterion_id": criterion["id"],
            "binding": deepcopy(result["binding"]), "kind": "OBSERVATION",
            "outcome": "PASS", "source_ref": "synthetic-acceptance:" + evidence_id,
            "origin_id": evidence_id, "derived_from": [],
        })
    return result


def selected_memory_binding(context):
    destination = {
        "store_id": "synthetic-store-a", "owner_id": "synthetic-owner-a",
        "connector_id": "synthetic-connector-a", "project_id": "synthetic-memory-project-a",
    }
    return {
        **destination, "mode": "READ_WRITE",
        "tools": {
            "search_memories": "mcp__synthetic_a__search_memories",
            "get_memory": "mcp__synthetic_a__get_memory",
            "save_memory": "mcp__synthetic_a__save_memory",
        },
        "identity": {
            "verified": True,
            **{key: destination[key] for key in ("store_id", "owner_id", "connector_id")},
            "source_ref": "synthetic-acceptance:host-identity-observation",
        },
        "authorization": {
            "binding": deepcopy(context), "destination": deepcopy(destination),
            "read": True, "write": True,
            "source_ref": "synthetic-acceptance:user-authorizes-selected-destination",
            "expires_at": "2026-11-19T13:00:00+00:00",
        },
    }


def load_bridge(root: Path) -> dict:
    # run_name deliberately avoids the CLI branch. No suite code is imported.
    return runpy.run_path(str(root / BRIDGE_REL), run_name="acceptance_observer")


def declared_skills(root: Path) -> dict[Path, str]:
    result = {}
    for path in sorted(root.rglob("SKILL.md")):
        text = path.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        if frontmatter is None:
            continue  # Included historical module documentation is not a skill.
        match = re.search(r"(?m)^name:\s*([^\r\n]+)$", frontmatter[1])
        if match is None:
            raise AssertionError(f"Skill frontmatter lacks a name: {path}")
        result[path.relative_to(root)] = match[1].strip().strip("\"'")
    return result


class PackageConservationAcceptance(unittest.TestCase):
    def test_all_live_skills_keep_the_required_unique_prefix(self):
        skills = declared_skills(ROOT)
        self.assertEqual(set(skills.values()), BASELINE_PORTABLE_SKILLS)
        self.assertEqual(len(skills), len(set(skills.values())))
        for relative, name in skills.items():
            with self.subTest(path=str(relative)):
                if relative == Path("skills/bago5/SKILL.md"):
                    self.assertEqual(name, "bago5")
                else:
                    self.assertRegex(name, r"\Abago5-[a-z0-9]+(?:-[a-z0-9]+)*\Z")
                if relative.parent.parent.name == "skills":
                    self.assertEqual(relative.parent.name, name)

    def test_published_capabilities_remain_and_mythos_stays_unlinked(self):
        names = {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual(len(BASELINE_PORTABLE_SKILLS), 25)
        self.assertTrue(BASELINE_PORTABLE_SKILLS <= names,
                        sorted(BASELINE_PORTABLE_SKILLS - names))
        self.assertFalse(RETIRED_PROJECT_SKILLS & names)

    def test_canonical_routes_resolve_without_duplicate_invocations(self):
        registry = json.loads((ROOT / "skills/bago5/references/ROUTES.json").read_text())
        commands = [item["command"] for item in registry["routes"]]
        self.assertEqual(len(commands), len(set(commands)))
        invocations = registry["skill_invocations"]
        self.assertEqual(len(invocations), len({item["invoke"] for item in invocations}))
        self.assertEqual(len(invocations), len({item["target"] for item in invocations}))
        actual_targets = {path.relative_to(ROOT).as_posix()
                          for path in (ROOT / "skills").glob("*/SKILL.md")}
        self.assertEqual({item["target"] for item in invocations}, actual_targets)
        for item in invocations:
            with self.subTest(target=item["target"]):
                self.assertEqual(item["invoke"], "$" + Path(item["target"]).parent.name)
                if item["target"] == "skills/bago5/SKILL.md":
                    self.assertEqual(item["invoke"], "$bago5")
                else:
                    self.assertTrue(item["invoke"].startswith("$bago5-"))
        for item in registry["routes"]:
            target = item.get("target", "")
            if target.endswith("/SKILL.md"):
                self.assertTrue((ROOT / target).is_file(), target)
                self.assertNotIn(Path(target).parent.name, RETIRED_PROJECT_SKILLS)

    def test_app_identity_and_manifest_versions_remain_consistent(self):
        self.assertEqual(json.loads((ROOT / ".app.json").read_bytes()), GOVERNED_APP_BINDINGS)
        portable = json.loads((ROOT / "plugin.json").read_text())
        compatibility = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        self.assertEqual(portable["name"], "bago5-governed-classic")
        self.assertEqual(compatibility["name"], portable["name"])
        self.assertEqual(compatibility["version"], portable["version"])
        self.assertEqual(portable["extensions"]["com.openai"]["apps"], "./.app.json")
        self.assertEqual(compatibility["apps"], "./.app.json")
        self.assertRegex(portable["version"], r"\A\d+\.\d+\.\d+\Z")


class RuntimePinAcceptance(unittest.TestCase):
    def test_pin_matches_the_actual_packaged_identity(self):
        bridge = load_bridge(ROOT)
        digest = hashlib.sha256((ROOT / SUITE_REL / "PACKAGE_IDENTITY.json").read_bytes()).hexdigest()
        self.assertEqual(bridge["PINNED_IDENTITY_SHA256"], digest)

    def test_actual_packaged_suite_is_observed_without_execution(self):
        bridge = load_bridge(ROOT)
        result = bridge["inspect_suite"](ROOT / SUITE_REL)
        self.assertEqual(result["status"], "VERIFIED")
        self.assertEqual(Path(result["root"]), (ROOT / SUITE_REL).resolve())
        self.assertIn("not host authorization or functioning", result["scope"])

    def _temporary_plugin_copy(self, directory: str) -> Path:
        copy = Path(directory) / "plugin"
        (copy / BRIDGE_REL).parent.mkdir(parents=True)
        shutil.copyfile(ROOT / BRIDGE_REL, copy / BRIDGE_REL)
        shutil.copytree(ROOT / SUITE_REL, copy / SUITE_REL,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return copy

    def test_modified_payload_is_rejected_with_the_identity_unchanged(self):
        with tempfile.TemporaryDirectory(prefix="bago5_acceptance_payload_") as temporary:
            copy = self._temporary_plugin_copy(temporary)
            entry = copy / SUITE_REL / "scripts" / "suite_identity.py"
            entry.write_bytes(entry.read_bytes() + b"\nUnauthorized payload change.\n")
            bridge = load_bridge(copy)
            with self.assertRaisesRegex(bridge["ObservationError"], "suite_payload_changed"):
                bridge["inspect_suite"](copy / SUITE_REL)

    def test_modified_identity_is_rejected_before_acceptance(self):
        with tempfile.TemporaryDirectory(prefix="bago5_acceptance_identity_") as temporary:
            copy = self._temporary_plugin_copy(temporary)
            identity = copy / SUITE_REL / "PACKAGE_IDENTITY.json"
            identity.write_bytes(identity.read_bytes() + b"\n")
            bridge = load_bridge(copy)
            with self.assertRaisesRegex(bridge["ObservationError"], "suite_identity_pin_mismatch"):
                bridge["inspect_suite"](copy / SUITE_REL)


class MemoryBoundaryAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "skills/bago5-ganchos-sesion/scripts"))
        cls.guard = importlib.import_module("memory_guard")

    def setUp(self):
        self.context = deepcopy(session_receipt()["binding"])
        self.binding = selected_memory_binding(self.context)
        self.memory = self.guard.select_memory(self.binding, self.context, now=NOW)
        self.payload = {
            "title": "Synthetic acceptance checkpoint",
            "content": "A material result from an isolated acceptance fixture.",
            "project_id": self.binding["project_id"], "kind": "context", "status": "active",
            "source": "synthetic-acceptance:material-observation", "tags": ["acceptance"],
            "pinned": False, "archived": False, "decision_closed": False,
        }

    def call(self, memory, operation, arguments, call_id, response):
        name = self.binding["tools"][operation]
        before = self.guard.before_tool(memory, self.context, name, arguments,
                                         call_id, now=NOW)
        self.assertEqual(before["decision"], "ALLOW", before.get("reason"))
        return self.guard.after_tool(before["state"], self.context, name, arguments,
                                      call_id, response, now=NOW)

    def accepted_save(self):
        searched = self.call(self.memory, "search_memories",
                             {"project_id": self.binding["project_id"], "query": self.payload["title"]},
                             "search-1", {"memories": []})
        prepared = self.guard.prepare_checkpoint(searched["state"], self.context, "material-1",
                                                  self.payload, "synthetic-acceptance:material-1", now=NOW)
        self.assertEqual(prepared["decision"], "PREPARED")
        record = {**deepcopy(self.payload), "id": "synthetic-memory-1", "version": 1,
                  "owner_id": self.binding["owner_id"]}
        saved = self.call(prepared["state"], "save_memory", self.payload,
                         "save-1", {"memory": record})
        self.assertEqual(saved["status"], "EXECUTED")
        return saved["state"], record

    def test_permission_is_bound_to_every_destination_dimension(self):
        for field in ("store_id", "owner_id", "connector_id", "project_id"):
            with self.subTest(field=field):
                foreign = deepcopy(self.binding)
                foreign[field] += "-other"
                if field in foreign["identity"]:
                    foreign["identity"][field] = foreign[field]
                with self.assertRaises(self.guard.MemoryGuardError):
                    self.guard.select_memory(foreign, self.context, now=NOW)

    def test_new_binding_cannot_reuse_cached_ids_from_previous_destination(self):
        changed = deepcopy(self.memory)
        changed["known_ids"] = ["old-store-record"]
        for field in ("store_id", "owner_id", "connector_id", "project_id"):
            value = changed["binding"][field] + "-other"
            changed["binding"][field] = value
            changed["binding"]["authorization"]["destination"][field] = value
            if field in changed["binding"]["identity"]:
                changed["binding"]["identity"][field] = value
        result = self.guard.before_tool(
            changed, self.context, self.binding["tools"]["get_memory"],
            {"id": "old-store-record"}, "foreign-get", now=NOW)
        self.assertEqual(result["decision"], "DENY")

    def test_accepted_save_is_not_verified_without_separate_readback(self):
        saved, _record = self.accepted_save()
        self.assertEqual(saved["pending"]["status"], "EXECUTED")
        self.assertNotEqual(saved["events"]["material-1"]["status"], "VERIFIED")

    def test_stop_after_accepted_save_prevents_a_goodbye_readback(self):
        saved, record = self.accepted_save()
        before = deepcopy(saved)
        denied = self.guard.before_tool(
            saved, self.context, self.binding["tools"]["get_memory"],
            {"id": record["id"]}, "readback-after-stop", control="STOP", now=NOW)
        self.assertEqual(denied["decision"], "DENY")
        self.assertEqual(saved, before)
        self.assertEqual(denied["state"]["pending"]["status"], "EXECUTED")

    def test_readback_verifies_then_duplicate_checkpoint_performs_no_new_save(self):
        saved, record = self.accepted_save()
        verified = self.call(saved, "get_memory", {"id": record["id"]},
                             "readback-1", {"memory": record})
        self.assertEqual(verified["status"], "VERIFIED")
        duplicate = self.guard.prepare_checkpoint(
            verified["state"], self.context, "material-1", self.payload,
            "synthetic-acceptance:material-1", now=NOW)
        self.assertEqual(duplicate["decision"], "SKIP")
        self.assertEqual(duplicate["state"]["events"]["material-1"]["status"], "VERIFIED")

    def test_wrong_readback_cannot_claim_the_requested_checkpoint(self):
        saved, record = self.accepted_save()
        record["content"] = "Different content that does not satisfy the checkpoint."
        result = self.call(saved, "get_memory", {"id": record["id"]},
                           "readback-different", {"memory": record})
        self.assertNotEqual(result.get("status"), "VERIFIED")
        self.assertEqual(result["decision"], "DENY")

    def test_memory_guard_uses_no_file_network_or_process_io(self):
        # Real services are not replaced with fabricated success. The test checks
        # a pure transition sequence whose explicit inputs are synthetic results.
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "socket.socket", "subprocess.run"):
                stack.enter_context(patch(target, side_effect=AssertionError("I/O attempted: " + target)))
            saved, record = self.accepted_save()
            result = self.call(saved, "get_memory", {"id": record["id"]},
                               "readback-no-io", {"memory": record})
            self.assertEqual(result["status"], "VERIFIED")


class NativeEventMeaningAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "skills/bago5-ganchos-sesion/scripts"))
        cls.native = importlib.import_module("native_hooks")

    def test_native_stop_means_turn_close_and_cannot_be_user_stop(self):
        event = self.native.normalize(
            {"hook_event_name": "Stop", "session_id": "synthetic-host-session",
             "cwd": str(ROOT), "last_assistant_message": "STOP", "grant_permission": True},
            "CODEX", "Stop")
        self.assertEqual(event["event"], "BEFORE_TURN_CLOSE")
        self.assertNotIn("grant_permission", event)
        self.assertNotIn("last_assistant_message", event)

    def test_session_start_resume_does_not_become_explicit_resume(self):
        event = self.native.normalize(
            {"hook_event_name": "SessionStart", "session_id": "synthetic-host-session",
             "cwd": str(ROOT), "source": "resume"}, "CODEX", "SessionStart")
        self.assertEqual(event["event"], "SESSION_START")
        self.assertEqual(event["source"], "resume")
        self.assertNotEqual(event["event"], "RESUME_EXPLICIT")


class SessionControlAcceptance(unittest.TestCase):
    """Public API scenarios fixed from the contract before engine implementation."""

    @classmethod
    def setUpClass(cls):
        scripts = ROOT / "skills/bago5-ganchos-sesion/scripts"
        sys.path.insert(0, str(scripts))
        cls.engine = importlib.import_module("session_engine")

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="bago5_acceptance_session_")
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name) / "project-one"
        self.workspace.mkdir()
        self.receipt = session_receipt()
        self.init = {
            "op": "INIT", "host": "CODEX",
            "host_session_id": self.receipt["binding"]["session_id"],
            "workspace_root": str(self.workspace.resolve()),
            "receipt": deepcopy(self.receipt),
            "source_ref": "synthetic-acceptance:explicit-session-selection",
            "persistence": {
                "authorized": True,
                "source_ref": "synthetic-acceptance:explicit-local-state-request",
            },
        }
        self.state = self.engine.apply_command(None, deepcopy(self.init), now=NOW)["state"]

    def command(self, state, op, **fields):
        command = {"op": op, "source_ref": "synthetic-acceptance:current-user-instruction", **fields}
        return self.engine.apply_command(state, command, now=NOW)

    def event(self, event, **fields):
        return {
            "event": event, "host": "CODEX",
            "host_session_id": self.init["host_session_id"],
            "cwd": self.init["workspace_root"], **fields,
        }

    def authority(self, binding=None):
        return {
            "state": "ALLOWED", "source_type": "USER_INSTRUCTION", "current": True,
            "binding": deepcopy(binding or self.state["binding"]),
            "source_ref": "synthetic-acceptance:explicit-resume-instruction",
        }

    def running_control(self, binding=None):
        return {
            "state": "RUNNING", "current": True,
            "binding": deepcopy(binding or self.state["binding"]),
            "source_ref": "synthetic-acceptance:current-control-observation",
        }

    def continuity_command(self):
        binding = self.state["binding"]
        return {
            "op": "PREPARE_CONTINUITY",
            "source_ref": "synthetic-acceptance:explicit-continuity-request",
            "architecture": "Use the existing project controller and selected host tools.",
            "resume_steps": ["Verify the selected project, current control and permissions."],
            "invariants": ["Preserve original objective and mandatory acceptance criteria."],
            "handoff": {
                "project_id": binding["project_id"], "mission_id": binding["mission_id"],
                "candidate": binding["candidate_id"], "operation": "VERIFICATION",
                "scope": binding["scope_id"],
                "acceptance": [item["description"] for item in self.receipt["baseline_criteria"]],
                "stop_status": "NOT_STOPPED",
                "sources": [{"ref": "synthetic-acceptance:original-request", "version": "1", "retrieved": True}],
                "decisions": [], "evidence": [], "status": "PROPOSED",
                "pending": [item["id"] for item in self.receipt["criteria"]],
                "resumption_authorized": False,
            },
        }

    def test_initialization_requires_explicit_persistence_intent(self):
        command = deepcopy(self.init)
        command["persistence"]["authorized"] = False
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(None, command, now=NOW)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_init_cannot_overwrite_an_existing_selected_session(self):
        before = deepcopy(self.state)
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(self.state, deepcopy(self.init), now=NOW)
        self.assertEqual(self.state, before)

    def test_init_cannot_replay_a_receipt_from_a_different_host_session(self):
        command = deepcopy(self.init)
        command["host_session_id"] = "a-different-real-host-session"
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(None, command, now=NOW)

    def test_session_recovery_cannot_resume_a_stopped_mission(self):
        stopped = self.command(self.state, "STOP")["state"]
        self.assertEqual(stopped["control"]["state"], "STOP")
        for source in ("startup", "resume", "compact", "fork"):
            with self.subTest(source=source):
                observed = self.engine.handle_event(
                    stopped, self.event("SESSION_START", source=source), now=NOW)
                self.assertEqual(observed["state"]["control"]["state"], "STOP")
                self.assertEqual(observed["result"]["action"], "STOP")

    def test_resume_prompt_is_delivered_without_releasing_stop(self):
        stopped = self.command(self.state, "STOP")["state"]
        native = importlib.import_module("native_hooks")
        observed = []

        def engine(event):
            result = self.engine.handle_event(stopped, event, now=NOW)
            observed.append(result)
            return result["result"]

        payload = {
            "hook_event_name": "UserPromptSubmit",
            "session_id": self.init["host_session_id"], "cwd": self.init["workspace_root"],
            "prompt": "reanuda explícitamente el trabajo de este proyecto",
        }
        output, _ = native.dispatch(json.dumps(payload).encode(), "CODEX", "UserPromptSubmit", engine)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0]["state"]["control"]["state"], "STOP")
        self.assertEqual(observed[0]["result"]["action"], "NOTICE")
        self.assertIsNot(output.get("continue"), False)
        self.assertEqual(output["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("STOP", output["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(stopped["control"]["state"], "STOP")

    def test_native_turn_close_still_halts_after_a_resume_request(self):
        stopped = self.command(self.state, "STOP")["state"]
        requested = self.engine.handle_event(
            stopped, self.event("USER_PROMPT", prompt="reanuda el trabajo"), now=NOW)["state"]
        native = importlib.import_module("native_hooks")
        payload = {
            "hook_event_name": "Stop", "session_id": self.init["host_session_id"],
            "cwd": self.init["workspace_root"], "stop_hook_active": False,
        }
        output, _ = native.dispatch(
            json.dumps(payload).encode(), "CODEX", "Stop",
            lambda event: self.engine.handle_event(requested, event, now=NOW)["result"])
        self.assertIs(output.get("continue"), False)
        self.assertIn("stopReason", output)
        self.assertEqual(requested["control"]["state"], "STOP")

    def test_set_receipt_cannot_clear_stop(self):
        stopped = self.command(self.state, "STOP")["state"]
        before = deepcopy(stopped)
        with self.assertRaises(self.engine.HookError):
            self.command(stopped, "SET_RECEIPT", receipt=deepcopy(self.receipt))
        self.assertEqual(stopped, before)

    def test_resume_rejects_stale_or_foreign_authority(self):
        stopped = self.command(self.state, "STOP")["state"]
        cases = []
        stale = self.authority()
        stale["current"] = False
        cases.append(stale)
        foreign = self.authority()
        foreign["binding"]["session_id"] = "different-session"
        cases.append(foreign)
        memory_claim = self.authority()
        memory_claim["source_type"] = "MEMORY"
        cases.append(memory_claim)
        for authority in cases:
            with self.subTest(authority=authority):
                with self.assertRaises(self.engine.HookError):
                    self.command(stopped, "RESUME", authority=authority,
                                 control=self.running_control())
                self.assertEqual(stopped["control"]["state"], "STOP")

    def test_current_explicit_resume_preserves_the_original_scope(self):
        stopped = self.command(self.state, "STOP")["state"]
        resumed = self.command(stopped, "RESUME", authority=self.authority(),
                               control=self.running_control())["state"]
        self.assertEqual(resumed["control"]["state"], "RUNNING")
        self.assertEqual(resumed["binding"], self.state["binding"])
        self.assertIsNone(resumed["memory"])

    def test_a_new_receipt_cannot_replace_the_original_goal(self):
        replacement = deepcopy(self.receipt)
        replacement["goal"].update(baseline="Different goal", current="Different goal")
        with self.assertRaises(self.engine.HookError):
            self.command(self.state, "SET_RECEIPT", receipt=replacement)
        self.assertEqual(self.state["binding"], self.receipt["binding"])

    def test_a_valid_smaller_receipt_cannot_drop_an_original_obligation(self):
        replacement = deepcopy(self.receipt)
        replacement["baseline_criteria"] = replacement["baseline_criteria"][:1]
        replacement["criteria"] = replacement["criteria"][:1]
        replacement["actions"] = replacement["actions"][:1]
        with self.assertRaises(self.engine.HookError):
            self.command(self.state, "SET_RECEIPT", receipt=replacement)

    def test_same_id_cannot_weaken_its_original_acceptance_definition(self):
        replacement = deepcopy(self.receipt)
        replacement["baseline_criteria"][0]["expected_basis"] = "DECLARATION"
        replacement["criteria"][0]["expected_basis"] = "DECLARATION"
        with self.assertRaises(self.engine.HookError):
            self.command(self.state, "SET_RECEIPT", receipt=replacement)

    def test_project_switch_cannot_reset_anchors_or_detach_controller_in_same_scope(self):
        initial = deepcopy(self.init)
        initial["runtime_selection"] = {
            "state_dir": str(self.workspace.parent / "existing-controller"),
            "workspace_root": initial["workspace_root"], "expected_state_sha256": "a" * 64,
            "source_ref": "synthetic-acceptance:selected-existing-controller",
        }
        selected = self.engine.apply_command(None, initial, now=NOW)["state"]
        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority())
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(selected, switch, now=NOW)
        self.assertEqual(selected["runtime_selection"], initial["runtime_selection"])

    def test_relabeling_scope_cannot_detach_the_same_native_mission(self):
        initial = deepcopy(self.init)
        initial["runtime_selection"] = {
            "state_dir": str(self.workspace.parent / "existing-controller"),
            "workspace_root": initial["workspace_root"], "expected_state_sha256": "a" * 64,
            "source_ref": "synthetic-acceptance:selected-existing-controller",
        }
        selected = self.engine.apply_command(None, initial, now=NOW)["state"]
        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority())

        def relabel(value):
            if isinstance(value, dict):
                return {key: "relabelled-scope" if key == "scope_id" else relabel(item)
                        for key, item in value.items()}
            if isinstance(value, list):
                return [relabel(item) for item in value]
            return value

        switch["receipt"] = relabel(switch["receipt"])
        self.assertEqual(switch["receipt"]["binding"]["mission_id"], selected["binding"]["mission_id"])
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(selected, switch, now=NOW)

    def test_scope_relabel_cannot_weaken_acceptance_of_the_same_original_goal(self):
        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority())

        def relabel(value):
            if isinstance(value, dict):
                return {key: "relabelled-scope" if key == "scope_id" else relabel(item)
                        for key, item in value.items()}
            if isinstance(value, list):
                return [relabel(item) for item in value]
            return value

        switch["receipt"] = relabel(switch["receipt"])
        switch["receipt"]["baseline_criteria"][0]["expected_basis"] = "DECLARATION"
        switch["receipt"]["criteria"][0]["expected_basis"] = "DECLARATION"
        self.assertEqual(switch["receipt"]["binding"]["goal_id"], self.state["binding"]["goal_id"])
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(self.state, switch, now=NOW)

    def test_foreign_workspace_is_rejected_before_runtime_observation(self):
        initial = deepcopy(self.init)
        initial["runtime_selection"] = {
            "state_dir": str(self.workspace.parent / "existing-controller"),
            "workspace_root": initial["workspace_root"], "expected_state_sha256": "a" * 64,
            "source_ref": "synthetic-acceptance:selected-existing-controller",
        }
        selected = self.engine.apply_command(None, initial, now=NOW)["state"]
        store = importlib.import_module("session_store")
        data_dir = self.workspace.parent / "authorized-state-surface"
        with store.transaction(str(data_dir), initial["host"], initial["host_session_id"], create=True) as transaction:
            transaction.save(selected)
        event = self.event("BEFORE_TOOL", tool_name="mcp__synthetic_a__get_memory",
                           arguments={"id": "synthetic-memory"}, call_id="foreign-workspace-call")
        event["cwd"] = str(self.workspace.parent / "different-project")
        with patch.dict(os.environ, {"PLUGIN_DATA": str(data_dir)}):
            with patch.object(self.engine, "_runtime_check", return_value=None) as observation:
                try:
                    result = self.engine.run_native(event)
                except self.engine.HookError as error:
                    self.assertIn("SCOPE", error.code)
                else:
                    self.assertIn(result["action"], {"DENY", "BLOCKED"})
                self.assertEqual(observation.call_count, 0,
                                 "Foreign workspace reached runtime observation before scope validation.")

    def test_bound_auxiliary_tool_is_denied_on_scope_error_with_a_custom_name(self):
        memory = selected_memory_binding(self.state["binding"])
        memory["tools"]["identity"] = "synthetic_service__current_account"
        selected = self.command(self.state, "SELECT_MEMORY", memory_binding=memory)["state"]
        store = importlib.import_module("session_store")
        data_dir = self.workspace.parent / "authorized-state-surface"
        with store.transaction(str(data_dir), self.init["host"], self.init["host_session_id"], create=True) as transaction:
            transaction.save(selected)
        payload = {
            "hook_event_name": "PreToolUse", "session_id": self.init["host_session_id"],
            "cwd": str(self.workspace.parent / "different-project"),
            "tool_name": memory["tools"]["identity"], "tool_input": {},
            "tool_use_id": "synthetic-foreign-scope-identity",
        }
        native = importlib.import_module("native_hooks")
        with patch.dict(os.environ, {"PLUGIN_DATA": str(data_dir)}):
            output, _ = native.dispatch(json.dumps(payload).encode(), "CODEX", "PreToolUse", self.engine.run_native)
        self.assertEqual(output["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("SCOPE", output["hookSpecificOutput"]["permissionDecisionReason"])

    def test_project_switch_to_a_new_scope_invalidates_memory_and_old_authority(self):
        selected = self.command(self.state, "SELECT_MEMORY",
                                memory_binding=selected_memory_binding(self.state["binding"]))["state"]
        new_binding = deepcopy(self.state["binding"])
        new_binding.update(project_id="synthetic-project-two", mission_id="synthetic-mission-two",
                           goal_id="synthetic-goal-two", candidate_id="synthetic-candidate-two",
                           scope_id="synthetic-scope-two")

        def rebind(value):
            if isinstance(value, dict):
                if set(value) == set(new_binding):
                    return deepcopy(new_binding)
                return {key: rebind(item) for key, item in value.items()}
            if isinstance(value, list):
                return [rebind(item) for item in value]
            return value

        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority(),
                      workspace_root=str(self.workspace.parent / "project-two"),
                      receipt=rebind(self.receipt))
        result = self.engine.apply_command(selected, switch, now=NOW)["state"]
        self.assertEqual(result["binding"], new_binding)
        self.assertIsNone(result["memory"])
        self.assertEqual(len(result["memory_history"]), 1)
        self.assertEqual(result["memory_history"][0]["context"], self.state["binding"])

    def test_a_project_switch_does_not_lift_stop(self):
        stopped = self.command(self.state, "STOP")["state"]
        switch = deepcopy(self.init)
        switch.update(op="PROJECT_SWITCH", authority=self.authority())
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(stopped, switch, now=NOW)
        self.assertEqual(stopped["control"]["state"], "STOP")

    def test_continuity_preserves_original_ids_and_cannot_transfer_authority(self):
        result = self.engine.apply_command(self.state, self.continuity_command(), now=NOW)
        packet = result["state"]["continuity"]
        self.assertEqual(packet["binding"], self.receipt["binding"])
        self.assertEqual(packet["goal"], self.receipt["goal"])
        self.assertEqual(packet["baseline_criteria"], self.receipt["baseline_criteria"])
        self.assertEqual(packet["criteria"], self.receipt["criteria"])
        self.assertFalse(packet["handoff"]["resumption_authorized"])
        self.assertEqual(packet["execution"], "NOT_RUN_AT_RECIPIENT")

    def test_continuity_cannot_discard_an_original_acceptance_criterion(self):
        command = self.continuity_command()
        command["handoff"]["acceptance"] = command["handoff"]["acceptance"][:1]
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(self.state, command, now=NOW)

    def test_continuity_rejects_violations_of_existing_handoff_schema(self):
        # These constraints come from bago5/references/HANDOFF.schema.json.
        invalid = []
        command = self.continuity_command()
        command["handoff"]["operation"] = "DELETE_ALL"
        invalid.append(command)
        command = self.continuity_command()
        command["handoff"]["scope"] = {"unexpected": "object"}
        invalid.append(command)
        command = self.continuity_command()
        command["handoff"]["sources"][0]["retrieved"] = "true"
        invalid.append(command)
        command = self.continuity_command()
        command["handoff"]["undeclared_authority"] = True
        invalid.append(command)
        for command in invalid:
            with self.subTest(handoff=command["handoff"]):
                with self.assertRaises(self.engine.HookError):
                    self.engine.apply_command(self.state, command, now=NOW)

    def test_continuity_explicit_resumption_permission_is_rejected(self):
        command = self.continuity_command()
        command["handoff"]["resumption_authorized"] = True
        with self.assertRaises(self.engine.HookError):
            self.engine.apply_command(self.state, command, now=NOW)

    def test_before_close_continues_available_local_work_without_memory(self):
        self.assertIsNone(self.state["memory"])
        result = self.engine.handle_event(
            self.state, self.event("BEFORE_TURN_CLOSE"), now=NOW)
        self.assertEqual(result["result"]["action"], "CONTINUE")

    def test_before_close_closes_only_after_original_obligations_are_satisfied(self):
        updated = self.command(self.state, "SET_RECEIPT",
                               receipt=completed_receipt(self.receipt))["state"]
        result = self.engine.handle_event(
            updated, self.event("BEFORE_TURN_CLOSE"), now=NOW)
        self.assertEqual(result["result"]["action"], "CLOSE")

    def test_stop_overrides_a_completed_receipt_at_turn_close(self):
        updated = self.command(self.state, "SET_RECEIPT",
                               receipt=completed_receipt(self.receipt))["state"]
        stopped = self.command(updated, "STOP")["state"]
        result = self.engine.handle_event(
            stopped, self.event("BEFORE_TURN_CLOSE"), now=NOW)
        self.assertEqual(result["result"]["action"], "STOP")


if __name__ == "__main__":
    unittest.main()
