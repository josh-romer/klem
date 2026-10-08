"""Build and test the actual integrated Rust,assets and corpus-adapter packages."""
import datetime
import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT=Path('/home/josh/projects/klem');OUTPUT=Path('/tmp/klem-ostensible-reason-package-nix-retry1.json');LOG=OUTPUT.with_suffix('.log');assert not OUTPUT.exists() and not LOG.exists()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
profiles={label:subprocess.check_output(['nix','eval','--offline','--raw',f'.#checks.x86_64-linux.{label}.src.outPath'],cwd=ROOT,text=True).strip() for label in ['klem','web-assets','corpus-adapter']}
assert profiles['klem']==profiles['corpus-adapter']
snapshot={}
for label,source in profiles.items():
    for p in Path(source).rglob('*'):
        if not p.is_file():continue
        relative=str(p.relative_to(source));name='web/'+relative if label=='web-assets' else relative
        raw=p.read_bytes();assert raw==(ROOT/name).read_bytes(),(label,name)
        snapshot[name]={'sha256':sha(raw),'bytes':len(raw)}
assert len(snapshot)==924,len(snapshot)
command=['nix','build','--offline','--option','build-dir','/var/tmp/klem-degree-expectation-nix-build','--cores','4','--max-jobs','2','--no-link','--print-out-paths','-L',*[f'.#checks.x86_64-linux.{label}' for label in profiles]]
producer=Path(__file__);receipt={'schema_version':1,'state':'running','pid':os.getpid(),'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':command,'source_profiles':profiles,'snapshot':{'files':snapshot},'producer':{'text':producer.read_text(),'sha256':sha(producer.read_bytes())},'scope':'Actual independent Nix Rust/CLI/server and SolidJS assets,plus the separate corpus-adapter package sharing exact907 Rust inputs. All924 compile/frontend source bytes frozen; full Rust release tests run for main library and CLI. Inventory/doc/runtime/browser/performance gates remain separate; no contextual or precision claim.'}
OUTPUT.write_text(json.dumps(receipt,indent=2)+'\n');env=os.environ.copy();env['TMPDIR']='/var/tmp/klem-degree-expectation-nix-build'
with LOG.open('xb') as stream:result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
receipt.update(state='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),snapshot_unchanged=all(sha((ROOT/name).read_bytes())==row['sha256'] for name,row in snapshot.items()),log_sha256=sha(LOG.read_bytes()),outputs=[line for line in LOG.read_text().splitlines() if line.startswith('/nix/store/')])
OUTPUT.write_text(json.dumps(receipt,indent=2)+'\n');print('Actual integrated ostensible Nix packages:',receipt['state'],'exit',result.returncode,'frozen924:',receipt['snapshot_unchanged'],flush=True)
assert receipt['snapshot_unchanged']
if result.returncode==0:assert len(receipt['outputs'])==3
raise SystemExit(result.returncode)
