"""Replay every prototype stream and retain older source-cohort assessments."""
import argparse
import copy
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path
from copula_expectation_production import ROOT,read,sha,replay
from doeda_native_corpora import words_from_cli
from reported_deoni_parent import actual_parent,frame


def capture(cli,output):
 cli=Path(cli).resolve();evaluator=cli.parent/'examples/evaluate'
 db=ROOT/'data/dictionaries/krdict/krdict.db'
 inputs=['docs/reported-deoni-prototype-source-streams.json.gz',
         'docs/reported-deoni-prototype-corpora.json.gz',
         'docs/reported-deoni-prototype-broad.json.gz',
         'docs/copula-expectation-source-streams.json.gz',
         'src/engine.rs','src/grammar.rs','src/dictionary/attachment.rs',
         'web/src/grammar-labels.json']
 frozen={path:sha(ROOT/path) for path in inputs}
 binaries={str(path):sha(path) for path in [cli,evaluator,db]}
 source=read(inputs[0]);source_runs=[]
 for encoding,modes in source['runs'].items():
  request=unicodedata.normalize(encoding,source['input'])
  for mode,stages in modes.items():
   old=stages['after'];command=[str(cli),*old['command'][1:]]
   records=len(old['jsonl'].splitlines())
   result=replay(command,old['sha256'],records,request)
   source_runs.append({'encoding':encoding,'mode':mode,
                       'input_sha256':hashlib.sha256(request.encode()).hexdigest(),**result})
   print('source',encoding,mode,records,flush=True)
 corpus=read(inputs[1]);corpus_runs=[]
 for old in corpus['corpora']:
  assert sha(ROOT/old['source'])==old['source_sha256']
  result=replay([str(evaluator),old['corpus'],old['source']],
                hashlib.sha256(old['after_jsonl'].encode()).hexdigest(),old['report_lines'])
  corpus_runs.append({key:old[key] for key in ['corpus','partition','source','source_sha256']}|result)
  print('corpus',old['corpus'],old['partition'],old['report_lines']-1,flush=True)
 words=words_from_cli(cli,sorted(corpus['after_words']))
 assert words==corpus['after_words'] and len(words)==32096
 broad=read(inputs[2]);broad_runs=[]
 for old in broad['comparisons']:
  assert sha(old['source'])==old['source_sha256']
  result=replay([str(cli),*old['commands'][1][1:]],old['after_jsonl_sha256'],old['records'])
  broad_runs.append({key:old[key] for key in ['source','source_sha256','mode']}|result)
  print('broad',old['mode'],old['records'],flush=True)
 # Replay the earlier degree/counterfactual cohorts as well. New reported paths
 # require actual old package companions; all prior dictionary readings survive.
 legacy=read(inputs[3]);legacy_runs=[];parents={}
 for report in [source,corpus,broad]:parents.update(report['actual_prior_companions'])
 old_cli='/nix/store/al7vdmyi8h0gsjbnz59qab3vvskkrj0l-klem-0.1.0/bin/klem'
 binaries[old_cli]=sha(old_cli)
 def parent_for(word,path):
  try:return actual_parent(word,path,parents)
  except AssertionError as error:
   detail=error.args[0]
   if not isinstance(detail,tuple) or len(detail)!=4:raise
   for proposal in detail[3]:
    if proposal not in parents:
     parents[proposal]=json.loads(subprocess.check_output([old_cli,'word',proposal],text=True,cwd=ROOT))
   return actual_parent(word,path,parents)
 for family,report in legacy['reports'].items():
  prior_path=f'docs/{family}-cohort.json.gz';original=read(prior_path)
  assert sha(ROOT/prior_path)==report['prior_cohort_sha256']
  for encoding,modes in report['runs'].items():
   request=unicodedata.normalize(encoding,original['input'])
   for mode,old in modes.items():
    command=[str(cli),*old['command'][1:]]
    result=subprocess.run(command,input=request,text=True,capture_output=True,check=True,cwd=ROOT)
    before=[json.loads(line) for line in old['after_jsonl'].splitlines()]
    after=[json.loads(line) for line in result.stdout.splitlines()]
    assert len(before)==len(after)==old['records']
    assert ''.join(row['surface'] for row in after)==request
    changed=[]
    for index,(b,a) in enumerate(zip(before,after,strict=True)):
     if b==a:continue
     assert a['kind']=='word'
     for path in a['analysis']['analyses']:
      if path not in b['analysis']['analyses']:parent_for(a['analysis']['normalized'],path)
     additions=frame(b,a,parents);assert additions
     changed.append({'record':index,'before':b,'after':a})
    legacy_runs.append({'family':family,'encoding':encoding,'mode':mode,'command':command,
                        'exit_code':result.returncode,'records':len(after),
                        'prior_stream_sha256':old['after_sha256'],
                        'sha256':hashlib.sha256(result.stdout.encode()).hexdigest(),
                        'input_sha256':hashlib.sha256(request.encode()).hexdigest(),
                        'changed_frames':changed})
    print('legacy',family,encoding,mode,len(after),'frames;',len(changed),'changed.',flush=True)
 assert len(source_runs)==6 and sum(r['records'] for r in source_runs)==378774
 assert len(corpus_runs)==4 and sum(r['records']-1 for r in corpus_runs)==66570
 assert len(broad_runs)==8 and sum(r['records'] for r in broad_runs)==1128312
 assert len(legacy_runs)==12 and sum(r['records'] for r in legacy_runs)==309660
 assert all(sha(ROOT/path)==value for path,value in frozen.items())
 assert all(sha(path)==value for path,value in binaries.items())
 producer=Path(__file__)
 report={'schema_version':1,'state':'passed','prototype_parity':True,'frozen_inputs':frozen,
         'binaries':binaries,'source_runs':source_runs,'corpus_runs':corpus_runs,
         'corpus_words':len(words),'corpus_word_sha256':hashlib.sha256(json.dumps(words,ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
         'broad_runs':broad_runs,'legacy_source_runs':legacy_runs,
         'legacy_actual_companions':parents,'inputs_unchanged':True,
         'producer':{'text':producer.read_text(),'sha256':sha(producer)},
         'scope':'Actual integrated CLI/evaluator exact prototype stream and full-word parity; older source cohorts retain prior paths/readings with exact actual old counterparts for additions. Source, corpus and structural outcomes remain separate from contextual/independent certification.'}
 output=Path(output);assert not output.exists();output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print('Integrated production parity passes all source/corpus/broad streams and prior source preservation.',flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cli',required=True);parser.add_argument('--output',required=True)
 args=parser.parse_args();capture(args.cli,args.output)
