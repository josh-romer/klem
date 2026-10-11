"""Bind the gentle append to exact parent bytes and independent source judgments."""
import gzip
import hashlib
import json
from pathlib import Path

import gentle_command_source_audit as source_audit
from review_inventory import digest, source_entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
PARENT_SHA = 'e5bf297ad75bfec83b8836c16e718796827deb71caf96f4332979e4102cad88e'
REVIEWS_SHA = 'fd6a487eeaf98e0166f04115f1d3c664d695f4b1e2dc88a2cd47faac8a018950'
SCOPED_SHA = '7e8e7641a8a778893d23b86a7dc623121696f9928ecb09e5a81ef77fcaa0afe3'


def original_inputs():
    docs = ROOT/'docs'
    return dict(parent_raw=gzip.decompress((docs/'gentle-command-parent-validity.json.gz').read_bytes()),
                parent_reviews_raw=gzip.decompress((docs/'gentle-command-parent-inventory-reviews.json.gz').read_bytes()),
                current_raw=(ROOT/'tests/fixtures/validity.json').read_bytes(),
                current_reviews=json.loads((docs/'inventory-reviews.json').read_bytes()),
                scoped_raw=(docs/'gentle-command-scoped-reviews.json').read_bytes(),
                source_evidence=source_audit.inputs())


def inputs():
    values = original_inputs()
    values['actual_current_raw'] = values['current_raw']
    values['actual_current_reviews'] = values['current_reviews']
    if len(json.loads(values['current_raw'])['cases']) > 35704:
        import gentle_command_long_ledger_audit as long_audit
        complete = long_audit.inputs()
        values['long_append'] = complete
        values['current_raw'] = complete['parent_raw']
        values['current_reviews'] = json.loads(complete['parent_reviews_raw'])
    return values


def inspect_historical(v):
    source_audit.inspect(v['source_evidence'])
    assert sha(v['parent_raw']) == PARENT_SHA, 'exact original35681-case parent bytes'
    assert sha(v['parent_reviews_raw']) == REVIEWS_SHA, 'exact original515-review parent bytes'
    assert sha(v['scoped_raw']) == SCOPED_SHA, 'exact two independently recorded scoped dispositions'
    parent = json.loads(v['parent_raw']); current = json.loads(v['current_raw'])
    reviews = json.loads(v['parent_reviews_raw']); scoped = json.loads(v['scoped_raw'])
    suite = v['source_evidence']['suite']; source = v['source_evidence']['source']
    assert len(parent['cases']) == 35681 and len(current['cases']) == 35704, 'complete parent and23-case append'
    assert current['cases'][:35681] == parent['cases'], 'every original parent case and judgment field/order'
    assert current['cases'][35681:] == suite['cases'], 'exact reviewed15required8forbidden append'
    body = lambda raw: raw.split(b'"cases": [',1)[1].rsplit(b'\n  ]\n}',1)[0]
    assert body(v['current_raw']).startswith(body(v['parent_raw'])), 'every original serialized parent case byte'
    sources = dict(parent['sources'])
    for key,value in suite['sources'].items():
        assert key not in sources or sources[key] == value, 'unchanged overlapping source identities'
        sources[key] = value
    assert current['sources'] == sources, 'all original and only independently reviewed source citations'
    assert {k:t for k,t in current.items() if k not in ['cases','sources']} == {k:t for k,t in parent.items() if k not in ['cases','sources']}, 'original parent ledger metadata'
    assert len({case['id'] for case in current['cases']}) == 35704, 'all unique stable case IDs'
    counts = {kind:sum(j['verdict'] == kind for c in current['cases'] for j in c['judgments']) for kind in ['required','forbidden']}
    assert counts == {'required':31427,'forbidden':4294}, 'complete current required/forbidden counts'
    active = v['current_reviews']
    assert len(reviews['entries']) == 515 and len(active['entries']) == 517, 'exact parent and two scoped reviews'
    assert active['entries'][:515] == reviews['entries'], 'every original manual review field/order'
    assert {k:t for k,t in active.items() if k != 'entries'} == {k:t for k,t in reviews.items() if k != 'entries'}, 'original manual review metadata'
    new = scoped['entries']
    assert active['entries'][515:] == new and len(new) == 2, 'only exact bounded gentle reviews appended'
    assert [r['id'] for r in new] == source['ending_owner_ids'] == ['krdict:79340','krdict:79343'], 'both separate original ending owners'
    for review in new:
        assert review['status'] == 'scoped' and review['remaining'] and review['checklist'] == ['COV-017cz'], 'bounded structural review scope'
        assert review['source_sha256'] == digest(source_entry(source['owners'][review['id']])), 'complete original inventory source digest'
        expected = [{'case':c['id'],'judgment':j['id']} for c in suite['cases'] for j in c['judgments']
                    if c['id'].startswith('gentle-command-'+review['id'].split(':')[1]+'-')
                    and j['verdict'] == 'required'
                    and suite['sources'][j['source']] == source['owners'][review['id']]['url']]
        assert review['judgments'] == expected and len(expected) == 4, 'all four independent original groups per ending owner'
    return dict(state='exact-gentle-command-append-and-scoped-reviews-passed',
                parent_cases=35681,active_cases=35704,added_cases=23,required=31427,forbidden=4294,
                original_reviews=515,active_reviews=517,unreviewed=198,
                unjudged_novel_or_history_paths_promoted=False,full_coverage_complete=False)


def inspect(v):
    result = inspect_historical(v)
    if v['actual_current_raw'] != v['current_raw']:
        import gentle_command_long_ledger_audit as long_audit
        complete = v['long_append']
        assert complete['current_raw'] == v['actual_current_raw'], 'mandatory complete current long ledger bytes'
        assert complete['current_reviews'] == v['actual_current_reviews'], 'mandatory complete current long review fields'
        assert complete['parent_raw'] == v['current_raw'], 'historical gentle matches exact long parent'
        assert json.loads(complete['parent_reviews_raw']) == v['current_reviews'], 'historical gentle reviews match exact long parent'
        checked = long_audit.inspect(complete)
        return {**result, 'historical': result,
                'scope': 'historical35704-and-complete-current35740',
                'complete_current_cases': checked['active_cases'],
                'complete_current_required': checked['required'],
                'complete_current_forbidden': checked['forbidden'],
                'complete_current_reviews': checked['active_reviews'],
                'long_added_cases': checked['added_cases']}
    assert v['actual_current_reviews'] == v['current_reviews'], 'complete original current review fields'
    return {**result, 'scope': 'complete-current35704',
            'complete_current_cases': result['active_cases'],
            'complete_current_required': result['required'],
            'complete_current_forbidden': result['forbidden'],
            'complete_current_reviews': result['active_reviews']}


if __name__ == '__main__':
    print(inspect(inputs()))
