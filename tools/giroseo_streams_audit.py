"""Independently check complete source streams and all original Native owners."""
import gzip, hashlib, json, unicodedata
from pathlib import Path
from native_lmf import entry
ROOT = Path(__file__).resolve().parents[1]
sha = lambda b: hashlib.sha256(b).hexdigest()
def read(p):
    raw = Path(p).read_bytes()
    return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def inspect(prepared, streams, closure, native, entries):
    assert streams['state'] == 'passed' and streams['inputs_unchanged'], 'terminal source capture'
    assert sha(streams['producer']['text'].encode()) == streams['producer']['sha256'], 'source producer digest'
    assert streams['complete_original_groups'] == prepared['complete_groups'], 'original source groups'
    assert streams['complete_source_text'] == prepared['complete_source_text'], 'original source text'
    modes = [(e, m, c) for e in ['NFC', 'NFD'] for m in ['raw', 'headword', 'compatible'] for c in [0, 8388608]]
    assert [(r['encoding'], r['mode'], r['cache_bytes']) for r in streams['runs']] == modes, 'all twelve source modes'
    additions = []; cache = {}; frames = 0
    for run in streams['runs']:
        encoding, mode, capacity = run['encoding'], run['mode'], run['cache_bytes']
        text = unicodedata.normalize(encoding, prepared['complete_source_text']); raw = text.encode()
        assert run['input_text'] == text and run['input_sha256'] == sha(raw), 'exact Unicode source input'
        captures = run['captures']; assert len(captures) == 2, 'before and after captures'
        for capture in captures:
            assert capture['exit_code'] == 0 and sha(capture['jsonl'].encode()) == capture['stdout_sha256'], 'actual capture digest'
            rows = [json.loads(line) for line in capture['jsonl'].splitlines()]
            assert rows == capture['records'] and len(rows) == 167, 'complete actual source frames'
            command = capture['command']; flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[mode]
            assert command[0] in streams['frozen_inputs'] and command[1:] == ['text', '-', '--dictionary', command[4], '--cache-bytes', str(capacity), *flags] and command[4] in streams['frozen_inputs'], 'actual command identity'
            cursor = 0
            for row in rows:
                start, end = row['span']['start'], row['span']['end']
                assert start == cursor and end >= start and raw[start:end].decode() == row['surface'], 'original byte conservation'
                cursor = end
            assert cursor == len(raw), 'complete original byte coverage'
        before, after = [c['records'] for c in captures]; derived = []
        for ordinal, (old, new) in enumerate(zip(before, after, strict=True), 1):
            assert {k:v for k,v in old.items() if k not in ['analysis','dictionary']} == {k:v for k,v in new.items() if k not in ['analysis','dictionary']}, 'unchanged original frame identity'
            if old.get('analysis') is None:
                assert old == new, 'unchanged nonanalysis frame'; continue
            oldpaths, newpaths = old['analysis']['analyses'], new['analysis']['analyses']
            assert [p for p in newpaths if p in oldpaths] == oldpaths, 'all prior paths and order'
            assert all(v in new['dictionary']['lemmas'] for v in old['dictionary']['lemmas']), 'all prior lexical owners'
            for path in oldpaths:
                assert old['dictionary']['readings'][oldpaths.index(path)] == new['dictionary']['readings'][newpaths.index(path)], 'all prior Native assessments'
            for path in newpaths:
                if path in oldpaths: continue
                assert 'ending.concessive_giroseo' in path['rules'], 'new path provenance'
                span = new['span']; left = raw.rfind(b'\n', 0, span['start']) + 1; right = raw.find(b'\n', span['end'])
                value = {'encoding':encoding, 'mode':mode, 'cache_bytes':capacity, 'record':ordinal, 'surface':new['surface'], 'span':span, 'complete_original_line':raw[left:right if right >= 0 else len(raw)].decode(), 'analysis':path, 'dictionary_assessment':new['dictionary']['readings'][newpaths.index(path)], 'contextual_verdict':'unjudged', 'independent_review':'pending'}
                ident = 'giroseo-source-stream-' + sha(json.dumps(value,ensure_ascii=False,sort_keys=True).encode())[:24]
                derived.append({'id':ident, **value})
        assert derived == run['individual_additions'], 'independently derived individual additions'
        additions.extend(derived); frames += len(after)
        hashes = [c['stdout_sha256'] for c in captures]
        if capacity == 0: cache[(encoding,mode)] = hashes
        else: assert hashes == cache[(encoding,mode)], 'cache parity'
    assert additions == streams['individual_additions'] and len(additions) == 132, 'complete individual source accounting'
    assert closure['source_streams_sha256'] == sha((ROOT/'docs/giroseo-source-streams.json.gz').read_bytes()), 'Native closure source binding'
    assert sha(closure['producer']['text'].encode()) == closure['producer']['sha256'], 'closure producer digest'
    originals = {entry(v)['id']:v for v in native['LexicalResource']['Lexicon']['LexicalEntry']}
    assert originals == closure['original_native_entries'], 'lossless complete Native originals'
    assert sha(json.dumps(originals,ensure_ascii=False,sort_keys=True).encode()) == 'b8b5e838b00c7c8a917fbaf03bd5cadf6484bbcd4ffb7c367f8e39989b924db1', 'pinned original Native fields'
    assert {i:entry(v) for i,v in originals.items()} == entries == closure['entries'] and len(entries) == 34, 'complete Native projection'
    assert all(originals[i] == v for i,v in prepared['original_native_entries'].items()), 'all initial Native owners'
    needed = set(prepared['complete_imported_entries']); ownership = []
    for run in streams['runs']:
        rows = run['captures'][1]['records']
        for observation in run['individual_additions']:
            row = rows[observation['record']-1]
            owners = [next(v for v in row['dictionary']['lemmas'] if v['lemma'] == lemma) for lemma in observation['analysis']['lemmas']]
            needed.update(e['id'] for owner in owners for e in owner['entries'])
            ownership.append({'id':observation['id'], 'dictionary_owners':owners})
            for owner in owners:
                for lexical in owner['entries']:
                    full = entries[lexical['id']]
                    assert all(lexical[k] == full[k] for k in ['id','headword','homonym','pos']), 'exact observed Native ownership'
    assert needed == set(entries) and ownership == closure['individual_owner_observations'], 'complete individual Native ownership'
    extra = {i for export in closure['additional_exports'].values() for i in export['ids']}
    assert extra == needed - set(prepared['complete_imported_entries']) == {'krdict:66820','krdict:66821'}, 'complete additional homonym exports'
    return {'source_streams':12,'frames':frames,'individual_additions':len(additions),'native_entries':len(entries),'contextual_and_independent_review':'pending'}
def inputs():
    return [read(ROOT/p) for p in ['docs/giroseo-source-preparation.json.gz','docs/giroseo-source-streams.json.gz','docs/giroseo-native-closure.json.gz','tests/fixtures/giroseo-additional-native.json','tests/fixtures/giroseo-additional-native-entries.json']]
if __name__ == '__main__': print(inspect(*inputs()))
