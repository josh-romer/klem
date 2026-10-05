"""Verify complete broad stream pairs and finite compound additions."""
import argparse
import copy
import hashlib
from collections import Counter
from pathlib import Path

from well_doeda_audit import FIXTURE, ROOT, RULE, SOURCE, digest, read, sha

PRIOR = ROOT / 'docs/doeda-partial-origin-observations.json.gz'
REPORT = ROOT / 'docs/well-doeda-observations.json.gz'


def compare(before, after, location, changes):
    if before == after:
        return
    if isinstance(before, dict):
        assert isinstance(after, dict) and before.keys() == after.keys()
        if before.get('kind') == 'word':
            assert {k:v for k,v in before.items() if k not in {'analysis','dictionary'}} == {k:v for k,v in after.items() if k not in {'analysis','dictionary'}}
            assert before['analysis']['normalized'] == after['analysis']['normalized']
            old, new = before['analysis']['analyses'], after['analysis']['analyses']
            assert [a for a in new if RULE not in a['rules']] == old
            assert {k:v for k,v in before['dictionary'].items() if k not in {'lemmas','readings'}} == {k:v for k,v in after['dictionary'].items() if k not in {'lemmas','readings'}}
            slots = before['dictionary']['lemmas']
            assert [s for s in after['dictionary']['lemmas'] if s in slots] == slots
            for i, a in enumerate(new):
                if RULE not in a['rules']:
                    assert after['dictionary']['readings'][i] == before['dictionary']['readings'][old.index(a)]
                    continue
                assert a['lemmas'][:2] == [{'text':'잘','kind':'adverbial'},{'text':'되다','kind':'predicate'}]
                parent=copy.deepcopy(a)
                parent['lemmas']=[{'text':'잘되다','kind':'predicate'}]+parent['lemmas'][2:]
                parent['rules'].remove(RULE)
                assert parent in old
                owner=after['dictionary']['readings'][i]['lemmas'][1]
                assert next(e for e in owner['entries'] if e['id']=='krdict:48214')['status']=='incompatible'
                changes.append({'id':'well-doeda-broad-'+digest((after['analysis']['normalized'],a)),'surface':after['analysis']['normalized'],'analysis':a,'parent':parent,'reading':after['dictionary']['readings'][i],'location':location,'contextual_verdict':'unjudged','independent_review':'pending'})
            return
        for key in before:
            compare(before[key],after[key],dict(location,field=location.get('field',[])+[key]),changes)
    elif isinstance(before,list):
        assert isinstance(after,list) and len(before)==len(after)
        for i,(b,a) in enumerate(zip(before,after,strict=True)):
            compare(b,a,dict(location,field=location.get('field',[])+[i]),changes)
    else:
        assert before == after,(location,before,after)


def inspect(report):
    prior=read(PRIOR)
    assert report['schema_version']==1 and report['checklist']=='COV-022n'
    assert report['prior_sha256']==sha(PRIOR) and report['source_sha256']==sha(SOURCE)
    assert report['before_cli_sha256']==prior['cli_sha256']==read(SOURCE)['before_cli_sha256']
    assert report['dictionary_sha256']==prior['dictionary_sha256']
    assert report['fixture_sha256']==sha(FIXTURE)
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    assert len(report['comparisons'])==len(prior['comparisons'])==8
    counts=Counter();positions=set();changes=[]
    for pair in report['changed_record_pairs']:
        location=pair['location'];mode=pair['mode'];key=(mode,location['record'])
        assert key not in positions;positions.add(key);counts[mode]+=1
        assert pair['before']!=pair['after']
        assert pair['before']['span']==pair['after']['span']==location['span']
        compare(pair['before'],pair['after'],location,changes)
    for before,after in zip(prior['comparisons'],report['comparisons'],strict=True):
        for key in before.keys()-{'before_jsonl_sha256','after_jsonl_sha256','changed_records'}:
            assert before[key]==after[key]
        assert after['before_jsonl_sha256']==before['after_jsonl_sha256']
        assert after['changed_records']==counts[after['mode']]
        assert all(0<=index<after['records'] for mode,index in positions if mode==after['mode'])
        if not after['changed_records']:
            assert after['before_jsonl_sha256']==after['after_jsonl_sha256']
        source=Path(after['source'])
        if source.exists():assert sha(source)==after['source_sha256']
    assert sum(c['records'] for c in report['comparisons'])==1128312
    assert report['changes']==changes
    return len(positions),len({c['id'] for c in changes})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args()
    print('Verified broad frames and individual additions:',inspect(read(args.report)))
