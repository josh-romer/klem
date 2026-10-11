"""Rederive long-ending evidence, preserving historical judgments and gold."""
import gzip
import json
import unicodedata
from pathlib import Path

import gentle_command_long_revision as revision
import gentle_command_long_source_audit as source_audit
import gentle_command_runtime_audit as prior_audit
from native_lmf import entry

ROOT = revision.ROOT
sha = revision.sha
NOVEL_NATIVE_SHA = 'aa78e5e9eac21e2a32fc21c1e71eefb564e6008bfc2a19a665fbacbb4a468eb7'
VALIDATION_SHA = '8258cacf89c2ae73e3a11e1e1c864fbdfe7a80308485fa08cbd88e7bd4656138'
COHORT_SHA = '31d4e4836d94c2381c747938ab8a204b3983ff47e343248e356e8f0d18388476'


def inputs():
    proof, hashes = revision.archive('gentle-command-long-runtime-proof-archive.json', revision.MANIFEST_SHA)
    native, _ = revision.archive('gentle-command-long-novel-native-proof-archive.json', NOVEL_NATIVE_SHA)
    validated, validation_hashes = revision.archive('gentle-command-long-runtime-validation-proof-archive.json', VALIDATION_SHA)
    raw = (ROOT / 'docs/gentle-command-history-proof-gentle-command-cohorts.json.gz').read_bytes()
    assert sha(raw) == COHORT_SHA, 'immutable complete parent cohort'
    return dict(revision=revision.inputs(), source=source_audit.inputs(), prior=prior_audit.inputs(),
                hashes=hashes, proof=proof,
                streams=proof['gentle-command-long-source-runtime-retry1.json.gz'],
                native=proof['gentle-command-long-native-cli-retry1.json'],
                novel_native=native['gentle-command-long-novel-native-cli.json'],
                cohorts=proof['gentle-command-long-cohorts-retry1.json.gz'],
                parent_cohorts=json.loads(gzip.decompress(raw)),
                gold=proof['gentle-command-long-corpora.json.gz'],
                broad=proof['gentle-command-long-broad.json.gz'],
                novel=proof['gentle-command-long-novel-targets.json.gz'],
                novel_suite=proof['gentle-command-long-novel-validity.json'],
                validation=validated['gentle-command-long-runtime-regressions.json'],
                validation_hashes=validation_hashes)


def bound_report(v, report, state, replays_baseline=False):
    prior_audit.terminal(report, state)
    frozen = report['frozen_inputs']; binding = v['revision']['binding']
    binding_path = '/home/josh/projects/klem/.direnv/willingness-question-prepared/gentle-command-long-runtime-binding.json'
    assert frozen[binding_path] == v['hashes']['gentle-command-long-runtime-binding.json'], 'actual revision receipt binding'
    for name in ['klem']:
        binary = binding['binaries'][name]
        assert frozen[binary['path']] == binary['sha256'], 'exact compiled runtime executable'
    before = v['source']['baseline']['runs'][0]['command'][0]
    if replays_baseline:
        baseline_paths = [p for p in frozen if p.endswith('gentle-command-long-installed-baseline.json.gz')]
        assert len(baseline_paths) == 1 and frozen[baseline_paths[0]] == sha(v['source']['baseline_raw']), 'exact replayed original installed baseline'
    else:
        assert frozen[before] == v['source']['baseline']['frozen_inputs'][before], 'exact original installed parent executable'
    return before, binding['binaries']['klem']['path']


def additions(old, new):
    assert {k: old[k] for k in ['surface', 'span', 'kind']} == {k: new[k] for k in ['surface', 'span', 'kind']}, 'original token ownership'
    before, after = old.get('analysis') or {}, new.get('analysis') or {}
    old_paths, new_paths = before.get('analyses', []), after.get('analyses', [])
    assert [p for p in new_paths if p in old_paths] == old_paths, 'every original candidate and order'
    added = [p for p in new_paths if p not in old_paths]
    assert all('ending.gentle_command_long' in p['rules'] and
               {'form': '으려무나', 'kind': 'ending'} in p['morphemes']
               for p in added), 'only canonical long-command additions'
    for index, path in enumerate(old_paths):
        assert old['dictionary']['readings'][index] == new['dictionary']['readings'][new_paths.index(path)], 'every original Native assessment'
    if old['kind'] == 'word':
        assert all(owner in new['dictionary']['lemmas'] for owner in old['dictionary']['lemmas']), 'every original Native owner'
        assert {k: v for k, v in before.items() if k != 'analyses'} == {k: v for k, v in after.items() if k != 'analyses'}, 'original analysis fields'
    return added


def inspect_streams(v):
    report = v['streams']; before, cli = bound_report(v, report, 'complete-gentle-command-long-source-runtime-passed', replays_baseline=True)
    source = json.loads(v['source']['source_raw']); suite = v['source']['suite']; baseline = v['source']['baseline']
    expected = [(family, encoding, mode, cache) for family in ['complete-source', 'individual-targets', 'individual-validity'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]]
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in report['runs']] == expected, 'all36complete source policies'
    cached = {}; observations = 0
    for run in report['runs']:
        family = run['family']
        text = '\n\n'.join('\n'.join(i['complete_original_group']) for i in source['items']) if family == 'complete-source' else ' '.join(i['surface'] for i in (suite['cases'] if family == 'individual-validity' else source['items']))
        raw = unicodedata.normalize(run['encoding'], text).encode()
        assert raw.decode() == run['input_text'] and sha(raw) == run['input_sha256'], 'complete original source bytes'
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert run['command'][:4] == [cli, 'text', '-', '--dictionary'] and run['command'][4] in report['frozen_inputs'] and run['command'][5:] == flags + ['--cache-bytes', str(run['cache_bytes'])], 'actual source filter/cache command'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'complete actual source output'
        frames = [json.loads(line) for line in run['jsonl'].splitlines()]; cursor = 0
        for frame in frames:
            assert frame['span']['start'] == cursor and raw[cursor:frame['span']['end']].decode() == frame['surface'], 'contiguous original source spans'
            cursor = frame['span']['end']
        assert cursor == len(raw) and len(frames) == run['records'] and run['original_bytes_conserved'], 'all original source frames'
        derived = []
        if family != 'individual-validity':
            old = next(r for r in baseline['runs'] if all(r[k] == run[k] for k in ['family', 'encoding', 'mode', 'cache_bytes']))
            assert old['command'][0] == before, 'same exact source baseline executable'
            previous = [json.loads(line) for line in old['jsonl'].splitlines()]
            assert len(previous) == len(frames), 'all previous source frames'
            for old_frame, new_frame in zip(previous, frames, strict=True): additions(old_frame, new_frame)
            for item in source['items']:
                located = [(i, f) for i, f in enumerate(frames) if f['kind'] == 'word' and unicodedata.normalize('NFC', f['surface']) == item['surface']]
                assert len(located) == 1, 'every original source target'
                index, frame = located[0]
                target = {**item['independent_typed_proposal'], 'required_rules': ['ending.gentle_command_long']}
                indices = [i for i, p in enumerate(frame['analysis']['analyses']) if prior_audit.matches(p, target)]
                assert indices, 'every independently authored source decomposition'
                derived.append(dict(case_id=item['id'], record_index=index, required_analysis_indices=indices))
        else:
            offset = 0
            for case in suite['cases']:
                token = unicodedata.normalize(run['encoding'], case['surface']).encode()
                located = [(i, f) for i, f in enumerate(frames) if f['span']['start'] == offset]
                assert len(located) == 1 and located[0][1]['surface'].encode() == token, 'individual judgment occurrence'
                index, frame = located[0]; offset += len(token) + 1
                for judgment in case['judgments']:
                    indices = [i for i, p in enumerate(frame['analysis']['analyses']) if prior_audit.matches(p, judgment)]
                    assert bool(indices) == (judgment['verdict'] == 'required'), 'all25private required/forbidden paths'
                    derived.append(dict(case_id=case['id'], judgment_id=judgment['id'], verdict=judgment['verdict'], record_index=index, analysis_indices=indices))
        assert run['observations'] == derived, 'all492individually rederived observations'
        observations += len(derived); key = (family, run['encoding'], run['mode'])
        assert key not in cached or cached[key] == run['jsonl'], 'exact cache output parity'
        cached[key] = run['jsonl']
    assert observations == 492 and report['streams'] == 36 and report['frames'] == sum(r['records'] for r in report['runs']) == 2100, 'complete finite source totals'
    assert report['linguistic_judgments_promoted'] is False, 'private judgments not silently promoted'


def inspect_native(v):
    for report, expected, count in [(v['native'], {**v['source']['entries'], **v['source']['boundary_entries']}, 43),
                                    (v['novel_native'], v['source']['novel_entries'], 15)]:
        binaries = bound_report(v, report, 'complete-gentle-command-long-native-cli-passed')
        assert len(report['records']) == report['entries'] == len(expected) == count, 'all complete Native owners'
        assert [r['id'] for r in report['records']] == list(expected), 'every Native owner/order'
        for row in report['records']:
            assert row['complete_original_entry'] == expected[row['id']], 'all original Native fields'
            assert len(row['captures']) == 2 and row['captures'][0]['json'] == row['captures'][1]['json'], 'both actual Native CLI versions'
            for capture, cli in zip(row['captures'], binaries, strict=True):
                assert capture['command'][:3] == [cli, 'dict', 'entry'] and capture['command'][3] in report['frozen_inputs'] and capture['command'][4:] == [row['id']], 'actual bound Native CLI and owner'
                assert capture['exit_code'] == 0 and sha(capture['json'].encode()) == capture['stdout_sha256'], 'actual Native response bytes'
                assert json.loads(capture['json'])['entry'] == expected[row['id']], 'full original CLI entry fields'
    assert len(set(v['source']['entries']) | set(v['source']['boundary_entries']) | set(v['source']['novel_entries'])) == 48, 'all48unique Native owners'


def inspect_cohorts(v):
    report = v['cohorts']; binaries = bound_report(v, report, 'complete-original-corpus-history-comparison-passed')
    assert [(r['family'], r['surfaces']) for r in report['runs']] == [('corpus', 32096), ('history', 21406)], 'all53502original cohort words'
    assert len(v['parent_cohorts']['runs']) == 2, 'both original cohort partitions'
    for run, parent in zip(report['runs'], v['parent_cohorts']['runs'], strict=True):
        assert (run['family'], run['surfaces']) == (parent['family'], parent['surfaces']), 'original cohort identity'
        assert len(run['captures']) == 2 and [c['binary'] for c in run['captures']] == list(binaries), 'both actual cohort executables'
        original = parent['captures'][1]['words']
        assert len(original) == run['surfaces'] and all(c['words'] == original for c in run['captures']), 'every complete ordered original WordAnalysis'
        assert run['changed_words'] == [], 'no hidden changed cohort words'
    assert report['individual_changed_words'] == [], 'no silently relabeled historical additions'


def inspect_gold(v):
    report = v['gold']; prior_audit.terminal(report, 'complete-gentle-command-long-annotated-comparison-passed')
    current = v['revision']['binding']['binaries']['adapter']
    assert report['frozen_inputs'][current['path']] == current['sha256'], 'exact compiled annotated adapter'
    previous = '/nix/store/jm0k70335nd5rkl6ppg7jp227q6j9r3j-klem-corpus-adapter-0.1.0/bin/klem-corpus-adapter'
    assert report['frozen_inputs'][previous] == '76cd89e0982f5e463302629bcf70e1f3cef19ed49df597a4bbef8e3daa21ce7f', 'exact installed annotated parent executable'
    assert len(report['runs']) == len(v['prior']['gold']['runs']) == 4, 'all four original annotated partitions'
    for run, parent, annotation in zip(report['runs'], v['prior']['gold']['runs'], v['prior']['parents']['annotations']['corpora'], strict=True):
        assert (run['corpus'], run['partition'], run['source_sha256']) == (parent['corpus'], parent['partition'], parent['source_sha256']), 'original corpus identity'
        assert run['command'] == [current['path'], run['corpus'], run['source']], 'actual bound annotated adapter command'
        assert run['before_command'] == [previous, run['corpus'], run['source']], 'actual installed parent adapter command'
        source_path = '/home/josh/projects/klem/' + run['source']
        assert run['source_sha256'] == report['frozen_inputs'][source_path], 'exact original corpus input bytes'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['stdout_sha256'] == run['before_stdout_sha256'] == sha(parent['jsonl'].encode()), 'every original annotated output byte unchanged'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) - 1 == run['rows'] and [{k: r[k] for k in ['id', 'surface', 'expected']} for r in rows[1:]] == [{k: r[k] for k in ['id', 'surface', 'expected']} for r in annotation['original_converted_rows']], 'every independent gold annotation'
        assert run['summary_changes'] == {}, 'unchanged original corpus summaries'
    assert sum(r['rows'] for r in report['runs']) == 66570 and report['individual_changed_rows'] == [], 'all66570original annotated rows'


def inspect_broad(v):
    report = v['broad']; binaries = bound_report(v, report, 'complete-gentle-command-long-broad-comparison-passed')
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible', 'novel-raw', 'novel-headword', 'novel-compatible', 'novel-headword-spacing', 'novel-compatible-spacing']
    assert [r['mode'] for r in report['runs']] == modes and sum(r['records'] for r in report['runs']) == 1128312, 'all eight complete broad streams'
    occurrences = [(19073, 19088), (269792, 269807), (528363, 528375), (528505, 528517), (629528, 629540), (640624, 640636), (702617, 702632), (749095, 749107)]
    for run, parent in zip(report['runs'], v['prior']['broad']['runs'], strict=True):
        raw = v['prior']['parents']['broad_inputs']['sources'][run['source']]['text'].encode()
        assert run['source'] == parent['source'] and run['source_sha256'] == parent['source_sha256'] == sha(raw), 'all original broad input bytes'
        assert run['exit_codes'] == [0, 0] and run['records'] == parent['records'] and run['original_bytes_conserved'], 'complete original broad frames'
        assert run['before_jsonl_sha256'] == parent['after_jsonl_sha256'], 'exact complete prior broad baseline'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        assert len(run['commands']) == 2 and [c[0] for c in run['commands']] == list(binaries), 'both actual bound broad binaries'
        for command in run['commands']:
            assert command[1:4] == ['text', run['actual_source'], '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags + (['--suggest-spacing'] if 'spacing' in run['mode'] else []), 'actual broad filter/spacing command'
        if run['mode'].startswith('candidate-'):
            assert not run['changed_frames'] and run['new_family_paths'] == 0 and run['before_jsonl_sha256'] == run['after_jsonl_sha256'], 'all candidate streams unchanged'
            continue
        assert [(c['after']['span']['start'], c['after']['span']['end']) for c in run['changed_frames']] == occurrences, 'every exact original novel occurrence'
        total = 0
        for change in run['changed_frames']:
            added = additions(change['before'], change['after']); total += len(added)
            start, end = change['after']['span']['start'], change['after']['span']['end']
            assert raw[start:end].decode() == change['after']['surface'], 'exact original novel surface bytes'
            begin = raw.rfind(b'\n', 0, start) + 1; finish = raw.find(b'\n', end); finish = len(raw) if finish < 0 else finish
            assert change['line_byte_start'] == begin and change['complete_original_line'] == raw[begin:finish].decode(), 'complete original novel context'
            assert change['id'] == f"gentle-command-long-broad-{run['mode']}-{start}-{end}" and change['contextual_verdict'] == 'unjudged', 'original occurrence identity and unjudged status'
            assert change['new_paths'] == added, 'every exact novel candidate addition'
        assert total == run['new_family_paths'] == (19 if run['mode'] == 'novel-raw' else 8), 'all exact per-policy novel additions'


def inspect_novel(v):
    report = v['novel']; prior_audit.terminal(report, 'complete-original-long-gentle-novel-occurrences-and-lexical-proposals-preserved')
    assert not report['proposals_precede_runtime'] and not report['active_shared_cases_or_reviews_changed'], 'honest post-observation unpromoted novel proposals'
    raw_run = v['broad']['runs'][3]; compatible_run = v['broad']['runs'][5]
    assert report['original_broad_capture_sha256'] == v['hashes']['gentle-command-long-broad.json.gz'], 'exact original broad packet binding'
    assert len(report['items']) == report['novel_occurrences'] == report['typed_structural_proposals'] == 8 and report['new_raw_paths'] == 19, 'all eight bounded novel proposals'
    assert len(report['complete_imported_entries']) == report['native_owners'] == 15 and report['complete_imported_entries'] == v['source']['novel_entries'], 'all complete original novel lexical owners'
    assert {ident: entry(owner) for ident, owner in report['original_native_entries'].items()} == report['complete_imported_entries'], 'all fifteen original Native import projections'
    assert len(v['novel_suite']['cases']) == 8, 'all eight individual novel regressions'
    for item, change, compatible, case in zip(report['items'], raw_run['changed_frames'], compatible_run['changed_frames'], v['novel_suite']['cases'], strict=True):
        start, end = change['after']['span']['start'], change['after']['span']['end']
        assert item['id'] == case['id'] == f'long-gentle-novel-{start}-{end}', 'exact individual novel case identity'
        assert item['surface'] == case['surface'] == change['after']['surface'] and item['span'] == change['after']['span'], 'original individual novel token'
        assert item['source_sha256'] == report['source_sha256'] == raw_run['source_sha256'], 'original novel source identity'
        assert item['complete_original_line'] == change['complete_original_line'] and item['line_byte_start'] == change['line_byte_start'], 'every full original novel context'
        assert item['original_raw_before'] == change['before'] and item['original_raw_after'] == change['after'] and item['all_new_raw_paths'] == change['new_paths'] and item['compatible_observation'] == compatible, 'all original raw and compatible alternatives'
        target = item['source_based_typed_proposal']; judgment = case['judgments'][0]
        assert len(case['judgments']) == 1 and judgment['verdict'] == 'required' and all(judgment[k] == value for k, value in target.items()), 'specific post-observation lexical proposal'
        assert sum(prior_audit.matches(p, target) for p in compatible['new_paths']) == 1 and item['independent_review'] == 'pending', 'specific compatible path with independent review pending'
        assert item['lexical_owner_ids'] == [ident for ident, owner in report['complete_imported_entries'].items() if owner['headword'] == target['lemmas'][0]], 'every complete lexical homonym owner'
        assert report['complete_imported_entries'][item['ending_owner']]['headword'] in ['-려무나', '-으려무나'], 'actual Native long-ending owner'


def inspect_validation(v):
    report = v['validation']; prior_audit.terminal(report, 'passed')
    assert report['head_unchanged'] and report['index_unchanged'] and len(report['frozen_inputs']) == 6638, 'complete additional regression source freeze'
    assert report['controls'] == 45 and report['rust_totals'] == {'passed': 18, 'failed': 0, 'ignored': 0} and report['rust_batches'] == 3, 'actual additional18Rust45controls'
    assert report['log_sha256'] == v['validation_hashes']['gentle-command-long-runtime-regressions.log'], 'complete additional regression log'
    assert all(step['exit_code'] == 0 for step in report['results']), 'all actual regression commands passed'
    assert sum(step['controls'] for step in report['results']) == 45, 'all actual regression control totals'
    preparation = v['proof']['gentle-command-long-runtime-preparation-failures.json']
    assert preparation['state'] == 'initial-preparation-failure-preserved' and preparation['actual_source_session_exit'] == preparation['actual_native_session_exit'] == 1 and not preparation['source_or_baseline_changed'], 'original preparation failures preserved'
    shape = v['proof']['gentle-command-long-dapda-proposal-shape-failure.json']
    assert shape['actual_exit_code'] == 1 and shape['original_private25_and_shared_judgments_unchanged'], 'original derived-shape failure preserved'
    compile_failure = v['proof']['gentle-command-long-interaction-compile-failure.json']
    assert compile_failure['state'] == 'failed' and compile_failure['actual_exit_code'] == 101 and sha(compile_failure['source'].encode()) == compile_failure['source_sha256'], 'original interaction compile failure preserved'


def inspect(v):
    revision.inspect(v['revision']); source_audit.inspect(v['source'])
    inspect_streams(v); inspect_native(v); inspect_cohorts(v); inspect_gold(v)
    inspect_broad(v); inspect_novel(v); inspect_validation(v)
    return dict(original_rust_tests=1189, additional_focused_rust_tests=18,
                additional_controls=45, source_streams=36, source_frames=2100,
                target_checks=492, unique_native_owners=48, cohort_words=53502,
                changed_cohort_words=0, annotated_rows=66570, changed_annotated_rows=0,
                broad_frames=1128312, novel_occurrences=8, raw_novel_additions=19,
                compatible_novel_additions=8, other_raw_novel_additions_unjudged=11,
                current_installed_browser_nix_main='pending',
                contextual_and_independent_review='pending', full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
