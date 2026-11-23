#!/usr/bin/env python3
"""Verificador del contrato de resultados; independiente de los módulos productores."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def _sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify(report_path, sources=None):
    errors, source_checks = [], []
    report_path = Path(report_path)
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes.decode('utf-8'))
    if report.get('schema_version') != '0.2':
        errors.append('SCHEMA_VERSION')
    for key in ('archives', 'duplicate_groups', 'same_path_different_content', 'consolidation_proposals', 'duplicate_classification', 'dependency_analysis'):
        if key not in report:
            errors.append('MISSING_KEY:' + key)
    if errors:
        return {'status': 'FAIL', 'errors': errors}
    entries, archive_by_node = {}, {}
    if report.get('archive_count') != len(report['archives']):
        errors.append('ARCHIVE_COUNT_MISMATCH')
    for archive in report['archives']:
        for entry in archive['entries']:
            node_id = entry['id']
            if node_id in entries:
                errors.append('DUPLICATE_NODE_ID:' + node_id)
            entries[node_id] = entry
            archive_by_node[node_id] = archive
        if sources is not None:
            raw = archive['zip'].replace('\\', '/')
            path = PurePosixPath(raw)
            if path.is_absolute() or '..' in path.parts or (len(raw) > 1 and raw[1] == ':'):
                errors.append('UNSAFE_ARCHIVE_REFERENCE')
                continue
            target = Path(sources)/Path(*path.parts)
            if not target.is_file():
                errors.append('NO_RECUPERADO:' + raw)
                continue
            digest = _sha(target)
            match = digest == archive['zip_sha256']
            source_checks.append({'zip': raw, 'sha256': digest, 'matches_report': match})
            if not match:
                errors.append('SOURCE_SHA_MISMATCH:' + raw)
    dependency = report['dependency_analysis']
    graph_ids = {n['id'] for n in dependency['nodes']}
    if graph_ids != set(entries) or len(dependency['nodes']) != len(entries):
        errors.append('GRAPH_ENTRY_SET_MISMATCH')
    if dependency.get('consolidation_authorized') is not False:
        errors.append('CONSOLIDATION_AUTHORITY_VIOLATION')
    if dependency.get('runtime_verification') != 'NOT_RUN':
        errors.append('UNSUPPORTED_RUNTIME_VERIFICATION_CLAIM')
    for edge in dependency['edges']:
        source, target = edge['source'], edge.get('target')
        if source not in entries:
            errors.append('MISSING_EDGE_SOURCE')
            continue
        if target is not None and target not in entries:
            errors.append('MISSING_EDGE_TARGET')
        if edge['status'] == 'RESOLVED_INTERNAL':
            if target not in entries or archive_by_node[source]['zip'] != archive_by_node.get(target, {}).get('zip'):
                errors.append('CROSS_ARCHIVE_OR_MISSING_INTERNAL_TARGET')
        if edge['status'] != 'RESOLVED_INTERNAL' and target is not None:
            errors.append('NONRESOLVED_EDGE_HAS_TARGET')
        if edge['evidence']['entry_sha256'] != entries[source]['sha256'] or edge['evidence']['zip_sha256'] != archive_by_node[source]['zip_sha256'] or edge['evidence']['entry_index'] != entries[source]['entry_index']:
            errors.append('EDGE_EVIDENCE_MISMATCH')
    for group in report['duplicate_groups']:
        if len(group['instances']) < 2:
            errors.append('DUPLICATE_GROUP_TOO_SMALL')
        for instance in group['instances']:
            entry = entries.get(instance['id'], {})
            if entry.get('sha256') != group['sha256'] or instance['sha256'] != group['sha256']:
                errors.append('DUPLICATE_GROUP_SHA_MISMATCH')
    if report['duplicate_classification'].get('automatic_actions'):
        errors.append('AUTOMATIC_ACTIONS_PRESENT')
    for proposal in report['consolidation_proposals']:
        if proposal.get('status') != 'PROPOSED' or proposal.get('automatic_action') is not None:
            errors.append('PROPOSAL_AUTHORITY_VIOLATION')
    manifest = json.loads((report_path.parent/'SHA256SUMS.json').read_text(encoding='utf-8'))
    # Bind the bytes actually parsed above to the manifest. Checking a sibling
    # report.json alone must not validate an unrelated report argument.
    if manifest.get(report_path.name) != hashlib.sha256(report_bytes).hexdigest():
        errors.append('REPORT_ARGUMENT_NOT_COVERED')
    if set(manifest) != {'report.json', 'inventory.csv', 'report.html', 'duplicates.csv', 'dependencies.csv', 'dependency_nodes.csv'}:
        errors.append('REPORT_MANIFEST_COVERAGE_MISMATCH')
    for name, expected in manifest.items():
        if name != Path(name).name or not (report_path.parent/name).is_file():
            errors.append('INVALID_REPORT_MANIFEST_PATH')
        elif _sha(report_path.parent/name) != expected:
            errors.append('REPORT_SHA_MISMATCH:' + name)
    return {'status': 'FAIL' if errors else 'PASS', 'errors': sorted(set(errors)),
            'archives': len(report['archives']), 'nodes': len(entries), 'edges': len(dependency['edges']),
            'source_identity_checks': source_checks,
            'scope': 'Estructura, referencias, autoridad de propuestas e identidad de informes/fuentes; no equivalencia funcional ni ejecución de las fuentes.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--sources', type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify(args.report.resolve(), args.sources.resolve() if args.sources else None)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        result = {'status': 'FAIL', 'errors': [type(exc).__name__ + ': ' + str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
