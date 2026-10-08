"""Verify actual main finite CLI observations without claiming packaged or contextual coverage."""
import argparse,gzip,json
from pathlib import Path
from additive_ppundeoreo_audit import inspect as source_inspect,inputs,read,sha
ROOT=Path(__file__).resolve().parents[1]
def main_inputs():
 return [read(ROOT/'docs'/('additive-ppundeoreo-'+n+'.json.gz')) for n in ['main-binaries','main-source-replay','main-boundary-preflight']]
def inspect(binaries,replay,boundary):
 assert binaries['state']=='actual-main-binaries-captured-full-suite-pending'
 assert binaries['cwd']=='/home/josh/projects/klem' and len(binaries['snapshot_files'])==964
 assert sha(binaries['producer']['text'].encode())==binaries['producer']['sha256']
 assert binaries['producer']['text']==gzip.decompress((ROOT/'docs/additive-ppundeoreo-capture-main-binaries.py.gz').read_bytes()).decode()
 cli=binaries['binaries']['cli'];assert cli['path']=='/tmp/klem-additive-ppundeoreo-main-cli'
 assert replay['cli']==cli['path'] and replay['cli_sha256']==cli['sha256']
 for report,stem in [(replay,'main-source-replay'),(boundary,'main-boundary-replay')]:
  assert report['producer']['text']==gzip.decompress((ROOT/'docs'/('additive-ppundeoreo-'+stem+'.py.gz')).read_bytes()).decode()
  assert report['frozen_inputs'][cli['path']]==cli['sha256']
  assert len(report['runs'])==6 and all(run['command'][0]==cli['path'] for run in report['runs'])
 source,closure,earlier_replay,earlier_boundary,fixture,cases=inputs()
 result=source_inspect(source,closure,replay,boundary,fixture,cases)
 for actual,old in [(replay,earlier_replay),(boundary,earlier_boundary)]:
  assert [(r['encoding'],r['mode'],r['jsonl']) for r in actual['runs']]==[(r['encoding'],r['mode'],r['jsonl']) for r in old['runs']]
 result['scope']='Actual main finite CLI/source/Native behavior matches every independently checked isolated observation. Full main Rust result, broad/runtime/package/performance and contextual review remain separately tracked.'
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');parser.parse_args();print(inspect(*main_inputs()),flush=True)
