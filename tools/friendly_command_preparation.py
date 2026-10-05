"""Verify the preserved source discovery for the still-unimplemented command -ㄴ."""
import hashlib
import json

from lexical_nada_audit import ROOT, read
from native_lmf import entry


def inspect():
    report = read(ROOT / 'docs/friendly-command-source-preparation.json.gz')
    assert report['schema_version'] == 1 and report['checklist'] == 'COV-017bx'
    assert report['preparation_only'] is True
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    native = {ident: entry(raw) for ident, raw in report['original_lmf'].items()}
    assert native == report['complete_native_entries']
    assert len(native) == 59 and all(value['id'] == ident for ident, value in native.items())
    source = native[report['source_entry']]
    assert source['id'] == 'krdict:73877' and source['headword'] == '-ㄴ'
    assert source['homonym'] == '2' and source['pos'] == '어미'
    assert '오다' in source['senses'][0]['notes'][0]
    assert len([e for e in native.values() if e['headword'] == '-ㄴ']) == 2
    groups = [dict(source_entry=source['id'], source_sense=sense['id'],
                   example_index=index, original_group=group)
              for sense in source['senses'] for index, group in enumerate(sense['examples'])]
    assert report['all_original_groups'] == groups and len(groups) == 5
    coming = {ident: value['headword'] for ident, value in native.items()
              if value['pos'] == '동사' and value['headword'].endswith('오다')}
    assert coming == report['coming_head_inventory'] and len(coming) == 57
    captures = report['discovery_captures']
    assert set(captures) == {'온', '날아온', '내려온', '돌아온'}
    for word, capture in captures.items():
        response = capture['response']
        assert json.loads(capture['json']) == response and response['normalized'] == word
        predicate = '오다' if word == '온' else word[:-1] + '오다'
        assert capture['existing_adnominal_lemma'] == predicate
        assert any(path['lemmas'] == [{'text': predicate, 'kind': 'predicate'}]
                   and path['morphemes'] == [{'form': '은', 'kind': 'ending'}]
                   for path in response['analyses'])
        assert not any(m['form'] == 'ㄴ' and m['kind'] == 'ending'
                       for path in response['analyses'] for m in path['morphemes'])
    assert report['contextual_verdict'] == 'unjudged' and report['independent_review'] == 'pending'
    return len(native), len(groups), len(captures)


if __name__ == '__main__':
    print('Verified preparation-only native owners, original groups and actual discovery captures:', inspect())
