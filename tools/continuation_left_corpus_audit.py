"""Verify the frozen annotated continuation groups without rewriting gold."""
import argparse
import gzip
import json
from pathlib import Path
from continuation_left_compare import Audit

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true',required=True);p.parse_args()
    with gzip.open(ROOT/'docs/continuation-left-dictionary-corpora.json.gz','rt')as f:data=json.load(f)
    raw=json.loads((ROOT/'docs/continuation-left-corpora.json').read_text())
    sources={(c['corpus'],c['partition']):c for c in raw['corpora']}
    audit=Audit(None,None);counts={};total=0
    for corpus in data['corpora']:
        source=sources[(corpus['corpus'],corpus['partition'])]
        assert corpus['source']==source['source']and corpus['source_sha256']==source['source_sha256']
        cases=corpus['cases'];assert len(cases)==corpus['selected_gold_rows']
        matched={mode:0 for mode in ['all','headword','compatible']}
        for case in cases:
            total+=1;row=case['original_gold_row']
            assert any(h in ['내다','나다','나가다','버리다','치우다']for h in row['expected'][1:])
            sid,token_id=row['id'].split('/',1);sid=sid.removeprefix('id:')
            block=case['original_sentence_block']
            assert '# sent_id = '+sid+'\n'in block
            token=next(line.split('\t')for line in block.splitlines()if line.split('\t')[0]==token_id)
            assert token[1]==row['surface']
            audit.raw[row['surface']]=case['observations']['all']['after']
            for mode,observation in case['observations'].items():
                b,a=observation['before'],observation['after']
                audit.word(b,a,mode,[corpus['corpus'],corpus['partition'],row['id'],mode])
                hits=[[i for i,analysis in enumerate(w['analyses'])if [l['text']for l in analysis['lemmas']]==row['expected']]for w in [b,a]]
                assert hits[0]==observation['before_gold_indices']and hits[1]==observation['after_gold_indices']
                assert bool(hits[0])==bool(hits[1])
                matched[mode]+=bool(hits[1])
        counts[corpus['corpus']+'-'+corpus['partition']]=dict(rows=len(cases),matched_groups=matched)
    assert total==98
    print(json.dumps(dict(gold_rows=total,partitions=counts,all_original_gold_group_filter_memberships_preserved=True)),flush=True)
if __name__=='__main__':main()
