"""Replay all finite, broad and old surface cohorts against the actual integrated CLI."""
import argparse,datetime,gzip,hashlib,json,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from doeda_native_corpora import words_from_cli
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--cli',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
CLI=args.cli.resolve();DB=ROOT/'data/dictionaries/krdict/krdict.db';OUT=args.output;assert not OUT.exists()
read=lambda p:json.loads(gzip.decompress(Path(p).read_bytes()) if str(p).endswith('.gz') else Path(p).read_bytes())
sha=lambda raw:hashlib.sha256(raw).hexdigest()
integration=read(ROOT/'docs/literary-future-kko-main-integration.json.gz');snapshot=integration['snapshot_files'];assert len(snapshot)==947
assert all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items())
frozen={str(p):sha(p.read_bytes()) for p in [CLI,DB,Path(__file__)]};results=[];broad_runs=[];words=[]
r={'schema_version':1,'state':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cli':str(CLI),'cli_sha256':frozen[str(CLI)],'snapshot_files':snapshot,'finite_runs':results,'broad':broad_runs,'words':words,'frozen_inputs':frozen,'producer':{'text':Path(__file__).read_text(),'sha256':sha(Path(__file__).read_bytes())},'scope':'Actual configured current CLI replay of every previously captured finite source/boundary/owner-extension/spacing mode, eight complete broad streams and all old corpus/historical surfaces. Actual outputs must equal the preserved isolated captures byte for byte or structurally for WordAnalysis calls. Hash-only receipts bind those already archived complete outputs; no new judgments or gold changes are inferred. Package/adapter/browser/performance and full main Rust validation are separate.'}
def save():OUT.write_text(json.dumps(r,indent=2)+'\n')
save()
for family,name in [('source','prototype-source-replay'),('boundary','boundary-preflight'),('owner','owner-extension-preflight'),('spacing','spacing-preflight-retry1')]:
 p=ROOT/'docs'/('literary-future-kko-'+name+'.json.gz');expected=read(p);frozen[str(p)]=sha(p.read_bytes())
 for run in expected['runs']:
  mode=run['mode'];flags=['--dict-compatible'] if mode=='compatible' else ['--dict-only'] if mode=='headword' else []
  if family=='spacing':flags.append('--suggest-spacing')
  text=run['input'] if family=='spacing' else unicodedata.normalize(run['encoding'],expected.get('input',read(ROOT/'docs/literary-future-kko-source-discovery.json.gz')['input']) if family=='source' else expected['input'])
  command=[str(CLI),'text','-','--dictionary',str(DB),*flags];job=subprocess.run(command,input=text.encode(),capture_output=True,check=True)
  old=run['after']['jsonl'] if family=='spacing' else run['jsonl']
  assert job.stdout.decode()==old,(family,run['encoding'],mode)
  results.append({'family':family,'encoding':run['encoding'],'mode':mode,'command':command,'input_sha256':sha(text.encode()),'jsonl_sha256':sha(job.stdout),'records':len(job.stdout.splitlines()),'expected_capture':str(p.relative_to(ROOT)),'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True,'exit_code':0})
 save();print(family,'complete mode replay passed',flush=True)
p=ROOT/'docs/literary-future-kko-prototype-broad.json.gz';expected=read(p);frozen[str(p)]=sha(p.read_bytes())
for run in expected['comparisons']:
 path=Path(run['source']);assert sha(path.read_bytes())==run['source_sha256'];frozen[str(path)]=run['source_sha256'];mode=run['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
 command=[str(CLI),'text',str(path),'--dictionary',str(DB),*flags,*(['--suggest-spacing'] if 'spacing' in mode else [])]
 job=subprocess.Popen(command,stdout=subprocess.PIPE);h=hashlib.sha256();count=0
 try:
  for line in job.stdout:h.update(line);count+=1
  code=job.wait();assert code==0 and count==run['records'] and h.hexdigest()==run['after_jsonl_sha256']
 finally:
  if job.poll() is None:job.terminate();job.wait()
 broad_runs.append({'command':command,'source':run['source'],'source_sha256':run['source_sha256'],'mode':mode,'records':count,'sha256':h.hexdigest(),'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True,'exit_code':code});save();print(mode,count,'exact integrated frames',flush=True)
for family,name in [('corpus','prototype-corpora'),('historical','prototype-legacy-history-retry1')]:
 p=ROOT/'docs'/('literary-future-kko-'+name+'.json.gz');capture=read(p);frozen[str(p)]=sha(p.read_bytes());surfaces=sorted(capture['after_words']);actual=words_from_cli(CLI,surfaces);assert actual==capture['after_words']
 digest=sha(json.dumps(actual,ensure_ascii=False,sort_keys=True).encode());assert digest==capture['after_words_sha256']
 words.append({'family':family,'surfaces':len(surfaces),'actual_word_analysis_sha256':digest,'expected_capture_sha256':frozen[str(p)],'exact_captured_output':True});save();print(family,len(surfaces),'exact integrated WordAnalysis outputs',flush=True)
assert all(sha(Path(p).read_bytes())==h for p,h in frozen.items()) and all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items())
r.update(state='passed',exit_code=0,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_unchanged=True);save();print('Actual configured complete CLI replay passed;947inputs unchanged.',flush=True)
