"""Verify recorded release timings and every complete novel cache stream."""
import gzip,json,math,os,statistics
from pathlib import Path
from declarative_contrast_performance import verify_samples
ROOT=Path(os.environ.get('KLEM_ROOT',Path(__file__).resolve().parents[1]))
def read(name):return json.loads(gzip.decompress((ROOT/name).read_bytes()))
def verify(report,package,prior,broad):
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged']
    assert report['checklist']=='COV-017cn' and len(report['cpu_affinity'])==1
    assert set(report['cpu_affinity'])<=set(report['allowed_cpus'])
    assert package['state']==prior['state']=='passed' and package['snapshot_unchanged']
    binaries={version:next(p for p in receipt['outputs'] if p.endswith('-klem-0.1.0'))+'/bin/klem' for version,receipt in [('before',prior),('after',package)]}
    assert binaries['before']==report['before_cli'] and binaries['after']==report['cli']
    original_book=next(p for p,h in report['frozen_inputs'].items() if p.endswith('/data/books/mujeong.txt') and h==report['input_sha256'])
    original_dictionary=next(p for p,h in report['frozen_inputs'].items() if p.endswith('/data/dictionaries/krdict/krdict.db') and h==report['dictionary_sha256'])
    assert verify_samples(report['workloads'],binaries,original_book,original_dictionary)==80
    assert [r['mode']for r in report['cache_parity']]==['raw','headword','compatible','headword-spacing','compatible-spacing']
    for run in report['cache_parity']:
        expected=next(r for r in broad['comparisons'] if r['mode']=='novel-'+run['mode'])
        assert len(run['checks'])==2
        flags=[]if run['mode']=='raw'else['--dict-compatible']if'compatible'in run['mode']else['--dict-only']
        if 'spacing'in run['mode']:flags+=['--suggest-spacing']
        for cache,check in zip([0,8388608],run['checks'],strict=True):
            assert check['command']==[binaries['after'],'text',original_book,'--dictionary',original_dictionary,*flags,'--cache-bytes',str(cache)]
            assert check['exit_code']==0 and check['cache_bytes']==cache and check['records']==expected['records']==179112
            assert check['sha256']==expected['after_jsonl_sha256']
    return {'paired_samples':80,'complete_cache_streams':10,'frames_per_stream':179112,'scope':'Observed timings on one machine/novel; no statistical equivalence or contextual precision claim.'}
if __name__=='__main__':print(verify(read('docs/declarative-dao-performance.json.gz'),read('docs/declarative-dao-nix.json.gz'),read('docs/possessive-bound-noun-nix.json.gz'),read('docs/declarative-dao-broad-final.json.gz')))
