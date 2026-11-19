#!/usr/bin/env python3
"""Validate a local plan and its references without writing to a service."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import argparse
import sys
from graphlib import CycleError, TopologicalSorter

try:
    from jsonschema import Draft202012Validator
except ImportError:
    Draft202012Validator = None

SCHEMA = json.loads((Path(__file__).resolve().parents[1] / 'schemas' / 'traceability-v2.schema.json').read_text(encoding='utf-8'))


def validate(bundle: dict) -> list[str]:
    errors: list[str] = []
    if Draft202012Validator is not None:
        checker = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
        errors += [f"{e.json_path}: {e.validator}" for e in checker.iter_errors(bundle)]
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
            for task, deps in taskdeps.items():
                if any(dep not in taskids for dep in deps):
                    errors.append(f"Dependencia de trabajo fuera de la fase: {task}")
            try:
                tuple(TopologicalSorter(taskdeps).static_order())
            except CycleError:
                errors.append(f"Ciclo de trabajos en fase: {phase['phase_id']}")


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



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="Local JSON bundle to check")
    args = parser.parse_args()
    try:
        bundle = json.loads(args.plan.read_text(encoding="utf-8"))
        errors = validate(bundle)
    except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
