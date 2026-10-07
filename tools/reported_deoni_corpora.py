"""Audit every preserved gold outcome and ambiguity metric against full CLI analyses."""
import copy,gzip,hashlib,json
from pathlib import Path
from doeda_native_corpora import contexts_text,gold_changes
from reported_deoni_parent import actual_parent
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(gzip.decompress((ROOT/p).read_bytes()))
sha=lambda p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

def verify_rows(rows, word_results):
 counts=[];matched=0;recovered=0;gold_total=0;transformed=0;transformed_matches=0;misses={}
 for row in rows[1:]:
  word=word_results[row['surface']];gold=row['expected'];sets=set();exact=False
  counts.append(len(word['analyses']))
  for analysis in word['analyses']:
   lemmas=[lemma['text'] for lemma in analysis['lemmas']]
   exact=exact or lemmas==gold
   indices=[]
   for lemma in lemmas:
    unused=next((i for i,g in enumerate(gold) if g==lemma and i not in indices),None)
    if unused is not None:indices.append(unused)
   if indices:sets.add(tuple(sorted(indices)))
  maximal=sorted(s for s in sets if not any(set(s)<set(other) for other in sets))
  assert row['matched']==exact,(row['id'],'matched')
  assert row['recovered_sets']==[list(s) for s in maximal],(row['id'],'recovered_sets')
  best=max(map(len,maximal),default=0)
  assert row['recovered']==best,(row['id'],'recovered')
  matched+=exact;recovered+=best;gold_total+=len(gold)
  if gold!=[word['normalized']]:transformed+=1;transformed_matches+=exact
  if not exact:
   key=(row['surface'],tuple(gold));misses[key]=misses.get(key,0)+1
 counts.sort();n=len(counts);summary=rows[0]
 expected={'converted_rows':n,'grouped_matches':matched,'gold_lemmas':gold_total,'recovered_gold_lemmas':recovered,'transformed_rows':transformed,'transformed_matches':transformed_matches,'mean_candidates':sum(counts)/n if n else 0.0,'p95_candidates':counts[min(n*95//100,n-1)] if n else 0,'max_candidates':max(counts,default=0),'grouped_lemma_recall':matched/n if n else 0.0,'lemma_recall':recovered/gold_total if gold_total else 0.0,'transformed_grouped_recall':transformed_matches/transformed if transformed else 0.0,'adapter_coverage':n/(summary['rows']-summary['excluded_rows']) if summary['rows']!=summary['excluded_rows'] else 0.0,'common_misses':[{'surface':surface,'expected':list(gold),'count':count} for (surface,gold),count in sorted(misses.items(),key=lambda pair:(-pair[1],pair[0]))[:30]]}
 for key,value in expected.items():
  actual=summary[key]
  if isinstance(value,float):assert abs(value-actual)<=1e-12,(key,value,actual)
  else:assert actual==value,(key,value,actual)
 return {'rows':n,'gold_outcomes_verified':True,'summary_fields_verified':sorted(expected),'candidate_count_sum':sum(counts)}

def verify(report):
 previous=read('docs/copula-expectation-corpora.json.gz')
 assert report['previous_report_sha256']==sha('docs/copula-expectation-corpora.json.gz')
 assert len(previous['after_words'])==len(report['after_words'])==32096
 observations=[];changed={};locations={};total=0
 for word,before in previous['after_words'].items():
  after=report['after_words'][word]
  assert {k:v for k,v in before.items() if k!='analyses'}=={k:v for k,v in after.items() if k!='analyses'}
  assert [a for a in after['analyses'] if a in before['analyses']]==before['analyses']
  if before==after:continue
  changed[word]={'before':before,'after':after}
  for path in after['analyses']:
   if path in before['analyses']:continue
   parent_surface,parent=actual_parent(word,path,report['actual_prior_companions'])
   ident=hashlib.sha256(json.dumps([word,path],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
   observations.append({'id':'reported-deoni-corpus-'+ident,'surface':word,'analysis':path,'parent_surface':parent_surface,'exact_parent':parent,'contextual_verdict':'unjudged','independent_review':'pending'})
 assert report['changed_words']==changed
 assert len(report['corpora'])==len(previous['corpora'])==4
 for run,old in zip(report['corpora'],previous['corpora'],strict=True):
  for key in ['corpus','partition','source','source_sha256','report_lines']:assert run[key]==old[key]
  original=run['original_source_text'];assert hashlib.sha256(original.encode()).hexdigest()==run['source_sha256']
  assert run['before_jsonl']==old['after_jsonl'] and run['exit_code']==0
  assert run['command'][1:]==[old['corpus'],old['source']]
  before=[json.loads(line) for line in run['before_jsonl'].splitlines()]
  after=[json.loads(line) for line in run['after_jsonl'].splitlines()]
  assert len(before)==len(after)==run['report_lines']
  for summary in [before[0],after[0]]:assert summary['input_sha256']==run['source_sha256'] and summary['input']==run['source']
  assert run['independent_cli_verification']=={'before':verify_rows(before,previous['after_words']),'after':verify_rows(after,report['after_words'])}
  context=contexts_text(original)
  assert gold_changes(before[1:],after[1:],context)==run['changed_gold_outcomes']
  assert run['changed_summary_fields']=={k:{'before':before[0].get(k),'after':after[0].get(k)} for k in set(before[0])|set(after[0]) if before[0].get(k)!=after[0].get(k)}
  for row in after[1:]:locations.setdefault(row['surface'],[]).append({'source':run['source'],'source_sha256':run['source_sha256'],'id':row['id'],**context[row['id']]})
  total+=len(after)-1
 for row in observations:row['occurrences']=locations[row['surface']]
 assert report['candidate_changes']==observations
 assert report['converted_rows']==total==66570
 assert report['after_word_sha256']==hashlib.sha256(json.dumps(report['after_words'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 print('Verified66570 unchanged annotated rows and32096 complete words;',len(changed),'changed words;',len(observations),'exact-parent additions.',flush=True)
 return total

if __name__=='__main__':verify(read('docs/reported-deoni-prototype-corpora.json.gz'))
