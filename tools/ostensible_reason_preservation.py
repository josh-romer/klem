"""Independently verify complete unchanged broad, gold and historical captures."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def sha(raw):return hashlib.sha256(raw).hexdigest()

def producer(report):
    assert sha(report['producer']['text'].encode())==report['producer']['sha256']
    assert report['inputs_unchanged'] is True
    # External executable/data paths are historical capture identities.
    # Repository helpers remain independently bound in every environment.
    for name,h in report['frozen_inputs'].items():
        prefix='/home/josh/projects/klem/'
        relative=name.removeprefix(prefix) if name.startswith(prefix) else None
        if relative and relative.startswith(('tools/','examples/','docs/')):
            assert sha((ROOT/relative).read_bytes())==h,(name,'changed captured helper')
    assert report['before_cli_sha256'] in report['frozen_inputs'].values()
    assert report['cli_sha256'] in report['frozen_inputs'].values()

def inspect(broad,corpus,history):
    for report in [broad,corpus,history]:producer(report)
    assert len({r['before_cli_sha256'] for r in [broad,corpus,history]})==1
    assert len({r['cli_sha256'] for r in [broad,corpus,history]})==1
    previous=read(ROOT/'docs/declarative-contrast-prototype-broad.json.gz')
    assert broad['prior_capture_sha256']==sha((ROOT/'docs/declarative-contrast-prototype-broad.json.gz').read_bytes())
    assert len(broad['comparisons'])==len(previous['comparisons'])==8
    assert broad['individual_additions']==[]
    frames=0
    for old,new in zip(previous['comparisons'],broad['comparisons'],strict=True):
        for key in ['source','source_sha256','mode','records']:assert old[key]==new[key],key
        assert new['exit_codes']==[0,0] and new['changed_frames']==[]
        assert new['original_bytes_conserved'] is True and new['baseline_matches_previous_capture'] is True
        assert new['before_jsonl_sha256']==new['after_jsonl_sha256']==new['previous_capture_after_sha256']==old['after_jsonl_sha256']
        local=ROOT/new['source'].removeprefix('/home/josh/projects/klem/')
        if local.exists():assert sha(local.read_bytes())==new['source_sha256']
        frames+=new['records']
    assert frames==1128312
    previous=read(ROOT/'docs/declarative-contrast-prototype-corpora.json.gz')
    assert corpus['previous_report_sha256']==sha((ROOT/'docs/declarative-contrast-prototype-corpora.json.gz').read_bytes())
    assert corpus['before_words']==corpus['after_words']==previous['after_words']
    assert len(corpus['after_words'])==corpus['unique_surfaces']==32096
    assert digest(corpus['before_words'])==digest(corpus['after_words'])==corpus['before_words_sha256']==corpus['after_words_sha256']
    assert corpus['changed_words']=={} and corpus['candidate_changes']==[]
    assert len(corpus['corpora'])==len(previous['corpora'])==4
    total=0
    for old,new in zip(previous['corpora'],corpus['corpora'],strict=True):
        for key in ['corpus','partition','source','source_sha256','report_lines','original_source_text','original_converted_rows','original_converted_rows_sha256']:
            assert old[key]==new[key],key
        assert sha(new['original_source_text'].encode())==new['source_sha256']
        local=ROOT/new['source']
        if local.exists():assert local.read_text()==new['original_source_text']
        assert digest(new['original_converted_rows'])==new['original_converted_rows_sha256']
        assert len(new['comparisons'])==len(new['original_converted_rows'])==new['report_lines']-1
        assert new['changed_gold_outcomes']==[]
        assert new['before_summary']==new['after_summary']==old['after_summary']
        for oldrow,row,gold in zip(old['comparisons'],new['comparisons'],new['original_converted_rows'],strict=True):
            for key in ['id','surface','expected']:assert row[key]==oldrow[key]==gold[key]
            assert row['before']==row['after']==oldrow['after']
            assert row['after']['candidates']==len(corpus['after_words'][row['surface']]['analyses'])
        total+=len(new['comparisons'])
    assert total==corpus['converted_rows']==66570
    prior=read(ROOT/'docs/declarative-contrast-prototype-legacy-history.json')
    expected=dict(prior['source_files_sha256'])
    for name in ['tests/fixtures/declarative-contrast-original-cases.json','tests/fixtures/declarative-contrast-boundary-before.json']:
        expected[name]=sha((ROOT/name).read_bytes())
    assert history['source_files_sha256']==expected and len(expected)==49
    origins={}
    fields={'before_words','before_analyses','source_before_analyses','source_cohort_before_analyses'}
    def add(surface,name,pointer):
        item={'source':name,'source_sha256':expected[name],'pointer':pointer}
        if item not in origins.setdefault(surface,[]):origins[surface].append(item)
    def visit(value,name,pointer=''):
        if isinstance(value,dict):
            if isinstance(value.get('surface'),str) and isinstance(value.get('before'),dict) and 'analyses' in value['before']:
                add(value['surface'],name,pointer+'/before')
            for key,item in value.items():
                at=pointer+'/'+key
                if key in fields and isinstance(item,dict):
                    for surface in item:add(surface,name,at+'/'+surface)
                else:visit(item,name,at)
        elif isinstance(value,list):
            for i,item in enumerate(value):visit(item,name,pointer+'/'+str(i))
    for name,h in expected.items():
        assert sha((ROOT/name).read_bytes())==h
        visit(read(ROOT/name),name)
    assert history['origins']==origins and len(origins)==history['surfaces']==21341
    assert set(history['before_words'])==set(history['after_words'])==set(origins)
    assert history['before_words']==history['after_words']
    assert digest(history['before_words'])==digest(history['after_words'])==history['before_words_sha256']==history['after_words_sha256']
    assert history['changes']=={} and history['individual_additions']==[]
    assert history['changed_words']==history['added_paths']==0
    return {'broad_frames':frames,'gold_rows':total,'corpus_words':32096,'legacy_archives':49,'legacy_words':21341,
            'all_streams_and_candidates_unchanged':True,'new_broad_corpus_history_paths':0,
            'scope':'Exact unchanged observed cohorts; no coverage, precision or contextual claim for unseen compositions.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();assert not args.output.exists()
    paths=[ROOT/'docs'/('ostensible-reason-prototype-'+name+'.json.gz') for name in ['broad','corpora','legacy-history']]
    reports=list(map(read,paths));result=inspect(*reports)
    report={'schema_version':1,'state':'passed','derived':result,'captures_sha256':{str(p):sha(p.read_bytes()) for p in paths},
            'producer':{'text':Path(__file__).read_text(),'sha256':sha(Path(__file__).read_bytes())}}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(result,flush=True)

if __name__=='__main__':main()
