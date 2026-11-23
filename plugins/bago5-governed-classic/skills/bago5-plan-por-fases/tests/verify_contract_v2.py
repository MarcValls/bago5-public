#!/usr/bin/env python3
"""Validador referencial conservador sobre candidatos v2 (no ejecuta ni escribe Site)."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import unittest

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / 'traceability-v2.schema.json').read_text(encoding='utf-8'))


def literal(text: str, source_ref='source:v1') -> dict:
    b = text.encode('utf-8')
    return {'text': text, 'source_ref': source_ref, 'utf8_length': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def validate(bundle: dict) -> list[str]:
    errors: list[str] = []
    if Draft202012Validator is not None:
        errors += [e.message for e in Draft202012Validator(SCHEMA).iter_errors(bundle)]
        if errors:
            return errors
    else:
        raise RuntimeError('Instala jsonschema para ejecutar la validación de esquema')

    ids = set()
    indexes = {name: {} for name in ['plans', 'phases', 'tasks', 'test_cases', 'executions', 'evidences', 'verifications', 'acceptances', 'events']}
    def register(typ, key, obj):
        value = obj[key]
        if value in ids:
            errors.append(f'ID duplicado: {value}')
        ids.add(value)
        indexes[typ][value] = obj

    gid = bundle['goal']['goal_id']
    ids.add(gid)
    for plan in bundle['plans']:
        register('plans', 'plan_id', plan)
        if plan['goal_id'] != gid:
            errors.append(f'Plan huérfano: {plan["plan_id"]}')
        for phase in plan['phases']:
            register('phases', 'phase_id', phase)
            if phase['plan_id'] != plan['plan_id']:
                errors.append(f'Fase huérfana: {phase["phase_id"]}')
            for task in phase['tasks']:
                register('tasks', 'task_id', task)
                if task['phase_id'] != phase['phase_id']:
                    errors.append(f'Trabajo huérfano: {task["task_id"]}')
    for typ,key in [('test_cases','test_id'),('executions','run_id'),('evidences','evidence_id'),('verifications','verification_id'),('acceptances','acceptance_id'),('events','event_id')]:
        for obj in bundle[typ]:
            register(typ,key,obj)

    for event in indexes['events'].values():
        if event['object_ref'] not in ids:
            errors.append(f"Evento con objeto ausente: {event['event_id']}")

    for v in [bundle['goal']] + bundle['plans'] + list(indexes['phases'].values()):
        l = v['literal']
        b = l['text'].encode('utf-8')
        if len(b) != l['utf8_length'] or hashlib.sha256(b).hexdigest() != l['sha256']:
            errors.append('Literal alterado o hash/longitud incorrectos')

    for plan in bundle['plans']:
        phases = plan['phases']
        ranks = [p['phase_order'] for p in phases]
        if len(set(ranks)) != len(ranks):
            errors.append('Orden de fases repetido')
        by_rank = {p['phase_id']: p['phase_order'] for p in phases}
        for phase in phases:
            for dep in phase['depends_on_phases']:
                if dep not in by_rank or by_rank[dep] >= phase['phase_order']:
                    errors.append(f'Dependencia de fase inválida: {phase["phase_id"]}->{dep}')
            taskids = {t['task_id'] for t in phase['tasks']}
            taskdeps = {t['task_id']: t['depends_on_tasks'] for t in phase['tasks']}
            def visit(t, stack):
                if t in stack:
                    errors.append(f'Ciclo de trabajos: {t}')
                    return
                for d in taskdeps.get(t, []):
                    if d not in taskids:
                        errors.append(f'Dependencia a otro ámbito o inexistente: {t}->{d}')
                    else:
                        visit(d, stack | {t})
            for t in taskids: visit(t, set())

    tests = indexes['test_cases']
    runs = indexes['executions']
    evidence = indexes['evidences']
    verifications = indexes['verifications']
    for t in tests.values():
        if t['task_id'] not in indexes['tasks']:
            errors.append(f'Caso sin trabajo: {t["test_id"]}')
    for run in runs.values():
        if run['test_id'] not in tests:
            errors.append(f'Ejecución sin caso: {run["run_id"]}')
        if any(i not in evidence for i in run['evidence_ids']):
            errors.append(f'Ejecución con evidencia ausente: {run["run_id"]}')
        if run['result'] == 'PASS' and not run['evidence_ids']:
            errors.append(f'Ejecución PASS sin recibo: {run["run_id"]}')
    for v in verifications.values():
        run = runs.get(v['run_id'])
        if run is None:
            errors.append(f'Verificación sin ejecución: {v["verification_id"]}')
        if any(i not in evidence for i in v['evidence_ids']):
            errors.append(f'Verificación con evidencia ausente: {v["verification_id"]}')
        if v['result'] == 'PASS' and (run is None or run['result'] != 'PASS' or not v['evidence_ids']):
            errors.append(f'Verificación PASS sin ejecución/evidencia PASS: {v["verification_id"]}')
        if v['independent'] and run and v['verifier_ref'] == run['actor_ref']:
            errors.append(f'Independencia falsa: {v["verification_id"]}')
    for acc in indexes['acceptances'].values():
        if acc['gate_ref'] not in indexes['phases'] and acc['gate_ref'] != gid:
            errors.append(f'Gate inexistente: {acc["acceptance_id"]}')
        refvals=[verifications.get(v) for v in acc['verification_ids']]
        if any(x is None for x in refvals):
            errors.append(f'Verificador inexistente: {acc["acceptance_id"]}')
        if acc['status'] == 'GO':
            gate_tasks = {
                task['task_id'] for task in indexes['tasks'].values()
                if task['mandatory'] and (acc['gate_ref'] == gid or task['phase_id'] == acc['gate_ref'])
            }
            covered_tasks = {test['task_id'] for test in tests.values() if test['mandatory']}
            if not gate_tasks.issubset(covered_tasks):
                errors.append(f"GO con trabajo obligatorio sin caso: {acc['acceptance_id']}")
            if acc['open_critical_issues'] > 0 or not refvals or any(v is None or v['result'] != 'PASS' for v in refvals):
                errors.append(f'GO sin verificaciones completas: {acc["acceptance_id"]}')
            mandatory_tests={t['test_id'] for t in tests.values() if t['mandatory'] and t['task_id'] in indexes['tasks'] and (acc['gate_ref']==gid or indexes['tasks'][t['task_id']]['phase_id']==acc['gate_ref'])}
            valid_tests={runs[v['run_id']]['test_id'] for v in refvals if v and v['result']=='PASS' and v['run_id'] in runs and runs[v['run_id']]['candidate']==acc['candidate']}
            if not mandatory_tests or not mandatory_tests.issubset(valid_tests):
                errors.append(f'GO con casos obligatorios sin PASS: {acc["acceptance_id"]}')
    return errors


def sample() -> dict:
    return {
      'schema_version':'2.0.0', 'memory_id':'memory:test', 'owner_id':'owner:test', 'project_id':'project:test',
      'goal': {'goal_id':'goal:1','version':1,'literal':literal('Resultado exacto'),'status':'in_progress'},
      'plans':[{'plan_id':'plan:1','goal_id':'goal:1','version':1,'literal':literal('Plan íntegro'), 'status':'draft',
      'phases':[{'phase_id':'phase:1','plan_id':'plan:1','version':1,'phase_order':1,'status':'draft',
      'literal':literal('Fase exacta'), 'depends_on_phases':[], 'tasks':[{'task_id':'task:1','phase_id':'phase:1','title':'Probar lectura','status':'completed','acceptance_criteria':['Lectura literal'],'depends_on_tasks':[], 'mandatory':True}]}]}],
      'test_cases':[{'test_id':'test:1','task_id':'task:1','version':1,'mandatory':True,'polarity':'negative','expected':'Rechazo correcto'}],
      'executions':[{'run_id':'run:1','test_id':'test:1','candidate':'commit:abc','client':'chatgpt','actor_ref':'actor:worker','result':'PASS','evidence_ids':['ev:1']}],
      'evidences':[{'evidence_id':'ev:1','source_ref':'recibo:1','sha256':'a'*64,'utf8_length':1,'captured_at':'2026-11-14T20:00:00Z'}],
      'verifications':[{'verification_id':'ver:1','run_id':'run:1','verifier_ref':'actor:verifier','result':'PASS','evidence_ids':['ev:1'],'independent':True}],
      'acceptances':[{'acceptance_id':'acc:1','gate_ref':'phase:1','candidate':'commit:abc','actor_ref':'actor:owner','status':'GO','verification_ids':['ver:1'],'open_critical_issues':0}],
      'events':[{'event_id':'evt:1','actor_ref':'actor:owner','timestamp':'2026-11-14T20:00:00Z','object_ref':'goal:1','action':'created','source_ref':'source:1'}]
    }

class ContractV2Tests(unittest.TestCase):
    def test_event_object_must_exist(self):
        bundle = sample()
        bundle['events'][0]['object_ref'] = 'goal:missing'
        self.assertTrue(validate(bundle))

    def test_go_requires_a_case_for_each_mandatory_task(self):
        bundle = sample()
        tasks = bundle['plans'][0]['phases'][0]['tasks']
        tasks.append(dict(tasks[0], task_id='task:uncovered'))
        self.assertTrue(validate(bundle))

    def test_go_requires_matching_candidate(self):
        bundle = sample()
        bundle['acceptances'][0]['candidate'] = 'commit:other'
        self.assertTrue(validate(bundle))

    def test_positive(self): self.assertEqual(validate(sample()), [])
    def test_negative_orphan_plan(self):
        x=sample();x['plans'][0]['goal_id']='goal:other';self.assertTrue(validate(x))
    def test_negative_orphan_phase(self):
        x=sample();x['plans'][0]['phases'][0]['plan_id']='plan:other';self.assertTrue(validate(x))
    def test_negative_orphan_test(self):
        x=sample();x['test_cases'][0]['task_id']='task:absent';self.assertTrue(validate(x))
    def test_negative_missing_evidence(self):
        x=sample();x['executions'][0]['evidence_ids']=['ev:absent'];self.assertTrue(validate(x))
    def test_negative_fake_independent_verifier(self):
        x=sample();x['verifications'][0]['verifier_ref']='actor:worker';self.assertTrue(validate(x))
    def test_negative_go_with_not_run(self):
        x=sample();x['executions'][0]['result']='NOT_RUN';self.assertTrue(validate(x))
    def test_negative_go_with_fail(self):
        x=sample();x['verifications'][0]['result']='FAIL';self.assertTrue(validate(x))
    def test_negative_go_with_p1(self):
        x=sample();x['acceptances'][0]['open_critical_issues']=1;self.assertTrue(validate(x))
    def test_negative_literal_modified(self):
        x=sample();x['plans'][0]['literal']['text']+=' alterado';self.assertTrue(validate(x))
    def test_negative_cross_phase_dependency(self):
        x=sample();x['plans'][0]['phases'][0]['tasks'][0]['depends_on_tasks']=['task:other'];self.assertTrue(validate(x))
    def test_negative_duplicate_id(self):
        x=sample();x['plans'][0]['plan_id']='goal:1';x['plans'][0]['phases'][0]['plan_id']='goal:1';self.assertTrue(validate(x))

if __name__ == '__main__':
    unittest.main(verbosity=2)
