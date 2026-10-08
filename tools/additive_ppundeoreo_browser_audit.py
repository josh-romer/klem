"""Derive source diagrams, filter policies, complete Native endpoints and shutdown bindings."""
import argparse,gzip,json,math,unicodedata
from pathlib import Path
from literary_question_geona_runtime import read,sha
ROOT=Path(__file__).resolve().parents[1]
def original_bytes(path):
    raw=Path(path).read_bytes();return gzip.decompress(raw) if str(path).endswith('.gz') else raw
from literary_future_kko_audit import matches
from native_lmf import entry,verify_native_lmf

def inspect(runtime,browser,prepared,*,browser_path,phase="isolated"):
    assert phase in ["isolated","main"]
    main=phase=="main"
    binary_name="main-binaries" if main else "current-binaries"
    frontend_name="main-frontend-build" if main else "frontend-build"
    replay_name="main-source-replay" if main else "source-replay"
    producer_name="main-browser" if main else "browser"
    assert runtime['state']=='passed' and runtime['exit_code']==0 and runtime['inputs_unchanged'] is True
    assert runtime['server_stopped'] is True and runtime['server_exit_code'] in [-2,130]
    producer_path='/tmp/klem-additive-ppundeoreo-'+producer_name+'.py'
    assert sha(original_bytes(ROOT/'docs'/('additive-ppundeoreo-'+producer_name+'.py.gz')))==runtime['frozen_inputs'][producer_path]
    raw=Path(browser_path).read_bytes();raw=gzip.decompress(raw) if str(browser_path).endswith('.gz') else raw
    assert runtime['browser_sha256']==sha(raw)
    assert browser['errors']==[]
    cli=next(p for p in runtime['frozen_inputs'] if p.endswith('/bin/klem') or p.endswith('-current-cli') or p.endswith('-main-cli'))
    assert browser['cli_sha256']==runtime['frozen_inputs'][cli]
    node=next(p for p in runtime['frozen_inputs'] if p.endswith('.mjs'))
    assert browser['producer_sha256']==runtime['frozen_inputs'][node]
    integration=read(ROOT/'docs'/('additive-ppundeoreo-'+binary_name+'.json.gz'))
    assert runtime['snapshot_files']==integration['snapshot_files'] and runtime['frozen_inputs']['/tmp/klem-additive-ppundeoreo-'+binary_name+'.json']==sha(original_bytes(ROOT/'docs'/('additive-ppundeoreo-'+binary_name+'.json.gz')))
    assert browser['catalog_sha256']==runtime['snapshot_files']['web/src/grammar-labels.json']['sha256']
    frontend=read(ROOT/'docs'/('additive-ppundeoreo-'+frontend_name+'.json.gz'))
    assert frontend['state']=='passed' and frontend['exit_code']==0
    assert runtime['frontend_inputs']==frontend['source_inputs'] and runtime['assets']==frontend['assets']
    assert len(runtime['served_asset_checks'])==2
    for asset in runtime['served_asset_checks']:
        assert runtime['assets'][asset['path'].lstrip('/')]=={k:v for k,v in asset.items() if k!='path'}
    source=read(ROOT/'docs/additive-ppundeoreo-source-discovery.json.gz')
    replay=read(ROOT/'docs'/('additive-ppundeoreo-'+replay_name+'.json.gz'))
    assert [r['encoding'] for r in browser['responses']]==['NFC','NFD']
    for response in browser['responses']:
        api=response['response'];run=next(r for r in replay['runs'] if r['encoding']==response['encoding'] and r['mode']=='raw')
        assert api['records']==list(map(json.loads,run['jsonl'].splitlines())) and len(api['records'])==229
        assert type(api['elapsed_ms']) in [float,int] and math.isfinite(api['elapsed_ms']) and api['elapsed_ms']>=0
        assert len(api['breakdowns'])==229
        for record,orders in zip(api['records'],api['breakdowns'],strict=True):
            if record.get('analysis'):
                assert len(orders)==len(record['analysis']['analyses'])
                for path,order in zip(record['analysis']['analyses'],orders,strict=True):
                    assert order is not None
                    assert {c['lemma'] for c in order if 'lemma' in c}==set(range(len(path['lemmas'])))
                    assert {c['morpheme'] for c in order if 'morpheme' in c}==set(range(len(path['morphemes'])))
            else:assert orders is None
    originals=read(ROOT/'tests/fixtures/additive-ppundeoreo-original-cases.json')
    boundaries=read(ROOT/'tests/fixtures/additive-ppundeoreo-authored-boundaries.json')['cases']
    cases=[{**c,**c['expected'],'expected_presence':{m:True for m in ['raw','headword','compatible']}} for c in originals]+boundaries
    assert len(cases)==46
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
    assert judgments==browser['modeJudgments'] and len(judgments)==276
    assert len(browser['diagrams'])==20 and len({(d['case_id'],d['encoding']) for d in browser['diagrams']})==20
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
        assert diagram['label']=='Addition / also'
        assert all(i in diagram['title'] for i in ['74341','74021'])
        assert len(diagram['order'])==len(path['lemmas'])+len(path['morphemes'])
        assert {c['lemma'] for c in diagram['order'] if 'lemma' in c}==set(range(len(path['lemmas'])))
        assert {c['morpheme'] for c in diagram['order'] if 'morpheme' in c}==set(range(len(path['morphemes'])))
    native=prepared['complete_native_entries'];assert len(native)==62
    assert {i:entry(raw) for i,raw in prepared['original_lmf'].items()}==native
    verify_native_lmf(prepared['english_projection'],native)
    assert len(browser['native'])==62 and {r['id']:r['response']['entry'] for r in browser['native']}==native
    assert browser['opened']==[{'id':i,'head':native[i]['headword']} for i in ['krdict:74341','krdict:74021']]
    return {'phase':phase,'source_api_frames':458,'source_diagrams':20,'mode_checks':276,'exports':6,'complete_native_entries':62,'owned_server_stopped':True,'precision_context_and_independent_review':'pending'}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['isolated','main'],default='isolated');args=parser.parse_args()
    prefix='main' if args.phase=='main' else 'current'
    print(inspect(read(ROOT/'docs'/('additive-ppundeoreo-'+prefix+'-browser-runtime.json.gz')),read(ROOT/'docs'/('additive-ppundeoreo-'+prefix+'-browser.json.gz')),read(ROOT/'docs/additive-ppundeoreo-owner-closure.json.gz'),browser_path=ROOT/'docs'/('additive-ppundeoreo-'+prefix+'-browser.json.gz'),phase=args.phase))
