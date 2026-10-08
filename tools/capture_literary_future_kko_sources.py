"""Preserve exact tested literary-future-question source profiles before the next rule integration."""
import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from reported_deoni_complete_sources import source_store_path
sha=lambda raw:hashlib.sha256(raw).hexdigest()
read=lambda p:json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
OUTPUT=Path('/tmp/klem-literary-future-kko-historical-sources.json.gz');assert not OUTPUT.exists()
receipt_path=ROOT/'docs/literary-future-kko-package-nix.json';receipt=read(receipt_path)
baseline_path=ROOT/'docs/literary-question-go-historical-sources.json.gz';baseline=read(baseline_path)
assert receipt['state']=='passed' and receipt['exit_code']==0
snapshot=receipt['snapshot']['files'];assert len(snapshot)==947
updates={}
for name,record in snapshot.items():
    raw=(ROOT/name).read_bytes();assert sha(raw)==record['sha256'] and len(raw)==record['bytes']
    old=baseline['snapshot_files'].get(name)
    if old!=record:
        updates[name]={'before_sha256':old['sha256'] if old else None,'after_sha256':sha(raw),'after_text':raw.decode()}
assert len(updates)==15 and set(baseline['snapshot_files'])<=set(snapshot)
profiles={};mapped=set()
for label,source,output in [
    ('klem',receipt['source_profiles']['klem'],next(p for p in receipt['outputs'] if p.endswith('-klem-0.1.0'))),
    ('web-assets',receipt['source_profiles']['web-assets'],next(p for p in receipt['outputs'] if p.endswith('-klem-web-assets-0.1.0'))),
    ('corpus-adapter',receipt['source_profiles']['corpus-adapter'],next(p for p in receipt['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0')))]:
    derivation=subprocess.check_output(['nix-store','--query','--deriver',output],text=True).strip()
    drv_text=subprocess.check_output(['nix','derivation','show',derivation],text=True)
    drv=json.loads(drv_text);assert len(drv)==1 and derivation in drv
    assert drv[derivation]['env']['src']==source and drv[derivation]['outputs']['out']['path']==output
    files={};directories=[]
    for path in Path(source).rglob('*'):
        assert not path.is_symlink();relative=str(path.relative_to(source))
        if path.is_dir():directories.append(relative);continue
        name='web/'+relative if label=='web-assets' else relative
        record=snapshot[name];raw=path.read_bytes();assert sha(raw)==record['sha256'] and len(raw)==record['bytes']
        files[relative]=dict(record,snapshot_path=name,executable=bool(path.stat().st_mode&0o111));mapped.add(name)
    assert len(files)==(18 if label=='web-assets' else 930)
    command=['nix-store','--dump',source];job=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);h=hashlib.sha256();count=0
    while chunk:=job.stdout.read(1048576):h.update(chunk);count+=len(chunk)
    error=job.stderr.read();assert job.wait()==0,error
    assert source_store_path(h.hexdigest())==source
    profiles[label]={'source':source,'package':output,'derivation':derivation,'derivation_json_text':drv_text,'derivation_json_sha256':sha(drv_text.encode()),
                     'files':files,'directories':sorted(directories),'nar_sha256':h.hexdigest(),'nar_bytes':count,'nar_command':command,'actual_dump_verified':True}
    print(label,len(files),'actual exact source files;',count,'NAR bytes',flush=True)
assert mapped==set(snapshot) and profiles['klem']['files']==profiles['corpus-adapter']['files']
assert profiles['klem']['nar_sha256']==profiles['corpus-adapter']['nar_sha256']
assert all(sha((ROOT/name).read_bytes())==record['sha256'] for name,record in snapshot.items())
producer=Path(__file__)
report={'schema_version':1,'state':'passed','receipt_sha256':sha(receipt_path.read_bytes()),
        'baseline':{'proof':'docs/literary-question-go-historical-sources.json.gz','proof_sha256':sha(baseline_path.read_bytes())},
        'snapshot_files':snapshot,'updates':updates,'profiles':profiles,'current_inputs_unchanged':True,
        'producer':{'text':producer.read_text(),'sha256':sha(producer.read_bytes())},
        'scope':'Exact historical reconstruction delta for all947 tested literary-future-kko source inputs. Actual main Rust,frontend and separately built corpus-adapter derivations/source NARs are independently retained. This prepares continued rule development without changing prior package evidence or claiming future implementation/package parity.'}
OUTPUT.write_bytes(gzip.compress((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
print('Saved15 verified source updates and3 actual derivation/NAR profiles.',flush=True)
