"""Independently verify Source-bound -세나 binaries and complete CLI comparisons."""
import gzip
import json
import os
import unicodedata
from pathlib import Path

import friendly_hortative_sena_source_audit as source

ROOT = source.ROOT
sha = source.sha
RULE = 'ending.friendly_hortative.sena'
RUNTIME_SHA = '58703c44a44f232485d2f24a577d22f586e4a175d2fca9219eddf30cd0696d44'
SELECTED_SHA = '6356d488a20767f5a10d25b2be135910607e95172bdee45aba4f1d41cb6a10fb'
CHANGES = {'src/grammar.rs', 'src/engine.rs', 'src/dictionary/attachment.rs',
           'src/bin/klem-web/grammar_labels.rs', 'web/src/grammar-labels.json'}


def archive(name, digest):
    raw = (ROOT / 'docs' / name).read_bytes()
    assert sha(raw) == digest, 'immutable original runtime evidence manifest'
    result, hashes, originals = {}, {}, {}
    for name, item in json.loads(raw)['files'].items():
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'packed original runtime evidence'
        raw = gzip.decompress(packed)
        assert sha(raw) == item['source_sha256'], 'full original runtime evidence'
        originals[name] = raw
        hashes[name] = sha(raw)
        if name.endswith('.json') or name.endswith('.json.gz'):
            result[name] = json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)
    return result, hashes, originals


def binary_mode(value=None):
    mode = os.environ.get('KLEM_SENA_BINARY_EVIDENCE', 'live') if value is None else value
    assert mode in {'live', 'captured'}, 'explicit live or captured binary evidence mode'
    return mode


def inputs(binary_evidence=None):
    mode = binary_mode(binary_evidence)
    proof, hashes, originals = archive('friendly-hortative-sena-runtime-proof-archive.json', RUNTIME_SHA)
    selected, selected_hashes, selected_originals = archive(
        'friendly-hortative-sena-selected-source-proof-archive.json', SELECTED_SHA)
    binding = proof['friendly-hortative-sena-complete-runtime-binding.json']
    current_binaries = ({name: sha(Path(row['path']).read_bytes()) for name, row in binding['binaries'].items()}
                        if mode == 'live' else {name: row['sha256'] for name, row in binding['binaries'].items()})
    parent_binaries = ({path: sha(Path(path).read_bytes()) for path in binding['protected_parent_binaries']}
                       if mode == 'live' else binding['protected_parent_binaries'].copy())
    evidence = dict(mode=mode, live_executable_files_verified=mode == 'live',
                    binding_manifest_sha256=RUNTIME_SHA,
                    binding_receipt_sha256=hashes['friendly-hortative-sena-complete-runtime-binding.json'])
    return dict(source=source.inputs(), hashes=hashes, originals=originals,
                selected_hashes=selected_hashes, selected_originals=selected_originals,
                selected=selected['friendly-hortative-sena-selected-source.json'],
                binding=binding, streams=proof['friendly-hortative-sena-runtime.json'],
                captures=proof['friendly-hortative-sena-runtime-records.json.gz'],
                current_binaries=current_binaries, parent_binaries=parent_binaries, binary_evidence=evidence,
                current={p: sha((ROOT / p).read_bytes()) for p in binding['production_inputs']},
                frontend={p: sha((ROOT / p).read_bytes()) for p in binding['frontend_inputs']})


def terminal(report):
    assert report['state'] == 'passed', 'actual passed terminal receipt'
    assert all(report[k] is True for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged']), 'captured Source/HEAD/index unchanged'


def inspect_binding(v):
    binding, selected = v['binding'], v['selected']
    terminal(binding)
    terminal(selected)
    assert binding['external_inputs_unchanged'] and binding['parent_production_unchanged'] and binding['protected_parent_binaries_unchanged'], 'captured external and protected parent inputs'
    assert binding['production_inputs'] == v['current'] and len(v['current']) == 44, 'complete44 current production inputs'
    assert v['frontend'] == binding['frontend_inputs'] and len(v['frontend']) == 18, 'complete18 current frontend inputs'
    assert binding['production_inputs'] == selected['production_inputs'], 'actual selected production closure'
    assert set(binding['parent_production_inputs']) == set(v['current']), 'complete parent production closure'
    changed = {p for p in v['current'] if v['current'][p] != binding['parent_production_inputs'][p]}
    assert changed == CHANGES == set(binding['declared_production_changes']) == set(selected['declared_production_changes']), 'exact five declared production changes'
    parent_files = v['source']['installed']['profiles']['klem']['files']
    assert all(parent_files[p] == digest for p, digest in binding['parent_production_inputs'].items()), 'exact installed parent Source binding'
    assert binding['compiled_profiles'] == selected['profiles'], 'all actual selected compile profiles'
    assert {p: len(r['files']) for p, r in selected['profiles'].items()} == {'klem': 1153, 'corpus-adapter': 1153, 'web-assets': 18}, 'complete1153/1153/18 compile profiles'
    for attr, prefix in [('klem', ''), ('corpus-adapter', ''), ('web-assets', 'web/')]:
        assert all(binding['frozen_inputs'][prefix + p] == digest
                   for p, digest in selected['profiles'][attr]['files'].items()), 'every captured compile input'
    assert len(binding['frozen_inputs']) == 7049 and all(binding['frozen_inputs'][p] == digest for p, digest in v['current'].items()), 'complete captured production files'
    assert selected['controls'] == 64 and [r['controls'] for r in selected['results']] == [0, 42, 22, 0], 'actual selected64 controls'
    assert all(r['exit_code'] == 0 for r in selected['results']), 'all selected commands passed'
    assert binding['results'] == [{'command': ['cargo', 'build', '--locked', '--offline', '--features', 'web', '--bins', '--example', 'evaluate'], 'exit_code': 0}], 'actual CLI/server/adapter build command'
    for report, name, originals in [(binding, 'build_friendly_hortative_sena_runtime_binding.py', v['originals']),
                                    (selected, 'preflight_friendly_hortative_sena_selected_source.py', v['selected_originals'])]:
        assert report['producer'] == dict(text=originals[name].decode(), sha256=sha(originals[name])), 'exact original build/selection producer'
    assert binding['log_sha256'] == v['hashes']['friendly-hortative-sena-complete-runtime-binding.log'], 'full original build log'
    assert selected['log_sha256'] == v['selected_hashes']['friendly-hortative-sena-selected-source.log'], 'full original selection log'
    assert set(binding['binaries']) == {'klem', 'server', 'adapter'}, 'all three captured binaries'
    assert v['current_binaries'] == {name: b['sha256'] for name, b in binding['binaries'].items()}, 'all actual current binary fingerprints'
    assert all(len(b['sha256']) == 64 and b['path'].startswith('/home/josh/projects/klem/.direnv/friendly-hortative-sena-target/debug/') for b in binding['binaries'].values()), 'own captured binary paths'
    assert v['parent_binaries'] == binding['protected_parent_binaries'], 'all original parent binaries retained'
    mode = binary_mode(v['binary_evidence']['mode'])
    assert v['binary_evidence'] == dict(mode=mode, live_executable_files_verified=mode == 'live',
        binding_manifest_sha256=RUNTIME_SHA,
        binding_receipt_sha256=v['hashes']['friendly-hortative-sena-complete-runtime-binding.json']), 'honest immutable binary evidence scope'


def word_additions(old, new):
    assert {k: v for k, v in old.items() if k != 'analyses'} == {k: v for k, v in new.items() if k != 'analyses'}, 'all original WordAnalysis fields'
    before, after = old['analyses'], new['analyses']
    assert [p for p in after if p in before] == before, 'every old candidate and relative order'
    assert len(after) == len({json.dumps(p, sort_keys=True) for p in after}), 'unique candidate records'
    added = [p for p in after if p not in before]
    assert all(RULE in p['rules'] and {'form': '세나', 'kind': 'ending'} in p['morphemes'] for p in added), 'only canonical Sena additions'
    return added


def additions(old, new):
    assert {k: v for k, v in old.items() if k not in ['analysis', 'dictionary']} == {
        k: v for k, v in new.items() if k not in ['analysis', 'dictionary']}, 'original token identity and ownership'
    if old['kind'] != 'word':
        assert old == new, 'all original nonword fields'
        return []
    added = word_additions(old['analysis'], new['analysis'])
    before, after = old['dictionary'], new['dictionary']
    assert {k: v for k, v in before.items() if k not in ['readings', 'lemmas']} == {
        k: v for k, v in after.items() if k not in ['readings', 'lemmas']}, 'original dictionary source and fingerprint'
    assert len(after['readings']) == len(new['analysis']['analyses']), 'one dictionary assessment per candidate'
    for ordinal, path in enumerate(old['analysis']['analyses']):
        assert before['readings'][ordinal] == after['readings'][new['analysis']['analyses'].index(path)], 'every old full dictionary assessment'
    assert all(owner in after['lemmas'] for owner in before['lemmas']), 'every old Native owner and field'
    return added


def inspect_streams(v):
    report, packet, baseline = v['streams'], v['captures'], v['source']['captures']
    terminal(report)
    assert report['external_inputs_unchanged'], 'actual captured external inputs unchanged'
    binding = v['binding']
    assert report['head'] == binding['head'] and report['index_sha256'] == binding['index_sha256'], 'same current binary Source revision'
    assert report['frozen_inputs'] == binding['frozen_inputs'], 'same complete7049 Source snapshot'
    cli = binding['binaries']['klem']
    assert report['external_inputs'][cli['path']] == cli['sha256'], 'exact captured CLI executable'
    assert report['capture_sha256'] == v['hashes']['friendly-hortative-sena-runtime-records.json.gz'], 'full original capture binding'
    assert report['log_sha256'] == v['hashes']['friendly-hortative-sena-runtime.log'], 'full original runtime log'
    name = 'capture_friendly_hortative_sena_runtime.py'
    assert report['producer'] == dict(text=v['originals'][name].decode(), sha256=sha(v['originals'][name])), 'exact original capture producer'
    assert len(packet['captures']) == len(baseline['captures']) == report['runs'] == 36, 'every36 policy capture'
    totals = dict(frames=0, old_paths=0, added=0, required=0, forbidden=0)
    log_rows = []
    for run, previous in zip(packet['captures'], baseline['captures'], strict=True):
        assert all(run[k] == previous[k] for k in ['family', 'normalization', 'mode', 'cache_bytes', 'input']), 'entire baseline input and policy'
        assert run['command'] == [cli['path'], *previous['command'][1:]] and run['exit_code'] == 0 and run['stderr'] == '', 'actual bound Unicode/filter/cache command'
        assert [json.loads(line) for line in run['stdout'].splitlines()] == run['frames'], 'complete stdout frame order'
        assert len(run['frames']) == len(previous['frames']), 'every original frame'
        cursor, observations, new_paths = 0, [], []
        raw = run['input'].encode()
        for old, current in zip(previous['frames'], run['frames'], strict=True):
            span = current['span']
            assert span['start'] == cursor and raw[cursor:span['end']].decode() == current['surface'], 'contiguous Unicode byte spans'
            cursor = span['end']
            added = additions(old, current)
            totals['frames'] += 1
            totals['added'] += len(added)
            if current['kind'] != 'word':
                continue
            paths = current['analysis']['analyses']
            totals['old_paths'] += len(old['analysis']['analyses'])
            new_paths.extend(dict(surface=current['surface'], span=span, analysis=p,
                                  assessment=current['dictionary']['readings'][paths.index(p)]) for p in added)
            for case in v['source']['suite']['cases']:
                if unicodedata.normalize('NFC', current['surface']) != case['surface']:
                    continue
                j = case['judgments'][0]
                present = any(source.typed_match(p, j) for p in paths)
                assert present == (j['verdict'] == 'required'), 'every independent required and forbidden path'
                totals[j['verdict']] += 1
                observations.append(dict(case_id=case['id'], span=span, verdict=j['verdict'], present=present))
        assert cursor == len(raw), 'entire original input covered'
        assert run['observations'] == observations, 'all rederived judgment observations'
        assert run['new_paths'] == new_paths, 'all rederived added paths and assessments'
        log_rows.append({k: run[k] for k in ['family', 'normalization', 'mode', 'cache_bytes']} |
                        dict(frames=len(run['frames']), additions=len(new_paths)))
        for peer in packet['captures']:
            if all(run[k] == peer[k] for k in ['family', 'normalization', 'mode']):
                assert run['stdout'] == peer['stdout'], 'exact full cache parity'
            if all(run[k] == peer[k] for k in ['family', 'mode', 'cache_bytes']):
                def project(r):
                    return [(f['kind'], unicodedata.normalize('NFC', f['surface']), f['analysis'], f['dictionary']) for f in r['frames']]
                assert project(run) == project(peer), 'complete NFC/NFD analysis and assessment parity'
    assert totals == dict(frames=1608, old_paths=2916, added=716, required=324, forbidden=72), 'all independently rederived CLI totals'
    assert (report['frames'], report['old_paths_preserved'], report['new_unjudged_paths'], report['required_checks'], report['forbidden_checks']) == tuple(totals.values()), 'reported totals equal complete captures'
    assert log_rows == [json.loads(line) for line in v['originals']['friendly-hortative-sena-runtime.log'].splitlines()], 'all complete rederived runtime log rows'
    assert set(packet['native_entries']) == set(baseline['native_entries']) == set(v['source']['entries']) and report['complete_native_owners'] == 36, 'all36 complete Native responses'
    for ident, row in packet['native_entries'].items():
        old = baseline['native_entries'][ident]
        assert row['command'] == [cli['path'], *old['command'][1:]] and row['exit_code'] == 0, 'actual bound Native command'
        assert row['stdout'] == old['stdout'] and row['stderr'] == old['stderr'], 'unchanged full Native stdout bytes'
        assert json.loads(row['stdout']) == row['response'] and row['response']['entry'] == v['source']['entries'][ident], 'complete original Native fields and homonyms'


def inspect_boundaries(v):
    runs = v['captures']['captures']
    raw = next(r for r in runs if r['family'] == 'unjudged-lexical-prefinal-boundaries' and r['mode'] == 'all'
               and r['normalization'] == 'NFC' and r['cache_bytes'] == 0)
    tests = [('예쁘시세나', ['예쁘다'], ['시', '세나']),
             ('학생이시세나', ['학생', '이다'], ['시', '세나']),
             ('먹었세나', ['먹다'], ['었', '세나']), ('먹겠세나', ['먹다'], ['겠', '세나'])]
    for surface, lemmas, forms in tests:
        frame = next(f for f in raw['frames'] if f['surface'] == surface)
        i = next(i for i, p in enumerate(frame['analysis']['analyses'])
                 if [l['text'] for l in p['lemmas']] == lemmas and [m['form'] for m in p['morphemes']] == forms and RULE in p['rules'])
        assert frame['dictionary']['readings'][i]['status'] == 'unknown', 'unreviewed prefinals keep Unknown status'
    frame = next(f for f in raw['frames'] if f['surface'] == '예쁘세나')
    i = next(i for i, p in enumerate(frame['analysis']['analyses']) if [l['text'] for l in p['lemmas']] == ['예쁘다']
             and [m['form'] for m in p['morphemes']] == ['세나'] and RULE in p['rules'])
    assert frame['dictionary']['readings'][i]['status'] == 'incompatible', 'bare known adjective cannot borrow verb license'
    run = next(r for r in runs if r['family'] == 'preauthored-25-proposals' and r['mode'] == 'compatible'
               and r['normalization'] == 'NFC' and r['cache_bytes'] == 0)
    for frame in [f for f in run['frames'] if f['surface'] == '사세나']:
        for lemma, recovery in [('살다', True), ('사다', False)]:
            p = next(p for p in frame['analysis']['analyses'] if [l['text'] for l in p['lemmas']] == [lemma]
                     and [m['form'] for m in p['morphemes']] == ['세나'] and RULE in p['rules'])
            assert ('deletion.rieul' in p['rules']) == recovery, 'both original lexical paths with exact Rieul recovery'


def inspect(v):
    source.inspect(v['source'])
    inspect_binding(v)
    inspect_streams(v)
    inspect_boundaries(v)
    return dict(cli_runs=36, cli_frames=1608, old_path_occurrences=2916, new_unjudged_path_occurrences=716,
                required_checks=324, forbidden_checks=72, complete_native_owners=36,
                production_inputs=44, frontend_inputs=18, binary_evidence=v['binary_evidence'],
                full_Rust_history_broad_gold_browser_installed_Nix_main_quiet_context_register_independent_review='pending',
                full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
