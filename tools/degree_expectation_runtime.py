"""Replay production source streams, bounded APIs and browser regressions offline."""
import copy
import hashlib
import json

from degree_expectation_audit import ROOT, inspect as sources, read
from degree_expectation_parent import inverse


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def inspect():
    sources()
    capture = read('docs/degree-expectation-main-cohort.json.gz')
    api = read('docs/degree-expectation-main-api.json.gz')
    browser = read('docs/degree-expectation-main-browser.json.gz')
    assert capture['production_worktree'] and api['production_worktree'] and browser['production_worktree']
    assert capture['cli_sha256'] == api['cli_sha256'] == browser['cli_sha256']
    assert api['cohort_sha256'] == sha('docs/degree-expectation-main-cohort.json.gz')
    for report in (capture, api):
        assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    assert browser['producer_sha256'] == sha('web/tests/degree-expectation.mjs')
    added = []
    native = {}
    frames = 0
    for family, name in enumerate(['degree-rimankeum', 'counterfactual-ryeon']):
        prior = read(f'docs/{name}-cohort.json.gz')
        source = read(f'docs/{name}-source-preparation.json.gz')
        native.update(source['complete_native_entries'])
        assert capture['reports'][name]['prior_cohort_sha256'] == sha(f'docs/{name}-cohort.json.gz')
        assert browser['source_sha256'][f'docs/{name}-source-preparation.json.gz'] == sha(f'docs/{name}-source-preparation.json.gz')
        for encoding in ['NFC', 'NFD']:
            for mode, run in capture['reports'][name]['runs'][encoding].items():
                assert run['exit_code'] == 0 and run['sha256'] == hashlib.sha256(run['jsonl'].encode()).hexdigest()
                assert run['jsonl'] == prior['runs'][encoding][mode]['after']['jsonl']
            stages = {}
            for stage in ['before', 'after']:
                raw = prior['runs'][encoding]['raw']['before']['jsonl'] if stage == 'before' else capture['reports'][name]['runs'][encoding]['raw']['jsonl']
                rows = [json.loads(line) for line in raw.splitlines()]
                records, orders, cursor = [], [], 0
                for batch in api['runs'][name][encoding][stage]:
                    start, end = batch['source_record_range']
                    assert start == cursor and start < end <= len(rows)
                    offset = rows[start]['span']['start']
                    assert batch['request']['text'] == ''.join(r['surface'] for r in rows[start:end])
                    assert len(batch['request']['text'].encode()) <= 7000
                    expected = copy.deepcopy(rows[start:end])
                    for row in expected:
                        row['span'] = {key: value - offset for key, value in row['span'].items()}
                    response = batch['response']
                    assert response['records'] == expected
                    assert len(response['breakdowns']) == len(expected)
                    records.extend(response['records'])
                    orders.extend(response['breakdowns'])
                    cursor = end
                assert cursor == len(rows)
                frames += len(rows)
                stages[stage] = (records, orders)
            for i, (before, after) in enumerate(zip(stages['before'][0], stages['after'][0], strict=True)):
                if after['kind'] != 'word':
                    continue
                old, new = before['analysis']['analyses'], after['analysis']['analyses']
                assert [p for p in new if p in old] == old
                assert len(stages['after'][1][i]) == len(new)
                for j, path in enumerate(new):
                    order = stages['after'][1][i][j]
                    if path in old:
                        assert order == stages['before'][1][i][old.index(path)]
                        continue
                    word = after['analysis']['normalized']
                    companion, parent, _ = inverse(word, path)
                    oldapi = api['companion_responses'][companion]
                    token = next(k for k, r in enumerate(oldapi['records']) if (r.get('analysis') or {}).get('normalized') == companion)
                    k = oldapi['records'][token]['analysis']['analyses'].index(parent)
                    assert order is not None and order == oldapi['breakdowns'][token][k]
                    added.append(dict(family=name, encoding=encoding, record=i, surface=word, analysis=path,
                                      order=order, companion=companion, parent=parent, parent_index=k,
                                      contextual_verdict='unjudged'))
    assert api['added_orders'] == added and len(added) == 346
    assert frames == 206440
    assert len(browser['records']) == 12 and len(browser['diagrams']) == 54 and browser['errors'] == []
    for diagram in browser['diagrams']:
        response = next(r['response'] for r in browser['responses'] if r['family'] == diagram['family'] and r['encoding'] == diagram['encoding'])
        token = next(i for i, r in enumerate(response['records']) if (r.get('analysis') or {}).get('normalized') == diagram['word'])
        assert response['records'][token]['analysis']['analyses'][diagram['index']] == diagram['analysis']
        assert response['breakdowns'][token][diagram['index']] == diagram['order']
        assert diagram['label'] == ('To such a degree' if diagram['family'] == 0 else 'Counterfactual expectation')
    assert {r['id']: r['response']['entry'] for r in browser['native']} == native and len(native) == 67
    return frames, len(added), len(browser['diagrams']), len(native)


if __name__ == '__main__':
    print('Verified production API frames, exact added orders, browser diagrams and native entries:', inspect())
