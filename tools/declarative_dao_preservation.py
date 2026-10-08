"""Verify every captured dao addition and new spacing boundary against original source bytes."""
import copy,gzip,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(os.environ.get('KLEM_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT/'tools'))
from predicate_auxiliary_spacing_runtime import verify_segment
read=lambda name:json.loads(gzip.decompress((ROOT/name).read_bytes()))

def prior_paths(old,new):
    assert {k:v for k,v in old.items() if k not in ['analysis','dictionary','spacing','breakdowns']} == {k:v for k,v in new.items() if k not in ['analysis','dictionary','spacing','breakdowns']}
    if old.get('analysis') is None:assert old==new;return []
    a,b=old['analysis'],new['analysis'];assert a['normalized']==b['normalized']
    assert [p for p in b['analyses'] if p in a['analyses']]==a['analyses']
    od,nd=old['dictionary'],new['dictionary']
    assert {k:v for k,v in od.items() if k not in ['lemmas','readings']}=={k:v for k,v in nd.items() if k not in ['lemmas','readings']}
    assert all(m in nd['lemmas'] for m in od['lemmas'])
    for p in a['analyses']:
        i,j=a['analyses'].index(p),b['analyses'].index(p)
        assert od['readings'][i]==nd['readings'][j]
        if 'breakdowns' in old:assert old['breakdowns'][i]==new['breakdowns'][j]
    return [p for p in b['analyses'] if p not in a['analyses']]

def verify(report,baseline,inputs,native):
    assert report['state']=='draft-complete-broad-preservation-passed' and report['inputs_unchanged']
    assert len(report['comparisons'])==len(baseline['comparisons'])==8
    total=0;expected=[];expected_spacing=[]
    for run,oldrun in zip(report['comparisons'],baseline['comparisons'],strict=True):
        for key in ['source','source_sha256','mode','records']:assert run[key]==oldrun[key]
        assert run['before_jsonl_sha256']==oldrun['after_jsonl_sha256']
        assert run['exit_codes']==[0,0] and run['original_bytes_conserved']
        original=inputs['sources'][run['source']]['text'].encode();assert hashlib.sha256(original).hexdigest()==run['source_sha256'];total+=run['records']
        previous=0
        for changed in run['changed_frames']:
            ordinal=changed['record'];assert previous<ordinal<=run['records'];previous=ordinal
            old,new=changed['before'],changed['after'];span=new['span'];assert original[span['start']:span['end']].decode()==new['surface']
            left=original.rfind(b'\n',0,span['start'])+1;right=original.find(b'\n',span['end']);right=len(original) if right<0 else right
            context=original[left:right].decode();assert changed['complete_original_line']==context
            additions=prior_paths(old,new);assert changed['added_paths']==len(additions)
            for p in additions:
                assert p['rules'].count('ending.declarative_dao')==1
                inverse=copy.deepcopy(p);inverse['rules'].remove('ending.declarative_dao');m=inverse['morphemes'][-1];assert m['kind']=='ending'
                m['form']={'다오':'다고','는다오':'는다고'}[m['form']]
                parent=new['analysis']['normalized'][:-1]+'고';assert inverse in report['actual_prior_companions'][parent]['analyses']
                index=new['analysis']['analyses'].index(p);owners=[next(m for m in new['dictionary']['lemmas'] if m['lemma']==lemma) for lemma in p['lemmas']]
                for member in owners:
                    for entry in member['entries']:
                        value=native[entry['id']];assert (entry['headword'],entry['pos'])==(value['headword'],value['pos'])
                row={'location':'word','surface':new['surface'],'span':span,'analysis':p,'dictionary_assessment':new['dictionary']['readings'][index],'dictionary_owners':owners,'parent_surface':parent,'exact_parent':inverse,'contextual_verdict':'unjudged','independent_review':'pending'}
                ident=hashlib.sha256(json.dumps([run['source_sha256'],run['mode'],ordinal,row],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
                expected.append({'id':'declarative-dao-broad-'+ident,'source':run['source'],'source_sha256':run['source_sha256'],'mode':run['mode'],'record':ordinal,'complete_original_line':context,**row})
            added=[]
            if 'spacing' in old:
                key=lambda h:(h['rule'],h['spaced'],tuple(h['inserted_at']))
                oldkeys=[key(h) for h in old['spacing']['alternatives']]
                assert [key(h) for h in new['spacing']['alternatives'] if key(h) in oldkeys]==oldkeys
                for hypothesis in old['spacing']['alternatives']:
                    now=next(h for h in new['spacing']['alternatives'] if key(h)==key(hypothesis))
                    # This batch's captured prior options are wholly unchanged;
                    # future segment additions need explicit individual evidence.
                    assert hypothesis==now
                added=[h for h in new['spacing']['alternatives'] if key(h) not in oldkeys]
                for h in added:
                    assert ''.join(s['surface'] for s in h['records'])==new['surface']
                    assert h['spaced']==' '.join(s['surface'] for s in h['records']) and h['inserted_at']==[s['span']['start'] for s in h['records'][1:]]
                    pieces=h['records']+h.get('joined_contexts',[])
                    assert any('ending.declarative_dao' in p['rules'] for s in pieces for p in s['analysis']['analyses'])
                    for s in pieces:verify_segment(s,original.decode(),report['independent_spacing_replay'])
                    row={'location':'word','hypothesis':h,'original_surface':new['surface'],'original_span':span}
                    ident=hashlib.sha256(json.dumps([run['source_sha256'],run['mode'],ordinal,row],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
                    expected_spacing.append({'id':'declarative-dao-broad-spacing-'+ident,'source':run['source'],'source_sha256':run['source_sha256'],'mode':run['mode'],'record':ordinal,'complete_original_line':context,'contextual_verdict':'unjudged','independent_review':'pending',**row})
            assert changed['added_spacing_options']==len(added)
    assert total==1128312 and report['individual_additions']==expected and len(expected)==27
    assert report['individual_spacing_additions']==expected_spacing and len(expected_spacing)==2
    assert len({r['id'] for r in expected+expected_spacing})==29
    return {'frames':total,'individual_path_observations':27,'individual_spacing_observations':2,'contextual_review_complete':False}

def values():
    return (read('docs/declarative-dao-broad-final.json.gz'),read('docs/possessive-bound-noun-broad-final.json.gz'),read('docs/reported-deoni-broad-inputs.json.gz'),read('docs/declarative-dao-native-revision2.json.gz')['complete_native_entries'])
if __name__=='__main__':print(verify(*values()))
