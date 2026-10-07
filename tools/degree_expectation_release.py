"""Verify packaged source/API/browser outputs and complete broad/corpus parity."""
import argparse
import base64
import hashlib
import math
import re
from pathlib import Path

from degree_expectation_audit import ROOT, read

REPORT = 'docs/degree-expectation-packaged-checks.json.gz'


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def semantic(response):
    elapsed = response['elapsed_ms']
    assert isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed >= 0
    return {k: v for k, v in response.items() if k != 'elapsed_ms'}


def verify_release_sources(snapshot, package, sources):
    assert sources['schema_version'] == 1
    assert sources['package'] == package
    paths = ['src/engine.rs', 'src/grammar.rs', 'src/dictionary/attachment.rs',
             'tests/degree_rimankeum.rs', 'tests/counterfactual_ryeon.rs',
             'tests/fixtures/validity.json', 'tests/validity.rs', 'web/src/grammar-labels.json']
    assert set(sources['files']) == set(paths)
    for path in paths:
        source = sources['files'][path]
        assert hashlib.sha256(source['text'].encode()).hexdigest() == source['sha256']
        assert snapshot[path] == source['sha256'], path


def inspect(report):
    assert report['schema_version'] == 1
    assert report['checklist'] == ['COV-017by', 'COV-017bz']
    receipt = report['nix_receipt']
    assert receipt['state'] == 'passed' and receipt['exit_code'] == 0 and receipt['snapshot_unchanged']
    # The historical package keeps its exact source texts as later rules evolve.
    verify_release_sources(receipt['snapshot'], report['nix_outputs']['klem'],
                           read('docs/degree-expectation-release-sources.json.gz'))
    log = report['nix_log']
    assert hashlib.sha256(log.encode()).hexdigest() == receipt['log_sha256']
    assert 'FAILED' not in log and 'error:' not in log
    counts = re.findall(r'klem> test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;', log)
    assert (sum(int(p) for p, i in counts), sum(int(i) for p, i in counts), len(counts)) == (976, 1, 208)
    outputs = report['nix_outputs']
    assert set(outputs) == {'klem', 'web-assets'}
    assert set(outputs.values()) == set(receipt['outputs'])
    assert all(p.startswith('/nix/store/') and p in log.splitlines() for p in outputs.values())
    assert report['cli_sha256'] != read('docs/degree-expectation-main-cohort.json.gz')['cli_sha256']
    for field, path in [('cohort', 'docs/degree-expectation-main-cohort.json.gz'),
                        ('api', 'docs/degree-expectation-main-api.json.gz'),
                        ('browser', 'docs/degree-expectation-main-browser.json.gz')]:
        assert report['main_sha256'][field] == sha(path)
        actual, debug = report[field], read(path)
        assert actual['cli_sha256'] == report['cli_sha256']
        if field == 'cohort':
            assert actual['engine_sha256'] == debug['engine_sha256']
            assert actual['dictionary_sha256'] == debug['dictionary_sha256']
            assert actual['reports'].keys() == debug['reports'].keys()
            for family, data in actual['reports'].items():
                prior = debug['reports'][family]
                assert data['prior_cohort_sha256'] == prior['prior_cohort_sha256']
                assert data['runs'].keys() == prior['runs'].keys()
                for encoding, runs in data['runs'].items():
                    assert runs.keys() == prior['runs'][encoding].keys()
                    for mode, run in runs.items():
                        original = prior['runs'][encoding][mode]
                        assert run['exit_code'] == 0 and run['jsonl'] == original['jsonl']
                        assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256'] == original['sha256']
                        assert run['command'][0] == outputs['klem'] + '/bin/klem'
                        assert run['command'][1:] == original['command'][1:]
                        assert run['input_sha256'] == original['input_sha256']
        elif field == 'api':
            assert actual['cohort_sha256'] == report['capture_sha256']['cohort']
            assert actual['added_orders'] == debug['added_orders']
            assert len(actual['added_orders']) == 346
            assert actual['runs'].keys() == debug['runs'].keys()
            frames = 0
            for family, encodings in actual['runs'].items():
                assert encodings.keys() == debug['runs'][family].keys()
                for encoding, stages in encodings.items():
                    assert stages.keys() == {'before', 'after'}
                    for stage, batches in stages.items():
                        old = debug['runs'][family][encoding][stage]
                        assert len(batches) == len(old)
                        for batch, original in zip(batches, old, strict=True):
                            assert {k: v for k, v in batch.items() if k != 'response'} == {k: v for k, v in original.items() if k != 'response'}
                            assert len(batch['request']['text'].encode()) <= 7000
                            assert semantic(batch['response']) == semantic(original['response'])
                            frames += len(batch['response']['records'])
            assert frames == 206440
            assert actual['companion_responses'].keys() == debug['companion_responses'].keys()
            for word, response in actual['companion_responses'].items():
                assert semantic(response) == semantic(debug['companion_responses'][word])
        else:
            for key in ['schema_version', 'source_sha256', 'producer_sha256', 'records', 'diagrams', 'native', 'errors']:
                assert actual[key] == debug[key], key
            assert len(actual['diagrams']) == 54 and len(actual['native']) == 67 and not actual['errors']
            assert len(actual['responses']) == len(debug['responses']) == 4
            for response, original in zip(actual['responses'], debug['responses'], strict=True):
                assert {k: v for k, v in response.items() if k != 'response'} == {k: v for k, v in original.items() if k != 'response'}
                assert semantic(response['response']) == semantic(original['response'])
    for name in ['cohort', 'api', 'browser', 'streams']:
        capture_path = ROOT / ('docs/degree-expectation-packaged-' + name + '.json.gz')
        raw = capture_path.read_bytes()
        if name == 'browser':
            raw = __import__('gzip').decompress(raw)
        assert hashlib.sha256(raw).hexdigest() == report['capture_sha256'][name]
    streams = report['streams']
    assert streams['cli_sha256'] == report['cli_sha256']
    assert streams['dictionary_sha256'] == report['cohort']['dictionary_sha256']
    broad = read('docs/degree-expectation-main-observations-capture.json.gz')
    corpus = read('docs/degree-expectation-main-corpora.json.gz')
    assert report['comparisons'] == broad['comparisons']
    assert report['before_cli_sha256'] == broad['before_cli_sha256']
    assert report['dictionary_sha256'] == broad['dictionary_sha256']
    assert streams['main_broad_sha256'] == sha('docs/degree-expectation-main-observations-capture.json.gz')
    assert streams['main_corpus_sha256'] == sha('docs/degree-expectation-main-corpora.json.gz')
    assert len(streams['streams']) == len(broad['comparisons']) == 8
    dictionary = report['cohort']['reports']['degree-rimankeum']['runs']['NFC']['raw']['command'][4]
    assert dictionary.endswith('/data/dictionaries/krdict/krdict.db')
    for actual, debug in zip(streams['streams'], broad['comparisons'], strict=True):
        for key in ['mode', 'source', 'source_sha256', 'records']:
            assert actual[key] == debug[key]
        assert actual['exit_code'] == 0 and actual['sha256'] == debug['after_jsonl_sha256']
        mode = actual['mode']
        flags = ['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
        assert actual['command'] == [outputs['klem'] + '/bin/klem', 'text', actual['source'], '--dictionary', dictionary, *flags, *(['--suggest-spacing'] if 'spacing' in mode else [])]
    assert sum(s['records'] for s in streams['streams']) == 1128312
    assert streams['corpus_words'] == corpus['after_words'] and len(streams['corpus_words']) == 32096
    assert hashlib.sha256(__import__('json').dumps(streams['corpus_words'], ensure_ascii=False, sort_keys=True).encode()).hexdigest() == streams['corpus_word_stream_sha256'] == corpus['after_word_stream_sha256']
    assert set(report['screenshots']) == {'0-desktop', '0-mobile', '1-desktop', '1-mobile'}
    for capture in report['screenshots'].values():
        raw = base64.b64decode(capture['base64'], validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw).hexdigest() == capture['sha256']
    for capture in [report['cohort'], report['api'], streams]:
        assert hashlib.sha256(capture['producer']['text'].encode()).hexdigest() == capture['producer']['sha256']
    for producer in [report['producer'], report['finalizer']]:
        assert hashlib.sha256(producer['text'].encode()).hexdigest() == producer['sha256']
    runner = report['runner_receipt']
    assert runner['state'] == 'passed' and runner['exit_code'] == 0
    assert [s['name'] for s in runner['steps']] == ['cohort', 'api', 'browser-runner', 'streams']
    assert all(s['exit_code'] == 0 for s in runner['steps'])
    return 206440, 346, 54, 67, 1128312, 32096


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified packaged API frames, new orders, diagrams, native entries, broad frames and corpus surfaces:', inspect(read(REPORT)))
