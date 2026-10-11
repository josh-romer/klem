"""Audit -세나 source judgments against preserved original data and CLI output."""
import gzip
import hashlib
import itertools
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'friendly-hortative-sena'
MANIFEST_SHA = '1a2e9d3f9430b00c743e47ef262623ab19e33c29429af8a9fe50a72e34a3257b'
SUITE_SHA = 'd85973f2aa29dc5f82b3710f23b46f7dad8e67785cbf4b04d8edfc81056f91be'
BASELINE_HEAD = '6cf27565c7891005de12651abcb7f18911495adf'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def manifest():
    raw = (ROOT / f'docs/{PREFIX}-source-baseline-proof-archive.json').read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'immutable original evidence manifest'
    return json.loads(raw)


def inputs():
    originals = {}
    for name, item in manifest()['files'].items():
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'packed original evidence bytes'
        original = gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'original evidence bytes'
        originals[name] = original
    fixtures = ROOT / 'tests/fixtures'

    def read(suffix):
        return json.loads((fixtures / f'{PREFIX}-{suffix}.json').read_bytes())

    return dict(
        originals=originals, source=read('source'), suite=read('validity'),
        suite_raw=(fixtures / f'{PREFIX}-validity.json').read_bytes(),
        native=read('native'), entries=read('native-entries'),
        ending_native=read('ending-native'), prior_paths=read('prior-paths'),
        captures=json.loads(gzip.decompress(originals[f'{PREFIX}-baseline-records.json.gz'])),
        baseline=json.loads(originals[f'{PREFIX}-baseline.json']),
        installed=json.loads(gzip.decompress(originals['baseline-installed-reference.json.gz'])),
        label=json.loads((ROOT / 'web/src/grammar-labels.json').read_bytes())['-세나'])


def lemma_match(analysis, judgment):
    return ([l['text'] for l in analysis['lemmas']] == judgment['lemmas']
            and [l['kind'] for l in analysis['lemmas']] == judgment['lemma_kinds'])


def typed_match(analysis, judgment):
    return (lemma_match(analysis, judgment)
            and [m['form'] for m in analysis['morphemes']] == judgment['morphemes']
            and [m['kind'] for m in analysis['morphemes']] == judgment['morpheme_kinds'])


def inspect(v):
    original = v['originals']
    expected_files = manifest()['files']
    assert set(original) == set(expected_files), 'all original evidence artifacts'
    assert all(sha(original[n]) == item['source_sha256']
               for n, item in expected_files.items()), 'all original payload bytes'

    def read(name):
        raw = original[name]
        return json.loads(gzip.decompress(raw) if name.endswith('.gz') else raw)

    author = read(f'{PREFIX}-source-authoring-reviewed.json')
    initial_author = read(f'{PREFIX}-source-authoring.json')
    closure = read(f'{PREFIX}-original-native-closure-reviewed.json.gz')
    initial_closure = read(f'{PREFIX}-original-native-closure.json.gz')
    assert v['source'] == author, 'complete original authoring and correction fields'
    assert {k: value for k, value in initial_closure.items() if k != 'state'} == {
        k: value for k, value in closure.items() if k != 'state'
    }, 'metadata correction preserves all original Native/LMF bytes'
    assert initial_closure['state'] == 'complete-original-gena-owner-lexical-boundary-closure'
    assert closure['state'] == 'complete-original-sena-owner-lexical-boundary-closure'
    correction = author['metadata_label_correction']
    assert correction['from_state'] == initial_closure['state']
    assert correction['to_state'] == closure['state']
    assert all(correction[k] is True for k in [
        'case_and_judgment_bytes_unchanged',
        'all_complete_native_and_original_lmf_fields_unchanged', 'original_payloads_retained'])
    extra = {'original_authoring_producer', 'original_authoring_sha256',
             'original_native_closure_sha256', 'metadata_label_correction'}
    changed = {'native_closure_sha256', 'producer'}
    assert {k: value for k, value in author.items() if k not in extra | changed} == {
        k: value for k, value in initial_author.items() if k not in changed
    }, 'correction cannot change any source target or judgment'
    assert author['original_authoring_sha256'] == sha(original[f'{PREFIX}-source-authoring.json'])
    assert author['original_native_closure_sha256'] == sha(original[f'{PREFIX}-original-native-closure.json.gz'])
    assert author['native_closure_sha256'] == sha(original[f'{PREFIX}-original-native-closure-reviewed.json.gz'])
    assert author['original_authoring_producer'] == initial_author['producer']
    for record, name in [(initial_author, 'author_friendly_hortative_sena_sources.py'),
                         (author, 'review_friendly_hortative_sena_authoring_metadata.py'),
                         (v['baseline'], 'capture_friendly_hortative_sena_baseline.py')]:
        assert record['producer'] == dict(text=original[name].decode(), sha256=sha(original[name])), 'original producer binding'
    assert not author['candidate_runtime_observed'] and not author['shared_cases_reviews_changed']
    assert author['historical_whole_inventory_discovery_already_exists'] is True
    assert author['prior_discovery_outputs_used_for_target_selection'] is False
    assert author['required_rule_ids_assigned'] is False, 'canonical baseline independent of future rule IDs'

    assert sha(v['suite_raw']) == SUITE_SHA == author['suite_sha256']
    assert v['suite_raw'] == original[f'{PREFIX}-validity.json'], 'exact preauthored judgment bytes'
    assert v['suite'] == json.loads(v['suite_raw']), 'every current judgment field'
    cases = v['suite']['cases']
    assert len(cases) == 25 and len({c['id'] for c in cases}) == 25
    assert {kind: sum(c['judgments'][0]['verdict'] == kind for c in cases)
            for kind in ['required', 'forbidden']} == {'required': 19, 'forbidden': 6}
    assert all(len(c['judgments']) == 1 and not c['judgments'][0].get('required_rules') for c in cases)
    owner = author['owners']['krdict:78469']
    assert author['owner_ids'] == ['krdict:78469'] and owner['headword'] == '-세나'
    assert owner['notes'] == ['동사 또는 ‘-으시-’ 뒤에 붙여 쓴다.']
    assert len(owner['senses']) == 1 and len(owner['senses'][0]['examples']) == 5
    assert set(author['related_owners']) == {'krdict:78404', 'krdict:78434'}
    assert len(author['items']) == 5
    for item, case, group in zip(author['items'], cases[:5], owner['senses'][0]['examples'], strict=True):
        assert item['complete_original_group'] == group, 'complete original dialogue group'
        assert item['typed_target'] == case['judgments'][0] and item['id'] == case['id'] and item['surface'] == case['surface']
        span = item['local_span']
        assert '\n'.join(group).encode()[span['start']:span['end']].decode() == item['surface'], 'original UTF-8 occurrence'
        assert item['contextual_verdict'] == 'unjudged' and item['independent_korean_review'] == 'pending'

    assert len(closure['source_exports']) == 11 and len(closure['selected_heads']) == 23
    assert len(closure['complete_native_entries']) == 36
    assert v['entries'] == closure['complete_native_entries'], 'every Native field and same-head homonym'
    lexical = v['native']['LexicalResource']['Lexicon']['LexicalEntry']
    assert lexical == list(closure['original_lmf'].values()), 'complete original LMF and order'
    assert {e['id']: e for e in map(entry, lexical)} == v['entries'], 'independent Native projection'
    assert {e['headword'] for e in v['entries'].values()} == set(closure['selected_heads'])
    assert author['owners'] == {'krdict:78469': v['entries']['krdict:78469']}
    assert author['related_owners'] == {k: v['entries'][k] for k in ['krdict:78404', 'krdict:78434']}
    assert v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'] == [closure['original_lmf']['krdict:78469']]
    assert v['label']['kind'] == 'ending' and v['label']['label'] == 'Friendly invitation'
    assert v['label']['sources'] == [{'id': 78469, 'headword': '-세나', 'pos': '어미'}], 'label attributed only to its own ending'

    baseline = v['baseline']
    installed = v['installed']
    assert baseline == read(f'{PREFIX}-baseline.json'), 'complete actual baseline receipt'
    assert installed == read('baseline-installed-reference.json.gz'), 'complete actual installed parent reference'
    for report in [baseline, installed]:
        assert report['state'] == 'passed' and all(report[k] is True for k in [
            'inputs_unchanged', 'source_unchanged', 'head_unchanged', 'index_unchanged'])
    assert baseline['head'] == installed['captured_head'] == BASELINE_HEAD
    assert baseline['index_sha256'] == installed['index_sha256']
    assert len(baseline['source_inputs']) == 6985
    assert all(baseline['source_inputs'][n] == digest for n, digest in installed['profiles']['klem']['files'].items())
    cli = installed['binaries']['klem']
    assert baseline['frozen_inputs'][cli['path']] == cli['sha256'], 'actual installed CLI binary binding'
    frozen_by_name = {Path(path).name: digest for path, digest in baseline['frozen_inputs'].items()}
    for name in [f'{PREFIX}-source-authoring-reviewed.json', f'{PREFIX}-validity.json',
                 f'{PREFIX}-original-native-closure-reviewed.json.gz', 'capture_friendly_hortative_sena_baseline.py']:
        assert frozen_by_name[name] == sha(original[name]), 'frozen authored and capture input'
    assert frozen_by_name['friendly-command-gena-installed-runtime.json.gz'] == sha(original['baseline-installed-reference.json.gz'])
    assert frozen_by_name['krdict.db'] == '23d993696c55d0e54660e4a2b23dac7d68525fecb1fdc44341e1f2b3f75dead5'
    assert baseline['source_authoring_sha256'] == sha(original[f'{PREFIX}-source-authoring-reviewed.json'])
    assert baseline['capture_sha256'] == sha(original[f'{PREFIX}-baseline-records.json.gz'])
    assert baseline['log_sha256'] == sha(original[f'{PREFIX}-baseline.log'])
    assert author['authored_at'] < correction['corrected_at'] < baseline['started_at'] < baseline['finished_at']
    assert not baseline['production_changed'] and not baseline['shared_judgments_reviews_changed']

    packet = v['captures']
    assert packet == read(f'{PREFIX}-baseline-records.json.gz'), 'all full original captured output fields'
    families = {
        'complete-original-groups': '\n\n'.join('\n'.join(i['complete_original_group']) for i in author['items']) + '\n',
        'preauthored-25-proposals': '\n'.join(c['surface'] for c in cases) + '\n',
        'unjudged-lexical-prefinal-boundaries': '\n'.join([
            '예쁘세나', '예쁘시세나', '학생이시세나', '학생답시세나', '먹었세나', '먹겠세나', '가세나요']) + '\n'}
    policies = set(itertools.product(families, ['NFC', 'NFD'], ['all', 'headwords', 'compatible'], [0, 4096]))
    captures = packet['captures']
    assert len(captures) == 36 and {(c['family'], c['normalization'], c['mode'], c['cache_bytes']) for c in captures} == policies
    totals = dict(frame_count=0, canonical_typed_matches=0, required_canonical_typed_matches=0,
                  forbidden_canonical_typed_matches=0, required_lemma_role_matches=0, required_observations=0)
    log_rows = []
    for capture in captures:
        assert capture['exit_code'] == 0 and capture['stderr'] == ''
        text = unicodedata.normalize(capture['normalization'], families[capture['family']])
        assert capture['input'] == text, 'entire independently assembled baseline input'
        command = [cli['path'], 'text', '-', '--dictionary', next(p for p in baseline['frozen_inputs'] if Path(p).name == 'krdict.db'),
                   '--cache-bytes', str(capture['cache_bytes'])]
        if capture['mode'] != 'all':
            command += ['--dict-only' if capture['mode'] == 'headwords' else '--dict-compatible']
        assert capture['command'] == command, 'actual Unicode/filter/cache command'
        frames = capture['frames']
        assert [json.loads(line) for line in capture['stdout'].splitlines()] == frames
        raw = text.encode()
        cursor = 0
        for frame in frames:
            span = frame['span']
            assert span['start'] == cursor and raw[cursor:span['end']].decode() == frame['surface']
            cursor = span['end']
        assert cursor == len(raw), 'every original UTF-8/NFD span'
        observations = []
        for case in cases:
            j = case['judgments'][0]
            for frame in frames:
                if unicodedata.normalize('NFC', frame['surface']) == case['surface']:
                    analyses = frame['analysis']['analyses']
                    observations.append(dict(case_id=case['id'], span=frame['span'], verdict=j['verdict'],
                                             typed_path_present=any(typed_match(a, j) for a in analyses),
                                             lemma_role_path_present=any(lemma_match(a, j) for a in analyses)))
        assert capture['observations'] == observations, 'recomputed typed and lemma-role matches independent of rule provenance'
        totals['frame_count'] += len(frames)
        for o in observations:
            totals['canonical_typed_matches'] += o['typed_path_present']
            totals[f"{o['verdict']}_canonical_typed_matches"] += o['typed_path_present']
            if o['verdict'] == 'required':
                totals['required_lemma_role_matches'] += o['lemma_role_path_present']
                totals['required_observations'] += 1
        peer = next(c for c in captures if all(c[k] == capture[k] for k in ['family', 'normalization', 'mode'])
                    and c['cache_bytes'] != capture['cache_bytes'])
        assert capture['stdout'] == peer['stdout'], 'complete cache parity'
        log_rows.append({k: capture[k] for k in ['family', 'normalization', 'mode', 'cache_bytes']} | dict(
            frames=len(frames), canonical_typed_matches=sum(o['typed_path_present'] for o in observations),
            required_lemma_role_matches=sum(o['lemma_role_path_present'] for o in observations if o['verdict'] == 'required')))
    assert log_rows == [json.loads(line) for line in original[f'{PREFIX}-baseline.log'].splitlines()]
    assert all(baseline[k] == count for k, count in totals.items()), 'recomputed whole baseline totals'
    assert totals == dict(frame_count=1608, canonical_typed_matches=0, required_canonical_typed_matches=0,
                         forbidden_canonical_typed_matches=0, required_lemma_role_matches=0, required_observations=324)
    assert baseline['runs'] == 36 and baseline['complete_native_owners'] == 36 and baseline['preauthored_cases'] == 25
    assert set(packet['native_entries']) == set(v['entries'])
    db = next(p for p in baseline['frozen_inputs'] if Path(p).name == 'krdict.db')
    for ident, response in packet['native_entries'].items():
        assert response['exit_code'] == 0 and response['stderr'] == ''
        assert response['command'] == [cli['path'], 'dict', 'entry', db, ident]
        assert json.loads(response['stdout']) == response['response']
        assert response['response']['entry'] == v['entries'][ident], 'all actual complete Native responses'
    prior = [f for c in captures if c['normalization'] == 'NFC' and c['mode'] == 'all' and c['cache_bytes'] == 0
             for f in c['frames'] if f['kind'] == 'word']
    assert v['prior_paths'] == prior and len(prior) == 63, 'all prior paths, assessments, spans and ordering'
    return dict(source_groups=5, private_cases=25, required=19, forbidden=6,
                full_native_owners=36, baseline_runs=36, baseline_frames=1608,
                required_observations=324, canonical_typed_matches=0, required_lemma_role_matches=0,
                prior_word_records=63, context_register_independent_review='pending', full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
