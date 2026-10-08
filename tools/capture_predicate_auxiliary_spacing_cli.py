"""Replay all actual main finite, broad and word outputs through the installed CLI."""
import argparse,datetime,gzip,hashlib,json,subprocess,sys,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));from doeda_native_corpora import words_from_cli
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def read(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();assert not args.output.exists();package=read(args.package);assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
CLI=Path(next(p for p in package['outputs'] if p.endswith('-klem-0.1.0')))/'bin/klem';DB=ROOT/'data/dictionaries/krdict/krdict.db';snapshot=package['snapshot']['files'];assert len(snapshot)==969 and all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items());frozen={str(p):sha(p.read_bytes()) for p in [CLI,DB,args.package,Path(__file__)]};finite=[];broad=[];words=[]
r={'state':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'cli':str(CLI),'cli_sha256':sha(CLI.read_bytes()),'snapshot_files':snapshot,'package_sha256':sha(args.package.read_bytes()),'finite_runs':finite,'broad':broad,'words':words,'frozen_inputs':frozen,'producer':{'text':Path(__file__).read_text(),'sha256':sha(Path(__file__).read_bytes())},'scope':'Actual installed969-input CLI against unchanged main source/boundary observations, complete8broadstreams and both complete word cohorts. Additional typed-owner and spacing captures remain separate unless explicitly listed. No contextual/precision certification.'}
def save():args.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
save()
for family,name in [('source','main-source-replay'),('boundary','main-boundary-preflight')]:
 path=ROOT/'docs'/('additive-ppundeoreo-'+name+'.json.gz');capture=read(path);frozen[str(path)]=sha(path.read_bytes())
 if family=='source':text=read(ROOT/'docs/additive-ppundeoreo-source-discovery.json.gz')['input']
 else:text=' '.join(dict.fromkeys(c['surface'] for c in read(ROOT/'tests/fixtures/additive-ppundeoreo-authored-boundaries.json')['cases']))
 for old in capture['runs']:
  encoded=unicodedata.normalize(old['encoding'],text).encode();assert sha(encoded)==old['input_sha256'];command=list(old['command']);command[0]=str(CLI);p=subprocess.run(command,input=encoded,capture_output=True,check=True);assert p.stderr==b'' and p.stdout.decode()==old['jsonl'];finite.append({'family':family,'encoding':old['encoding'],'mode':old['mode'],'command':command,'input_sha256':sha(encoded),'output_sha256':sha(p.stdout),'records':len(p.stdout.splitlines()),'exit_code':0,'exact_captured_output':True,'expected_capture':str(path.relative_to(ROOT)),'expected_capture_sha256':frozen[str(path)]})
 save();print(family,'all6actual installed modes exact',flush=True)
path=ROOT/'docs/predicate-auxiliary-spacing-main-broad.json.gz';capture=read(path);frozen[str(path)]=sha(path.read_bytes())
for old in capture['comparisons']:
 source=Path(old['source']);assert sha(source.read_bytes())==old['source_sha256'];frozen[str(source)]=sha(source.read_bytes());command=list(old['commands'][1]);command[0]=str(CLI);p=subprocess.Popen(command,stdout=subprocess.PIPE);h=hashlib.sha256();count=0
 try:
  for line in p.stdout:h.update(line);count+=1
  code=p.wait();assert code==0 and count==old['records'] and h.hexdigest()==old['after_jsonl_sha256']
 finally:
  if p.poll() is None:p.terminate();p.wait()
 broad.append({'mode':old['mode'],'source':str(source),'source_sha256':old['source_sha256'],'command':command,'records':count,'output_sha256':h.hexdigest(),'exit_code':code,'exact_captured_output':True});save();print(old['mode'],count,'exact frames',flush=True)
path=ROOT/'docs/additive-ppundeoreo-main-corpus-history.json.gz';capture=read(path);frozen[str(path)]=sha(path.read_bytes())
for old in capture['cohorts']:
 actual=words_from_cli(CLI,sorted(old['after_words']));assert actual==old['after_words'];digest=sha(json.dumps(actual,ensure_ascii=False,sort_keys=True).encode());assert digest==old['after_word_sha256'];words.append({'family':old['family'],'surfaces':len(actual),'word_sha256':digest,'exact_captured_output':True});save();print(old['family'],len(actual),'exact words',flush=True)
assert len(finite)==12 and sum(row['records'] for row in broad)==1128312 and all(sha(Path(p).read_bytes())==v for p,v in frozen.items());assert all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in snapshot.items());r.update(state='passed',exit_code=0,inputs_unchanged=True,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat());save()
