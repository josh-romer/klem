"""Verify actual -씩 API/browser/source/export captures independently offline."""
import hashlib

from ssik_audit import ROOT, read
from native_lmf import array, entry
from ssik_adverb_comparison import parent_for


def inspect_outer_tail():
    """Keep the separately discovered particle-tail observation source-owned."""
    report = read('docs/ssik-adverb-outer-tail.json')
    native = entry(report['original_lmf'])
    assert native == report['complete_native_entry']
    lead = report['lead']
    assert native['id'] == lead['source_entry'] == 'krdict:73319'
    sense = next(s for s in native['senses'] if s['id'] == lead['source_sense'])
    assert sense['examples'][lead['example_index']] == lead['original_group']
    assert lead['surface'] == '조금씩이라도'
    assert any(lead['surface'] in text for text in lead['original_group'])
    import json
    source = ROOT / report['source']
    if source.exists():
        assert hashlib.sha256(source.read_bytes()).hexdigest() == report['source_sha256']
        originals = array(json.loads(source.read_text())['LexicalResource']['Lexicon']['LexicalEntry'])
        assert report['original_lmf'] in originals
    before, after = [report['captures'][key] for key in ['before', 'after']]
    for capture in [before, after]:
        assert json.loads(capture['json']) == capture['response']
        assert capture['response']['normalized'] == lead['surface']
        assert capture['command'][1:4] == ['word', lead['surface'], '--dictionary']
        assert capture['command'][4].endswith('/data/dictionaries/krdict/krdict.db')
    diagnostic = read('docs/ssik-adverb-diagnostics.json.gz')
    assert before['cli_sha256'] == diagnostic['before_cli_sha256']
    assert after['cli_sha256'] == diagnostic['cli_sha256']
    old, new = before['response']['analyses'], after['response']['analyses']
    assert [path for path in new if path in old] == old
    for index, path in enumerate(old):
        current = new.index(path)
        assert after['response']['dictionary']['readings'][current] == before['response']['dictionary']['readings'][index]
    added = [path for path in new if path not in old]
    assert len(added) == 1
    path = added[0]
    assert path['morphemes'] == [
        {'form': '씩', 'kind': 'suffix'},
        {'form': '이라도', 'kind': 'particle'},
    ]
    parent_for(path, lead['surface'], old)
    assert report['contextual_verdict'] == 'unjudged'
    assert report['independent_review'] == 'pending'
    return lead['surface']


def inspect():
    report = read('docs/ssik-adverb-browser.json.gz')
    fixture = read('tests/fixtures/ssik-adverb-sources.json')
    diagnostic = read('docs/ssik-adverb-diagnostics.json.gz')
    assert report['cli_sha256'] == diagnostic['cli_sha256']
    assert report['dictionary_sha256'] == diagnostic['dictionary_sha256']
    assert report['fixture_sha256'] == diagnostic['fixture_sha256'] == hashlib.sha256((ROOT / 'tests/fixtures/ssik-adverb-sources.json').read_bytes()).hexdigest()
    assert report['producer_sha256'] == hashlib.sha256((ROOT / 'web/tests/ssik-adverb.mjs').read_bytes()).hexdigest()
    assert report['browser_errors'] == []
    assert len(report['responses']) == 2 and len(report['checks']) == 6
    assert len(report['diagrams']) == 20 and len(report['native']) == 349
    selected = [base + '씩' for base in fixture['eligible_bases']] + ['조금씩은요']
    for encoding in ['NFC', 'NFD']:
        capture = next(c for c in report['responses'] if c['encoding'] == encoding)
        response = capture['response']
        assert ''.join(r['surface'] for r in response['records']) == capture['request']['text']
        for mode in ['raw', 'headword', 'compatible']:
            check = next(c for c in report['checks'] if c['encoding'] == encoding and c['mode'] == mode)
            assert check['cli_records'] == check['exported_records']
            assert ''.join(r['surface'] for r in check['cli_records']) == capture['request']['text']
            if mode == 'raw':
                assert check['cli_records'] == response['records']
        for word in selected:
            diagram = next(d for d in report['diagrams'] if d['encoding'] == encoding and d['word'] == word)
            record_index, record = next((i, r) for i, r in enumerate(response['records']) if (r.get('analysis') or {}).get('normalized') == word)
            analysis = record['analysis']['analyses'][diagram['selected']]
            assert diagram['analysis'] == analysis
            assert analysis['lemmas'][0]['kind'] == 'adverbial'
            assert 'suffix.distributive.ssik.adverbial_base' in analysis['rules']
            forms = ['씩', '은', '요'] if word.endswith('은요') else ['씩']
            assert [m['form'] for m in analysis['morphemes']] == forms
            assert analysis['morphemes'][0]['kind'] == 'suffix'
            assert diagram['order'] == response['breakdowns'][record_index][diagram['selected']]
            assert diagram['order'] == [{'lemma': 0}] + [{'morpheme': i} for i in range(len(forms))]
            assert diagram['parts'] == [analysis['lemmas'][0]['text']] + forms
            assert diagram['label'] == 'Each / unexpected amount'
            assert '72043' in diagram['title'] and 'Quantity context and speaker expectation are not inferred' in diagram['title']
            noun = record['analysis']['analyses'][diagram['noun_selected']]
            assert noun['lemmas'][0] == {'text': analysis['lemmas'][0]['text'], 'kind': 'nominal'}
            assert noun['morphemes'] == analysis['morphemes']
            assert 'noun base' in diagram['noun_label']
            assert 'adverb base' in diagram['adverb_label'] and 'adverb-forming' not in diagram['adverb_label']
            whole = record['analysis']['analyses'][diagram['whole_selected']]
            assert whole['unchanged'] and whole['lemmas'][0]['text'] == word
        standalone = next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized') == '씩')
        opaque = next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized') == '씩씩')
        assert any(e['id'] == 'krdict:66460' for lemma in standalone['dictionary']['lemmas'] for e in lemma['entries'])
        assert any(e['id'] == 'krdict:69538' for lemma in opaque['dictionary']['lemmas'] for e in lemma['entries'])
        assert all('suffix.distributive.ssik.adverbial_base' not in path['rules'] for path in opaque['analysis']['analyses'])
    assert {item['id']: item['response']['entry'] for item in report['native']} == fixture['complete_native_entries']
    return len(report['diagrams']), len(report['checks']), len(report['native'])


if __name__ == '__main__':
    print('Verified actual ordered source diagrams, retained alternatives, exports and complete native endpoints:', inspect())
    print('Verified separate source-owned outer particle observation:', inspect_outer_tail())
