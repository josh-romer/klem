"""Independently compare full corpus/history/gold captures and all novel changes."""
import argparse
import gzip
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def read(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))

def inputs(directory=None):
    docs = ROOT / 'docs'
    phase2 = lambda name: read(docs / ('conjectural-additive-phase2-' + name))
    return {'cohorts': phase2('copula-cohorts.json.gz'),
            'gold': phase2('copula-corpora.json.gz'),
            'broad': phase2('copula-broad.json.gz'),
            'parent_cohorts': read(docs / 'formal-volitional-cohorts.json.gz'),
            'parent_gold': read(docs / 'formal-volitional-corpora.json.gz'),
            'parent_broad': read(docs / 'formal-volitional-broad.json.gz'),
            'original_gold': read(docs / 'literary-question-geona-prototype-corpora.json.gz'),
            'original_inputs': read(docs / 'reported-deoni-broad-inputs.json.gz'),
            'phase1_broad': read(docs / 'conjectural-additive-phase1-broad.json.gz'),
            'binding': read(docs / 'formal-volitional-expression-installed-source-binding.json.gz')}

def inspect(v):
    for name, state in [('cohorts', 'complete-corpus-history-cohorts-passed'),
                        ('gold', 'complete-original-annotated-comparison-passed'),
                        ('broad', 'complete-broad-candidate-comparison-passed')]:
        record = v[name]
        assert record['state'] == state and record['inputs_unchanged'], 'terminal frozen complete distribution capture'
        assert sha(record['producer']['text'].encode()) == record['producer']['sha256'], 'actual distribution producer identity'
    binding = v['binding']
    assert binding['state'] == 'passed', 'actual installed parent binding'
    cli = str(Path(next(p for p in binding['outputs'] if p.endswith('-klem-0.1.0'))) / 'bin/klem')
    adapter = str(Path(next(p for p in binding['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))) / 'bin/klem-corpus-adapter')
    cohorts = v['cohorts']
    assert [(run['family'], run['surfaces']) for run in cohorts['runs']] == [('corpus', 32096), ('history', 21406)], 'all complete original cohorts'
    for run, parent in zip(cohorts['runs'], v['parent_cohorts']['runs'], strict=True):
        old, new = run['captures']
        assert old['binary'] == cli and new['binary'] in cohorts['frozen_inputs'], 'actual bound cohort commands'
        expected = parent['captures'][1]['words']
        assert len(expected) == run['surfaces'] and old['words'] == expected, 'all exact original cohort words'
        assert new['words'] == expected and not run['changed_words'], 'all cohort outputs unchanged'
    assert not cohorts['individual_changed_words'], 'no invented cohort changes'
    gold = v['gold']
    assert [(run['corpus'], run['partition'], run['rows']) for run in gold['runs']] == [('kaist', 'dev', 22220), ('kaist', 'test', 24490), ('gsd', 'dev', 9989), ('gsd', 'test', 9871)], 'all four complete annotated partitions'
    for run, parent, original in zip(gold['runs'], v['parent_gold']['runs'], v['original_gold']['corpora'], strict=True):
        assert (run['corpus'], run['partition'], run['source'], run['source_sha256']) == (original['corpus'], original['partition'], original['source'], original['source_sha256']), 'unchanged original annotated source identity'
        assert run['before_command'] == [adapter, run['corpus'], run['source']], 'actual bound original adapter command'
        assert run['command'][0] in gold['frozen_inputs'] and run['command'][1:] == [run['corpus'], run['source']], 'actual new adapter command'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['stdout_sha256'], 'complete actual annotated output'
        assert run['jsonl'] == parent['jsonl'] and sha(parent['jsonl'].encode()) == run['before_stdout_sha256'] and not run['summary_changes'], 'all annotated output and original recall unchanged'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == run['rows'] + 1, 'every individual annotated row'
        assert [{k: row[k] for k in ['id', 'surface', 'expected']} for row in rows[1:]] == [{k: row[k] for k in ['id', 'surface', 'expected']} for row in original['original_converted_rows']], 'all independent original annotation IDs/surfaces/gold'
    assert not gold['individual_changed_rows'], 'no invented annotated changes'
    broad = v['broad']
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible', 'novel-raw', 'novel-headword', 'novel-compatible', 'novel-headword-spacing', 'novel-compatible-spacing']
    assert [run['mode'] for run in broad['runs']] == modes and sum(run['records'] for run in broad['runs']) == 1128312, 'all eight complete broad streams'
    phase1 = {run['mode']: run for run in v['phase1_broad']['runs']}
    novel_paths = {}
    for run, parent in zip(broad['runs'], v['parent_broad']['comparisons'], strict=True):
        raw = v['original_inputs']['sources'][run['source']]['text'].encode()
        assert run['source'] == parent['source'] and run['source_sha256'] == parent['source_sha256'] == sha(raw), 'every original broad source byte'
        assert run['records'] == parent['records'] and run['exit_codes'] == [0, 0] and run['original_bytes_conserved'], 'actual complete broad token coverage'
        assert run['before_jsonl_sha256'] == parent['after_jsonl_sha256'], 'actual bound parent broad output'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        for index, command in enumerate(run['commands']):
            assert command[0] == cli if index == 0 else command[0] in broad['frozen_inputs'], 'actual broad executable binding'
            assert command[1:4] == ['text', run['actual_source'], '--dictionary'] and command[4] in broad['frozen_inputs'] and command[5:] == [*flags, *(['--suggest-spacing'] if 'spacing' in run['mode'] else [])], 'actual broad filter/spacing flags'
        if run['mode'].startswith('candidate'):
            assert not run['changed_frames'] and run['new_family_paths'] == 0 and run['before_jsonl_sha256'] == run['after_jsonl_sha256'], 'complete candidate corpus unchanged'
            continue
        # Independently derive every suffix occurrence directly from original text.
        expected_spans = []
        text = raw.decode()
        for match in re.finditer(r'[가-힣]+려니와', text):
            start = len(text[:match.start()].encode())
            expected_spans.append((start, start + len(match.group().encode()), match.group()))
        assert len(expected_spans) == 15 and [(item['after']['span']['start'], item['after']['span']['end'], item['after']['surface']) for item in run['changed_frames']] == expected_spans, 'every independently rederived original novel occurrence'
        old_phase1 = {item['id']: item for item in phase1[run['mode']]['changed_frames']}
        count = 0
        for item in run['changed_frames']:
            before, after = item['before'], item['after']
            assert {k: before[k] for k in ['surface', 'span', 'kind']} == {k: after[k] for k in ['surface', 'span', 'kind']}, 'original broad token identity'
            start, end = after['span']['start'], after['span']['end']
            assert raw[start:end].decode() == after['surface'], 'original novel occurrence bytes'
            line_start = raw.rfind(b'\n', 0, start) + 1
            line_end = raw.find(b'\n', end)
            if line_end < 0: line_end = len(raw)
            assert item['line_byte_start'] == line_start and item['complete_original_line'] == raw[line_start:line_end].decode(), 'complete original novel context retained'
            assert item['id'] == f"conjectural-additive-broad-{run['mode']}-{start}-{end}" and item['contextual_verdict'] == 'unjudged', 'stable individually unjudged novel occurrence'
            paths = after['analysis']['analyses']
            for old_index, path in enumerate(before['analysis']['analyses']):
                assert path in paths, 'every original novel candidate retained'
                assert before['dictionary']['readings'][old_index] == after['dictionary']['readings'][paths.index(path)], 'every original novel Native assessment retained'
            added = [path for path in paths if path not in before['analysis']['analyses']]
            assert added == item['new_paths'] and all('ending.conjectural_additive' in path['rules'] for path in added), 'every new novel candidate individually retained'
            count += len(added)
            if item['id'] in old_phase1:
                for index, path in enumerate(old_phase1[item['id']]['after']['analysis']['analyses']):
                    assert path in paths, 'every initial prototype novel candidate retained'
                    assert old_phase1[item['id']]['after']['dictionary']['readings'][index] == after['dictionary']['readings'][paths.index(path)], 'every initial novel Native assessment retained'
            if after['surface'] == '장래려니와':
                typed = [index for index, path in enumerate(paths) if [(lemma['text'], lemma['kind']) for lemma in path['lemmas']] == [('장래', 'nominal'), ('이다', 'copula')] and [(morph['form'], morph['kind']) for morph in path['morphemes']] == [('으려니와', 'ending')] and 'copula.omitted_ending' in path['rules']]
                assert typed and all(after['dictionary']['readings'][i]['status'] == 'compatible' for i in typed), 'original novel independently typed omitted copula present'
        assert count == run['new_family_paths'], 'exact complete novel candidate totals'
        novel_paths[run['mode']] = count
    assert novel_paths == {'novel-raw': 58, 'novel-headword': 30, 'novel-compatible': 27, 'novel-headword-spacing': 30, 'novel-compatible-spacing': 27}, 'complete raw/filter/spacing new path totals'
    return {'state': 'complete-independent-copula-distribution-audit-passed', 'cohort_words': 53502,
            'annotated_rows': 66570, 'broad_frames': 1128312, 'novel_occurrences': 15,
            'new_novel_paths': novel_paths, 'contextual_and_independent_review': 'pending'}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    print(json.dumps(inspect(inputs(args.evidence_dir)), ensure_ascii=False, indent=2))
