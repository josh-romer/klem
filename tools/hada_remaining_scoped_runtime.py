"""Verify nested suffix labels against each owner's immediate inflection."""
import argparse
import unicodedata

from hada_remaining_audit import ROOT, REPORT as DIAGNOSTICS, read, sha

REPORT = ROOT / 'docs/hada-remaining-scoped-runtime.json'
CASES = {
    '먹는양하는양하다': ['Auxiliary verb formation', 'Auxiliary verb / adjective formation'],
    '먹는양하는듯하다': ['Auxiliary verb formation', 'Auxiliary adjective formation'],
    '먹는양했던양하다': ['Auxiliary verb / adjective formation', 'Auxiliary verb / adjective formation'],
}


def inspect(report):
    assert report['errors'] == []
    assert report['producer_sha256'] == sha(ROOT / 'web/tests/hada-remaining-scoped.mjs')
    assert report['frontend_sha256'] == sha(ROOT / 'web/src/breakdown.ts')
    assert report['cli_sha256'] == read(DIAGNOSTICS)['cli_sha256']
    assert len(report['checks']) == 6
    seen = set()
    for check in report['checks']:
        text, encoding = check['request']['text'], check['encoding']
        word = unicodedata.normalize('NFC', text)
        assert text == check['surface'] == unicodedata.normalize(encoding, word)
        assert encoding in ['NFC', 'NFD'] and word in CASES
        assert (word, encoding) not in seen
        seen.add((word, encoding))
        response = check['response']
        assert response['records'] == check['cli_records']
        records = response['records']
        assert ''.join(r['surface'] for r in records) == text
        index = next(i for i, r in enumerate(records) if r.get('analysis'))
        analysis = records[index]['analysis']['analyses'][check['selected']]
        assert analysis['lemmas'] == [{'text':'먹다', 'kind':'predicate'}, {'text':'양', 'kind':'nominal'}, {'text':'듯' if '듯' in word else '양', 'kind':'nominal'}]
        assert {'suffix.auxiliary.verb.hada', 'suffix.auxiliary.adjective.hada'} <= set(analysis['rules'])
        order = response['breakdowns'][index][check['selected']]
        for li in [1, 2]:
            at = order.index({'lemma':li})
            mi = order[at + 1]['morpheme']
            assert analysis['morphemes'][mi] == {'form':'하다', 'kind':'suffix'}
            if li == 1:
                following = analysis['morphemes'][mi + 1]
                assert following == ({'form':'었', 'kind':'prefinal'} if '했던' in word else {'form':'는', 'kind':'ending'})
        assert check['labels'] == CASES[word]
    assert seen == {(word, encoding) for word in CASES for encoding in ['NFC', 'NFD']}
    return len(seen)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.parse_args()
    print('Verified independently scoped nested suffix diagrams:', inspect(read(REPORT)))
