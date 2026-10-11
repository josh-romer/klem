"""Verify the exact finite Gena append while preserving every prior judgment."""
import argparse
import gzip
import json
import sys
from pathlib import Path

# The external draft directory also contains older preserved helper sources.
# Prefer the current worktree dependencies while this auditor is prepared there.
if Path(__file__).resolve().parent.name=='willingness-question-prepared':
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'friendly-command-gena/tools'))

import friendly_command_gena_source_audit as source
import friendly_command_gena_revision as revision
import gentle_command_long_ledger_audit as historical
from review_inventory import digest, source_entry

ROOT=revision.ROOT
sha=revision.sha
PARENT_SHA='c8696d8f241550f089857bb238daab7d1428967b9bd4834705d96c8b334ee2ea'
REVIEWS_SHA='c47411d0e832d2220ade356cb956ed778852eaee9da90dba3f091e15c6557a12'
QUEUE_SHA='251b600a9d61baf8982a221c8b1729b929b768ef9220aae5bb8c1eff0bd04190'
PROPOSAL_SHA='da4ef8fe8cc2a4f1f1ae481dd1bd37e73924697b85f48c210d5bd20f04ff6ef2'
SCOPED_SHA='f32d6387a4876e2842a54c015f408f729a3c42727af07e70687c9ecff5921220'
DRAFT_SHA='fd2c382140eb816148de1c89b99850062737df2c124ac9f31a8b03a8bb26c6a6'


def inputs(draft=False,prepared=None):
    docs=ROOT/'docs'
    if prepared is not None:
        directory=Path(prepared)
        read=lambda name:(directory/name).read_bytes()
    elif (docs/'friendly-command-gena-ledger-draft.json').exists():
        names={'draft.json':'friendly-command-gena-ledger-draft.json',
               'proposed-cases.json':'friendly-command-gena-ledger-proposed-cases.json',
               'proposed-scoped-reviews.json':'friendly-command-gena-scoped-reviews.json'}
        read=lambda name:(docs/names.get(name,'friendly-command-gena-'+name)).read_bytes()
    else:
        directory=Path(__file__).resolve().parent/'friendly-command-gena-promotion-draft'
        read=lambda name:(directory/name).read_bytes()
    parent_raw=gzip.decompress(read('parent-validity.json.gz'))
    reviews_raw=gzip.decompress(read('parent-inventory-reviews.json.gz'))
    proposed_raw=read('proposed-cases.json');scoped_raw=read('proposed-scoped-reviews.json')
    current_raw=(ROOT/'tests/fixtures/validity.json').read_bytes()
    active_reviews=json.loads((docs/'inventory-reviews.json').read_bytes())
    if draft:
        candidate=json.loads(parent_raw);proposal=json.loads(proposed_raw)
        candidate['cases'].extend(proposal['cases']);candidate['sources'].update(proposal['sources'])
        current_raw=(json.dumps(candidate,ensure_ascii=False,indent=2)+'\n').encode()
        active_reviews=json.loads(reviews_raw);active_reviews['entries'].extend(json.loads(scoped_raw)['entries'])
    previous=historical.original_inputs()
    previous['current_raw']=parent_raw;previous['current_reviews']=json.loads(reviews_raw)
    return dict(parent_raw=parent_raw,parent_reviews_raw=reviews_raw,
                parent_queue_raw=gzip.decompress(read('parent-inventory-review-queue.json.gz')),
                proposed_raw=proposed_raw,scoped_raw=scoped_raw,draft_raw=read('draft.json'),
                original_suite_raw=(ROOT/'tests/fixtures/friendly-command-gena-validity.json').read_bytes(),
                source=source.inputs(),historical=previous,current_raw=current_raw,
                current_reviews=active_reviews,draft=draft)


def inspect(v):
    assert sha(v['parent_raw'])==PARENT_SHA, 'exact original35740 parent ledger bytes'
    assert sha(v['parent_reviews_raw'])==REVIEWS_SHA, 'exact original519 manual review bytes'
    assert sha(v['parent_queue_raw'])==QUEUE_SHA, 'exact original715 source queue bytes'
    assert sha(v['proposed_raw'])==PROPOSAL_SHA, 'exact unchanged24-case Gena proposal'
    assert sha(v['scoped_raw'])==SCOPED_SHA, 'exact single bounded Gena review'
    assert sha(v['draft_raw'])==DRAFT_SHA, 'original honest Gena draft metadata'
    assert sha(v['original_suite_raw'])==source.SUITE_SHA, 'original preauthored Gena judgments'
    source.inspect(v['source']);historical.inspect(v['historical'])
    assert v['historical']['current_raw']==v['parent_raw'] and v['historical']['current_reviews']==json.loads(v['parent_reviews_raw']), 'unchanged complete historical long parent'
    parent=json.loads(v['parent_raw']);current=json.loads(v['current_raw']);suite=json.loads(v['original_suite_raw']);proposal=json.loads(v['proposed_raw'])
    assert len(parent['cases'])==35740 and len(current['cases'])==35764, 'complete35740 parent plus24 cases'
    assert proposal['cases']==suite['cases'] and len(suite['cases'])==24, 'every unchanged preauthored case and judgment'
    assert current['cases'][:35740]==parent['cases'], 'every old case field and relative order'
    assert current['cases'][35740:]==suite['cases'], 'only exact24 preauthored cases appended'
    body=lambda raw:raw.split(b'"cases": [',1)[1].rsplit(b'\n  ]\n}',1)[0]
    assert body(v['current_raw']).startswith(body(v['parent_raw'])), 'every old serialized case byte'
    expected=dict(parent['sources'])
    for key,url in suite['sources'].items():
        assert key not in expected or expected[key]==url, 'old source declaration preserved'
        expected[key]=url
    assert current['sources']==expected and proposal['sources']==suite['sources'], 'only exact attributed source declarations'
    assert {k:x for k,x in current.items() if k not in ('cases','sources')}=={k:x for k,x in parent.items() if k not in ('cases','sources')}, 'original ledger metadata unchanged'
    assert len({c['id'] for c in current['cases']})==35764, 'all stable unique case IDs'
    counts={kind:sum(j['verdict']==kind for c in current['cases'] for j in c['judgments']) for kind in ['required','forbidden']}
    assert counts==dict(required=31469,forbidden=4312), 'complete required forbidden counts'
    old=json.loads(v['parent_reviews_raw']);active=v['current_reviews'];new=json.loads(v['scoped_raw'])['entries']
    assert len(old['entries'])==519 and len(active['entries'])==520, 'complete519 reviews plus one bounded owner'
    assert active['entries'][:519]==old['entries'], 'every old manual review field and relative order'
    assert active['entries'][519:]==new and len(new)==1, 'only exact bounded Gena review appended'
    assert {k:x for k,x in active.items() if k!='entries'}=={k:x for k,x in old.items() if k!='entries'}, 'old review metadata unchanged'
    review=new[0];author=v['source']['source'];owner=author['owners']['krdict:66968']
    assert review['id']=='krdict:66968' and review['status']=='scoped' and review['checklist']==['COV-017db'] and review['remaining'], 'finite own-owner review scope'
    assert review['source_sha256']==digest(source_entry(owner)), 'complete own source digest'
    targets=[dict(case=c['id'],judgment=j['id']) for c in suite['cases'][:4] for j in c['judgments']]
    assert len(targets)==4 and review['judgments']==targets, 'all four original example groups only'
    queue=json.loads(v['parent_queue_raw']);queued=next(r for r in queue['entries'] if r['source']['id']==review['id'])
    assert queued['source_sha256']==review['source_sha256'] and queued['review']['status']=='unreviewed', 'own original unreviewed source preserved'
    draft=json.loads(v['draft_raw'])
    assert draft['original_case_authoring_precedes_runtime'] and draft['review_draft_authored_after_runtime'] and draft['all_five_historical_words_eighteen_broad_contexts_remain_unjudged'], 'honest authoring and unjudged hypotheses preserved'
    return dict(parent_cases=35740,current_cases=35764,added_cases=24,required=31469,forbidden=4312,
                parent_reviews=519,current_reviews=520,source_example_groups=4,
                historical_and_broad_hypotheses_promoted=False,actual_shared_promotion=not v['draft'],
                context_register_independent_review='pending',full_coverage_complete=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--draft',action='store_true')
    args=parser.parse_args();print(inspect(inputs(draft=args.draft)))
