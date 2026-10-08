"""Independently bind original sources, complete Native entries and finite observations."""
import collections,gzip,hashlib,json,re,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from native_lmf import entry,verify_native_lmf
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda path:json.loads(gzip.decompress(Path(path).read_bytes()) if str(path).endswith('.gz') else Path(path).read_bytes())
def shape(path,expected):
    return ([v['text'] for v in path['lemmas']]==expected['lemmas'] and
            [v['kind'] for v in path['lemmas']]==expected['lemma_kinds'] and
            [v['form'] for v in path['morphemes']]==expected['morphemes'] and
            [v['kind'] for v in path['morphemes']]==expected['morpheme_kinds'] and
            'ending.additive_ppundeoreo' in path['rules'])
def inspect(source,closure,replay,boundary,fixture,cases):
    for capture in [source,closure,replay,boundary]:
        assert sha(capture['producer']['text'].encode())==capture['producer']['sha256'],'producer bytes'
        assert capture['inputs_unchanged'] is True,'frozen inputs'
    assert source['state']==closure['state']==replay['state']=='passed','source/replay terminal states'
    assert boundary['state']=='observed-proposals-match' and boundary['mismatches']==[],'finite proposal matches'
    assert set(source['sqlite_entries'])=={'krdict:74341','krdict:74021'},'original primary IDs'
    native=closure['complete_native_entries'];assert len(native)==len(closure['original_lmf'])==62,'complete Native scope'
    assert {i:entry(raw) for i,raw in closure['original_lmf'].items()}==native,'complete original Native fields'
    verify_native_lmf(closure['english_projection'],native)
    assert all(native[i]==v for i,v in source['sqlite_entries'].items()),'primary entries unchanged'
    groups=[];lines=[];targets=[];cursor=0
    for ident,value in sorted(source['sqlite_entries'].items()):
        assert len(value['senses'])==1 and value['senses'][0]['notes'],'original senses/notes'
        for sense in value['senses']:
            for index,original in enumerate(sense['examples']):
                groups.append({'source':ident,'sense':sense['id'],'index':index,'original':original})
                for line_index,text in enumerate(original):
                    lines.append(text)
                    for found in re.finditer(r'[가-힣]+뿐더러(?=$|[\s.,!?])',text):
                        targets.append({'source':ident,'sense':sense['id'],'group_index':index,'line_index':line_index,
                                        'surface':found.group(),'char_span':{'start':cursor+found.start(),'end':cursor+found.end()}})
                    cursor+=len(text)+1
    text='\n'.join(lines)+'\n'
    assert source['all_original_groups']==groups and len(groups)==10,'every original group/dialogue'
    assert source['targets']==targets and len(targets)==10 and source['input']==text,'original targets/input'
    assert len(cases)==10 and len({c['id'] for c in cases})==10,'ten individual original cases'
    for case,target in zip(cases,targets,strict=True):
        assert case['id']==f"additive-ppundeoreo-original-{target['source'].split(':')[1]}-{target['sense']}-{target['group_index']}"
        assert case['source_occurrence']==target and case['surface']==target['surface'],'source occurrence identity'
        assert case['contextual_verdict']=='unjudged' and case['independent_review']=='pending','context scope'
    keys=[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in source['runs']]==keys
    assert [(r['encoding'],r['mode']) for r in replay['runs']]==keys
    observed=[]
    for old,new in zip(source['runs'],replay['runs'],strict=True):
        encoded=unicodedata.normalize(old['encoding'],text).encode()
        assert sha(encoded)==old['input_sha256']==new['input_sha256'],'source Unicode input bytes'
        assert sha(old['jsonl'].encode())==old['sha256'] and sha(new['jsonl'].encode())==new['sha256'],'source output bytes'
        assert old['exit_code']==new['exit_code']==0
        earlier=list(map(json.loads,old['jsonl'].splitlines()));rows=list(map(json.loads,new['jsonl'].splitlines()))
        assert len(rows)==len(earlier)==old['records']==new['records'],'all original frames'
        position=0
        for a,b in zip(earlier,rows,strict=True):
            for key in ['surface','span','kind']:assert a[key]==b[key],'preserved token metadata'
            assert b['span']['start']==position and encoded[position:b['span']['end']].decode()==b['surface'],'exact UTF8 spans'
            position=b['span']['end']
            paths=lambda row:row['analysis']['analyses'] if row.get('analysis') else []
            key=lambda path:json.dumps(path,ensure_ascii=False,sort_keys=True)
            assert not(collections.Counter(map(key,paths(a)))-collections.Counter(map(key,paths(b)))),'prior raw paths'
        assert position==len(encoded),'complete original input'
        for case,target in zip(cases,targets,strict=True):
            span={k:len(unicodedata.normalize(old['encoding'],text[:v]).encode()) for k,v in target['char_span'].items()}
            row=next(r for r in rows if r['span']==span)
            matching=[a for a in row['analysis']['analyses'] if shape(a,case['expected'])]
            assert matching,'original whole-ending structure'
            observed.append({'target':target,'encoding':old['encoding'],'mode':old['mode'],'span':span,
                             'expected_shape':{k:v for k,v in case['expected'].items() if k!='required_rules'},
                             'matched':matching,'record':row,'contextual_verdict':'unjudged','independent_review':'pending'})
    assert observed==replay['observations'] and len(observed)==60,'all source observations'
    assert len(fixture['cases'])==36 and len({c['id'] for c in fixture['cases']})==36,'finite authored scope'
    assert [(r['encoding'],r['mode']) for r in boundary['runs']]==keys
    judgments=[];boundary_text=' '.join(dict.fromkeys(c['surface'] for c in fixture['cases']))
    for run in boundary['runs']:
        encoded=unicodedata.normalize(run['encoding'],boundary_text).encode()
        assert sha(encoded)==run['input_sha256'] and sha(run['jsonl'].encode())==run['sha256'],'boundary bytes'
        rows=list(map(json.loads,run['jsonl'].splitlines()));assert len(rows)==run['records'] and run['exit_code']==0
        by_word={r['analysis']['normalized']:r for r in rows if r.get('analysis')}
        for case in fixture['cases']:
            row=by_word[case['surface']];selected=[(i,a) for i,a in enumerate(row['analysis']['analyses']) if shape(a,case)]
            statuses=[row['dictionary']['readings'][i]['status'] for i,a in selected]
            present=bool(selected);assert present==case['expected_presence'][run['mode']],'authored structural presence'
            assert all(s==case['expected_status'] for s in statuses),'scoped Native status'
            judgments.append({'case_id':case['id'],'encoding':run['encoding'],'mode':run['mode'],'present':present,
                              'expected_present':case['expected_presence'][run['mode']],'statuses':statuses,
                              'expected_status':case['expected_status'],'proposal_matches_observation':True,
                              'record':row,'matched':[a for i,a in selected]})
    assert judgments==boundary['observations'] and len(judgments)==216,'all boundary observations'
    matched={v['id'] for o in replay['observations']+boundary['observations'] for l in o['record']['dictionary']['lemmas'] for v in l['entries']}
    assert sorted(matched)==closure['matched_owner_ids'] and len(matched)==60,'actual owner IDs'
    assert matched<=set(native)
    conditional=sum(c['proposal']=='conditional' for c in fixture['cases'])
    return {'original_groups':10,'source_observations':60,'authored_cases':36,'authored_observations':216,
            'matched_owners':60,'complete_native_entries':62,'conditional_authored_cases':conditional,
            'scope':'Finite isolated source/proposal verification only; context, broad/main/package and independent review remain separate.'}
def inputs():
    return [read(ROOT/'docs'/('additive-ppundeoreo-'+n+'.json.gz')) for n in ['source-discovery','owner-closure','source-replay','boundary-preflight']]+[
        read(ROOT/'tests/fixtures/additive-ppundeoreo-authored-boundaries.json'),
        read(ROOT/'tests/fixtures/additive-ppundeoreo-original-cases.json')]
if __name__=='__main__':print(inspect(*inputs()))
