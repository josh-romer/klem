"""Verify command -ㄴ source closure, frozen outputs and individual judgments."""
import copy
import hashlib
import json
from lexical_nada_audit import ROOT, read, sha
from native_lmf import array, entry, verify_native_lmf
from friendly_command_preparation import inspect as preparation


def inspect():
    assert preparation() == (59, 5, 4)
    p = read(ROOT / 'docs/friendly-command-preflight.json.gz')
    f = read(ROOT / 'tests/fixtures/friendly-command-sources.json')
    assert p['schema_version'] == 1 and p['checklist'] == 'COV-017bx'
    assert p['preparation_only'] is True
    assert p['preparation_sha256'] == sha(ROOT / 'docs/friendly-command-source-preparation.json.gz')
    assert f['source_sha256'] == sha(ROOT / 'docs/friendly-command-preflight.json.gz')
    assert hashlib.sha256(p['producer']['text'].encode()).hexdigest() == p['producer']['sha256']
    native = p['complete_native_entries']
    assert len(native) == 60 and native == f['complete_native_entries']
    assert {k: entry(v) for k, v in p['original_lmf'].items()} == native
    prior = read(ROOT / 'docs/friendly-command-source-preparation.json.gz')
    assert all(native[k] == v for k, v in prior['complete_native_entries'].items())
    assert native['krdict:69517']['pos'] == '보조 동사'
    assert native['krdict:69514']['pos'] == '동사'
    assert p['coming_head_inventory'] == f['coming_head_inventory'] == prior['coming_head_inventory']
    assert p['command_original_groups'] == f['command_original_groups'] == prior['all_original_groups']
    groups = [dict(source_entry=k, source_sense=s['id'], example_index=i, original_group=g)
              for k in sorted(native) for s in native[k]['senses'] for i, g in enumerate(s['examples'])]
    assert groups == p['all_original_groups'] and len(groups) == 1874
    original = read(ROOT / 'tests/fixtures/krdict-friendly-command-original.json')
    english = read(ROOT / 'tests/fixtures/krdict-friendly-command-english.json')
    assert {entry(raw)['id']: entry(raw) for raw in array(original['LexicalResource']['Lexicon']['LexicalEntry'])} == native
    expected = copy.deepcopy(original)
    for raw in array(expected['LexicalResource']['Lexicon']['LexicalEntry']):
        for sense in array(raw.get('Sense')):
            if 'Equivalent' in sense:
                sense['Equivalent'] = [e for e in array(sense['Equivalent']) if any(x['att'] == 'language' and x['val'] == '영어' for x in array(e.get('feat')))]
    assert english == expected
    verify_native_lmf(english, native)
    labels = read(ROOT / 'tests/fixtures/krdict-friendly-command-labels.json')
    assert labels['LexicalResource']['Lexicon']['LexicalEntry'] == [r for r in english['LexicalResource']['Lexicon']['LexicalEntry'] if r['val'] == '73877']
    assert p['lmf_sha256'] == {name: sha(ROOT / f'tests/fixtures/krdict-friendly-command-{name}.json') for name in ['original', 'english']}
    text = '\n'.join(p['words'] + [t for g in groups for t in g['original_group']]) + '\n'
    assert p['input'] == text and p['input_sha256'] == hashlib.sha256(text.encode()).hexdigest()
    assert p['before_cli_sha256'] == read(ROOT / 'docs/ssik-adverb-packaged-checks.json.gz')['cli_sha256']
    assert set(p['runs']) == {'raw', 'headword', 'compatible'}
    for mode, run in p['runs'].items():
        assert run['exit_code'] == 0 and run['sha256'] == hashlib.sha256(run['jsonl'].encode()).hexdigest()
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert ''.join(r['surface'] for r in rows) == text
        offset = 0
        for row in rows:
            assert row['span'] == dict(start=offset, end=offset + len(row['surface'].encode()))
            offset = row['span']['end']
        if mode == 'raw':
            before = {r['analysis']['normalized']: r['analysis'] for r in rows if r['kind'] == 'word'}
            assert before == p['before_analyses'] == f['before_analyses'] and len(before) == 4794
    ledger = read(ROOT / 'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('friendly-command-')] == f['cases']
    assert len(f['cases']) == 7
    assert sum(j['verdict'] == 'required' for c in f['cases'] for j in c['judgments']) == 4
    assert sum(j['verdict'] == 'forbidden' for c in f['cases'] for j in c['judgments']) == 3
    for key, value in f['sources'].items():
        assert ledger['sources'][key] == value
    catalog = read(ROOT / 'web/src/grammar-labels.json')
    assert catalog['-ㄴ']['kind'] == 'ending'
    assert catalog['-ㄴ']['sources'] == [dict(id=78634, headword='-ㄴ', pos='어미'), dict(id=73877, headword='-ㄴ', pos='어미')]
    assert p['contextual_verdict'] == f['contextual_verdict'] == 'unjudged'
    assert p['independent_review'] == f['independent_review'] == 'pending'
    return len(native), len(groups), len(before), len(f['cases'])


if __name__ == '__main__':
    print('Verified complete command/adnominal/auxiliary owners, original groups, frozen outputs and individual cases:', inspect())
