"""Verify every unchanged broad workload against the complete actual parent capture."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def inspect(report, prior, sources):
    assert report['state'] == 'draft-complete-broad-preservation-passed', 'terminal broad capture'
    assert report['inputs_unchanged'] and not report['full_coverage_complete'], 'frozen broad inputs and bounded scope'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual broad producer bytes'
    assert prior['inputs_unchanged'], 'actual preserved parent inputs'
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible',
             'novel-raw', 'novel-headword', 'novel-compatible',
             'novel-headword-spacing', 'novel-compatible-spacing']
    runs = report['comparisons']
    assert [r['mode'] for r in runs] == [r['mode'] for r in prior['comparisons']] == modes, 'all eight complete workloads'
    assert sum(r['records'] for r in runs) == 1128312, 'complete original frame count'
    for run, previous in zip(runs, prior['comparisons'], strict=True):
        assert all(run[k] == previous[k] for k in ['source', 'source_sha256', 'mode', 'records']), 'complete original workload identity'
        original = sources['sources'][run['source']]['text'].encode()
        assert sha(original) == run['source_sha256'], 'complete original source bytes'
        assert run['exit_codes'] == [0, 0] and run['original_bytes_conserved'], 'successful complete byte-conserving execution'
        assert run['before_jsonl_sha256'] == previous['after_jsonl_sha256'], 'exact actual completed parent stream'
        assert run['after_jsonl_sha256'] == run['before_jsonl_sha256'], 'complete current stream byte parity'
        assert not run['changed_frames'], 'complete unchanged frames including spacing diagnostics'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        if 'spacing' in run['mode']:
            flags.append('--suggest-spacing')
        assert len(run['commands']) == 2, 'actual before and after commands'
        for command in run['commands']:
            assert command[0] in report['frozen_inputs'], 'actual frozen workload executable'
            assert command[1] == 'text' and command[3] == '--dictionary' and command[5:] == flags, 'actual dictionary filter and spacing flags'
            assert command[4] in report['frozen_inputs'], 'actual frozen dictionary'
            assert report['frozen_inputs'][command[2]] == run['source_sha256'], 'actual frozen complete input'
    assert report['individual_additions'] == report['individual_spacing_additions'] == [], 'complete zero emitted path accounting'
    assert report['individual_probe_diagnostics'] == [], 'complete zero changed diagnostic accounting'
    assert report['complete_native_entries'] == report['independent_spacing_replay'] == {}, 'complete zero new owners and segment accounting'
    return {'broad_frames': 1128312, 'unchanged_streams': 8, 'added_candidate_paths': 0,
            'added_spacing_options': 0, 'changed_probe_diagnostics': 0,
            'contextual_and_independent_review': 'pending', 'full_coverage_complete': False}


def inputs():
    return [read(ROOT / 'docs' / name) for name in ['fear-lsera-broad.json.gz',
            'familiar-geurae-broad.json.gz', 'reported-deoni-broad-inputs.json.gz']]


if __name__ == '__main__':
    print(inspect(*inputs()))
