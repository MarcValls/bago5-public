import copy
import importlib.util
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'boolean_audit.py'
spec = importlib.util.spec_from_file_location('boolean_audit', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def claim(expression, **changes):
    names = sorted({n.id for n in __import__('ast').walk(__import__('ast').parse(expression, mode='eval')) if isinstance(n, __import__('ast').Name)})
    result = {'source': 'fixture:1', 'quote': expression, 'context': dict(project='test', referent='switch', time='same', condition='always', modality='fact', scope='v1'), 'atoms': {n: n + ' is a stable boolean' for n in names}, 'expression': expression, 'mapping': 'reviewed', 'assumptions': ['Pure stable booleans']}
    result.update(changes)
    return result


def run(*claims):
    return module.audit({'claims': list(claims)})


def kinds(result):
    return [f['kind'] for f in result['findings']]


class BooleanAuditTests(unittest.TestCase):
    def test_opposites(self):
        r = run(claim('p'), claim('not p'))
        self.assertIn('CONTRADICTION_IN_MODEL', kinds(r))
        self.assertIsNone(r['relations'][0]['joint_witness'])
        self.assertEqual(len(r['truth_tables'][0]['rows']), 2)

    def test_repetition_is_not_contradiction(self):
        r = run(claim('p'), claim('p'))
        self.assertEqual(r['literal_groups'], [['C001', 'C002']])
        self.assertIn('EQUIVALENT_IN_MODEL', kinds(r))
        self.assertNotIn('CONTRADICTION_IN_MODEL', kinds(r))

    def test_double_negation(self):
        self.assertIn('EQUIVALENT_IN_MODEL', kinds(run(claim('not not p'), claim('p'))))

    def test_tautology_is_not_automatic_defect(self):
        r = run(claim('p or not p'))
        self.assertEqual(r['findings'][0]['is_defect'], 'NOT_ESTABLISHED')

    def test_self_contradiction(self):
        self.assertIn('SELF_CONTRADICTION_IN_MODEL', kinds(run(claim('p and not p'))))

    def test_demorgan_counterexample(self):
        r = run(claim('not (p and q)'), claim('not p and not q'))
        self.assertFalse(r['relations'][0]['equivalent_in_model'])
        e = r['relations'][0]['equivalence_counterexample']
        self.assertNotEqual(not(e['p'] and e['q']), not e['p'] and not e['q'])

    def test_demorgan_equivalence(self):
        self.assertIn('EQUIVALENT_IN_MODEL', kinds(run(claim('not (p and q)'), claim('not p or not q'))))

    def test_context_isolation(self):
        a, b = claim('p'), claim('not p')
        b['context']['time'] = 'later'
        self.assertEqual(run(a,b)['pairs_checked'], 0)

    def test_atom_meaning_isolation(self):
        a,b = claim('p'),claim('not p')
        b['atoms']['p'] = 'another fact'
        self.assertEqual(run(a,b)['pairs_checked'], 0)

    def test_assumption_isolation(self):
        a,b = claim('p'),claim('not p')
        b['assumptions'] = ['Different assumption']
        self.assertEqual(run(a,b)['pairs_checked'], 0)

    def test_unreviewed_span_is_preserved(self):
        r = run(claim('p', quote='No vino nadie', mapping='candidate'))
        self.assertEqual(r['coverage'], 'PARTIAL')
        self.assertFalse(r['findings'])
        self.assertEqual(r['inventory'][0]['quote'], 'No vino nadie')

    def test_incomplete_context(self):
        self.assertEqual(run(claim('p', context={}))['coverage'], 'PARTIAL')

    def test_unsafe_or_unsupported_expressions(self):
        for expression in ['f()', 'x.y', 'p == q', '1', 'p + q', 'p & q', '[p]', 'p if q else False', '__import__("os").system("echo BAD")']:
            with self.subTest(expression=expression):
                r = run(claim(expression))
                self.assertEqual(r['coverage'], 'PARTIAL')
                self.assertFalse(r['truth_tables'])

    def test_invalid_expression(self):
        a = claim('p'); a['expression'] = 'p and'
        self.assertEqual(run(a)['coverage'], 'PARTIAL')

    def test_constants(self):
        self.assertIn('SELF_CONTRADICTION_IN_MODEL', kinds(run(claim('False'))))
        self.assertIn('TAUTOLOGY_IN_MODEL', kinds(run(claim('True'))))

    def test_normalization_preserves_polarity(self):
        r = run(claim('p', quote='\ufeffA\r\nB'), claim('p', quote='A\nB'), claim('not p', quote='No A\nB'))
        self.assertEqual(r['normalized_groups'], [['C001', 'C002']])
        self.assertFalse(r['literal_groups'])
        self.assertNotEqual(r['inventory'][0]['quote_sha256'], r['inventory'][1]['quote_sha256'])

    def test_joint_inconsistency_without_pair_conflict(self):
        r = run(claim('p or q'), claim('not p or q'), claim('p or not q'), claim('not p or not q'))
        self.assertIn('INCONSISTENT_SET_IN_MODEL', kinds(r))
        self.assertNotIn('CONTRADICTION_IN_MODEL', kinds(r))

    def test_variable_limit(self):
        r = run(claim(' and '.join('v'+str(i) for i in range(11))))
        self.assertEqual(r['coverage'], 'PARTIAL')

    def test_pair_limit(self):
        r = run(*[claim('p') for _ in range(46)])
        self.assertEqual(r['pairs_checked'], 1000)
        self.assertEqual(r['pairs_omitted'], 35)
        self.assertEqual(r['coverage'], 'PARTIAL')

    def test_invalid_global_input(self):
        for data in [{}, {'claims': []}, {'claims': [None]}, {'claims': [claim('p')]*101}]:
            with self.assertRaises(ValueError): module.audit(data)

    def test_bounded_formula(self):
        a = claim('p'); a['expression'] = 'not '*130 + 'p'
        self.assertEqual(run(a)['coverage'], 'PARTIAL')

    def test_input_unchanged(self):
        a = claim('p'); before = copy.deepcopy(a)
        run(a)
        self.assertEqual(a, before)

    def test_truth_tables_against_independent_boolean_functions(self):
        examples = [('p and q', lambda p,q:p and q), ('not (p or q)', lambda p,q:not p and not q), ('p or not q', lambda p,q:p or not q)]
        for expression, oracle in examples:
            table = run(claim(expression))['truth_tables'][0]
            for row in table['rows']:
                self.assertEqual(row['values']['C001'], oracle(**row['assignment']))

    def test_cli_and_source_integrity(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'input.json'; p.write_text(json.dumps({'claims':[claim('p'),claim('not p')]}))
            before = p.read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('CONTRADICTION_IN_MODEL', kinds(json.loads(result.stdout)))
            self.assertEqual(before,p.read_bytes())
            p.write_text('{')
            result = subprocess.run([sys.executable,str(SCRIPT),str(p)],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)
            self.assertEqual(json.loads(result.stdout)['coverage'],'NONE')


if __name__ == '__main__': unittest.main()
