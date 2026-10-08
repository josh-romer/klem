"""Replay every preserved finite, full-stream, corpus and historical geona output."""
import argparse,datetime,gzip,hashlib,json,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from doeda_native_corpora import words_from_cli

def read(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cli',type=Path,required=True);parser.add_argument('--snapshot',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();CLI=args.cli.resolve();DB=ROOT/'data/dictionaries/krdict/krdict.db';OUT=args.output;assert not OUT.exists();snapshot=read(args.snapshot)['snapshot_files'];assert len(snapshot)==957;assert all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items())
 frozen={str(p):sha(p.read_bytes()) for p in [CLI,DB,Path(__file__),args.snapshot]};results=[];broad=[];words=[];r={'schema_version':1,'state':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cli':str(CLI),'cli_sha256':frozen[str(CLI)],'snapshot_files':snapshot,'finite_runs':results,'broad':broad,'words':words,'frozen_inputs':frozen,'producer':{'text':Path(__file__).read_text(),'sha256':frozen[str(Path(__file__))]},'scope':'Actual configured957-input CLI repeats every preserved finite source/boundary/typed-owner/spacing mode,8complete broad streams,32096corpus words and21406historical words. Complete archived output bytes are retained and must match exactly; no changes to gold, precision or unjudged alternatives are inferred. Full Rust, adapter, browser, packages and performance are separate.'}
 def save():OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 save()
 for family,name in [('source','prototype-source-replay'),('boundary','boundary-corrected'),('owner','owner-extension-typed'),('spacing','spacing-preflight')]:
  p=ROOT/'docs'/('literary-question-geona-'+name+'.json.gz');capture=read(p);frozen[str(p)]=sha(p.read_bytes())
  for run in capture['runs']:
   text=run.get('input',unicodedata.normalize(run['encoding'],capture.get('input','')));captured=run.get('after',run);command=list(captured['command']);command[0]=str(CLI);command[command.index('--dictionary')+1]=str(DB);job=subprocess.run(command,input=text.encode(),capture_output=True,check=True);assert job.stderr==b'' and job.stdout.decode()==captured['jsonl'],(family,run['encoding'],run['mode'])
   results.append({'family':family,'encoding':run['encoding'],'mode':run['mode'],'command':command,'input_sha256':sha(text.encode()),'jsonl_sha256':sha(job.stdout),'records':len(job.stdout.splitlines()),'expected_capture':str(p.relative_to(ROOT)),'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True,'exit_code':0})
  save();print(family,'complete finite mode replay passed',flush=True)
 p=ROOT/'docs/literary-question-geona-prototype-broad.json.gz';capture=read(p);frozen[str(p)]=sha(p.read_bytes())
 for comparison in capture['comparisons']:
  source=Path(comparison['source']);assert sha(source.read_bytes())==comparison['source_sha256'];frozen[str(source)]=comparison['source_sha256'];mode=comparison['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
  command=[str(CLI),'text',str(source),'--dictionary',str(DB),*flags,*(['--suggest-spacing'] if 'spacing' in mode else [])];job=subprocess.Popen(command,stdout=subprocess.PIPE);digest=hashlib.sha256();count=0
  try:
   for line in job.stdout:digest.update(line);count+=1
   code=job.wait();assert code==0 and count==comparison['records'] and digest.hexdigest()==comparison['after_jsonl_sha256'],mode
  finally:
   if job.poll() is None:job.terminate();job.wait()
  broad.append({'command':command,'source':str(source),'source_sha256':comparison['source_sha256'],'mode':mode,'records':count,'sha256':digest.hexdigest(),'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True,'exit_code':0});save();print(mode,count,'exact complete frames',flush=True)
 for family,name in [('corpus','prototype-corpora'),('historical','prototype-legacy-history')]:
  p=ROOT/'docs'/('literary-question-geona-'+name+'.json.gz');capture=read(p);frozen[str(p)]=sha(p.read_bytes());surfaces=sorted(capture['after_words']);actual=words_from_cli(CLI,surfaces);assert actual==capture['after_words'];digest=sha(json.dumps(actual,ensure_ascii=False,sort_keys=True).encode());assert digest==capture['after_words_sha256'];words.append({'family':family,'surfaces':len(surfaces),'actual_word_analysis_sha256':digest,'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True});save();print(family,len(surfaces),'exact WordAnalysis outputs',flush=True)
 assert len(results)==22 and sum(v['records'] for v in broad)==1128312;assert all(sha(Path(p).read_bytes())==h for p,h in frozen.items()) and all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items());r.update(state='passed',exit_code=0,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_unchanged=True);save();print('Allactual957-source CLI cohorts passed.',flush=True)
if __name__=='__main__':main()
