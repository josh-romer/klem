"""Bind the finite long-ending append to original parents and unchanged judgments."""
import argparse
import gzip
import json
from pathlib import Path

import gentle_command_long_source_audit as source_audit
import gentle_command_ledger_audit as historical
from review_inventory import digest, source_entry

ROOT = Path(__file__).resolve().parents[1]
sha = source_audit.sha
PARENT_SHA = 'e2ce047408d1cc2e0c07d5fb43276571e4a22cc6fd5ba4e7dc861c03750b46f6'
REVIEWS_SHA = '81e771c20311f36d3982efc0c1721211ff7c6b2a8dc4f43b4a1cfbd433b0573c'
SCOPED_SHA = '4c378b8d3bf3c16187df2ae14d71ba0cf2ca25bbc6a84b3620c17d719072e04e'
PROPOSAL_SHA = '128e2bd79aa2a1ac44823a4a299a96ecf73f374afd97e9e07e6e1712e0c1ab7a'
DRAFT_SHA = '34bc7add26fc58a94a9fa3fdf5a613d8a6bbbdc7a76237e61041456cf6fc3ea0'
SUITES = [('gentle-command-long-validity.json',25,'d5440ac1a4801573e78eca3a5fdd98544c1e548a9cd5b7733d3c3060bd1c3668'),
          ('gentle-command-long-novel-validity.json',8,'63c0ac391529fb7c5806656cb1061a7b4dcd7282dca57d372905ebb885478463'),
          ('gentle-command-class-interaction-validity.json',3,'655f08927753cc454373a47dff559e77b08b1afc80cc46c84bdf2abbd8bd5026')]


def original_inputs(draft=False):
    docs = ROOT/'docs'
    parent_raw = gzip.decompress((docs/'gentle-command-long-parent-validity.json.gz').read_bytes())
    reviews_raw = gzip.decompress((docs/'gentle-command-long-parent-inventory-reviews.json.gz').read_bytes())
    scoped_raw = (docs/'gentle-command-long-scoped-reviews.json').read_bytes()
    proposed_raw = (docs/'gentle-command-long-ledger-proposed-cases.json').read_bytes()
    original = historical.original_inputs()
    original['current_raw'] = parent_raw
    original['current_reviews'] = json.loads(reviews_raw)
    current_raw = (ROOT/'tests/fixtures/validity.json').read_bytes()
    reviews = json.loads((docs/'inventory-reviews.json').read_bytes())
    if draft:
        candidate = json.loads(parent_raw); proposal = json.loads(proposed_raw)
        candidate['cases'].extend(proposal['cases']); candidate['sources'].update(proposal['sources'])
        current_raw = (json.dumps(candidate,ensure_ascii=False,indent=2)+'\n').encode()
        reviews = json.loads(reviews_raw); reviews['entries'].extend(json.loads(scoped_raw)['entries'])
    return dict(parent_raw=parent_raw,parent_reviews_raw=reviews_raw,scoped_raw=scoped_raw,
                proposed_raw=proposed_raw,draft_raw=(docs/'gentle-command-long-ledger-draft.json').read_bytes(),
                suite_raw=[(ROOT/'tests/fixtures'/name).read_bytes() for name,_,_ in SUITES],
                source_evidence=source_audit.inputs(),historical=original,
                current_raw=current_raw,current_reviews=reviews,draft=draft)


def inputs(draft=False):
    values = original_inputs(draft=draft)
    if not draft and len(json.loads(values['current_raw'])['cases']) > 35740:
        import friendly_command_gena_ledger_audit as gena
        complete = gena.inputs()
        values['actual_current_raw'] = values['current_raw']
        values['actual_current_reviews'] = values['current_reviews']
        values['gena_append'] = complete
        values['current_raw'] = complete['parent_raw']
        values['current_reviews'] = json.loads(complete['parent_reviews_raw'])
    return values


def inspect(v):
    assert sha(v['parent_raw'])==PARENT_SHA, 'exact original35704 parent ledger bytes'
    assert sha(v['parent_reviews_raw'])==REVIEWS_SHA, 'exact original517 parent review bytes'
    assert sha(v['scoped_raw'])==SCOPED_SHA, 'exact bounded long-ending review dispositions'
    assert sha(v['proposed_raw'])==PROPOSAL_SHA, 'exact original36-case long proposal'
    assert sha(v['draft_raw'])==DRAFT_SHA, 'unchanged original long draft metadata'
    assert [sha(raw) for raw in v['suite_raw']]==[digest for _,_,digest in SUITES], 'all three original private judgment fixtures'
    source_audit.inspect(v['source_evidence'])
    historical.inspect_historical(v['historical'])
    assert v['historical']['current_raw']==v['parent_raw'], 'historical35704 matches complete long parent'
    assert v['historical']['current_reviews']==json.loads(v['parent_reviews_raw']), 'historical517 reviews match complete long parent'
    parent, current = json.loads(v['parent_raw']), json.loads(v['current_raw'])
    suites = [json.loads(raw) for raw in v['suite_raw']]
    assert [len(s['cases']) for s in suites]==[25,8,3], 'complete original25novel8derived3 proposal scope'
    cases = [case for suite in suites for case in suite['cases']]
    proposal = json.loads(v['proposed_raw'])
    assert proposal['cases']==cases, 'every unchanged original private judgment in proposal'
    assert len(parent['cases'])==35704 and len(current['cases'])==35740, 'complete original parent and36-case append'
    assert current['cases'][:35704]==parent['cases'], 'every original parent case field and order'
    assert current['cases'][35704:]==cases, 'only exact25preauthored8novel3derived judgments appended'
    body = lambda raw:raw.split(b'"cases": [',1)[1].rsplit(b'\n  ]\n}',1)[0]
    assert body(v['current_raw']).startswith(body(v['parent_raw'])), 'every original serialized35704 case byte'
    sources = dict(parent['sources']); added = {}
    for suite in suites:
        for key,value in suite['sources'].items():
            assert key not in sources or sources[key]==value, 'unchanged overlapping source identities'
            sources[key]=value;added[key]=value
    assert proposal['sources']==added and current['sources']==sources, 'all original and only exact reviewed source citations'
    assert {k:value for k,value in current.items() if k not in ['cases','sources']}=={k:value for k,value in parent.items() if k not in ['cases','sources']}, 'original ledger metadata remains bounded'
    assert len({c['id'] for c in current['cases']})==35740, 'all unique stable current case IDs'
    counts = {kind:sum(j['verdict']==kind for c in current['cases'] for j in c['judgments']) for kind in ['required','forbidden']}
    assert counts=={'required':31452,'forbidden':4305}, 'complete current required forbidden counts'
    previous, active = json.loads(v['parent_reviews_raw']), v['current_reviews']
    new = json.loads(v['scoped_raw'])['entries']
    assert len(previous['entries'])==517 and len(active['entries'])==519, 'complete original517 and two long reviews'
    assert active['entries'][:517]==previous['entries'], 'every original manual review field and order'
    assert active['entries'][517:]==new and len(new)==2, 'only exact bounded long reviews appended'
    assert {k:value for k,value in active.items() if k!='entries'}=={k:value for k,value in previous.items() if k!='entries'}, 'original manual review metadata'
    source = json.loads(v['source_evidence']['source_raw'])
    assert [r['id'] for r in new]==source['ending_owner_ids']==['krdict:79266','krdict:79265'], 'both separate original long ending owners'
    for review in new:
        assert review['status']=='scoped' and review['remaining'] and review['checklist']==['COV-017da'], 'bounded structural long review scope'
        assert review['source_sha256']==digest(source_entry(source['owners'][review['id']])), 'complete original long inventory source digest'
        expected = [{'case':c['id'],'judgment':j['id']} for c in suites[0]['cases'] for j in c['judgments']
                    if c['id'].startswith('gentle-command-long-'+review['id'].split(':')[1]+'-sense-') and j['verdict']=='required']
        assert len(expected)==4 and review['judgments']==expected, 'all four original example groups per long owner'
    metadata = json.loads(v['draft_raw'])
    assert metadata['long25_authoring_precedes_runtime'] is True and metadata['novel8_authoring_precedes_runtime'] is False and metadata['other11novel_hypotheses_promoted'] is False, 'honest authoring and unjudged novel scope'
    result = dict(state='exact-long-command-append-and-scoped-reviews-passed',parent_cases=35704,
                active_cases=35740,added_cases=36,required=31452,forbidden=4305,
                parent_reviews=517,active_reviews=519,unreviewed=196,
                original25preauthored=True,novel8preauthored=False,other11rawnovel_promoted=False,
                actual_shared_promotion=not v['draft'],full_coverage_complete=False)
    if 'actual_current_raw' in v or 'actual_current_reviews' in v:
        import friendly_command_gena_ledger_audit as gena
        complete = v['gena_append']
        assert complete['current_raw'] == v['actual_current_raw'], 'mandatory complete current Gena ledger bytes'
        assert complete['current_reviews'] == v['actual_current_reviews'], 'mandatory complete current Gena review fields'
        assert complete['parent_raw'] == v['current_raw'], 'historical long matches exact Gena parent'
        assert sha(complete['parent_reviews_raw']) == gena.REVIEWS_SHA and json.loads(complete['parent_reviews_raw']) == v['current_reviews'], 'historical long reviews match exact Gena parent'
        checked = gena.inspect(complete)
        result.update(scope='historical-long35740-with-complete-current-Gena35764',
                      complete_current_cases=checked['current_cases'],complete_current_reviews=checked['current_reviews'],
                      complete_current_required=checked['required'],complete_current_forbidden=checked['forbidden'],
                      gena_added_cases=checked['added_cases'])
    else:
        result['scope'] = 'complete-evaluated-long35740'
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--draft',action='store_true')
    args = parser.parse_args()
    print(inspect(inputs(draft=args.draft)))
