import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

MODULE = Path(__file__).resolve().parents[1] / "content_grouping.py"
spec = importlib.util.spec_from_file_location("content_grouping_subject", MODULE)
grouping = importlib.util.module_from_spec(spec)
spec.loader.exec_module(grouping)

PANTRY_CODE = '''
from decimal import Decimal
class PantryInventory:
    def __init__(self, household_records, pantry_capacity, delivery_schedule):
        self.household_records = household_records
        self.pantry_capacity = pantry_capacity
        self.delivery_schedule = delivery_schedule
    def register_delivery(self, household_identifier, selected_products, delivery_date):
        household_record = self.household_records[household_identifier]
        remaining_allowance = household_record['weekly_allowance']
        allocation_summary = []
        for product in selected_products:
            requested_units = product['requested_units']
            available_units = self.pantry_capacity.get(product['product_code'], 0)
            allocated_units = min(requested_units, available_units, remaining_allowance)
            allocation_summary.append({'household_identifier': household_identifier,
                                       'product_code': product['product_code'],
                                       'allocated_units': allocated_units,
                                       'delivery_date': delivery_date})
            remaining_allowance -= allocated_units
        household_record['remaining_allowance'] = remaining_allowance
        self.delivery_schedule.append(allocation_summary)
        return allocation_summary
    def summarize_households(self):
        household_summary = []
        for household_identifier, household_record in self.household_records.items():
            household_summary.append({'identifier': household_identifier,
                                      'remaining_allowance': household_record['remaining_allowance'],
                                      'delivery_count': len(self.delivery_schedule)})
        return household_summary
'''

HTML_CODE = '''<!doctype html><html><head><title>Huerto Familiar v1.0</title>
<style>body{font-family:system-ui;background:#fff}button{border:0;padding:12px}</style></head>
<body><h1>Huerto Familiar</h1><p>Calendario de riego y cosechas para cada parcela.</p>
<script>
const gardenParcels = [];
function registerHarvest(parcelIdentifier, vegetableSpecies, harvestedKilograms, harvestDate) {
  const harvestRecord = { parcelIdentifier, vegetableSpecies, harvestedKilograms, harvestDate };
  gardenParcels.push(harvestRecord);
  updateHarvestSummary();
  return harvestRecord;
}
function updateHarvestSummary() {
  const harvestByVegetable = {};
  gardenParcels.forEach(harvestRecord => {
    const vegetableSpecies = harvestRecord.vegetableSpecies;
    const previousHarvest = harvestByVegetable[vegetableSpecies] || 0;
    harvestByVegetable[vegetableSpecies] = previousHarvest + harvestRecord.harvestedKilograms;
  });
  document.getElementById('harvest-summary').textContent = JSON.stringify(harvestByVegetable);
  return harvestByVegetable;
}
function planIrrigation(parcelIdentifier, soilMoisture, irrigationLitres) {
  const irrigationSchedule = gardenParcels.filter(harvestRecord => harvestRecord.parcelIdentifier === parcelIdentifier);
  const irrigationNeeded = soilMoisture < 25;
  return { irrigationSchedule, irrigationNeeded, irrigationLitres, parcelIdentifier };
}
</script><div id="harvest-summary"></div></body></html>'''

WEATHER_CODE = '''
class StormForecast:
    def forecast_thunderstorms(self, atmospheric_pressure, wind_measurements, humidity_readings):
        regional_predictions = []
        for station_identifier, pressure_history in atmospheric_pressure.items():
            pressure_difference = pressure_history[-1] - pressure_history[0]
            gust_velocity = max(wind_measurements[station_identifier])
            relative_humidity = humidity_readings[station_identifier]
            thunderstorm_probability = abs(pressure_difference) * relative_humidity / (gust_velocity + 1)
            regional_predictions.append({'station_identifier': station_identifier,
                                         'thunderstorm_probability': thunderstorm_probability,
                                         'gust_velocity': gust_velocity,
                                         'relative_humidity': relative_humidity})
        return regional_predictions
    def publish_weather_bulletin(self, regional_predictions, weather_office):
        bulletin_paragraphs = []
        for prediction in regional_predictions:
            bulletin_paragraphs.append(weather_office.format_station_prediction(prediction))
        return '\\n'.join(bulletin_paragraphs)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_archive(root, name, files, reverse=False):
    target = root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    items = list(files.items())
    if reverse:
        items.reverse()
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for filename, content in items:
            info = zipfile.ZipInfo(filename, date_time=(2025, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zipped.writestr(info, content.encode() if isinstance(content, str) else content)
    return target


def archive_record(root, path):
    relative = path.relative_to(root).as_posix()
    record = {'zip': relative, 'zip_sha256': sha(path.read_bytes()), 'status': 'ANALYZED', 'entries': []}
    with zipfile.ZipFile(path) as zipped:
        paths = [info.filename for info in zipped.infolist() if not info.is_dir()]
        first = {name.split('/')[0] for name in paths}
        prefix = next(iter(first)) + '/' if len(first) == 1 and all('/' in name for name in paths) else ''
        for index, info in enumerate(zipped.infolist()):
            if info.is_dir():
                continue
            data = zipped.read(info)
            record['entries'].append({'path': info.filename, 'logical_path': info.filename[len(prefix):],
                                      'entry_index': index, 'size': info.file_size, 'compressed_size': info.compress_size,
                                      'sha256': sha(data), 'status': 'ANALYZED', 'issues': []})
    return record


def write_report(parent, files, rows=None):
    source = parent / 'inputs'
    source.mkdir(exist_ok=True)
    if rows is None:
        rows = [archive_record(source, write_archive(source, name, contents)) for name, contents in files.items()]
    output = parent / 'report'
    output.mkdir(exist_ok=True)
    value = {'schema_version': '0.2', 'tool_version': '0.2.2', 'root': str(source.absolute()), 'archives': rows,
             'archive_count': len(rows)}
    target = output / 'report.json'
    target.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
    (output / 'SHA256SUMS.json').write_text(json.dumps({'report.json': sha(target.read_bytes())}))
    (output / 'verificacion.json').write_text('{"status":"PASS"}')
    return source, target


def package_files(code=PANTRY_CODE, name='Despensa Vecinal v1.0', root=''):
    return {root + 'package.json': json.dumps({'name': name, 'dependencies': {'react': 'latest'}}),
            root + 'src/pantry.py': code, root + 'README.md': '# ' + name}


def grouped_members(plan):
    archives = {item['id']: item['relative_path'] for item in plan['archives']}
    return {frozenset(archives[identifier] for identifier in group['member_ids']) for group in plan['groups']}


class ContentGroupingTests(unittest.TestCase):
    def test_renamed_archives_modified_code_and_root_names_group(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            changed = PANTRY_CODE.replace("remaining_allowance -= allocated_units", "remaining_allowance -= max(0, allocated_units)")
            source, report = write_report(root, {'download_ABC.zip': package_files(root='old-prototype/'),
                                                  'unrelated_filename_937.zip': package_files(changed, 'Despensa Vecinal v2.1', root='totally-renamed-root/')})
            before = {path: path.read_bytes() for path in source.rglob('*.zip')}
            plan = grouping.build_proposal(report)
            self.assertEqual(grouped_members(plan), {frozenset(before_path.name for before_path in before)})
            self.assertEqual(plan['groups'][0]['label'], 'Despensa Vecinal')
            self.assertNotIn('download', plan['groups'][0]['directory_name'])
            self.assertEqual(plan['groups'][0]['evidence']['pairs'][0]['functional_equivalence'], 'NOT_VERIFIED')
            self.assertEqual({path: path.read_bytes() for path in before}, before)
            self.assertFalse(Path(plan['paths']['json']).exists())

    def test_single_html_minor_changes_group_without_zip_name_signal(self):
        with tempfile.TemporaryDirectory() as folder:
            changed = HTML_CODE.replace('v1.0', 'v1.1').replace('soilMoisture < 25', 'soilMoisture < 30')
            _, report = write_report(Path(folder), {'one.zip': {'index.html': HTML_CODE},
                                                   'completely_different.zip': {'prototype.html': changed}})
            plan = grouping.build_proposal(report)
            self.assertEqual(len(plan['groups']), 1)
            self.assertEqual(len(plan['groups'][0]['member_ids']), 2)
            self.assertEqual(plan['groups'][0]['label'], 'Huerto Familiar')

    def test_unrelated_apps_sharing_dependencies_template_and_readme_are_separate(self):
        with tempfile.TemporaryDirectory() as folder:
            common = {'package.json': json.dumps({'name': 'vite-react-starter', 'dependencies': {'react': '18'}}),
                      'README.md': '# Vite React Starter\nA web app template.',
                      'src/main.jsx': "import React from 'react';\nReactDOM.createRoot(document.getElementById('root')).render(<App/>);",
                      'node_modules/giant/library.py': PANTRY_CODE,
                      'package-lock.json': json.dumps({'dependencies': {'everything': 'same'}})}
            _, report = write_report(Path(folder), {'app_one.zip': dict(common, **{'src/app.py': PANTRY_CODE}),
                                                   'app_two.zip': dict(common, **{'src/app.py': WEATHER_CODE})})
            plan = grouping.build_proposal(report)
            self.assertEqual(len(plan['groups']), 2)
            self.assertTrue(all(group['status'] == 'SIN_COINCIDENCIAS' for group in plan['groups']))

    def test_declaration_only_does_not_group(self):
        with tempfile.TemporaryDirectory() as folder:
            _, report = write_report(Path(folder), {'a.zip': {'package.json': '{"name":"Shared Specific Name"}', 'a.txt': 'one'},
                                                   'b.zip': {'package.json': '{"name":"Shared Specific Name"}', 'b.txt': 'two'}})
            plan = grouping.build_proposal(report)
            self.assertEqual(len(plan['groups']), 2)

    def test_tiny_exact_own_code_requires_domain_anchor_and_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            files = {'package.json': '{"name":"cuaderno-aurora"}',
                     'src/main.py': 'from records import record_note\nprint(record_note("aurora"))\n',
                     'src/records.py': 'def record_note(value):\n    return {"aurora_note": value}\n'}
            _, report = write_report(Path(folder), {'first.zip': dict(files, **{'version.txt': '1'}),
                                                   'second.zip': dict(files, **{'version.txt': '2'})})
            plan = grouping.build_proposal(report)
            self.assertEqual(len(plan['groups']), 1)
            self.assertEqual(plan['groups'][0]['evidence']['pairs'][0]['rule'], 'EXACT_OWN_CODE_WITH_DOMAIN_IDENTITY')

    def test_entry_reordering_and_report_order_do_not_change_content_partition_or_label(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder)
            source, report = write_report(parent, {'a.zip': package_files(), 'b.zip': package_files(PANTRY_CODE + '\n# Edition two\n')})
            first = grouping.build_proposal(report)
            write_archive(source, 'a.zip', package_files(), reverse=True)
            rows = [archive_record(source, source / 'b.zip'), archive_record(source, source / 'a.zip')]
            _, report = write_report(parent, {}, rows=rows)
            second = grouping.build_proposal(report)
            self.assertEqual(grouped_members(first), grouped_members(second))
            self.assertEqual([group['label'] for group in first['groups']], [group['label'] for group in second['groups']])
            self.assertEqual([group['evidence']['pairs'][0]['metrics'] for group in first['groups']],
                             [group['evidence']['pairs'][0]['metrics'] for group in second['groups']])

    def test_low_text_budget_keeps_verified_sources_as_singletons(self):
        with tempfile.TemporaryDirectory() as folder:
            _, report = write_report(Path(folder), {'a.zip': package_files(), 'b.zip': package_files(PANTRY_CODE + '\n# other')})
            with patch.dict(grouping.LIMITS, {'max_text_file_bytes': 30}):
                plan = grouping.build_proposal(report)
            self.assertEqual(plan['coverage']['eligible_archives'], 2)
            self.assertEqual(len(plan['groups']), 2)
            self.assertTrue(all(group['status'] == 'SIN_COINCIDENCIAS' for group in plan['groups']))

    def test_corrupt_source_hash_drift_and_symlink_are_excluded(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, report = write_report(root, {'a.zip': package_files(), 'b.zip': package_files()})
            (source / 'a.zip').write_bytes(b'changed after analysis')
            plan = grouping.build_proposal(report)
            bad = next(item for item in plan['archives'] if item['relative_path'] == 'a.zip')
            self.assertFalse(bad['eligible'])
            self.assertIn('SOURCE_HASH_MISMATCH', bad['issues'])
            (source / 'b.zip').rename(root / 'external.zip')
            try:
                (source / 'b.zip').symlink_to(root / 'external.zip')
            except OSError:
                self.skipTest('Symlink creation unavailable')
            plan = grouping.build_proposal(report)
            self.assertEqual(plan['coverage']['eligible_archives'], 0)
            self.assertEqual(plan['groups'], [])
            record = {'zip': 'bad.zip', 'zip_sha256': sha(b'not a zip'), 'status': 'ERROR', 'entries': []}
            (source / 'bad.zip').write_bytes(b'not a zip')
            _, report = write_report(root, {}, rows=[record])
            plan = grouping.build_proposal(report)
            self.assertFalse(plan['archives'][0]['eligible'])
            self.assertTrue(any('BadZipFile' in issue for issue in plan['archives'][0]['issues']))

    def test_entry_index_metadata_and_member_hash_are_checked(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, report = write_report(root, {'a.zip': package_files()})
            row = archive_record(source, source / 'a.zip')
            row['entries'][0]['entry_index'] = 999
            _, report = write_report(root, {}, rows=[row])
            plan = grouping.build_proposal(report)
            self.assertIn('ENTRY_INDEX_MISMATCH', plan['archives'][0]['issues'])
            row = archive_record(source, source / 'a.zip')
            row['entries'][0]['sha256'] = '0' * 64
            _, report = write_report(root, {}, rows=[row])
            plan = grouping.build_proposal(report)
            self.assertIn('MEMBER_HASH_MISMATCH', plan['archives'][0]['issues'])

    def test_seal_deterministic_and_persisted_plan_exactly_matches_return(self):
        with tempfile.TemporaryDirectory() as folder:
            source, report = write_report(Path(folder), {'mystery.zip': package_files()})
            first = grouping.build_proposal(report)
            second = grouping.write_proposal(report)
            self.assertEqual(first, second)
            self.assertEqual(second, json.loads(Path(second['paths']['json']).read_text(encoding='utf-8')))
            self.assertEqual(grouping.plan_digest(second), second['plan_sha256'])
            mutated = copy.deepcopy(second)
            mutated['paths']['html'] += '.changed'
            self.assertNotEqual(grouping.plan_digest(mutated), second['plan_sha256'])
            document = Path(second['paths']['html']).read_text(encoding='utf-8')
            self.assertIn('no crea copias', '\n'.join(first['console_lines']))
            self.assertIn('Esta propuesta no crea copias por sí sola', document)
            self.assertTrue((source / 'mystery.zip').is_file())

    def test_singleton_directory_name_windows_safe_and_content_derived(self):
        with tempfile.TemporaryDirectory() as folder:
            _, report = write_report(Path(folder), {'totally_unknown.zip': {'index.html': HTML_CODE.replace('Huerto Familiar', 'Planos: Norte / Sur? v2.5')}})
            plan = grouping.build_proposal(report)
            group = plan['groups'][0]
            self.assertEqual(group['status'], 'SIN_COINCIDENCIAS')
            self.assertNotIn('totally_unknown', group['directory_name'])
            self.assertFalse(any(char in group['directory_name'] for char in '<>:"/\\|?*'))
            self.assertFalse(group['directory_name'].endswith((' ', '.')))
            self.assertEqual(grouping._directory_name('CON', '1234'), 'Contenido__1234')

    def test_complete_link_rejects_chain_only_group(self):
        def profile(identifier):
            return {'record': {'id': identifier, 'sha256': identifier}, 'fingerprint': identifier,
                    'identities': [], 'extensions': {}, 'core_files': [], 'text_files_read': 1, 'coverage': 1.0, 'notes': []}
        profiles = [profile('a'), profile('b'), profile('c')]
        pairs = {('a', 'b'): {'qualifies': True, 'score': .9}, ('b', 'c'): {'qualifies': True, 'score': .9},
                 ('a', 'c'): {'qualifies': False, 'score': .0}}
        groups = grouping._make_groups(profiles, pairs, grouping.LIMITS)
        self.assertEqual(sorted(len(group['member_ids']) for group in groups), [1, 2])

    def test_report_hash_drift_fails_before_proposal(self):
        with tempfile.TemporaryDirectory() as folder:
            _, report = write_report(Path(folder), {'one.zip': package_files()})
            report.write_bytes(report.read_bytes() + b' ')
            with self.assertRaises(ValueError):
                grouping.build_proposal(report)

    def test_pair_budget_is_explicit_and_every_eligible_is_partitioned(self):
        with tempfile.TemporaryDirectory() as folder:
            _, report = write_report(Path(folder), {f'archive_{n}.zip': package_files(PANTRY_CODE + f'\n# revision {n}\n') for n in range(4)})
            with patch.dict(grouping.LIMITS, {'max_pairs': 1}):
                plan = grouping.build_proposal(report)
            self.assertEqual(plan['coverage']['examined_pairs'], 1)
            self.assertEqual(plan['coverage']['unexamined_pairs'], 5)
            members = [identifier for group in plan['groups'] for identifier in group['member_ids']]
            self.assertEqual(sorted(members), sorted(item['id'] for item in plan['archives'] if item['eligible']))
            self.assertEqual(len(members), len(set(members)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
