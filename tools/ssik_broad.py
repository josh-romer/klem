"""Verify every changed full-stream frame against original records and -씩 parents."""
import argparse
import hashlib
from pathlib import Path

from ssik_audit import inspect as inspect_source
from ssik_comparison import parent_for

FIXTURE = Path(__file__).resolve().parents[1] / "tests/fixtures/ssik-sources.json"
SOURCE = Path(__file__).resolve().parents[1] / "docs/ssik-preflight.json.gz"
from well_doeda_audit import ROOT, digest, read, sha

PRIOR=ROOT/'docs/hada-remaining-packaged-observations.json.gz'
REPORT=ROOT/'docs/ssik-observations.json.gz'


def inspect(report):
    prior,source=read(PRIOR),read(SOURCE);inspect_source()
    assert report['schema_version']==1 and report['checklist']=='COV-022u'
    assert report['prior_sha256']==sha(PRIOR) and report['source_sha256']==sha(SOURCE)
    assert report['fixture_sha256']==sha(FIXTURE)
    assert report['before_cli_sha256']==prior['cli_sha256']==source['before_cli_sha256']
    assert report['dictionary_sha256']==prior['dictionary_sha256']==source['dictionary_sha256']
    assert len(report['comparisons'])==len(prior['comparisons'])==8
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    changes=[]
    spacing_changes=[]
    component_capture=report['spacing_component_preflight']
    for key in ['before_cli_sha256','cli_sha256','dictionary_sha256']:
        assert component_capture[key] == report[key]
    assert hashlib.sha256(component_capture['producer']['text'].encode()).hexdigest() == component_capture['producer']['sha256']
    components=component_capture['components']
    for word,capture in components.items():
        for key in ['before','after']:
            import json
            rows=[json.loads(line) for line in capture[key]['jsonl'].splitlines()]
            assert rows == [capture[key]['record']]
            assert rows[0]['surface'] == word
            assert rows[0]['span'] == {'start':0,'end':len(word.encode())}
        assert capture['api']['records'] == [capture['after']['record']]
    raw_parents={}
    for pair in report['changed_record_pairs']:
        if pair['mode'].endswith('raw'):
            word=pair['before']['analysis']['normalized']
            paths=pair['before']['analysis']['analyses']
            if word in raw_parents: assert raw_parents[word] == paths
            raw_parents[word]=paths
    for old,new in zip(prior['comparisons'],report['comparisons'],strict=True):
        assert {k:v for k,v in old.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}=={k:v for k,v in new.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}
        assert new['before_jsonl_sha256']==old['after_jsonl_sha256']
        pairs=[p for p in report['changed_record_pairs'] if p['mode']==new['mode']]
        assert len(pairs)==new['changed_records']
        assert len({p['location']['record'] for p in pairs})==len(pairs)
        path=Path(new['source']);text=None
        if path.exists():
            assert sha(path)==new['source_sha256'];text=path.read_bytes()
        for pair in pairs:
            b,a=pair['before'],pair['after'];location=pair['location']
            assert location['mode']==new['mode'] and 0<=location['record']<new['records']
            assert {k:v for k,v in b.items() if k not in ['analysis','dictionary','spacing']}=={k:v for k,v in a.items() if k not in ['analysis','dictionary','spacing']}
            assert location['span']==a['span']
            if text is not None:
                span=a['span'];assert text[span['start']:span['end']].decode()==a['surface']
                assert location['context']==text[max(0,span['start']-120):min(len(text),span['end']+120)].decode(errors='replace')
            word=a['analysis']['normalized'];old_paths=b['analysis']['analyses'];new_paths=a['analysis']['analyses']
            assert {k:v for k,v in b['analysis'].items() if k!='analyses'}=={k:v for k,v in a['analysis'].items() if k!='analyses'}
            assert [p for p in new_paths if p in old_paths]==old_paths
            assert {k:v for k,v in b['dictionary'].items() if k not in ['lemmas','readings']}=={k:v for k,v in a['dictionary'].items() if k not in ['lemmas','readings']}
            old_lemmas=b['dictionary']['lemmas'];old_keys=[l['lemma'] for l in old_lemmas]
            retained=[l for l in a['dictionary']['lemmas'] if l['lemma'] in old_keys]
            assert [l['lemma'] for l in retained]==old_keys
            assert retained == old_lemmas
            for index,analysis in enumerate(new_paths):
                reading=a['dictionary']['readings'][index]
                if analysis in old_paths:
                    assert reading==b['dictionary']['readings'][old_paths.index(analysis)];continue
                parent,quantity_index=parent_for(analysis,word,raw_parents[word])
                changes.append({'id':'ssik-stream-'+digest([new['mode'],location['record'],word,analysis]),'mode':new['mode'],'location':location,'surface':word,'analysis':analysis,'parent':parent,'quantity_morpheme_index':quantity_index,'parent_retained_in_filter':parent in old_paths,'source_entry':'krdict:72043','source_sense_ids':['1','2'],'reading':reading,'contextual_verdict':'unjudged','independent_review':'pending'})
            if b.get('spacing') != a.get('spacing'):
                bs,ns=b['spacing'],a['spacing']
                assert {k:v for k,v in bs.items() if k not in ['alternatives','segment_probes']} == {k:v for k,v in ns.items() if k not in ['alternatives','segment_probes']}
                assert ns['segment_probes'] >= bs['segment_probes']
                assert [alt for alt in ns['alternatives'] if alt in bs['alternatives']] == bs['alternatives']
                for alt in ns['alternatives']:
                    if alt in bs['alternatives']:continue
                    left,right=alt['records']
                    assert left['surface']+right['surface'] == a['surface']
                    assert alt['spaced'] == left['surface']+' '+right['surface']
                    boundary=a['span']['start']+len(left['surface'].encode())
                    assert alt['inserted_at'] == [boundary]
                    assert left['span']=={'start':a['span']['start'],'end':boundary}
                    assert right['span']=={'start':boundary,'end':a['span']['end']}
                    left_parents=[]
                    for segment in [left,right]:
                        capture=components[segment['surface']]
                        current=capture['after']['record']
                        original=capture['before']['record']['analysis']['analyses']
                        assert {k:v for k,v in segment['analysis'].items() if k!='analyses'} == {k:v for k,v in current['analysis'].items() if k!='analyses'}
                        assert len(segment['breakdowns']) == len(segment['analysis']['analyses'])
                        for i,path in enumerate(segment['analysis']['analyses']):
                            index=current['analysis']['analyses'].index(path)
                            assert segment['dictionary']['readings'][i] == current['dictionary']['readings'][index]
                            assert segment['breakdowns'][i] == capture['api']['breakdowns'][0][index]
                            if segment is left:
                                parent,quantity_index=parent_for(path,segment['surface'],original)
                                left_parents.append({'analysis':path,'parent':parent,'quantity_morpheme_index':quantity_index})
                            else:assert path in original
                        assert segment['dictionary']['source'] == current['dictionary']['source']
                        assert segment['dictionary']['fingerprint'] == current['dictionary']['fingerprint']
                        for lemma in segment['dictionary']['lemmas']:assert lemma in current['dictionary']['lemmas']
                    spacing_changes.append({'id':'ssik-spacing-'+digest([new['mode'],location['record'],alt]),'mode':new['mode'],'location':location,'original_surface':a['surface'],'alternative':alt,'left_parents':left_parents,'source_entry':'krdict:72043','contextual_verdict':'unjudged','independent_review':'pending'})
        assert (new['before_jsonl_sha256']==new['after_jsonl_sha256'])==(not pairs)
    assert sum(c['records'] for c in report['comparisons'])==1128312
    if 'candidate_changes' in report:assert report['candidate_changes']==changes
    if 'spacing_changes' in report:assert report['spacing_changes']==spacing_changes
    return changes,spacing_changes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true',required=True);p.add_argument('--report',type=Path,default=REPORT);a=p.parse_args()
    changes,spacing=inspect(read(a.report))
    print('Verified 1128312 original frames;',len(changes),'individually parent-attributed additions;',len(spacing),'new optional spacing alternatives')
