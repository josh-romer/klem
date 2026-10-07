"""Offline validation of captured RI differentials, owners, and corpus adapters.

Complete broad stream hashes are capture provenance. This verifier independently
checks every captured changed frame and derives its individual additions. Corpus
captures include all word analyses and adapter rows, which are fully recomputed.
Neither preservation nor dictionary compatibility establishes precision.
"""
import json
from collections import Counter

from doeda_native_corpora import contexts_text
from friendly_command_corpora import outcome
from literary_ri_prefinal_audit import BASE, ROOT, producer, read, sha
from native_lmf import entry, verify_native_lmf


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def metadata(report):
    producer(report)
    assert report['preparation_only'] and report['inputs_unchanged']
    assert report['contextual_verdict'] == 'unjudged'
    assert report['independent_review'] == 'pending'


def additions(before, after):
    assert {k: v for k, v in before.items() if k != 'analyses'} == {
        k: v for k, v in after.items() if k != 'analyses'
    }
    old, new = before['analyses'], after['analyses']
    assert [p for p in new if p in old] == old
    added = [p for p in new if p not in old]
    for path in added:
        assert 'prefinal.conjectural_ni' in path['rules']
        assert any(
            pair[0] == {'form': '으리', 'kind': 'prefinal'}
            and pair[1]['kind'] == 'ending'
            and pair[1]['form'] in ['니', '으니라']
            for pair in zip(path['morphemes'], path['morphemes'][1:])
        )
    return added


def unjudged(observation):
    assert observation['source_entries'] == ['krdict:52612', 'krdict:86606']
    assert observation['structural_verdict'] == 'unjudged broader composition'
    assert observation['contextual_verdict'] == 'unjudged'
    assert observation['independent_review'] == 'pending'


def verify_broad(report, owners):
    metadata(report)
    producer(owners)
    assert owners['broad_capture_sha256'] == sha(
        (BASE / 'literary-ri-prefinal-prototype-broad.json.gz').read_bytes()
    )
    native = owners['complete_native_entries']
    assert len(native) == 182
    assert native == {k: entry(v) for k, v in owners['original_lmf'].items()}
    verify_native_lmf(owners['english_projection'], native)
    assert native == read(ROOT / 'tests/fixtures/literary-ri-prefinal-broad-native.json')
    assert owners['english_projection'] == read(
        ROOT / 'tests/fixtures/krdict-literary-ri-prefinal-broad-english.json'
    )
    assert owners['source_capture_sha256'] == sha(
        (BASE / 'literary-ri-prefinal-source-discovery.json.gz').read_bytes()
    )
    manifest = json.loads(read(BASE / 'literary-ri-prefinal-source-discovery.json.gz')['dictionary_metadata']['manifest'])
    assert {k.rsplit('/', 1)[-1]: v for k, v in owners['source_hashes'].items()} == {
        f['name']: f['sha256'] for f in manifest['files']
    }
    comparisons = report['comparisons']
    assert len(comparisons) == 8
    assert sum(c['records'] for c in comparisons) == 1128312
    assert len({c['mode'] for c in comparisons}) == 8
    derived, matched = [], set()
    for comparison in comparisons:
        assert comparison['exit_codes'] == [0, 0]
        assert comparison['baseline_matches_previous_capture']
        assert comparison['before_jsonl_sha256'] == comparison['previous_capture_after_sha256']
        assert comparison['original_bytes_conserved']
        indices = [f['record'] for f in comparison['changed_frames']]
        assert indices == sorted(set(indices))
        assert all(1 <= i <= comparison['records'] for i in indices)
        for frame in comparison['changed_frames']:
            before, after = frame['before'], frame['after']
            assert {k: v for k, v in before.items() if k not in ['analysis', 'dictionary']} == {
                k: v for k, v in after.items() if k not in ['analysis', 'dictionary']
            }
            assert after['span']['end'] - after['span']['start'] == len(after['surface'].encode())
            new = additions(before['analysis'], after['analysis'])
            assert new
            for i, path in enumerate(before['analysis']['analyses']):
                assert before['dictionary']['readings'][i] == after['dictionary']['readings'][
                    after['analysis']['analyses'].index(path)
                ]
            assert all(row in after['dictionary']['lemmas'] for row in before['dictionary']['lemmas'])
            for key in ['source', 'fingerprint']:
                assert before['dictionary'][key] == after['dictionary'][key]
            for path in new:
                ident = 'literary-ri-prefinal-broad-' + digest([
                    comparison['source_sha256'], comparison['mode'], frame['record'], path
                ])[:24]
                assessment = after['dictionary']['readings'][after['analysis']['analyses'].index(path)]
                derived.append((ident, comparison['source'], comparison['source_sha256'],
                                comparison['mode'], frame['record'], after['surface'],
                                after['span'], path, assessment))
                for lemma in assessment['lemmas']:
                    matched.update(e['id'] for e in lemma['entries'])
    observations = report['individual_additions']
    actual = []
    for row in observations:
        unjudged(row)
        assert row['surface'] in row['complete_original_line']
        actual.append(tuple(row[k] for k in ['id', 'source', 'source_sha256', 'mode',
                                            'record', 'surface', 'span', 'analysis',
                                            'dictionary_assessment']))
    assert actual == derived and len(derived) == 731
    assert len({row['id'] for row in observations}) == 731
    assert matched == set(owners['matched_broad_ids']) and len(matched) == 138
    assert matched <= native.keys()
    # The formal bundle is generated but has no pinned dictionary head.
    # Preserve that unknown ownership explicitly rather than inventing an entry.
    heads = {e['headword'] for e in native.values()}
    assert set(owners['named_headwords']) - heads == {'-으리다'}
    return {'frames': 1128312, 'captured_additions': 731, 'matched_owners': 138,
            'complete_native_owners': 182, 'statuses': dict(Counter(
                o['dictionary_assessment']['status'] for o in observations))}


def verify_corpora(report, adapter):
    metadata(report)
    metadata(adapter)
    assert adapter['cli_capture_sha256'] == sha(
        (BASE / 'literary-ri-prefinal-prototype-corpora.json.gz').read_bytes()
    )
    before, after = report['before_words'], report['after_words']
    assert len(before) == len(after) == report['unique_surfaces'] == 32096
    assert digest(before) == report['before_words_sha256']
    assert digest(after) == report['after_words_sha256']
    assert before == after and report['changed_words'] == {} and report['candidate_changes'] == []
    assert len(report['corpora']) == len(adapter['runs']) == 4
    assert {(r['corpus'], r['partition']) for r in report['corpora']} == {
        ('kaist', 'dev'), ('kaist', 'test'), ('gsd', 'dev'), ('gsd', 'test')
    }
    total = 0
    for corpus, run in zip(report['corpora'], adapter['runs'], strict=True):
        assert all(corpus[k] == run[k] for k in ['corpus', 'partition', 'source', 'source_sha256'])
        assert sha(corpus['original_source_text'].encode()) == corpus['source_sha256']
        contexts = contexts_text(corpus['original_source_text'])
        original = corpus['original_converted_rows']
        assert digest(original) == corpus['original_converted_rows_sha256']
        assert len(original) == len(corpus['comparisons']) == corpus['report_lines'] - 1
        assert len({r['id'] for r in original}) == len(original)
        assert corpus['changed_gold_outcomes'] == []
        assert corpus['before_summary'] == corpus['after_summary']
        assert run['exact_baseline_prototype_output']
        assert [s['mode'] for s in run['streams']] == ['before', 'after']
        assert run['streams'][0]['jsonl'] == run['streams'][1]['jsonl']
        for stream in run['streams']:
            assert stream['exit_code'] == 0
            assert sha(stream['jsonl'].encode()) == stream['sha256']
            rows = [json.loads(line) for line in stream['jsonl'].splitlines()]
            assert len(rows) - 1 == stream['rows'] == len(original)
            assert rows[0]['input_sha256'] == corpus['source_sha256']
            for row, old, comparison in zip(rows[1:], original, corpus['comparisons'], strict=True):
                assert all(row[k] == old[k] == comparison[k] for k in ['id', 'surface', 'expected'])
                assert contexts[row['id']]['original_row'][1] == row['surface']
                matched, recovered, sets = outcome(row['expected'], after[row['surface']]['analyses'])
                assert (row['matched'], row['recovered'], row['recovered_sets']) == (matched, recovered, sets)
                expected = {'matched': matched, 'recovered': recovered, 'recovered_sets': sets,
                            'candidates': len(after[row['surface']]['analyses'])}
                assert comparison['before'] == comparison['after'] == expected
            counts = sorted(len(after[r['surface']]['analyses']) for r in rows[1:])
            summary = {'converted_rows': len(counts), 'grouped_matches': sum(r['matched'] for r in rows[1:]),
                       'recovered_gold_lemmas': sum(r['recovered'] for r in rows[1:]),
                       'gold_lemmas': sum(len(r['expected']) for r in rows[1:]),
                       'candidate_count_sum': sum(counts), 'mean_candidates': sum(counts) / len(counts),
                       'p95_candidates': counts[min(len(counts) * 95 // 100, len(counts) - 1)],
                       'max_candidates': max(counts)}
            assert summary == corpus[stream['mode'] + '_summary']
            for key, value in summary.items():
                if key != 'candidate_count_sum':
                    assert abs(rows[0][key] - value) < 1e-10
        total += len(original)
    assert total == report['converted_rows'] == 66570
    return {'unique_surfaces': 32096, 'converted_rows': total, 'changed_words': 0}


def verify_history(report):
    metadata(report)
    assert report == read(ROOT / 'tests/fixtures/literary-ri-prefinal-history.json')
    assert len(report['source_files_sha256']) == 47
    origins = {}
    fields = {'before_words', 'before_analyses', 'source_before_analyses', 'source_cohort_before_analyses'}

    def visit(value, source, pointer=''):
        if isinstance(value, dict):
            for key, item in value.items():
                at = pointer + '/' + key
                if key in fields and isinstance(item, dict):
                    for surface in item:
                        origins.setdefault(surface, []).append({'source': source,
                            'source_sha256': report['source_files_sha256'][source], 'pointer': at})
                else:
                    visit(item, source, at)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                visit(item, source, pointer + '/' + str(i))

    for source, expected in report['source_files_sha256'].items():
        data = (ROOT / source).read_bytes()
        assert sha(data) == expected
        visit(json.loads(data), source)
    assert len(origins) == report['surfaces'] == 21298
    assert len(report['changes']) == report['changed_words'] == 9
    count = 0
    for surface, row in report['changes'].items():
        assert row['origins'] == origins[surface]
        new = additions(row['before'], row['after'])
        assert [a['analysis'] for a in row['additions']] == new
        for observation in row['additions']:
            unjudged(observation)
            assert observation['id'] == 'literary-ri-prefinal-legacy-' + digest([
                surface, observation['analysis']])[:24]
        count += len(new)
    assert count == report['added_paths'] == 17
    return {'original_files': 47, 'original_surfaces': 21298, 'changed_words': 9, 'added_paths': 17}


def inputs():
    return [read(BASE / ('literary-ri-prefinal-' + name)) for name in [
        'prototype-broad.json.gz', 'broad-owner-preparation.json.gz',
        'prototype-corpora.json.gz', 'prototype-adapter.json.gz', 'legacy-history.json']]


def verify(broad, owners, corpora, adapter, history):
    assert len({d['before_cli_sha256'] for d in [broad, corpora, history]}) == 1
    assert len({d['cli_sha256'] for d in [broad, corpora, history]}) == 1
    return {'state': 'captured-preservation-audit-passed',
            'broad': verify_broad(broad, owners), 'corpora': verify_corpora(corpora, adapter),
            'history': verify_history(history), 'contextual_verdict': 'unjudged',
            'independent_review': 'pending'}


if __name__ == '__main__':
    print(json.dumps(verify(*inputs()), ensure_ascii=False))
