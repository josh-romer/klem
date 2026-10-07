"""Offline original RI sources, owner modes and complete prototype captures."""
import gzip,hashlib,json,sys,unicodedata
from pathlib import Path
from native_lmf import entry,verify_native_lmf
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs';REVIEW=ROOT
sha=lambda data:hashlib.sha256(data).hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b) if p.suffix=='.gz' else b)
def producer(d):assert sha(d['producer']['text'].encode())==d['producer']['sha256']
def match(a,j):return [l['text'] for l in a['lemmas']]==j['lemmas'] and [l['kind'] for l in a['lemmas']]==j['lemma_kinds'] and [m['form'] for m in a['morphemes']]==j['morphemes'] and [m['kind'] for m in a['morphemes']]==j['morpheme_kinds']
def verify(source,owners,proposal,modes,cli,raw,policy,browser):
 for d in [source,owners,proposal,cli]:producer(d);assert d['preparation_only'] and d['contextual_verdict']=='unjudged' and d['independent_review']=='pending'
 source_hash=sha((BASE/'literary-ri-prefinal-source-discovery.json.gz').read_bytes())
 proposal_hash=sha((BASE/'literary-ri-prefinal-target-proposals.json').read_bytes())
 assert source_hash==owners['source_capture_sha256']==proposal['source_capture_sha256']==cli['source_capture_sha256']
 assert proposal_hash==owners['target_proposals_sha256']==cli['target_proposals_sha256']
 assert cli['mode_scope_review_sha256']==sha((BASE/'literary-ri-prefinal-mode-scope-review.json').read_bytes())
 assert source['inputs_unchanged'] and cli['inputs_unchanged']
 manifest=json.loads(source['dictionary_metadata']['manifest'])
 assert manifest['license']=='CC-BY-SA-2.0-KR' and len(manifest['files'])==11
 assert {Path(k).name:v for k,v in owners['source_hashes'].items()}=={f['name']:f['sha256'] for f in manifest['files']}

 native=owners['complete_native_entries'];assert len(native)==56;assert {k:entry(v) for k,v in owners['original_lmf'].items()}==native;verify_native_lmf(owners['english_projection'],native)
 assert set(source['sqlite_entries'])=={'krdict:52612','krdict:86606'};assert source['sqlite_entries']=={k:native[k] for k in source['sqlite_entries']}
 groups=[{'source':k,'sense':s['id'],'index':i,'original':g} for k,e in source['sqlite_entries'].items() for s in e['senses'] for i,g in enumerate(s['examples'])];assert groups==source['all_original_groups'] and len(groups)==18;assert sum(len(e['senses']) for e in source['sqlite_entries'].values())==4
 conditional={c['case_id'] for c in modes['cases']};assert len(conditional)==6
 cases=proposal['cases'];assert len(cases)==40
 assert policy['cases'][:40]==[{k:v for k,v in c.items() if k!='source_occurrence'} for c in cases]
 assert raw['cases']==[c for c in policy['cases'] if c['id'] not in conditional];assert len(raw['cases'])==36
 assert len(policy['cases'])==42
 supplement=read(BASE/'literary-ri-prefinal-supplemental-b.json')
 assert supplement['native_owner']==native['krdict:17203']
 assert any(f['kind']=='활용' and f['written']=='도우니' for f in supplement['native_owner']['forms'])
 for c,raw_case,policy_case in zip(supplement['cases'],raw['cases'][-2:],policy['cases'][-2:],strict=True):
  assert raw_case==policy_case and raw_case['surface']==c['surface']
  assert {k:v for k,v in raw_case['judgments'][0].items() if k in c['judgment']}==c['judgment']
 assert len(supplement['probes'])==8
 for run in supplement['probes']:
  c=next(c for c in supplement['cases'] if c['id']==run['case']);assert sha(run['json'].encode())==run['sha256'] and run['exit_code']==0
  assert [p for p in json.loads(run['json'])['analyses'] if match(p,c['judgment'])]==run['matching_paths'] and run['matching_paths']
 assert sum(j['verdict']=='required' for c in raw['cases'] for j in c['judgments'])==30
 assert sum(j['verdict']=='forbidden' for c in raw['cases'] for j in c['judgments'])==6
 assert sum(j['verdict']=='forbidden' for c in policy['cases'] for j in c['judgments'])==12
 for c in cases[:18]:
  o=c['source_occurrence'];e=native[o['source']];sense=next(s for s in e['senses'] if s['id']==o['sense']);assert sense['examples'][o['index']]==o['original'];start,end=o['character_span'];assert o['original'][o['text_index']][start:end]==c['surface']
 assert cases[0]['judgments'][0]['lemmas']==['들다'] and cases[0]['judgments'][0]['morphemes']==['시','으리','라']
 eat=native['krdict:57293'];assert eat['headword']=='들다' and eat['homonym']=='3' and any(s['id']=='3' for s in eat['senses'])
 for c in cases:
  for j in c['judgments']:
   if c['surface'] in ['도착하리다','전화하리다','막으리다']:assert j['morphemes']==['으리다']
   if c['surface'].endswith('리니라'):assert j['morphemes'][-2:]==['으리','으니라']
 assert len(source['runs'])==len(cli['streams'])==6
 for original,run in zip(source['runs'],cli['streams'],strict=True):
  assert (original['encoding'],original['mode'])==(run['encoding'],run['mode']);assert sha(original['jsonl'].encode())==original['sha256'];assert sha(run['jsonl'].encode())==run['sha256'];assert original['records']==run['records']==275
  b=[json.loads(l) for l in original['jsonl'].splitlines()];a=[json.loads(l) for l in run['jsonl'].splitlines()];assert len(a)==len(b)==275
  text=unicodedata.normalize(run['encoding'],source['input']).encode();assert ''.join(r['surface'] for r in a).encode()==text;cursor=0
  for old,new in zip(b,a,strict=True):
   assert old['span']==new['span'] and old['surface']==new['surface'] and old['kind']==new['kind'];assert new['span']['start']==cursor;cursor=new['span']['end'];assert text[new['span']['start']:cursor]==new['surface'].encode()
   if not old.get('analysis'):assert old==new;continue
   assert [p for p in new['analysis']['analyses'] if p in old['analysis']['analyses']]==old['analysis']['analyses']
   for i,p in enumerate(old['analysis']['analyses']):assert old['dictionary']['readings'][i]==new['dictionary']['readings'][new['analysis']['analyses'].index(p)]
  assert cursor==len(text) and run['all_original_candidates_order_and_assessments_preserved']
 assert len(cli['probes'])==160
 by_id={c['id']:c for c in cases};seen=set()
 for run in cli['probes']:
  key=(run['case'],run['encoding'],run['mode']);assert key not in seen;seen.add(key);assert sha(run['json'].encode())==run['sha256'] and run['exit_code']==0
  c=by_id[run['case']];d=json.loads(run['json']);assert d['normalized']==c['surface'];assert run['command'][2]==unicodedata.normalize(run['encoding'],c['surface'])
  for j,o in zip(c['judgments'],run['observations'],strict=True):
   paths=[p for p in d['analyses'] if match(p,j)];assert o['matching_paths']==paths and o['judgment']==j['id']
   expected='unjudged' if c['id'] in conditional and run['mode']=='raw' else j['verdict'];assert o['mode_verdict']==expected;assert bool(paths)==(expected!='forbidden')
 assert seen=={(c,e,m) for c in by_id for e in ['NFC','NFD'] for m in ['raw','compatible']}
 assert len(browser['diagrams'])==56 and len(browser['native'])==56 and len(browser['exports'])==6 and not browser['errors']
 assert {row['id']:row['response']['entry'] for row in browser['native']}==native
 for exported in browser['exports']:
  for ident in conditional:
   c=by_id[ident];record=next(r for r in exported['records'] if (r.get('analysis') or {}).get('normalized')==c['surface']);present=any(match(p,c['judgments'][0]) for p in record['analysis']['analyses']);assert present==(exported['mode']!='compatible')
 return {'state':'bounded-source-and-mode-audit-passed','groups':18,'senses':4,'required':30,'raw_forbidden':6,'provider_forbidden':12,'conditional_raw_hypotheses':6,'native_owners':56,'streams':6,'frames_per_stream':275,'word_probes':168,'diagrams':56,'exports':6,'contextual_verdict':'unjudged','independent_review':'pending'}
def inputs():return [read(BASE/'literary-ri-prefinal-source-discovery.json.gz'),read(BASE/'literary-ri-prefinal-owner-preparation-v2.json.gz'),read(BASE/'literary-ri-prefinal-target-proposals.json'),read(BASE/'literary-ri-prefinal-mode-scope-review.json'),read(BASE/'literary-ri-prefinal-prototype-cli.json.gz'),read(REVIEW/'tests/fixtures/literary-ri-prefinal-validity.json'),read(REVIEW/'tests/fixtures/literary-ri-prefinal-policy-validity.json'),read(BASE/'literary-ri-prefinal-prototype-browser-final-browser.json')]
if __name__=='__main__':print(json.dumps(verify(*inputs()),ensure_ascii=False))
