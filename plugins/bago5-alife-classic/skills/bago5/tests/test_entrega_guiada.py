import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / 'skills/bago5/references'


class EntregaGuiadaTests(unittest.TestCase):
    def test_reachable_from_entry_and_implementation_routes(self):
        protocol = REF / 'entrega-guiada.md'
        self.assertTrue(protocol.is_file())
        for name in ('bago5', 'bago5-desarrollo', 'bago5-aplicaciones-juegos'):
            skill = ROOT / 'skills' / name / 'SKILL.md'
            self.assertIn('entrega-guiada.md', skill.read_text(encoding='utf-8'))

    def test_vectors_have_distinct_ids_and_expected_outcomes(self):
        data = json.loads((REF / 'entrega-guiada-vectores.json').read_text(encoding='utf-8'))
        cases = data['escenarios']
        self.assertEqual([c['id'] for c in cases], [f'GUIA-{i:02d}' for i in range(1, 10)])
        self.assertTrue(all(c['entrada'] and c['esperado'] for c in cases))


if __name__ == '__main__':
    unittest.main()
