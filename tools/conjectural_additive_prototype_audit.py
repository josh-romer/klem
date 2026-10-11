"""Audit omitted-copula source/novel/Native/browser evidence without changing the initial capture."""
import argparse
import gzip
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import conjectural_additive_source_audit as original

FIXTURE_SHA = '669e3f979cbb6156dfa2444e67272b4cdd24151a276976b6c5cbe9b137acbb06'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def inputs(directory=None):
    docs = ROOT / 'docs'
    phase1 = lambda name: read(docs / ('conjectural-additive-phase1-' + name + ('' if name.endswith('.gz') else '.gz')))
    phase2 = lambda name: read(docs / ('conjectural-additive-phase2-' + name + ('' if name.endswith('.gz') else '.gz')))
    return {
        'source': read(docs / 'conjectural-additive-source-preparation.json.gz'),
        'before': read(docs / 'conjectural-additive-before-streams.json.gz'),
        'native': read(docs / 'conjectural-additive-original-native-closure.json.gz'),
        'authoring': phase1('typed-path-preparation.json'),
        'after': phase2('copula-source-streams.json.gz'),
        'queue': phase2('copula-source-candidate-review-queue.json'),
        'browser': phase2('conjectural-additive-copula-closure-browser.json'),
        'runtime': phase2('conjectural-additive-copula-closure-browser-runtime.json'),
        'rust_log': gzip.decompress((docs / 'conjectural-additive-phase2-copula-native-focused-rust.log.gz').read_bytes()).decode(),
        'checks': phase2('copula-checks.json'),
        'phase1': phase1('after-streams.json.gz'),
        'copula_author': phase2('copula-independent-authoring.json'),
        'copula_fixture': read(ROOT / 'tests/fixtures/conjectural-additive-copula-validity.json'),
        'copula_native': phase2('copula-native-closure.json.gz'),
        'novel': phase2('copula-cli-streams.json'),
        'original_broad_inputs': read(docs / 'reported-deoni-broad-inputs.json.gz'),
    }

def matches(path, judgment):
    return ([lemma['text'] for lemma in path['lemmas']] == judgment['lemmas']
            and [lemma['kind'] for lemma in path['lemmas']] == judgment['lemma_kinds']
            and [morph['form'] for morph in path['morphemes']] == judgment['morphemes']
            and [morph['kind'] for morph in path['morphemes']] == judgment['morpheme_kinds']
            and all(rule in path['rules'] for rule in judgment['required_rules']))

def inspect_source_and_browser(values):
    source, before, native = (values[key] for key in ['source', 'before', 'native'])
    base = original.inspect(source, before, native)
    assert base['groups'] == 16 and base['proposed_lemma_groups_found'] == 0, 'complete unchanged original preflight'
    author, after, queue = (values[key] for key in ['authoring', 'after', 'queue'])
    assert author['state'] == 'typed-judgments-authored-before-implementation-probe', 'independent preimplementation authoring'
    assert author['fixture_sha256'] == FIXTURE_SHA, 'original authored fixture identity'
    fixture = after['typed_fixture']
    assert sha((json.dumps(fixture, ensure_ascii=False, indent=2) + '\n').encode()) == FIXTURE_SHA, 'every independently authored judgment unchanged'
    assert len(fixture['cases']) == 35, 'all source and constructed boundary cases'
    cases = fixture['cases'][:16]
    assert [(case['surface'], case['judgments'][0]['lemmas']) for case in cases] == original.TARGETS, 'all independent source lexical targets'
    assert [case['id'] for case in cases] == [group['id'] for group in source['complete_groups']], 'original context IDs'
    for record in [author, after, queue, values['checks']]:
        assert sha(record['producer']['text'].encode()) == record['producer']['sha256'], 'producer identity'
    assert after['state'] == 'complete-after-observation-passed' and after['inputs_unchanged'], 'terminal unchanged after capture'
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in after['runs']] == [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in before['runs']], 'all original24Unicode/filter/cache streams'
    preserved = additions = 0
    canonical_queue = []
    cached = {}
    for old_run, run in zip(before['runs'], after['runs'], strict=True):
        original_groups = ['\n'.join(g['complete_original_group']) for g in source['complete_groups']] if run['family'] == 'complete-original-source' else [case['surface'] for case in cases]
        text = ('\n' if run['family'] == 'complete-original-source' else ' ').join(original_groups)
        raw = unicodedata.normalize(run['encoding'], text).encode()
        assert run['exit_code'] == 0 and run['original_bytes_conserved'], 'successful original byte capture'
        assert run['input_sha256'] == sha(raw), 'complete unchanged source input'
        assert run['jsonl_sha256'] == sha(run['jsonl'].encode()), 'complete actual JSONL capture'
        command = run['command']
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert command[0] in after['frozen_inputs'] and command[1:4] == ['text', '-', '--dictionary'] and command[4] in after['frozen_inputs'] and command[5:] == [*flags, '--cache-bytes', str(run['cache_bytes'])], 'actual filter/cache command'
        old_rows = [json.loads(line) for line in old_run['jsonl'].splitlines()]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == len(old_rows) == run['records'], 'complete original frame coverage'
        cursor = old_count = added_count = 0
        for old, row in zip(old_rows, rows, strict=True):
            assert {key: old[key] for key in ['surface', 'span', 'kind']} == {key: row[key] for key in ['surface', 'span', 'kind']}, 'original token identity'
            assert row['span']['start'] == cursor, 'continuous original byte ownership'
            cursor = row['span']['end']
            assert raw[row['span']['start']:cursor].decode() == row['surface'], 'every original UTF8 byte'
            old_paths = (old.get('analysis') or {}).get('analyses', [])
            paths = (row.get('analysis') or {}).get('analyses', [])
            assert all(path in paths for path in old_paths), 'every original candidate retained'
            new_only = [path for path in paths if path not in old_paths]
            assert all('ending.conjectural_additive' in path['rules'] for path in new_only), 'only new family candidate additions'
            old_count += len(old_paths)
            added_count += len(new_only)
        assert cursor == len(raw), 'complete byte stream'
        assert (old_count, added_count) == (run['original_paths_preserved'], run['new_family_paths']), 'exact preserved and added candidate counts'
        preserved += old_count
        additions += added_count
        observed = []
        offset = 0
        for ordinal, (group, case) in enumerate(zip(original_groups, cases, strict=True)):
            group_bytes = unicodedata.normalize(run['encoding'], group).encode()
            target = unicodedata.normalize(run['encoding'], case['surface']).encode()
            position = offset + group_bytes.index(target)
            offset += len(group_bytes) + 1
            index, row = next((i, r) for i, r in enumerate(rows) if r['span']['start'] == position)
            assert row['surface'].encode() == target, 'original occurrence position'
            paths = row['analysis']['analyses']
            indices = [i for i, path in enumerate(paths) if matches(path, case['judgments'][0])]
            assert indices, 'independent typed original path present'
            observed.append({'id': case['id'], 'record_index': index, 'typed_path_indices': indices})
            if (run['family'], run['encoding'], run['mode'], run['cache_bytes']) == ('complete-original-source', 'NFC', 'raw', 0):
                for path_index, path in enumerate(paths):
                    if path in old_rows[index]['analysis']['analyses']:
                        continue
                    digest = sha(json.dumps(path, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode())
                    covered = path_index in indices
                    canonical_queue.append({'id': case['id'] + '-candidate-' + digest,
                         'source_case_id': case['id'], 'source_group': source['complete_groups'][ordinal],
                         'surface': row['surface'], 'span': row['span'], 'record_index': index,
                         'analysis_index': path_index, 'analysis': path,
                         'dictionary_reading': row['dictionary']['readings'][path_index],
                         'coverage': 'covered-by-independent-required-path' if covered else 'unjudged-alternative',
                         'independent_judgment': case['judgments'][0] if covered else None,
                         'contextual_sense_verdict': 'unjudged'})
        assert observed == run['observed_typed_paths'], 'independently rederived typed path indices'
        key = (run['family'], run['encoding'], run['mode'])
        assert key not in cached or cached[key] == run['jsonl'], 'exact zero4096cache parity'
        cached[key] = run['jsonl']
    assert (preserved, additions) == (5576, 1024), 'complete actual source candidate totals'
    assert queue['state'] == 'complete-original-context-candidate-queue-preserved', 'candidate tracking state'
    assert queue['items'] == canonical_queue and len(canonical_queue) == 82, 'every original-context candidate and Native assessment tracked'
    assert queue['covered_paths'] == 16 and queue['unjudged_alternatives'] == 66, 'no automatic promotion of unjudged alternatives'
    checks = values['checks']
    assert 'test result: ok. 6 passed; 0 failed; 0 ignored;' in values['rust_log'], 'all six focused tests completed'
    assert 'test result: ok. 2 passed; 0 failed; 0 ignored;' in values['rust_log'], 'both copula focused tests completed'
    assert checks['state'] == 'passed' and checks['inputs_unchanged'] and all(run['exit_code'] == 0 for run in checks['runs']), 'actual focused format and Clippy completion'
    assert checks['runs'][0]['command'] == ['cargo', 'fmt', '--all', '--', '--check'], 'actual formatting check'
    assert checks['runs'][1]['command'][-3:] == ['--', '-D', 'warnings'], 'actual warnings-denied Clippy'
    browser, runtime = values['browser'], values['runtime']
    assert runtime['state'] == 'passed' and runtime['exit_code'] == 0 and runtime['inputs_unchanged'] and runtime['server_stopped'], 'actual browser completion and shutdown'
    assert not browser['errors'], 'no browser errors'
    positive = [case for case in fixture['cases'] + values['copula_fixture']['cases'] if case['judgments'][0]['verdict'] == 'required']
    assert len(positive) == 32 and len(browser['policyDecisions']) == len(browser['diagrams']) == 192, 'all browser source and boundary positives'
    assert [(d['encoding'], d['mode'], d['case_id']) for d in browser['policyDecisions']] == [(encoding, mode, case['id']) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for case in positive], 'every browser Unicode/filter decision'
    assert [(e['encoding'], e['mode']) for e in browser['exports']] == [(encoding, mode) for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']], 'all six actual browser exports'
    assert len(browser['responses']) == 2 and [r['encoding'] for r in browser['responses']] == ['NFC', 'NFD'], 'both actual API captures'
    for decision, diagram in zip(browser['policyDecisions'], browser['diagrams'], strict=True):
        case = next(c for c in positive if c['id'] == decision['case_id'])
        assert decision['allowed'] and str(decision['raw_analysis_index']) in decision['offered_indices'], 'actual authored path available in viewer'
        assert matches(decision['analysis'], case['judgments'][0]), 'exact typed browser candidate'
        api = next(r['api'] for r in browser['responses'] if r['encoding'] == decision['encoding'])
        index = decision['record_index']
        assert api['records'][index]['surface'] == unicodedata.normalize(decision['encoding'], case['surface']), 'actual API original word'
        assert api['records'][index]['analysis']['analyses'][decision['raw_analysis_index']] == decision['analysis'], 'actual API analysis index'
        exported = next(e for e in browser['exports'] if (e['encoding'], e['mode']) == (decision['encoding'], decision['mode']))
        assert decision['analysis'] in exported['records'][index]['analysis']['analyses'], 'actual exported selected path'
        heads = [head[:-1] if kind in ['predicate', 'auxiliary', 'copula'] and head.endswith('다') else head for head, kind in zip(case['judgments'][0]['lemmas'], case['judgments'][0]['lemma_kinds'], strict=True)]
        forms = case['judgments'][0]['morphemes']
        expected = [heads[0], *forms] if len(heads) == 1 else [heads[0], forms[0], heads[1], *forms[1:]] if case['judgments'][0]['lemma_kinds'][1] == 'auxiliary' else [*heads, *forms]
        if len(heads) == 1 and case['judgments'][0]['lemmas'][0].endswith('하다'):
            expected[1] = '여' + expected[1][1:] if expected[1].startswith('어') else '였' + expected[1][1:] if expected[1].startswith('었') else expected[1]
        assert diagram['analysis'] == decision['analysis'] and diagram['forms'] == expected, 'independent displayed component order'
        assert all(str(owner) in diagram['source_hint'] for owner in [86083, 86084]), 'both original ending source links'
    native_endpoints = {record['id']: record['entry'] for record in browser['nativeEntries']}
    all_native = dict(native['complete_imported_entries'])
    all_native.update(values['copula_native']['complete_imported_entries'])
    assert len(browser['nativeEntries']) == len(native_endpoints) == 37 and native_endpoints == all_native, 'every original Native endpoint field'
    return {'state': 'independent-prototype-audit-passed', 'original_groups': 16,
            'source_streams': 24, 'source_frames': 4080, 'typed_source_occurrences': 384,
            'preserved_candidate_occurrences': preserved, 'new_candidate_occurrences': additions,
            'canonical_source_candidates': 82, 'required_source_paths': 16, 'unjudged_source_alternatives': 66,
            'focused_rust': 8, 'browser_decisions': 192, 'browser_diagrams': 192,
            'browser_exports': 6, 'original_native_owners': 37, 'full_coverage_complete': False}

COPULA_FIXTURE_SHA = '5c585034c57c61fb665a68a6acf949477cca054d1fb219c587f2f67ac7cada15'
COPULA_AUTHOR_SHA = 'ba235594349332444bf35784e20eff9a44d2944cc4b0074fd6ee4f1e9144ba50'
NOVEL_SHA = '50a02d2f5f11f148497f2f00c782733ee3f8c2e331e1c0e5f74e3b7c8b0ca4dc'


def inspect(values):
    author, fixture = values['copula_author'], values['copula_fixture']
    encode = lambda value: (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    assert sha(encode(author)) == COPULA_AUTHOR_SHA, 'unchanged independently authored original novel target'
    assert sha(encode(fixture)) == COPULA_FIXTURE_SHA, 'unchanged six independently authored copula judgments'
    judgment = fixture['cases'][0]['judgments'][0]
    assert [author['typed_' + field] for field in ['lemmas', 'lemma_kinds', 'morphemes', 'morpheme_kinds']] == [judgment[field] for field in ['lemmas', 'lemma_kinds', 'morphemes', 'morpheme_kinds']], 'original typed nominal/copula ownership'
    assert author['required_rules'] == judgment['required_rules'], 'original omitted-copula rule'
    native = values['copula_native']
    assert native['state'] == 'complete-original-copula-native-closure-preserved', 'supplemental original Native state'
    expected = native['complete_imported_entries']
    identities = {'krdict:73276': ('학교', '0'), 'krdict:31670': ('학생', '0'),
                  'krdict:86083': ('-려니와', '0'), 'krdict:86084': ('-으려니와', '0'),
                  'krdict:92457': ('이다', '1'), 'krdict:86232': ('이다', '2'),
                  'krdict:86118': ('이다', '3'), 'krdict:70089': ('장래', '0')}
    assert native['owners'] == len(expected) == 8 and {key: (entry['headword'], entry['homonym']) for key, entry in expected.items()} == identities, 'all eight original supplemental Native identities'
    assert {key: original.entry(value) for key, value in native['original_native_entries'].items()} == expected, 'every supplemental Native projection field'
    assert {key: sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) for key, value in expected.items()} == {'krdict:73276': '84cad33ad2f15de5e93c669b5ea71996bb2e85d17f68347051a4f0d5c576b008', 'krdict:31670': '87aa0a447f96911b4e54306ba59b5c6b47d748fa9cc1f3332a40303b726fcae5', 'krdict:86083': '53e025f1777baaa6210d99fcef31db9d764bacdc929d2a69855de9d65fd28ff2', 'krdict:86084': '7af5bea878be4857ce61a9c12765ccaf7932cea0d37bc88ad744aafbeda03c86', 'krdict:92457': '95a989b11f29986ae5601e4ab67fc60666b8f3fa0b25483b1adb624c18004ae9', 'krdict:86232': 'f0d6180e19cf42559b952d483afd40d28330ff66226ef39695607f10ea2b73a3', 'krdict:86118': '9950a7975997030c9493abf691b47aff9afa860f71a935f98abb8427e93182c8', 'krdict:70089': '5249914c124b1599b6f4e241fae83642783bade786e373b932f98afed3ae471b'}, 'all original supplemental Native fields pinned'
    assert len(native['original_exports']) == 11 and {key for export in native['original_exports'].values() for key in export['ids']} == set(expected), 'all supplemental original Native exports'
    for key in set(expected) & set(values['native']['complete_imported_entries']):
        assert expected[key] == values['native']['complete_imported_entries'][key], 'overlapping original Native fields'
    assert author['source_dictionary_noun'] == 'krdict:70089' and author['source_dictionary_copula'] == 'krdict:86232' and expected['krdict:70089']['pos'] == '명사' and expected['krdict:86232']['pos'] == '조사', 'independent original novel dictionary owners'
    assert sha(native['producer']['text'].encode()) == native['producer']['sha256'], 'actual supplemental Native producer'
    result = inspect_source_and_browser(values)
    for prior, after in zip(values['phase1']['runs'], values['after']['runs'], strict=True):
        assert (prior['family'], prior['encoding'], prior['mode'], prior['cache_bytes']) == (after['family'], after['encoding'], after['mode'], after['cache_bytes']), 'all initial source streams retained'
        for old, new in zip(map(json.loads, prior['jsonl'].splitlines()), map(json.loads, after['jsonl'].splitlines()), strict=True):
            old_paths = (old.get('analysis') or {}).get('analyses', [])
            new_paths = (new.get('analysis') or {}).get('analyses', [])
            for index, path in enumerate(old_paths):
                assert path in new_paths, 'every initial prototype candidate retained'
                assert old['dictionary']['readings'][index] == new['dictionary']['readings'][new_paths.index(path)], 'every initial Native assessment retained'
    novel = values['novel']
    assert novel['state'] == 'original-novel-copula-cli-streams-passed' and novel['inputs_unchanged'], 'terminal frozen novel CLI capture'
    assert [(run['context'], run['encoding'], run['mode'], run['cache_bytes']) for run in novel['runs']] == [(context, encoding, mode, cache) for context in ['original-complete-line', 'target'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]], 'all original novel Unicode/filter/cache streams'
    observation = author['original_observation']
    original_bytes = values['original_broad_inputs']['sources'][author['source']]['text'].encode()
    assert sha(original_bytes) == author['source_sha256'] == NOVEL_SHA, 'unchanged complete original novel'
    original_line = observation['complete_original_line'].encode()
    line_start = observation['line_byte_start']
    assert original_bytes[line_start:line_start + len(original_line)] == original_line, 'complete original novel line'
    span = observation['before']['span']
    assert span == {'start': 535800, 'end': 535815} and original_bytes[span['start']:span['end']].decode() == fixture['cases'][0]['surface'], 'literal original novel occurrence'
    cached = {}
    for run in novel['runs']:
        text = observation['complete_original_line'] if run['context'] == 'original-complete-line' else fixture['cases'][0]['surface']
        raw = unicodedata.normalize(run['encoding'], text).encode()
        assert run['input_sha256'] == sha(raw) and run['jsonl_sha256'] == sha(run['jsonl'].encode()) and run['exit_code'] == 0, 'complete successful novel capture'
        command = run['command']
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert command[0] in novel['frozen_inputs'] and command[1:4] == ['text', '-', '--dictionary'] and command[4] in novel['frozen_inputs'] and command[5:] == [*flags, '--cache-bytes', str(run['cache_bytes'])], 'actual novel filter/cache command'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == run['records'], 'complete novel frame coverage'
        cursor = 0
        for row in rows:
            assert row['span']['start'] == cursor, 'novel byte continuity'
            cursor = row['span']['end']
            assert raw[row['span']['start']:cursor].decode() == row['surface'], 'every original novel byte'
        assert cursor == len(raw), 'complete novel byte stream'
        target = unicodedata.normalize(run['encoding'], fixture['cases'][0]['surface']).encode()
        position = raw.index(target)
        index, row = next((index, row) for index, row in enumerate(rows) if row['span']['start'] == position)
        paths = row['analysis']['analyses']
        indices = [index for index, path in enumerate(paths) if matches(path, judgment)]
        assert indices and index == run['record_index'] and indices == run['typed_path_indices'], 'independently rederived novel copula path indices'
        assert all(row['dictionary']['readings'][i]['status'] == 'compatible' for i in indices), 'correct Native novel nominal/copula owners'
        key = (run['context'], run['encoding'], run['mode'])
        assert key not in cached or cached[key] == run['jsonl'], 'exact novel zero4096cache parity'
        cached[key] = run['jsonl']
    for response in values['browser']['responses']:
        for case in values['after']['typed_fixture']['cases'] + fixture['cases']:
            if case['judgments'][0]['verdict'] != 'required':
                continue
            row = next(row for row in response['api']['records'] if row['surface'] == unicodedata.normalize(response['encoding'], case['surface']))
            judgment = case['judgments'][0]
            found = any(matches(path, judgment) for path in row['analysis']['analyses'])
            assert found == (judgment['verdict'] == 'required'), 'every captured browser required typed judgment'
    result.update(novel_streams=24, novel_frames=sum(run['records'] for run in novel['runs']),
                  supplemental_native_owners=8, copula_cases=6, copula_required=4, copula_forbidden=2)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(inspect(inputs(args.evidence_dir)), ensure_ascii=False, indent=2))
