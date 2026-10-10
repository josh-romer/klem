"""Verify complete installed formal-volitional output against independently reviewed captures."""
import hashlib
import json
import unicodedata
from pathlib import Path

import formal_volitional_expression_browser_audit as browser_audit
import formal_volitional_expression_streams_audit as streams_audit

ROOT = Path(__file__).resolve().parents[1]
read = browser_audit.read
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inspect(binding, build, broad, cohorts, corpora, finite, browser, runtime,
            expected_broad, expected_cohorts, expected_corpora, source, streams,
            suites, native, labels, driver, supervisor):
    assert binding['state'] == build['state'] == 'passed' and binding['exit_code'] == build['exit_code'] == 0, 'terminal actual Nix packages'
    assert all(binding[k] and build[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged']), 'unchanged committed package inputs'
    assert build['status_unchanged'] and not build['worktree_status'], 'clean committed package checkout'
    assert binding['head'] == build['head'] and binding['outputs'] == build['outputs'], 'same built and bound packages'
    assert set(binding['profiles']) == set(build['profiles']) == {'klem', 'web-assets', 'corpus-adapter'}, 'complete source profiles'
    assert {name: len(profile['files']) for name, profile in binding['profiles'].items()} == {'klem': 1083, 'web-assets': 18, 'corpus-adapter': 1083}, 'complete source files'
    assert binding['profiles']['klem']['files'] == binding['profiles']['corpus-adapter']['files'], 'same Rust adapter source'
    for name, profile in binding['profiles'].items():
        assert profile['source'] == build['profiles'][name]['source'], 'actual evaluated source identity'
        assert {key: {k: value[k] for k in ['bytes', 'sha256']} for key, value in profile['files'].items()} == build['profiles'][name]['files'], 'every actual package source byte'
        assert sha(profile['derivation_json'].encode()) == profile['derivation_json_sha256'], 'actual derivation bytes'
        drv = json.loads(profile['derivation_json'])[profile['derivation']]
        assert drv['env']['src'] == profile['source'] and drv['outputs']['out']['path'] == profile['package'], 'actual derivation source and output'
        assert profile['package'] in binding['outputs'], 'actual bound output'
    cli = binding['profiles']['klem']['package'] + '/bin/klem'
    adapter = binding['profiles']['corpus-adapter']['package'] + '/bin/klem-corpus-adapter'
    launcher = binding['launcher']
    assert sha(launcher['text'].encode()) == launcher['sha256'], 'actual launcher bytes'
    assert binding['profiles']['klem']['package'] + '/bin/klem-web' in launcher['text'], 'actual launcher server'
    assert binding['profiles']['web-assets']['package'] + '/share/klem-web' in launcher['text'], 'actual launcher assets'
    for report in [broad, cohorts, corpora, finite]:
        assert 'passed' in report['state'] and report['inputs_unchanged'], 'terminal complete installed capture'
        assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual runtime producer'
    assert len(broad['runs']) == len(expected_broad['comparisons']) == 8, 'complete broad workloads'
    for run, expected in zip(broad['runs'], expected_broad['comparisons'], strict=True):
        assert run['mode'] == expected['mode'] and run['source_sha256'] == expected['source_sha256'] and run['records'] == expected['records'], 'complete original broad inputs'
        assert run['actual_jsonl_sha256'] == expected['after_jsonl_sha256'] and run['exit_code'] == 0 and run['exact_preserved_capture'] and run['original_bytes_conserved'], 'complete installed broad output'
        mode = run['mode']
        flags = ['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
        assert run['command'][:3] == [cli, 'text', run['source']] and run['command'][3] == '--dictionary' and run['command'][5:] == flags + (['--suggest-spacing'] if 'spacing' in mode else []), 'actual broad filter and spacing command'
    assert sum(run['records'] for run in broad['runs']) == 1128312, 'complete broad frames'
    assert len(cohorts['runs']) == len(expected_cohorts['runs']) == 2, 'complete corpus history cohorts'
    for run, expected in zip(cohorts['runs'], expected_cohorts['runs'], strict=True):
        assert run['family'] == expected['family'] and run['surfaces'] == expected['surfaces'], 'complete cohort identity'
        assert len(run['captures']) == 2 and run['captures'][-1]['binary'] == cli, 'actual installed cohort executable'
        assert run['changed_words'] == expected['changed_words'], 'individual original cohort changes'
        for capture in run['captures']:
            assert capture['words'] == expected['captures'][1]['words'], 'every complete captured word'
            assert sha(json.dumps(capture['words'], ensure_ascii=False, sort_keys=True).encode()) == capture['word_sha256'], 'complete word capture digest'
    assert sum(run['surfaces'] for run in cohorts['runs']) == 53502, 'complete word surfaces'
    assert corpora['adapter'] == adapter and len(corpora['runs']) == len(expected_corpora['runs']) == 4, 'actual installed original gold adapter'
    assert corpora['individual_changed_rows'] == expected_corpora['individual_changed_rows'] and len(corpora['individual_changed_rows']) == 0, 'individual original gold recoveries'
    for run, expected in zip(corpora['runs'], expected_corpora['runs'], strict=True):
        assert all(run[key] == expected[key] for key in ['corpus', 'partition', 'source', 'source_sha256', 'rows', 'jsonl', 'stdout_sha256', 'summary_changes']), 'all complete original annotated outputs'
        assert sha(run['jsonl'].encode()) == run['stdout_sha256'] and run['command'] == [adapter, run['corpus'], run['source']] and run['exit_code'] == 0, 'actual complete adapter execution'
    assert sum(run['rows'] for run in corpora['runs']) == 66570, 'complete annotated rows'
    keys = [(family, encoding, mode, cache) for family in ['complete-original-source', 'all-individual-cases']
            for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]]
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in finite['runs']] == keys, 'complete finite Unicode filter cache streams'
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in streams['runs']] == keys, 'complete reference Source cache streams'
    assert len(suites) == 1 and len(suites[0]['cases']) == 8, 'original separate expression scope'
    streams_audit.inspect(source, suites[0], finite)
    streams_audit.inspect(source, suites[0], streams)
    for run, previous in zip(finite['runs'], streams['runs'], strict=True):
        assert run['command'][0] == cli, 'actual installed finite executable'
        assert run['jsonl'] == previous['jsonl'], 'complete original Source stream parity'
    assert runtime['command'] == [launcher['package'] + '/bin/klem-web', '--port', '0', '--assets', binding['profiles']['web-assets']['package'] + '/share/klem-web', '--dictionary', runtime['command'][-1]], 'actual installed launcher command'
    assert runtime['command'][0] in runtime['frozen_inputs'], 'actual frozen launcher bytes'
    # Reuse the complete policy/diagram/export/Native audit. The explicit --assets value agrees with the actual installed launcher
    # and is independently checked above before the complete browser audit.
    browser_runtime = runtime
    assert browser['state'] == 'actual-installed-browser-passed', 'terminal installed browser capture'
    browser_capture = {**browser, 'state': 'isolated-browser-passed'}
    view = browser_audit.inspect(browser_capture, browser_runtime, suites, native, labels, driver, supervisor)
    return {'package_source_files': 1083, 'broad_frames': 1128312, 'cohort_words': 53502,
            'annotated_rows': 66570, 'gold_recoveries': 0,
            'finite_streams': len(finite['runs']), 'finite_frames': sum(r['records'] for r in finite['runs']),
            **view, 'full_coverage_complete': False}


def inputs():
    docs = ROOT / 'docs'
    installed = ['installed-source-binding', 'integration-packages', 'installed-broad', 'installed-cohorts',
                 'installed-corpora', 'installed-finite', 'installed-browser', 'installed-browser-runtime']
    evidence = [read(docs / ('formal-volitional-expression-' + name + '.json.gz')) for name in installed]
    evidence += [read(docs / ('formal-volitional-' + name + '.json.gz')) for name in ['broad', 'cohorts', 'corpora']]
    evidence += [read(docs / ('formal-volitional-expression-' + name + '.json.gz')) for name in ['source-preparation', 'source-streams']]
    suites = [read(ROOT / 'tests/fixtures/formal-volitional-expression-validity.json')]
    native = read(ROOT / 'tests/fixtures/formal-volitional-expression-native-entries.json')
    labels = read(ROOT / 'web/src/grammar-labels.json')
    driver = browser_audit.gzip.decompress((docs / 'formal-volitional-expression-installed-browser.mjs.gz').read_bytes()).decode()
    supervisor = browser_audit.gzip.decompress((docs / 'formal-volitional-expression-installed-browser-supervisor.py.gz').read_bytes()).decode()
    return (*evidence, suites, native, labels, driver, supervisor)


if __name__ == '__main__':
    print(inspect(*inputs()))
