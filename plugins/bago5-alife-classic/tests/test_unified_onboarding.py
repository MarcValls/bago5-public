import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Onboarding(unittest.TestCase):
    def test_apps_and_scopes(self):
        apps = json.loads((ROOT / '.app.json').read_bytes())['apps']
        self.assertEqual(apps, {
            'alife-gestor-nativo': {'id':'asdk_app_6b033b078db08191bc467fb08c71189a'},
            'alife-memoria-viva': {'id':'asdk_app_6b0339c22c3481919cce222512431e0e'},
        })
        for name in ('plugin.json', '.codex-plugin/plugin.json'):
            manifest = json.loads((ROOT / name).read_text())
            config = manifest['extensions']['com.openai'] if name == 'plugin.json' else manifest
            self.assertEqual(config['apps'], './.app.json')
            self.assertFalse(config.get('requires_local_executor', False))
        for name in ('bago5', 'bago5-memoria-viva'):
            config = (ROOT / 'skills' / name / 'agents/openai.yaml').read_text()
            self.assertNotIn('dependencies:', config)
        active = json.loads((ROOT / 'mcp.json').read_text())['mcpServers']
        expected = {
            'alife-gestor-nativo': ('https://alifememories.com/mcp/gestor', 'bago5-chatgpt-gestor', 'manager.read'),
            'alife-memoria-viva': ('https://alifememories.com/mcp', 'bago5-chatgpt-memoria', 'memory.read'),
        }
        self.assertEqual(set(active), set(expected))
        for name, (url, client, scope) in expected.items():
            server = active[name]
            self.assertEqual(server['url'], url)
            self.assertEqual(server['type'], 'streamable-http')
            auth = server['extensions']['com.openai']['auth']
            self.assertEqual(auth['client'], {'mode':'provided','clientId':client,'tokenEndpointAuthMethod':'none'})
            self.assertEqual(auth['type'], 'oauth')
            self.assertEqual(auth['baseScopes'], [scope])
            expected_scopes = [scope, 'memory.write'] if name == 'alife-memoria-viva' else [scope]
            self.assertEqual(auth['defaultScopes'], expected_scopes)
        self.assertEqual(set(apps), set(active))
        compat = json.loads((ROOT / '.mcp.json').read_bytes())['mcpServers']
        self.assertEqual(compat, {name: {**server, 'headers': {}} for name, server in active.items()})
        candidate = json.loads((ROOT / 'integrations/alife/mcp.candidate.json').read_bytes())
        self.assertEqual(candidate, json.loads((ROOT / 'mcp.json').read_bytes()))


    def test_welcome(self):
        manifests = [json.loads((ROOT / name).read_bytes()) for name in ("plugin.json", ".codex-plugin/plugin.json")]
        prompts = [manifests[0]["extensions"]["com.openai"]["interface"]["defaultPrompt"], manifests[1]["interface"]["defaultPrompt"]]
        self.assertEqual(prompts[0], prompts[1])
        for option in ("crear mi memoria", "conectar una", "sin memoria"):
            self.assertIn(option, prompts[0])
        self.assertIn("https://alifememories.com/memoria-viva", (ROOT / "skills/bago5/SKILL.md").read_text(encoding="utf-8"))

if __name__ == "__main__":
    unittest.main()
