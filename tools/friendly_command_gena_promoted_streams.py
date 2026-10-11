"""Verify retained command bytes, failed-prefix reuse, and complete word cohorts.

All paths in historical receipts are evidence identifiers. Read bytes supplied
by the portable archive loader; never open the captured host paths or run a CLI.
"""
import gzip
import hashlib
import json
from pathlib import Path

sha = lambda payload: hashlib.sha256(payload).hexdigest()


def inspect_prefix(v):
    report = v['installed']
    manifest_raw = v['failed_prefix_manifest_raw']
    manifest = json.loads(manifest_raw)
    assert manifest['verified_original_completed_explicit_commands'] == 149 and manifest['verified_full_prefix_streams'] == 298, 'original failed prefix scope retained'
    assert manifest['unrecorded_concurrent_bytes_may_be_missing'], 'failed concurrent recorder limits retained'
    assert len(manifest['files']) == 313, 'all313 original failed recorder artifacts retained'
    for name, row in manifest['files'].items():
        packed = v['failed_prefix_originals'][name]
        assert sha(packed) == row['archive_sha256'], 'complete original failed recorder packed artifact'
        raw = gzip.decompress(packed)
        assert sha(raw) == row['source_sha256'] and len(raw) == row['bytes'], 'complete original failed recorder artifact'
    receipt_name = 'friendly-command-gena-promoted-installed-runtime.json.gz'
    receipt_row = manifest['files'][receipt_name]
    packed = v['failed_prefix_originals'][receipt_name]
    receipt_raw = gzip.decompress(packed)
    seed = json.loads(gzip.decompress(receipt_raw))
    assert seed['state'] == 'failed' and seed['error'] is not None, 'original recorder receipt remains failed'
    producer = gzip.decompress(v['failed_prefix_originals']['capture_friendly_command_gena_promoted_installed_runtime_retry3.py'])
    assert seed['producer'] == dict(text=producer.decode(), sha256=sha(producer)), 'actual failed recorder producer retained'
    assert seed['cohort_runs'] == seed['corpus_runs'] == seed['broad_runs'] == [], 'no incomplete failed cohort promoted'
    assert len(seed['cohort_command_attempts']) == manifest['partial_cohort_records'], 'original partial cohort records preserved'
    for key in ['captured_head', 'index_sha256', 'profiles', 'binaries', 'packages', 'assets', 'release_rust']:
        assert seed[key] == report[key], 'same source and package checkpoint for reused prefix'
    for key, count in [('source_runs', 36), ('native_records', 44), ('lookup_records', 69)]:
        assert len(seed[key]) == count and seed[key] == report[key], 'every whole reused original prefix record retained'
    assert len(seed['command_attempts']) == 149 and seed['command_attempts'] == report['command_attempts'][:149], 'actual149 commands reused in original order'
    prefix = report['reused_completed_prefix']
    assert prefix == dict(failed_original_receipt_sha256=sha(receipt_raw), original_archive_sha256=sha(packed),
                         actual_completed_commands=149, whole_streams=298, prefix_commands_replayed=0,
                         failed_cohort_artifacts_retained=True), 'exact failed prefix reuse provenance'
    manifest_path = next((path for path in report['frozen_inputs'] if Path(path).name == 'gena-installed-cohort-recorder-failure-originals.json'), None)
    assert manifest_path is not None and report['frozen_inputs'][manifest_path] == sha(manifest_raw), 'actual failed prefix manifest binding'
    assert report['frozen_inputs'].get(receipt_row['path']) == sha(packed), 'actual failed prefix packed receipt binding'
    streams = set()
    for attempt in seed['command_attempts']:
        assert attempt['exit_code'] == 0 and set(attempt['streams']) == {'stdout', 'stderr'}, 'complete actual reused successful commands'
        for stream in attempt['streams'].values():
            path = stream['path']
            assert path not in streams, 'unique actual reused prefix streams'
            streams.add(path)
            original = gzip.decompress(v['failed_prefix_originals'][Path(path).name])
            assert original == v['command_streams'][path] and sha(original) == stream['archive_sha256'], 'actual reused prefix stream equals archived failed-run stream'
            raw = gzip.decompress(original)
            assert sha(raw) == stream['source_sha256'] and len(raw) == stream['bytes'], 'every complete actual reused prefix stream'
    assert len(streams) == 298, 'all298 original reused prefix streams'
    return dict(reused_commands=149, reused_streams=298, prefix_command_replays=0, failed_artifacts=313)


def inspect_cohorts(v):
    report = v['installed']
    assert len(report['cohort_command_attempts']) == 75 and len(report['cohort_runs']) == 2, 'all75 actual cohort commands and two complete cohorts'
    assert len(v['cohort_command_streams']) == 150, 'all150 whole actual cohort streams retained'
    attempts = iter(report['cohort_command_attempts'])
    streams = set()
    total = 0
    cli = report['binaries']['klem']['path']

    def decode(attempt):
        assert attempt['exit_code'] == 0 and set(attempt['streams']) == {'stdout', 'stderr'}, 'successful complete actual cohort command'
        supplied = attempt['input']
        assert attempt['input_sha256'] == (None if supplied is None else sha(supplied.encode())), 'actual cohort input hash'
        values = {}
        for kind, row in attempt['streams'].items():
            path = row['path']
            assert path not in streams and path not in v['command_streams'], 'unique actual cohort command stream'
            streams.add(path)
            assert path in v['cohort_command_streams'], 'actual cohort stream present'
            packed = v['cohort_command_streams'][path]
            assert sha(packed) == row['archive_sha256'] == report['frozen_inputs'][path], 'actual packed cohort stream binding'
            raw = gzip.decompress(packed)
            assert sha(raw) == row['source_sha256'] and len(raw) == row['bytes'], 'whole actual cohort stream content'
            values[kind] = raw
        assert values['stderr'] == b'', 'original actual cohort stderr retained'
        return values['stdout']

    for run in report['cohort_runs']:
        words = run['words']
        ordered = sorted(words)
        text = '\n'.join(ordered) + '\n'
        attempt = next(attempts)
        assert attempt['command'] == [cli, 'text', '-'] and attempt['input'] == text, 'actual complete cohort command and input'
        raw = text.encode()
        cursor = offset = 0
        starts = {}
        whole = {}
        for word in ordered:
            starts[offset] = word
            offset += len(word.encode()) + 1
        for line in decode(attempt).splitlines():
            frame = json.loads(line)
            span = frame['span']
            assert span['start'] == cursor and span['end'] >= cursor and raw[cursor:span['end']].decode() == frame['surface'], 'complete original cohort UTF8 frame spans'
            cursor = span['end']
            if frame['kind'] == 'word' and starts.get(span['start']) == frame['surface'] and span['end'] == span['start'] + len(frame['surface'].encode()):
                whole[frame['surface']] = frame['analysis']
        assert cursor == len(raw), 'actual cohort frames cover complete input'
        missing = set(words) - set(whole)
        for _ in range(len(missing)):
            attempt = next(attempts)
            command = attempt['command']
            assert len(command) == 3 and command[:2] == [cli, 'word'] and command[2] in missing and attempt['input'] is None, 'actual punctuation fallback word command'
            word = command[2]
            missing.remove(word)
            whole[word] = json.loads(decode(attempt))
        assert not missing and whole == words and len(words) == run['surfaces'], 'every whole53502 original cohort word reconstructed from actual streams'
        total += len(words)
    assert next(attempts, None) is None and total == 53502 and len(streams) == 150, 'complete cohort commands streams and word totals'
    return dict(cohort_words=total, cohort_commands=75, cohort_streams=150, executable_replays=0)
