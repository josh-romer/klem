"""Audit finite original connective sources, individual judgments and all source frames."""
import argparse
import gzip
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from native_lmf import entry, verify_native_lmf
from klem_declarative_contrast_inversion import FORMS, split_parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def producer(report):
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256']


def matches(candidate, judgment):
    return ([l['text'] for l in candidate['lemmas']] == judgment['lemmas']
            and [l['kind'] for l in candidate['lemmas']] == judgment['lemma_kinds']
            and [m['form'] for m in candidate['morphemes']] == judgment['morphemes']
            and [m['kind'] for m in candidate['morphemes']] == judgment['morpheme_kinds']
            and set(judgment['required_rules']) <= set(candidate['rules']))


def verify_sources(capture, preparation, targets, suite, originals, catalog, replay, target_audit):
    for report in [capture, preparation, replay, target_audit]:
        producer(report)
    native = preparation['complete_native_entries']
    assert len(native) == 115 and set(native) == set(preparation['original_lmf'])
    for ident, raw in preparation['original_lmf'].items():
        assert entry(raw) == native[ident]
    verify_native_lmf(preparation['english_projection'], native)
    primary = {f'krdict:{id}' for id in range(80321, 80327)}
    assert set(capture['sqlite_entries']) == primary
    assert all(capture['sqlite_entries'][id] == native[id] for id in primary)
    groups = [{'source': ident, 'sense': sense['id'], 'index': i, 'original': group}
              for ident in sorted(primary) for sense in native[ident]['senses']
              for i, group in enumerate(sense['examples'])]
    assert len(groups) == 24 and groups == capture['all_original_groups']
    assert sum(len(native[id]['senses']) for id in primary) == 6
    lines, cursor = [], 0
    for group in groups:
        for i, text in enumerate(group['original']):
            lines.append((group['source'], str(group['sense']), group['index'], i, text, cursor))
            cursor += len(text) + 1
    assert '\n'.join(line[4] for line in lines) + '\n' == capture['input']
    for form, (_, _, ids) in FORMS.items():
        atom = catalog['-' + form]
        assert atom['label'] == 'Although / but (connective)'
        assert [s['id'] for s in atom['sources']] == [int(id.split(':')[1]) for id in ids]
        for source in atom['sources']:
            assert source['headword'] == native['krdict:' + str(source['id'])]['headword']
    assert len(suite['cases']) == 42 and len({c['id'] for c in suite['cases']}) == 42
    judgments = [j for c in suite['cases'] for j in c['judgments']]
    assert sum(j['verdict'] == 'required' for j in judgments) == 32
    assert sum(j['verdict'] == 'forbidden' for j in judgments) == 10
    assert set(suite['sources']) == {str(id) for id in range(80321, 80327)}
    cases = {c['id']: c for c in suite['cases']}
    assert len(originals) == len(targets['targets']) == 24
    for original, target in zip(originals, targets['targets'], strict=True):
        assert original['source_occurrence'] == target
        c = cases[original['id']]
        assert c['surface'] == original['surface'] == target['surface']
        assert c['judgments'][0]['verdict'] == 'required'
        assert all(c['judgments'][0][k] == v for k, v in original['expected'].items())
        assert 'krdict:' + c['judgments'][0]['source'] == target['source']
    expected_modes = {(encoding, mode) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']}
    assert {(r['encoding'], r['mode']) for r in capture['runs']} == expected_modes
    assert {(r['encoding'], r['mode']) for r in replay['runs']} == expected_modes
    assert len(capture['runs']) == len(replay['runs']) == 6 and replay['inputs_unchanged']
    additions, owners, rows_by_run = [], set(), {}
    for run in replay['runs']:
        key = (run['encoding'], run['mode'])
        oldrun = next(r for r in capture['runs'] if (r['encoding'], r['mode']) == key)
        text = unicodedata.normalize(run['encoding'], capture['input'])
        assert sha(text.encode()) == run['input_sha256'] == oldrun['input_sha256']
        assert sha(oldrun['jsonl'].encode()) == oldrun['sha256'] == run['before_sha256']
        assert sha(run['jsonl'].encode()) == run['after_sha256']
        assert run['exit_code'] == 0 and run['all_old_paths_order_assessments_and_native_preserved'] is True
        before = list(map(json.loads, oldrun['jsonl'].splitlines()))
        after = list(map(json.loads, run['jsonl'].splitlines()))
        assert len(before) == len(after) == run['frames'] == 506
        rows_by_run[key] = after
        for index, (old, now) in enumerate(zip(before, after, strict=True)):
            assert {k:v for k,v in old.items() if k not in ['analysis', 'dictionary']} == {k:v for k,v in now.items() if k not in ['analysis', 'dictionary']}
            assert now['surface'] == text.encode()[now['span']['start']:now['span']['end']].decode()
            if old['analysis'] is None:
                assert old == now
                continue
            assert old['analysis']['normalized'] == now['analysis']['normalized']
            oa, na = old['analysis']['analyses'], now['analysis']['analyses']
            assert [a for a in na if a in oa] == oa
            od, nd = old['dictionary'], now['dictionary']
            assert od['source'] == nd['source'] and od['fingerprint'] == nd['fingerprint']
            assert len(od['readings']) == len(oa) and len(nd['readings']) == len(na)
            for a, assessment in zip(oa, od['readings'], strict=True):
                assert nd['readings'][na.index(a)] == assessment
            for match in od['lemmas']:
                assert match in nd['lemmas']
            for n, a in enumerate(na):
                if a in oa:
                    continue
                inverse, _ = split_parent(a)
                assert inverse in oa, (now['surface'], 'missing exact old particle parent')
                assessment = nd['readings'][n]
                for slot in assessment['lemmas']:
                    owners.update(e['id'] for e in slot['entries'])
                additions.append({'encoding': run['encoding'], 'mode': run['mode'], 'frame_index': index,
                                  'surface': now['surface'], 'span': now['span'], 'analysis': a,
                                  'assessment': assessment, 'contextual_verdict': 'unjudged', 'independent_review': 'pending'})
    assert len(additions) == 270 and additions == replay['additions']
    assert sorted(owners) == replay['matched_native_owner_ids'] and len(owners) == 56 and owners <= native.keys()
    observations = []
    for c in originals:
        occurrence = c['source_occurrence']
        line = next(l for l in lines if l[:4] == (occurrence['source'], str(occurrence['sense']), occurrence['group'], occurrence['text_index']))
        a, b = occurrence['character_span']
        assert line[4][a:b] == c['surface']
        for run in replay['runs']:
            encoding, mode = run['encoding'], run['mode']
            start = len(unicodedata.normalize(encoding, capture['input'][:line[5]+a]).encode())
            end = len(unicodedata.normalize(encoding, capture['input'][:line[5]+b]).encode())
            frame = next(r for r in rows_by_run[(encoding, mode)] if r['span'] == {'start': start, 'end': end})
            assert frame['surface'] == unicodedata.normalize(encoding, c['surface'])
            indexes = [i for i,p in enumerate(frame['analysis']['analyses']) if matches(p,c['expected'])]
            assert indexes
            status = 'unknown' if c['id'] == 'declarative-contrast-original-80322-3' else 'compatible'
            assert all(frame['dictionary']['readings'][i]['status'] == status for i in indexes)
            assert any('particle.concessive' in p['rules'] for p in frame['analysis']['analyses'])
            observations.append({'case':c['id'], 'source_occurrence':occurrence, 'encoding':encoding, 'mode':mode,
                                 'byte_span':[start,end], 'matching_whole_connective_paths':[frame['analysis']['analyses'][i] for i in indexes],
                                 'matching_native_assessments':[frame['dictionary']['readings'][i] for i in indexes],
                                 'expected_native_status':status, 'older_particle_alternatives_preserved':True,
                                 'contextual_verdict':'unjudged', 'independent_review':'pending'})
    assert len(observations) == 144 and observations == target_audit['required_source_occurrence_observations']
    assert target_audit['source_groups'] == 24 and target_audit['streams'] == 6 and target_audit['frames_per_stream'] == 506
    return {'native':115, 'groups':24, 'cases':42, 'frames':3036, 'unjudged_additions':270, 'exact_occurrence_observations':144}


def inspect_captures():
    fixtures = ROOT / 'tests/fixtures'
    replay_path = ROOT / 'docs/declarative-contrast-prototype-source-replay.json.gz'
    target_audit = read(ROOT / 'docs/declarative-contrast-prototype-source-target-audit.json.gz')
    assert target_audit['source_replay_sha256'] == sha(replay_path.read_bytes())
    targets = read(ROOT / 'docs/declarative-contrast-target-observations.json')
    capture_path = ROOT / 'docs/declarative-contrast-source-discovery.json.gz'
    assert targets['source_capture_sha256'] == sha(capture_path.read_bytes())
    return verify_sources(read(capture_path), read(ROOT / 'docs/declarative-contrast-broad-owner-preparation.json.gz'),
                          targets, read(fixtures / 'declarative-contrast-validity.json'),
                          read(fixtures / 'declarative-contrast-original-cases.json'),
                          read(ROOT / 'web/src/grammar-labels.json'),
                          read(replay_path), target_audit)


if __name__ == '__main__':
    print('Verified complete contrast source replay:', inspect_captures())
