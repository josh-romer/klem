"""Audit complete installed prototype sources and original annotated-row outcomes."""
import argparse,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from predicate_auxiliary_spacing_sources import package_source_texts_cached
from reported_dana_sources import nar_contents
from reported_deoni_complete_sources import source_store_path
from friendly_command_corpora import outcome
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def receipt_bytes(p):
 p=Path(p);return gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
def read(p):
 return json.loads(receipt_bytes(p))
def source_audit(proof,receipt):
 assert proof['state']=='passed' and proof['actual_source_profiles_verified']
 assert receipt['state']=='passed' and receipt['exit_code']==0 and receipt['source_unchanged'] and receipt['inputs_unchanged']
 assert receipt['root_head_unchanged'] and receipt['root_index_unchanged']
 assert sha(proof['producer']['text'].encode())==proof['producer']['sha256']
 assert proof['baseline']=={'proof':'docs/predicate-auxiliary-spacing-historical-sources.json.gz','proof_sha256':sha((ROOT/'docs/predicate-auxiliary-spacing-historical-sources.json.gz').read_bytes())}
 baseline=package_source_texts_cached();texts=dict(baseline);updates=proof['updates'];assert len(updates)==7 and sum(u['before_sha256'] is None for u in updates.values())==4
 for name,update in updates.items():
  assert update['before_sha256']==(sha(baseline[name].encode()) if name in baseline else None)
  assert sha(update['after_text'].encode())==update['after_sha256'];texts[name]=update['after_text']
 assert len(texts)==len(proof['snapshot_files'])==973 and set(texts)==set(proof['snapshot_files'])
 for name,text in texts.items():assert proof['snapshot_files'][name]=={'bytes':len(text.encode()),'sha256':sha(text.encode())}
 mapped=set()
 for label,profile in proof['profiles'].items():
  assert profile['package'] in receipt['outputs'] and profile['actual_dump_verified']
  assert profile['package'].endswith({'klem':'-klem-0.1.0','web-assets':'-klem-web-assets-0.1.0','corpus-adapter':'-klem-corpus-adapter-0.1.0'}[label])
  assert profile['nar_command']==['nix-store','--dump',profile['source']]
  if label!='web-assets':assert {n:{k:v for k,v in f.items() if k not in ['snapshot_path','executable']} for n,f in profile['files'].items()}==receipt['source_profile']['files']
  assert sha(profile['derivation_json_text'].encode())==profile['derivation_json_sha256']
  drv=json.loads(profile['derivation_json_text']);assert len(drv)==1 and profile['derivation'] in drv
  assert drv[profile['derivation']]['env']['src']==profile['source'] and drv[profile['derivation']]['outputs']['out']['path']==profile['package']
  assert len(profile['files'])==(18 if label=='web-assets' else 956)
  contents={}
  for name,file in profile['files'].items():
   path='web/'+name if label=='web-assets' else name;assert file['snapshot_path']==path
   assert {k:v for k,v in file.items() if k not in ['snapshot_path','executable']}==proof['snapshot_files'][path]
   assert isinstance(file['executable'],bool);mapped.add(path);contents[name]=texts[path]
  nar_hash,nar_bytes=nar_contents(profile['files'],profile['directories'],contents)
  assert nar_hash==profile['nar_sha256'] and nar_bytes==profile['nar_bytes'] and source_store_path(nar_hash)==profile['source']
 assert mapped==set(texts) and set(proof['profiles'])=={'klem','web-assets','corpus-adapter'}
 assert proof['profiles']['klem']['files']==proof['profiles']['corpus-adapter']['files'] and proof['profiles']['klem']['source']==receipt['source_profile']['source']
 return {'source_inputs':973,'rust_profile_inputs':956,'frontend_profile_inputs':18,'exact_deltas':7}
def adapter_audit(report,receipt,corpus):
 assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged']
 assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
 assert sha(report['producer']['text'].encode())==report['producer']['sha256']
 assert report['adapter_sha256']==report['frozen_inputs'][report['adapter']]
 assert report['source_profile']==receipt['source_profile']
 assert report['adapter']==next(o for o in receipt['outputs'] if o.endswith('-klem-corpus-adapter-0.1.0'))+'/bin/klem-corpus-adapter'
 assert len(report['runs'])==len(corpus['corpora'])==4;total=0
 for actual,expected in zip(report['runs'],corpus['corpora'],strict=True):
  for key in ['corpus','partition','source','source_sha256']:assert actual[key]==expected[key]
  assert actual['exit_code']==0 and actual['all_original_rows_and_candidate_summaries_bound']
  assert sha(actual['jsonl'].encode())==actual['sha256'];rows=list(map(json.loads,actual['jsonl'].splitlines()));assert len(rows)-1==actual['rows']==len(expected['original_converted_rows'])
  assert rows[0]==actual['summary'] and rows[0]['input_sha256']==expected['source_sha256']
  counts=[];matched=recovered=gold_lemmas=0
  for row,gold in zip(rows[1:],expected['original_converted_rows'],strict=True):
   for key in ['id','surface','expected']:assert row[key]==gold[key]
   analyses=corpus['after_words'][gold['surface']]['analyses'];m,r,s=outcome(gold['expected'],analyses);assert (row['matched'],row['recovered'],row['recovered_sets'])==(m,r,s)
   counts.append(len(analyses));matched+=m;recovered+=r;gold_lemmas+=len(gold['expected'])
  counts.sort();n=len(counts);derived={'converted_rows':n,'grouped_matches':matched,'recovered_gold_lemmas':recovered,'gold_lemmas':gold_lemmas,'mean_candidates':sum(counts)/n,'p95_candidates':counts[min(n*95//100,n-1)],'max_candidates':max(counts)}
  for key,value in derived.items():assert abs(rows[0][key]-value)<1e-10 and abs(expected['after_summary'][key]-value)<1e-10
  total+=n
 assert total==66570;return {'actual_original_annotated_rows':total,'partitions':4,'contextual_review':'pending'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--package',type=Path,required=True);p.add_argument('--sources',type=Path);p.add_argument('--adapter',type=Path);args=p.parse_args();receipt=read(args.package);result={}
 if args.sources:
  proof=read(args.sources);assert proof['receipt_sha256']==sha(receipt_bytes(args.package));result['sources']=source_audit(proof,receipt)
 if args.adapter:
  report=read(args.adapter);assert report['package_sha256']==sha(receipt_bytes(args.package));assert report['corpus_sha256']==sha((ROOT/'docs/literary-question-geona-prototype-corpora.json.gz').read_bytes());result['adapter']=adapter_audit(report,receipt,read(ROOT/'docs/literary-question-geona-prototype-corpora.json.gz'))
 assert result;print(json.dumps(result))
