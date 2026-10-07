"""Verify paired release measurements and every full-novel cache stream."""
import argparse
import math
import statistics

from declarative_contrast_audit import ROOT, producer, read, sha
from doeda_identity_performance import MODES


def verify_samples(workloads, binaries, book, dictionary):
    assert [(w['mode'],w['cache_bytes']) for w in workloads]==MODES
    for workload in workloads:
        mode, cache, rows = workload['mode'], workload['cache_bytes'], workload['samples']
        assert [(r['run'],r['version']) for r in rows]==[
            (run+1,version) for run in range(5)
            for version in (['before','after'] if run%2==0 else ['after','before'])]
        for row in rows:
            command = [binaries[row['version']],'text',book,'--cache-bytes',str(cache)]
            if mode!='novel-unannotated':
                command += ['--dictionary',dictionary]
            if mode not in ['novel-unannotated','novel-raw']:
                command += ['--dict-compatible' if 'compatible' in mode else '--dict-only']
            if 'spacing' in mode:
                command += ['--suggest-spacing']
            assert row['command']==command
            assert row['exit_code']==0
            assert type(row['peak_rss_kib']) is int and row['peak_rss_kib']>0
            for key in ['seconds','user_seconds','system_seconds','gnu_elapsed_seconds']:
                value = row[key]
                assert type(value) in (int,float) and math.isfinite(value) and value>=0
            assert row['seconds']>0
            for context in [row['start_context'],row['end_context']]:
                assert isinstance(context['loadavg'],str) and context['loadavg']
                frequency = context['cpu_frequency_khz']
                assert frequency is None or type(frequency) is int and frequency>0
        assert workload['summary']=={
            version:{'median_seconds':statistics.median(r['seconds'] for r in rows if r['version']==version),
                     'median_user_seconds':statistics.median(r['user_seconds'] for r in rows if r['version']==version),
                     'min_seconds':min(r['seconds'] for r in rows if r['version']==version),
                     'max_seconds':max(r['seconds'] for r in rows if r['version']==version)}
            for version in ['before','after']}
    return sum(len(w['samples']) for w in workloads)


def inspect(report):
    assert report['schema_version']==1 and report['checklist']=='COV-017ch'
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/capture_declarative_contrast_performance.py').read_text()
    package_path = ROOT/'docs/declarative-contrast-package-nix.json'
    previous_path = ROOT/'docs/literary-ri-prefinal-package-nix.json'
    comparison_path = ROOT/'docs/declarative-contrast-prototype-broad.json.gz'
    package, previous, broad = map(read,[package_path,previous_path,comparison_path])
    assert report['package_sha256']==sha(package_path.read_bytes())
    assert report['previous_package_sha256']==sha(previous_path.read_bytes())
    assert report['comparison_sha256']==sha(comparison_path.read_bytes())
    outputs = {}
    for version, receipt in [('before',previous),('after',package)]:
        assert receipt['state']=='passed' and receipt['exit_code']==0 and receipt['snapshot_unchanged'] is True
        outputs[version] = next(p for p in receipt['outputs'] if p.endswith('-klem-0.1.0'))+'/bin/klem'
    assert report['before_cli']==outputs['before'] and report['cli']==outputs['after']
    assert outputs['before']!=outputs['after']
    actual_cli = read(ROOT/'docs/declarative-contrast-packaged-cli-replay.json')
    assert report['cli_sha256']==actual_cli['cli_sha256']
    old_cli = read(ROOT/'docs/literary-ri-prefinal-packaged-cli-replay.json.gz')
    assert report['before_cli_sha256']==old_cli['cli_sha256']
    assert report['input_source']=='data/books/mujeong.txt' and report['input_bytes']==786078
    assert len(report['cpu_affinity'])==1
    assert report['allowed_cpus'] and all(type(cpu) is int and cpu>=0 for cpu in report['allowed_cpus'])
    assert set(report['cpu_affinity'])<=set(report['allowed_cpus'])
    # Captured commands use the original workspace root, even inside Nix's
    # independently evaluated audit source. Resolve it from the frozen input.
    original_book = next(p for p,digest in report['frozen_inputs'].items()
                         if p.endswith('/data/books/mujeong.txt') and digest==report['input_sha256'])
    original_dictionary = next(p for p,digest in report['frozen_inputs'].items()
                               if p.endswith('/data/dictionaries/krdict/krdict.db') and digest==report['dictionary_sha256'])
    # The actual packaged replay froze these same complete input bytes. The
    # offline audit source contains the captures, not the downloaded database.
    assert actual_cli['frozen_inputs'][original_book]==report['input_sha256']
    captured_dictionary = [digest for p,digest in actual_cli['frozen_inputs'].items()
                           if p.endswith('data/dictionaries/krdict/krdict.db')]
    assert captured_dictionary==[report['dictionary_sha256']]
    for key, path in [('before_cli_sha256',outputs['before']),('cli_sha256',outputs['after'])]:
        assert report['frozen_inputs'][path]==report[key]
    count = verify_samples(report['workloads'],outputs,original_book,original_dictionary)
    assert count==80
    assert [r['mode'] for r in report['cache_parity']]==['raw','headword','compatible']
    for stream in report['cache_parity']:
        mode = stream['mode']
        baseline = next(r for r in broad['comparisons'] if r['mode']=='novel-'+mode)
        assert baseline['source_sha256']==report['input_sha256']
        assert len(stream['checks'])==2
        flags = [] if mode=='raw' else ['--dict-only'] if mode=='headword' else ['--dict-compatible']
        for cache, row in zip([0,8388608],stream['checks'],strict=True):
            assert row['command']==[outputs['after'],'text',original_book,'--dictionary',original_dictionary,*flags,'--cache-bytes',str(cache)]
            assert row['cache_bytes']==cache and row['records']==baseline['records']==179112
            assert row['exit_code']==0 and row['sha256']==baseline['after_jsonl_sha256']
    return {'paired_timing_samples':count,'cache_streams':6,'novel_frames_per_stream':179112}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.parse_args()
    print(inspect(read(ROOT/'docs/declarative-contrast-performance.json')))


if __name__=='__main__':
    main()
