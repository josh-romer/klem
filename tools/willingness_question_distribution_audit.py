"""Compare complete original inputs and paths without refreshing expected output."""
import gzip
import hashlib
import json
import math
import unicodedata
from pathlib import Path

from conjectural_additive_novel_audit import matches

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
PARENTS = {
    'cohorts': ('conjectural-additive-phase2-copula-cohorts.json.gz', '628967f76f1da18a569bebc269707ae2f40028fec00b47b900f292a070a2f43f'),
    'gold': ('conjectural-additive-phase2-copula-corpora.json.gz', 'ac5e598443f463f0f454c8980a833168844118774f6cb8ce007e17418a39b56d'),
    'broad': ('conjectural-additive-phase2-copula-broad.json.gz', '887fd6121832a8f3aaa3ca2652ad3f3037fdb2ef82fa7a24f8b48e9ce16eb0a4'),
    'broad_inputs': ('reported-deoni-broad-inputs.json.gz', '7d43206bb6add22e79cb27173ff049cf501e9dcdabe307c9d5a4cacc2ab26902'),
    'annotations': ('literary-question-geona-prototype-corpora.json.gz', '12b9e453369bd11bd4c963bda66eaa69e438aff5c9d47999151445d4a2d220a3'),
}


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inputs():
    docs = ROOT / 'docs'
    parents = {}
    for key, (name, digest) in PARENTS.items():
        raw = (docs / name).read_bytes()
        assert sha(raw) == digest, 'unchanged original parent archive'
        parents[key] = json.loads(gzip.decompress(raw))
    proof = lambda name: read(docs / ('willingness-question-distribution-proof-' + name + '.gz'))
    return {
        'parents': parents,
        'source': read(ROOT / 'tests/fixtures/willingness-question-source.json'),
        'gold_cases': read(ROOT / 'tests/fixtures/willingness-question-validity.json'),
        'baseline': read(docs / 'willingness-question-source-proof-original-installed-baseline.json.gz'),
        'streams': proof('willingness-source-streams.json'),
        'cohorts': proof('willingness-cohorts.json'), 'gold': proof('willingness-corpora.json'),
        'broad': proof('willingness-broad.json'), 'contexts': proof('distribution-contexts.json'),
        'original_corpora': proof('original-corpus-inputs.json'),
        'binding': proof('prototype-binaries-retry2.json'),
        'parent_binding': proof('parent-installed-binding.json'),
    }


def binaries(v):
    binding, parent = v['binding'], v['parent_binding']
    assert binding['state'] == parent['state'] == 'passed' and binding['inputs_unchanged'] and parent['inputs_unchanged'], 'terminal frozen binary bindings'
    before_cli = next(p for p in parent['outputs'] if p.endswith('-klem-0.1.0')) + '/bin/klem'
    before_adapter = next(p for p in parent['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0')) + '/bin/klem-corpus-adapter'
    return before_cli, before_adapter, binding['binaries']['klem']['path'], binding['binaries']['klem-corpus-adapter']['path']


def terminal(report, state):
    assert report['state'] == state and report['inputs_unchanged'], 'terminal complete distribution capture'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual distribution producer'


def additions(before, after):
    old = before.get('analyses', [])
    new = after.get('analyses', [])
    assert [path for path in new if path in old] == old, 'every ordered original candidate retained'
    added = [path for path in new if path not in old]
    assert all('ending.willingness_question' in p['rules'] and any(m['form'] == '으련' and m['kind'] == 'ending' for m in p['morphemes']) for p in added), 'only new canonical willingness paths'
    return added


def frame_additions(before, after):
    assert {k: before[k] for k in ['surface', 'span', 'kind']} == {k: after[k] for k in ['surface', 'span', 'kind']}, 'original token ownership'
    old, new = before.get('analysis') or {}, after.get('analysis') or {}
    added = additions(old, new)
    for i, path in enumerate(old.get('analyses', [])):
        assert before['dictionary']['readings'][i] == after['dictionary']['readings'][new['analyses'].index(path)], 'every original Native assessment retained'
    return added


def inspect_streams(v):
    report = v['streams']
    terminal(report, 'complete-original-source-stream-comparison-passed')
    cli = binaries(v)[2]
    assert len(report['runs']) == len(v['baseline']['runs']) == 24, 'all original source policies'
    items = v['source']['items'] + v['source']['separate_expression_groups']
    cached = {}
    total = 0
    for run, old in zip(report['runs'], v['baseline']['runs'], strict=True):
        assert all(run[k] == old[k] for k in ['family', 'encoding', 'mode', 'cache_bytes', 'records', 'input_sha256']), 'original Unicode filter cache choices'
        groups = ['\n'.join(item['complete_original_group']) if run['family'] == 'complete-original-source' else item['surface'] for item in items]
        raw = unicodedata.normalize(run['encoding'], ('\n' if run['family'] == 'complete-original-source' else ' ').join(groups)).encode()
        assert sha(raw) == run['input_sha256'], 'every original source input byte'
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert run['command'][:4] == [cli, 'text', '-', '--dictionary'] and run['command'][4] in report['frozen_inputs'] and run['command'][5:] == flags + ['--cache-bytes', str(run['cache_bytes'])], 'actual source filter command'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['jsonl_sha256'] and run['before_jsonl_sha256'] == old['jsonl_sha256'], 'complete source output identity'
        previous = [json.loads(line) for line in old['jsonl'].splitlines()]
        records = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(records) == len(previous) == run['records'], 'all source frames'
        cursor = preserved = count = 0
        changes = []
        for index, (before, after) in enumerate(zip(previous, records, strict=True)):
            assert after['span']['start'] == cursor and raw[cursor:after['span']['end']].decode() == after['surface'], 'contiguous original source spans'
            cursor = after['span']['end']
            added = frame_additions(before, after)
            preserved += len((before.get('analysis') or {}).get('analyses', []))
            count += len(added)
            if before != after:
                changes.append({'record_index': index, 'before': before, 'after': after, 'new_paths': added, 'contextual_verdict': 'unjudged'})
        assert cursor == len(raw) and run['original_bytes_conserved'], 'complete original source coverage'
        assert changes == run['changed_frames'] and preserved == run['original_paths_preserved'] and count == run['new_family_paths'], 'all individual source changes retained'
        assert len(run['observations']) == len(items) == 18, 'all ending and expression observations'
        for observed, original, item in zip(run['observations'], old['observations'], items, strict=True):
            assert observed['id'] == item['id'] and observed['record_index'] == original['record_index'], 'original target observation identity'
            if 'typed_target' in item:
                target = dict(item['typed_target'], required_rules=['ending.willingness_question'])
                paths = records[observed['record_index']]['analysis']['analyses']
                indices = [i for i, path in enumerate(paths) if matches(path, target)]
                assert indices == observed['typed_path_indices'] and indices, 'all independent required source decompositions'
            else:
                assert observed['morphological_judgment'] == 'unjudged; ending semantic ownership not assigned', 'expression semantics remain separate'
        key = (run['family'], run['encoding'], run['mode'])
        assert key not in cached or cached[key] == run['jsonl'], 'cache preserves complete output bytes'
        cached[key] = run['jsonl']
        total += count
    assert sum(run['records'] for run in report['runs']) == 3336, 'complete finite source frame total'
    return total


def inspect_cohorts(v):
    report = v['cohorts']
    terminal(report, 'complete-corpus-history-cohorts-passed')
    before_cli, _, cli, _ = binaries(v)
    assert [(r['family'], r['surfaces']) for r in report['runs']] == [('corpus', 32096), ('history', 21406)], 'all complete original cohorts'
    observations = []
    for run, parent in zip(report['runs'], v['parents']['cohorts']['runs'], strict=True):
        before, after = run['captures']
        expected = parent['captures'][1]['words']
        assert before['binary'] == before_cli and after['binary'] == cli, 'actual bound cohort binaries'
        assert before['words'] == expected and len(expected) == run['surfaces'], 'exact complete original cohort baseline'
        assert set(after['words']) == set(expected), 'every original cohort word retained'
        changed = []
        for surface, old in expected.items():
            new = after['words'][surface]
            assert old['normalized'] == new['normalized'], 'original cohort normalization'
            added = additions(old, new)
            if old != new:
                changed.append(surface)
                observations.append({'id': f"willingness-question-cohort-{run['family']}-{len(changed)}", 'family': run['family'], 'surface': surface, 'before': old, 'after': new, 'new_paths': added, 'contextual_verdict': 'unjudged'})
        assert run['changed_words'] == changed, 'all independently derived changed cohort words'
    assert report['individual_changed_words'] == observations, 'every complete individual cohort observation'
    assert [o['surface'] for o in observations] == ['구소련', '대련', '마련', '소련'], 'bounded observed corpus changes'
    return observations


def inspect_contexts(v):
    contexts = v['contexts']
    assert contexts['state'] == 'all-original-distribution-contexts-preserved', 'complete distribution contexts'
    assert sha(contexts['producer']['text'].encode()) == contexts['producer']['sha256'], 'actual context producer'
    observations = {o['surface']: o for o in v['cohorts']['individual_changed_words']}
    assert set(observations) == {'구소련', '대련', '마련', '소련'}, 'all changed words have original contexts'
    occurrences, sources = [], {}
    originals = v['original_corpora']['sources']
    assert set(originals) == {r['source'] for r in v['parents']['gold']['runs']}, 'all four complete original corpus inputs'
    for run in v['parents']['gold']['runs']:
        source = run['source']
        original = originals[source]
        raw = original['text'].encode()
        assert sha(raw) == original['sha256'] == run['source_sha256'] and len(raw) == original['bytes'], 'unchanged complete original annotated input bytes'
        sources[source] = {'sha256': run['source_sha256'], 'bytes': len(raw)}
        for ordinal, sentence in enumerate(raw.split(b'\n\n')):
            for row in sentence.splitlines():
                if not row or row.startswith(b'#'):
                    continue
                fields = row.decode().split('\t')
                if len(fields) != 10 or fields[1] not in observations:
                    continue
                occurrences.append({'id': 'willingness-question-observed-' + run['corpus'] + '-' + run['partition'] + '-' + str(ordinal) + '-' + fields[0], 'corpus': run['corpus'], 'partition': run['partition'], 'source': source, 'surface': fields[1], 'original_annotation_fields': fields, 'complete_original_sentence': sentence.decode(), 'observation': observations[fields[1]], 'contextual_verdict': 'unjudged; original annotations are preserved without forbidding every alternative'})
    assert contexts['corpus_sources'] == sources and contexts['corpus_occurrences'] == occurrences and len(occurrences) == 14, 'every independently derived complete annotated context'
    assert contexts['changed_word_observations'] == list(observations.values()), 'all original word observations retained'
    novel = [o for r in v['broad']['runs'] for o in r['changed_frames']]
    assert len(novel) == 1 and contexts['complete_novel_observation'] == novel[0], 'complete original novel observation'
    return occurrences


def inspect_gold(v):
    report = v['gold']
    terminal(report, 'complete-original-annotated-comparison-passed')
    _, before_adapter, _, adapter = binaries(v)
    occurrences = inspect_contexts(v)
    assert [(r['corpus'], r['partition'], r['rows']) for r in report['runs']] == [('kaist', 'dev', 22220), ('kaist', 'test', 24490), ('gsd', 'dev', 9989), ('gsd', 'test', 9871)], 'all complete original annotated partitions'
    increments = {}
    for run, parent, annotation in zip(report['runs'], v['parents']['gold']['runs'], v['parents']['annotations']['corpora'], strict=True):
        assert all(run[k] == parent[k] == annotation[k] for k in ['corpus', 'partition', 'source', 'source_sha256']), 'original annotated partition identity'
        assert run['before_command'] == [before_adapter, run['corpus'], run['source']] and run['command'] == [adapter, run['corpus'], run['source']], 'actual bound corpus adapter commands'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['stdout_sha256'] and sha(parent['jsonl'].encode()) == run['before_stdout_sha256'], 'complete actual corpus output identity'
        old = [json.loads(line) for line in parent['jsonl'].splitlines()]
        new = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(new) == len(old) == run['rows'] + 1 and new[1:] == old[1:], 'every original annotated row and recovery unchanged'
        assert [{k: r[k] for k in ['id', 'surface', 'expected']} for r in new[1:]] == [{k: r[k] for k in ['id', 'surface', 'expected']} for r in annotation['original_converted_rows']], 'every independent original gold lemma retained'
        extra = sum(len(o['observation']['new_paths']) for o in occurrences if (o['corpus'], o['partition']) == (run['corpus'], run['partition']))
        assert {k: value for k, value in new[0].items() if k != 'mean_candidates'} == {k: value for k, value in old[0].items() if k != 'mean_candidates'}, 'all original summary metadata and recall unchanged'
        assert math.isclose(new[0]['mean_candidates'], old[0]['mean_candidates'] + extra / new[0]['converted_rows'], rel_tol=0, abs_tol=1e-12), 'candidate mean independently explained by original contexts'
        changes = {k: {'before': old[0].get(k), 'after': value} for k, value in new[0].items() if old[0].get(k) != value}
        assert run['summary_changes'] == changes, 'all exact corpus summary deltas retained'
        increments[(run['corpus'], run['partition'])] = extra
    assert not report['individual_changed_rows'], 'no invented gold changes'
    assert list(increments.values()) == [2, 24, 2, 0], 'all 28 raw candidate additions explained'
    return increments


def inspect_broad(v):
    report = v['broad']
    terminal(report, 'complete-broad-candidate-comparison-passed')
    before_cli, _, cli, _ = binaries(v)
    modes = ['candidate-raw', 'candidate-headword', 'candidate-compatible', 'novel-raw', 'novel-headword', 'novel-compatible', 'novel-headword-spacing', 'novel-compatible-spacing']
    assert [r['mode'] for r in report['runs']] == modes and sum(r['records'] for r in report['runs']) == 1128312, 'all eight complete broad streams'
    for run, parent in zip(report['runs'], v['parents']['broad']['runs'], strict=True):
        raw = v['parents']['broad_inputs']['sources'][run['source']]['text'].encode()
        assert run['source'] == parent['source'] and run['source_sha256'] == parent['source_sha256'] == sha(raw), 'complete original broad input bytes'
        assert run['records'] == parent['records'] and run['exit_codes'] == [0, 0] and run['original_bytes_conserved'], 'all complete broad token coverage'
        assert run['before_jsonl_sha256'] == parent['after_jsonl_sha256'], 'unchanged original broad baseline'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        for binary, command in zip([before_cli, cli], run['commands'], strict=True):
            assert command[:4] == [binary, 'text', run['actual_source'], '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags + (['--suggest-spacing'] if 'spacing' in run['mode'] else []), 'actual broad filter and spacing commands'
        changed = run['changed_frames']
        if run['mode'] != 'novel-raw':
            assert not changed and run['new_family_paths'] == 0 and run['before_jsonl_sha256'] == run['after_jsonl_sha256'], 'every other broad stream unchanged'
            continue
        assert len(changed) == 1 and run['new_family_paths'] == 1, 'one individually tracked raw novel change'
        item = changed[0]
        added = frame_additions(item['before'], item['after'])
        after = item['after']
        start, end = after['span']['start'], after['span']['end']
        assert after['surface'] == raw[start:end].decode() == '궐련', 'original changed novel token bytes'
        line_start = raw.rfind(b'\n', 0, start) + 1
        line_end = raw.find(b'\n', end)
        if line_end < 0:
            line_end = len(raw)
        assert item['line_byte_start'] == line_start and item['complete_original_line'] == raw[line_start:line_end].decode(), 'complete original novel passage bytes'
        assert item['id'] == f'willingness-question-broad-novel-raw-{start}-{end}' and item['contextual_verdict'] == 'unjudged', 'novel hypothesis is contextually unjudged'
        assert item['new_paths'] == added and len(added) == 1 and [h['text'] for h in added[0]['lemmas']] == ['궐다'], 'exact independently tracked novel hypothesis'
    return 1


def inspect(v):
    source_paths = inspect_streams(v)
    inspect_cohorts(v)
    increments = inspect_gold(v)
    inspect_broad(v)
    return {'state': 'complete-independent-willingness-distribution-audit-passed',
            'source_streams': 24, 'source_frames': 3336, 'new_source_paths': source_paths,
            'cohort_words': 53502, 'changed_corpus_words': 4, 'annotated_rows': 66570,
            'original_corpus_occurrences': 14, 'new_raw_annotated_candidates': sum(increments.values()),
            'broad_frames': 1128312, 'changed_broad_frames': 1,
            'contextual_review_complete': False, 'full_coverage_complete': False}


if __name__ == '__main__':
    print(json.dumps(inspect(inputs()), ensure_ascii=False, indent=2))
