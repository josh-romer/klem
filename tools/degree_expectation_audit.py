"""Verify complete source closure and append-only structural judgments offline."""
import copy
import hashlib
import json
from pathlib import Path

from native_lmf import array, entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    import gzip
    path = ROOT / path
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def inspect():
    ledger = read('tests/fixtures/validity.json')
    catalog = read('web/src/grammar-labels.json')
    totals = []
    for name, owners, examples, words, groups, cohort_words, required, forbidden in [
        ('degree-rimankeum', 43, 9, 8, 2073, 5019, 9, 3),
        ('counterfactual-ryeon', 44, 19, 19, 2334, 5463, 19, 6),
    ]:
        source = read(f'docs/{name}-source-preparation.json.gz')
        cohort = read(f'docs/{name}-cohort.json.gz')
        fixture = read(f'tests/fixtures/{name}-sources.json')
        suite = read(f'tests/fixtures/{name}-validity.json')
        native = source['complete_native_entries']
        assert len(native) == owners and native == fixture['complete_native_entries']
        assert {k: entry(v) for k, v in source['original_lmf'].items()} == native
        assert len(source['all_original_groups']) == examples
        assert source['all_original_groups'] == fixture['original_groups']
        assert len(source['expected_single_predicate_heads']) == words
        assert source['expected_single_predicate_heads'] == fixture['expected_heads']
        assert hashlib.sha256(source['producer']['text'].encode()).hexdigest() == source['producer']['sha256']
        assert cohort['source_sha256'] == hashlib.sha256((ROOT / f'docs/{name}-source-preparation.json.gz').read_bytes()).hexdigest()
        expected_groups = [dict(source_entry=k, source_sense=s['id'], example_index=i, original_group=g)
                           for k in sorted(native) for s in native[k]['senses'] for i, g in enumerate(s['examples'])]
        assert len(expected_groups) == groups
        assert cohort['source_groups'] == fixture['source_cohort_original_groups'] == expected_groups
        assert cohort['before_analyses'] == fixture['source_cohort_before_analyses']
        assert len(cohort['before_analyses']) == cohort_words
        before = {r['analysis']['normalized']: r['analysis']
                  for r in map(json.loads, source['captures']['NFC']['raw']['jsonl'].splitlines()) if r['kind'] == 'word'}
        assert before == fixture['before_analyses']
        for observation in source['literal_observations']:
            text = observation['original_group'][observation['text_index']]
            start, end = observation['character_span']
            assert text[start:end] == observation['surface']
        english = read(f'tests/fixtures/krdict-{name}-english.json')
        expected = copy.deepcopy(source['original_lmf'])
        for raw in expected.values():
            for sense in array(raw.get('Sense')):
                sense['Equivalent'] = [t for t in array(sense.get('Equivalent'))
                                       if any(f['att'] == 'language' and f['val'] == '영어' for f in array(t.get('feat')))]
        assert english['LexicalResource']['Lexicon']['LexicalEntry'] == list(expected.values())
        verify_native_lmf(english, native)
        for key, url in suite['sources'].items():
            assert ledger['sources'][key] == url
        assert [c for c in ledger['cases'] if c['id'].startswith(name + '-')] == suite['cases']
        judgments = [j for c in suite['cases'] for j in c['judgments']]
        assert sum(j['verdict'] == 'required' for j in judgments) == required
        assert sum(j['verdict'] == 'forbidden' for j in judgments) == forbidden
        totals.append((owners, examples, cohort_words, required, forbidden))
    expected_labels = {
        '-으리만큼': ('To such a degree', [87692, 86608]),
        '-으련만': ('Counterfactual expectation', [86546, 86603]),
        '-으련마는': ('Counterfactual expectation', [86545, 86602]),
    }
    labels = read('tests/fixtures/krdict-degree-expectation-labels.json')
    label_ids = {int(r['val']) for r in labels['LexicalResource']['Lexicon']['LexicalEntry']}
    assert label_ids == {i for _, ids in expected_labels.values() for i in ids}
    for key, (label, ids) in expected_labels.items():
        assert catalog[key]['kind'] == 'ending' and catalog[key]['label'] == label
        assert [s['id'] for s in catalog[key]['sources']] == ids
    return totals


if __name__ == '__main__':
    print('Verified complete source/import closure, original groups, frozen words and stable judgments:', inspect())
