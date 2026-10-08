"""Independent current922-input browser/source/filter/native/diagram verification."""
import argparse,copy,gzip,hashlib,json,math,pathlib,sys,unicodedata
ROOT=pathlib.Path(__file__).resolve().parents[1];PROTO=ROOT;FRONT=ROOT/'web';sys.path.insert(0,str(ROOT/'tools'))
from ostensible_reason_audit import read,sha,matches
from native_lmf import entry,verify_native_lmf

def inspect(runtime,browser,prepared):
 rust=read(ROOT/'docs/literary-question-go-main-full-rust.json')
 assert runtime['frozen_inputs'][runtime['rust_receipt']]==sha((ROOT/'docs/literary-question-go-main-full-rust.json').read_bytes())
 assert rust['state']=='passed' and rust['exit_code']==0 and rust['inputs_unchanged'] is True
 assert rust['tests']=={'passed':1052,'failed':0,'ignored':1,'batches':222}
 assert runtime['source_snapshot']==rust['snapshot']['files'] and len(runtime['source_snapshot'])==922
 assert runtime['state']=='passed' and runtime['exit_code']==0 and runtime['inputs_unchanged'] is True
 assert runtime['server_stopped'] is True and runtime['server_exit_code'] in [-2,130]
 assert sha(runtime['producer']['text'].encode())==runtime['producer']['sha256']
 assert runtime['producer']['text']==(ROOT/'tools/capture_literary_question_go_web.py').read_text()
 assert browser['producer_sha256']==sha((ROOT/'web/tests/literary-question-go.mjs').read_bytes())
 assert browser['catalog_sha256']==runtime['frontend_snapshot']['src/grammar-labels.json']==sha((FRONT/'src/grammar-labels.json').read_bytes())
 assert browser['cli_sha256']==runtime['frozen_inputs'][runtime['cli']]
 assert runtime['browser_sha256']==sha((ROOT/'docs/literary-question-go-main-browser.json').read_bytes())
 assert len(runtime['asset_checks'])==2
 for r in runtime['asset_checks']:assert r['sha256']==runtime['asset_snapshot'][r['path'].lstrip('/')]
 assert browser['errors']==[] and browser['particleDiagrams']==[]
 assert [r['encoding'] for r in browser['responses']]==['NFC','NFD']
 source=read(ROOT/'docs/literary-question-go-source-discovery.json.gz');after=read(ROOT/'docs/literary-question-go-prototype-source-replay.json.gz')
 for response in browser['responses']:
  e=response['encoding'];assert response['request']['text']==unicodedata.normalize(e,source['input']);elapsed=response['after']['elapsed_ms'];assert type(elapsed) in [int,float] and math.isfinite(elapsed) and elapsed>=0
  before=next(r for r in source['runs'] if r['encoding']==e and r['mode']=='raw');current=next(r for r in after['runs'] if r['encoding']==e and r['mode']=='raw')
  assert response['before']['records']==list(map(json.loads,before['jsonl'].splitlines()))
  assert response['after']['records']==list(map(json.loads,current['jsonl'].splitlines())) and len(response['after']['records'])==535
  for r,orders in zip(response['after']['records'],response['after']['breakdowns'],strict=True):
   if r.get('analysis'):
    assert len(orders)==len(r['analysis']['analyses']) and all(o is not None for o in orders)
 suite=read(PROTO/'tests/fixtures/literary-question-go-validity.json');suite['cases']+=read(PROTO/'tests/fixtures/literary-question-go-boundaries.json')['cases'];normal={c['id']:c for c in suite['cases']};assert len(normal)==62
 keys=[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']];assert [(r['encoding'],r['mode']) for r in browser['exports']]==keys
 judgments=[]
 for export in browser['exports']:
  rows={r['analysis']['normalized']:r for r in export['records'] if r.get('analysis')}
  text=unicodedata.normalize(export['encoding'],' '.join(dict.fromkeys(c['surface'] for c in suite['cases'])));assert export['request']['text']==text
  for c in suite['cases']:
   for j in c['judgments']:
    present=any(matches(p,j) for p in rows[c['surface']]['analysis']['analyses']);assert present==(j['verdict']=='required')
    judgments.append({'encoding':export['encoding'],'mode':export['mode'],'case_id':c['id'],'judgment_id':j['id'],'present':present,'verdict':j['verdict']})
 assert browser['modeJudgments']==judgments and len(judgments)==372
 matrix=read(PROTO/'tests/fixtures/literary-question-go-mode-scope.json');special={c['id']:c for c in matrix['cases']};modes=read(ROOT/'docs/literary-question-go-prototype-modes.json.gz');conditional=[]
 assert [(r['encoding'],r['mode']) for r in browser['conditionalExports']]==keys
 for actual,run in zip(browser['conditionalExports'],modes['runs'],strict=True):
  assert actual['request']['text']==run['input'] and actual['records']==list(map(json.loads,run['after_jsonl'].splitlines()))
  rows={r['analysis']['normalized']:r for r in actual['records'] if r.get('analysis')}
  for c in matrix['cases']:
   targets=[i for i,p in enumerate(rows[c['surface']]['analysis']['analyses']) if matches(p,c['expected'])];assert bool(targets)==c['expected_presence'][actual['mode']]
   conditional.append({'encoding':actual['encoding'],'mode':actual['mode'],'case_id':c['id'],'judgment_id':c['judgment_id'],'present':bool(targets),'expected_presence':c['expected_presence'][actual['mode']],'contextual_verdict':'unjudged'})
 assert conditional==browser['conditionalModeJudgments'] and len(conditional)==96
 catalog=read(FRONT/'src/grammar-labels.json')
 for name,cases,expected_count in [('diagrams',normal,116),('conditionalDiagrams',special,30)]:
  diagrams=browser[name];assert len(diagrams)==expected_count
  assert len({(d['case_id'],d['judgment_id'],d['encoding']) for d in diagrams})==expected_count
  for d in diagrams:
   c=cases[d['case_id']];j=next(j for j in c['judgments'] if j['id']==d['judgment_id']) if name=='diagrams' else c['expected'];assert matches(d['analysis'],j)
   if name=='diagrams':assert j['verdict']=='required'
   assert len(d['pieces'])==1;piece=d['pieces'][0];m=d['analysis']['morphemes'][piece['morpheme']];key='-'+m['form'];assert piece['key']==key and piece['label']==catalog[key]['label']=='Literary question'
   for s in catalog[key]['sources']:assert str(s['id']) in piece['title']
   assert len(d['order'])==len(d['analysis']['lemmas'])+len(d['analysis']['morphemes'])
   assert {v['lemma'] for v in d['order'] if 'lemma' in v}==set(range(len(d['analysis']['lemmas'])))
   assert {v['morpheme'] for v in d['order'] if 'morpheme' in v}==set(range(len(d['analysis']['morphemes'])))
 native=prepared['complete_native_entries'];assert len(native)==136
 for i,raw in prepared['original_lmf'].items():assert entry(raw)==native[i]
 verify_native_lmf(prepared['english_projection'],native)
 assert len(browser['native'])==136 and {r['id']:r['response']['entry'] for r in browser['native']}==native
 assert browser['opened']==[{'id':i,'head':native[i]['headword']} for i in ['krdict:73889','krdict:73892','krdict:73898','krdict:73901']]
 return {'completed_full_rust_inputs':922,'full_rust_passed':1052,'original_source_api_frames':1070,'source_and_boundary_diagrams':116,'conditional_diagrams':30,'exact_exports':12,'native_entries':136,'source_mode_judgments':372,'conditional_mode_judgments':96,'owned_server_stopped':True}
if __name__=='__main__':
 print(inspect(read(ROOT/'docs/literary-question-go-main-browser-runtime.json'),read(ROOT/'docs/literary-question-go-main-browser.json'),read(ROOT/'docs/literary-question-go-boundary-matched-owner-preparation.json.gz')),flush=True)
