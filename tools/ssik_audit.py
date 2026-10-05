"""Verify preserved -씩 source, original candidates and stable structural cases."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import array, entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    data = (ROOT / path).read_bytes()
    return json.loads(gzip.decompress(data) if path.endswith('.gz') else data)


def inspect():
    preflight_path = 'docs/ssik-preflight.json.gz'
    preflight = read(preflight_path)
    fixture = read('tests/fixtures/ssik-sources.json')
    assert fixture['source_sha256'] == hashlib.sha256((ROOT / preflight_path).read_bytes()).hexdigest()
    native = fixture['complete_native_entries']
    assert len(native) == 17
    original = read('tests/fixtures/krdict-ssik-original.json')
    assert {entry(e)['id']: entry(e) for e in array(original['LexicalResource']['Lexicon']['LexicalEntry'])} == native
    adapter = read('tests/fixtures/krdict-ssik-english.json')
    expected = copy.deepcopy(original)
    for raw in array(expected['LexicalResource']['Lexicon']['LexicalEntry']):
        for sense in array(raw.get('Sense')):
            if 'Equivalent' in sense:
                sense['Equivalent'] = [e for e in array(sense['Equivalent']) if any(f['att'] == 'language' and f['val'] == '영어' for f in array(e.get('feat')))]
    assert adapter == expected
    verify_native_lmf(adapter, native)
    for name in ['original', 'english']:
        assert hashlib.sha256((ROOT / ('tests/fixtures/krdict-ssik-' + name + '.json')).read_bytes()).hexdigest() == preflight['source'][name + '_lmf_sha256']
    suffix, adverb = native['krdict:72043'], native['krdict:66460']
    assert (suffix['headword'], suffix['pos']) == ('-씩', '접사')
    assert (adverb['headword'], adverb['pos']) == ('씩', '부사')
    assert [len(s['examples']) for s in suffix['senses']] == [8, 3]
    groups = [{'sense': s['id'], 'example_index': i, 'original_group': g} for s in suffix['senses'] for i, g in enumerate(s['examples'])]
    assert groups == fixture['all_original_groups'] == preflight['all_original_groups']
    assert preflight['preparation_only'] is True
    assert preflight['before_cli_sha256'] == read('docs/hada-remaining-packaged-checks.json.gz')['cli_sha256']
    assert set(preflight['runs']) == {'raw', 'headword', 'compatible'}
    for runs in preflight['runs'].values():
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        for run in runs.values():
            assert run['exit_code'] == 0
            assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
    records = [json.loads(line) for line in preflight['runs']['raw']['NFC-cached']['jsonl'].splitlines()]
    assert fixture['before_analyses'] == {r['analysis']['normalized']: r['analysis'] for r in records if r['kind'] == 'word'}
    assert len(fixture['before_analyses']) == 193
    cases = fixture['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 159
    assert sum(c['judgments'][0]['verdict'] == 'required' for c in cases) == 148
    assert sum(c['judgments'][0]['verdict'] == 'forbidden' for c in cases) == 11
    ledger = read('tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('ssik-')] == cases
    assert ledger['sources']['ssik-krdict'] == suffix['url']
    label = read('web/src/grammar-labels.json')['-씩']
    assert label['kind'] == 'suffix'
    assert label['sources'] == [{'id': 72043, 'headword': '-씩', 'pos': '접사'}]
    assert fixture['contextual_verdict'] == 'unjudged' and fixture['independent_review'] == 'pending'
    return len(native), len(groups), len(cases), len(fixture['before_analyses'])


if __name__ == '__main__':
    print('Verified exact original LMF, separate adapter, suffix/adverb identities, original groups, frozen package streams and stable cases:', inspect())
