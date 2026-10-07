"""Offline audit of complete original double-past sources and exact proposals."""
import gzip,hashlib,json,re,unicodedata
from pathlib import Path
from native_lmf import entry,verify_native_lmf
ROOT=Path(__file__).resolve().parents[1]
FILES={
 'source':ROOT/'docs/double-past-prefinal-source-discovery.json.gz',
 'owners':ROOT/'docs/double-past-prefinal-owner-preparation.json.gz',
 'draft':ROOT/'docs/double-past-prefinal-judgments.json',
 'suite':ROOT/'tests/fixtures/double-past-prefinal-validity.json'}

def sha(data):return hashlib.sha256(data).hexdigest()
def read(key):
 p=FILES[key];data=p.read_bytes();return json.loads(gzip.decompress(data) if p.suffix=='.gz' else data)
def producer(report):assert sha(report['producer']['text'].encode())==report['producer']['sha256']
def verify_sources(source,owners):
 for r in [source,owners]:
  producer(r);assert r['preparation_only'] and r['contextual_verdict']=='unjudged' and r['independent_review']=='pending'
 assert source['inputs_unchanged'] is True
 native=owners['complete_native_entries']
 assert len(native)==37
 assert {k:entry(raw) for k,raw in owners['original_lmf'].items()}==native
 verify_native_lmf(owners['english_projection'],native)
 assert set(source['sqlite_entries'])=={'krdict:68836','krdict:68838','krdict:68840'}
 assert source['sqlite_entries']=={k:native[k] for k in source['sqlite_entries']}
 manifest=json.loads(source['dictionary_metadata']['manifest'])
 assert manifest['license']=='CC-BY-SA-2.0-KR' and len(manifest['files'])==11
 assert {Path(k).name:v for k,v in owners['source_hashes'].items()}=={f['name']:f['sha256'] for f in manifest['files']}
 groups=[{'source':k,'sense':s['id'],'index':i,'original':g} for k,e in source['sqlite_entries'].items() for s in e['senses'] for i,g in enumerate(s['examples'])]
 assert len(groups)==11 and groups==source['all_original_groups']
 assert all(len(e['senses'])==1 and e['senses'][0]['id']=='1' for e in source['sqlite_entries'].values())
 assert native['krdict:68836']['senses'][0]['notes']==['끝음절의 모음이 ‘ㅏ, ㅗ’인 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.']
 assert native['krdict:68838']['senses'][0]['notes']==['끝음절의 모음이 ‘ㅏ, ㅗ’가 아닌 동사와 형용사 뒤에, 다른 어미 앞에 붙여 쓴다.']
 assert native['krdict:68840']['senses'][0]['notes']==['‘하다’나 ‘하다’가 붙는 동사와 형용사 뒤에 붙여 쓴다. ']
 assert source['input']=='\n'.join(t for g in groups for t in g['original'])+'\n'
def verify_targets(source,draft,suite):
 producer(draft);assert draft['preparation_only'] and draft['contextual_verdict']=='unjudged' and draft['independent_review']=='pending'
 cases=draft['cases'];positive=[c for c in cases if 'source_occurrence' in c]
 assert len(cases)==17 and len(positive)==11
 rows=[]
 for g in source['all_original_groups']:
  for ti,text in enumerate(g['original']):
   for m in re.finditer(r'[가-힣]+',text):
    if sum((ord(ch)-0xAC00)%28==20 for ch in m[0])>=2:
     rows.append({'source':g['source'],'sense':g['sense'],'index':g['index'],'text_index':ti,'character_span':[m.start(),m.end()],'surface':m[0]})
 assert len(rows)==11 and rows==draft['literal_double_ss_observations']
 covered=[]
 # Exact source-owned lexical proposals below are authored before engine observations.
 expected={'작았었다':('작다','다'),'살았었다':('살다','다'),'갔었다':('가다','다'),'알아봤었는데':('알아보다','는데'),'컸었다':('크다','다'),'예뻤었어':('예쁘다','어'),'적었었다':('적다','다'),'두었었는데요':('두다','는데'),'잘했었다':('잘하다','다'),'했었다':('하다','다'),'노력했었는데':('노력하다','는데')}
 for c in positive:
  o=c['source_occurrence'];surface=c['surface'];start,end=o['character_span']
  g=next(g for g in source['all_original_groups'] if (g['source'],g['sense'],g['index'])==(o['source'],o['sense'],o['index']))
  assert o['original']==g['original'] and g['original'][o['text_index']][start:end]==surface
  assert c['id']==f"double-past-prefinal-{o['source'].split(':')[1]}-1-{o['index']}-{o['text_index']}-{start}"
  covered.append({k:o[k] for k in ['source','sense','index','text_index','character_span']}|{'surface':surface})
  lemma,ending=expected[surface]
  assert len(c['judgments'])==(2 if surface=='두었었는데요' else 1)
  j=c['judgments'][0]
  assert j['lemmas']==[lemma] and j['lemma_kinds']==['predicate'] and j['verdict']=='required'
  assert j['morphemes']==['었','었',ending]+(['요'] if surface=='두었었는데요' else [])
  assert j['morpheme_kinds']==['prefinal','prefinal','ending']+(['particle'] if surface=='두었었는데요' else [])
  if surface=='두었었는데요':
   j=c['judgments'][1];assert j['lemmas']==['두다'] and j['verdict']=='required' and j['morphemes']==['었','었','는데요'] and j['morpheme_kinds']==['prefinal','prefinal','ending']
 assert covered==rows
 negatives=[('가었었다','가다',2),('먹았었다','먹다',2),('하았었다','하다',2),('하었었다','하다',2),('좋었었다','좋다',2),('먹었었었다','먹다',3)]
 for c,(surface,lemma,n) in zip(cases[11:],negatives,strict=True):
  assert c['surface']==surface and len(c['judgments'])==1
  j=c['judgments'][0];assert j['lemmas']==[lemma] and j['lemma_kinds']==['predicate'] and j['verdict']=='forbidden'
  assert j['morphemes']==['었']*n+['다'] and j['morpheme_kinds']==['prefinal']*n+['ending']
 assert 'not an explicit source prohibition' in suite['review_status']
 assert suite['cases']==[{k:v for k,v in c.items() if k!='source_occurrence'} for c in cases]
def verify_streams(source,draft):
 assert len(source['runs'])==6
 assert {(r['encoding'],r['mode']) for r in source['runs']}=={(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']}
 for run in source['runs']:
  text=unicodedata.normalize(run['encoding'],source['input']).encode();assert sha(text)==run['input_sha256']
  assert run['command'][0] in source['frozen_inputs'] and run['command'][1:4]==['text','-','--dictionary']
  assert run['command'][4] in source['frozen_inputs']
  assert run['command'][5:]=={'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}[run['mode']]
  assert sha(run['jsonl'].encode())==run['sha256'] and run['exit_code']==0
  frames=[json.loads(l) for l in run['jsonl'].splitlines()];assert len(frames)==run['records']==181
  cursor=0
  for f in frames:
   assert f['span']['start']==cursor;cursor=f['span']['end'];assert text[f['span']['start']:cursor]==f['surface'].encode()
  assert cursor==len(text)
 cases={c['id']:c for c in draft['cases']}
 assert len(draft['probes'])==68
 assert {(r['case'],r['encoding'],r['mode']) for r in draft['probes']}=={(c,e,m) for c in cases for e in ['NFC','NFD'] for m in ['raw','compatible']}
 for run in draft['probes']:
  assert sha(run['json'].encode())==run['sha256'] and run['exit_code']==0
  c=cases[run['case']];response=json.loads(run['json']);assert response['normalized']==c['surface']
  assert run['command'][0] in source['frozen_inputs'] and run['command'][1]=='word'
  assert run['command'][2]==unicodedata.normalize(run['encoding'],c['surface'])
  assert run['command'][3]=='--dictionary' and run['command'][4] in source['frozen_inputs']
  assert run['command'][5:]==([] if run['mode']=='raw' else ['--dict-compatible'])
  assert len(run['observations'])==len(c['judgments'])
  for j,o in zip(c['judgments'],run['observations'],strict=True):
   matching=[a for a in response['analyses'] if [l['text'] for l in a['lemmas']]==j['lemmas'] and [l['kind'] for l in a['lemmas']]==j['lemma_kinds'] and [m['form'] for m in a['morphemes']]==j['morphemes'] and [m['kind'] for m in a['morphemes']]==j['morpheme_kinds'] and set(j.get('required_rules',[]))<=set(a['rules'])]
   assert o['judgment']==j['id'] and o['matching_paths']==matching
   assert bool(matching)==(j['verdict']=='required')
def verify():
 source,owners,draft,suite=map(read,['source','owners','draft','suite'])
 assert sha(FILES['source'].read_bytes())==owners['source_capture_sha256']==draft['source_capture_sha256']
 assert sha(FILES['draft'].read_bytes())==owners['target_proposals_sha256']
 verify_sources(source,owners);verify_targets(source,draft,suite);verify_streams(source,draft)
 history=json.loads(gzip.decompress((ROOT/'docs/double-past-prefinal-preparation-history.json.gz').read_bytes()))
 for archived in history.values():
  data=bytes.fromhex(archived['content']) if archived['encoding']=='hex' else archived['content'].encode()
  assert sha(data)==archived['sha256']
 rust=json.loads(history['klem-double-past-prefinal-review-rust.json']['content']);assert rust['state']=='passed' and rust['exit_code']==0 and rust['tests_passed']==3
 assert rust['required']==12 and rust['forbidden']==6 and rust['complete_native_owners']==37
 assert history['wrapper/tests/fixtures/double-past-prefinal-validity.json']['sha256']==rust['wrapper_files']['tests/fixtures/double-past-prefinal-validity.json']
 assert sha(FILES['source'].read_bytes())==rust['source_capture_sha256']
 assert sha(FILES['owners'].read_bytes())==rust['owner_preparation_sha256']
 assert sha(FILES['draft'].read_bytes())==rust['source_draft_sha256']
 verify_main_and_before_api(source,owners,suite)
 browser=json.loads(gzip.decompress((ROOT/'docs/double-past-prefinal-main-browser.json.gz').read_bytes()))
 verify_browser(browser,owners,suite)
 return {'state':'bounded-source-audit-passed','groups':11,'required':12,'forbidden':6,'complete_named_owners':37,'streams':6,'frames_per_stream':181,'word_probes':68,'main_browser_diagrams':24,'contextual_verdict':'unjudged','independent_review':'pending'}

def verify_browser(browser,owners,suite):
 """Check archived actual API/Native/selected-candidate evidence offline."""
 before=json.loads(gzip.decompress((ROOT/'docs/double-past-prefinal-before-api.json.gz').read_bytes()))
 assert browser['errors']==[]
 assert browser['producer_sha256']==sha((ROOT/'web/tests/double-past-prefinal.mjs').read_bytes())
 assert browser['suite_sha256']==sha(FILES['suite'].read_bytes())
 assert len(browser['responses'])==2 and {r['encoding'] for r in browser['responses']}=={'NFC','NFD'}
 expected_family=[{key:owners['complete_native_entries'][eid][key] for key in ['headword','homonym','id','pos']} for eid in ['krdict:68838','krdict:68836','krdict:68840']]
 for run in browser['responses']:
  original=next(r for r in before['runs'] if r['encoding']==run['encoding'])
  assert run['request']==original['request']
  for key in ['records','rules','breakdowns','glosses']:assert run['response'][key]==original['response'][key]
  assert run['response']['grammar']['-었었-']==expected_family
  assert {k:v for k,v in run['response']['grammar'].items() if k!='-었었-'}==original['response']['grammar']
 assert len(browser['native'])==37
 assert {r['id']:r['response']['entry'] for r in browser['native']}==owners['complete_native_entries']
 assert browser['opened']==[{'id':eid,'head':owners['complete_native_entries'][eid]['headword']} for eid in ['krdict:68836','krdict:68838','krdict:68840']]
 assert len(browser['exports'])==6
 assert {(r['encoding'],r['mode']) for r in browser['exports']}=={(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']}
 expected={(c['id'],j['id'],e):(c,j) for c in suite['cases'] for j in c['judgments'] if j['verdict']=='required' for e in ['NFC','NFD']}
 assert len(browser['diagrams'])==len(expected)==24
 assert {(r['case_id'],r['judgment_id'],r['encoding']) for r in browser['diagrams']}==set(expected)
 for row in browser['diagrams']:
  c,j=expected[row['case_id'],row['judgment_id'],row['encoding']];a=row['analysis']
  assert row['surface']==c['surface']
  assert [l['text'] for l in a['lemmas']]==j['lemmas'] and [l['kind'] for l in a['lemmas']]==j['lemma_kinds']
  assert [m['form'] for m in a['morphemes']]==j['morphemes'] and [m['kind'] for m in a['morphemes']]==j['morpheme_kinds']
  assert set(j.get('required_rules',[]))<=set(a['rules'])
  raw=next(r for r in browser['exports'] if r['encoding']==row['encoding'] and r['mode']=='raw')
  record=next(r for r in raw['records'] if (r.get('analysis') or {}).get('normalized')==c['surface'])
  assert record['analysis']['analyses'][row['index']]==a
  assert sorted(row['order'],key=lambda p:(next(iter(p)),next(iter(p.values()))))==sorted([{'lemma':i} for i in range(len(a['lemmas']))]+[{'morpheme':i} for i in range(len(a['morphemes']))],key=lambda p:(next(iter(p)),next(iter(p.values()))))
  positions=[i for i,p in enumerate(row['order']) if 'morpheme' in p and a['morphemes'][p['morpheme']]['kind']=='prefinal' and a['morphemes'][p['morpheme']]['form']=='었']
  assert len(positions)==2 and positions[1]==positions[0]+1
  assert all(str(eid) in row['title'] for eid in [68838,68836,68840])
def verify_main_and_before_api(source,owners,suite):
 ledger=json.loads((ROOT/'tests/fixtures/validity.json').read_text())
 indexed={c['id']:c for c in ledger['cases']}
 assert all(indexed[c['id']]==c for c in suite['cases'])
 assert all(ledger['sources'][k]==v for k,v in suite['sources'].items())
 assert json.loads((ROOT/'tests/fixtures/double-past-prefinal-native.json').read_text())==owners['complete_native_entries']
 assert json.loads((ROOT/'tests/fixtures/krdict-double-past-prefinal-english.json').read_text())==owners['english_projection']
 before=json.loads(gzip.decompress((ROOT/'docs/double-past-prefinal-before-api.json.gz').read_bytes()))
 producer(before);assert before['state']=='before-api-captured' and before['inputs_unchanged']
 assert len(before['runs'])==2 and {r['encoding'] for r in before['runs']}=={'NFC','NFD'}
 for run in before['runs']:
  assert run['status']==200 and sha(run['json'].encode())==run['sha256'] and json.loads(run['json'])==run['response']
  original=next(r for r in source['runs'] if r['encoding']==run['encoding'] and r['mode']=='raw')
  assert run['request']=={'text':unicodedata.normalize(run['encoding'],source['input'])}
  assert run['response']['records']==[json.loads(l) for l in original['jsonl'].splitlines()]
  assert '-었었-' not in run['response']['grammar']
  assert [e['id'] for e in run['response']['grammar']['-었-']]==['krdict:68719','krdict:66954','krdict:68723']
 native=before['complete_primary_native_endpoints'];assert len(native)==3
 assert {r['request']['id'] for r in native}==set(source['sqlite_entries'])
 for run in native:
  assert run['status']==200 and sha(run['json'].encode())==run['sha256'] and json.loads(run['json'])==run['response']
  assert run['response']['entry']==owners['complete_native_entries'][run['request']['id']]
 catalog=json.loads((ROOT/'web/src/grammar-labels.json').read_text())
 assert catalog['-었었-']['kind']=='prefinal'
 assert catalog['-었었-']['components']==['었','었']
 assert catalog['-었었-']['sources']==[{'id':68838,'headword':'-었었-','pos':'어미'},{'id':68836,'headword':'-았었-','pos':'어미'},{'id':68840,'headword':'-였었-','pos':'어미'}]
 assert 'Contextual temporal meaning is not selected.' in catalog['-었었-']['note']
 expected={k:owners['complete_native_entries'][k] for k in source['sqlite_entries']}
 verify_native_lmf(json.loads((ROOT/'tests/fixtures/krdict-double-past-prefinal-labels.json').read_text()),expected)

if __name__=='__main__':print(json.dumps(verify(),ensure_ascii=False))
