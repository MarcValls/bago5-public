"""Recovery of a locally archived checkpoint, without resetting its ledger."""
from copy import deepcopy
import importlib
from pathlib import Path
import sys
import tempfile
import unittest

import test_session_acceptance as fixtures

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/bago5-ganchos-sesion/scripts"))
engine = importlib.import_module("session_engine")


class RecoveryRegression(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix="bago5-recovery-")
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.receipt = fixtures.session_receipt()
        self.state = engine.apply_command(None, {
            "op": "INIT", "host": "CODEX", "host_session_id": self.receipt["binding"]["session_id"],
            "workspace_root": self.root, "receipt": self.receipt,
            "source_ref": "synthetic:scope", "persistence": {"authorized": True, "source_ref": "synthetic:storage"},
        }, now=fixtures.NOW)["state"]
        self.binding = fixtures.selected_memory_binding(self.state["binding"])
        self.cmd("SELECT_MEMORY", memory_binding=self.binding)
        self.payload = {"title": "Synthetic checkpoint", "content": "Observed material advance.",
                        "project_id": self.binding["project_id"], "kind": "context", "status": "active",
                        "source": "synthetic:evidence", "tags": [], "pinned": False,
                        "archived": False, "decision_closed": False}
        self.record = {**self.payload, "id": "synthetic-record", "version": 1}

    def cmd(self, op, **fields):
        result = engine.apply_command(self.state, {"op": op, "source_ref": "synthetic:current-instruction", **fields}, now=fixtures.NOW)
        self.state = result["state"]
        return result["result"]

    def event(self, kind, **fields):
        result = engine.handle_event(self.state, {
            "host": "CODEX", "host_session_id": self.state["host_session_id"], "cwd": self.root,
            "event": kind, **fields,
        }, now=fixtures.NOW)
        self.state = result["state"]
        return result["result"]

    def call(self, op, args, call_id, response):
        name = self.binding["tools"][op]
        result = self.event("BEFORE_TOOL", tool_name=name, arguments=args, call_id=call_id)
        self.assertEqual(result["action"], "ALLOW", result)
        return self.event("AFTER_TOOL", tool_name=name, arguments=args, call_id=call_id, response=response)

    def test_clear_and_explicit_reselection_recovers_inflight_without_resending(self):
        self.call("search_memories", {"project_id": self.binding["project_id"]}, "search-before", {"memories": []})
        self.cmd("PREPARE_CHECKPOINT", event_id="material-event", payload=self.payload, material=True)
        pre = self.event("BEFORE_TOOL", tool_name=self.binding["tools"]["save_memory"],
                         arguments=self.payload, call_id="original-save")
        self.assertEqual(pre["action"], "ALLOW")
        self.event("SESSION_START", source="clear")
        self.assertIsNone(self.state["memory"])
        self.cmd("SET_RECEIPT", receipt=self.receipt)
        self.cmd("SELECT_MEMORY", memory_binding=self.binding)
        self.assertEqual(self.state["memory"]["pending"]["status"], "IN_FLIGHT")
        again = self.event("BEFORE_TOOL", tool_name=self.binding["tools"]["save_memory"],
                           arguments=self.payload, call_id="forbidden-retry")
        self.assertEqual(again["action"], "DENY")
        self.call("search_memories", {"project_id": self.binding["project_id"]}, "search-reconcile", {"memories": [self.record]})
        result = self.call("get_memory", {"id": self.record["id"]}, "read-reconcile", {"memory": self.record})
        self.assertEqual(result["checkpoint_status"], "VERIFIED")
        self.assertNotIn("forbidden-retry", self.state["memory"]["calls"])
        self.assertEqual(self.state["memory"]["events"]["material-event"]["status"], "VERIFIED")

    def test_identical_edit_does_not_prepare_a_redundant_revision(self):
        self.call("search_memories", {"project_id": self.binding["project_id"]}, "search", {"memories": [self.record]})
        self.call("get_memory", {"id": self.record["id"]}, "read", {"memory": self.record})
        before = deepcopy(self.state["memory"])
        payload = {**self.payload, "id": self.record["id"], "expected_version": 1}
        result = self.cmd("PREPARE_CHECKPOINT", event_id="noop", payload=payload,
                          changes={"content": self.payload["content"]}, material=True)
        self.assertEqual(result["checkpoint_status"], "SKIP")
        self.assertEqual(self.state["memory"], before)


if __name__ == "__main__":
    unittest.main()
