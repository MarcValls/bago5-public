"""Informes suplementarios sin activos de red ni scripts de contenido externo."""
import csv
import html
import json
from pathlib import Path


def safe_csv_cell(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False)
    if isinstance(value, str) and (value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@'))):
        return "'" + value
    return value


def _csv(path, fields, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            # Los datos proceden de ZIP no confiables: evita fórmulas al abrir en Excel.
            safe = {}
            for field in fields:
                safe[field] = safe_csv_cell(row.get(field, ''))
            writer.writerow(safe)


def _table(fields, rows):
    escape = lambda value: html.escape(str(value), quote=True)
    content = []
    for row in rows:
        content.append('<tr>' + ''.join('<td>' + escape(row.get(f, '')) + '</td>' for f in fields) + '</tr>')
    return '<div class="scroll"><table><thead><tr>' + ''.join('<th>' + escape(f) + '</th>' for f in fields) + '</tr></thead><tbody>' + ''.join(content) + '</tbody></table></div>'


def emit_analysis(result, output):
    output = Path(output)
    classes = result.get('duplicate_classification', {})
    dep = result.get('dependency_analysis', {})
    nodes = {n['id']: n for n in dep.get('nodes', [])}
    dup_rows = []
    for key in ('exact_content_groups', 'normalized_text_groups', 'logical_path_variants', 'similar_text_candidates'):
        for number, group in enumerate(classes.get(key, []), 1):
            for instance in group.get('instances', group.get('left', []) + group.get('right', [])):
                dup_rows.append({'group': key + ':' + str(number), 'classification': group['classification'],
                                 **instance, 'score': group.get('score', ''), 'status': 'PROPOSED',
                                 'criterion': group['criterion']})
    _csv(output/'duplicates.csv', ['group', 'classification', 'zip', 'path', 'id', 'sha256', 'score', 'status', 'criterion'], dup_rows)
    edge_rows = []
    for edge in dep.get('edges', []):
        src, target = nodes[edge['source']], nodes.get(edge.get('target'), {})
        edge_rows.append({**edge, 'source_zip': src['zip'], 'source_path': src['path'],
                          'target_zip': target.get('zip', ''), 'target_path': target.get('path', '')})
    _csv(output/'dependencies.csv', ['source', 'source_zip', 'source_path', 'line', 'kind', 'reference', 'status', 'target', 'target_zip', 'target_path', 'candidates', 'confidence', 'detail'], edge_rows)
    _csv(output/'dependency_nodes.csv', ['id', 'zip', 'path', 'analysis_status', 'incoming_references', 'incoming_runtime_references', 'outgoing_references', 'orphan_status'], dep.get('nodes', []))
    escape = lambda value: html.escape(str(value), quote=True)
    sections = ['<h2>Estado de las fuentes</h2>' + _table(['zip', 'status', 'warnings'], result['archives']),
                '<section id="classification"><h2>Clasificación de duplicados</h2>',
                '<p>Sin acciones automáticas. La similitud es una candidata a revisión; no acredita equivalencia funcional ni autoriza consolidar.</p>']
    summary = [{'clase': k, 'grupos': len(classes.get(k, []))} for k in
               ('exact_archive_groups', 'same_file_set_groups', 'exact_content_groups', 'normalized_text_groups', 'logical_path_variants', 'similar_text_candidates')]
    sections.append(_table(['clase', 'grupos'], summary))
    sections.append('<p>Cobertura de similitud: <code>' + escape(json.dumps(classes.get('similarity_coverage', {}), ensure_ascii=False)) + '</code></p>')
    sections.append('<details><summary>Ver ocurrencias clasificadas (' + str(len(dup_rows)) + ')</summary>' + _table(['group', 'classification', 'zip', 'path', 'score', 'status'], dup_rows) + '</details></section>')
    sections.append('<section id="dependencies"><h2>Dependencias estáticas</h2><p>Estado: <b>' + escape(dep.get('status')) + '</b>. Ejecución de fuentes: <b>NOT_RUN</b>. ' + escape(dep.get('resolution_policy', '')) + '</p>')
    sections.append(_table(['estado', 'cantidad'], [{'estado': k, 'cantidad': v} for k, v in dep.get('summary', {}).get('edge_status_counts', {}).items()]))
    sections.append('<details open><summary>Referencias locales no encontradas</summary>' + _table(['source_zip', 'source_path', 'line', 'kind', 'reference', 'confidence'], [e for e in edge_rows if e['status'] == 'MISSING_LOCAL']) + '</details>')
    sections.append('<details><summary>Todas las referencias (' + str(len(edge_rows)) + ')</summary>' + _table(['source_zip', 'source_path', 'line', 'kind', 'reference', 'status', 'target_path', 'confidence'], edge_rows) + '</details>')
    sections.append('<details><summary>Componentes cíclicas estáticas candidatas (' + str(len(dep.get('cycles', []))) + ')</summary><ul>' + ''.join('<li>' + ', '.join(escape(nodes[i]['zip'] + ':' + nodes[i]['path']) for i in group['node_ids']) + '</li>' for group in dep.get('cycles', [])) + '</ul></details>')
    orphans = []
    for candidate in dep.get('orphan_candidates', []):
        n = nodes[candidate['node_id']]
        orphans.append({'zip': n['zip'], 'path': n['path'], 'entrypoint_hint': candidate['entrypoint_hint'], 'status': candidate['status']})
    sections.append('<details><summary>Sin referencias estáticas entrantes de ejecución (' + str(len(orphans)) + ')</summary><p>Son candidatos. Un CLI, test o plugin puede ser válido sin referencias entrantes. Los enlaces de documentación no cuentan como llamadas de ejecución.</p>' + _table(['zip', 'path', 'entrypoint_hint', 'status'], orphans) + '</details>')
    sections.append('<details><summary>Cobertura por archivo</summary>' + _table(['zip', 'path', 'analysis_status', 'orphan_status'], dep.get('nodes', [])) + '</details></section>')
    document = (output/'report.html').read_text(encoding='utf-8')
    css = '<style>.scroll{overflow:auto}section{margin-block:2rem}details{margin-block:1rem}summary{cursor:pointer;font-weight:600}td{max-width:44rem}nav a{margin-right:1rem}</style>'
    nav = '<nav><a href="#classification">Duplicados</a><a href="#dependencies">Dependencias</a><a href="report.json">JSON</a><a href="duplicates.csv">CSV duplicados</a><a href="dependencies.csv">CSV dependencias</a><a href="dependency_nodes.csv">CSV nodos</a></nav>'
    document = document.replace('<h2>Inventario</h2>', css + nav + ''.join(sections) + '<h2>Inventario</h2>')
    (output/'report.html').write_text(document, encoding='utf-8')
