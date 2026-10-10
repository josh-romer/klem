"""Rederive all annotated outcomes and statistics from unchanged original gold."""
import gzip
import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from friendly_command_corpora import outcome

ROOT = Path(__file__).resolve().parents[1]
sha = lambda value: hashlib.sha256(value).hexdigest()


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def inspect(report, prior, original, cohorts, contexts):
    assert report['state'] == 'passed' and report['inputs_unchanged'], 'terminal actual adapter'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual producer bytes'
    assert report['adapter'] in report['frozen_inputs'], 'actual adapter identity'
    assert len(report['runs']) == len(prior['runs']) == len(original['corpora']) == 4, 'complete gold partitions'
    words = next(r for r in cohorts['runs'] if r['family'] == 'corpus')['captures'][1]['words']
    changes, total, matched_gain, recovered_gain = [], 0, 0, 0
    originals = {}
    for run, previous, source in zip(report['runs'], prior['runs'], original['corpora'], strict=True):
        for key in ['corpus', 'partition', 'source', 'source_sha256']:
            assert run[key] == previous[key] == source[key], 'original partition identity'
        assert sha(source['original_source_text'].encode()) == run['source_sha256'], 'original source bytes'
        assert run['exit_code'] == 0 and run['command'] == [report['adapter'], run['corpus'], run['source']], 'actual adapter command'
        assert sha(run['jsonl'].encode()) == run['stdout_sha256'], 'complete capture digest'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        old = [json.loads(line) for line in previous['jsonl'].splitlines()]
        gold = source['original_converted_rows']
        assert len(rows) == len(old) == len(gold) + 1 and run['rows'] == len(gold), 'complete original gold rows'
        counts = []
        for row, before, target in zip(rows[1:], old[1:], gold, strict=True):
            assert {k: row[k] for k in ['id', 'surface', 'expected']} == {k: target[k] for k in ['id', 'surface', 'expected']}, 'unaltered original gold identity'
            paths = words[target['surface']]['analyses']
            assert (row['matched'], row['recovered'], row['recovered_sets']) == outcome(target['expected'], paths), 'independently derived gold recovery'
            assert not before['matched'] or row['matched'], 'prior gold match conserved'
            assert before['recovered'] <= row['recovered'] and all(s in row['recovered_sets'] for s in before['recovered_sets']), 'prior gold recovery conserved'
            counts.append(len(paths))
            if before != row:
                change = {'id': row['id'], 'corpus': run['corpus'], 'partition': run['partition'], 'before': before, 'after': row, 'contextual_verdict': 'unjudged'}
                changes.append(change)
                originals[row['id']] = (source, target, before, row)
        summary = rows[0]
        n = len(gold)
        matches = sum(row['matched'] for row in rows[1:])
        recovered = sum(row['recovered'] for row in rows[1:])
        gold_count = sum(len(row['expected']) for row in rows[1:])
        transformed = [row for row in rows[1:] if row['expected'] != [unicodedata.normalize('NFC', row['surface'])]]
        derived = {'converted_rows': n, 'grouped_matches': matches, 'recovered_gold_lemmas': recovered,
                   'gold_lemmas': gold_count, 'mean_candidates': sum(counts) / n,
                   'p95_candidates': sorted(counts)[n * 95 // 100], 'max_candidates': max(counts),
                   'grouped_lemma_recall': matches / n, 'lemma_recall': recovered / gold_count,
                   'transformed_rows': len(transformed), 'transformed_matches': sum(row['matched'] for row in transformed),
                   'transformed_grouped_recall': sum(row['matched'] for row in transformed) / len(transformed) if transformed else 0.0}
        for key, value in derived.items():
            assert abs(summary[key] - value) < 1e-10, 'independently derived candidate and recovery statistics'
        misses = Counter((row['surface'], tuple(row['expected'])) for row in rows[1:] if not row['matched'])
        expected_misses = [{'surface': surface, 'expected': list(expected), 'count': count}
                           for (surface, expected), count in sorted(misses.items(), key=lambda item: (-item[1], *item[0]))[:30]]
        assert summary['common_misses'] == expected_misses, 'independently derived common misses'
        delta = {key: {'before': old[0][key], 'after': value} for key, value in summary.items() if old[0].get(key) != value}
        assert run['summary_changes'] == delta, 'complete summary delta accounting'
        assert summary['input_sha256'] == run['source_sha256'], 'original summary input'
        for key in set(summary) - set(derived) - {'common_misses'}:
            assert summary[key] == old[0][key], 'other original summary fields conserved'
        matched_gain += matches - old[0]['grouped_matches']
        recovered_gain += recovered - old[0]['recovered_gold_lemmas']
        total += n
    assert total == 66570 and report['individual_changed_rows'] == changes, 'complete changed row accounting'
    assert {r['id'] for r in changes} == {'id:MH2_0110-s387/3', 'id:MH2_0110-s395/5'}, 'exact original gold recoveries'
    assert matched_gain == 2 and recovered_gain == 3, 'exact original recovery gains'
    assert len(contexts) == 2 and {r['id'] for r in contexts} == set(originals), 'complete recovered gold contexts'
    for context in contexts:
        source, target, before, after = originals[context['id']]
        assert context['source_sha256'] == source['source_sha256'], 'original context source identity'
        block = context['complete_original_annotation_block']
        assert block in source['original_source_text'].split('\n\n'), 'complete original annotation block'
        sentence, ordinal = context['id'].removeprefix('id:').split('/')
        assert '# sent_id = ' + sentence in block.splitlines(), 'original sentence identity'
        token = next(line.split('\t') for line in block.splitlines() if line.startswith(ordinal + '\t'))
        assert token[1] == context['surface'] == target['surface'] and token[2] == context['original_annotation'], 'original annotated token'
        assert context['expected'] == target['expected'] and context['original_converted_row'] == target, 'independent original lemma targets'
        assert '# text = ' + context['text'] in block.splitlines(), 'complete original sentence'
    return {'original_gold_rows': total, 'changed_rows': len(changes), 'new_grouped_matches': matched_gain,
            'new_recovered_lemmas': recovered_gain, 'contextual_and_independent_review': 'pending'}


def inputs():
    return [read(ROOT / 'docs' / name) for name in ['explanatory-se-corpora.json.gz', 'giroseo-corpora.json.gz',
            'literary-question-geona-prototype-corpora.json.gz', 'explanatory-se-cohorts.json.gz']] + [read(ROOT / 'tests/fixtures/explanatory-se-gold-contexts.json')]


if __name__ == '__main__':
    print(inspect(*inputs()))
