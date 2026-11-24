import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / 'skills/bago5/references'


class AutonomiaStructureTests(unittest.TestCase):
    def test_scenarios_are_distinct_and_have_observables(self):
        vectors = json.loads((REF / 'autonomia-vectores.json').read_text(encoding='utf-8'))
        cases = vectors['casos']
        self.assertGreaterEqual(len(cases), 13)
        self.assertTrue({'AUT-%02d' % i for i in range(1, 14)} <= {c['id'] for c in cases})
        self.assertEqual(len({c['id'] for c in cases}), len(cases))
        for case in cases:
            self.assertTrue(case['escenario'].strip())
            self.assertGreaterEqual(len(case['esperado']), 2)
            self.assertTrue(all(x.strip() for x in case['esperado']))

    def test_entry_points_refer_to_existing_protocol(self):
        self.assertTrue((REF / 'autonomia-recuperacion.md').is_file())
        for path in ['skills/bago5/SKILL.md', 'skills/bago5-objetivos/SKILL.md',
                     'skills/bago5-ciclo-contexto/SKILL.md']:
            self.assertIn('autonomia-recuperacion.md', (ROOT / path).read_text(encoding='utf-8'))

    def test_existing_handoff_contract_is_preserved(self):
        schema = json.loads((REF / 'HANDOFF.schema.json').read_text(encoding='utf-8'))
        self.assertIn('stop_status', schema['required'])
        self.assertIn('evidence', schema['required'])
        self.assertIn('pending', schema['required'])


if __name__ == '__main__':
    unittest.main()
