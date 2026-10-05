"""Verify actual -씩 API/browser/source/export captures independently offline."""
import hashlib

from ssik_audit import ROOT, read


def inspect():
    report = read('docs/ssik-browser.json.gz')
    fixture = read('tests/fixtures/ssik-sources.json')
    diagnostic = read('docs/ssik-diagnostics.json.gz')
    assert report['cli_sha256'] == diagnostic['cli_sha256']
    assert report['dictionary_sha256'] == diagnostic['dictionary_sha256']
    assert report['fixture_sha256'] == diagnostic['fixture_sha256'] == hashlib.sha256((ROOT / 'tests/fixtures/ssik-sources.json').read_bytes()).hexdigest()
    assert report['producer_sha256'] == hashlib.sha256((ROOT / 'web/tests/ssik.mjs').read_bytes()).hexdigest()
    assert report['browser_errors'] == []
    assert len(report['responses']) == 2 and len(report['checks']) == 6
    assert len(report['diagrams']) == 24 and len(report['native']) == 17
    selected = ['잔씩', '사람씩', '마리씩', '며칠씩', '그릇씩', '조금씩', '하나씩', '걸음씩', '번씩', '고기씩이나', '선물씩이나', '용돈씩이나']
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
            assert analysis['lemmas'][0]['kind'] == 'nominal'
            assert 'suffix.distributive.ssik' in analysis['rules']
            forms = ['씩', '이나'] if word.endswith('이나') else ['씩']
            assert [m['form'] for m in analysis['morphemes']] == forms
            assert analysis['morphemes'][0]['kind'] == 'suffix'
            assert diagram['order'] == response['breakdowns'][record_index][diagram['selected']]
            assert diagram['order'] == [{'lemma': 0}] + [{'morpheme': i} for i in range(len(forms))]
            assert diagram['parts'] == [analysis['lemmas'][0]['text']] + forms
            assert diagram['label'] == 'Each / unexpected amount'
            assert '72043' in diagram['title'] and 'Quantity context and speaker expectation are not inferred' in diagram['title']
            whole = record['analysis']['analyses'][diagram['whole_selected']]
            assert whole['unchanged'] and whole['lemmas'][0]['text'] == word
    assert {item['id']: item['response']['entry'] for item in report['native']} == fixture['complete_native_entries']
    return len(report['diagrams']), len(report['checks']), len(report['native'])


if __name__ == '__main__':
    print('Verified actual ordered source diagrams, retained alternatives, exports and complete native endpoints:', inspect())
