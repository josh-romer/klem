"""Derive every installed spacing adapter outcome from original annotated rows."""
import gzip,hashlib,json
from pathlib import Path
from friendly_command_corpora import outcome
ROOT=Path(__file__).resolve().parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def inspect(report,corpus):
 assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
 assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
 assert report['producer']['text']==(ROOT/'tools/capture_predicate_auxiliary_spacing_adapter.py').read_text()
 assert sha(report['producer']['text'].encode())==report['producer']['sha256']
 assert report['adapter_sha256']==report['frozen_inputs'][report['adapter']]
 receipt=json.loads((ROOT/'docs/predicate-auxiliary-spacing-package-nix.json').read_bytes())
 assert report['package_sha256']==sha((ROOT/'docs/predicate-auxiliary-spacing-package-nix.json').read_bytes())
 assert report['snapshot_files']==receipt['snapshot']['files'] and len(report['snapshot_files'])==969
 assert report['adapter']==next(p for p in receipt['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))+'/bin/klem-corpus-adapter'
 assert report['corpus_sha256']==sha((ROOT/'docs/literary-question-geona-prototype-corpora.json.gz').read_bytes())
 assert len(report['runs'])==len(corpus['corpora'])==4
 total=0
 for actual,expected in zip(report['runs'],corpus['corpora'],strict=True):
  for k in ['corpus','partition','source','source_sha256']:assert actual[k]==expected[k]
  assert actual['exit_code']==0 and actual['all_original_rows_and_candidate_summaries_bound'] is True
  assert sha(actual['jsonl'].encode())==actual['sha256']
  rows=list(map(json.loads,actual['jsonl'].splitlines()));assert len(rows)-1==actual['rows']==len(expected['original_converted_rows'])
  assert rows[0]==actual['summary'] and rows[0]['input_sha256']==expected['source_sha256']
  counts=[];matches=0;recovered=0;gold_lemmas=0
  for row,gold in zip(rows[1:],expected['original_converted_rows'],strict=True):
   for k in ['id','surface','expected']:assert row[k]==gold[k]
   paths=corpus['after_words'][gold['surface']]['analyses'];m,r,s=outcome(gold['expected'],paths);assert (row['matched'],row['recovered'],row['recovered_sets'])==(m,r,s)
   counts.append(len(paths));matches+=m;recovered+=r;gold_lemmas+=len(gold['expected'])
  counts.sort();n=len(counts);derived={'converted_rows':n,'grouped_matches':matches,'recovered_gold_lemmas':recovered,'gold_lemmas':gold_lemmas,'mean_candidates':sum(counts)/n,'p95_candidates':counts[min(n*95//100,n-1)],'max_candidates':max(counts)}
  for k,v in derived.items():assert abs(rows[0][k]-v)<1e-10 and abs(expected['after_summary'][k]-v)<1e-10,k
  total+=n
 assert total==66570
 return {'phase':'installed-spacing-package','actual_rust_adapter_original_rows':total,'partitions':4,'all_original_gold_outcomes_and_current_candidate_summaries_bound':True,'precision_context_and_independent_review':'pending'}
