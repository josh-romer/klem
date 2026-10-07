"""Replay retained source streams, exact parents and actual browser evidence."""
import copy
import hashlib
import json
import unicodedata
from collections import Counter
from lexical_nada_audit import ROOT, read, sha


def command(path):
    return 'ending.friendly_command.n' in path['rules']


def inspect():
    p = read(ROOT / 'docs/friendly-command-preflight.json.gz')
    f = read(ROOT / 'tests/fixtures/friendly-command-sources.json')
    d = read(ROOT / 'docs/friendly-command-diagnostics.json.gz')
    assert d['schema_version'] == 1 and d['checklist'] == 'COV-017bx'
    assert d['source_sha256'] == sha(ROOT / 'docs/friendly-command-preflight.json.gz')
    assert d['fixture_sha256'] == sha(ROOT / 'tests/fixtures/friendly-command-sources.json')
    assert d['dictionary_sha256'] == p['dictionary_sha256']
    assert d['cli_sha256']['before'] == p['before_cli_sha256']
    assert hashlib.sha256(d['producer']['text'].encode()).hexdigest() == d['producer']['sha256']
    assert set(d['runs']) == {'raw', 'headword', 'compatible'}
    total = Counter()
    for mode, captures in d['runs'].items():
        assert set(captures) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        semantic = {}
        raw_reference = None
        for key, pair in captures.items():
            assert set(pair) == {'before', 'after'}
            frames = {}
            for stage, run in pair.items():
                assert run['exit_code'] == 0
                assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
                rows = [json.loads(line) for line in run['jsonl'].splitlines()]
                assert ''.join(r['surface'] for r in rows) == unicodedata.normalize(key.split('-')[0], p['input'])
                offset = 0
                for row in rows:
                    assert row['span'] == dict(start=offset, end=offset + len(row['surface'].encode()))
                    offset = row['span']['end']
                value = [(r.get('analysis'), r.get('dictionary')) for r in rows]
                if stage in semantic:
                    assert value == semantic[stage], (mode, key, stage)
                else:
                    semantic[stage] = value
                frames[stage] = rows
            before, after = frames['before'], frames['after']
            assert len(before) == len(after)
            if key == 'NFC-cached':
                assert pair['before']['jsonl'] == p['runs'][mode]['jsonl']
            raw_reference = p['before_analyses']
            for record_index, (old, new) in enumerate(zip(before, after)):
                assert {k: v for k, v in old.items() if k not in {'analysis', 'dictionary'}} == {k: v for k, v in new.items() if k not in {'analysis', 'dictionary'}}
                if old['kind'] != 'word':
                    assert old == new
                    continue
                assert old['analysis']['normalized'] == new['analysis']['normalized']
                word = old['analysis']['normalized']
                old_paths, new_paths = old['analysis']['analyses'], new['analysis']['analyses']
                retained = [a for a in new_paths if a in old_paths]
                assert retained == old_paths, (mode, key, record_index, word)
                for a in new_paths:
                    if a in old_paths:
                        continue
                    assert command(a), (mode, key, record_index, word, a)
                    assert a['lemmas'][-1]['kind'] in {'predicate', 'auxiliary'}
                    assert a['lemmas'][-1]['text'].endswith('오다')
                    parent = copy.deepcopy(a)
                    parent['rules'].remove('ending.friendly_command.n')
                    ending = next(m for m in reversed(parent['morphemes']) if m['kind'] == 'ending')
                    assert ending['form'] == 'ㄴ'
                    ending['form'] = '은'
                    assert parent in raw_reference[word]['analyses'], (word, a)
                    total[mode] += 1
                assert {k: v for k, v in old['dictionary'].items() if k != 'readings'} == {k: v for k, v in new['dictionary'].items() if k != 'readings'}
                for i, a in enumerate(old_paths):
                    j = new_paths.index(a)
                    assert old['dictionary']['readings'][i] == new['dictionary']['readings'][j]
    browser = read(ROOT / 'docs/friendly-command-browser.json.gz')
    assert browser['checklist'] == 'COV-017bx' and browser['schema_version'] == 1
    assert browser['cli_sha256'] == d['cli_sha256']['after']
    assert browser['dictionary_sha256'] == d['dictionary_sha256']
    assert browser['fixture_sha256'] == d['fixture_sha256']
    assert browser['producer_sha256'] == sha(ROOT / 'web/tests/friendly-command.mjs')
    assert browser['browser_errors'] == []
    assert len(browser['responses']) == 2 and len(browser['checks']) == 6
    assert len(browser['diagrams']) == 12 and len(browser['native']) == 60
    for check in browser['checks']:
        assert check['cli_records'] == check['exported_records']
    for diagram in browser['diagrams']:
        friendly = diagram['word'] not in {'못난이', '흰둥이'}
        assert command(diagram['analysis']) == friendly
        assert diagram['source'] == (73877 if friendly else 78634)
        assert diagram['label'] == ('Friendly command (come)' if friendly else 'Noun modifier')
        assert str(diagram['source']) in diagram['title']
        assert str(78634 if friendly else 73877) not in diagram['title']
        api = next(r['response'] for r in browser['responses'] if r['encoding'] == diagram['encoding'])
        token_index = next(i for i, r in enumerate(api['records']) if r.get('analysis') and r['analysis']['normalized'] == diagram['word'])
        token = api['records'][token_index]
        assert token['analysis']['analyses'][diagram['selected']] == diagram['analysis']
        assert api['breakdowns'][token_index][diagram['selected']] == diagram['order']
        assert token['analysis']['analyses'][diagram['whole_selected']]['unchanged'] is True
        expected = [{'lemma': i} for i in range(len(diagram['analysis']['lemmas']))] + [{'morpheme': i} for i in range(len(diagram['analysis']['morphemes']))]
        assert sorted(map(json.dumps, diagram['order'])) == sorted(map(json.dumps, expected))
    assert {row['id']: row['response']['entry'] for row in browser['native']} == f['complete_native_entries']
    api = read(ROOT / 'docs/friendly-command-api.json.gz')
    assert api['schema_version'] == 1 and api['checklist'] == 'COV-017bx'
    assert api['diagnostics_sha256'] == sha(ROOT / 'docs/friendly-command-diagnostics.json.gz')
    assert api['cli_sha256'] == d['cli_sha256']
    assert hashlib.sha256(api['producer']['text'].encode()).hexdigest() == api['producer']['sha256']
    assert set(api['runs']) == {'NFC', 'NFD'}
    api_additions = 0
    for encoding, stages in api['runs'].items():
        assert set(stages) == {'before', 'after'}
        actual_stages = {}
        for stage, batches in stages.items():
            reference = [json.loads(line) for line in d['runs']['raw'][encoding + '-cached'][stage]['jsonl'].splitlines()]
            begin = 0
            actual_stages[stage] = []
            for batch in batches:
                left, right = batch['source_record_range']
                assert left == begin and right > left
                start = reference[left]['span']['start']
                assert batch['source_span'] == dict(start=start, end=reference[right - 1]['span']['end'])
                text = ''.join(r['surface'] for r in reference[left:right])
                assert batch['request'] == dict(text=text) and len(text.encode()) <= 7000
                expected = copy.deepcopy(reference[left:right])
                for row in expected:
                    row['span'] = {k: v - start for k, v in row['span'].items()}
                assert batch['response']['records'] == expected
                assert len(batch['response']['breakdowns']) == len(expected)
                actual_stages[stage].extend(zip(expected, batch['response']['breakdowns']))
                begin = right
            assert begin == len(reference) == 21198
        for (old, old_orders), (new, new_orders) in zip(actual_stages['before'], actual_stages['after']):
            if old['kind'] != 'word':
                continue
            old_paths, new_paths = old['analysis']['analyses'], new['analysis']['analyses']
            for i, path in enumerate(old_paths):
                assert new_orders[new_paths.index(path)] == old_orders[i]
            for i, path in enumerate(new_paths):
                if path in old_paths:
                    continue
                assert command(path) and new_orders[i] is not None
                parent = copy.deepcopy(path)
                parent['rules'].remove('ending.friendly_command.n')
                next(m for m in reversed(parent['morphemes']) if m['kind'] == 'ending')['form'] = '은'
                assert new_orders[i] == old_orders[old_paths.index(parent)]
                api_additions += 1
    assert api_additions == total['raw'] // 2
    assert all(total[mode] > 0 for mode in d['runs'])
    return dict(total), len(browser['diagrams']), len(browser['native']), api_additions


if __name__ == '__main__':
    print('Verified complete source streams, retained orders/readings/entries, exact raw parents and source-owned browser diagrams:', inspect())
