"""Verify independent direct/nested -화하다 sources, parents and dictionary evidence."""
import argparse
import copy
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from native_lmf import verify_native_lmf
from well_doeda_audit import MODES, ROOT, digest, read, sha, word_records

SOURCE=ROOT/'docs/nominal-hwa-hada-preflight.json.gz'
FIXTURE=ROOT/'tests/fixtures/nominal-hwa-hada-sources.json'
LMF=ROOT/'tests/fixtures/krdict-nominal-hwa-hada.json'
REPORT=ROOT/'docs/nominal-hwa-hada-diagnostics.json.gz'
RULE='suffix.verb.hada'


def licenses(source):
    native=source['complete_native_entries'];direct=[];nested=[]
    for f in source['families']:
        noun={o for i in f['whole_nominal_ids'] if native[i]['pos']=='명사' for o in native[i]['origins']}
        origins={o.removesuffix('하다') for i in f['whole_hada_ids'] if native[i]['pos']=='동사' for o in native[i]['origins'] if o.endswith('化하다')}
        assert origins and origins<=noun
        direct.append(f['head'])
        bases={o for i in f['base_ids'] if native[i]['pos']=='명사' for o in native[i]['origins']}
        split={o.removesuffix('化하다') for i in f['whole_hada_ids'] for o in native[i]['origins']}
        deep=bool(bases) and split<=bases and f['nominal_supported']
        assert f['verbal_supported']==deep
        if deep:nested.append(f['base'])
    return direct,nested


def inspect_source(source):
    assert source['schema_version']==1 and source['checklist']=='COV-022q'
    assert source['contextual_verdict']=='unjudged' and source['independent_review']=='pending'
    assert source['before_cli_sha256']==read(ROOT/'docs/nominal-hwa-packaged-checks.json.gz')['cli_sha256']
    assert source['previous_source_sha256']==sha(ROOT/'docs/nominal-hwa-preflight.json.gz')
    assert source['previous_package_sha256']==sha(ROOT/'docs/nominal-hwa-packaged-checks.json.gz')
    native=source['complete_native_entries'];assert len(native)==165
    hada=native['krdict:88475'];assert (hada['headword'],hada['pos'])==('-하다','접사')
    assert len(hada['senses'])==6 and hada['senses'][0]['notes']==['일부 명사 뒤에 붙는다.']
    assert source['lmf_sha256']==sha(LMF);verify_native_lmf(read(LMF),native)
    verify_native_lmf(read(ROOT/'tests/fixtures/krdict-hada-suffix-labels.json'),{'krdict:88475':hada})
    direct,nested=licenses(source)
    assert len(direct)==28 and len(nested)==22 and len(set(direct))==28
    fixture=read(FIXTURE);assert fixture['source_sha256']==sha(SOURCE)
    for field in ['families','complete_native_entries','corpora']:assert fixture[field]==source[field]
    assert fixture['direct_nominal_heads']==direct and fixture['nested_bases']==nested
    assert len(source['words'])==len(set(source['words']))==562
    assert source['input']==' '.join(source['words']) and set(source['before'])==set(MODES)
    for mode,run in source['before'].items():
        assert run['exit_code']==0 and hashlib.sha256(run['jsonl'].encode()).hexdigest()==run['sha256']
        records,words=word_records(run['jsonl']);assert set(words)==set(source['words'])
        assert ''.join(r['surface'] for r in records)==source['input']
        assert all(RULE not in a['rules'] for r in words.values() for a in r['analysis']['analyses'])
        if mode=='raw':assert fixture['before_analyses']=={w:r['analysis'] for w,r in words.items()}
    cases=fixture['cases'];assert len(cases)==len({c['id'] for c in cases})==1154
    assert sum(c['judgments'][0]['verdict']=='required' for c in cases)==1136
    ledger=read(ROOT/'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('hwa-hada-')]==cases
    assert ledger['sources']['nominal-hwa-hada-krdict']==hada['url']
    parents={p['case_id']:p for p in fixture['required_parents']};assert len(parents)==1136
    for case in cases:
        j=case['judgments'][0];value={k:v for k,v in j.items() if k not in ['id','source']}
        ident='hwa-hada-'+hashlib.sha256(json.dumps([case['surface'],value],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
        assert case['id']==ident and j['id']==ident+'-structure'
        assert j['source']=='nominal-hwa-hada-krdict' and RULE in j['required_rules']
        if j['verdict']!='required':continue
        p=parents[ident];assert p['surface']==case['surface']
        old=fixture['before_analyses'][case['surface']]['analyses'];assert p['before_parent'] in old
        nested_path=j['morphemes'][0]=='화';base=j['lemmas'][0]
        assert base in (nested if nested_path else direct) and j['lemma_kinds'][0]=='nominal'
        at=2 if nested_path else 1;prefix=['화','하다'] if nested_path else ['하다']
        assert j['morphemes'][:at]==prefix and j['morpheme_kinds'][:at]==['suffix']*at
        parent=p['before_parent'];assert parent['lemmas'][0]=={'text':base+('화하다' if nested_path else '하다'),'kind':'predicate'}
        assert j['lemmas'][1:]==[l['text'] for l in parent['lemmas'][1:]]
        assert j['morphemes'][at:]==[m['form'] for m in parent['morphemes']]
        assert j['morpheme_kinds'][at:]==[m['kind'] for m in parent['morphemes']]
    rows=[];assert len(source['corpora'])==6
    for corpus in source['corpora']:
        path=ROOT/corpus['source']
        if path.exists():assert sha(path)==corpus['sha256']
        for row in corpus['rows']:
            assert len(row['original_row'])==10 and '화+하' in row['original_lemma']
            assert '\t'.join(row['original_row']) in row['complete_sentence'].splitlines()
            if path.exists():assert row['complete_sentence'] in path.read_text()
            rows.append(row)
    assert len(rows)==30
    assert hashlib.sha256(source['producer']['text'].encode()).hexdigest()==source['producer']['sha256']
    return 1154,562,165,30


def parent_for(source,word,analysis,raw_before=None):
    nested=analysis['morphemes'][0]=={'form':'화','kind':'suffix'}
    base=analysis['lemmas'][0]['text'];direct,deep=licenses(source)
    assert analysis['lemmas'][0]['kind']=='nominal' and base in (deep if nested else direct)
    count=2 if nested else 1
    assert analysis['morphemes'][:count]==([{'form':'화','kind':'suffix'},{'form':'하다','kind':'suffix'}] if nested else [{'form':'하다','kind':'suffix'}])
    head=base+('화하다' if nested else '하다');parent=copy.deepcopy(analysis)
    parent['lemmas'][0]={'text':head,'kind':'predicate'};parent['morphemes']=parent['morphemes'][count:]
    for path in parent.get('spelling_paths',[]):
        assert all(r['morpheme_index']>=count for r in path)
        for r in path:r['morpheme_index']-=count
    if raw_before is None:
        _,raw_before=word_records(source['before']['raw']['jsonl'])
    matches=[p for p in raw_before[word]['analysis']['analyses'] if {k:v for k,v in p.items() if k!='rules'}=={k:v for k,v in parent.items() if k!='rules'}]
    assert matches,(word,analysis)
    assert set(analysis['rules'])<={r for p in matches for r in p['rules']}|{RULE}|({'suffix.nominal.hwa'} if nested else set())
    return next(f for f in source['families'] if f['verbal_head']==head),nested,matches[0]


def inspect_comparison(source,report):
    assert report['source_sha256']==sha(SOURCE) and report['fixture_sha256']==sha(FIXTURE)
    assert report['before_cli_sha256']==source['before_cli_sha256'] and report['dictionary_sha256']==source['dictionary_sha256']
    assert set(report['runs'])==set(MODES);changes=[];native=source['complete_native_entries']
    _,raw_before=word_records(source['before']['raw']['jsonl'])
    for mode,runs in report['runs'].items():
        assert set(runs)=={'NFC-cached','NFC-uncached','NFD-cached','NFD-uncached'}
        _,before=word_records(source['before'][mode]['jsonl']);parity=None
        for name,run in runs.items():
            assert run['exit_code']==0 and hashlib.sha256(run['jsonl'].encode()).hexdigest()==run['sha256']
            records,after=word_records(run['jsonl']);assert set(after)==set(before)
            assert ''.join(r['surface'] for r in records)==unicodedata.normalize(name.split('-')[0],source['input'])
            semantic={w:(r['analysis'],r['dictionary']) for w,r in after.items()}
            if parity is None:parity=semantic
            else:assert semantic==parity
        for word,r in after.items():
            old=before[word]['analysis']['analyses'];new=r['analysis']['analyses']
            assert [a for a in new if RULE not in a['rules']]==old,word
            for i,a in enumerate(new):
                reading=r['dictionary']['readings'][i]
                if RULE not in a['rules']:
                    assert reading==before[word]['dictionary']['readings'][old.index(a)],word
                    continue
                f,nested,parent=parent_for(source,word,a,raw_before)
                ids=f['whole_hada_ids'];expected=sorted({o.removesuffix('化하다' if nested else '하다') for ident in ids for o in native[ident]['origins']})
                for entry in reading['lemmas'][0]['entries']:
                    actual=native[entry['id']];identity=entry.get('derivational_identity')
                    if actual['pos']!='명사':assert identity is None;continue
                    assert identity is not None and identity['morpheme_index']==int(nested)
                    assert identity['whole_entries']==ids and identity['expected_origins']==expected
                    assert identity['whole_origins_complete'] is True
                    relation='recorded_match' if set(actual['origins'])&set(expected) else 'recorded_difference' if actual['origins'] else 'unknown'
                    assert identity['relation']==relation
                changes.append({'id':'hwa-hada-change-'+digest([mode,word,a]),'mode':mode,'surface':word,'analysis':a,'parent':parent,'reading':reading,'contextual_verdict':'unjudged','independent_review':'pending'})
    assert report['changes']==changes
    return len(changes)


def capture(cli,output):
    assert not output.exists();source=read(SOURCE);inspect_source(source)
    report={'schema_version':1,'checklist':'COV-022q','source_sha256':sha(SOURCE),'fixture_sha256':sha(FIXTURE),'before_cli_sha256':source['before_cli_sha256'],'cli_sha256':sha(cli),'dictionary_sha256':sha(ROOT/'data/dictionaries/krdict/krdict.db'),'runs':{},'changes':[]}
    _,raw_before=word_records(source['before']['raw']['jsonl'])
    for mode,flags in MODES.items():
        report['runs'][mode]={}
        for encoding in ['NFC','NFD']:
            for name,budget in [('cached','8388608'),('uncached','0')]:
                command=[str(cli),'text','-','--dictionary',str(ROOT/'data/dictionaries/krdict/krdict.db'),*flags,'--cache-bytes',budget]
                run=subprocess.run(command,input=unicodedata.normalize(encoding,source['input']),text=True,capture_output=True,check=True)
                report['runs'][mode][encoding+'-'+name]={'command':command,'exit_code':run.returncode,'jsonl':run.stdout,'sha256':hashlib.sha256(run.stdout.encode()).hexdigest()}
        _,words=word_records(report['runs'][mode]['NFC-cached']['jsonl'])
        for word,r in words.items():
            for i,a in enumerate(r['analysis']['analyses']):
                if RULE not in a['rules']:continue
                _,_,parent=parent_for(source,word,a,raw_before)
                report['changes'].append({'id':'hwa-hada-change-'+digest([mode,word,a]),'mode':mode,'surface':word,'analysis':a,'parent':parent,'reading':r['dictionary']['readings'][i],'contextual_verdict':'unjudged','independent_review':'pending'})
    with gzip.GzipFile(filename=str(output),mode='wb',mtime=0) as stream:stream.write((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode())
    return inspect_comparison(source,report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');p.add_argument('--cli',type=Path);p.add_argument('--output',type=Path);p.add_argument('--comparison',type=Path,default=REPORT);a=p.parse_args()
    print('Verified source/cases/words/native/rows:',inspect_source(read(SOURCE)))
    if a.cli:assert a.output;print('Captured new parent-attributed paths:',capture(a.cli,a.output))
    elif a.verify:print('Verified candidate/reading changes:',inspect_comparison(read(SOURCE),read(a.comparison)))
