"""Verify the complete unchanged broad and annotated-word cohorts independently."""
import gzip,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):
 raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def word_digest(words):return sha(json.dumps(words,ensure_ascii=False,sort_keys=True).encode())
def inspect(broad,cohorts,prior_broad,prior_corpus,prior_history,*,phase="isolated"):
 assert phase in ["isolated","main"]
 main=phase=="main"
 cli="/tmp/klem-additive-ppundeoreo-"+("main-cli" if main else "current-cli")
 assert broad['state']==('main-complete-broad-preservation-passed' if main else 'prototype-complete-broad-preservation-passed')
 assert cohorts['state']=='passed'
 for report,name in [(broad,'main-broad' if main else 'prototype-broad'),(cohorts,'main-corpus-history' if main else 'corpus-history')]:
  assert report['preparation_only'] is (not main) and report['inputs_unchanged'] is True
  assert sha(report['producer']['text'].encode())==report['producer']['sha256']
  assert report['producer']['text']==gzip.decompress((ROOT/'docs'/('additive-ppundeoreo-'+name+'.py.gz')).read_bytes()).decode()
  assert report['cli_sha256']==read(ROOT/'docs'/('additive-ppundeoreo-'+('main-binaries' if main else 'current-binaries')+'.json.gz'))['binaries']['cli']['sha256']
  assert report['cli_sha256']==report['frozen_inputs'][cli]
  for cohort in report.get('cohorts',[]):assert report['frozen_inputs'][cohort['baseline_capture']]==cohort['baseline_sha256']
 assert broad['contextual_verdict']=='unjudged' and broad['independent_review']=='pending'
 assert broad['individual_additions']==broad['individual_spacing_additions']==cohorts['individual_additions']==[]
 assert broad['prior_capture_sha256']==sha((ROOT/'docs/literary-question-geona-prototype-broad.json.gz').read_bytes())
 assert broad['before_cli_sha256']==read(ROOT/'docs/literary-question-geona-packaged-cli-replay.json')['cli_sha256']
 assert len(broad['comparisons'])==len(prior_broad['comparisons'])==8
 for row,old in zip(broad['comparisons'],prior_broad['comparisons'],strict=True):
  for key in ['source','source_sha256','mode','records']:assert row[key]==old[key],key
  original=read(ROOT/'docs/literary-question-go-broad-inputs.json.gz')['sources'][row['source_sha256']]
  raw=original['text'].encode();assert row['source'] in original['original_paths']
  assert len(raw)==original['bytes'] and sha(raw)==row['source_sha256']
  assert row['before_jsonl_sha256']==row['after_jsonl_sha256']==row['previous_capture_after_sha256']==old['after_jsonl_sha256']
  assert row['exit_codes']==[0,0] and row['changed_frames']==[]
  assert row['baseline_matches_previous_capture'] is True and row['original_bytes_conserved'] is True and row['previous_spacing_suggestions_conserved'] is True
  expected=[]
  for cli in ['/nix/store/cc0wxddigm591zabxi46lli9x8s0kfpd-klem-0.1.0/bin/klem',cli]:
   mode=row['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
   expected.append([cli,'text',row['source'],'--dictionary','/home/josh/projects/klem/data/dictionaries/krdict/krdict.db',*flags,*(['--suggest-spacing'] if 'spacing' in mode else [])])
  assert row['commands']==expected
 assert sum(r['records'] for r in broad['comparisons'])==1128312
 assert cohorts['cli']==cli
 assert len(cohorts['cohorts'])==2
 for row,family,old,count,suffix in zip(cohorts['cohorts'],['corpus','history'],[prior_corpus,prior_history],[32096,21406],['prototype-corpora','prototype-legacy-history'],strict=True):
  assert row['family']==family and row['surfaces']==len(row['before_words'])==len(row['after_words'])==count
  path=ROOT/'docs'/('literary-question-geona-'+suffix+'.json.gz')
  assert row['baseline_capture']=='/home/josh/projects/klem/docs/'+path.name and row['baseline_sha256']==sha(path.read_bytes())
  assert row['before_words']==row['after_words']==old['after_words']
  assert row['all_prior_candidates_retained'] is True and row['exact_prior_words'] is True
  assert row['before_word_sha256']==word_digest(row['before_words'])==row['after_word_sha256']==word_digest(row['after_words'])==old['after_words_sha256']
 return {'phase':phase,'broad_streams':8,'broad_frames':1128312,'corpus_words':32096,'historical_words':21406,'new_paths':0,'new_spacing':0,'scope':'Exact retained outputs in the finite frozen corpora; no general precision or unseen-text claim.'}
def inputs(*,phase="isolated"):return [read(ROOT/'docs'/('additive-ppundeoreo-'+n+'.json.gz')) for n in (['main-broad','main-corpus-history'] if phase=='main' else ['prototype-broad','corpus-history'])]+[read(ROOT/'docs'/('literary-question-geona-'+n+'.json.gz')) for n in ['prototype-broad','prototype-corpora','prototype-legacy-history']]
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--phase',choices=['isolated','main'],default='isolated');args=parser.parse_args();print(inspect(*inputs(phase=args.phase),phase=args.phase),flush=True)
