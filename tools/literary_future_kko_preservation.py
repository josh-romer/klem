"""Derive complete broad-stream and original annotated-corpus preservation."""
import gzip,hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from friendly_command_corpora import outcome
from doeda_native_corpora import contexts_text
read=lambda p:json.loads(gzip.decompress(pathlib.Path(p).read_bytes()) if str(p).endswith('.gz') else pathlib.Path(p).read_bytes())
sha=lambda b:hashlib.sha256(b).hexdigest()
digest=lambda v:sha(json.dumps(v,ensure_ascii=False,sort_keys=True).encode())
def sources(candidate):
 return sorted({i for m in candidate['morphemes'] for i in {'을꼬':['krdict:81026','krdict:81032']}.get(m['form'],[])})
def inspect(broad,corpus):
 for r in [broad,corpus]:
  assert r['inputs_unchanged'] is True and sha(r['producer']['text'].encode())==r['producer']['sha256']
  assert r['before_cli_sha256'] in r['frozen_inputs'].values() and r['cli_sha256'] in r['frozen_inputs'].values()
  assert r['contextual_verdict']=='unjudged' and r['independent_review']=='pending'
 assert broad['before_cli_sha256']==corpus['before_cli_sha256']==read(ROOT/'docs/literary-question-go-packaged-cli-replay.json')['cli_sha256']
 assert broad['cli_sha256']==corpus['cli_sha256']
 prior=read(ROOT/'docs/literary-question-go-prototype-broad.json.gz')
 assert broad['prior_capture_sha256']==sha((ROOT/'docs/literary-question-go-prototype-broad.json.gz').read_bytes())
 assert len(broad['comparisons'])==len(prior['comparisons'])==8
 observations=[];spacing_observations=[];frames=0;changed_frames=0
 for b,a in zip(prior['comparisons'],broad['comparisons'],strict=True):
  for k in ['source','source_sha256','mode','records']:assert a[k]==b[k]
  assert a['before_jsonl_sha256']==a['previous_capture_after_sha256']==b['after_jsonl_sha256']
  assert a['baseline_matches_previous_capture'] is True and a['original_bytes_conserved'] is True and a['exit_codes']==[0,0]
  archived=read(ROOT/'docs/literary-question-go-broad-inputs.json.gz');assert archived['state']=='passed'
  original=archived['sources'][a['source_sha256']];assert a['source'] in original['original_paths']
  raw=original['text'].encode();assert len(raw)==original['bytes'] and sha(raw)==a['source_sha256']
  seen=set()
  for delta in a['changed_frames']:
   record=delta['record'];assert 0<record<=a['records'] and record not in seen;seen.add(record)
   old,new=delta['before'],delta['after'];assert old!=new
   assert {k:v for k,v in old.items() if k not in ['analysis','dictionary','spacing']}=={k:v for k,v in new.items() if k not in ['analysis','dictionary','spacing']}
   span=new['span'];assert raw[span['start']:span['end']].decode()==new['surface']
   oa,na=old['analysis'],new['analysis'];assert {k:v for k,v in oa.items() if k!='analyses'}=={k:v for k,v in na.items() if k!='analyses'}
   assert [p for p in na['analyses'] if p in oa['analyses']]==oa['analyses']
   od,nd=old['dictionary'],new['dictionary']
   for p,assessment in zip(oa['analyses'],od['readings'],strict=True):assert nd['readings'][na['analyses'].index(p)]==assessment
   assert all(x in nd['lemmas'] for x in od['lemmas'])
   for k in ['source','fingerprint']:assert od[k]==nd[k]
   left=raw.rfind(b'\n',0,span['start'])+1;right=raw.find(b'\n',span['end']);right=len(raw) if right<0 else right
   additions=[p for p in na['analyses'] if p not in oa['analyses']];assert additions or old.get('spacing')!=new.get('spacing')
   bs,ns=old.get('spacing'),new.get('spacing')
   if bs is not None:
    assert ns is not None
    for k in ['rule','limits']:assert bs[k]==ns[k]
    assert a['previous_spacing_suggestions_conserved'] is True
    for h in bs['alternatives']:
     at=next((t for t in ns['alternatives'] if t['inserted_at']==h['inserted_at'] and t.get('rule')==h.get('rule')),None);assert at is not None
     assert {k:v for k,v in h.items() if k!='records'}=={k:v for k,v in at.items() if k!='records'}
     for bseg,aseg in zip(h['records'],at['records'],strict=True):
      assert {k:v for k,v in bseg.items() if k not in ['analysis','dictionary','breakdowns']}=={k:v for k,v in aseg.items() if k not in ['analysis','dictionary','breakdowns']}
      bp,ap=bseg['analysis'],aseg['analysis'];assert {k:v for k,v in bp.items() if k!='analyses'}=={k:v for k,v in ap.items() if k!='analyses'}
      assert [p for p in ap['analyses'] if p in bp['analyses']]==bp['analyses']
      for i,p in enumerate(bp['analyses']):
       ix=ap['analyses'].index(p);assert bseg['breakdowns'][i]==aseg['breakdowns'][ix];assert bseg['dictionary']['readings'][i]==aseg['dictionary']['readings'][ix]
      for k in ['source','fingerprint']:assert bseg['dictionary'][k]==aseg['dictionary'][k]
      assert all(l in aseg['dictionary']['lemmas'] for l in bseg['dictionary']['lemmas'])
    if bs!=ns:
     for h in ns['alternatives']:
      if h in bs['alternatives']:continue
      paths=[p for seg in h['records'] for p in seg['analysis']['analyses'] if 'ending.literary_future_question_kko' in p['rules']];assert paths
      for seg in h['records']:
       ss=seg['span'];assert raw[ss['start']:ss['end']].decode()==seg['surface'];assert span['start']<=ss['start']<ss['end']<=span['end']
      assert h['spaced']==' '.join(seg['surface'] for seg in h['records'])
      assert h['inserted_at']==[seg['span']['start'] for seg in h['records'][1:]]
      earlier=next((t for t in bs['alternatives'] if t['inserted_at']==h['inserted_at'] and t.get('rule')==h.get('rule')),None)
      spacing_observations.append({'id':'literary-future-kko-spacing-'+digest([a['source_sha256'],a['mode'],record,h])[:24],'source':a['source'],'source_sha256':a['source_sha256'],'mode':a['mode'],'record':record,'surface':new['surface'],'span':span,'complete_original_line':raw[left:right].decode(),'hypothesis':h,'earlier_alternative':earlier,'source_entries':sorted({i for p in paths for i in sources(p)}),'structural_verdict':'unjudged spacing composition','contextual_verdict':'unjudged','independent_review':'pending'})
   for p in additions:
    assert 'ending.literary_future_question_kko' in p['rules']
    ident=digest([a['source_sha256'],a['mode'],record,p])[:24]
    observations.append({'id':'literary-future-kko-broad-'+ident,'source':a['source'],'source_sha256':a['source_sha256'],'mode':a['mode'],'record':record,'surface':new['surface'],'span':span,'complete_original_line':raw[left:right].decode(),'analysis':p,'dictionary_assessment':nd['readings'][na['analyses'].index(p)],'source_entries':sources(p),'structural_verdict':'unjudged broader composition','contextual_verdict':'unjudged','independent_review':'pending'})
  if not a['changed_frames']:assert a['before_jsonl_sha256']==a['after_jsonl_sha256']
  changed_frames+=len(seen);frames+=a['records']
 assert frames==1128312 and observations==broad['individual_additions']
 assert spacing_observations==broad['individual_spacing_additions']
 prior=read(ROOT/'docs/literary-question-go-prototype-corpora.json.gz')
 assert corpus['previous_report_sha256']==sha((ROOT/'docs/literary-question-go-prototype-corpora.json.gz').read_bytes())
 assert corpus['before_words']==prior['after_words']
 assert len(corpus['before_words'])==len(corpus['after_words'])==corpus['unique_surfaces']==32096
 for key in ['before','after']:assert digest(corpus[key+'_words'])==corpus[key+'_words_sha256']
 changes={};additions=[];locations={};gold_rows=0
 for w,b in corpus['before_words'].items():
  a=corpus['after_words'][w]
  assert {k:v for k,v in b.items() if k!='analyses'}=={k:v for k,v in a.items() if k!='analyses'}
  assert [p for p in a['analyses'] if p in b['analyses']]==b['analyses']
  if a==b:continue
  changes[w]={'before':b,'after':a}
  for p in a['analyses']:
   if p in b['analyses']:continue
   assert 'ending.literary_future_question_kko' in p['rules']
   additions.append({'id':'literary-future-kko-corpus-'+digest([w,p])[:24],'surface':w,'analysis':p,'source_entries':sources(p),'structural_verdict':'unjudged broader composition','contextual_verdict':'unjudged','independent_review':'pending'})
 assert changes==corpus['changed_words'] and len(corpus['corpora'])==len(prior['corpora'])==4
 for b,a in zip(prior['corpora'],corpus['corpora'],strict=True):
  for k in ['corpus','partition','source','source_sha256','report_lines','original_source_text','original_converted_rows','original_converted_rows_sha256']:assert b[k]==a[k]
  assert sha(a['original_source_text'].encode())==a['source_sha256']
  assert digest(a['original_converted_rows'])==a['original_converted_rows_sha256']
  contexts=contexts_text(a['original_source_text']);gold_changes=[]
  assert len(a['comparisons'])==len(a['original_converted_rows'])==a['report_lines']-1
  for gold,row in zip(a['original_converted_rows'],a['comparisons'],strict=True):
   for k in ['id','surface','expected']:assert gold[k]==row[k]
   w=gold['surface'];context=contexts[gold['id']];assert context['original_row'][1]==w
   locations.setdefault(w,[]).append({'source':a['source'],'source_sha256':a['source_sha256'],'id':gold['id'],**context})
   computed=[]
   for mode in ['before','after']:
    paths=corpus[mode+'_words'][w]['analyses'];matched,recovered,sets=outcome(gold['expected'],paths)
    result={'matched':matched,'recovered':recovered,'recovered_sets':sets,'candidates':len(paths)};assert row[mode]==result
    computed.append((matched,recovered,sets))
   if computed[0]!=computed[1]:gold_changes.append(row)
  assert gold_changes==a['changed_gold_outcomes']==[]
  for mode in ['before','after']:
   counts=sorted(r[mode]['candidates'] for r in a['comparisons']);n=len(counts);summary={'converted_rows':n,'grouped_matches':sum(r[mode]['matched'] for r in a['comparisons']),'recovered_gold_lemmas':sum(r[mode]['recovered'] for r in a['comparisons']),'gold_lemmas':sum(len(r['expected']) for r in a['comparisons']),'candidate_count_sum':sum(counts),'mean_candidates':sum(counts)/n,'p95_candidates':counts[min(n*95//100,n-1)],'max_candidates':max(counts)}
   assert summary==a[mode+'_summary']
  assert a['before_summary']==b['after_summary'];gold_rows+=len(a['comparisons'])
 for row in additions:row['occurrences']=locations[row['surface']]
 assert additions==corpus['candidate_changes'] and gold_rows==corpus['converted_rows']==66570
 return {'broad_frames':frames,'changed_broad_frames':changed_frames,'individually_unjudged_broad_additions':len(observations),'individually_unjudged_spacing_alternatives':len(spacing_observations),'corpus_surfaces':32096,'gold_rows':gold_rows,'changed_corpus_words':len(changes),'individually_unjudged_corpus_paths':len(additions),'changed_gold_outcomes':0,'precision_context_and_independent_review':'pending'}
if __name__=='__main__':
 print(inspect(read(ROOT/'docs/literary-future-kko-prototype-broad.json.gz'),read(ROOT/'docs/literary-future-kko-prototype-corpora.json.gz')),flush=True)
