"""Verify complete source groups, every captured frame and exact individual judgments."""
import gzip, hashlib, importlib.util, json, sys, os
from pathlib import Path

ROOT = Path(os.environ.get('KLEM_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'tools'))
from native_lmf import entry, verify_native_lmf

read = lambda p: json.loads(gzip.decompress(Path(p).read_bytes()))
sha = lambda raw: hashlib.sha256(raw).hexdigest()
prepared = read(ROOT / 'docs/declarative-dao-preparation-complete.json.gz')
closure = read(ROOT / 'docs/declarative-dao-native-revision2.json.gz')
runtime = read(ROOT / 'docs/declarative-dao-runtime.json.gz')
suite = json.loads((ROOT / 'tests/fixtures/declarative-dao-validity.json').read_text())

def inspect(prepared, closure, runtime, suite):
    native = closure['complete_native_entries']
    assert len(native) == 378 and set(closure['original_lmf']) == set(native)
    verify_native_lmf(closure['english_projection'], native)
    for ident, value in closure['original_lmf'].items():
        assert entry(value) == native[ident]
    expected = []
    for ident, value in prepared['complete_native_entries'].items():
        assert native[ident] == value and closure['original_lmf'][ident] == prepared['original_lmf'][ident]
        for sense in value['senses']:
            for ordinal, group in enumerate(sense['examples'], 1):
                expected.append({'entry_id': ident, 'sense_id': sense['id'], 'group': ordinal,
                                 'complete_original_examples': group, 'judgment': 'unreviewed'})
    assert expected == prepared['complete_groups'] == closure['complete_groups'] and len(expected) == 26
    assert set(prepared['inventory_entries']) == {'krdict:77931', 'krdict:79421', 'krdict:79419'}
    assert set(prepared['expression_entries']) == {'krdict:88935', 'krdict:88936', 'krdict:88937'}
    text = ''.join('\n'.join(g['complete_original_examples']) + '\n' for g in expected)
    assert text == prepared['complete_source_text']
    assert runtime['state'] == 'draft-complete-source-runtime-passed' and runtime['inputs_unchanged']
    assert len(runtime['runs']) == 6
    assert {(r['mode'], r['cache_bytes']) for r in runtime['runs']} == {
        (m, c) for m in ['raw', 'headword', 'compatible'] for c in [0, 4096]}
    expected_changes, observed = [], {}
    for run in runtime['runs']:
        assert run['exit_code'] == 0 and len(run['records']) == 417
        cursor = 0
        before = prepared['baseline_runs'][run['mode']]['records']
        assert len(before) == len(run['records'])
        for index, (old, record) in enumerate(zip(before, run['records'], strict=True)):
            assert record['span']['start'] == cursor
            assert text.encode()[cursor:record['span']['end']].decode() == record['surface']
            cursor = record['span']['end']
            assert (old['span'], old['kind'], old['surface']) == (record['span'], record['kind'], record['surface'])
            if old['analysis'] is None:
                assert old == record
                continue
            old_paths, paths = old['analysis']['analyses'], record['analysis']['analyses']
            assert [a for a in paths if a in old_paths] == old_paths
            for path in old_paths:
                oi, ni = old_paths.index(path), paths.index(path)
                assert old['dictionary']['readings'][oi] == record['dictionary']['readings'][ni]
                for lemma in path['lemmas']:
                    lookup = lambda r: next(m for m in r['dictionary']['lemmas'] if m['lemma'] == lemma)
                    assert lookup(old) == lookup(record)
            for matches in record['dictionary']['lemmas']:
                for e in matches['entries']:
                    assert e['id'] in native
                    assert (e['headword'], e['pos']) == (native[e['id']]['headword'], native[e['id']]['pos'])
            additions = [a for a in paths if a not in old_paths]
            assert all('ending.declarative_dao' in a['rules'] for a in additions)
            if additions and run['cache_bytes'] == 0:
                expected_changes.append({'mode': run['mode'], 'record': index, 'surface': record['surface'],
                                         'span': record['span'], 'before': old, 'after': record,
                                         'additions': additions, 'contextual_verdict': 'unjudged'})
        assert cursor == len(text.encode())
        raw = b''.join((json.dumps(r, ensure_ascii=False, separators=(',', ':')) + '\n').encode() for r in run['records'])
        assert sha(raw) == run['stdout_sha256']
        observed.setdefault(run['mode'], []).append(run['stdout_sha256'])
    assert all(len(set(hashes)) == 1 for hashes in observed.values())
    assert runtime['changes'] == expected_changes
    assert len(suite['cases']) == 36 and len({c['id'] for c in suite['cases']}) == 36
    indexed = {c['id']: c for c in suite['cases']}
    for proposal in prepared['proposals']:
        case = indexed[proposal['id']]
        assert case['surface'] == proposal['surface'] and len(case['judgments']) == 1
        judgment = case['judgments'][0]
        assert judgment['lemmas'] == [proposal['proposed_lemma']] and judgment['verdict'] == 'required'
        assert judgment['source'] == 'dao-' + proposal['source_entry'].split(':')[1]
        assert suite['sources'][judgment['source']] == native[proposal['source_entry']]['url']
        expected_kind = '다오' if proposal['source_entry'] in ['krdict:79419', 'krdict:88937'] else '는다오'
        assert judgment['morphemes'][-1] == expected_kind and judgment['morpheme_kinds'][-1] == 'ending'
        assert judgment['required_rules'] == ['ending.declarative_dao']
    return {'original_groups': 26, 'source_identities': 6, 'complete_native_entries': 378,
            'streams': 6, 'frames': 2502, 'individual_cases': 36,
            'contextual_review_complete': False, 'independent_review_complete': False}

if __name__ == '__main__':
    print(inspect(prepared, closure, runtime, suite))
