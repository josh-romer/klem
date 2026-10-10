"""Audit independent novel targets against original text, Native fields and CLI bytes."""
import gzip
import hashlib
import itertools
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get('KLEM_NOVEL_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / 'tools'))
from native_lmf import entry

sha = lambda raw: hashlib.sha256(raw).hexdigest()

def inputs():
    def read(relative):
        raw = (ROOT / relative).read_bytes()
        return json.loads(gzip.decompress(raw) if relative.endswith('.gz') else raw)
    return {
        'original': read('docs/reported-deoni-broad-inputs.json.gz')['sources']['/home/josh/projects/klem/data/books/mujeong.txt'],
        'author': read('tests/fixtures/conjectural-additive-novel-contexts.json'),
        'fixture_raw': (ROOT / 'tests/fixtures/conjectural-additive-novel-validity.json').read_bytes(),
        'native_raw': (ROOT / 'tests/fixtures/conjectural-additive-novel-native.json').read_bytes(),
        'native_entries_raw': (ROOT / 'tests/fixtures/conjectural-additive-novel-native-entries.json').read_bytes(),
        'closure': read('docs/conjectural-additive-novel-context-native-closure.json.gz'),
        'capture': read('docs/conjectural-additive-novel-context-prototype-regressions-retry1.json.gz'),
        'queue': read('docs/inventory-review-queue.json'),
    }

def matches(path, target):
    return ([lemma['text'] for lemma in path['lemmas']] == target['lemmas']
            and [lemma['kind'] for lemma in path['lemmas']] == target['lemma_kinds']
            and [morph['form'] for morph in path['morphemes']] == target['morphemes']
            and [morph['kind'] for morph in path['morphemes']] == target['morpheme_kinds']
            and set(target['required_rules']) <= set(path['rules']))

def inspect(v):
    assert sha(v['fixture_raw']) == 'b0b3a87c59895f1a056ccb3525ae9a3e4b9e0536edb6729af8c8574f67341732', 'independent novel targets unchanged'
    assert sha(v['native_raw']) == '4a64a44b9aca5fe7b64ef4a1c1c3dff2a2c7bce0df39e35d58d2bf6a75f38a55', 'complete original Native fixture unchanged'
    assert sha(v['native_entries_raw']) == '5efe314f9193b4c4d8c2e8202534a66087c759ed35564fe7463abc66b10135c7', 'complete Native projections unchanged'
    raw = v['original']['text'].encode()
    assert sha(raw) == v['original']['sha256'] == '50a02d2f5f11f148497f2f00c782733ee3f8c2e331e1c0e5f74e3b7c8b0ca4dc', 'every original novel byte'
    author, closure, capture = v['author'], v['closure'], v['capture']
    suite = json.loads(v['fixture_raw'])
    assert author['original_novel_sha256'] == sha(raw) and author['fixture_sha256'] == sha(v['fixture_raw']), 'original context/target provenance'
    spans = [(len(v['original']['text'][:m.start()].encode()), len(v['original']['text'][:m.end()].encode()), m.group())
             for m in re.finditer(r'[가-힣]*(?:으려니와|려니와)', v['original']['text'])]
    assert len(spans) == len(author['items']) == len(suite['cases']) == 15, 'all fifteen literal original occurrences'
    for item, case, (start, end, surface) in zip(author['items'], suite['cases'], spans, strict=True):
        line_start = raw.rfind(b'\n', 0, start) + 1
        line_end = raw.find(b'\n', end)
        if line_end < 0: line_end = len(raw)
        assert item['span'] == {'start': start, 'end': end} and item['surface'] == surface, 'exact original target spans'
        assert item['line_byte_start'] == line_start and item['line_byte_end'] == line_end and item['complete_original_line'] == raw[line_start:line_end].decode(), 'complete original line retained'
        assert item['id'] == case['id'] == f'conjectural-additive-novel-{start}-{end}' and case['surface'] == surface, 'stable independent occurrence identities'
        assert item['typed_targets'] == case['judgments'], 'authoring targets equal original independent judgments'
    assert sum(len(case['judgments']) for case in suite['cases']) == 16 and all(j['verdict'] == 'required' for case in suite['cases'] for j in case['judgments']), 'only sixteen required targets; no alternative forbidden'
    original_native = json.loads(v['native_raw'])['LexicalResource']['Lexicon']['LexicalEntry']
    projected = json.loads(v['native_entries_raw'])
    assert len(original_native) == len(projected) == closure['owners'] == 29, 'every original Native homonym retained'
    assert {'krdict:' + owner['val']: owner for owner in original_native} == closure['original_native_entries'], 'exact original Native fields'
    assert {entry(owner)['id']: entry(owner) for owner in original_native} == projected == closure['complete_imported_entries'], 'every complete Native projection'
    manifest = json.loads(v['queue']['dictionary_metadata']['manifest'])
    assert {name: export['sha256'] for name, export in closure['original_exports'].items()} == {item['name']: item['sha256'] for item in manifest['files']}, 'all eleven original exports bound to pinned snapshot'
    assert closure['original_database_sha256'] == '23d993696c55d0e54660e4a2b23dac7d68525fecb1fdc44341e1f2b3f75dead5', 'original pinned database'
    assert capture['state'] == 'passed' and capture['inputs_unchanged'] and not capture['missing'] and capture['native_import_exact_fields'] and capture['native_owners'] == 29, 'actual successful original-Native CLI capture'
    commands = capture['commands']
    assert len(commands) == 54 and all(command['exit_code'] == 0 and not command['stderr'] for command in commands), 'all actual import/entry/stream commands succeeded'
    cli, _, _, native_path, database, *_ = commands[0]['command']
    assert cli in capture['frozen_inputs'] and native_path in capture['frozen_inputs'] and database in capture['frozen_inputs'], 'actual frozen executable and imported Native inputs'
    assert capture['frozen_inputs'][native_path] == sha(v['native_raw']), 'import uses exact original Native fixture'
    assert [command['command'] for command in commands[1:30]] == [[cli, 'dict', 'entry', database, ident] for ident in projected], 'every original owner actually retrieved'
    combinations = list(itertools.product(['complete-original-novel-lines', 'standalone-novel-targets'], ['NFC', 'NFD'], ['raw', 'headword', 'compatible'], [0, 4096]))
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in capture['runs']] == combinations, 'complete twenty-four policy/Unicode/cache streams'
    outputs = {}
    total = checks = 0
    for run, command in zip(capture['runs'], commands[30:], strict=True):
        encoding, family, mode, cache = run['encoding'], run['family'], run['mode'], run['cache_bytes']
        groups = [unicodedata.normalize(encoding, item['complete_original_line'] if family.startswith('complete') else item['surface']) for item in author['items']]
        original = '\n'.join(groups).encode()
        assert run['input'] == original.decode() and run['input_sha256'] == sha(original), 'complete original encoded contexts'
        flags = ['--dict-only'] if mode == 'headword' else ['--dict-compatible'] if mode == 'compatible' else []
        expected_command = [cli, 'text', '-', '--dictionary', database, *flags, '--cache-bytes', str(cache)]
        assert run['command'] == command['command'] == expected_command and run['exit_code'] == 0, 'actual correct filter/cache command'
        assert sha(run['jsonl'].encode()) == run['jsonl_sha256'] == command['stdout_sha256'], 'complete actual output bytes'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == run['records'] == (3975 if family.startswith('complete') else 29), 'all complete output frames'
        cursor = 0
        for row in rows:
            assert row['span']['start'] == cursor, 'continuous original byte coverage'
            cursor = row['span']['end']
            assert original[row['span']['start']:cursor].decode() == row['surface'], 'original UTF8 token ownership'
            if row['analysis']:
                assert len(row['analysis']['analyses']) == len(row['dictionary']['readings']), 'every candidate has its own dictionary reading'
                for lemma in row['dictionary']['lemmas']:
                    for owner in lemma['entries']:
                        assert owner['id'] in projected and all(owner[key] == projected[owner['id']][key] for key in ['headword', 'homonym', 'pos']), 'real original Native lemma owner'
        assert cursor == len(original) and run['original_bytes_conserved'], 'complete original bytes conserved'
        offset = 0
        assert len(run['observations']) == 15, 'every authored occurrence observed'
        for group, case, observation in zip(groups, suite['cases'], run['observations'], strict=True):
            target = unicodedata.normalize(encoding, case['surface'])
            assert group.count(target) == 1
            position = offset + group.encode().index(target.encode())
            offset += len(group.encode()) + 1
            index, row = next((i, row) for i, row in enumerate(rows) if row['span']['start'] == position)
            assert observation['id'] == case['id'] and observation['record_index'] == index, 'exact complete-context target record'
            assert row['surface'] == target, 'exact encoded target surface'
            expected = []
            for judgment in case['judgments']:
                indices = [i for i, path in enumerate(row['analysis']['analyses']) if matches(path, judgment)]
                assert indices, 'every independently authored typed target recovered'
                if mode == 'compatible':
                    assert all(row['dictionary']['readings'][i]['status'] != 'incompatible' for i in indices), 'compatible filter preserves finite original lexical licenses'
                expected.append({'judgment_id': judgment['id'], 'typed_path_indices': indices})
                checks += 1
            assert observation['judgments'] == expected, 'exact original independent target matches'
        key = (family, encoding, mode)
        if key in outputs: assert outputs[key] == run['jsonl'], 'complete cache output parity'
        outputs[key] = run['jsonl']
        total += len(rows)
    assert total == 48048 and checks == 384, 'complete original contexts and typed target scope'
    return {'state': 'complete-independent-original-novel-audit-passed', 'occurrences': 15, 'typed_requirements': 16, 'native_owners': 29, 'streams': 24, 'frames': total, 'typed_occurrence_checks': checks, 'other_paths_and_senses': 'unjudged', 'independent_Korean_review': 'pending'}

if __name__ == '__main__':
    print(json.dumps(inspect(inputs()), ensure_ascii=False, indent=2))
