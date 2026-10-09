"""Capture the actual four-check current-flake Nix gate with frozen Root inputs."""
import datetime,hashlib,json,os,subprocess
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prefix',type=Path,required=True);args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1];PREFIX=args.prefix;PREFIX.parent.mkdir(parents=True,exist_ok=True);OUT=Path(str(PREFIX)+'.json');LOG=Path(str(PREFIX)+'.log');assert not OUT.exists() and not LOG.exists()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=subprocess.check_output(['nix','eval','--offline','--raw','.#checks.x86_64-linux.inventory-review.src'],cwd=ROOT,text=True).strip();assert source.startswith('/nix/store/') and source.endswith('-source')
inputs={};source_files={}
for p in Path(source).rglob('*'):
 assert not p.is_symlink()
 if not p.is_file():continue
 name=str(p.relative_to(source));raw=p.read_bytes();assert (ROOT/name).read_bytes()==raw,name
 source_files[name]={'bytes':len(raw),'sha256':sha(raw)}
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')[:-1]
for name in tracked:
 raw=(ROOT/name).read_bytes();inputs[name]={'bytes':len(raw),'sha256':sha(raw)}
assert set(source_files)<=set(inputs)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();index=sha(subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT))
assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
Path('/tmp/klem-inventory-gate-build').mkdir(exist_ok=True)
command=['nix','build','--offline','--option','build-dir','/tmp/klem-inventory-gate-build','--cores','4','--max-jobs','1','--no-link','--print-out-paths','-L','.#checks.x86_64-linux.klem','.#checks.x86_64-linux.web-assets','.#checks.x86_64-linux.corpus-adapter','.#checks.x86_64-linux.inventory-review']
producer=Path(__file__);r={'schema_version':1,'state':'running','started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':os.getpid(),'command':command,'head':head,'index_sha256':index,'snapshot_files':inputs,'inventory_source':source,'inventory_source_files':source_files,'flake_sha256':sha((ROOT/'flake.nix').read_bytes()),'producer':{'text':producer.read_text(),'sha256':sha(producer.read_bytes())},'scope':'Actual complete four-check current-flake gate after declarative-dao integration, completed package/source/runtime/browser/adapter/performance checks and final queue regeneration and exact DAO-aware historical ledger audit repair and queue regenerated after final evidence updates evaluated and built using the actual committed Git-backed flake. All selected inventory source files and all tracked Root files/HEAD/index are frozen and compared before and after. Main CLI/server, frontend and adapter package checks are the actual independent Nix outputs; the complete inventory derivation runs every wired audit/control. This gate does not close broader linguistic coverage, precision or independent contextual review.'}
def save():OUT.write_text(json.dumps(r,indent=2)+'\n')
save();env=os.environ.copy();env['TMPDIR']='/tmp/klem-inventory-gate-build'
with LOG.open('xb') as stream:job=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
r.update(state='passed' if job.returncode==0 else 'failed',exit_code=job.returncode,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),inputs_unchanged=all(sha((ROOT/n).read_bytes())==v['sha256'] for n,v in inputs.items()),head_unchanged=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==head,index_unchanged=sha(subprocess.check_output(['git','ls-files','--stage','-z'],cwd=ROOT))==index,log_sha256=sha(LOG.read_bytes()),outputs=[line for line in LOG.read_text().splitlines() if line.startswith('/nix/store/')])
save();print('Actual combined four-check Nix gate:',r['state'],'exit',job.returncode,'Root inputs frozen:',r['inputs_unchanged'],'HEAD/index:',r['head_unchanged'],r['index_unchanged'],flush=True)
assert r['inputs_unchanged'] and r['head_unchanged'] and r['index_unchanged']
if job.returncode==0:assert len(r['outputs'])==4
raise SystemExit(job.returncode)
