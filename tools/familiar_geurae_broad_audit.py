"""Independently account for complete broad streams and every probe-only delta."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
SCOPE = 'Suffix inventory can consider an additional boundary after familiar 그래; no new candidate, dictionary assessment, displayed diagram, exported spacing option or original byte changes.'

def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def inspect(report, prior, sources, diagnostics):
    assert report['state'] == 'draft-complete-broad-preservation-passed' and report['inputs_unchanged'] and not report['full_coverage_complete'], 'terminal broad capture and partial coverage'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual broad producer bytes'
    assert diagnostics['state'] == 'individually-tracked-probe-only-spacing-deltas', 'individual diagnostics state'
    assert diagnostics['complete_broad_report_sha256'] == sha((ROOT / 'docs/familiar-geurae-broad.json.gz').read_bytes()), 'complete broad diagnostic binding'
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible', 'novel-raw', 'novel-headword', 'novel-compatible', 'novel-headword-spacing', 'novel-compatible-spacing']
    assert [r['mode'] for r in report['comparisons']] == [r['mode'] for r in prior['comparisons']] == modes, 'all eight complete workloads'
    assert sum(r['records'] for r in report['comparisons']) == 1128312, 'complete broad frame count'
    assert report['individual_additions'] == report['individual_spacing_additions'] == [], 'no untracked new paths or spacing hypotheses'
    assert report['complete_native_entries'] == report['independent_spacing_replay'] == {}, 'no new emitted path owners or segments'
    observations = []
    for run, previous in zip(report['comparisons'], prior['comparisons'], strict=True):
        assert all(run[k] == previous[k] for k in ['source', 'source_sha256', 'mode', 'records']), 'complete original workload identity'
        assert run['before_jsonl_sha256'] == previous['after_jsonl_sha256'], 'exact actual completed parent output'
        assert run['exit_codes'] == [0, 0] and run['original_bytes_conserved'], 'terminal complete stream execution'
        text = sources['sources'][run['source']]['text']
        raw = text.encode()
        assert sha(raw) == run['source_sha256'], 'complete original source byte digest'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        if 'spacing' in run['mode']:
            flags.append('--suggest-spacing')
        assert len(run['commands']) == 2 and all(c[0] in report['frozen_inputs'] and c[1] == 'text' and c[3] == '--dictionary' and c[4] in report['frozen_inputs'] and c[5:] == flags for c in run['commands']), 'actual workload executables dictionary and flags'
        assert all(report['frozen_inputs'][c[2]] == run['source_sha256'] for c in run['commands']), 'actual frozen complete source identity'
        if 'spacing' not in run['mode']:
            assert run['changed_frames'] == [] and run['after_jsonl_sha256'] == run['before_jsonl_sha256'], 'six complete nonspacing streams exact'
            continue
        assert len(run['changed_frames']) == 199 and run['after_jsonl_sha256'] != run['before_jsonl_sha256'], 'all individually changed spacing frames'
        previous_record = 0
        for frame in run['changed_frames']:
            record = frame['record']
            assert previous_record < record <= run['records'], 'individual original frame order'
            previous_record = record
            before, after = frame['before'], frame['after']
            span = after['span']
            assert raw[span['start']:span['end']].decode() == after['surface'], 'original changed source byte ownership'
            left = raw.rfind(b'\n', 0, span['start']) + 1
            right = raw.find(b'\n', span['end'])
            line = raw[left:right if right >= 0 else len(raw)].decode()
            assert frame['complete_original_line'] == line, 'complete original changed context'
            assert frame['added_paths'] == frame['added_spacing_options'] == 0, 'no emitted candidate or alternative additions'
            changed = copy.deepcopy(before)
            assert after['spacing']['segment_probes'] == before['spacing']['segment_probes'] + 1, 'exact one additional internal segment probe'
            changed['spacing']['segment_probes'] = after['spacing']['segment_probes']
            assert changed == after, 'every other candidate assessment display and spacing field exact'
            value = {'source': run['source'], 'source_sha256': run['source_sha256'], 'mode': run['mode'],
                     'record': record, 'surface': after['surface'], 'span': span, 'complete_original_line': line,
                     'field': 'spacing.segment_probes', 'before': before['spacing']['segment_probes'],
                     'after': after['spacing']['segment_probes'], 'candidate_paths_unchanged': True,
                     'spacing_alternatives_unchanged': True, 'scope': SCOPE}
            ident = 'familiar-geurae-spacing-probe-' + sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())[:24]
            observations.append({**value, 'id': ident})
    assert len(observations) == len({o['id'] for o in observations}) == 398 and diagnostics['observations'] == observations, 'every individually derived diagnostic and stable ID'
    expected_surfaces = ['그래도', '그래듀에이트', '그래라', '그래서', '그래서야', '그래요', '동그래진다', '둥그래졌다', '둥그래졌다가', '둥그래지며', '둥그래진', '둥그래진다']
    assert diagnostics['surfaces'] == sorted({o['surface'] for o in observations}) == expected_surfaces, 'complete original diagnostic surface inventory'
    return {'broad_frames': 1128312, 'exact_nonspacing_streams': 6, 'probe_only_observations': 398,
            'changed_surfaces': 12, 'added_candidate_paths': 0, 'added_spacing_alternatives': 0,
            'full_coverage_complete': False}

def inputs():
    return [read(ROOT / path) for path in ['docs/familiar-geurae-broad.json.gz', 'docs/explanatory-se-broad.json.gz',
                                          'docs/reported-deoni-broad-inputs.json.gz', 'docs/familiar-geurae-spacing-probe-diagnostics.json.gz']]

if __name__ == '__main__':
    print(inspect(*inputs()))
