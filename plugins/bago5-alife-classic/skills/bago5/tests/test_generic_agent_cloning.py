"""Configuración y dispatch reales con estado temporal; NO ejecutan workers."""
from __future__ import annotations

import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
API = ROOT / (
    "optional-runtime/bago-operating-suite/runtime/BAGO-4.11.10/"
    "backend/.bago/api"
)
BACKEND = API.parents[1]


class Response:
    """Transporte en memoria; serializers y handlers son los del paquete."""
    def __init__(self):
        self.status = None
        self.headers = {}
        self.wfile = io.BytesIO()

    def send_response(self, status):
        self.status = status

    def send_header(self, key, value):
        self.headers[key] = value

    def _send_cors_headers(self):
        pass

    def end_headers(self):
        pass

    def result(self):
        return self.status, json.loads(self.wfile.getvalue())


class AgentTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = ExitStack()
        cls.addClassCleanup(cls.context.close)
        # Restaurar módulos y sys.path incluso si falla un test o la importación.
        # No dejar mocks de bago_core contaminando las demás suites.
        cls.context.enter_context(patch.dict(sys.modules))
        cls.context.enter_context(patch.object(sys, "path", [str(API), str(BACKEND), *sys.path]))
        core = BACKEND / ".bago/core"
        roots = {p.stem for directory in (API, core) for p in directory.glob("*.py")}
        roots.update(p.name for p in core.iterdir() if p.is_dir() and (p / "__init__.py").is_file())
        roots.add("bago_core")
        for name in list(sys.modules):
            if name.split(".")[0] in roots:
                sys.modules.pop(name)
        cls.helper = importlib.import_module("generic_agent_template")
        cls.api = importlib.import_module("handlers_agents")
        cls.dispatch = importlib.import_module("api_dispatch")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "skills/bago5-auditoria").mkdir(parents=True)
        (root / "skills/bago5-auditoria/SKILL.md").write_text("---\nname: bago5-auditoria\n---\n")
        cat = root / "CATALOGO_HABILIDADES.json"
        cat.write_text(json.dumps({"skills": [{"new_name": "bago5-auditoria",
                                               "scope": "publica",
                                               "new_path": "skills/bago5-auditoria/SKILL.md"}]}))
        self.patches = [patch.object(self.helper, "PLUGIN_ROOT", root),
                        patch.object(self.helper, "CATALOG_PATH", cat),
                        patch.object(self.api, "AGENTS_STATE_DIR", root / ".bago/state/agents"),
                        patch.dict(os.environ, {"BAGO_USER_ROOT": str(root / "user"),
                                                "BAGO_STATE_ROOT": str(root / "user/state")})]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def request(self, function, *args):
        h = Response()
        function(h, *args)
        return h.result()

    def route(self, method, path, body=None):
        h = Response()
        resolve = getattr(self.dispatch, "resolve_" + method.lower())
        if method in ("POST", "PUT"):
            matched, function = resolve(h, path, body or {})
            self.assertTrue(matched)
            function(h, body or {})
        else:
            matched, function = resolve(h, path)
            self.assertTrue(matched)
            function(h)
        return h.result()

    def test_template_is_virtual_disabled_and_unskilled(self):
        code, payload = self.request(self.api.handle_get_list)
        self.assertEqual(code, 200)
        self.assertEqual(payload["agents"], [])
        base = payload["templates"][0]
        self.assertEqual(base["id"], self.helper.TEMPLATE_ID)
        self.assertFalse(base["enabled"])
        self.assertEqual(base["skills"], [])
        self.assertEqual(base["sandboxMode"], "read-only")

    def test_two_clones_independent_with_no_permissions_or_skills(self):
        c1, a1 = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        c2, a2 = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        self.assertEqual((c1, c2), (201, 201))
        x, y = a1["agent"], a2["agent"]
        self.assertNotEqual(x["id"], y["id"])
        for a in (x, y):
            self.assertFalse(a["enabled"])
            self.assertEqual(a["skills"], [])
            self.assertEqual(a["systemPrompt"], "")
            self.assertEqual(a["provider"], "")
            self.assertEqual(a["templateId"], self.helper.TEMPLATE_ID)
        path = self.api.AGENTS_STATE_DIR / "agents_registry.json"
        self.assertEqual(len(json.loads(path.read_text())["agents"]), 2)

    def test_assign_known_skill_only_to_one_clone_and_revoke(self):
        _, a1 = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        _, a2 = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        first = a1["agent"]
        code, payload = self.request(self.api.handle_put, {"revision": "1", "skills": ["$bago5-auditoria"]}, first["id"])
        self.assertEqual(code, 200)
        self.assertEqual(payload["agent"]["skills"], ["$bago5-auditoria"])
        self.assertEqual(self.request(self.api.handle_get, a2["agent"]["id"])[1]["agent"]["skills"], [])
        self.assertEqual(self.request(self.api.handle_put,
                                      {"revision": "2", "skills": []}, first["id"])[1]["agent"]["skills"], [])

    def test_reject_undeclared_skill_without_persisting(self):
        _, response = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        agent = response["agent"]
        code, payload = self.request(self.api.handle_put, {"skills": ["$bago5-inventada"]}, agent["id"])
        self.assertEqual(code, 400)
        self.assertEqual(payload["code"], "INVALID_SKILL_BINDING")
        self.assertEqual(self.request(self.api.handle_get, agent["id"])[1]["agent"]["revision"], "1")

    def test_duplicate_of_configured_generic_resets_bindings(self):
        _, created = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        agent_id = created["agent"]["id"]
        self.request(self.api.handle_put, {"skills": ["bago5-auditoria"], "enabled": True,
                                               "systemPrompt": "private"}, agent_id)
        code, resp = self.request(self.api.handle_duplicate, agent_id)
        self.assertEqual(code, 201)
        fresh = resp["agent"]
        self.assertFalse(fresh["enabled"])
        self.assertEqual(fresh["skills"], [])
        self.assertEqual(fresh["systemPrompt"], "")

    def test_legacy_create_still_works_and_template_cannot_be_edited(self):
        self.assertEqual(self.request(self.api.handle_post, {"name": "legacy"})[0], 201)
        self.assertEqual(self.request(self.api.handle_put, {"skills": []}, self.helper.TEMPLATE_ID)[0], 404)

    def test_missing_catalog_blocks_new_bindings_but_allows_revocation(self):
        _, created = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        ident = created["agent"]["id"]
        with patch.object(self.helper, "CATALOG_PATH", Path(self.tmp.name) / "missing.json"):
            self.assertEqual(self.request(self.api.handle_put,
                                          {"skills": ["$bago5-auditoria"]}, ident)[0], 400)
            self.assertEqual(self.request(self.api.handle_put,
                                          {"skills": []}, ident)[0], 200)

    def test_legacy_duplicate_keeps_preexisting_contract(self):
        _, created = self.request(self.api.handle_post, {"name": "legacy", "systemPrompt": "legacy prompt"})
        ident = created["agent"]["id"]
        code, cloned = self.request(self.api.handle_duplicate, ident)
        self.assertEqual(code, 201)
        self.assertEqual(cloned["agent"]["systemPrompt"], "legacy prompt")
        self.assertEqual(cloned["agent"]["name"], "legacy (copy)")

    def test_revision_conflict_and_bad_types(self):
        _, created = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        ident = created["agent"]["id"]
        self.assertEqual(self.request(self.api.handle_put, {"revision": "7", "skills": []}, ident)[0], 409)
        self.assertEqual(self.request(self.api.handle_put, {"skills": "bago5-auditoria"}, ident)[0], 400)

    def test_real_catalog_and_dispatch_preserve_clone_boundaries(self):
        with patch.object(self.helper, "PLUGIN_ROOT", ROOT), patch.object(
            self.helper, "CATALOG_PATH", ROOT / "skills/bago5/references/CATALOGO_HABILIDADES.json"
        ):
            available = self.helper.available_skills()
            self.assertIn("bago5-plan-por-fases", available)
            self.assertIn("bago5-auditoria", available)
            self.assertNotIn("bago5", available)
            self.assertEqual(self.route("GET", "/agents")[1]["agents"], [])
            self.assertEqual(self.route("GET", "/agents/bago5-generic")[0], 200)
            code, first = self.route("POST", "/agents/bago5-generic/duplicate")
            self.assertEqual(code, 201)
            _, second = self.route("POST", "/agents/bago5-generic/duplicate")
            first_id, second_id = first["agent"]["id"], second["agent"]["id"]
            self.assertNotEqual(first_id, second_id)
            code, bound = self.route("PUT", f"/agents/{first_id}", {
                "revision": "1", "skills": ["bago5-plan-por-fases"],
                "sandboxMode": "unrestricted", "templateId": "injected", "authority": "full",
            })
            self.assertEqual(code, 200)
            self.assertEqual(bound["agent"]["skills"], ["$bago5-plan-por-fases"])
            self.assertFalse(bound["agent"]["enabled"])
            self.assertEqual(bound["agent"]["templateId"], self.helper.TEMPLATE_ID)
            self.assertEqual(bound["agent"]["sandboxMode"], "read-only")
            self.assertNotIn("authority", bound["agent"])
            self.assertEqual(self.route("GET", f"/agents/{second_id}")[1]["agent"]["skills"], [])
            self.assertEqual(self.route("PUT", f"/agents/{first_id}", {
                "revision": "1", "skills": [],
            })[0], 409)
            self.assertEqual(self.route("PUT", f"/agents/{first_id}", {
                "revision": "2", "skills": [],
            })[1]["agent"]["skills"], [])
            self.assertEqual(self.route("DELETE", "/agents/bago5-generic")[0], 404)
            self.assertEqual(self.route("DELETE", f"/agents/{first_id}")[0], 200)
            self.assertEqual(self.route("GET", f"/agents/{first_id}")[0], 404)
            self.assertEqual(self.route("GET", f"/agents/{second_id}")[0], 200)

    def test_invalid_bindings_leave_persistent_bytes_unchanged(self):
        _, created = self.request(self.api.handle_duplicate, self.helper.TEMPLATE_ID)
        ident = created["agent"]["id"]
        registry = self.api.AGENTS_STATE_DIR / "agents_registry.json"
        before = registry.read_bytes()
        for invalid in (["bago5-auditoria", "$bago5-auditoria"], [None],
                        ["bago5-auditoria"] * 33, {"skill": "bago5-auditoria"},
                        ["bago5-local-gobierno"]):
            with self.subTest(invalid=invalid):
                self.assertEqual(self.route("PUT", f"/agents/{ident}", {"skills": invalid})[0], 400)
                self.assertEqual(registry.read_bytes(), before)

    def test_catalog_rejects_malformed_and_outside_sources(self):
        catalog = self.helper.CATALOG_PATH
        for data in (None, [], {"skills": {}}, {"skills": []}):
            with self.subTest(data=data):
                catalog.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(self.helper.SkillBindingError):
                    self.helper.validate_skill_bindings(["bago5-auditoria"])
        (Path(self.tmp.name) / "outside.md").write_text("outside", encoding="utf-8")
        catalog.write_text(json.dumps({"skills": [{
            "new_name": "bago5-auditoria", "scope": "publica",
            "new_path": "skills/../outside.md",
        }]}), encoding="utf-8")
        with self.assertRaises(self.helper.SkillBindingError):
            self.helper.validate_skill_bindings(["bago5-auditoria"])
        self.assertEqual(self.helper.validate_skill_bindings([]), [])


if __name__ == "__main__":
    unittest.main()
