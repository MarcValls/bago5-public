import copy
import datetime as dt
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "scripts" / "target_preflight.py"
spec = importlib.util.spec_from_file_location("target_preflight", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
NOW = dt.datetime(2026, 11, 17, 12, 0, tzinfo=dt.timezone.utc)

def valid():
    return {"action_id": "prepare-hosting", "target": {"id": "hosting-A", "environment": "staging"},
            "required_facts": ["php_version"], "observations": [{"fact": "php_version",
            "action_id": "prepare-hosting", "target_id": "hosting-A", "environment": "staging",
            "source_type": "authenticated_panel", "source_ref": "panel/php", "captured_at": "2026-11-17T11:59:00Z",
            "observed": "8.5", "expected": "8.5"}]}

class Tests(unittest.TestCase):
    def decision(self, value):
        return module.assess(value, NOW)["decision"]

    def test_fresh_target_observation(self):
        self.assertEqual(self.decision(valid()), "READY_FOR_DEPENDENT_WORK")

    def test_old_memory_cannot_set_host_runtime(self):
        x = valid(); x["observations"][0].update(source_type="historical_memory", observed="7.4")
        self.assertEqual(self.decision(x), "BLOCKED")

    def test_local_docker_is_not_hosting(self):
        x = valid(); x["observations"][0].update(environment="local", source_type="target_probe", observed="7.4")
        self.assertEqual(self.decision(x), "BLOCKED")

    def test_provider_availability_is_not_installed(self):
        x = valid(); x["observations"][0]["source_type"] = "vendor_catalog"
        self.assertEqual(self.decision(x), "BLOCKED")

    def test_stale_or_wrong_action_is_blocked(self):
        x = valid(); x["observations"][0]["captured_at"] = "2026-11-17T11:00:00Z"
        self.assertEqual(self.decision(x), "BLOCKED")
        x = valid(); x["observations"][0]["action_id"] = "other"
        self.assertEqual(self.decision(x), "BLOCKED")

    def test_conflicts_and_missing_source_are_blocked(self):
        for change in ({"observed": "7.4"}, {"source_ref": ""}, {"conflict": True}, {"captured_at": "bad"}):
            x = valid(); x["observations"][0].update(change)
            self.assertEqual(self.decision(x), "BLOCKED")

    def test_missing_duplicate_and_excessive_ttl_are_blocked(self):
        x = valid(); x["observations"] = []
        self.assertEqual(self.decision(x), "BLOCKED")
        x = valid(); x["observations"].append(copy.deepcopy(x["observations"][0]))
        self.assertEqual(self.decision(x), "BLOCKED")
        x = valid(); x["max_age_seconds"] = 999999
        self.assertEqual(self.decision(x), "BLOCKED")

if __name__ == "__main__":
    unittest.main()
