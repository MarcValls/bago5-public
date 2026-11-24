import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DeliveryContractTest(unittest.TestCase):
    def test_trigger_and_absolute_last(self):
        x=(ROOT/'SKILL.md').read_text(encoding='utf8')
        self.assertIn('TODA respuesta',x)
        self.assertIn('final absoluto',x)
        self.assertIn('DESPUÉS de `NOTA FINAL`',x)
    def test_reference(self):
        x=(ROOT/'references/PROTOCOLO_VERSIONES_Y_ENLACES.md').read_text(encoding='utf8')
        for s in ('VERSIONES.md','SHA256SUMS.txt','LEEME.md','NO_RECUPERADO','Carpeta'):
            self.assertIn(s,x)
    def test_vectors(self):
        v=json.loads((ROOT/'references/ACCEPTANCE.json').read_text(encoding='utf8'))
        self.assertEqual(len(v['cases']),12)
        self.assertEqual(len({x['id'] for x in v['cases']}),12)
    def test_frontmatter(self):
        self.assertTrue((ROOT/'SKILL.md').read_text(encoding='utf8').startswith('---\nname: bago5-entrega-paquetes'))
if __name__=='__main__': unittest.main()
