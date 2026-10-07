"""Verify immutable omission evidence, individual paths and production parity offline."""
import base64
import copy
import hashlib
import itertools
import json
import math
import re
from copula_expectation_production import ROOT, read, sha
from native_lmf import entry


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def inverse(path):
    result = copy.deepcopy(path)
    assert 'copula.omitted_ending' in result['rules']
    assert len(result['lemmas']) == 2
    assert [l['kind'] for l in result['lemmas']] == ['nominal', 'copula']
    assert result['lemmas'][1]['text'] == '이다'
    result['rules'].remove('copula.omitted_ending')
    result['rules'] = sorted(set(result['rules'] + ['boundary.eu']))
    return result


def frame(before, after):
    assert {k: v for k, v in before.items() if k not in ['analysis', 'dictionary']} == {
        k: v for k, v in after.items() if k not in ['analysis', 'dictionary']}
    if before == after:
        return []
    prior = before['analysis']['analyses']
    current = after['analysis']['analyses']
    assert [p for p in current if p in prior] == prior
    added = [p for p in current if p not in prior]
    assert added
    for path in added:
        inverse(path)
    if before.get('dictionary'):
        old, new = before['dictionary'], after['dictionary']
        assert {k: v for k, v in old.items() if k not in ['readings', 'lemmas']} == {
            k: v for k, v in new.items() if k not in ['readings', 'lemmas']}
        assert [p for p in new['lemmas'] if p in old['lemmas']] == old['lemmas']
        for index, path in enumerate(prior):
            assert old['readings'][index] == new['readings'][current.index(path)]
    return added


def native(report):
    assert report['complete_native_entries'].keys() == report['original_lmf'].keys()
    for ident, raw in report['original_lmf'].items():
        assert entry(raw) == report['complete_native_entries'][ident], ident


def verify_added_source_paths(data):
    assert data['before_analyses'].keys() == data['after_analyses'].keys()
    rows = data['individual_additions']
    assert len({r['id'] for r in rows}) == len(rows)
    total = 0
    for word, before in data['before_analyses'].items():
        after = data['after_analyses'][word]
        assert [p for p in after['analyses'] if p in before['analyses']] == before['analyses']
        for path in after['analyses']:
            if path in before['analyses']:
                continue
            matches = [r for r in rows if r['surface'] == word and r['after'] == path]
            assert len(matches) == 1
            row = matches[0]
            assert row['contextual_verdict'] == 'unjudged'
            parent = inverse(path)
            assert row['explicit_parents']
            for parent_word in row['explicit_parents']:
                assert parent in data['explicit_parents'][parent_word]['analyses']
            total += 1
    assert total == len(rows)
    return total


def sources():
    prep = read('docs/copula-expectation-source-preparation.json.gz')
    suite = read('tests/copula-expectation-validity.json')
    assert len(suite['cases']) == 30
    assert (sum(j['verdict'] == 'required' for c in suite['cases'] for j in c['judgments']),
            sum(j['verdict'] == 'forbidden' for c in suite['cases'] for j in c['judgments'])) == (21, 9)
    assert prep['required'] == 21 and prep['forbidden'] == 9
    assert prep['contextual_verdict'] == 'unjudged' and prep['independent_review'] == 'pending'
    assert len(prep['primary_guidance']) == 2
    assert sha(ROOT / 'tests/copula-expectation-validity.json') == prep['judgment_sha256']
    ledger = read('tests/fixtures/validity.json')
    ledger_cases = {c['id']: c for c in ledger['cases']}
    for case in suite['cases']:
        assert ledger_cases[case['id']] == case
    data = read('docs/copula-expectation-full-source.json.gz')
    assert len(data['before_analyses']) == len(data['after_analyses']) == 7071
    assert len(data['individual_additions']) == 28 and len(data['explicit_parents']) == 27
    assert verify_added_source_paths(data) == 28
    stream = read('docs/copula-expectation-source-streams.json.gz')
    frames = runs = 0
    for family, report in stream['reports'].items():
        assert report['prior_cohort_sha256'] == sha(ROOT / f'docs/{family}-cohort.json.gz')
        assert set(report['runs']) == {'NFC', 'NFD'}
        for encoding, modes in report['runs'].items():
            assert set(modes) == {'raw', 'headword', 'compatible'}
            for mode, run in modes.items():
                assert digest(run['before_jsonl']) == run['before_sha256']
                assert digest(run['after_jsonl']) == run['after_sha256']
                count = changed = 0
                for old, new in itertools.zip_longest(run['before_jsonl'].splitlines(), run['after_jsonl'].splitlines()):
                    assert old is not None and new is not None
                    count += 1
                    if old != new:
                        frame(json.loads(old), json.loads(new))
                        changed += 1
                assert count == run['records'] and changed == len(run['changed_frames'])
                frames += count
                runs += 1
    assert (runs, frames) == (12, 309660)
    return stream


def broad():
    report = read('docs/copula-expectation-broad.json.gz')
    individual = read('docs/copula-expectation-individual.json.gz')
    assert individual['broad_capture_sha256'] == sha(ROOT / 'docs/copula-expectation-broad.json.gz')
    native(individual)
    rows = individual['observations']
    assert len(rows) == len({r['id'] for r in rows}) == 36
    assert len(report['comparisons']) == 8
    assert sum(r['records'] for r in report['comparisons']) == 1128312
    total = 0
    for run in report['comparisons']:
        for changed in run['changed_frames']:
            paths = frame(changed['before'], changed['after'])
            for path in paths:
                matches = [r for r in rows if r['source_sha256'] == run['source_sha256']
                           and r['mode'] == run['mode'] and r['record'] == changed['record'] and r['after'] == path]
                assert len(matches) == 1
                row = matches[0]
                assert row['span'] == changed['after']['span']
                assert row['surface'] == changed['after']['surface']
                assert row['surface'] in row['complete_original_line']
                assert row['span']['end'] - row['span']['start'] == len(row['surface'].encode())
                parent = inverse(path)
                assert row['exact_parent'] == parent and row['explicit_parent_surfaces']
                for word in row['explicit_parent_surfaces']:
                    assert parent in individual['explicit_parents'][word]['analyses']
                index = changed['after']['analysis']['analyses'].index(path)
                assert row['dictionary_assessment'] == changed['after']['dictionary']['readings'][index]
                assert row['contextual_verdict'] == 'unjudged' and row['independent_review'] == 'pending'
                for owner in row['native_owners']:
                    for ident in owner['entry_ids']:
                        assert individual['complete_native_entries'][ident]['headword'] == owner['lemma']['text']
                total += 1
    assert total == 36
    return report


def production(source, broad_report):
    report = read('docs/copula-expectation-main-production.json')
    assert report['state'] == 'passed' and report['prototype_parity'] and report['inputs_unchanged']
    for name in ['source-streams', 'corpora', 'broad']:
        path = f'docs/copula-expectation-{name}.json.gz'
        assert report['frozen_inputs'][path] == sha(ROOT / path)
    expected_source = {(f, enc, mode): run for f, family in source['reports'].items()
                       for enc, modes in family['runs'].items() for mode, run in modes.items()}
    assert len(report['source_runs']) == 12
    assert {(r['family'], r['encoding'], r['mode']) for r in report['source_runs']} == set(expected_source)
    for run in report['source_runs']:
        old = expected_source[run['family'], run['encoding'], run['mode']]
        assert run['exit_code'] == 0
        assert run['sha256'] == run['expected_sha256'] == old['after_sha256']
        assert run['records'] == old['records'] and run['input_sha256'] == old['input_sha256']
    assert len(report['broad_runs']) == 8
    for run, old in zip(report['broad_runs'], broad_report['comparisons'], strict=True):
        assert all(run[k] == old[k] for k in ['source', 'source_sha256', 'mode', 'records'])
        assert run['exit_code'] == 0 and run['sha256'] == run['expected_sha256'] == old['after_jsonl_sha256']
    corpus = read('docs/copula-expectation-corpora.json.gz')
    assert corpus['converted_rows'] == 66570 and len(corpus['after_words']) == 32096
    assert len(report['corpus_runs']) == len(corpus['corpora']) == 4
    for run, old in zip(report['corpus_runs'], corpus['corpora'], strict=True):
        assert old['changed_gold_outcomes'] == [] and old['changed_summary_fields'] == {}
        assert old['before_jsonl'] == old['after_jsonl']
        assert run['sha256'] == run['expected_sha256'] == digest(old['after_jsonl'])
        assert run['records'] == old['report_lines'] and run['exit_code'] == 0
    assert report['corpus_words'] == 32096
    assert report['corpus_word_sha256'] == digest(json.dumps(corpus['after_words'], ensure_ascii=False, sort_keys=True))
    return report


def runtime(production_report, *, browser_path='docs/copula-expectation-main-browser.json.gz',
            entries_path='docs/copula-expectation-main-native-closure.json.gz'):
    current = read(browser_path)
    prototype = read('docs/copula-expectation-prototype-runtime.json.gz')
    assert current['state'] == 'passed' and current['exit_code'] == 0 and current['prototype_parity']
    assert current['owned_preview_stopped']
    assert current['prototype_sha256'] == sha(ROOT / 'docs/copula-expectation-prototype-runtime.json.gz')
    actual, old = current['browser'], prototype['browser']
    assert len(actual['diagrams']) == 42 and len(actual['records']) == 6 and len(actual['native']) == 9
    for key in ['diagrams', 'records', 'native', 'errors']:
        assert actual[key] == old[key]
    assert actual['errors'] == [] and len(actual['responses']) == len(old['responses']) == 2
    for now, previous in zip(actual['responses'], old['responses'], strict=True):
        assert now['encoding'] == previous['encoding'] and now['request'] == previous['request']
        for response in [now['response'], previous['response']]:
            assert isinstance(response['elapsed_ms'], (int, float)) and math.isfinite(response['elapsed_ms'])
        assert {k: v for k, v in now['response'].items() if k != 'elapsed_ms'} == {
            k: v for k, v in previous['response'].items() if k != 'elapsed_ms'}
    assert set(current['screenshots']) == {'desktop', 'mobile'}
    for screenshot in current['screenshots'].values():
        raw = base64.b64decode(screenshot['base64'], validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw).hexdigest() == screenshot['sha256']
    closure = read('docs/copula-expectation-native-closure.json.gz')
    native(closure)
    entries = read(entries_path)
    assert entries['state'] == 'passed' and entries['owned_preview_stopped']
    assert entries['source_sha256'] == sha(ROOT / 'docs/copula-expectation-native-closure.json.gz')
    assert len(entries['entries']) == len(closure['complete_native_entries']) == 17
    assert {e['id']: e['response']['entry'] for e in entries['entries']} == closure['complete_native_entries']
    assert current['web_sha256'] == entries['web_sha256']
    assert current['cli_sha256'] == entries['cli_sha256'] == actual['cli_sha256']
    assert current['cli_sha256'] in production_report['binaries'].values()


def rust():
    receipt = read('docs/copula-expectation-main-rust.json')
    archive = read('docs/copula-expectation-main-sources.json.gz')
    assert receipt['state'] == 'passed' and receipt['exit_code'] == 0 and receipt['inputs_unchanged']
    assert (receipt['passed'], receipt['ignored'], receipt['batches']) == (983, 1, 209)
    assert archive['rust_receipt_sha256'] == sha(ROOT / 'docs/copula-expectation-main-rust.json')
    for path, source in archive['files'].items():
        assert digest(source['text']) == source['sha256']
    for path, value in receipt['frozen_inputs'].items():
        assert archive['files'][path]['sha256'] == value
    log = (ROOT / 'docs/copula-expectation-main-rust.log.gz')
    import gzip
    text = gzip.decompress(log.read_bytes()).decode()
    assert digest(text) == receipt['log_sha256']
    batches = re.findall(r'test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;', text)
    assert (sum(int(p) for p, i in batches), sum(int(i) for p, i in batches), len(batches)) == (983, 1, 209)
    assert 'FAILED' not in text and 'error:' not in text


def verify():
    rust()
    source = sources()
    wide = broad()
    result = production(source, wide)
    runtime(result)
    print('Verified copula source/ledger closure, 28 source and36 novel paths,983 production tests, complete CLI/corpus/broad parity,42 diagrams and17 full Native owners.')


if __name__ == '__main__':
    verify()
