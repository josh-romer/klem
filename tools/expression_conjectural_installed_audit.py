"""Bind complete installed workloads and browser choices to original reviewed evidence."""
import gzip
import hashlib
import itertools
import json
import re
import unicodedata
from pathlib import Path

from conjectural_additive_novel_audit import matches
from formal_volitional_browser_audit import filtered, kept_indices

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inputs():
    docs = ROOT / 'docs'
    installed = lambda name: read(docs / ('expression-combined-installed-proof-' + name + '.gz'))
    names = ['source', 'copula', 'novel', 'cohorts', 'gold', 'broad', 'expression']
    references = ['conjectural-additive-phase2-copula-source-streams.json.gz',
                  'conjectural-additive-phase2-copula-cli-streams.json.gz',
                  'conjectural-additive-novel-context-prototype-regressions-retry1.json.gz',
                  'conjectural-additive-phase2-copula-cohorts.json.gz',
                  'conjectural-additive-phase2-copula-corpora.json.gz',
                  'conjectural-additive-phase2-copula-broad.json.gz',
                  'formal-volitional-expression-source-streams.json.gz']
    native = {}
    for filename in ['conjectural-additive-original-native-closure.json.gz',
                     'conjectural-additive-phase2-copula-native-closure.json.gz',
                     'conjectural-additive-novel-context-native-closure.json.gz']:
        for ident, entry in read(docs / filename)['complete_imported_entries'].items():
            assert ident not in native or native[ident] == entry, 'original Native overlap'
            native[ident] = entry
    for ident, entry in read(ROOT / 'tests/fixtures/formal-volitional-expression-native-entries.json').items():
        assert ident not in native or native[ident] == entry, 'original Native overlap'
        native[ident] = entry
    return {'binding': installed('combined-installed-source-binding.json'),
            'binding_raw': gzip.decompress((docs / 'expression-combined-installed-proof-combined-installed-source-binding.json.gz').read_bytes()),
            'release': installed('combined-installed-release-tests.json'),
            'release_log': gzip.decompress((docs / 'expression-combined-installed-proof-combined-installed-release-tests.log.gz').read_bytes()),
            'families': {name: installed('combined-installed-' + name + '.json') for name in names},
            'references': {name: read(docs / filename) for name, filename in zip(names, references, strict=True)},
            'browser': installed('combined-installed-browser.json'),
            'runtime': installed('combined-installed-browser-runtime.json'),
            'driver': gzip.decompress((docs / 'expression-combined-installed-proof-combined-browser.mjs.gz').read_bytes()),
            'supervisor': gzip.decompress((docs / 'expression-combined-installed-proof-run_installed_browser.py.gz').read_bytes()),
            'suites': [read(ROOT / 'tests/fixtures' / filename) for filename in ['conjectural-additive-validity.json', 'conjectural-additive-copula-validity.json', 'conjectural-additive-novel-validity.json', 'formal-volitional-expression-validity.json']],
            'native': native, 'labels': read(ROOT / 'web/src/grammar-labels.json')}


def inspect(v):
    binding = v['binding']
    assert binding['state'] == 'passed' and binding['exit_code'] == 0, 'terminal installed packages'
    assert all(binding[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged', 'all_tracked_inputs_unchanged']), 'frozen installed package inputs'
    assert sha(v['binding_raw']) == sha((json.dumps(binding, ensure_ascii=False, indent=2) + '\n').encode()), 'unchanged binding receipt'
    assert {name: len(p['files']) for name, p in binding['profiles'].items()} == {'klem': 1102, 'web-assets': 18, 'corpus-adapter': 1102}, 'complete actual package profiles'
    assert binding['profiles']['klem']['files'] == binding['profiles']['corpus-adapter']['files'], 'same CLI and adapter source'
    for profile in binding['profiles'].values():
        assert sha(profile['derivation_json'].encode()) == profile['derivation_json_sha256'], 'actual derivation capture'
        drv = json.loads(profile['derivation_json'])[profile['derivation']]
        assert drv['env']['src'] == profile['source'] and drv['outputs']['out']['path'] == profile['package'] and profile['package'] in binding['outputs'], 'actual derivation source and output'
    cli = binding['profiles']['klem']['package'] + '/bin/klem'
    adapter = binding['profiles']['corpus-adapter']['package'] + '/bin/klem-corpus-adapter'
    launcher = binding['launcher']
    assert sha(launcher['text'].encode()) == launcher['sha256'], 'actual launcher bytes'
    assert binding['profiles']['klem']['package'] + '/bin/klem-web' in launcher['text'] and binding['profiles']['web-assets']['package'] + '/share/klem-web' in launcher['text'], 'bound server and assets'
    release = v['release']
    batches = re.findall(rb'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', v['release_log'])
    totals = {key: sum(int(b[i + 1]) for b in batches) for i, key in enumerate(['passed', 'failed', 'ignored'])}
    assert sha(v['release_log']) == release['log_sha256'] and release['state'] == 'passed' and release['package'] == binding['profiles']['klem']['package'] and release['derivation'] == binding['profiles']['klem']['derivation'], 'actual installed release log'
    assert totals == release['totals'] == {'passed': 1164, 'failed': 0, 'ignored': 1} and len(batches) == release['batches'] == 251, 'complete actual release tests'
    assert list(v['families']) == ['source', 'copula', 'novel', 'cohorts', 'gold', 'broad', 'expression'], 'all seven installed families'
    for family, report in v['families'].items():
        assert report['family'] == family and report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged'], 'terminal installed workload'
        assert report['binding_sha256'] == sha(v['binding_raw']), 'same installed binding'
        assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual installed replay producer'
        old_runs = v['references'][family]['runs']
        assert len(report['runs']) == len(old_runs), 'complete installed workload runs'
        for run, old in zip(report['runs'], old_runs, strict=True):
            if family in ['source', 'copula', 'novel', 'expression']:
                assert [run[k] for k in ['family', 'encoding', 'mode', 'cache_bytes']] == [old.get('family', old.get('context')), old['encoding'], old['mode'], old['cache_bytes']], 'all original Unicode filter cache choices'
                assert run['records'] == old['records'] and run['input_sha256'] == old['input_sha256'] and run['stdout_sha256'] == run['reference_stdout_sha256'] == old['jsonl_sha256'] == sha(old['jsonl'].encode()) and run['exact_all_output_bytes'], 'every complete finite output'
                command = run['command']
                flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
                assert command[:4] == [cli, 'text', '-', '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags + ['--cache-bytes', str(run['cache_bytes'])] and run['exit_code'] == 0, 'actual finite filter command'
            elif family == 'cohorts':
                words = old['captures'][1]['words']
                assert run['family'] == old['family'] and run['surfaces'] == len(words) and run['binary'] == cli and run['every_original_word_and_path_identical'], 'complete original cohort identity'
                assert run['actual_words_sha256'] == run['reference_words_sha256'] == sha(json.dumps(words, ensure_ascii=False, sort_keys=True).encode()), 'every complete cohort word'
            elif family == 'gold':
                assert all(run[k] == old[k] for k in ['corpus', 'partition', 'source', 'source_sha256', 'rows']), 'all original annotated partitions'
                assert run['command'] == [adapter, run['corpus'], run['source']] and run['exit_code'] == 0 and run['every_original_annotated_row_and_summary_identical'], 'actual annotated adapter command'
                assert run['stdout_sha256'] == run['reference_stdout_sha256'] == old['stdout_sha256'] == sha(old['jsonl'].encode()), 'every complete annotated row and summary'
            else:
                assert all(run[k] == old[k] for k in ['mode', 'source', 'source_sha256', 'records']), 'complete original broad workloads'
                assert run['stdout_sha256'] == run['reference_stdout_sha256'] == old['after_jsonl_sha256'] and run['original_bytes_conserved'] and run['exact_all_output_bytes'] and run['all_individual_changed_records_exact'] == len(old['changed_frames']), 'every complete broad output'
                flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
                assert run['command'][:4] == [cli, 'text', run['actual_source'], '--dictionary'] and run['command'][4] in report['frozen_inputs'] and run['command'][5:] == flags + (['--suggest-spacing'] if 'spacing' in run['mode'] else []) and run['exit_code'] == 0, 'actual broad filter spacing command'
    assert sum(r['records'] for r in v['families']['broad']['runs']) == 1128312 and sum(r['rows'] for r in v['families']['gold']['runs']) == 66570 and sum(r['surfaces'] for r in v['families']['cohorts']['runs']) == 53502, 'complete broad gold cohort sizes'
    browser, runtime = v['browser'], v['runtime']
    assert browser['state'] == 'installed-combined-expression-conjectural-browser-passed' and not browser['errors'], 'terminal installed browser'
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'] and runtime['server_exit_code'] in [0, -2], 'owned installed server stopped'
    assert runtime['binding_sha256'] == sha(v['binding_raw']) and runtime['command'][:3] == [launcher['package'] + '/bin/klem-web', '--port', '0'] and runtime['command'][0] in runtime['frozen_inputs'], 'actual installed browser launcher'
    assert browser['producer_sha256'] == sha(v['driver']) and sha(v['driver']) in runtime['frozen_inputs'].values() and sha(v['supervisor']) in runtime['frozen_inputs'].values(), 'actual frozen browser producers'
    cases = [(case, judgment) for suite in v['suites'] for case in suite['cases'] for judgment in case['judgments'] if judgment['verdict'] == 'required']
    assert len(cases) == 56 and len({case['id'] + '/' + j['id'] for case, j in cases}) == 56, 'all original independent browser paths'
    policies = list(itertools.product(['NFC', 'NFD'], ['raw', 'headword', 'compatible']))
    assert [(e['encoding'], e['mode']) for e in browser['exports']] == policies and [r['encoding'] for r in browser['responses']] == ['NFC', 'NFD'], 'all six browser export choices'
    decisions, diagrams = [], []
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        raw = ' '.join(unicodedata.normalize(encoding, case['surface']) for case, _ in cases).encode()
        cursor = 0
        assert len(api['records']) == len(api['breakdowns']) == 111 and api['rules'].get('ending.conjectural_additive'), 'complete original browser API frames'
        for record in api['records']:
            assert record['span']['start'] == cursor and raw[cursor:record['span']['end']].decode() == record['surface'], 'complete original browser bytes'
            cursor = record['span']['end']
        assert cursor == len(raw), 'complete original browser bytes'
        words = [(i, r) for i, r in enumerate(api['records']) if r['kind'] == 'word']
        assert len(words) == len(cases), 'every original browser target'
        for mode in ['raw', 'headword', 'compatible']:
            export = next(e for e in browser['exports'] if (e['encoding'], e['mode']) == (encoding, mode))
            assert export['records'] == [filtered(r, mode) for r in api['records']], 'independently derived complete browser export'
            for (case, j), (ordinal, record) in zip(cases, words, strict=True):
                assert record['surface'] == unicodedata.normalize(encoding, case['surface']), 'original browser target identity'
                indices = [i for i, path in enumerate(record['analysis']['analyses']) if matches(path, j)]
                assert indices, 'independent typed browser path present'
                index = indices[0]
                path = record['analysis']['analyses'][index]
                kept = kept_indices(record, mode)
                ident = case['id'] + '/' + j['id']
                decision = {'case_id': ident, 'encoding': encoding, 'mode': mode, 'record_index': ordinal, 'raw_analysis_index': index, 'analysis': path, 'allowed': index in kept, 'offered_indices': [str(i) for i in kept] if kept else ['']}
                if not kept: decision['empty_message'] = 'No matching reading'
                decisions.append(decision)
                if index not in kept: continue
                heads = [head[:-1] if kind in ['predicate', 'auxiliary', 'copula'] and head.endswith('다') else head for head, kind in zip(j['lemmas'], j['lemma_kinds'], strict=True)]
                forms = [heads[0], *j['morphemes']] if len(heads) == 1 else [heads[0], j['morphemes'][0], heads[1], *j['morphemes'][1:]] if j['lemma_kinds'][1] == 'auxiliary' else [*heads, *j['morphemes']]
                if len(heads) == 1 and j['lemmas'][0].endswith('하다'):
                    if forms[1].startswith('어'): forms[1] = '여' + forms[1][1:]
                    elif forms[1].startswith('었'): forms[1] = '였' + forms[1][1:]
                diagrams.append((ident, encoding, mode, path, forms))
    assert browser['policyDecisions'] == decisions and len(decisions) == 336, 'every independently derived browser policy'
    assert [(d['case_id'], d['encoding'], d['mode'], d['analysis'], d['forms']) for d in browser['diagrams']] == diagrams and len(diagrams) == 336, 'every independent typed component order'
    for diagram in browser['diagrams']:
        final = diagram['analysis']['morphemes'][-1]
        label = v['labels'][('-' if final['kind'] != 'particle' else '') + final['form']]
        assert label['kind'] == final['kind'] and all(str(s['id']) in diagram['source_hint'] for s in label['sources']) and not diagram['references'], 'original grammar label owners'
    assert len(browser['nativeEntries']) == len(v['native']) == 73 and {r['id']: r['entry'] for r in browser['nativeEntries']} == v['native'], 'every original Native endpoint field'
    assert not browser['spacingDiagrams'], 'separate browser spacing scope'
    return {'state': 'complete-installed-expression-conjectural-audit-passed', 'rust_release_tests': 1164, 'finite_streams': 96, 'finite_frames': sum(r['records'] for name in ['source', 'copula', 'novel', 'expression'] for r in v['families'][name]['runs']), 'broad_frames': 1128312, 'annotated_rows': 66570, 'cohort_words': 53502, 'browser_decisions': 336, 'browser_diagrams': 336, 'browser_exports': 6, 'native_entries': 73, 'full_coverage_complete': False}


if __name__ == '__main__':
    print(inspect(inputs()))
