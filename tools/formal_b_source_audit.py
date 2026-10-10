"""Verify original formal-ending groups, Native identities and finite judgments."""
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [('습디다', 80528, 80530), ('습디까', 80533, 80536),
         ('습지요', 80544, 80547), ('습죠', 80546, 80550), ('습네', 86556, 86561)]


def read(name):
    path = ROOT / name
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def inspect(prepared, closure, native, proposals, suite, labels, label_fixture):
    identities = ['krdict:' + str(i) for _, a, b in PAIRS for i in [a, b]]
    original = prepared['complete_imported_entries']
    assert set(original) == set(identities), 'all ten distinct ending owners'
    assert all(e['pos'] == '어미' for e in original.values()), 'original ending roles'
    values = native['LexicalResource']['Lexicon']['LexicalEntry']
    projected = {entry(raw)['id']: entry(raw) for raw in values}
    assert len(projected) == len(values) == 92, 'no lost or duplicate Native identity'
    assert projected == closure['entries'], 'complete original Native projection'
    for ident, raw in prepared['original_native_entries'].items():
        assert entry(raw) == projected[ident] == original[ident], 'complete original source owner'
        assert raw == next(v for v in values if v['val'] == raw['val']), 'original LMF bytes projected without edits'
    groups = []
    text = ''
    for ident in identities:
        for sense in original[ident]['senses']:
            for ordinal, examples in enumerate(sense['examples'], 1):
                start = len(text.encode())
                block = '\n'.join(examples)
                text += block + '\n'
                groups.append({'id': f"formal-b-source-{ident.split(':')[1]}-{sense['id']}-{ordinal}",
                               'entry_id': ident, 'sense_id': sense['id'], 'group': ordinal,
                               'complete_original_examples': examples,
                               'span': {'start': start, 'end': start + len(block.encode())}})
    assert groups == prepared['complete_groups'] and len(groups) == 46, 'all original groups in order'
    assert text == prepared['complete_source_text'], 'complete original source text'
    assert proposals == prepared['proposals'] and len(proposals) == 46, 'all authored original proposals'
    assert {p['source_group_id'] for p in proposals} == {g['id'] for g in groups}, 'every source group has a proposal'
    cases = {c['id']: c for c in suite['cases']}
    assert len(cases) == len(suite['cases']) == 99, 'stable unique source and boundary cases'
    for p in proposals:
        group = next(g for g in groups if g['id'] == p['source_group_id'])
        assert p['complete_original_group'] == group['complete_original_examples'], 'complete proposal context'
        block = '\n'.join(p['complete_original_group']).encode()
        assert block.find(p['surface'].encode()) == int(p['id'].rsplit('-', 1)[1]), 'original source byte offset'
        case = cases[p['id']]
        assert case['surface'] == p['surface'] and len(case['judgments']) == 1, 'source surface identity'
        judgment = case['judgments'][0]
        assert judgment['lemmas'] == p['proposed_lemmas'] and judgment['verdict'] == 'required', 'original authored lemma proposal'
        assert judgment['required_rules'] == ['ending.formal_b'], 'source path attribution'
    assert {v: sum(j['verdict'] == v for c in suite['cases'] for j in c['judgments'])
            for v in ['required', 'forbidden']} == {'required': 71, 'forbidden': 28}, 'exact finite judgments'
    label_values = label_fixture['LexicalResource']['Lexicon']['LexicalEntry']
    assert len(label_values) == 10 and {entry(v)['id'] for v in label_values} == set(identities), 'complete label owner identities'
    assert all(v == next(raw for raw in values if raw['val'] == v['val']) for v in label_values), 'complete original label entries'
    for form, a, b in PAIRS:
        label = labels['-' + form]
        assert label['kind'] == 'ending', 'label morphology role'
        assert label['sources'] == [{'id': i, 'headword': original['krdict:' + str(i)]['headword'], 'pos': '어미'}
                                    for i in [a, b]], 'distinct allomorph source identities'
    tension = projected['krdict:71290']
    assert tension['headword'] == '아름답다' and tension['pos'] == '형용사', 'no source tension reclassification'
    assert any('아름답네' in line for sense in original['krdict:86556']['senses']
               for group in sense['examples'] for line in group), 'independent exact source tension witness'
    return {'source_groups': 46, 'native_entries': 92, 'required': 71, 'forbidden': 28,
            'independent_contextual_review_complete': False}


def inputs():
    return [read(p) for p in ['docs/formal-b-source-preparation.json.gz', 'docs/formal-b-native-closure.json.gz',
                             'tests/fixtures/formal-b-native.json', 'tests/fixtures/formal-b-proposals.json',
                             'tests/fixtures/formal-b-validity.json', 'web/src/grammar-labels.json',
                             'tests/fixtures/krdict-formal-b-labels.json']]


if __name__ == '__main__':
    print(inspect(*inputs()))
