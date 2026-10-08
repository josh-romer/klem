"""Derive source diagrams, filter policies, complete Native endpoints and shutdown bindings."""
import argparse,gzip,json,math,unicodedata
from pathlib import Path
from literary_future_kko_runtime import ROOT,read,sha
from literary_future_kko_audit import matches
from native_lmf import entry,verify_native_lmf

def inspect(runtime,browser,prepared,*,browser_path):
    assert runtime['state']=='passed' and runtime['exit_code']==0 and runtime['inputs_unchanged'] is True
    assert runtime['server_stopped'] is True and runtime['server_exit_code'] in [-2,130]
    assert sha(runtime['producer']['text'].encode())==runtime['producer']['sha256']
    raw=Path(browser_path).read_bytes();raw=gzip.decompress(raw) if str(browser_path).endswith('.gz') else raw
    assert runtime['browser_sha256']==sha(raw)
    assert browser['errors']==[]
    cli=next(p for p in runtime['frozen_inputs'] if p.endswith('/bin/klem') or p.endswith('-main-cli'))
    assert browser['cli_sha256']==runtime['frozen_inputs'][cli]
    node=next(p for p in runtime['frozen_inputs'] if p.endswith('.mjs'))
    assert browser['producer_sha256']==runtime['frozen_inputs'][node]
    integration=read(ROOT/'docs/literary-future-kko-main-integration.json.gz')
    assert runtime['source_snapshot']==integration['snapshot_files'] and len(runtime['source_snapshot'])==947
    assert browser['catalog_sha256']==runtime['source_snapshot']['web/src/grammar-labels.json']['sha256']
    source=read(ROOT/'docs/literary-future-kko-source-discovery.json.gz')
    replay=read(ROOT/'docs/literary-future-kko-prototype-source-replay.json.gz')
    assert [r['encoding'] for r in browser['responses']]==['NFC','NFD']
    for response in browser['responses']:
        api=response['response'];run=next(r for r in replay['runs'] if r['encoding']==response['encoding'] and r['mode']=='raw')
        assert api['records']==list(map(json.loads,run['jsonl'].splitlines())) and len(api['records'])==253
        assert type(api['elapsed_ms']) in [float,int] and math.isfinite(api['elapsed_ms']) and api['elapsed_ms']>=0
        assert len(api['breakdowns'])==253
        for record,orders in zip(api['records'],api['breakdowns'],strict=True):
            if record.get('analysis'):
                assert len(orders)==len(record['analysis']['analyses'])
                for path,order in zip(record['analysis']['analyses'],orders,strict=True):
                    assert order is not None
                    assert {c['lemma'] for c in order if 'lemma' in c}==set(range(len(path['lemmas'])))
                    assert {c['morpheme'] for c in order if 'morpheme' in c}==set(range(len(path['morphemes'])))
            else:assert orders is None
    originals=read(ROOT/'tests/fixtures/literary-future-kko-original-cases.json')
    boundaries=read(ROOT/'tests/fixtures/literary-future-kko-authored-boundaries.json')['cases']
    finite=read(ROOT/'tests/fixtures/literary-future-kko-validity.json')['cases']
    for case in finite:
        if case['id'].startswith('literary-future-kko-owner-extension-'):
            j=case['judgments'][0];boundaries.append({**case,**j,'expected_presence':{m:j['verdict']=='required' for m in ['raw','headword','compatible']}})
    cases=[{**c,**c['expected'],'expected_presence':{m:True for m in ['raw','headword','compatible']}} for c in originals]+boundaries
    assert len(cases)==84
    keys=[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    assert [(e['encoding'],e['mode']) for e in browser['exports']]==keys
    judgments=[]
    for export in browser['exports']:
        text=unicodedata.normalize(export['encoding'],' '.join(dict.fromkeys(c['surface'] for c in cases)))
        assert export['request']['text']==text
        cursor=0;encoded=text.encode()
        for row in export['records']:
            assert row['span']['start']==cursor and encoded[cursor:row['span']['end']].decode()==row['surface'];cursor=row['span']['end']
        assert cursor==len(encoded)
        rows={r['analysis']['normalized']:r for r in export['records'] if r.get('analysis')}
        for case in cases:
            row=rows[case['surface']];present=any(matches(path,case) for path in row['analysis']['analyses'])
            assert present==case['expected_presence'][export['mode']]
            judgments.append({'encoding':export['encoding'],'mode':export['mode'],'case_id':case['id'],'present':present,'expected_present':case['expected_presence'][export['mode']]})
    assert judgments==browser['modeJudgments'] and len(judgments)==504
    assert len(browser['diagrams'])==38 and len({(d['case_id'],d['encoding']) for d in browser['diagrams']})==38
    by_id={c['id']:c for c in originals}
    for diagram in browser['diagrams']:
        case=by_id[diagram['case_id']];path=diagram['analysis'];assert matches(path,case['expected'])
        exported=next(e for e in browser['exports'] if (e['encoding'],e['mode'])==(diagram['encoding'],'raw'))
        row=next(r for r in exported['records'] if r.get('analysis') and r['analysis']['normalized']==case['surface'])
        assert row['analysis']['analyses'][diagram['index']]==path
        api=next(r['response'] for r in browser['responses'] if r['encoding']==diagram['encoding'])
        at=next(i for i,r in enumerate(api['records']) if r.get('analysis') and r['analysis']['normalized']==case['surface'])
        path_index=api['records'][at]['analysis']['analyses'].index(path)
        assert diagram['order']==api['breakdowns'][at][path_index]
        assert diagram['label']=='Literary future question'
        assert all(i in diagram['title'] for i in ['81026','81032'])
        assert len(diagram['order'])==len(path['lemmas'])+len(path['morphemes'])
        assert {c['lemma'] for c in diagram['order'] if 'lemma' in c}==set(range(len(path['lemmas'])))
        assert {c['morpheme'] for c in diagram['order'] if 'morpheme' in c}==set(range(len(path['morphemes'])))
    native=prepared['complete_native_entries'];assert len(native)==153
    assert {i:entry(raw) for i,raw in prepared['original_lmf'].items()}==native
    verify_native_lmf(prepared['english_projection'],native)
    assert len(browser['native'])==153 and {r['id']:r['response']['entry'] for r in browser['native']}==native
    assert browser['opened']==[{'id':i,'head':native[i]['headword']} for i in ['krdict:81026','krdict:81032']]
    return {'source_api_frames':506,'source_diagrams':38,'mode_checks':504,'exports':6,'complete_native_entries':153,'owned_server_stopped':True,'precision_context_and_independent_review':'pending'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--browser',type=Path,required=True);args=parser.parse_args()
    print(inspect(read(args.runtime),read(args.browser),read(ROOT/'docs/literary-future-kko-spacing-owner-preparation.json.gz'),browser_path=args.browser))
