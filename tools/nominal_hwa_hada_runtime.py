"""Verify actual -화하다 API orders, full native endpoints and browser exports."""
import argparse
import base64
import hashlib
import unicodedata

from nominal_hwa_hada_audit import FIXTURE, RULE, SOURCE
from nominal_hwa_hada_audit import REPORT as DIAGNOSTICS
from well_doeda_audit import MODES, ROOT, read, sha, word_records

REPORT=ROOT/'docs/nominal-hwa-hada-runtime-checks.json.gz'
CONTROLS=ROOT/'docs/nominal-hwa-hada-browser-controls.json.gz'


def inspect(report):
    source,diagnostic,control=read(SOURCE),read(DIAGNOSTICS),read(CONTROLS)
    words=list(read(FIXTURE)['before_analyses']);api,browser=report['api'],report['browser']
    assert report['source_sha256']==api['source_sha256']==control['source_sha256']==sha(SOURCE)
    assert report['diagnostics_sha256']==sha(DIAGNOSTICS) and report['browser_controls_sha256']==sha(CONTROLS)
    assert api['cli_sha256']==browser['cli_sha256']==control['cli_sha256']==diagnostic['cli_sha256']
    assert browser['fixture_sha256']==api['fixture_sha256']==sha(FIXTURE)
    assert browser['dictionary_sha256']==diagnostic['dictionary_sha256']
    assert api['before']['cli_sha256']==control['before_cli_sha256']==source['before_cli_sha256']
    assert api['before']['derived_orders']==0 and len(api['before']['batches'])==9
    assert len(api['batches'])==18 and [b['encoding'] for b in api['batches']]==['NFC']*9+['NFD']*9
    before={}
    for batch in api['before']['batches']:
        assert batch['encoding']=='NFC'
        records,_=word_records(batch['cli_jsonl']);assert batch['response']['records']==records
        for r,orders in zip(records,batch['response']['breakdowns'],strict=True):
            if r.get('analysis'):before[r['analysis']['normalized']]=(r,orders)
    assert set(before)==set(words)
    _,old=word_records(source['before']['raw']['jsonl'])
    for word,(r,_) in before.items():assert (r['analysis'],r['dictionary'])==(old[word]['analysis'],old[word]['dictionary'])
    _,expected=word_records(diagnostic['runs']['raw']['NFC-cached']['jsonl'])
    encoded={'NFC':[],'NFD':[]};total=derived=0
    for index,batch in enumerate(api['batches']):
        start=(index%9)*63;assert batch['request']['text']==unicodedata.normalize(batch['encoding'],' '.join(words[start:start+63]))
        assert len(batch['request']['text'].encode())<=8000
        assert hashlib.sha256(batch['cli_jsonl'].encode()).hexdigest()==batch['cli_jsonl_sha256']
        records,_=word_records(batch['cli_jsonl']);assert records==batch['response']['records']
        for r,orders in zip(records,batch['response']['breakdowns'],strict=True):
            if not r.get('analysis'):continue
            word=r['analysis']['normalized'];encoded[batch['encoding']].append(word);total+=1
            assert (r['analysis'],r['dictionary'])==(expected[word]['analysis'],expected[word]['dictionary'])
            previous,old_orders=before[word]
            for a,order in zip(r['analysis']['analyses'],orders,strict=True):
                if RULE not in a['rules']:
                    assert order==old_orders[previous['analysis']['analyses'].index(a)];continue
                assert order[:2]==[{'lemma':0},{'morpheme':0}]
                assert [c['morpheme'] for c in order if 'morpheme' in c]==list(range(len(a['morphemes'])))
                assert [c['lemma'] for c in order if 'lemma' in c]==list(range(len(a['lemmas'])))
                derived+=1
    assert all(v==words for v in encoded.values()) and total==1124 and derived==api['derived_orders']==2272
    assert api['complete_native_entries']==api['before']['complete_native_entries']==source['complete_native_entries']
    for captured in [api,api['before']]:
        assert hashlib.sha256(captured['producer']['text'].encode()).hexdigest()==captured['producer']['sha256']
    assert control['words']==['의인화했다','최소화한다'] and control['input']==' '.join(control['words'])
    from nominal_hwa_hada_audit import parent_for
    supplemental={**source,'input':control['input'],'words':control['words'],'before':control['runs']['before']}
    _,raw_controls=word_records(control['runs']['before']['raw']['jsonl'])
    # The controls keep their separate real pre-change owners and identity sources.
    for mode,runs in control['runs']['after'].items():
        assert runs['exit_code']==0 and hashlib.sha256(runs['jsonl'].encode()).hexdigest()==runs['sha256']
        old_run=control['runs']['before'][mode]
        assert old_run['exit_code']==0 and hashlib.sha256(old_run['jsonl'].encode()).hexdigest()==old_run['sha256']
        assert old_run['command'][0]==source['before_cli']
        _,values=word_records(runs['jsonl']);_,prior=word_records(old_run['jsonl'])
        for word,r in values.items():
            old_analyses=prior[word]['analysis']['analyses']
            assert [a for a in r['analysis']['analyses'] if RULE not in a['rules']]==old_analyses
            for index,a in enumerate(r['analysis']['analyses']):
                reading=r['dictionary']['readings'][index]
                if RULE not in a['rules']:
                    assert reading==prior[word]['dictionary']['readings'][old_analyses.index(a)];continue
                f,nested,_=parent_for(supplemental,word,a,raw_controls)
                ids=f['whole_hada_ids'];native=source['complete_native_entries']
                wanted=sorted({o.removesuffix('化하다' if nested else '하다') for i in ids for o in native[i]['origins']})
                for entry in reading['lemmas'][0]['entries']:
                    actual=native[entry['id']];identity=entry.get('derivational_identity')
                    if actual['pos']!='명사':assert identity is None;continue
                    assert identity['morpheme_index']==int(nested) and identity['whole_entries']==ids
                    assert identity['expected_origins']==wanted and identity['whole_origins_complete'] is True
                    relation='recorded_match' if set(actual['origins'])&set(wanted) else 'recorded_difference' if actual['origins'] else 'unknown'
                    assert identity['relation']==relation
        if mode=='raw':expected.update(values)
    assert browser['browser_errors']==[] and len(browser['diagrams'])==10 and len(browser['checks'])==6
    text='가시화했어요 상품화하는 의인화했다 간소화하시다 최소화한다'
    assert [b['encoding'] for b in browser['responses']]==['NFC','NFD']
    for b in browser['responses']:
        assert b['request']['text']==unicodedata.normalize(b['encoding'],text)
        assert any(e['id']=='krdict:88475' for e in b['response']['grammar']['-하다'])
        for r in b['response']['records']:
            if r.get('analysis'):
                want=expected[r['analysis']['normalized']];assert (r['analysis'],r['dictionary'])==(want['analysis'],want['dictionary'])
    assert {(c['encoding'],c['mode']) for c in browser['checks']}=={(e,m) for e in ['NFC','NFD'] for m in MODES}
    for c in browser['checks']:
        assert c['cli_records']==c['exported_records']
        _,want=word_records(diagnostic['runs'][c['mode']]['NFC-cached']['jsonl'])
        _,extra=word_records(control['runs']['after'][c['mode']]['jsonl']);want.update(extra)
        for r in c['exported_records']:
            if r.get('analysis'):
                old=want[r['analysis']['normalized']];assert (r['analysis'],r['dictionary'])==(old['analysis'],old['dictionary'])
    for d in browser['diagrams']:
        response=next(b['response'] for b in browser['responses'] if b['encoding']==d['encoding'])
        r=next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized')==d['word'])
        assert d['selected']!=d['whole_selected'] and d['owner']==r['dictionary']['readings'][d['selected']]['lemmas'][0]
        entry=next(e for e in d['owner']['entries'] if e['id']==d['entry']);idn=entry['derivational_identity']
        assert idn['relation']=='recorded_match' and idn['morpheme_index']==int(d['nested'])
        assert d['label']==response['glosses'][d['entry']]
        assert d['parts'][:(3 if d['nested'] else 2)]==([d['base'],'화','하'] if d['nested'] else [d['base'],'하'])
        if d['word']=='가시화했어요':assert d['parts'][3]=='였'
        if d['word']=='간소화하시다':assert d['parts'][2]=='시'
    assert set(report['screenshots'])=={'desktop','mobile'}
    for snap in report['screenshots'].values():
        raw=base64.b64decode(snap['base64'],validate=True);assert raw.startswith(b'\x89PNG\r\n\x1a\n') and hashlib.sha256(raw).hexdigest()==snap['sha256']
    return total,derived,165,10,6


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true',required=True);a=p.parse_args()
    print('Verified API words/orders/native/diagrams/exports:',inspect(read(REPORT)))
