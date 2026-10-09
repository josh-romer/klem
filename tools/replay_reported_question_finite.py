"""Bind installed source/name/title behavior to actual preserved prototype outcomes."""
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import argparse
parser = argparse.ArgumentParser(description=__doc__)
for name in ['package', 'baseline-cli', 'dictionary', 'output']:
    parser.add_argument('--' + name, type=Path, required=True)
args = parser.parse_args()
PACKAGE = args.package
OUT = args.output
PROTOTYPE = args.baseline_cli
DB = args.dictionary
SOURCE_PROOF = ROOT / 'docs/self-question-runtime-retry1.json.gz'
assert not OUT.exists()
package = json.loads(PACKAGE.read_bytes())
assert package['state'] == 'passed' and package['exit_code'] == 0
assert package['inputs_unchanged'] and package['head_unchanged'] and package['index_unchanged']
CLI = Path(next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))) / 'bin/klem'

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def capture(binary, text, flags):
    command = [str(binary), 'text', '-', '--dictionary', str(DB), *flags]
    job = subprocess.run(command, input=text.encode(), capture_output=True, check=True)
    assert not job.stderr
    rows = [json.loads(line) for line in job.stdout.splitlines()]
    cursor = 0
    for row in rows:
        assert row['span']['start'] == cursor
        cursor = row['span']['end']
        assert text.encode()[row['span']['start']:cursor].decode() == row['surface']
    assert cursor == len(text.encode())
    return {'command': command, 'rows': rows, 'stdout_sha256': hashlib.sha256(job.stdout).hexdigest(), 'exit_code': job.returncode}

frozen = {str(p): sha(p) for p in [PACKAGE, CLI, PROTOTYPE, DB, SOURCE_PROOF, Path(__file__)]}
source = json.loads(gzip.decompress(SOURCE_PROOF.read_bytes()))
prepared_path = ROOT / 'docs/self-question-source-preparation-retry1.json.gz'
frozen[str(prepared_path)] = sha(prepared_path)
text = json.loads(gzip.decompress(prepared_path.read_bytes()))['complete_source_text']
runs = []
for source_file, prepared_file, family in [
    ('self-question-runtime-retry1.json.gz', 'self-question-source-preparation-retry1.json.gz', 'self-question'),
    ('dapnikka-runtime.json.gz', 'dapnikka-source-preparation.json.gz', 'reported-question'),
]:
    source_path = ROOT / 'docs' / source_file
    prepared_path = ROOT / 'docs' / prepared_file
    for path in [source_path, prepared_path]:
        frozen[str(path)] = sha(path)
    source = json.loads(gzip.decompress(source_path.read_bytes()))
    text = json.loads(gzip.decompress(prepared_path.read_bytes()))['complete_source_text']
    for original in source['runs']:
        flags = ['--cache-bytes', str(original['cache_bytes'])]
        flags += ['--dict-only'] if original['mode'] == 'headword' else ['--dict-compatible'] if original['mode'] == 'compatible' else []
        actual = capture(CLI, unicodedata.normalize(original['encoding'], text), flags)
        assert actual['rows'] == original['records'][1], family + ': installed complete source stream differs'
        runs.append({'family': family, 'encoding': original['encoding'], 'mode': original['mode'], 'cache_bytes': original['cache_bytes'], 'actual': actual, 'exact_preserved_capture': True})
novel_path = ROOT / 'tests/fixtures/dapnikka-novel-case.json'
frozen[str(novel_path)] = sha(novel_path)
novel = json.loads(novel_path.read_bytes())
for encoding in ['NFC', 'NFD']:
    for cache in [0, 4096]:
        for mode, mode_flags in [('raw', []), ('headword', ['--dict-only']), ('compatible', ['--dict-compatible'])]:
            text = unicodedata.normalize(encoding, novel['complete_original_line'])
            flags = ['--cache-bytes', str(cache), *mode_flags]
            expected = capture(PROTOTYPE, text, flags)
            actual = capture(CLI, text, flags)
            assert actual['rows'] == expected['rows'], 'complete novel sentence preservation'
            word = next(r for r in actual['rows'] if unicodedata.normalize('NFC', r['surface']) == '말랍니까')
            assert any(a['lemmas'] == [{'text': '말다', 'kind': 'predicate'}] and a['morphemes'] == [{'form': '으랍니까', 'kind': 'ending'}] and 'ending.question_dapnikka' in a['rules'] for a in word['analysis']['analyses'])
            runs.append({'family': 'reported-question-novel', 'encoding': encoding, 'mode': mode, 'cache_bytes': cache, 'expected': expected, 'actual': actual})
for fixture, family, rule in [
    ('proper-name-spacing-cases.json', 'proper-name-possession', 'spacing.proper_name_title_possession'),
    ('named-title-spacing-cases.json', 'named-title', 'spacing.proper_name_title'),
]:
    path = ROOT / 'tests/fixtures' / fixture
    frozen[str(path)] = sha(path)
    cases = json.loads(path.read_bytes())['cases']
    for encoding in ['NFC', 'NFD']:
        sentence = '前🙂「' + ' '.join(unicodedata.normalize(encoding, case['surface']) for case in cases) + '」'
        for cache in [0, 4096]:
            for mode, mode_flags in [('raw', []), ('headword', ['--dict-only']), ('compatible', ['--dict-compatible'])]:
                for names in [False, True]:
                    flags = ['--suggest-spacing', '--cache-bytes', str(cache), *mode_flags, *(['--proper-names'] if names else [])]
                    expected = capture(PROTOTYPE, sentence, flags)
                    actual = capture(CLI, sentence, flags)
                    assert actual['rows'] == expected['rows'], 'installed final name/title behavior differs from current complete prototype'
                    words = [r for r in actual['rows'] if r['kind'] == 'word' and r['surface'] != '前']
                    assert len(words) == len(cases)
                    observations = []
                    for case, word in zip(cases, words, strict=True):
                        options = [h for h in word['spacing']['alternatives'] if h.get('rule') == rule]
                        required = case.get('required_spacing', case.get('spaced') if case.get('verdict') == 'required' else None)
                        if names and required:
                            option = next(h for h in options if unicodedata.normalize('NFC', h['spaced']) == required)
                            assert option['records'][0]['entry_witnesses'] == ['ud-ko-kaist:proper-name:park']
                        else:
                            assert not options
                        observations.append({'case_id': case['id'], 'original_surface': case['surface'], 'record': word, 'contextual_verdict': 'unjudged'})
                    runs.append({'family': family, 'encoding': encoding, 'mode': mode, 'cache_bytes': cache, 'proper_names': names, 'expected': expected, 'actual': actual, 'individual_observations': observations})
entries = {}
for family, closure_file in [
    ('self-question', 'docs/self-question-native-closure-retry2.json.gz'),
    ('dapnikka', 'tests/fixtures/dapnikka-native-entries.json'),
    ('dapnikka-novel', 'tests/fixtures/dapnikka-novel-entries.json'),
]:
    native_path = ROOT / 'tests/fixtures' / (family + '-native.json')
    closure_path = ROOT / closure_file
    for path in [native_path, closure_path]:
        frozen[str(path)] = sha(path)
    closure = json.loads(gzip.decompress(closure_path.read_bytes()))['entries'] if closure_path.suffix == '.gz' else json.loads(closure_path.read_bytes())
    temporary = OUT.with_name(family + '-installed-native.db')
    assert not temporary.exists()
    try:
        subprocess.run([str(CLI), 'dict', 'import-krdict', str(native_path), str(temporary), '--snapshot', 'integration-native-source'], capture_output=True, check=True)
        for ident, expected in closure.items():
            result = subprocess.run([str(CLI), 'dict', 'entry', str(temporary), ident], capture_output=True, check=True)
            assert not result.stderr
            actual = json.loads(result.stdout)['entry']
            assert actual == expected, ident
            if ident in entries:
                assert entries[ident] == actual, 'duplicate Native identity changed'
            entries[ident] = actual
    finally:
        temporary.unlink(missing_ok=True)
assert len(runs) == 84
assert all(sha(p) == digest for p, digest in frozen.items())
report = {'state': 'installed-source-name-title-finite-passed', 'runs': runs, 'complete_native_entries': entries, 'frozen_inputs': frozen, 'inputs_unchanged': True, 'producer': {'text': Path(__file__).read_text(), 'sha256': sha(__file__)}, 'scope': 'Actual Git-backed installed integration CLI, twenty-four exact preserved source streams, twelve complete novel sentence streams, all individual name/title cases in Unicode/filter/cache and opt-in/out modes, and all complete Native imported entries. Complete broad/corpus/cohorts, browser and quiet timings remain separate; structural hypotheses are not contextual gold.', 'full_coverage_complete': False}
OUT.write_bytes(gzip.compress((json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode(), mtime=0))
print('Installed finite:', len(runs), 'streams,', len(entries), 'exact complete Native entries', flush=True)
