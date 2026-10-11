"""Preserve both exact histories and validate the bounded willingness append."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inputs():
    docs = ROOT / 'docs'
    unpack = lambda name: gzip.decompress((docs / name).read_bytes())
    return {'expression_raw': unpack('formal-volitional-expression-validated-private-validity.json.gz'),
            'conjectural_raw': unpack('conjectural-additive-validated-private-validity.json.gz'),
            'current_raw': (ROOT / 'tests/fixtures/validity.json').read_bytes(),
            'parent_reviews_raw': unpack('expression-conjectural-parent-inventory-reviews.json.gz'),
            'current_reviews': json.loads((docs / 'inventory-reviews.json').read_bytes()),
            'conjectural_cases': [case for name in ['conjectural-additive-validity.json', 'conjectural-additive-copula-validity.json', 'conjectural-additive-novel-validity.json'] for case in json.loads((ROOT / 'tests/fixtures' / name).read_bytes())['cases']],
            'expression_cases': json.loads((ROOT / 'tests/fixtures/formal-volitional-expression-validity.json').read_bytes())['cases'],
            'willingness_raw': [(ROOT / 'tests/fixtures' / name).read_bytes() for name in ['willingness-question-validity.json', 'willingness-question-boundary-validity.json']]}


def inspect(v):
    assert sha(v['expression_raw']) == '4d5136fb9cdd8d2a89a612d9a3dc9e790956f5110bfb9c8e1ab7f7d2df1cdda4', 'exact expression historical ledger bytes'
    assert sha(v['conjectural_raw']) == '95f6fb575e4444081696ec08c85ae856423b3ec5ce81c1abb283406271a6bc88', 'exact conjectural historical ledger bytes'
    expression, conjectural, current = (json.loads(v[key]) for key in ['expression_raw', 'conjectural_raw', 'current_raw'])
    assert [sha(raw) for raw in v['willingness_raw']] == ['fb972dd5554f0f1016768cc98900b9d883702f11c481ca854c005191aeb1e769', '4e0e2d5d67b68c6fc3782a1d7457f8a3203f37e5acbfbdc3941e6ee58a5f66cf'], 'exact independently authored willingness judgments'
    willingness = [json.loads(raw) for raw in v['willingness_raw']]
    additions = [case for suite in willingness for case in suite['cases']]
    assert len(additions) == 22, 'twenty-two exact willingness additions'
    assert len(expression['cases']) == 35595 and len(conjectural['cases']) == 35643 and len(current['cases']) == 35673, 'complete historical and active ledger sizes'
    assert expression['cases'][:35587] == conjectural['cases'][:35587], 'identical common parent cases'
    assert expression['cases'][35587:] == v['expression_cases'] and len(v['expression_cases']) == 8, 'eight exact original expression judgments'
    assert conjectural['cases'][35587:] == v['conjectural_cases'] and len(v['conjectural_cases']) == 56, 'fifty-six exact original conjectural judgments'
    assert current['cases'][:35595] == expression['cases'], 'every original expression parent case retained'
    assert current['cases'][35595:35651] == conjectural['cases'][35587:], 'every original conjectural append retained'
    assert current['cases'][35651:] == additions, 'every exact original willingness append retained'
    prefix = v['expression_raw'].split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert v['current_raw'].split(b'"cases": [', 1)[1].startswith(prefix), 'every original serialized expression prefix byte'
    case_bytes = v['current_raw'].split(b'"cases": [', 1)[1]
    assert sha(case_bytes[:32220043]) == 'ccdf779f632cea3f4ba20d51bc3a9e57e1765d670daca66c05375937893e4f82', 'every original serialized combined case byte'
    assert len({case['id'] for case in current['cases']}) == 35673, 'every active stable case identity unique'
    sources = dict(expression['sources'])
    for key, value in conjectural['sources'].items():
        assert key not in sources or sources[key] == value, 'identical overlapping source citations'
        sources[key] = value
    for suite in willingness:
        for key, value in suite['sources'].items():
            assert key not in sources or sources[key] == value, 'identical willingness source citations'
            sources[key] = value
    assert current['sources'] == sources, 'every original branch source citation retained'
    assert {k: value for k, value in current.items() if k not in ['cases', 'sources']} == {k: value for k, value in expression.items() if k not in ['cases', 'sources']}, 'original parent ledger metadata retained'
    counts = {verdict: sum(j['verdict'] == verdict for case in current['cases'] for j in case['judgments']) for verdict in ['required', 'forbidden']}
    assert counts == {'required': 31408, 'forbidden': 4282}, 'complete active required and forbidden totals'
    assert sha(v['parent_reviews_raw']) == 'ead8f1ae0534f641704c143f0522b04a8216d0c1f25505d54d1e78abfd0444f8', 'exact historical manual review bytes'
    parent_reviews = json.loads(v['parent_reviews_raw'])['entries']
    current_reviews = v['current_reviews']['entries']
    indexed = {review['id']: review for review in current_reviews}
    assert len(parent_reviews) == 511 and len(current_reviews) == len(indexed) == 513, 'complete original and active inventory review sizes'
    assert all(indexed.get(review['id']) == review for review in parent_reviews), 'every original manual review field retained'
    assert set(indexed) - {r['id'] for r in parent_reviews} == {'krdict:86083', 'krdict:86084'}, 'only two bounded ending dispositions appended'
    return {'state': 'exact-both-histories-and-active-ledger-passed', 'expression_historical_cases': 35595,
            'conjectural_historical_cases': 35643, 'active_cases': 35673, 'required': 31408, 'forbidden': 4282,
            'unchanged_combined_parent_cases': 35651, 'willingness_added_cases': 22,
            'original_manual_reviews': 511, 'active_manual_reviews': 513, 'unjudged_alternatives_promoted': False,
            'full_coverage_complete': False}


if __name__ == '__main__':
    print(inspect(inputs()))
