"""Verify all actual historical release samples and complete cache-parity streams."""
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = [('novel-unannotated', 0), ('novel-unannotated', 8388608),
         ('novel-raw', 0), ('novel-raw', 8388608), ('novel-headword', 8388608),
         ('novel-compatible', 8388608), ('novel-headword-spacing', 8388608),
         ('novel-compatible-spacing', 8388608)]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inspect(report, before, after, broad, restoration, producer):
    assert report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged'], 'complete terminal benchmark'
    assert report['schema_version'] == 1 and report['checklist'] == 'COV-017cr', 'reported-experience scope'
    assert restoration['state'] == 'passed' and restoration['exit_code'] == 0, 'exact restored releases'
    expected_pair = [('formal-b', '173d1c992f0ab4593a24f9bbc0160eae3e8c6a0d', 1003),
                     ('reported-experience', '45ff043d84f9471fc4211345d48e0ea490165dd4', 1015)]
    assert len(restoration['packages']) == 2, 'complete original release pair'
    for package,binding,expected in zip(restoration['packages'], [before,after], expected_pair, strict=True):
        assert (package['family'],package['head'],package['source_files']) == expected, 'original release revisions and source scope'
        assert package['exit_code'] == 0 and package['all_original_source_files_exact'], 'exact restored release sources'
        assert binding['state'] == 'passed' and binding['exit_code'] == 0 and binding['inputs_unchanged'], 'actual original package binding'
        profile = binding['profiles']['klem']
        assert package['source'] == profile['source'] and len(profile['files']) == expected[2], 'original selected source identity'
        assert package['output'] in binding['outputs'], 'original release output identity'
    assert restoration['packages'][0]['binding_sha256'] == report['previous_package_sha256'] and restoration['packages'][1]['binding_sha256'] == report['package_sha256'], 'original frozen binding hashes'
    assert report['before_cli'] == restoration['packages'][0]['output'] + '/bin/klem', 'actual baseline release executable'
    assert report['cli'] == restoration['packages'][1]['output'] + '/bin/klem', 'actual after release executable'
    assert report['before_cli_sha256'] == restoration['packages'][0]['cli_sha256'] and report['cli_sha256'] == restoration['packages'][1]['cli_sha256'], 'actual restored executable hashes'
    assert report['input_sha256'] == '50a02d2f5f11f148497f2f00c782733ee3f8c2e331e1c0e5f74e3b7c8b0ca4dc' and report['input_bytes'] == 786078, 'complete original novel'
    assert report['producer']['text'].encode() == producer and sha(producer) == report['producer']['sha256'], 'actual preserved benchmark producer'
    assert len(report['frozen_inputs']) == 8 and all(len(value) == 64 for value in report['frozen_inputs'].values()), 'complete frozen input set'
    for path,digest in [(report['before_cli'], report['before_cli_sha256']), (report['cli'], report['cli_sha256']), (report['input_source'], report['input_sha256'])]:
        assert report['frozen_inputs'][path] == digest, 'actual frozen binary and novel hashes'
    assert report['cpu_affinity'] == [max(report['allowed_cpus'])], 'recorded single allowed CPU'
    assert [(w['mode'],w['cache_bytes']) for w in report['workloads']] == MODES, 'all eight complete workloads'
    dictionary = report['cache_parity'][0]['checks'][0]['command'][4]
    assert report['frozen_inputs'][dictionary] == report['dictionary_sha256'], 'actual frozen dictionary'
    summaries = []
    for workload in report['workloads']:
        mode,cache = workload['mode'],workload['cache_bytes']
        samples = workload['samples']
        expected_order = [(run+1,version) for run in range(5) for version in (['before','after'] if run % 2 == 0 else ['after','before'])]
        assert [(s['run'],s['version']) for s in samples] == expected_order, 'all ten interleaved actual samples'
        for sample in samples:
            flags = [] if mode == 'novel-unannotated' else ['--dictionary', dictionary]
            if mode not in ['novel-unannotated','novel-raw']:
                flags += ['--dict-compatible' if 'compatible' in mode else '--dict-only']
            if 'spacing' in mode:
                flags += ['--suggest-spacing']
            binary = report['before_cli'] if sample['version'] == 'before' else report['cli']
            assert sample['command'] == [binary,'text',report['input_source'],'--cache-bytes',str(cache),*flags], 'actual full workload command'
            assert sample['exit_code'] == 0, 'successful actual sample'
            assert isinstance(sample['peak_rss_kib'], int) and sample['peak_rss_kib'] > 0, 'actual peak RSS'
            assert all(math.isfinite(sample[key]) and sample[key] >= 0 for key in ['seconds','user_seconds','system_seconds','gnu_elapsed_seconds']) and sample['seconds'] > 0, 'actual finite timing'
            for phase in ['start_context','end_context']:
                context = sample[phase]
                assert len(context['loadavg'].split()) == 5, 'recorded host context'
                assert context['cpu_frequency_khz'] is None or context['cpu_frequency_khz'] > 0, 'recorded CPU clock context'
        expected = {version:{'median_seconds':statistics.median(s['seconds'] for s in samples if s['version'] == version),
                             'median_user_seconds':statistics.median(s['user_seconds'] for s in samples if s['version'] == version),
                             'min_seconds':min(s['seconds'] for s in samples if s['version'] == version),
                             'max_seconds':max(s['seconds'] for s in samples if s['version'] == version)}
                    for version in ['before','after']}
        assert workload['summary'] == expected, 'independently recomputed summaries'
        summaries.append({'mode':mode,'cache_bytes':cache, **expected,
                          'median_delta_percent':100*(expected['after']['median_seconds']/expected['before']['median_seconds']-1)})
    assert [group['mode'] for group in report['cache_parity']] == ['raw','headword','compatible'], 'all three cache-parity policies'
    for group in report['cache_parity']:
        expected = next(run for run in broad['comparisons'] if run['mode'] == 'novel-' + group['mode'])
        assert expected['source_sha256'] == report['input_sha256'] and expected['records'] == 179112, 'original complete novel comparison'
        assert [c['cache_bytes'] for c in group['checks']] == [0,8388608], 'both complete cache budgets'
        for check in group['checks']:
            flags = [] if group['mode'] == 'raw' else ['--dict-compatible' if group['mode'] == 'compatible' else '--dict-only']
            assert check['command'] == [report['cli'],'text',report['input_source'],'--dictionary',dictionary,*flags,'--cache-bytes',str(check['cache_bytes'])], 'actual complete parity command'
            assert check['sha256'] == expected['after_jsonl_sha256'] and check['records'] == 179112 and check['exit_code'] == 0, 'full cache-parity output binding'
    return {'samples':80,'cache_parity_streams':6,'cache_parity_records':1074672,'workloads':summaries,
            'scope':'Historical formal1003-to-reported1015 release pair only. Fresh-process samples include startup and serialization. Recorded context and a single CPU do not prove host isolation, constant clocks, statistical equivalence or causality. Later ending-family timing and contextual linguistic precision remain separate.'}


def inputs():
    docs = ROOT / 'docs'
    values = [read(docs / name) for name in ['reported-experience-performance.json.gz',
              'reported-experience-performance-before-binding.json.gz',
              'reported-experience-performance-after-binding.json.gz',
              'reported-experience-broad.json.gz', 'reported-experience-performance-restoration.json.gz']]
    for filename,key in [('reported-experience-performance-before-binding.json.gz','previous_package_sha256'),
                         ('reported-experience-performance-after-binding.json.gz','package_sha256')]:
        assert sha(gzip.decompress((docs / filename).read_bytes())) == values[0][key], 'exact archived original package bytes'
    assert sha((docs / 'reported-experience-broad.json.gz').read_bytes()) == values[0]['comparison_sha256'], 'exact archived original broad comparison'
    return [*values, gzip.decompress((docs / 'reported-experience-performance-producer.py.gz').read_bytes())]


if __name__ == '__main__':
    print(json.dumps(inspect(*inputs()), indent=2))
