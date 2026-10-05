"""Verify unchanged held-out gold, candidate counts and all raw word calls."""
import argparse
import hashlib
import json
from pathlib import Path

from nominal_si_audit import SOURCE
from well_doeda_audit import ROOT, read, sha

PRIOR=ROOT/'docs/well-doeda-packaged-corpora.json.gz'
REPORT=ROOT/'docs/nominal-si-corpora.json.gz'


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def inspect(report):
    prior,source=read(PRIOR),read(SOURCE)
    assert report['schema_version']==1 and report['checklist']=='COV-022o'
    assert report['previous_report_sha256']==sha(PRIOR)
    assert report['source_sha256']==sha(SOURCE)
    assert report['before_cli_sha256']==prior['cli_sha256']==source['before_cli_sha256']
    assert report['adapter_sha256']==prior['adapter_sha256']
    assert report['changed_words']=={} and report['candidate_changes']==[]
    assert report['after_words']==prior['after_words']
    words=report['after_words']
    assert len(words)==report['unique_surfaces']==32096
    assert report['before_word_stream_sha256']==report['after_word_stream_sha256']==prior['after_word_stream_sha256']
    assert report['after_word_stream_sha256']==digest(json.dumps(words,ensure_ascii=False,sort_keys=True))
    assert len(report['corpora'])==len(prior['corpora'])==4
    total=0
    for old,current in zip(prior['corpora'],report['corpora'],strict=True):
        for key in ['corpus','partition','source','source_sha256','converted_rows','report_lines','after_jsonl','after_report_sha256','after_candidate_counts']:
            assert current[key]==old[key],key
        assert current['before_report_sha256']==old['after_report_sha256']
        assert digest(current['after_jsonl'])==current['after_report_sha256']
        assert current['changed_gold_outcomes']==[] and current['changed_summary_fields']=={}
        rows=[json.loads(line) for line in current['after_jsonl'].splitlines()]
        counts=[len(words[r['surface']]['analyses']) for r in rows[1:]]
        assert counts==current['after_candidate_counts']
        assert len(rows)==current['report_lines']==current['converted_rows']+1
        assert rows[0]['mean_candidates']==sum(counts)/len(counts)
        assert rows[0]['p95_candidates']==sorted(counts)[len(counts)*95//100]
        assert rows[0]['max_candidates']==max(counts)
        path=ROOT/current['source']
        if path.exists():assert sha(path)==current['source_sha256']
        total+=len(rows)-1
    assert total==report['converted_rows']==66570
    assert digest(report['producer']['text'])==report['producer']['sha256']
    return total,len(words),0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args();print('Verified unchanged original gold/raw words:',inspect(read(args.report)))
