#!/usr/bin/env python3
"""Read-only ZIP distribution inventory and exact-content comparison."""
import argparse
import csv
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import sys
# Direct CLI use must leave the distributed source tree unchanged. This also
# covers users invoking this script without Python's -B option.
sys.dont_write_bytecode = True
import zipfile
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from zip_analysis import content_text, identify, classify, analyze_dependencies, reference, TEXT_EXTENSIONS
from zip_reporting import emit_analysis, safe_csv_cell

CHUNK = 1024 * 1024

def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(CHUNK), b''):
            h.update(block)
    return h.hexdigest()

def is_unsafe(name):
    n = name.replace('\\', '/')
    p = PurePosixPath(n)
    return n.startswith('/') or n.startswith('//') or any(x == '..' for x in p.parts) or (len(n) >= 2 and n[1] == ':' and n[0].isalpha())

def examine(path, root, limits, capture=None):
    rel = path.relative_to(root).as_posix()
    result = {'zip': rel, 'zip_sha256': None, 'status': 'ANALYZED', 'entries': [], 'warnings': []}
    try:
        result['zip_sha256'] = sha_file(path)
        with zipfile.ZipFile(path) as z:
            seen = set()
            infos = z.infolist()
            if len(infos) > limits.max_entries:
                result['status'] = 'PARTIAL'
                result['warnings'].append('Entry limit exceeded; archive not scanned')
                return result
            total = sum(i.file_size for i in infos if not i.is_dir())
            if total > limits.max_total_uncompressed:
                result['status'] = 'PARTIAL'
                result['warnings'].append('Uncompressed size limit exceeded; archive not scanned')
                return result
            for entry_index, info in enumerate(infos):
                if info.is_dir():
                    continue
                entry = {'path': info.filename, 'entry_index': entry_index, 'size': info.file_size, 'compressed_size': info.compress_size, 'sha256': None, 'status': 'ANALYZED', 'issues': [], 'text_status': 'NOT_SUPPORTED'}
                if info.filename in seen:
                    entry['issues'].append('DUPLICATE_ENTRY_NAME')
                seen.add(info.filename)
                if is_unsafe(info.filename):
                    entry['issues'].append('UNSAFE_PATH')
                if (info.flag_bits & 1):
                    entry['issues'].append('ENCRYPTED')
                if info.file_size > limits.max_entry_uncompressed:
                    entry['issues'].append('ENTRY_SIZE_LIMIT')
                if info.file_size > limits.max_ratio * max(info.compress_size, 1) and info.file_size > 1024 * 1024:
                    entry['issues'].append('COMPRESSION_RATIO_LIMIT')
                if any(i in entry['issues'] for i in ('ENCRYPTED', 'ENTRY_SIZE_LIMIT', 'COMPRESSION_RATIO_LIMIT')):
                    entry['status'] = 'NOT_ANALYZED'
                else:
                    try:
                        digest = hashlib.sha256()
                        amount = 0
                        is_text = PurePosixPath(info.filename).suffix.lower() in TEXT_EXTENSIONS
                        text_limit = getattr(limits, 'max_text_bytes', 1_000_000)
                        total_text_limit = getattr(limits, 'max_total_text_bytes', 50_000_000)
                        collect = capture is not None and is_text and not is_unsafe(info.filename) and info.file_size <= text_limit and capture['bytes'] + info.file_size <= total_text_limit
                        entry['text_status'] = 'CAPTURE_LIMIT' if is_text and not collect else 'NOT_SUPPORTED'
                        data = bytearray() if collect else None
                        with z.open(info) as stream:
                            while True:
                                block = stream.read(CHUNK)
                                if not block:
                                    break
                                amount += len(block)
                                if amount > limits.max_entry_uncompressed:
                                    raise ValueError('Entry size exceeded')
                                digest.update(block)
                                if data is not None:
                                    if amount <= text_limit and capture['bytes'] + amount <= total_text_limit:
                                        data.extend(block)
                                    else:
                                        data = None
                                        entry['text_status'] = 'CAPTURE_LIMIT'
                        entry['sha256'] = digest.hexdigest()
                        if data is not None:
                            text = content_text(info.filename, bytes(data))
                            if text is not None:
                                capture['values'][(rel, entry_index)] = text
                                capture['bytes'] += amount
                                entry['text_status'] = 'CAPTURED_UTF8'
                            else:
                                entry['text_status'] = 'NOT_UTF8_TEXT'
                    except Exception as exc:
                        entry['status'] = 'ERROR'
                        entry['issues'].append(f'READ_ERROR:{type(exc).__name__}')
                result['entries'].append(entry)
            if any(e['status'] != 'ANALYZED' for e in result['entries']):
                result['status'] = 'PARTIAL'
        if sha_file(path) != result['zip_sha256']:
            result['status'] = 'ERROR'
            result['warnings'].append('ARCHIVE_CHANGED_DURING_ANALYSIS')
            for entry in result['entries']:
                entry['status'] = 'ERROR'
                entry['sha256'] = None
                if capture is not None:
                    capture['values'].pop((rel, entry['entry_index']), None)
    except (zipfile.BadZipFile, OSError, ValueError) as exc:
        result['status'] = 'ERROR'
        result['warnings'].append(f'{type(exc).__name__}: {exc}')
    return result

def build(root, recursive, limits):
    root = Path(root).resolve()
    files = sorted((p for p in (root.rglob('*') if recursive else root.iterdir()) if p.suffix.lower() == '.zip'), key=lambda p: p.as_posix().lower())
    capture = {'values': {}, 'bytes': 0}
    archives = [examine(p, root, limits, capture) for p in files if p.is_file()]
    nodes = identify(archives)
    texts = {n['id']: capture['values'][(n['zip'], n['entry_index'])] for n in nodes.values() if (n['zip'], n['entry_index']) in capture['values'] and n['sha256']}
    classification = classify(archives, nodes, texts, limits)
    dependencies = analyze_dependencies(archives, nodes, texts, limits)
    by_hash = defaultdict(list)
    by_path = defaultdict(list)
    for arc in archives:
        for e in arc['entries']:
            if e['sha256']:
                ref = reference(nodes[e['id']])
                by_hash[e['sha256']].append(ref)
                by_path[e['path']].append(ref)
    duplicates = classification['exact_content_groups']
    differences = [{'path': name, 'variants': sorted(set(e['sha256'] for e in entries)), 'instances': entries} for name, entries in sorted(by_path.items()) if len(set(e['sha256'] for e in entries)) > 1]
    proposals = []
    dependency_nodes = {n['id']: n for n in dependencies['nodes']}
    for group in duplicates:
        zips = sorted(set(x['zip'] for x in group['instances']))
        context = [{'node_id': n['id'], 'runtime_dependents': dependency_nodes[n['id']]['runtime_dependents'], 'other_dependents': dependency_nodes[n['id']]['other_dependents'], 'analysis_status': dependency_nodes[n['id']]['analysis_status']} for n in group['instances']]
        proposals.append({'type': 'REVIEW_CONSOLIDATION', 'sha256': group['sha256'], 'instances': group['instances'], 'recommendation': 'Revisar roles, referencias y autonomía de cada distribución; conservar originales.', 'risk': 'Static references available; runtime and distribution independence NOT_VERIFIED', 'status': 'PROPOSED', 'archive_count': len(zips), 'review_tags': group['review_tags'], 'dependency_context': context, 'automatic_action': None})
    return {'schema_version': '0.2', 'tool_version': '0.2.2', 'generated_utc': datetime.now(timezone.utc).isoformat(), 'root': str(root), 'archive_count': len(archives), 'archives': archives, 'duplicate_groups': duplicates, 'same_path_different_content': differences, 'consolidation_proposals': proposals, 'duplicate_classification': classification, 'dependency_analysis': dependencies, 'analysis_limits': {k: v for k, v in vars(limits).items() if isinstance(v, (int, float, bool, str))}, 'text_capture_bytes': capture['bytes'], 'limitations': ['Exact bytes, normalized text and heuristic similarity are different claims; no functional equivalence', 'Static dependency analysis only; no import, installation, script execution or runtime verification', 'No deletion, consolidation or mutation of source archives; all proposals are PROPOSED', 'Each archive is independent; nested ZIP contents are not recursively parsed', 'Orphan candidates mean no observed static runtime inbound references, not unused or removable files', 'Python resolution approximates parent/src layouts; sys.path, optional imports, package exports and dynamic loading may change actual dependencies', 'JS/TS, shell and Markdown use bounded heuristics; JSON references may lack a line number; unsupported formats are listed in coverage', 'Text capture and similarity/edge budgets limit coverage; corrupt/encrypted/limited entries remain explicit']}

def _emit_legacy(result, output):
    output.mkdir(parents=True, exist_ok=True)
    (output/'report.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    with (output/'inventory.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['zip', 'zip_sha256', 'archive_status', 'path', 'size', 'compressed_size', 'sha256', 'status', 'issues'])
        for a in result['archives']:
            if not a['entries']:
                writer.writerow([safe_csv_cell(v) for v in [a['zip'], a['zip_sha256'], a['status'], '', '', '', '', '', ';'.join(a['warnings'])]])
            for e in a['entries']:
                writer.writerow([safe_csv_cell(v) for v in [a['zip'], a['zip_sha256'], a['status'], e['path'], e['size'], e['compressed_size'], e['sha256'], e['status'], ';'.join(e['issues'])]])
    rows = []
    for a in result['archives']:
        for e in a['entries']:
            rows.append('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in (a['zip'], e['path'], e['size'], e['sha256'] or '—', e['status'], ', '.join(e['issues']))) + '</tr>')
    escaped = lambda v: html.escape(str(v))
    document = f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>Auditoría ZIP</title><style>body{{font:15px system-ui;margin:3rem;max-width:1200px;color:#1b2630}}table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:left;overflow-wrap:anywhere}}th{{background:#f4f6f9}}code{{overflow-wrap:anywhere}}.muted{{color:#586675}}</style><h1>Auditoría de distribuciones ZIP</h1><p class="muted">Generado: {escaped(result['generated_utc'])}</p><p>ZIP: <b>{result['archive_count']}</b> · Grupos de duplicados: <b>{len(result['duplicate_groups'])}</b> · Mismas rutas con diferente contenido: <b>{len(result['same_path_different_content'])}</b></p><h2>Inventario</h2><table><thead><tr><th>ZIP</th><th>Ruta</th><th>Bytes</th><th>SHA-256</th><th>Estado</th><th>Incidencias</th></tr></thead><tbody>{''.join(rows)}</tbody></table><h2>Propuestas de consolidación</h2><p>No se ha modificado ni eliminado ningún archivo. Todas las propuestas requieren revisión humana.</p><ol>{''.join('<li><code>' + escaped(p['sha256']) + '</code> — ' + escaped(len(p['instances'])) + ' apariciones. Dependencias NO VERIFICADAS.</li>' for p in result['consolidation_proposals'])}</ol><h2>Limitaciones</h2><ul>{''.join('<li>'+escaped(l)+'</li>' for l in result['limitations'])}</ul></html>'''
    (output/'report.html').write_text(document, encoding='utf-8')
    manifest = {p.name: sha_file(p) for p in [output/'report.json', output/'inventory.csv', output/'report.html']}
    (output/'SHA256SUMS.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

def emit(result, output):
    """Publicación de informes sin seguir enlaces simbólicos de archivos destino."""
    output = Path(output)
    if output.is_symlink():
        raise ValueError('Output directory must not be a symbolic link')
    output = output.resolve()  # Canonical path before staging/atomic replacement on Windows.
    output.mkdir(parents=True, exist_ok=True)
    names = ['report.json', 'inventory.csv', 'report.html', 'duplicates.csv', 'dependencies.csv', 'dependency_nodes.csv', 'SHA256SUMS.json']
    for name in names:
        dest = output/name
        if dest.is_symlink() or (dest.exists() and not dest.is_file()):
            raise ValueError('Unsafe report destination: ' + name)
    with tempfile.TemporaryDirectory(prefix='.zip_auditor_', dir=output.parent) as temp:
        staging = Path(temp)
        _emit_legacy(result, staging)
        emit_analysis(result, staging)
        manifest = {name: sha_file(staging/name) for name in names if name != 'SHA256SUMS.json'}
        (staging/'SHA256SUMS.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        for name in names:
            os.replace(staging/name, output/name)

def main(argv=None):
    p = argparse.ArgumentParser(description='Read-only ZIP auditor; never extracts or alters original archives')
    p.add_argument('--folder', type=Path, default=Path.cwd())
    p.add_argument('--output', type=Path, default=None)
    p.add_argument('--recursive', action='store_true')
    p.add_argument('--max-entries', type=int, default=100000)
    p.add_argument('--max-total-uncompressed', type=int, default=5_000_000_000)
    p.add_argument('--max-entry-uncompressed', type=int, default=1_000_000_000)
    p.add_argument('--max-ratio', type=int, default=1000)
    p.add_argument('--max-text-bytes', type=int, default=1_000_000)
    p.add_argument('--max-total-text-bytes', type=int, default=50_000_000)
    p.add_argument('--max-similarity-pairs', type=int, default=10000)
    p.add_argument('--max-similarity-chars', type=int, default=50000)
    p.add_argument('--similarity-threshold', type=float, default=0.80)
    p.add_argument('--max-dependency-edges', type=int, default=200000)
    args = p.parse_args(argv)
    root = args.folder.resolve()
    if not root.is_dir():
        p.error('Folder not found')
    if min(args.max_entries, args.max_total_uncompressed, args.max_entry_uncompressed, args.max_ratio, args.max_text_bytes, args.max_total_text_bytes, args.max_similarity_pairs, args.max_similarity_chars, args.max_dependency_edges) <= 0:
        p.error('Limits must be positive')
    if not 0 < args.similarity_threshold <= 1:
        p.error('Similarity threshold must be in (0, 1]')
    # Preserve the selected path until emit checks it; resolve() would hide a
    # directory symlink and bypass the destination guard.
    output = (args.output or root/'ZIP_AUDITOR_REPORT').absolute()
    if output.is_symlink():
        p.error('Output directory must not be a symbolic link')
    if output.resolve() == root:
        p.error('Output directory must not be input directory')
    report = build(root, args.recursive, args)
    try:
        emit(report, output)
    except (OSError, ValueError) as exc:
        print('Report output failed: ' + str(exc), file=sys.stderr)
        return 2
    print(f"Archives={report['archive_count']} duplicates={len(report['duplicate_groups'])} differences={len(report['same_path_different_content'])}")
    print(f'Reports: {output}')
    print('Dependencies: nodes=%s edges=%s status=%s runtime=NOT_RUN' % (report['dependency_analysis']['summary']['nodes'], report['dependency_analysis']['summary']['edges'], report['dependency_analysis']['status']))
    return 1 if any(a['status'] != 'ANALYZED' for a in report['archives']) else 0

if __name__ == '__main__':
    sys.exit(main())
