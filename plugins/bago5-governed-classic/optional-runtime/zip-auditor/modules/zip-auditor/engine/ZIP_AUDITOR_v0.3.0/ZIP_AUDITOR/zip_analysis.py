"""Clasificación y referencias estáticas de ZIP; nunca importa código analizado."""
import ast
import bisect
from collections import Counter, defaultdict
import difflib
import hashlib
import json
import posixpath
import re
import sys
from pathlib import PurePosixPath
from urllib.parse import unquote
try:
    import tomllib
except ImportError:  # Python 3.9/3.10 siguen funcionando sin análisis TOML.
    tomllib = None

TEXT_EXTENSIONS = {'.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                   '.ps1', '.cmd', '.bat', '.sh', '.md', '.txt', '.json', '.toml',
                   '.cfg', '.ini', '.yaml', '.yml', '.html', '.css', '.csv', '.xml'}
SOURCE_EXTENSIONS = {'.py', '.pyi', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs',
                     '.ps1', '.cmd', '.bat', '.sh'}
JS_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
RUNTIME_KINDS = {'PYTHON_IMPORT', 'PYTHON_DYNAMIC_LITERAL', 'JS_IMPORT',
                 'JS_REQUIRE', 'SCRIPT_REFERENCE', 'PACKAGE_ENTRY'}


def content_text(name, data):
    """Normaliza exclusivamente BOM UTF-8 y saltos CRLF/CR; no espacios ni caso."""
    if PurePosixPath(name).suffix.lower() not in TEXT_EXTENSIONS or b'\x00' in data:
        return None
    try:
        return data.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    except UnicodeDecodeError:
        return None


def identify(archives):
    """Identidad por ocurrencia, preservando nombres duplicados dentro del ZIP."""
    nodes = {}
    for ai, archive in enumerate(archives, 1):
        archive['id'] = 'A%05d' % ai
        paths = [e['path'].replace('\\', '/') for e in archive['entries']
                 if 'UNSAFE_PATH' not in e['issues']]
        first = {p.split('/')[0] for p in paths}
        prefix = next(iter(first)) + '/' if len(first) == 1 and all('/' in p for p in paths) else ''
        archive['logical_root_prefix'] = prefix
        for ei, entry in enumerate(archive['entries'], 1):
            entry['id'] = '%s:E%06d' % (archive['id'], ei)
            path = entry['path'].replace('\\', '/')
            entry['logical_path'] = path[len(prefix):] if prefix and path.startswith(prefix) else path
            nodes[entry['id']] = {'id': entry['id'], 'zip': archive['zip'], **entry}
    return nodes


def reference(node):
    return {k: node[k] for k in ('id', 'zip', 'path', 'logical_path', 'sha256', 'size')}


def classify(archives, nodes, texts, limits):
    by_hash, by_path, by_normalized = defaultdict(list), defaultdict(list), defaultdict(list)
    for node in nodes.values():
        if node['sha256']:
            by_hash[node['sha256']].append(node)
            if 'UNSAFE_PATH' not in node['issues']:
                by_path[node['logical_path']].append(node)
        if node['id'] in texts:
            digest = hashlib.sha256(texts[node['id']].encode('utf-8')).hexdigest()
            by_normalized[digest].append(node)
    exact = []
    for digest, group in sorted(by_hash.items()):
        if len(group) < 2:
            continue
        archive_counts = Counter(n['zip'] for n in group)
        tags = []
        if len(archive_counts) > 1:
            tags.append('MULTIPLE_DISTRIBUTIONS_REVIEW_INDEPENDENCE')
        if any(c > 1 for c in archive_counts.values()):
            tags.append('WITHIN_ARCHIVE_REVIEW_ROLE')
        if any(n['issues'] for n in group):
            tags.append('ENTRY_ISSUES_REVIEW_REQUIRED')
        if any(PurePosixPath(n['path']).name.lower() in {'__init__.py', '.gitkeep'} or n['size'] == 0 for n in group):
            tags.append('SMALL_OR_MARKER_FILES_MAY_BE_INTENTIONAL')
        exact.append({'classification': 'EXACT_BYTES', 'sha256': digest,
                      'instances': [reference(n) for n in group], 'review_tags': tags,
                      'criterion': 'SHA-256 del contenido descomprimido idéntico; no equivalencia funcional.'})
    normalized = [{'classification': 'NORMALIZED_TEXT', 'normalized_sha256': digest,
                   'instances': [reference(n) for n in group],
                   'criterion': 'Iguales tras eliminar BOM UTF-8 y normalizar CRLF/CR a LF; bytes distintos.',
                   'status': 'PROPOSED'}
                  for digest, group in sorted(by_normalized.items())
                  if len({n['sha256'] for n in group}) > 1]
    variants = [{'classification': 'LOGICAL_PATH_VARIANTS', 'logical_path': path,
                 'variants': sorted({n['sha256'] for n in group}),
                 'instances': [reference(n) for n in group],
                 'criterion': 'Misma ruta tras retirar una única carpeta envolvente común; no implica conflicto ni orden de versiones.',
                 'status': 'PROPOSED'}
                for path, group in sorted(by_path.items()) if len({n['sha256'] for n in group}) > 1]
    archive_hashes, file_sets = defaultdict(list), defaultdict(list)
    for a in archives:
        if a['zip_sha256']:
            archive_hashes[a['zip_sha256']].append(a['zip'])
        if a['status'] == 'ANALYZED' and a['entries'] and all(not e['issues'] for e in a['entries']):
            signature = sorted((e['logical_path'], e['sha256']) for e in a['entries'])
            digest = hashlib.sha256(json.dumps(signature, ensure_ascii=True).encode()).hexdigest()
            file_sets[digest].append(a['zip'])
    candidates = []
    considered = compared = potential = 0
    budget = getattr(limits, 'max_similarity_pairs', 10000)
    threshold = getattr(limits, 'similarity_threshold', 0.80)
    max_chars = getattr(limits, 'max_similarity_chars', 50000)
    skipped_large = 0
    exhausted = False
    for path, group in sorted(by_path.items()):
        # Una representante por variante textual, conservando todas las ocurrencias.
        unique = {}
        for n in group:
            text = texts.get(n['id'])
            if text is not None and len(text) >= 40:
                unique.setdefault(text, []).append(n)
        values = list(unique.items())
        potential += len(values) * (len(values) - 1) // 2
        for i, (left, left_nodes) in enumerate(values):
            for right, right_nodes in values[i + 1:]:
                if considered >= budget:
                    exhausted = True
                    break
                considered += 1
                if len(left) > max_chars or len(right) > max_chars:
                    skipped_large += 1
                    continue
                compared += 1
                # Tokens acotados y autojunk; puntuación heurística, nunca semántica.
                lt = re.findall(r'\w+|[^\w\s]', left)
                rt = re.findall(r'\w+|[^\w\s]', right)
                matcher = difflib.SequenceMatcher(None, lt, rt, autojunk=True)
                if matcher.quick_ratio() < threshold:
                    continue
                score = matcher.ratio()
                if score >= threshold:
                    candidates.append({'classification': 'SIMILAR_TEXT_CANDIDATE', 'logical_path': path,
                                       'score': round(score, 6), 'threshold': threshold,
                                       'left': [reference(n) for n in left_nodes],
                                       'right': [reference(n) for n in right_nodes],
                                       'criterion': 'SequenceMatcher sobre tokens, solo misma ruta lógica; no prueba equivalencia.',
                                       'status': 'PROPOSED'})
            if exhausted:
                break
    return {'exact_content_groups': exact, 'normalized_text_groups': normalized,
            'logical_path_variants': variants, 'similar_text_candidates': candidates,
            'exact_archive_groups': [{'classification': 'EXACT_ARCHIVE_BYTES', 'sha256': h, 'archives': names}
                                     for h, names in sorted(archive_hashes.items()) if len(names) > 1],
            'same_file_set_groups': [{'classification': 'SAME_LOGICAL_FILE_SET', 'inventory_sha256': h,
                                     'archives': names, 'criterion': 'Mismo multiconjunto de rutas lógicas y SHA, sin entradas omitidas ni incidencias; metadatos ZIP pueden diferir.'}
                                    for h, names in sorted(file_sets.items()) if len(names) > 1],
            'text_coverage': {'captured_entries': len(texts), 'eligible_text_entries': sum(PurePosixPath(n['path']).suffix.lower() in TEXT_EXTENSIONS for n in nodes.values()),
                              'status_counts': dict(sorted(Counter(n.get('text_status', 'NOT_SUPPORTED') for n in nodes.values()).items())),
                              'note': 'Normalización/similitud solo sobre las entradas capturadas. El inventario SHA cubre también binarios y textos no capturados.'},
            'similarity_coverage': {'potential_pairs': potential, 'considered_pairs': considered, 'compared_pairs': compared,
                                    'skipped_large': skipped_large, 'pair_limit': budget,
                                    'status': 'PARTIAL' if exhausted or skipped_large else 'COMPLETE_WITHIN_SCOPE',
                                    'scope': 'UTF-8 legible dentro de límites, misma ruta lógica, mínimo 40 caracteres.'},
            'automatic_actions': [], 'consolidation_status': 'PROPOSED_ONLY'}


def _cycles(node_ids, edges):
    """Kosaraju iterativo: sin recursión, para grafos grandes."""
    forward, reverse = defaultdict(set), defaultdict(set)
    for e in edges:
        if e['status'] == 'RESOLVED_INTERNAL' and e['kind'] in RUNTIME_KINDS:
            forward[e['source']].add(e['target'])
            reverse[e['target']].add(e['source'])
    visited, order = set(), []
    for start in sorted(node_ids):
        if start in visited:
            continue
        stack = [(start, False)]
        while stack:
            n, done = stack.pop()
            if done:
                order.append(n)
                continue
            if n in visited:
                continue
            visited.add(n)
            stack.append((n, True))
            stack.extend((x, False) for x in sorted(forward[n], reverse=True) if x not in visited)
    visited, groups = set(), []
    for start in reversed(order):
        if start in visited:
            continue
        stack, component = [start], []
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            component.append(n)
            stack.extend(reverse[n] - visited)
        if len(component) > 1 or start in forward[start]:
            groups.append({'node_ids': sorted(component), 'classification': 'STATIC_RUNTIME_CYCLE_CANDIDATE',
                           'criterion': 'Componente fuertemente conexa de referencias estáticas; no demuestra fallo de ejecución.'})
    return sorted(groups, key=lambda g: g['node_ids'])


class DependencyAnalyzer:
    def __init__(self, archives, nodes, texts, limits):
        self.archives = {a['zip']: a for a in archives}
        self.nodes, self.texts = nodes, texts
        self.edges, self.coverage = [], []
        self.by_path = defaultdict(lambda: defaultdict(list))
        self.edge_keys = set()
        self.max_edges = getattr(limits, 'max_dependency_edges', 200000)
        self.omitted_edges = 0
        self.declared = defaultdict(set)
        self.stdlib = set(getattr(sys, 'stdlib_module_names', ())) | set(sys.builtin_module_names)
        for n in nodes.values():
            if 'UNSAFE_PATH' not in n['issues']:
                path = n['path'].replace('\\', '/')
                self.by_path[n['zip']][path].append(n['id'])
        for node_id, text in texts.items():
            n = nodes[node_id]
            if PurePosixPath(n['path']).name == 'package.json':
                try:
                    data = json.loads(text)
                    if isinstance(data, dict):
                        for field in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
                            if isinstance(data.get(field), dict):
                                self.declared[n['zip']].update(data[field])
                except (ValueError, TypeError, RecursionError):
                    pass
            elif re.fullmatch(r'requirements[^/]*\.txt', PurePosixPath(n['path']).name, re.I):
                for line in text.splitlines():
                    m = re.match(r'\s*([\w.-]+)(?:\[|[<>=!~;\s]|$)', line)
                    if m:
                        self.declared[n['zip']].add(m[1].lower().replace('-', '_'))
            elif PurePosixPath(n['path']).name == 'pyproject.toml' and tomllib is not None:
                try:
                    data = tomllib.loads(text)
                    for spec in data.get('project', {}).get('dependencies', []):
                        match = re.match(r'([\w.-]+)', spec) if isinstance(spec, str) else None
                        if match:
                            self.declared[n['zip']].add(match[1].lower().replace('-', '_'))
                except (ValueError, TypeError, AttributeError, RecursionError):
                    pass

    def add(self, node, kind, ref, line, status, target=None, candidates=None, confidence='STATIC_SYNTAX', detail=''):
        key = (node['id'], kind, ref, line, status, target)
        if key in self.edge_keys:
            return
        if len(self.edges) >= self.max_edges:
            self.omitted_edges += 1
            return
        self.edge_keys.add(key)
        self.edges.append({'source': node['id'], 'target': target, 'kind': kind, 'reference': ref,
                           'line': line, 'status': status, 'candidates': candidates or [],
                           'confidence': confidence, 'detail': detail,
                           'evidence': {'zip_sha256': self.archives[node['zip']]['zip_sha256'],
                                        'entry_sha256': node['sha256'], 'entry_index': node['entry_index']}})

    def candidates(self, node, paths):
        for path in paths:
            hits = self.by_path[node['zip']].get(path, [])
            if hits:
                return hits
        return []

    def resolve_paths(self, node, kind, ref, line, paths, missing='MISSING_LOCAL', confidence='STATIC_SYNTAX'):
        hits = self.candidates(node, paths)
        if len(hits) == 1:
            self.add(node, kind, ref, line, 'RESOLVED_INTERNAL', target=hits[0], confidence=confidence)
        elif hits:
            self.add(node, kind, ref, line, 'AMBIGUOUS_INTERNAL', candidates=hits, confidence=confidence)
        else:
            self.add(node, kind, ref, line, missing, confidence=confidence,
                     detail='No resuelto dentro del mismo ZIP; no se toma una copia de otra distribución.')
        return hits

    def local(self, node, kind, ref, line, js=False, confidence='STATIC_SYNTAX'):
        raw = unquote(ref.split('#', 1)[0].split('?', 1)[0]).replace('\\', '/')
        raw = raw.replace('$PSScriptRoot/', '').replace('${PSScriptRoot}/', '').replace('%~dp0', '')
        if not raw:
            return
        if raw.startswith('/') or re.match(r'^[A-Za-z]:', raw):
            self.add(node, kind, ref, line, 'OUTSIDE_ARCHIVE', confidence=confidence)
            return
        if '$' in raw or '%' in raw or '*' in raw or '{' in raw:
            self.add(node, kind, ref, line, 'DYNAMIC_NOT_RESOLVED', confidence=confidence)
            return
        path = posixpath.normpath(posixpath.join(posixpath.dirname(node['path'].replace('\\', '/')), raw))
        if path == '..' or path.startswith('../'):
            self.add(node, kind, ref, line, 'OUTSIDE_ARCHIVE', confidence=confidence)
            return
        paths = [path]
        if js:
            paths.extend(path + s for s in ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.json', '.d.ts'))
            paths.extend(path + '/index' + s for s in ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'))
            if path.endswith(('.js', '.mjs', '.cjs')):
                paths.extend(path.rsplit('.', 1)[0] + s for s in ('.ts', '.tsx', '.mts', '.cts'))
        return self.resolve_paths(node, kind, ref, line, paths, confidence=confidence)

    def python_import(self, node, module, line, level=0, kind='PYTHON_IMPORT', required=True):
        folder = posixpath.dirname(node['path'].replace('\\', '/'))
        bases = []
        if level:
            base = folder
            for _ in range(level - 1):
                base = posixpath.dirname(base) if base else '..'
            if base == '..' or not folder:
                if required:
                    self.add(node, kind, '.' * level + module, line, 'OUTSIDE_ARCHIVE')
                return []
            bases.append(base)
        else:
            base = folder
            while True:
                bases.append(base)
                if not base:
                    break
                base = posixpath.dirname(base)
            # layouts src/ explícitos, nunca búsqueda global por basename.
            bases += [posixpath.join(b, 'src') for b in list(bases)]
        stem = module.replace('.', '/')
        paths = []
        for base in bases:
            prefix = posixpath.join(base, stem) if stem else base
            paths += [prefix + '.py', prefix + '.pyi', prefix + '/__init__.py', prefix + '/__init__.pyi']
        hits = self.candidates(node, paths)
        ref = '.' * level + module
        if hits or (required and level):
            return self.resolve_paths(node, kind, ref, line, paths)
        if required:
            top = module.split('.')[0]
            if top in self.stdlib:
                status = 'STANDARD_LIBRARY'
            elif top in self.declared[node['zip']]:
                status = 'DECLARED_EXTERNAL'
            else:
                status = 'UNRESOLVED_IMPORT'
            self.add(node, kind, ref, line, status, detail='Resolución estática; no comprueba importación ni instalación real.')
        return []

    def python(self, node, text):
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError, MemoryError) as exc:
            return 'PARSE_ERROR', type(exc).__name__
        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                for alias in item.names:
                    self.python_import(node, alias.name, item.lineno)
            elif isinstance(item, ast.ImportFrom):
                if item.module:
                    self.python_import(node, item.module, item.lineno, item.level)
                for alias in item.names:
                    if alias.name == '*':
                        continue
                    module = (item.module + '.' if item.module else '') + alias.name
                    hits = self.python_import(node, module, item.lineno, item.level, required=False)
                    if not item.module and not hits:
                        # Puede ser un atributo de __init__, no necesariamente un archivo ausente.
                        parent_hits = self.python_import(node, '', item.lineno, item.level, required=False)
                        if not parent_hits:
                            self.add(node, 'PYTHON_IMPORT', '.' * item.level + alias.name,
                                     item.lineno, 'UNRESOLVED_IMPORT', detail='Puede ser módulo o atributo del paquete.')
            elif isinstance(item, ast.Call):
                func = item.func
                name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else '')
                if name in {'__import__', 'import_module'}:
                    value = item.args[0] if item.args else None
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        ref = value.value
                        if ref.startswith('.'):
                            self.add(node, 'PYTHON_DYNAMIC_LITERAL', ref, item.lineno,
                                     'DYNAMIC_NOT_RESOLVED', detail='Import relativo dinámico requiere contexto package.')
                        else:
                            self.python_import(node, ref, item.lineno, kind='PYTHON_DYNAMIC_LITERAL')
                    else:
                        self.add(node, 'PYTHON_DYNAMIC_LITERAL', '<dynamic>', item.lineno, 'DYNAMIC_NOT_RESOLVED')
        return 'PARSED', ''

    def javascript(self, node, text):
        # Regex acotadas: heurística explícita, sin cargar parsers o bundles del ZIP.
        string_spans = []
        def strip_comment(match):
            if match.group(1) is not None:
                string_spans.append((match.start(), match.end()))
                return match.group(1)
            return re.sub(r'[^\n]', ' ', match.group())
        cleaned = re.sub(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`(?:\\.|[^`\\])*`)|//[^\n]*|/\*[\s\S]*?\*/',
                         strip_comment, text)
        starts = [s[0] for s in string_spans]
        def inside_string(position):
            index = bisect.bisect_right(starts, position) - 1
            return index >= 0 and position < string_spans[index][1]
        patterns = [('JS_IMPORT', r'\b(?:import|export)\s+(?:[^;\n]*?\s+from\s+)?[\'\"]([^\'\"]+)[\'\"]'),
                    ('JS_REQUIRE', r'\brequire\s*\(\s*[\'\"]([^\'\"]+)[\'\"]\s*\)'),
                    ('JS_IMPORT', r'\bimport\s*\(\s*[\'\"]([^\'\"]+)[\'\"]\s*\)')]
        for kind, pattern in patterns:
            for m in re.finditer(pattern, cleaned):
                if inside_string(m.start()):
                    continue
                ref, line = m.group(1), cleaned.count('\n', 0, m.start()) + 1
                if ref.startswith('.') or ref.startswith('/'):
                    self.local(node, kind, ref, line, js=True, confidence='HEURISTIC_REGEX')
                else:
                    package = '/'.join(ref.split('/')[:2]) if ref.startswith('@') else ref.split('/')[0]
                    status = 'DECLARED_EXTERNAL' if package in self.declared[node['zip']] else 'EXTERNAL_OR_ALIAS'
                    self.add(node, kind, ref, line, status, confidence='HEURISTIC_REGEX',
                             detail='Puede ser paquete, módulo integrado o alias; no se verifica instalación.')
        for m in re.finditer(r'\b(?:import|require)\s*\(\s*(?![\s\'\"])([^)\n]+)\)', cleaned):
            if inside_string(m.start()):
                continue
            self.add(node, 'JS_IMPORT', '<dynamic>', cleaned.count('\n', 0, m.start()) + 1,
                     'DYNAMIC_NOT_RESOLVED', confidence='HEURISTIC_REGEX')
        return 'HEURISTIC_ANALYZED', 'Sin AST JS/TS; alias y template strings no se resuelven.'

    def links(self, node, text):
        for m in re.finditer(r'(?<!!)\[[^\]\n]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)', text):
            ref = m.group(1).strip('<>')
            if not ref or ref.startswith('#') or re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', ref) or ref.startswith('//'):
                continue
            self.local(node, 'DOCUMENT_LINK', ref, text.count('\n', 0, m.start()) + 1, confidence='HEURISTIC_REGEX')
        return 'HEURISTIC_ANALYZED', 'Solo enlaces inline Markdown; no establece dependencia de ejecución.'

    def scripts(self, node, text, kind='SCRIPT_REFERENCE'):
        for line_no, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith(('#', 'REM ', 'rem ', '::')):
                continue
            for m in re.finditer(r'''["']([^"'\r\n]+\.(?:py|ps1|cmd|bat|sh|js|cjs|mjs|ts))["']|(?<![\w/\\])((?:\.{1,2}[/\\]|%~dp0|\$PSScriptRoot[/\\])[^\s"'<>|]+\.(?:py|ps1|cmd|bat|sh|js|cjs|mjs|ts))''', line, re.I):
                self.local(node, kind, m.group(1) or m.group(2), line_no, confidence='HEURISTIC_LITERAL_PATH')
        return 'HEURISTIC_ANALYZED', 'Referencias literales; variables calculadas no se resuelven.'

    def manifest(self, node, text):
        try:
            data = json.loads(text)
        except (ValueError, RecursionError) as exc:
            return 'PARSE_ERROR', type(exc).__name__
        if not isinstance(data, (dict, list)):
            return 'PARSED', 'JSON sin referencias de archivo reconocibles.'
        stack = [('', data)]
        while stack:
            key, value = stack.pop()
            if isinstance(value, dict):
                for k, v in value.items():
                    # Manifiestos SHA (ruta como clave) son referencias, no código.
                    if isinstance(v, str) and re.fullmatch(r'[a-fA-F0-9]{64}', v) and PurePosixPath(k).suffix:
                        self.manifest_reference(node, k)
                    stack.append((k, v))
            elif isinstance(value, list):
                stack.extend((key, v) for v in value)
            elif isinstance(value, str) and key.lower() in {'path', 'file', 'source', 'target', 'main', 'module', 'types', 'script', 'entry', 'entrypoint'}:
                if PurePosixPath(value).suffix and not re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', value):
                    kind = 'PACKAGE_ENTRY' if PurePosixPath(node['path']).name == 'package.json' and key in {'main', 'module'} else 'MANIFEST_REFERENCE'
                    if kind == 'PACKAGE_ENTRY':
                        self.local(node, kind, value, None)
                    else:
                        self.manifest_reference(node, value)
        if PurePosixPath(node['path']).name == 'package.json' and isinstance(data, dict):
            for field in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
                deps = data.get(field, {})
                if isinstance(deps, dict):
                    for package, spec in sorted(deps.items()):
                        self.add(node, 'PACKAGE_DECLARATION', '%s@%s' % (package, spec), None, 'DECLARED_EXTERNAL')
            scripts = data.get('scripts', {})
            if isinstance(scripts, dict):
                for value in scripts.values():
                    if isinstance(value, str):
                        for match in re.finditer(r'(?:^|\s)([.\w/@-]+\.(?:js|ts|cjs|mjs|py))(?:\s|$)', value):
                            self.local(node, 'PACKAGE_ENTRY', match.group(1), None, confidence='HEURISTIC_LITERAL_PATH')
        return 'PARSED', 'Solo claves explícitas y manifiestos SHA; referencias JSON sin número de línea.'

    def manifest_reference(self, node, ref):
        """Los inventarios suelen usar la raíz del paquete, otros manifiestos su carpeta."""
        raw = ref.replace('\\', '/')
        if raw.startswith(('./', '../', '/')) or re.match(r'^[A-Za-z]:', raw):
            return self.local(node, 'MANIFEST_REFERENCE', ref, None)
        parent = posixpath.dirname(node['path'].replace('\\', '/'))
        wrapper = self.archives[node['zip']]['logical_root_prefix'].rstrip('/')
        paths = {posixpath.normpath(posixpath.join(base, raw)) for base in (parent, wrapper, '')}
        hits = sorted({hit for path in paths for hit in self.by_path[node['zip']].get(path, [])})
        if len(hits) == 1:
            self.add(node, 'MANIFEST_REFERENCE', ref, None, 'RESOLVED_INTERNAL', target=hits[0],
                     confidence='HEURISTIC_MANIFEST_BASE', detail='Coincidencia única entre carpeta del manifiesto, raíz envolvente y raíz del ZIP; base inferida.')
        elif hits:
            self.add(node, 'MANIFEST_REFERENCE', ref, None, 'AMBIGUOUS_INTERNAL', candidates=hits,
                     confidence='HEURISTIC_MANIFEST_BASE', detail='Varias bases posibles del manifiesto contienen esta ruta.')
        else:
            self.add(node, 'MANIFEST_REFERENCE', ref, None, 'UNRESOLVED_MANIFEST_REFERENCE',
                     confidence='HEURISTIC_MANIFEST_BASE', detail='No se conoce la base declarada; puede ser inventario de origen o referencia externa. No equivale a dependencia rota.')

    def requirements(self, node, text):
        for no, raw in enumerate(text.splitlines(), 1):
            line = raw.split('#', 1)[0].strip()
            if not line:
                continue
            m = re.match(r'(?:-r\s*|--requirement(?:=|\s+)|-c\s*|--constraint(?:=|\s+))(.+)', line)
            if m:
                self.local(node, 'MANIFEST_REFERENCE', m.group(1).strip('"\''), no)
            elif not line.startswith('-'):
                self.add(node, 'PACKAGE_DECLARATION', line, no, 'DECLARED_EXTERNAL')
        return 'PARSED', 'Declaraciones; no resuelve versiones, vulnerabilidades ni paquetes instalados.'

    def pyproject(self, node, text):
        if tomllib is None:
            return 'NOT_SUPPORTED', 'Análisis TOML requiere Python 3.11+; no se instala ningún parser.'
        try:
            data = tomllib.loads(text)
        except (ValueError, TypeError, RecursionError) as exc:
            return 'PARSE_ERROR', type(exc).__name__
        project = data.get('project', {})
        raw_specs = project.get('dependencies', []) if isinstance(project, dict) else []
        specs = list(raw_specs) if isinstance(raw_specs, list) else []
        optional = project.get('optional-dependencies', {}) if isinstance(project, dict) else {}
        if isinstance(optional, dict):
            for values in optional.values():
                if isinstance(values, list):
                    specs.extend(values)
        build_system = data.get('build-system', {})
        if isinstance(build_system, dict) and isinstance(build_system.get('requires'), list):
            specs.extend(build_system['requires'])
        for spec in specs:
            if isinstance(spec, str):
                self.add(node, 'PACKAGE_DECLARATION', spec, None, 'DECLARED_EXTERNAL')
        for field in ('scripts', 'gui-scripts'):
            scripts = project.get(field, {}) if isinstance(project, dict) else {}
            if isinstance(scripts, dict):
                for value in scripts.values():
                    if isinstance(value, str) and ':' in value:
                        self.python_import(node, value.split(':', 1)[0], None, kind='PACKAGE_ENTRY')
        return 'PARSED', 'PEP 621/build-system: declaraciones y entry points; no comprueba instalación ni resuelve versiones.'

    def analyze(self):
        for node in self.nodes.values():
            text = self.texts.get(node['id'])
            ext = PurePosixPath(node['path']).suffix.lower()
            state, detail = 'NOT_SUPPORTED', 'Sin analizador para este formato.'
            if node['status'] != 'ANALYZED' or 'UNSAFE_PATH' in node['issues']:
                state, detail = 'NOT_ANALYZED', 'Entrada no legible o ruta insegura.'
            elif ext == '.zip':
                state, detail = 'NESTED_ARCHIVE_NOT_ANALYZED', 'ZIP anidado inventariado por hash, sin recursión interna.'
            elif text is None and (ext in SOURCE_EXTENSIONS | {'.md', '.json'} or PurePosixPath(node['path']).name == 'pyproject.toml' or re.fullmatch(r'requirements[^/]*\.txt', PurePosixPath(node['path']).name, re.I)):
                state, detail = 'NOT_ANALYZED', 'Límite de texto, codificación no UTF-8 o texto binario.'
            elif text is not None:
                if ext in {'.py', '.pyi'}:
                    state, detail = self.python(node, text)
                elif ext in JS_EXTENSIONS:
                    state, detail = self.javascript(node, text)
                elif ext == '.md':
                    state, detail = self.links(node, text)
                elif ext in {'.ps1', '.cmd', '.bat', '.sh'}:
                    state, detail = self.scripts(node, text)
                elif ext == '.json':
                    state, detail = self.manifest(node, text)
                elif PurePosixPath(node['path']).name == 'pyproject.toml':
                    state, detail = self.pyproject(node, text)
                elif re.fullmatch(r'requirements[^/]*\.txt', PurePosixPath(node['path']).name, re.I):
                    state, detail = self.requirements(node, text)
            self.coverage.append({'node_id': node['id'], 'status': state, 'detail': detail})
        inbound, runtime_inbound, outgoing = Counter(), Counter(), Counter()
        runtime_dependents, other_dependents = defaultdict(set), defaultdict(set)
        for edge in self.edges:
            outgoing[edge['source']] += 1
            if edge['status'] == 'RESOLVED_INTERNAL':
                inbound[edge['target']] += 1
                if edge['kind'] in RUNTIME_KINDS:
                    runtime_inbound[edge['target']] += 1
                    runtime_dependents[edge['target']].add(edge['source'])
                else:
                    other_dependents[edge['target']].add(edge['source'])
        coverage_by_id = {c['node_id']: c for c in self.coverage}
        node_rows, orphans = [], []
        for n in self.nodes.values():
            coverage = coverage_by_id[n['id']]
            source = PurePosixPath(n['path']).suffix.lower() in SOURCE_EXTENSIONS
            parsed = coverage['status'] in {'PARSED', 'HEURISTIC_ANALYZED'}
            row = {**reference(n), 'analysis_status': coverage['status'], 'incoming_references': inbound[n['id']],
                   'incoming_runtime_references': runtime_inbound[n['id']], 'outgoing_references': outgoing[n['id']],
                   'runtime_dependents': sorted(runtime_dependents[n['id']]),
                   'other_dependents': sorted(other_dependents[n['id']]),
                   'orphan_status': 'NOT_ASSESSED'}
            if source and parsed:
                row['orphan_status'] = 'REFERENCED_STATICALLY' if runtime_inbound[n['id']] else 'NO_STATIC_RUNTIME_INBOUND'
                if not runtime_inbound[n['id']]:
                    orphans.append({'node_id': n['id'], 'status': 'PROPOSED',
                                    'classification': 'ORPHAN_CANDIDATE_ONLY',
                                    'entrypoint_hint': ('__main__' in self.texts.get(n['id'], '') or PurePosixPath(n['path']).suffix.lower() in {'.cmd', '.bat', '.sh', '.ps1'}),
                                    'reason': 'Sin referencias estáticas entrantes de ejecución; puede ser CLI, plugin, test, export o carga dinámica.'})
            node_rows.append(row)
        counts = Counter(e['status'] for e in self.edges)
        return {'status': 'PARTIAL' if self.omitted_edges or any(a['status'] != 'ANALYZED' for a in self.archives.values()) or any(c['status'] in {'PARSE_ERROR', 'NOT_ANALYZED'} for c in self.coverage) else 'STATIC_ANALYZED_WITH_LIMITS',
                'nodes': node_rows, 'edges': self.edges, 'coverage': self.coverage,
                'cycles': _cycles(self.nodes, self.edges), 'orphan_candidates': orphans,
                'missing_local_references': [e for e in self.edges if e['status'] == 'MISSING_LOCAL'],
                'ambiguous_references': [e for e in self.edges if e['status'] == 'AMBIGUOUS_INTERNAL'],
                'summary': {'nodes': len(node_rows), 'edges': len(self.edges), 'edge_status_counts': dict(sorted(counts.items())),
                            'coverage_status_counts': dict(sorted(Counter(c['status'] for c in self.coverage).items())),
                            'orphan_candidates': len(orphans), 'omitted_edges': self.omitted_edges},
                'resolution_policy': 'Cada ZIP es independiente. Resolución Python aproximada de directorios padres y src; no replica sys.path ni ejecuta importaciones. JS/shell/Markdown heurísticos.',
                'runtime_verification': 'NOT_RUN', 'declaration_scope': 'ARCHIVE_NOT_ENVIRONMENT',
                'stdlib_catalog_runtime': sys.version.split()[0], 'consolidation_authorized': False}


def analyze_dependencies(archives, nodes, texts, limits):
    return DependencyAnalyzer(archives, nodes, texts, limits).analyze()
