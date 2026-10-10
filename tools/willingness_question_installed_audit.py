"""Bind actual installed willingness outputs to preserved source and gold evidence."""
import argparse
import gzip
import hashlib
import json
import os
import re
import signal
import unicodedata
from pathlib import Path

from willingness_question_browser_audit import matches, filtered, kept_indices

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
REFERENCES = {
    'source': ('source-streams', '63f20a56f92c8919b3b68365667d707f45a036749ed4b6584d48becc1343c6ac'),
    'cohorts': ('cohorts', 'a5ac66a08a01e8fabe12ca6c2ecb638c7bf5d214d006892566181e916b010a3d'),
    'gold': ('corpora', 'a436df9184a7db2d440a88afcbe118c5b5ccc6596b8311458e0a155e135b5b6d'),
    'broad': ('broad', 'b361afea8a34f690fa4df13e31d9949775ae4f1461ee286f88e1a5f53831ae56'),
}


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inputs(prepared=None):
    prepared = prepared or os.environ.get('KLEM_WILLINGNESS_INSTALLED_PROOFS')
    def raw(name):
        if prepared:
            p = Path(prepared) / name
            if p.exists():
                return p.read_bytes()
            return gzip.decompress(Path(str(p) + '.gz').read_bytes())
        return gzip.decompress((ROOT / 'docs' / ('willingness-question-installed-proof-' + name + '.gz')).read_bytes())
    installed = lambda name: json.loads(raw(name))
    references = {}
    for family, (name, digest) in REFERENCES.items():
        p = ROOT / 'docs' / ('willingness-question-distribution-proof-willingness-' + name + '.json.gz')
        assert sha(p.read_bytes()) == digest, 'unchanged pre-install prototype reference'
        references[family] = read(p)
    native = read(ROOT / 'tests/fixtures/willingness-question-native-entries.json')
    supplemental = read(ROOT / 'docs/willingness-question-source-proof-supplemental-pos-native-closure.json.gz')['complete_imported_entries']
    assert not (native.keys() & supplemental.keys())
    return {'binding': installed('willingness-installed-source-binding-retry1.json'),
            'binding_raw': raw('willingness-installed-source-binding-retry1.json'),
            'release': installed('willingness-installed-release-tests.json'),
            'release_log': raw('willingness-installed-release-tests.log'),
            'full_rust': installed('willingness-merged-full-rust.json'),
            'full_rust_raw': raw('willingness-merged-full-rust.json'),
            'selected_validation': installed('willingness-selected-inventory-source.json'),
            'selected_logs': [raw('willingness-selected-inventory-audit-' + str(i) + '.log') for i in range(18)],
            'families': {name: installed('willingness-installed-' + name + '.json') for name in REFERENCES},
            'references': references,
            'browser': installed('willingness-installed-browser.json'),
            'runtime': installed('willingness-installed-browser-runtime.json'),
            'driver': raw('willingness-installed-browser.mjs'),
            'supervisor': raw('run_willingness_installed_browser.py'),
            'suites': [read(ROOT / 'tests/fixtures' / name) for name in ['willingness-question-validity.json', 'willingness-question-boundary-validity.json']],
            'label': read(ROOT / 'web/src/grammar-labels.json')['-으련'],
            'native': native, 'import_native': dict(native, **supplemental)}


def inspect_source_evidence(v):
    b, selected = v['binding'], v['selected_validation']
    assert selected['state'] == 'passed' and selected['exit_code'] == 0 and all(selected[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged']), 'terminal unchanged selected-source validation'
    assert selected['head'] == b['head'] and selected['all_tracked_files'] == b['all_tracked_files'], 'same complete tracked source snapshot'
    assert len(selected['runs']) == len(v['selected_logs']) == 18 and selected['controls'] == 233, 'complete independent selected-source audits'
    counts = [None, 14, None, 30, None, 17, None, 18, None, 14, None, 8, None, 28, None, 94, None, 10]
    names = ['willingness_question_source_audit', 'willingness_question_distribution_audit', 'willingness_question_browser_audit', 'expression_conjectural_ledger_audit', 'conjectural_additive_ledger_audit', 'formal_volitional_expression_ledger_audit', 'expression_conjectural_installed_audit', 'literary_question_geona_runtime', 'review_inventory']
    for i, (run, log, count) in enumerate(zip(selected['runs'], v['selected_logs'], counts, strict=True)):
        name = names[i // 2]
        assert run['exit_code'] == 0 and sha(log) == run['log_sha256'] and run['controls'] == count, 'actual independent audit logs'
        command = run['command']
        if count is None:
            expected = ['python3', 'tools/' + name + '.py']
            if name == 'literary_question_geona_runtime': expected += ['--report', 'docs/literary-question-geona-packaged-cli-replay.json']
            if name == 'review_inventory': expected += ['--verify']
        else:
            expected = ['python3', '-m', 'unittest', 'discover', '-s', 'tools', '-p', 'test_' + name + '.py']
            assert re.search(rb'Ran ' + str(count).encode() + rb' tests? in ', log) and log.rstrip().endswith(b'OK'), 'actual independent control count'
        assert command == expected, 'all original independent source audit commands'


def inspect_binding(v):
    b = v['binding']
    assert b['state'] == 'passed' and b['exit_code'] == 0, 'terminal installed packages'
    assert all(b[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged', 'all_tracked_inputs_unchanged']), 'frozen installed package inputs'
    assert sha(v['binding_raw']) == sha((json.dumps(b, ensure_ascii=False, indent=2) + '\n').encode()), 'unchanged binding receipt'
    assert {name: len(p['files']) for name, p in b['profiles'].items()} == {'klem': 1111, 'web-assets': 18, 'corpus-adapter': 1111}, 'complete actual package profiles'
    assert b['profiles']['klem']['files'] == b['profiles']['corpus-adapter']['files'], 'same CLI and adapter sources'
    assert len(b['outputs']) == 4 and len(set(b['outputs'])) == 4, 'all four actual packages'
    for profile in b['profiles'].values():
        assert sha(profile['derivation_json'].encode()) == profile['derivation_json_sha256'], 'actual derivation capture'
        drv = json.loads(profile['derivation_json'])[profile['derivation']]
        assert drv['env']['src'] == profile['source'] and drv['outputs']['out']['path'] == profile['package'] and profile['package'] in b['outputs'], 'actual derivation source and output'
        for f in profile['files'].values():
            assert b['all_tracked_files'][f['snapshot_path']] == f['sha256'], 'every selected file bound to tracked source'
    launcher = b['launcher']
    assert launcher['package'] in b['outputs'] and sha(launcher['text'].encode()) == launcher['sha256'], 'actual launcher bytes'
    assert b['profiles']['klem']['package'] + '/bin/klem-web' in launcher['text'] and b['profiles']['web-assets']['package'] + '/share/klem-web' in launcher['text'], 'bound server and assets'
    release = v['release']
    assert release['state'] == 'passed' and release['exit_code'] == 0 and sha(v['release_log']) == release['log_sha256'], 'actual installed release log'
    assert release['binding_sha256'] == sha(v['binding_raw']) and release['package'] == b['profiles']['klem']['package'] and release['derivation'] == b['profiles']['klem']['derivation'], 'same installed release derivation'
    batches = re.findall(rb'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', v['release_log'])
    totals = {key: sum(int(batch[i + 1]) for batch in batches) for i, key in enumerate(['passed', 'failed', 'ignored'])}
    assert all(batch[0] == b'ok' for batch in batches) and totals == release['totals'] == b['full_rust_totals'] == {'passed': 1174, 'failed': 0, 'ignored': 1} and len(batches) == release['batches'] == 252, 'complete actual release tests'
    full = v['full_rust']
    assert full['state'] == 'passed' and full['exit_code'] == 0 and all(full[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged']), 'terminal frozen debug Rust receipt'
    assert sha(v['full_rust_raw']) == b['full_rust_input_receipt_sha256'] == sha((json.dumps(full, ensure_ascii=False, indent=2) + '\n').encode()), 'actual debug Rust receipt'
    assert full['totals'] == totals and full['batches'] == 252, 'same complete debug and release tests'
    expected_outside = ['LICENSE-APACHE', 'LICENSE-MIT', 'examples/audit_adjectival_allomorph.rs', 'examples/benchmark.rs', 'examples/benchmark_stream.rs', 'examples/dictionary_coverage.rs', 'examples/evaluate.rs', 'examples/evaluate_validity.rs']
    outside = []
    for name, f in b['profiles']['klem']['files'].items():
        key = '/tmp/klem-willingness-question-prototype/' + f['snapshot_path']
        if key in full['frozen_inputs']:
            assert full['frozen_inputs'][key] == f['sha256'], 'actual shared debug Rust input bytes'
        else:
            outside.append(name)
    assert sorted(outside) == expected_outside, 'explicit debug Rust snapshot boundary'
    # The six example files and license files were outside the debug capture;
    # the installed Nix source binding/release build freezes all1111selected files.
    # Actual adapter/gold replays independently cover the example-backed adapter.


def inspect_families(v):
    b = v['binding']
    cli = b['profiles']['klem']['package'] + '/bin/klem'
    adapter = b['profiles']['corpus-adapter']['package'] + '/bin/klem-corpus-adapter'
    assert list(v['families']) == list(REFERENCES), 'all four installed workload families'
    for family, report in v['families'].items():
        assert report['family'] == family and report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged'], 'terminal installed workload'
        assert report['binding_sha256'] == sha(v['binding_raw']), 'same installed workload binding'
        assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual frozen replay producer'
        assert cli in report['frozen_inputs'] and adapter in report['frozen_inputs'], 'actual installed replay binaries'
        old_runs = v['references'][family]['runs']
        assert len(report['runs']) == len(old_runs), 'complete installed workload runs'
        for run, old in zip(report['runs'], old_runs, strict=True):
            if family == 'source':
                assert [run[k] for k in ['family', 'encoding', 'mode', 'cache_bytes']] == [old[k] for k in ['family', 'encoding', 'mode', 'cache_bytes']], 'all original Unicode filter cache choices'
                assert run['records'] == old['records'] and run['input_sha256'] == old['input_sha256'] and run['stdout_sha256'] == run['reference_stdout_sha256'] == old['jsonl_sha256'] == sha(old['jsonl'].encode()) and run['exact_all_output_bytes'], 'every complete finite output'
                flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
                command = run['command']
                assert command[:4] == [cli, 'text', '-', '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags + ['--cache-bytes', str(run['cache_bytes'])] and run['exit_code'] == 0, 'actual finite filter command'
            elif family == 'cohorts':
                words = old['captures'][1]['words']
                assert run['family'] == old['family'] and run['surfaces'] == len(words) and run['binary'] == cli and run['every_committed_word_and_path_identical'], 'complete original cohort identity'
                assert run['actual_words_sha256'] == run['reference_words_sha256'] == sha(json.dumps(words, ensure_ascii=False, sort_keys=True).encode()), 'every complete cohort word'
            elif family == 'gold':
                assert all(run[k] == old[k] for k in ['corpus', 'partition', 'source', 'source_sha256', 'rows']), 'all original annotated partitions'
                assert run['command'] == [adapter, run['corpus'], run['source']] and run['exit_code'] == 0 and run['every_committed_annotated_row_and_summary_identical'], 'actual annotated adapter command'
                assert report['frozen_inputs'][str(Path(report['cwd']) / run['source'])] == run['source_sha256'], 'original corpus input bound'
                assert run['stdout_sha256'] == run['reference_stdout_sha256'] == old['stdout_sha256'] == sha(old['jsonl'].encode()), 'every complete annotated row and summary'
            else:
                assert all(run[k] == old[k] for k in ['mode', 'source', 'source_sha256', 'records']), 'complete original broad workloads'
                assert run['stdout_sha256'] == run['reference_stdout_sha256'] == old['after_jsonl_sha256'] and run['original_bytes_conserved'] and run['exact_all_output_bytes'] and run['all_individual_changed_records_exact'] == len(old['changed_frames']), 'every complete broad output'
                flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
                command = run['command']
                assert command[:2] == [cli, 'text'] and report['frozen_inputs'][command[2]] == run['source_sha256'] and command[3] == '--dictionary' and command[4] in report['frozen_inputs'] and command[5:] == flags + (['--suggest-spacing'] if 'spacing' in run['mode'] else []) and run['exit_code'] == 0, 'actual broad filter spacing command'
    source = v['families']['source']
    imported = source['native_import']
    assert imported['original_native_owners'] == len(v['import_native']) == 30 and imported['every_complete_original_field_exact'] and imported['complete_imported_entries'] == v['import_native'], 'every complete original imported Native field'
    assert imported['database'] in source['frozen_inputs'] and imported['command'][0:2] == [cli, 'dict'] and imported['command'][2] == 'import-krdict' and imported['command'][4:] == [imported['database'], '--snapshot', 'independent-current-willingness-native'], 'actual installed Native importer command'
    assert imported['entry_queries'] == [[cli, 'dict', 'entry', imported['database'], ident] for ident in v['import_native']], 'every original Native query command'
    assert len(source['runs']) == 24 and sum(r['records'] for r in source['runs']) == 3336 and sum(r['surfaces'] for r in v['families']['cohorts']['runs']) == 53502 and sum(r['rows'] for r in v['families']['gold']['runs']) == 66570 and sum(r['records'] for r in v['families']['broad']['runs']) == 1128312, 'complete workload dimensions'


def inspect_browser(v):
    b, runtime, browser = v['binding'], v['runtime'], v['browser']
    assert browser['state'] == 'source-bound-willingness-installed-browser-passed' and not browser['errors'] and browser['producer_sha256'] == sha(v['driver']), 'actual error-free installed browser'
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'] and runtime['server_exit_code'] in [0, -signal.SIGINT], 'owned installed server stopped'
    command = runtime['command']
    assert runtime['binding_sha256'] == sha(v['binding_raw']) and command[:3] == [b['launcher']['package'] + '/bin/klem-web', '--port', '0'] and command[3] == '--dictionary' and command[4] in runtime['frozen_inputs'], 'actual installed browser launcher'
    assert command[0] in runtime['frozen_inputs'] and b['profiles']['klem']['package'] + '/bin/klem' in runtime['frozen_inputs'] and b['profiles']['klem']['package'] + '/bin/klem-web' in runtime['frozen_inputs'], 'actual installed browser binaries'
    assert sha(v['driver']) in runtime['frozen_inputs'].values() and sha(v['supervisor']) in runtime['frozen_inputs'].values(), 'actual frozen browser producers'
    assert sha(runtime['producer']['text'].encode()) == runtime['producer']['sha256'] == sha(v['supervisor']), 'actual installed browser supervisor'
    assets = b['profiles']['web-assets']['package'] + '/share/klem-web/'
    assert assets + 'index.html' in runtime['frozen_inputs'] and any(p.startswith(assets + 'assets/') and p.endswith('.js') for p in runtime['frozen_inputs']), 'actual installed frontend assets'
    # Apply the original independent typed-path/display/export checks directly;
    # never invent prototype build identities for an installed browser.
    inspect_browser_choices(v)


def inspect_browser_choices(v):
    browser = v['browser']
    cases = [(case, j) for suite in v['suites'] for case in suite['cases'] for j in case['judgments'] if j['verdict'] == 'required']
    assert len(cases) == 15, 'all independent source and boundary paths'
    assert [r['encoding'] for r in browser['responses']] == ['NFC', 'NFD'], 'both original browser Unicode encodings'
    assert [(e['encoding'], e['mode']) for e in browser['exports']] == [(encoding, mode) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']], 'all six original browser exports'
    expected_decisions, expected_diagrams = [], []
    label = v['label']
    assert label['kind'] == 'ending' and label['sources'] == [{'id': 76564, 'headword': '-련', 'pos': '어미'}, {'id': 76567, 'headword': '-으련', 'pos': '어미'}], 'ending owners remain separate from expression homonyms'
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        raw = unicodedata.normalize(encoding, ' '.join(case['surface'] for case, _ in cases)).encode()
        cursor = 0
        for record in api['records']:
            assert record['span']['start'] == cursor and raw[cursor:record['span']['end']].decode() == record['surface'], 'all original browser input bytes and spans'
            cursor = record['span']['end']
        assert cursor == len(raw), 'complete original browser sentence'
        assert 'ending.willingness_question' in api['rules'], 'new rule explanation present'
        indices = [i for i, r in enumerate(api['records']) if r['kind'] == 'word']
        assert len(indices) == len(cases), 'all original browser target words'
        for mode in ['raw', 'headword', 'compatible']:
            export = next(e for e in browser['exports'] if (e['encoding'], e['mode']) == (encoding, mode))
            assert export['records'] == [filtered(record, mode) for record in api['records']], 'every independently filtered complete export'
            for (case, judgment), record_index in zip(cases, indices, strict=True):
                record = api['records'][record_index]
                paths = record['analysis']['analyses']
                matching = [i for i, p in enumerate(paths) if matches(p, judgment)]
                assert matching, 'all independently typed browser decompositions'
                index = matching[0]
                path = paths[index]
                offered = [str(i) for i in kept_indices(record, mode)]
                assert str(index) in offered, 'original required path offered by dictionary policy'
                case_id = case['id'] + '/' + judgment.get('id', 'path')
                expected_decisions.append({'case_id': case_id, 'encoding': encoding, 'mode': mode, 'record_index': record_index, 'raw_analysis_index': index, 'analysis': path, 'allowed': True, 'offered_indices': offered})
                expected_diagrams.append((case_id, encoding, mode, path, [judgment['lemmas'][0][:-1], *judgment['morphemes']]))
    assert browser['policyDecisions'] == expected_decisions and len(expected_decisions) == 90, 'all original reading dropdown policies'
    assert len(browser['diagrams']) == len(expected_diagrams) == 90, 'all original browser diagrams'
    for diagram, expected in zip(browser['diagrams'], expected_diagrams, strict=True):
        assert (diagram['case_id'], diagram['encoding'], diagram['mode'], diagram['analysis'], diagram['forms']) == expected, 'all independently typed display components and order'
        assert not diagram['references'] and all(str(source['id']) in diagram['source_hint'] for source in label['sources']), 'original ending source ownership displayed'
    assert not browser['spacingDiagrams'], 'separate missing-space scope'
    assert len(v['native']) == len(browser['nativeEntries']) == 29 and {r['id']: r['entry'] for r in browser['nativeEntries']} == v['native'], 'every complete original Native endpoint field'


def inspect(v):
    inspect_source_evidence(v)
    inspect_binding(v)
    inspect_families(v)
    inspect_browser(v)
    return {'state': 'complete-installed-willingness-audit-passed', 'rust_release_tests': 1174,
            'source_streams': 24, 'source_frames': 3336, 'cohort_words': 53502,
            'annotated_rows': 66570, 'broad_frames': 1128312,
            'import_native_owners': 30, 'browser_decisions': 90,
            'browser_diagrams': 90, 'browser_exports': 6, 'browser_native_owners': 29,
            'contextual_review_complete': False, 'full_coverage_complete': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepared', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(inputs(args.prepared)), ensure_ascii=False, indent=2))
