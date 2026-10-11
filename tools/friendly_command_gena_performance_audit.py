"""Recompute the original Gena novel timings and verify their release bindings."""
import datetime
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parent if P.name == 'tools' else P.parents[1]
CAPTURE_ROOT = Path('/home/josh/projects/klem')
MANIFEST_SHA = '37c6bdb4895a4768d3a87863d02f778b196567ca237ae3090e1978bf77d0bfc3'
NOVEL_ARCHIVE_SHA = '7d43206bb6add22e79cb27173ff049cf501e9dcdabe307c9d5a4cacc2ab26902'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
MODES = [('novel-unannotated',0),('novel-unannotated',8388608),
         ('novel-raw',0),('novel-raw',8388608),('novel-headword',8388608),
         ('novel-compatible',8388608),('novel-headword-spacing',8388608),
         ('novel-compatible-spacing',8388608)]
CHANGES = {'src/grammar.rs','src/engine.rs','src/dictionary/attachment.rs',
           'src/bin/klem-web/grammar_labels.rs','web/src/grammar-labels.json'}


def prepared_inputs(prepared):
    P = Path(prepared)
    payload = (P/'friendly-command-gena-performance.json').read_bytes()
    report = json.loads(payload)
    originals = {}
    values = {}
    physical = {}
    for path, digest in report['frozen_inputs'].items():
        if path in [report['before_cli'],report['cli']]:
            continue
        file = Path(path)
        if not file.is_absolute(): file = CAPTURE_ROOT/file
        raw = file.read_bytes()
        assert sha(raw) == digest, 'every original physically unchanged timing input'
        physical[path] = sha(raw)
        if file.parent == P:
            originals[file.name] = raw
            if file.name.endswith(('.json','.json.gz')):
                values[file.name] = json.loads(gzip.decompress(raw) if file.name.endswith('.gz') else raw)
    before = values['gentle-command-long-installed-runtime.json.gz']['binaries']['klem']
    after = values['friendly-command-gena-installed-runtime.json.gz']['binaries']['klem']
    captured = {row['path']:row['sha256'] for row in [before,after]}
    return dict(report=report,report_sha256=sha(payload),values=values,originals=originals,
                physical=physical,captured_binaries=captured,
                input_bytes=Path(report['input_source']).stat().st_size,
                binary_evidence=dict(mode='captured',live_executable_files_verified=False),
                original_input_evidence=dict(mode='live-non-executable',live_non_executable_files_verified=True))


def inputs(prepared=None):
    if prepared is not None:
        return prepared_inputs(prepared)
    manifest_raw = (ROOT/'docs/friendly-command-gena-performance-proof-archive.json').read_bytes()
    assert sha(manifest_raw) == MANIFEST_SHA, 'pinned complete original timing manifest'
    manifest = json.loads(manifest_raw)
    originals = {}
    values = {}
    for name, item in manifest['files'].items():
        packed = (ROOT/'docs'/item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'complete packed timing evidence'
        original = gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'complete original timing evidence'
        originals[name] = original
        if name.endswith(('.json','.json.gz')):
            values[name] = json.loads(gzip.decompress(original) if name.endswith('.gz') else original)
    report = values['friendly-command-gena-performance.json']
    raw = (ROOT/'docs/reported-deoni-broad-inputs.json.gz').read_bytes()
    assert sha(raw) == NOVEL_ARCHIVE_SHA, 'immutable original whole novel archive'
    texts = json.loads(gzip.decompress(raw))['sources']
    novel = next(v for k,v in texts.items() if k.endswith('/mujeong.txt'))['text'].encode()
    assert sha(novel) == report['input_sha256'], 'every original archived novel byte'
    before = values['gentle-command-long-installed-runtime.json.gz']
    after = values['friendly-command-gena-installed-runtime.json.gz']
    captured = {row['path']:row['sha256'] for row in [before['binaries']['klem'],after['binaries']['klem']]}
    # Retain the original input-map key for the unchanged 23 controls. These
    # digests are derived from complete archived inputs, not live host files.
    digests = {}
    db = str(CAPTURE_ROOT/'.direnv/dictionary-restoration/krdict.db')
    for path in report['frozen_inputs']:
        if path in captured:
            continue
        if path == report['input_source']:
            digests[path] = sha(novel)
        elif path == db:
            assert before['frozen_inputs'][db] == after['frozen_inputs'][db], 'same originally captured imported dictionary'
            digests[path] = after['frozen_inputs'][db]
        else:
            file = Path(path)
            full = file if file.is_absolute() else CAPTURE_ROOT/file
            assert full.parent == CAPTURE_ROOT/'.direnv/willingness-question-prepared', 'original timing artifact directory'
            digests[path] = sha(originals[file.name])
    return dict(report=report,report_sha256=sha(originals['friendly-command-gena-performance.json']),
                values=values,originals=originals,manifest=manifest,manifest_raw=manifest_raw,physical=digests,
                captured_binaries=captured,input_bytes=len(novel),
                binary_evidence=dict(mode='captured',live_executable_files_verified=False),
                original_input_evidence=dict(mode='archived',live_non_executable_files_verified=False))


def inspect_evidence(v):
    scope = v['original_input_evidence']
    assert scope in [dict(mode='archived',live_non_executable_files_verified=False),
                     dict(mode='live-non-executable',live_non_executable_files_verified=True)], 'honest original timing input evidence scope'
    if scope['mode'] != 'archived':
        return
    values, originals = v['values'],v['originals']
    assert len(v['manifest']['files']) == len(originals) == 22, 'all22 complete timing and failure artifacts'
    assert sha(v['manifest_raw']) == MANIFEST_SHA and json.loads(v['manifest_raw']) == v['manifest'], 'immutable original timing archive catalog'
    assert set(originals) == set(v['manifest']['files']) and all(sha(raw) == v['manifest']['files'][name]['source_sha256'] for name,raw in originals.items()), 'every immutable original timing artifact body'
    first = values['first-failed-friendly-command-gena-performance-audit-validation.json']
    retry = values['friendly-command-gena-performance-audit-validation-retry1.json']
    assert first['state'] == 'failed' and first['tests_run'] == 0 and first['errors'] == 1, 'original missing-executable preflight stays failed'
    assert retry['state'] == 'passed' and retry['tests_run'] == 23 and retry['failures'] == retry['errors'] == retry['skipped'] == 0, 'actual original23 captured performance controls'
    assert retry['log_sha256'] == sha(originals['friendly-command-gena-performance-audit-validation-retry1.log']), 'full original captured timing control log'
    assert retry['original_auditor'] == dict(text=originals['friendly_command_gena_performance_audit.py'].decode(),sha256=sha(originals['friendly_command_gena_performance_audit.py'])), 'actual original successful timing auditor'
    assert retry['original_controls'] == dict(text=originals['test_friendly_command_gena_performance_audit.py'].decode(),sha256=sha(originals['test_friendly_command_gena_performance_audit.py'])), 'actual original23 timing control bodies'


def inspect_binding(v):
    r, values = v['report'],v['values']
    assert r['state'] == 'passed' and r['exit_code'] == 0 and all(r[k] for k in ['inputs_unchanged','source_unchanged','head_unchanged','index_unchanged']), 'actual terminal unchanged timings'
    assert r['schema_version'] == 1 and r['checklist'] == 'COV-017db', 'named Gena timing scope'
    assert r['captured_head'] == '6cf27565c7891005de12651abcb7f18911495adf' and len(r['source_inputs']) == 6985, 'complete6985 original Gena source checkpoint'
    after = values['friendly-command-gena-installed-runtime.json.gz']
    before = values['gentle-command-long-installed-runtime.json.gz']
    package = values['friendly-command-gena-nix-packages.json']
    previous = values['gentle-command-long-nix-packages-retry2.json']
    gate = values['friendly-command-gena-complete-nix-gate.json']
    prior_gate = values['gentle-command-long-promoted-complete-nix-gate-retry2.json']
    for report in [after,before,package,previous,gate,prior_gate]:
        assert report['state'] == 'passed' and report['inputs_unchanged'], 'actual passed timing prerequisites'
    assert gate['exit_code'] == prior_gate['exit_code'] == 0 and len(gate['outputs']) == len(prior_gate['outputs']) == 4, 'both full four-check timing prerequisites'
    assert gate['frozen_inputs'] == r['source_inputs'] and gate['head'] == r['captured_head'] and gate['index_sha256'] == r['index_sha256'], 'every original timing source byte and index'
    assert set(package['outputs']) == set(after['packages'].values()) and set(previous['outputs']) == set(before['packages'].values()), 'exact before after installed package outputs'
    assert r['cli'] == after['binaries']['klem']['path'] and r['cli_sha256'] == after['binaries']['klem']['sha256'] and r['before_cli'] == before['binaries']['klem']['path'] and r['before_cli_sha256'] == before['binaries']['klem']['sha256'] and r['before_cli'] != r['cli'], 'exact distinct release executable pair'
    assert r['before_profile'] == before['profiles']['klem']['files'] and r['after_profile'] == after['profiles']['klem']['files'], 'every original installed compile profile'
    compiled = values['friendly-command-gena-complete-runtime-binding.json']['production_inputs']
    assert len(compiled) == 44 and r['compiled_inputs'] == compiled and all(r['after_profile'][p] == d for p,d in compiled.items()), 'all44 original timing production inputs'
    assert {p for p,d in compiled.items() if r['before_profile'][p] != d} == CHANGES == set(r['individual_compiled_changes']), 'exact five compiled timing changes'
    assert v['binary_evidence'] == dict(mode='captured',live_executable_files_verified=False), 'honest captured timing executable scope'
    assert len(v['physical']) == 11 and len(v['captured_binaries']) == 2 and r['frozen_inputs'] == v['physical'] | v['captured_binaries'], 'all13 original timing input bindings'
    for field, name in [('package_sha256','friendly-command-gena-nix-packages.json'),('previous_package_sha256','gentle-command-long-nix-packages-retry2.json'),('comparison_sha256','friendly-command-gena-broad.json.gz')]:
        assert r[field] == sha(v['originals'][name]), 'exact original timing package comparison digests'
    assert r['producer'] == dict(text=v['originals']['capture_friendly_command_gena_performance.py'].decode(),sha256=sha(v['originals']['capture_friendly_command_gena_performance.py'])), 'complete original timing producer'
    novel = [row for row in values['friendly-command-gena-broad.json.gz']['runs'] if row['mode'].startswith('novel-')]
    assert len(novel) == 5 and all(row['actual_source'] == r['input_source'] and row['source_sha256'] == r['input_sha256'] for row in novel), 'same complete original novel input'
    assert r['input_bytes'] == v['input_bytes'] == 786078 and r['frozen_inputs'][r['input_source']] == r['input_sha256'], 'complete786078 original novel bytes'
    db = str(CAPTURE_ROOT/'.direnv/dictionary-restoration/krdict.db')
    assert r['dictionary_sha256'] == r['frozen_inputs'][db] == '23d993696c55d0e54660e4a2b23dac7d68525fecb1fdc44341e1f2b3f75dead5', 'unchanged full imported timing dictionary'
    start = datetime.datetime.fromisoformat(r['started_at'])
    assert start < datetime.datetime.fromisoformat(r['finished_at']) and all(datetime.datetime.fromisoformat(g['finished_at']) < start for g in [gate,prior_gate]), 'actual prerequisite gates finished before timings'


def inspect_samples(v):
    r = v['report']
    assert len(r['cpu_affinity']) == 1 and set(r['cpu_affinity']) <= set(r['allowed_cpus']) and not r['own_active_jobs_before_timing'], 'one allowed CPU and no recorded own timing jobs'
    assert [(w['mode'],w['cache_bytes']) for w in r['workloads']] == MODES, 'all eight full novel timing workloads'
    order = [(run+1,version) for run in range(5) for version in (['before','after'] if run%2 == 0 else ['after','before'])]
    db = str(CAPTURE_ROOT/'.direnv/dictionary-restoration/krdict.db')
    for workload in r['workloads']:
        mode, cache = workload['mode'],workload['cache_bytes']
        assert [(s['run'],s['version']) for s in workload['samples']] == order, 'all five interleaved original timing pairs'
        for sample in workload['samples']:
            cli = r['before_cli'] if sample['version'] == 'before' else r['cli']
            command = [cli,'text',r['input_source'],'--cache-bytes',str(cache)]
            if mode != 'novel-unannotated': command += ['--dictionary',db]
            if mode not in ['novel-unannotated','novel-raw']: command += ['--dict-compatible' if 'compatible' in mode else '--dict-only']
            if 'spacing' in mode: command += ['--suggest-spacing']
            assert sample['command'] == command and sample['exit_code'] == 0, 'exact actual full novel timing command'
            assert isinstance(sample['peak_rss_kib'],int) and sample['peak_rss_kib'] > 0, 'actual original peak memory observation'
            assert all(isinstance(sample[k],(int,float)) and math.isfinite(sample[k]) and sample[k] >= 0 for k in ['seconds','user_seconds','system_seconds','gnu_elapsed_seconds']) and sample['seconds'] > 0, 'finite original timing measurements'
            for key in ['start_context','end_context']:
                context = sample[key]
                assert set(context) == {'loadavg','cpu_frequency_khz','active_own_jobs'} and not context['active_own_jobs'], 'all original timing contexts with no recorded own jobs'
                assert len(context['loadavg'].split()) == 5 and (context['cpu_frequency_khz'] is None or isinstance(context['cpu_frequency_khz'],int) and context['cpu_frequency_khz'] > 0), 'original load and variable clock observations'
        summary = {}
        for version in ['before','after']:
            rows = [s for s in workload['samples'] if s['version'] == version]
            summary[version] = dict(median_seconds=statistics.median(s['seconds'] for s in rows),median_user_seconds=statistics.median(s['user_seconds'] for s in rows),min_seconds=min(s['seconds'] for s in rows),max_seconds=max(s['seconds'] for s in rows))
        assert workload['summary'] == summary, 'independently recomputed every original timing summary'
    assert 'No statistical equivalence or causality claim.' in r['scope'] and 'not evidence of isolation or constant clocks' in r['scope'], 'honest bounded timing scope'


def inspect_parity(v):
    r = v['report']
    broad = v['values']['friendly-command-gena-broad.json.gz']['runs']
    assert [row['mode'] for row in r['cache_parity']] == ['raw','headword','compatible'], 'all three original cache parity policies'
    db = str(CAPTURE_ROOT/'.direnv/dictionary-restoration/krdict.db')
    for row in r['cache_parity']:
        expected = next(b for b in broad if b['mode'] == 'novel-'+row['mode'])
        assert len(row['checks']) == 2, 'both complete original cache sizes'
        for check, cache in zip(row['checks'],[0,8388608],strict=True):
            flags = [] if row['mode'] == 'raw' else ['--dict-only'] if row['mode'] == 'headword' else ['--dict-compatible']
            assert check['command'] == [r['cli'],'text',r['input_source'],'--dictionary',db,*flags,'--cache-bytes',str(cache)] and check['cache_bytes'] == cache and check['exit_code'] == 0, 'actual complete cache parity command'
            assert check['records'] == expected['records'] == 179112 and check['sha256'] == expected['after_jsonl_sha256'], 'all179112 cache parity records and original broad bytes'


def inspect(v):
    inspect_evidence(v)
    inspect_binding(v)
    inspect_samples(v)
    inspect_parity(v)
    return dict(samples=80,workloads=8,cache_streams=6,novel_frames_per_stream=179112,
                input_bytes=786078,host_isolation_proved=False,statistical_equivalence_proved=False,
                executable_evidence='captured-original-installed-receipts',live_executable_files_verified=False,
                full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
