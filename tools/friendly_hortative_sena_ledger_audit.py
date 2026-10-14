"""Check the exact original Sena append before allowing a historical parent view.

This prepared guard grants no runtime, contextual, or integration claim. Its
input is the actual complete ledger, never a caller-supplied truncated parent.
"""
import copy
import hashlib
import json
from pathlib import Path

import friendly_hortative_sena_ledger_draft_audit as original


SCOPED_SHA = 'dc3eb7b3479b93f88d109f0f48581490db92a18e353b11f8a2f162e13d4a2c27'


def scoped_review():
    here = Path(__file__).resolve().parent
    path = (here / 'sena-promoted-scoped-review-prepared.json' if here.name == 'friendly-hortative-sena-prepared'
            else original.ROOT / 'docs/friendly-hortative-sena-scoped-reviews.json')
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SCOPED_SHA, 'exact current bounded Sena review'
    return json.loads(raw)['entries'][0]


def inputs(draft=False):
    authored = original.inputs()
    if draft:
        raw = authored['current_raw']
        reviews = copy.deepcopy(authored['current_reviews'])
        reviews['entries'][-1] = scoped_review()
    else:
        root = original.ROOT
        raw = (root / 'tests/fixtures/validity.json').read_bytes()
        reviews = json.loads((root / 'docs/inventory-reviews.json').read_bytes())
    return dict(original=authored, current_raw=raw, current_reviews=reviews,
                draft=draft)


def inspect(v):
    authored = v['original']
    original.inspect(authored)
    parent = json.loads(authored['parent_raw'])
    current = json.loads(v['current_raw'])
    suite = json.loads(authored['suite_raw'])
    assert len(current['cases']) == 35789, 'complete35764 parent plus25 Sena cases'
    assert current['cases'][:35764] == parent['cases'], 'all35764 parent case fields and order'
    assert current['cases'][35764:] == suite['cases'], 'only exact25 preauthored Sena cases'
    body = lambda raw: raw.split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert body(v['current_raw']).startswith(body(authored['parent_raw'])), 'all35764 serialized parent case bytes'
    assert len({case['id'] for case in current['cases']}) == 35789, 'all unique stable current IDs'
    expected_sources = dict(parent['sources'])
    for name, url in suite['sources'].items():
        assert name not in expected_sources or expected_sources[name] == url
        expected_sources[name] = url
    assert current['sources'] == expected_sources, 'only exact original Sena source declaration'
    assert {k: x for k, x in current.items() if k not in ('sources', 'cases')} == {
        k: x for k, x in parent.items() if k not in ('sources', 'cases')
    }, 'complete original ledger metadata'
    counts = {kind: sum(j['verdict'] == kind for c in current['cases'] for j in c['judgments'])
              for kind in ('required', 'forbidden')}
    assert counts == dict(required=31488, forbidden=4318), 'complete required and forbidden judgments'
    before = json.loads(authored['parent_reviews_raw'])
    reviews = v['current_reviews']
    assert len(reviews['entries']) == 521, 'complete520 parent reviews plus one Sena owner'
    assert reviews['entries'][:520] == before['entries'], 'all520 review fields and order'
    assert {k: x for k, x in reviews.items() if k != 'entries'} == {
        k: x for k, x in before.items() if k != 'entries'
    }, 'complete original review metadata'
    expected = scoped_review()
    drafted = authored['current_reviews']['entries'][-1]
    assert {k: x for k, x in expected.items() if k not in ('scope', 'remaining')} == {
        k: x for k, x in drafted.items() if k not in ('scope', 'remaining')
    }, 'every original owner source judgment evidence field unchanged'
    assert 'Proposed' not in expected['scope'] and 'external draft' not in expected['scope']
    assert expected['remaining'] and 'independent Korean-language review' in expected['remaining']
    assert reviews['entries'][520:] == [expected], 'exact bounded Sena review and source judgments'
    return dict(parent_cases=35764, current_cases=35789, added_cases=25,
                parent_reviews=520, current_reviews=521, required=31488, forbidden=4318,
                original_source_groups=5, original_required=19, original_forbidden=6,
                original_corpus_hypothesis_promoted=False,
                actual_shared_promotion=not v['draft'],
                context_register_independent_review='pending', full_coverage_complete=False)


def historical_parent(v):
    """Return the entire original parent only after verifying the whole append."""
    inspect(v)
    return dict(current_raw=v['original']['parent_raw'],
                current_reviews=copy.deepcopy(json.loads(v['original']['parent_reviews_raw'])))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft', action='store_true')
    args = parser.parse_args()
    print(inspect(inputs(draft=args.draft)))
