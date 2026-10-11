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
            'willingness_parent_reviews_raw': unpack('willingness-question-parent-inventory-reviews.json.gz'),
            'willingness_reviews_raw': (docs / 'willingness-question-scoped-reviews.json').read_bytes(),
            'willingness_source': json.loads((ROOT / 'tests/fixtures/willingness-question-source.json').read_bytes()),
            'interaction_parent_raw': unpack('willingness-question-interaction-parent-validity.json.gz'),
            'interaction_raw': (ROOT / 'tests/fixtures/willingness-question-interaction-validity.json').read_bytes(),
            'current_reviews': json.loads((docs / 'inventory-reviews.json').read_bytes()),
            'conjectural_cases': [case for name in ['conjectural-additive-validity.json', 'conjectural-additive-copula-validity.json', 'conjectural-additive-novel-validity.json'] for case in json.loads((ROOT / 'tests/fixtures' / name).read_bytes())['cases']],
            'expression_cases': json.loads((ROOT / 'tests/fixtures/formal-volitional-expression-validity.json').read_bytes())['cases'],
            'willingness_raw': [(ROOT / 'tests/fixtures' / name).read_bytes() for name in ['willingness-question-validity.json', 'willingness-question-boundary-validity.json']]}


def inspect(v):
    assert sha(v['interaction_parent_raw']) == '5f695ecf212ef16b5d932c1a43bdf0df3d570e3eea6d46f191953ddc8ea0f799', 'exact pre-interaction ledger bytes'
    assert sha(v['interaction_raw']) == '529f6614d742d6606f1b3e5f66c9df3a769cd698a6b92ee90eb276b09f438de3', 'exact independently authored interaction judgments'
    assert sha(v['expression_raw']) == '4d5136fb9cdd8d2a89a612d9a3dc9e790956f5110bfb9c8e1ab7f7d2df1cdda4', 'exact expression historical ledger bytes'
    assert sha(v['conjectural_raw']) == '95f6fb575e4444081696ec08c85ae856423b3ec5ce81c1abb283406271a6bc88', 'exact conjectural historical ledger bytes'
    expression, conjectural, current = (json.loads(v[key]) for key in ['expression_raw', 'conjectural_raw', 'current_raw'])
    assert [sha(raw) for raw in v['willingness_raw']] == ['fb972dd5554f0f1016768cc98900b9d883702f11c481ca854c005191aeb1e769', '4e0e2d5d67b68c6fc3782a1d7457f8a3203f37e5acbfbdc3941e6ee58a5f66cf'], 'exact independently authored willingness judgments'
    willingness = [json.loads(raw) for raw in v['willingness_raw']]
    additions = [case for suite in willingness for case in suite['cases']]
    assert len(additions) == 22, 'twenty-two exact willingness additions'
    assert len(expression['cases']) == 35595 and len(conjectural['cases']) == 35643 and len(current['cases']) == 35681, 'complete historical and active ledger sizes'
    assert expression['cases'][:35587] == conjectural['cases'][:35587], 'identical common parent cases'
    assert expression['cases'][35587:] == v['expression_cases'] and len(v['expression_cases']) == 8, 'eight exact original expression judgments'
    assert conjectural['cases'][35587:] == v['conjectural_cases'] and len(v['conjectural_cases']) == 56, 'fifty-six exact original conjectural judgments'
    assert current['cases'][:35595] == expression['cases'], 'every original expression parent case retained'
    assert current['cases'][35595:35651] == conjectural['cases'][35587:], 'every original conjectural append retained'
    assert current['cases'][35651:35673] == additions, 'every exact original willingness append retained'
    interactions = json.loads(v['interaction_raw'])
    assert len(interactions['cases']) == 8 and current['cases'][35673:] == interactions['cases'], 'every exact independently authored interaction append retained'
    parent = json.loads(v['interaction_parent_raw'])
    assert len(parent['cases']) == 35673 and current['cases'][:35673] == parent['cases'], 'every pre-interaction parent case retained'
    prefix = v['expression_raw'].split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert v['current_raw'].split(b'"cases": [', 1)[1].startswith(prefix), 'every original serialized expression prefix byte'
    case_bytes = v['current_raw'].split(b'"cases": [', 1)[1]
    assert sha(case_bytes[:32220043]) == 'ccdf779f632cea3f4ba20d51bc3a9e57e1765d670daca66c05375937893e4f82', 'every original serialized combined case byte'
    assert sha(case_bytes[:32236877]) == 'b8f9d6468f7b8e1a9c28d5f162fff50d0b20af9bb27c4281337be5bcd9157a29', 'every pre-interaction serialized case byte retained'
    assert len({case['id'] for case in current['cases']}) == 35681, 'every active stable case identity unique'
    sources = dict(expression['sources'])
    for key, value in conjectural['sources'].items():
        assert key not in sources or sources[key] == value, 'identical overlapping source citations'
        sources[key] = value
    for suite in [*willingness, interactions]:
        for key, value in suite['sources'].items():
            assert key not in sources or sources[key] == value, 'identical willingness source citations'
            sources[key] = value
    assert current['sources'] == sources, 'every original branch source citation retained'
    assert {k: value for k, value in current.items() if k not in ['cases', 'sources']} == {k: value for k, value in expression.items() if k not in ['cases', 'sources']}, 'original parent ledger metadata retained'
    counts = {verdict: sum(j['verdict'] == verdict for case in current['cases'] for j in case['judgments']) for verdict in ['required', 'forbidden']}
    assert counts == {'required': 31412, 'forbidden': 4286}, 'complete active required and forbidden totals'
    assert sha(v['parent_reviews_raw']) == 'ead8f1ae0534f641704c143f0522b04a8216d0c1f25505d54d1e78abfd0444f8', 'exact historical manual review bytes'
    parent_reviews = json.loads(v['parent_reviews_raw'])['entries']
    current_reviews = v['current_reviews']['entries']
    indexed = {review['id']: review for review in current_reviews}
    assert len(parent_reviews) == 511 and len(current_reviews) == len(indexed) == 515, 'complete original and active inventory review sizes'
    assert all(indexed.get(review['id']) == review for review in parent_reviews), 'every original manual review field retained'
    assert set(indexed) - {r['id'] for r in parent_reviews} == {'krdict:86083', 'krdict:86084', 'krdict:76564', 'krdict:76567'}, 'only two conjectural and two willingness dispositions appended'
    assert sha(v['willingness_parent_reviews_raw']) == '5809cc3e8a9dabd2c81a1f6f1d4f2bf48c19cc7615dcc0b699e0957459f65e48', 'exact pre-willingness inventory review bytes'
    old_reviews = json.loads(v['willingness_parent_reviews_raw'])
    assert len(old_reviews['entries']) == 513 and current_reviews[:513] == old_reviews['entries'], 'every pre-willingness manual review field and order retained'
    assert {k: value for k, value in v['current_reviews'].items() if k != 'entries'} == {k: value for k, value in old_reviews.items() if k != 'entries'}, 'original review metadata retained'
    assert sha(v['willingness_reviews_raw']) == '0d5ba30af82b1342609dc8f7e2ce9d72212325598f92483d52dd3809ff58c2f7', 'exact bounded willingness dispositions'
    new_reviews = json.loads(v['willingness_reviews_raw'])['entries']
    assert len(new_reviews) == 2 and current_reviews[513:] == new_reviews, 'only exact independently recorded willingness reviews appended'
    from review_inventory import digest, source_entry
    source = v['willingness_source']
    assert source['ending_owner_ids'] == [r['id'] for r in new_reviews] == ['krdict:76564', 'krdict:76567'], 'both original ending owners reviewed separately'
    for review in new_reviews:
        assert review['source_sha256'] == digest(source_entry(source['owners'][review['id']])), 'complete original inventory source digest for bounded review'
        expected = [{'case': case['id'], 'judgment': judgment['id']}
                    for case in additions for judgment in case['judgments']
                    if current['sources'][judgment['source']] == source['owners'][review['id']]['url'] and judgment['verdict'] == 'required'
                    and case['id'].startswith('willingness-question-' + review['id'].split(':')[1] + '-')]
        assert len(expected) in [4, 6] and review['judgments'] == expected, 'all original source group judgments for each bounded review'
    return {'state': 'exact-both-histories-and-active-ledger-passed', 'expression_historical_cases': 35595,
            'conjectural_historical_cases': 35643, 'active_cases': 35681, 'required': 31412, 'forbidden': 4286,
            'unchanged_combined_parent_cases': 35651, 'willingness_added_cases': 22, 'interaction_added_cases': 8, 'unchanged_pre_interaction_cases': 35673,
            'original_manual_reviews': 511, 'unchanged_pre_willingness_reviews': 513, 'active_manual_reviews': 515, 'new_willingness_reviews': 2, 'unjudged_alternatives_promoted': False,
            'full_coverage_complete': False}


if __name__ == '__main__':
    print(inspect(inputs()))
