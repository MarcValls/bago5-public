#!/usr/bin/env python3
"""Bounded truth tables for explicit models. Never executes audited source."""
import ast
import hashlib
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

MAX_INPUT = 1024 * 1024
MAX_CLAIMS = 100
MAX_PAIRS = 1000
CONTEXT_KEYS = {'project', 'referent', 'time', 'condition', 'modality', 'scope'}


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def parse(expression):
    if not isinstance(expression, str) or not 0 < len(expression) <= 512:
        raise ValueError('EXPRESSION_SIZE_OR_TYPE')
    tree = ast.parse(expression, mode='eval')
    nodes = list(ast.walk(tree))
    if len(nodes) > 128:
        raise ValueError('AST_LIMIT')
    allowed = (ast.Expression, ast.Name, ast.Load, ast.Constant, ast.UnaryOp,
               ast.Not, ast.BoolOp, ast.And, ast.Or)
    if any(not isinstance(n, allowed) for n in nodes):
        raise ValueError('UNSUPPORTED_SYNTAX')
    if any(isinstance(n, ast.Constant) and type(n.value) is not bool for n in nodes):
        raise ValueError('NON_BOOLEAN_CONSTANT')
    names = sorted({n.id for n in nodes if isinstance(n, ast.Name)})
    if len(names) > 10:
        raise ValueError('VARIABLE_LIMIT')
    return tree.body, names


def value(node, env):
    if isinstance(node, ast.Name):
        return env[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return not value(node.operand, env)
    values = [value(n, env) for n in node.values]
    return all(values) if isinstance(node.op, ast.And) else any(values)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


def audit(data):
    if not isinstance(data, dict) or not isinstance(data.get('claims'), list):
        raise ValueError('CLAIMS_REQUIRED')
    claims = data['claims']
    if not 0 < len(claims) <= MAX_CLAIMS:
        raise ValueError('CLAIM_COUNT')
    inventory, skipped, findings, tables, relations = [], [], [], [], []
    groups = defaultdict(list)
    exact, normalized = defaultdict(list), defaultdict(list)
    for index, claim in enumerate(claims):
        cid = f'C{index + 1:03d}'
        if not isinstance(claim, dict) or not all(isinstance(claim.get(k), str) and claim[k].strip() for k in ('source', 'quote')):
            raise ValueError('SOURCE_AND_QUOTE_REQUIRED:' + cid)
        quote = claim['quote']
        norm = quote.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
        item = dict(claim, id=cid, quote_sha256=digest(quote), normalized_quote_sha256=digest(norm))
        inventory.append(item)
        exact[digest(quote)].append(cid)
        normalized[digest(norm)].append(cid)
        try:
            if claim.get('mapping') != 'reviewed':
                raise ValueError('MAPPING_NOT_REVIEWED')
            context = claim.get('context')
            if not isinstance(context, dict) or not CONTEXT_KEYS <= context.keys() or not all(isinstance(v, str) and v.strip() for v in context.values()):
                raise ValueError('INCOMPLETE_CONTEXT')
            assumptions = claim.get('assumptions')
            if not isinstance(assumptions, list) or not assumptions or not all(isinstance(v, str) and v.strip() for v in assumptions):
                raise ValueError('ASSUMPTIONS_REQUIRED')
            tree, names = parse(claim.get('expression'))
            atoms = claim.get('atoms')
            if not isinstance(atoms, dict) or set(atoms) != set(names) or not all(isinstance(v, str) and v.strip() for v in atoms.values()):
                raise ValueError('ATOM_DEFINITIONS_REQUIRED')
            # Different assumptions cannot silently be merged into one model.
            key = canonical([context, atoms, sorted(set(assumptions))])
            groups[key].append((cid, tree, names))
        except (ValueError, SyntaxError, RecursionError) as exc:
            skipped.append({'id': cid, 'reason': str(exc)})
    pair_count = 0
    pairs_omitted = 0
    for key, members in groups.items():
        names = members[0][2]
        envs = [dict(zip(names, bits)) for bits in itertools.product((False, True), repeat=len(names))]
        columns = {cid: [value(tree, env) for env in envs] for cid, tree, _ in members}
        ids = list(columns)
        rows = [{'assignment': env, 'values': {cid: columns[cid][i] for cid in ids}} for i, env in enumerate(envs)]
        tables.append({'context_atoms_assumptions': json.loads(key), 'claim_ids': ids, 'rows': rows})
        for cid in ids:
            col = columns[cid]
            if not any(col):
                findings.append({'kind': 'SELF_CONTRADICTION_IN_MODEL', 'claim_ids': [cid]})
            elif all(col):
                findings.append({'kind': 'TAUTOLOGY_IN_MODEL', 'claim_ids': [cid], 'is_defect': 'NOT_ESTABLISHED'})
        joint = next((i for i in range(len(envs)) if all(columns[cid][i] for cid in ids)), None)
        if len(ids) > 1 and joint is None:
            findings.append({'kind': 'INCONSISTENT_SET_IN_MODEL', 'claim_ids': ids, 'minimal': False})
        for a, b in itertools.combinations(ids, 2):
            if pair_count >= MAX_PAIRS:
                pairs_omitted += 1
                continue
            pair_count += 1
            left, right = columns[a], columns[b]
            both = next((i for i in range(len(envs)) if left[i] and right[i]), None)
            diff = next((i for i in range(len(envs)) if left[i] != right[i]), None)
            incompatible = both is None
            relations.append({'claim_ids': [a, b], 'equivalent_in_model': diff is None,
                              'incompatible_in_model': incompatible,
                              'joint_witness': None if both is None else envs[both],
                              'equivalence_counterexample': None if diff is None else envs[diff]})
            if incompatible and any(left) and any(right):
                findings.append({'kind': 'CONTRADICTION_IN_MODEL', 'claim_ids': [a, b]})
            if diff is None:
                findings.append({'kind': 'EQUIVALENT_IN_MODEL', 'claim_ids': [a, b], 'is_defect': 'NOT_ESTABLISHED'})
    return {'schema_version': '0.1', 'coverage': 'PARTIAL' if skipped or pairs_omitted else 'COMPLETE_FOR_ACCEPTED_BOOLEAN_MODELS',
            'source_semantics': 'NOT_VERIFIED_BY_SCRIPT', 'runtime_verification': 'NOT_RUN',
            'automatic_actions': [], 'inventory': inventory,
            'literal_groups': [v for v in exact.values() if len(v) > 1],
            'normalized_groups': [v for v in normalized.values() if len(v) > 1],
            'skipped': skipped, 'pairs_checked': pair_count, 'pairs_omitted': pairs_omitted,
            'model_groups': len(groups), 'cross_group_comparisons': 'NOT_PERFORMED',
            'findings': findings, 'relations': relations, 'truth_tables': tables,
            'limitations': ['Only supplied formalizations; no natural-language or code translation.',
                            'Hashes bind supplied snippets, not full source files.',
                            'Context, atom definitions and assumptions must match exactly.',
                            'A model result does not establish source semantics or functional correctness.']}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if len(argv) != 1:
            raise ValueError('USAGE: boolean_audit.py input.json')
        with Path(argv[0]).open('rb') as stream:
            raw = stream.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError('INPUT_LIMIT')
        result = audit(json.loads(raw.decode('utf-8-sig')))
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        print(json.dumps({'status': 'ERROR', 'coverage': 'NONE', 'error': str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
