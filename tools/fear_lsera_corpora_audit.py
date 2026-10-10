"""Recompute all original gold outcomes from complete current cohort candidates."""
import gzip,hashlib,json
from pathlib import Path
from friendly_command_corpora import outcome
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):
 raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def inspect(report,prior,original,cohorts):
 assert report['state']=='passed' and report['inputs_unchanged'],'terminal actual adapter'
 assert sha(report['producer']['text'].encode())==report['producer']['sha256'],'actual adapter producer'
 assert report['adapter'] in report['frozen_inputs'],'actual adapter identity'
 assert len(report['runs'])==len(prior['runs'])==len(original['corpora'])==4,'complete gold partitions'
 words=next(r for r in cohorts['runs'] if r['family']=='corpus')['captures'][1]['words']
 changes=[];total=0
 for run,previous,source in zip(report['runs'],prior['runs'],original['corpora'],strict=True):
  for k in ['corpus','partition','source','source_sha256']:
   assert run[k]==previous[k]==source[k],'original partition identity'
  assert sha(source['original_source_text'].encode())==run['source_sha256'],'original source text'
  assert run['exit_code']==0 and run['command']==[report['adapter'],run['corpus'],run['source']],'actual adapter command'
  assert sha(run['jsonl'].encode())==run['stdout_sha256'],'complete adapter capture digest'
  rows=[json.loads(x) for x in run['jsonl'].splitlines()];old=[json.loads(x) for x in previous['jsonl'].splitlines()]
  gold=source['original_converted_rows'];n=len(gold)
  assert len(rows)==len(old)==n+1 and run['rows']==n,'all original gold rows'
  counts=[];matched=0;recovered=0;gold_count=0
  for row,before,expected in zip(rows[1:],old[1:],gold,strict=True):
   assert {k:row[k] for k in ['id','surface','expected']}=={k:expected[k] for k in ['id','surface','expected']},'unaltered original gold identity'
   paths=words[expected['surface']]['analyses'];m,r,s=outcome(expected['expected'],paths)
   assert (row['matched'],row['recovered'],row['recovered_sets'])==(m,r,s),'independently derived gold recovery'
   assert row==before,'unchanged complete original row'
   counts.append(len(paths));matched+=m;recovered+=r;gold_count+=len(expected['expected'])
   if row!=before:changes.append({'id':row['id'],'corpus':run['corpus'],'partition':run['partition'],'before':before,'after':row,'contextual_verdict':'unjudged'})
  counts.sort();derived={'converted_rows':n,'grouped_matches':matched,'recovered_gold_lemmas':recovered,'gold_lemmas':gold_count,'mean_candidates':sum(counts)/n,'p95_candidates':counts[min(n*95//100,n-1)],'max_candidates':max(counts)}
  for k,v in derived.items():assert abs(rows[0][k]-v)<1e-10,'independently derived candidate statistics'
  assert rows[0]==old[0] and not run['summary_changes'],'unchanged complete summary'
  assert rows[0]['input_sha256']==run['source_sha256'],'original summary input'
  total+=n
 assert total==66570 and report['individual_changed_rows']==changes==[],'complete unchanged row accounting'
 return {'original_gold_rows':total,'partitions':4,'changed_rows':0,'contextual_and_independent_review':'pending'}
def inputs():
 return [read(ROOT/'docs'/p) for p in ['fear-lsera-corpora.json.gz','familiar-geurae-corpora.json.gz','literary-question-geona-prototype-corpora.json.gz','fear-lsera-cohorts.json.gz']]
if __name__=='__main__':print(inspect(*inputs()))
