"""Bind installed package runtime evidence to exact source reconstruction and main outcomes."""
import argparse,copy,gzip,hashlib,json,math,re
from pathlib import Path
from additive_ppundeoreo_sources import inspect as source_inspect
from additive_ppundeoreo_adapter_audit import inspect as adapter_inspect
ROOT=Path(__file__).resolve().parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def read(p):
 raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def inputs():return [read(ROOT/'docs'/('additive-ppundeoreo-'+n)) for n in ['package-nix.json','packaged-cli.json','packaged-adapter.json.gz','packaged-runtime.json','packaged-browser.json']]
def inspect(package,cli,adapter,web,browser):
 assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
 assert sha(package['producer']['text'].encode())==package['producer']['sha256']
 assert package==read(ROOT/'docs/additive-ppundeoreo-package-nix.json')
 release_log=gzip.decompress((ROOT/'docs/additive-ppundeoreo-package-nix.log.gz').read_bytes());assert sha(release_log)==package['log_sha256']
 rows=re.findall(rb'klem> test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',release_log)
 assert len(rows)==229 and tuple(sum(int(r[i]) for r in rows) for i in range(3))==(1062,0,1)
 sources=source_inspect(ROOT/'docs/additive-ppundeoreo-historical-sources.json.gz');assert len(sources)==964
 paths={}
 for name in ['klem','web-assets','corpus-adapter']:
  found=[p for p in package['outputs'] if p.startswith('/nix/store/') and p.endswith('-'+name+'-0.1.0')];assert len(found)==1;paths[name]=found[0]
 assert len(package['outputs'])==3
 expected_sha=sha((ROOT/'docs/additive-ppundeoreo-package-nix.json').read_bytes())
 for report in [cli,web]:
  assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
  assert report['package_sha256']==expected_sha and report['snapshot_files']==package['snapshot']['files']
  assert sha(report['producer']['text'].encode())==report['producer']['sha256']
  assert report['cli']==paths['klem']+'/bin/klem' and report['cli_sha256']==report['frozen_inputs'][report['cli']]
 assert cli['producer']['text']==gzip.decompress((ROOT/'docs/additive-ppundeoreo-packaged-cli.py.gz').read_bytes()).decode()
 actual_finite=[]
 for family,name in [('source','main-source-replay'),('boundary','main-boundary-preflight')]:
  path=ROOT/'docs'/('additive-ppundeoreo-'+name+'.json.gz');capture=read(path)
  for run in capture['runs']:
   command=run['command'].copy();command[0]=cli['cli']
   actual_finite.append({'family':family,'encoding':run['encoding'],'mode':run['mode'],'command':command,'input_sha256':run['input_sha256'],'output_sha256':sha(run['jsonl'].encode()),'records':run['records'],'exit_code':0,'exact_captured_output':True,'expected_capture':str(path.relative_to(ROOT)),'expected_capture_sha256':sha(path.read_bytes())})
 assert cli['finite_runs']==actual_finite and len(actual_finite)==12
 broad=read(ROOT/'docs/additive-ppundeoreo-main-broad.json.gz');assert len(cli['broad'])==len(broad['comparisons'])==8
 for actual,old in zip(cli['broad'],broad['comparisons'],strict=True):
  command=old['commands'][1].copy();command[0]=cli['cli']
  assert actual=={'mode':old['mode'],'source':old['source'],'source_sha256':old['source_sha256'],'command':command,'records':old['records'],'output_sha256':old['after_jsonl_sha256'],'exit_code':0,'exact_captured_output':True}
 assert sum(r['records'] for r in cli['broad'])==1128312
 cohorts=read(ROOT/'docs/additive-ppundeoreo-main-corpus-history.json.gz')['cohorts']
 assert cli['words']==[{'family':r['family'],'surfaces':len(r['after_words']),'word_sha256':r['after_word_sha256'],'exact_captured_output':True} for r in cohorts]
 assert adapter['adapter']==paths['corpus-adapter']+'/bin/klem-corpus-adapter'
 adapter_inspect(adapter,read(ROOT/'docs/literary-question-geona-prototype-corpora.json.gz'))
 assert web['producer']['text']==gzip.decompress((ROOT/'docs/additive-ppundeoreo-packaged-web.py.gz').read_bytes()).decode()
 assert web['server']==paths['klem']+'/bin/klem-web' and web['assets']==paths['web-assets']+'/share/klem-web'
 assert web['server_stopped'] is True and web['server_exit_code'] in [-2,130] and web['help_exit_code']==0
 assert sha(web['launcher_text'].encode())==web['launcher_sha256']==web['frozen_inputs'][web['launcher']]
 assert [line for line in web['launcher_text'].splitlines() if line.startswith('exec ')]==[f'exec {web["server"]} --assets {web["assets"]} "$@"']
 assert web['command']==[web['launcher'],'--port',web['url'].rsplit(':',1)[1],'--dictionary','/home/josh/projects/klem/data/dictionaries/krdict/krdict.db']
 main_assets=read(ROOT/'docs/additive-ppundeoreo-main-frontend-build.json.gz')['assets']
 assert web['asset_snapshot']=={p:r['sha256'] for p,r in main_assets.items()}
 assert web['index_sha256']==main_assets['index.html']['sha256']
 assert len(web['asset_checks'])==2
 for asset in web['asset_checks']:assert main_assets[asset['path'].lstrip('/')]=={k:v for k,v in asset.items() if k!='path'}
 assert sha(json.dumps(browser,ensure_ascii=False,indent=2).encode()+b'\n')==web['browser_sha256']
 assert browser['cli_sha256']==web['cli_sha256']
 main=read(ROOT/'docs/additive-ppundeoreo-main-browser.json.gz')
 for key in ['exports','diagrams','native','opened','modeJudgments','errors','catalog_sha256']:assert browser[key]==main[key],key
 assert len(browser['responses'])==len(main['responses'])==2
 for actual,old in zip(browser['responses'],main['responses'],strict=True):
  assert actual['encoding']==old['encoding']
  elapsed=actual['response']['elapsed_ms'];assert type(elapsed) in [int,float] and math.isfinite(elapsed) and elapsed>=0
  assert {k:v for k,v in actual['response'].items() if k!='elapsed_ms'}=={k:v for k,v in old['response'].items() if k!='elapsed_ms'}
 return {'source_inputs':964,'release_tests':1062,'finite_cli_modes':12,'broad_frames':1128312,'original_annotated_rows':66570,'source_diagrams':20,'filter_checks':276,'native_entries':62,'exports':6,'owned_server_stopped':True,'scope':'Actual installed CLI/adapter/browser/launcher exactly match independently audited main outcomes and all reconstructed sources. Owner/spacing extension, performance, combined inventory and contextual review remain separate.'}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.parse_args();print(inspect(*inputs()),flush=True)
