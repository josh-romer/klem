"""Verify eight unchanged broad streams against their pinned before receipt."""
import argparse
import hashlib
from pathlib import Path

from nominal_hwa_hada_audit import FIXTURE, SOURCE
from well_doeda_audit import ROOT, read, sha

REPORT=ROOT/'docs/nominal-hwa-hada-observations.json.gz'
PRIOR=ROOT/'docs/nominal-hwa-packaged-observations.json.gz'


def inspect(report):
    prior,source=read(PRIOR),read(SOURCE)
    assert report['schema_version']==1 and report['checklist']=='COV-022q'
    assert report['prior_sha256']==sha(PRIOR) and report['source_sha256']==sha(SOURCE)
    assert report['fixture_sha256']==sha(FIXTURE)
    assert report['before_cli_sha256']==prior['cli_sha256']==source['before_cli_sha256']
    assert report['dictionary_sha256']==prior['dictionary_sha256']==source['dictionary_sha256']
    assert report['changed_record_pairs']==[]
    assert len(report['comparisons'])==len(prior['comparisons'])==8
    for old,new in zip(prior['comparisons'],report['comparisons'],strict=True):
        assert {k:v for k,v in old.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}=={k:v for k,v in new.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}
        assert new['before_jsonl_sha256']==new['after_jsonl_sha256']==old['after_jsonl_sha256']
        assert new['changed_records']==0
        path=Path(new['source'])
        if path.exists():assert sha(path)==new['source_sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    assert sum(c['records'] for c in report['comparisons'])==1128312
    return 1128312,0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args();print('Verified full unchanged broad streams:',inspect(read(args.report)))
