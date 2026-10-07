"""Verify packaged CLI, browser, Native entries and immutable Nix build evidence."""
import argparse
import gzip
import json
import re

from copula_expectation_audit import digest, runtime
from copula_expectation_production import ROOT, read, sha

PACKAGE = 'docs/copula-expectation-packaged-checks.json'
PRODUCTION = 'docs/copula-expectation-packaged-production.json'


def verify_build(receipt, archive, log, sources):
    assert receipt['state'] == 'passed' and receipt['exit_code'] == 0
    assert receipt['snapshot_unchanged']
    assert digest(log) == receipt['log_sha256']
    batches = re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;', log)
    assert (sum(int(p) for p, i in batches), sum(int(i) for p, i in batches), len(batches)) == (983, 1, 209)
    assert 'FAILED' not in log and 'error:' not in log
    snapshot = receipt['snapshot']['files']
    assert len(archive['files']) == 38
    assert sources['schema_version'] == 1 and sources['package'] in receipt['outputs']
    assert digest(sources['derivation_json_text']) == sources['derivation_json_sha256']
    assert json.loads(sources['derivation_json_text']) == sources['derivation_json']
    assert set(sources['derivation_json']) == {sources['derivation']}
    derivation = sources['derivation_json'][sources['derivation']]
    assert derivation['env']['src'] == sources['source']
    assert derivation['outputs']['out']['path'] == sources['package']
    assert set(sources['files']) == set(archive['files'])
    for path, source in archive['files'].items():
        assert digest(source['text']) == source['sha256']
        assert sources['files'][path]['sha256'] == source['sha256'], path
        assert sources['files'][path]['bytes'] == len(source['text'].encode()), path
        if path in snapshot:
            assert snapshot[path]['sha256'] == source['sha256'], path


def verify_streams(report, source, broad, corpus, cli):
    assert report['state'] == 'passed' and report['inputs_unchanged'] and report['prototype_parity']
    assert digest(report['producer']['text']) == report['producer']['sha256']
    expected = {(f, enc, mode): run for f, family in source['reports'].items()
                for enc, modes in family['runs'].items() for mode, run in modes.items()}
    assert len(report['source_runs']) == len(expected) == 12
    assert {(r['family'], r['encoding'], r['mode']) for r in report['source_runs']} == set(expected)
    for run in report['source_runs']:
        old = expected[run['family'], run['encoding'], run['mode']]
        assert run['exit_code'] == 0 and run['command'] == [cli, *old['command'][1:]]
        assert run['sha256'] == run['expected_sha256'] == old['after_sha256']
        assert run['records'] == old['records'] and run['input_sha256'] == old['input_sha256']
    assert sum(r['records'] for r in report['source_runs']) == 309660
    assert len(report['broad_runs']) == len(broad['comparisons']) == 8
    for run, old in zip(report['broad_runs'], broad['comparisons'], strict=True):
        assert all(run[k] == old[k] for k in ['source', 'source_sha256', 'mode', 'records'])
        assert run['exit_code'] == 0 and run['command'] == [cli, *old['commands'][1][1:]]
        assert run['sha256'] == run['expected_sha256'] == old['after_jsonl_sha256']
    assert sum(r['records'] for r in report['broad_runs']) == 1128312
    # The package ships no evaluator. Equality of complete original WordAnalyses
    # transfers the already verified evaluator results; retain that distinction.
    assert 'corpus_runs' not in report
    assert report['corpus_validation'] == {
        'method': 'Exact packaged CLI WordAnalysis equality for every original gold surface, tied to the unchanged verified evaluator results; no packaged evaluator executable is claimed.',
        'verified_gold_rows': 66570,
    }
    assert len(report['corpus_reference_runs']) == len(corpus['corpora']) == 4
    rows = 0
    for run, old in zip(report['corpus_reference_runs'], corpus['corpora'], strict=True):
        assert all(run[k] == old[k] for k in ['corpus', 'partition', 'source', 'source_sha256', 'report_lines'])
        assert old['changed_gold_outcomes'] == [] and old['changed_summary_fields'] == {}
        assert old['before_jsonl'] == old['after_jsonl']
        assert run['reference_evaluator_jsonl_sha256'] == digest(old['after_jsonl'])
        lines = old['after_jsonl'].splitlines()
        gold = [json.loads(line) for line in lines[1:]]
        assert len(gold) + 1 == old['report_lines']
        assert all(row['surface'] in corpus['after_words'] for row in gold)
        mean = sum(len(corpus['after_words'][row['surface']]['analyses']) for row in gold) / len(gold)
        assert mean == json.loads(lines[0])['mean_candidates']
        rows += len(gold)
    assert rows == corpus['converted_rows'] == 66570
    assert report['corpus_words'] == len(corpus['after_words']) == 32096
    assert report['corpus_word_sha256'] == digest(json.dumps(corpus['after_words'], ensure_ascii=False, sort_keys=True))


def inspect():
    package = read(PACKAGE)
    receipt = read('docs/copula-expectation-package-nix.json')
    archive = read('docs/copula-expectation-main-sources.json.gz')
    sources = read('docs/copula-expectation-package-sources.json')
    log = gzip.decompress((ROOT / 'docs/copula-expectation-package-nix.log.gz').read_bytes()).decode()
    verify_build(receipt, archive, log, sources)
    assert package['state'] == 'passed' and package['checklist'] == 'COV-020s'
    assert set(receipt['outputs']) == set(package['nix_outputs'].values())
    assert set(package['capture_sha256']) == {
        'docs/copula-expectation-package-nix.json', PRODUCTION,
        'docs/copula-expectation-packaged-browser.json.gz',
        'docs/copula-expectation-packaged-native-closure.json.gz',
    }
    for path, value in package['capture_sha256'].items():
        assert sha(ROOT / path) == value
    report = read(PRODUCTION)
    for path, value in report['frozen_inputs'].items():
        if path in sources['files']:
            assert sources['files'][path]['sha256'] == value
        else:
            assert receipt['snapshot']['files'][path]['sha256'] == value
    source, broad, corpus = [read(f'docs/copula-expectation-{n}.json.gz')
                             for n in ['source-streams', 'broad', 'corpora']]
    cli = package['nix_outputs']['klem'] + '/bin/klem'
    assert report['binaries'][cli] == package['cli_sha256']
    dictionaries = [value for path, value in report['binaries'].items()
                    if path.endswith('/data/dictionaries/krdict/krdict.db')]
    assert dictionaries == [package['dictionary_sha256']]
    verify_streams(report, source, broad, corpus, cli)
    assert len(package['comparisons']) == 8
    for check, old, actual in zip(package['comparisons'], broad['comparisons'], report['broad_runs'], strict=True):
        assert check == {**old, 'commands': [old['commands'][0], actual['command']],
                         'exit_codes': [0, actual['exit_code']]}
    runtime(report, browser_path='docs/copula-expectation-packaged-browser.json.gz',
            entries_path='docs/copula-expectation-packaged-native-closure.json.gz')
    for path in ['docs/copula-expectation-packaged-browser.json.gz',
                 'docs/copula-expectation-packaged-native-closure.json.gz']:
        capture = read(path)
        assert digest(capture['producer']['text']) == capture['producer']['sha256']
        assert capture['cli_sha256'] == package['cli_sha256']
    return {'source_frames': 309660, 'gold_rows': 66570, 'broad_frames': 1128312,
            'diagrams': 42, 'native_entries': 17}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified actual packaged release:', inspect())
