"""Verify actual main/package replays and fresh packaged browser evidence."""
import argparse
import json
import math

from hada_remaining_scoped_runtime import inspect_cases
from literary_ri_prefinal_audit import BASE, ROOT, producer, read, sha
from literary_ri_prefinal_preservation import digest


def verify_cli(report):
    producer(report)
    assert report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged']
    assert report['contextual_verdict'] == 'unjudged' and report['independent_review'] == 'pending'
    assert report['cli_sha256'] == report['frozen_inputs'][report['cli']]
    expected = read(BASE / 'literary-ri-prefinal-prototype-cli.json.gz')
    supplement = read(BASE / 'literary-ri-prefinal-supplemental-b.json')
    probes = {(r['case'], r['encoding'], r['mode']): r for r in expected['probes'] + supplement['probes']}
    assert len(report['runs']) == 6 and len(report['probes']) == len(probes) == 168
    for run, original in zip(report['runs'], expected['streams'], strict=True):
        assert (run['encoding'], run['mode']) == (original['encoding'], original['mode'])
        assert run['sha256'] == original['sha256'] and run['records'] == 275
        assert run['exit_code'] == 0 and run['exact_prototype_output']
    seen = set()
    conditional = {c['case_id'] for c in read(BASE / 'literary-ri-prefinal-mode-scope-review.json')['cases']}
    cases = {c['id']: c for c in read(ROOT / 'tests/fixtures/literary-ri-prefinal-policy-validity.json')['cases']}
    from literary_ri_prefinal_audit import match
    for run in report['probes']:
        key = (run['case'], run['encoding'], run['mode'])
        assert key not in seen
        seen.add(key)
        original = probes[key]
        assert run['sha256'] == sha(original['json'].encode())
        assert run['exit_code'] == 0 and run['exact_prototype_output']
        paths = json.loads(original['json'])['analyses']
        expected_observations = []
        for judgment in cases[run['case']]['judgments']:
            verdict = 'unjudged' if run['case'] in conditional and run['mode'] == 'raw' else judgment['verdict']
            expected_observations.append({'judgment': judgment['id'], 'mode_verdict': verdict,
                                         'matching_paths': [p for p in paths if match(p, judgment)]})
        assert run['observations'] == expected_observations
    assert seen == probes.keys()
    broad = read(BASE / 'literary-ri-prefinal-prototype-broad.json.gz')
    assert len(report['broad']) == 8
    for run, original in zip(report['broad'], broad['comparisons'], strict=True):
        assert all(run[k] == original[k] for k in ['source', 'source_sha256', 'mode', 'records'])
        assert run['sha256'] == original['after_jsonl_sha256']
        assert run['exit_code'] == 0 and run['exact_prototype_output'] and run['original_bytes_conserved']
    corpora = read(BASE / 'literary-ri-prefinal-prototype-corpora.json.gz')
    assert report['corpora'] == {'unique_surfaces': 32096, 'annotated_rows': 66570,
        'word_analyses_sha256': digest(corpora['after_words']), 'exact_prototype_word_analyses': True}
    return {'source_frames': 1650, 'word_probes': 168, 'broad_frames': 1128312, 'corpus_words': 32096}


def verify_adapter(report):
    producer(report)
    assert report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged']
    assert report['adapter_sha256'] == report['frozen_inputs'][report['adapter']]
    original_path = BASE / 'literary-ri-prefinal-prototype-adapter.json.gz'
    assert report['original_capture_sha256'] == sha(original_path.read_bytes())
    original = read(original_path)
    assert len(report['runs']) == len(original['runs']) == 4
    for run, previous in zip(report['runs'], original['runs'], strict=True):
        assert all(run[k] == previous[k] for k in ['corpus', 'partition', 'source', 'source_sha256'])
        expected = next(s for s in previous['streams'] if s['mode'] == 'after')
        assert run['sha256'] == expected['sha256'] and run['rows'] == expected['rows']
        assert run['exit_code'] == 0 and run['exact_prototype_output']
    assert sum(r['rows'] for r in report['runs']) == 66570
    return 66570


def verify_package(package, cli, browser, hada):
    assert package['state'] == 'passed' and package['exit_code'] == 0 and package['snapshot_unchanged']
    # Bind the new typed model and catalog as well as the unchanged breakdown.ts.
    # An older six-diagram capture alone cannot establish current package behavior.
    from literary_ri_prefinal_sources import package_source_texts
    sources = package_source_texts(package)
    for path, value in package['snapshot']['files'].items():
        assert sha(sources[path].encode()) == value['sha256'], path
    assert {'src/engine.rs', 'web/src/model.ts', 'web/src/breakdown.ts',
            'web/src/grammar-labels.json'} <= package['snapshot']['files'].keys()
    output = next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    assert cli['cli'] == output + '/bin/klem'
    counts = verify_cli(cli)
    main = read(BASE / 'literary-ri-prefinal-main-browser.json')
    assert browser['producer_sha256'] == sha((ROOT / 'web/tests/literary-ri-prefinal.mjs').read_bytes())
    assert browser['cli_sha256'] == hada['cli_sha256'] == cli['cli_sha256']
    assert browser['catalog_sha256'] == sha(sources['web/src/grammar-labels.json'].encode())
    assert api_semantics(browser['responses']) == api_semantics(main['responses'])
    for key in ['exports', 'diagrams', 'native', 'opened', 'modeJudgments', 'errors']:
        assert browser[key] == main[key], key
    assert len(browser['diagrams']) == 60 and len(browser['exports']) == 6
    assert len(browser['native']) == 182 and len(browser['opened']) == 2
    assert hada['producer_sha256'] == sha((ROOT / 'web/tests/hada-remaining-scoped.mjs').read_bytes())
    assert hada['frontend_sha256'] == sha(sources['web/src/breakdown.ts'].encode())
    assert inspect_cases(hada) == 6
    before = read(BASE / 'literary-ri-prefinal-main-hada-scoped-browser.json')
    assert scoped_semantics(hada['checks']) == scoped_semantics(before['checks'])
    assert hada['errors'] == before['errors'] == []
    return counts | {'diagrams': 60, 'native_entries': 182, 'fresh_nested_hada_diagrams': 6}


def api_semantics(runs):
    """Only current-call elapsed time varies across debug and release captures."""
    result = []
    for run in runs:
        result.append(dict(run, after=without_elapsed(run['after'])))
    return result


def without_elapsed(response):
    response = dict(response)
    elapsed = response.pop('elapsed_ms')
    assert type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0
    return response


def scoped_semantics(checks):
    return [dict(check, response=without_elapsed(check['response'])) for check in checks]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-only', action='store_true')
    args = parser.parse_args()
    result = {'main_cli': verify_cli(read(BASE / 'literary-ri-prefinal-main-cli-replay.json.gz')),
              'actual_main_adapter_rows': verify_adapter(read(BASE / 'literary-ri-prefinal-main-adapter-replay.json.gz'))}
    if not args.main_only:
        result['package'] = verify_package(
            read(BASE / 'literary-ri-prefinal-package-nix.json'),
            read(BASE / 'literary-ri-prefinal-packaged-cli-replay.json.gz'),
            read(BASE / 'literary-ri-prefinal-packaged-browser.json'),
            read(BASE / 'literary-ri-prefinal-packaged-hada-scoped-browser.json'))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
