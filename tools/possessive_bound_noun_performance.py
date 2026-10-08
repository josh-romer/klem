"""Verify every paired measurement and complete novel cache stream for the extension."""
import argparse,gzip,hashlib,json,os
from pathlib import Path
from predicate_auxiliary_spacing_performance import verify_samples
ROOT=Path(os.environ.get('KLEM_ROOT',Path(__file__).resolve().parents[1]))
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def raw(path):
 path=Path(path);return gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes()
def read(path):return json.loads(raw(path))
def inspect(report):
 assert report['schema_version']==1 and report['checklist']=='COV-020u'
 assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged']
 assert sha(report['producer']['text'].encode())==report['producer']['sha256']
 current_path=Path(os.environ.get('KLEM_POSSESSIVE_PACKAGE',ROOT/'docs/possessive-bound-noun-nix.json.gz'));previous_path=ROOT/'docs/bound-noun-spacing-nix.json.gz';broad_path=Path(os.environ.get('KLEM_POSSESSIVE_BROAD',ROOT/'docs/possessive-bound-noun-broad-final.json.gz'))
 current,previous,broad=map(read,[current_path,previous_path,broad_path])
 assert current['state']==previous['state']=='passed' and current['source_unchanged'] and previous['source_unchanged']
 assert report['package_sha256']==sha(raw(current_path)) and report['previous_package_sha256']==sha(previous_path.read_bytes()) and report['comparison_sha256']==sha(broad_path.read_bytes())
 binary=lambda r:next(o for o in r['outputs'] if o.endswith('-klem-0.1.0'))+'/bin/klem'
 binaries={'before':binary(previous),'after':binary(current)};assert report['before_cli']==binaries['before'] and report['cli']==binaries['after'] and binaries['before']!=binaries['after']
 assert report['input_source']=='data/books/mujeong.txt' and report['input_bytes']==786078
 assert len(report['cpu_affinity'])==1 and report['allowed_cpus'] and set(report['cpu_affinity'])<=set(report['allowed_cpus'])
 book=next(p for p,h in report['frozen_inputs'].items() if p.endswith('/data/books/mujeong.txt') and h==report['input_sha256'])
 dictionary=next(p for p,h in report['frozen_inputs'].items() if p.endswith('/data/dictionaries/krdict/krdict.db') and h==report['dictionary_sha256'])
 for key,path in [('before_cli_sha256',binaries['before']),('cli_sha256',binaries['after'])]:assert report['frozen_inputs'][path]==report[key]
 cli=read(Path(os.environ.get('KLEM_POSSESSIVE_CLI',ROOT/'docs/possessive-bound-noun-installed-cli.json.gz')));assert cli['cli']==binaries['after'] and cli['cli_sha256']==report['cli_sha256'] and cli['frozen_inputs'][dictionary]==report['dictionary_sha256']
 count=verify_samples(report['workloads'],binaries,book,dictionary);assert count==80
 assert [s['mode'] for s in report['cache_parity']]==['raw','headword','compatible','headword-spacing','compatible-spacing']
 for stream in report['cache_parity']:
  mode=stream['mode'];expected=next(c for c in broad['comparisons'] if c['mode']=='novel-'+mode)
  assert expected['source_sha256']==report['input_sha256'] and len(stream['checks'])==2
  flags=[] if mode=='raw' else ['--dict-compatible'] if mode.startswith('compatible') else ['--dict-only']
  if 'spacing' in mode:flags+=['--suggest-spacing']
  for cache,row in zip([0,8388608],stream['checks'],strict=True):
   assert row['command']==[binaries['after'],'text',book,'--dictionary',dictionary,*flags,'--cache-bytes',str(cache)]
   assert row['cache_bytes']==cache and row['records']==expected['records']==179112 and row['exit_code']==0 and row['sha256']==expected['after_jsonl_sha256']
 return {'paired_samples':count,'complete_cache_streams':10,'frames_per_stream':179112,'scope':'Retained machine/novel observations; no statistical equivalence, causal, contextual or independent-review claim.'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,default=ROOT/'docs/possessive-bound-noun-performance.json.gz');args=p.parse_args();print(json.dumps(inspect(read(args.report))))
