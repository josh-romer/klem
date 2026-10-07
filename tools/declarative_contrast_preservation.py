"""Independently audit captured connective additions and all held-out adapter rows.

Complete broad-stream hashes remain capture provenance; every changed frame is
checked here. Corpus captures retain every actual word output and original row.
Preservation does not establish precision or a contextual reading.
"""
import json
from collections import Counter
from pathlib import Path
import klem_declarative_contrast_inversion as parent
from declarative_contrast_audit import ROOT, producer, read, sha
from klem_declarative_contrast_inversion import split_parent
from doeda_native_corpora import contexts_text
from friendly_command_corpora import outcome


def digest(value):
    return sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def metadata(report):
    producer(report)
    assert report['preparation_only'] is True and report['inputs_unchanged'] is True
    assert report['contextual_verdict'] == 'unjudged' and report['independent_review'] == 'pending'
    assert sha(report['inversion_helper']['text'].encode()) == report['inversion_helper']['sha256']
    assert report['inversion_helper']['sha256'] == sha(Path(parent.__file__).read_bytes())


def additions(before, after):
    assert {k:v for k,v in before.items() if k != 'analyses'} == {k:v for k,v in after.items() if k != 'analyses'}
    old, new = before['analyses'], after['analyses']
    assert [p for p in new if p in old] == old
    result = [p for p in new if p not in old]
    for candidate in result:
        parent, _ = split_parent(candidate)
        assert parent in old
    return result


def unjudged(row, candidate):
    parent, ids = split_parent(candidate)
    assert row['analysis'] == candidate and row['source_entries'] == ids
    assert row['exact_split_particle_parent'] == parent
    assert row['structural_verdict'] == 'unjudged broader composition'
    assert row['contextual_verdict'] == 'unjudged' and row['independent_review'] == 'pending'


def verify_broad(report, prior, native):
    metadata(report)
    assert len(report['comparisons']) == len(prior['comparisons']) == 8
    assert sum(c['records'] for c in report['comparisons']) == 1128312
    assert len({c['mode'] for c in report['comparisons']}) == 8
    derived, owners = [], set()
    for comparison, previous in zip(report['comparisons'], prior['comparisons'], strict=True):
        for key in ['source', 'source_sha256', 'mode', 'records']:
            assert comparison[key] == previous[key]
        assert comparison['exit_codes'] == [0,0] and comparison['baseline_matches_previous_capture'] is True
        assert comparison['before_jsonl_sha256'] == comparison['previous_capture_after_sha256'] == previous['after_jsonl_sha256']
        assert comparison['original_bytes_conserved'] is True
        indices = [f['record'] for f in comparison['changed_frames']]
        assert indices == sorted(set(indices)) and all(1 <= i <= comparison['records'] for i in indices)
        for frame in comparison['changed_frames']:
            b, a = frame['before'], frame['after']
            assert {k:v for k,v in b.items() if k not in ['analysis','dictionary']} == {k:v for k,v in a.items() if k not in ['analysis','dictionary']}
            assert a['span']['end'] - a['span']['start'] == len(a['surface'].encode())
            added = additions(b['analysis'], a['analysis'])
            assert added
            ba, aa = b['analysis']['analyses'], a['analysis']['analyses']
            assert len(b['dictionary']['readings']) == len(ba) and len(a['dictionary']['readings']) == len(aa)
            for i, path in enumerate(ba):
                assert b['dictionary']['readings'][i] == a['dictionary']['readings'][aa.index(path)]
            assert all(row in a['dictionary']['lemmas'] for row in b['dictionary']['lemmas'])
            assert all(b['dictionary'][k] == a['dictionary'][k] for k in ['source','fingerprint'])
            for path in added:
                assessment = a['dictionary']['readings'][aa.index(path)]
                ident = 'declarative-contrast-broad-' + digest([comparison['source_sha256'], comparison['mode'], frame['record'], path])[:24]
                derived.append((ident, comparison['source'], comparison['source_sha256'], comparison['mode'], frame['record'], a['surface'], a['span'], path, assessment))
                owners.update(e['id'] for l in assessment['lemmas'] for e in l['entries'])
    actual = []
    for row in report['individual_additions']:
        unjudged(row, row['analysis'])
        assert row['surface'] in row['complete_original_line']
        actual.append(tuple(row[k] for k in ['id','source','source_sha256','mode','record','surface','span','analysis','dictionary_assessment']))
    assert actual == derived and len(derived) == 55 and len({r[0] for r in derived}) == 55
    assert len(owners) == 19 and owners <= native.keys()
    return {'frames':1128312, 'individually_unjudged_additions':55, 'native_owner_ids':19,
            'statuses':dict(Counter(r['dictionary_assessment']['status'] for r in report['individual_additions']))}


def summary(comparisons, mode):
    counts = sorted(r[mode]['candidates'] for r in comparisons)
    n = len(counts)
    return {'converted_rows':n, 'grouped_matches':sum(r[mode]['matched'] for r in comparisons),
            'recovered_gold_lemmas':sum(r[mode]['recovered'] for r in comparisons),
            'gold_lemmas':sum(len(r['expected']) for r in comparisons), 'candidate_count_sum':sum(counts),
            'mean_candidates':sum(counts)/n, 'p95_candidates':counts[min(n*95//100,n-1)], 'max_candidates':max(counts)}


def verify_corpora(report, adapter, prior):
    metadata(report)
    # Adapter has no inversion helper because its exact outputs are checked below.
    producer(adapter)
    assert adapter['preparation_only'] and adapter['inputs_unchanged']
    assert adapter['contextual_verdict'] == 'unjudged' and adapter['independent_review'] == 'pending'
    before, after = report['before_words'], report['after_words']
    assert before == prior['after_words']
    assert set(before) == set(after) and len(before) == report['unique_surfaces'] == 32096
    assert digest(before) == report['before_words_sha256'] and digest(after) == report['after_words_sha256']
    changed, derived = {}, []
    for word in sorted(before):
        added = additions(before[word], after[word])
        if before[word] != after[word]:
            assert added
            changed[word] = {'before':before[word], 'after':after[word]}
        for candidate in added:
            derived.append(('declarative-contrast-corpus-' + digest([word,candidate])[:24], word, candidate))
    assert len(changed) == 2 and changed == report['changed_words']
    assert len(derived) == 2
    assert [(r['id'], r['surface'], r['analysis']) for r in report['candidate_changes']] == derived
    for row in report['candidate_changes']:
        unjudged(row, row['analysis'])
    assert len(report['corpora']) == len(adapter['runs']) == len(prior['corpora']) == 4
    total, locations = 0, {}
    for corpus, run, original in zip(report['corpora'], adapter['runs'], prior['corpora'], strict=True):
        for key in ['corpus','partition','source','source_sha256','report_lines']:
            assert corpus[key] == original[key]
            if key != 'report_lines':
                assert run[key] == corpus[key]
        assert sha(corpus['original_source_text'].encode()) == corpus['source_sha256']
        contexts = contexts_text(corpus['original_source_text'])
        rows = corpus['original_converted_rows']
        assert rows == original['original_converted_rows'] and digest(rows) == corpus['original_converted_rows_sha256']
        assert len(rows) == corpus['report_lines']-1 and len({r['id'] for r in rows}) == len(rows)
        comparisons = []
        for row in rows:
            word, gold = row['surface'], row['expected']
            context = contexts[row['id']]
            assert context['original_row'][1] == word
            old, new = outcome(gold,before[word]['analyses']), outcome(gold,after[word]['analyses'])
            assert old == new
            comparison = {k:row[k] for k in ['id','surface','expected']}
            for mode, observed, words in [('before',old,before),('after',new,after)]:
                comparison[mode] = {'matched':observed[0], 'recovered':observed[1], 'recovered_sets':observed[2], 'candidates':len(words[word]['analyses'])}
            comparisons.append(comparison)
            locations.setdefault(word,[]).append({'source':corpus['source'], 'source_sha256':corpus['source_sha256'], 'id':row['id'], **context})
        assert comparisons == corpus['comparisons'] and corpus['changed_gold_outcomes'] == []
        assert [s['mode'] for s in run['streams']] == ['before','after']
        for stream in run['streams']:
            assert stream['exit_code'] == 0 and sha(stream['jsonl'].encode()) == stream['sha256']
            actual = list(map(json.loads,stream['jsonl'].splitlines()))
            assert len(actual)-1 == stream['rows'] == len(rows)
            assert actual[0]['input_sha256'] == corpus['source_sha256']
            mode = stream['mode']
            for row, comparison in zip(actual[1:], comparisons, strict=True):
                assert all(row[k] == comparison[k] for k in ['id','surface','expected'])
                assert all(row[k] == comparison[mode][k] for k in ['matched','recovered','recovered_sets'])
            expected = summary(comparisons,mode)
            assert expected == corpus[mode+'_summary']
            for key, value in expected.items():
                if key != 'candidate_count_sum':
                    assert abs(actual[0][key]-value) < 1e-10
        # Candidate-count changes may alter summaries despite unchanged gold rows.
        assert run['exact_baseline_prototype_output'] == (run['streams'][0]['jsonl'] == run['streams'][1]['jsonl'])
        total += len(rows)
    for row in report['candidate_changes']:
        assert row['occurrences'] == locations[row['surface']]
    assert total == report['converted_rows'] == 66570
    return {'original_gold_rows':66570, 'actual_word_outputs':32096, 'changed_words':2, 'unjudged_additions':2, 'changed_gold_outcomes':0}


def inspect_captures():
    owners = read(ROOT / 'docs/declarative-contrast-broad-owner-preparation.json.gz')['complete_native_entries']
    broad = verify_broad(read(ROOT / 'docs/declarative-contrast-prototype-broad.json.gz'),
                         read(ROOT/'docs/literary-ri-prefinal-prototype-broad.json.gz'), owners)
    corpora = verify_corpora(read(ROOT / 'docs/declarative-contrast-prototype-corpora.json.gz'),
                            read(ROOT / 'docs/declarative-contrast-prototype-adapter.json.gz'),
                            read(ROOT/'docs/literary-ri-prefinal-prototype-corpora.json.gz'))
    return {'broad':broad,'corpora':corpora}


if __name__ == '__main__':
    print('Verified complete contrast preservation:', inspect_captures())
