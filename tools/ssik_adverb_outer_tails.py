"""Audit the additional outer-tail scan and its unresolved attachment condition."""
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path

from lexical_nada_audit import ROOT, read, sha
from native_lmf import entry
from ssik_adverb_comparison import parent_for

REPORT = ROOT / 'docs/ssik-adverb-outer-tail-review.json.gz'


def discover(entries):
    heads = {}
    for value in entries:
        if value['pos'] == '부사':
            heads.setdefault(value['headword'], []).append(value['id'])
    observations = []
    for value in entries:
        for sense in value['senses']:
            for index, group in enumerate(sense['examples']):
                for text_index, text in enumerate(group):
                    for match in re.finditer(r'[가-힣]+', text):
                        token = match[0]
                        for pos, char in enumerate(token):
                            if char != '씩' or not pos:
                                continue
                            base, tail = token[:pos], token[pos + 1:]
                            if base not in heads or not tail:
                                continue
                            observations.append(dict(
                                source_entry=value['id'], source_sense=sense['id'],
                                example_index=index, text_index=text_index,
                                original_group=group, base=base,
                                adverb_base_entries=heads[base], surface=token,
                                tail=tail, character_span=[match.start(), match.end()],
                                contextual_verdict='unjudged', independent_review='pending',
                            ))
    return observations


def inspect(report, dictionary=None):
    assert report['checklist'] == 'COV-022v' and report['preparation_only'] is True
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    native = {ident: entry(raw) for ident, raw in report['original_lmf'].items()}
    assert native == report['complete_native_entries']
    assert all(ident == value['id'] for ident, value in native.items())
    plain = []
    observations = report['observations']
    assert len(observations) == len({o['id'] for o in observations}) == 107
    for observation in observations:
        original = {k: v for k, v in observation.items() if k not in ['id', 'disposition']}
        identity = hashlib.sha256(json.dumps(original, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
        assert observation['id'] == 'ssik-adverb-outer-' + identity
        plain.append(original)
        owner = native[original['source_entry']]
        sense = next(s for s in owner['senses'] if s['id'] == original['source_sense'])
        group = sense['examples'][original['example_index']]
        assert group == original['original_group']
        text = group[original['text_index']]
        start, end = original['character_span']
        assert text[start:end] == original['surface'] == original['base'] + '씩' + original['tail']
        for ident in original['adverb_base_entries']:
            assert native[ident]['headword'] == original['base'] and native[ident]['pos'] == '부사'
        expected = ('opaque_prefix_without_quantity_license' if original['base'] == '씩'
                    else 'noun_only_outer_attachment_unresolved_adverb_role' if original['surface'] == '잠깐씩밖에'
                    else 'conditional_adverb_particle_path_covered')
        assert observation['disposition'] == expected
    assert sum(o['base'] == '씩' for o in observations) == 99
    assert set(report['captures']) == {o['surface'] for o in observations}
    diagnostic = read(ROOT / 'docs/ssik-adverb-diagnostics.json.gz')
    for key in ['before_cli_sha256', 'cli_sha256', 'dictionary_sha256']:
        assert report[key] == diagnostic[key]
    for word, captures in report['captures'].items():
        before, after = [captures[key]['response'] for key in ['before', 'after']]
        for capture in captures.values():
            assert json.loads(capture['json']) == capture['response']
            assert capture['response']['normalized'] == word
            assert capture['command'][1:4] == ['word', word, '--dictionary']
        old, new = before['analyses'], after['analyses']
        assert [a for a in new if a in old] == old
        for index, analysis in enumerate(old):
            assert after['dictionary']['readings'][new.index(analysis)] == before['dictionary']['readings'][index]
        added = [a for a in new if a not in old]
        if word.startswith('씩씩') or word == '잠깐씩밖에':
            assert not added
        else:
            assert len(added) == 1
            parent_for(added[0], word, old)
        if word == '잠깐씩밖에':
            assert any(a['lemmas'] == [{'text': '잠깐', 'kind': 'nominal'}]
                       and a['morphemes'] == [{'form': '씩', 'kind': 'suffix'}, {'form': '밖에', 'kind': 'particle'}]
                       for a in old)
    assert native['krdict:70070']['notes'] == ['명사나 어미 ‘-기’ 뒤에 붙여 쓴다.']
    assert report['contextual_verdict'] == 'unjudged' and report['independent_review'] == 'pending'
    if dictionary is not None:
        assert sha(dictionary) == report['dictionary_sha256']
        with sqlite3.connect(dictionary.resolve().as_uri() + '?mode=ro', uri=True) as db:
            entries = [json.loads(data) for (data,) in db.execute('select data from entries order by id')]
        assert discover(entries) == plain
    return len(observations), len(report['captures']), 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', type=Path)
    args = parser.parse_args()
    print('Verified additional outer-tail occurrences, captured surfaces and unresolved attachment:',
          inspect(read(REPORT), args.dictionary))
