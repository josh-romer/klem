"""Verify all retained primary -하다 source groups and independently attributed changes."""
import argparse
import copy
import hashlib
import itertools
import json
import unicodedata

from hada_nominal_audit import inspect_source as inspect_previous_source
from native_lmf import verify_native_lmf
from well_doeda_audit import ROOT, read, sha, word_records

SOURCE = ROOT / 'docs/hada-remaining-preflight.json.gz'
FIXTURE = ROOT / 'tests/fixtures/hada-remaining-sources.json'
REPORT = ROOT / 'docs/hada-remaining-diagnostics.json.gz'
ROLES = {'adverbial': 'adverbial', 'root': 'root', 'bound_noun': 'nominal'}


def rules_for(owner):
    return {
        ('suffix.auxiliary.' if owner['sense_id'] == '6' else 'suffix.')
        + ('adjective.hada' if '형용사' in pos else 'verb.hada')
        for pos in owner['supported_predicate_classes']
    }


def inspect_source(source):
    previous = read(ROOT / 'docs/hada-nominal-preflight.json.gz')
    release = read(ROOT / 'docs/hada-nominal-packaged-checks.json.gz')
    inspect_previous_source(previous)
    assert source['previous_source_sha256'] == sha(ROOT / 'docs/hada-nominal-preflight.json.gz')
    assert source['previous_package_receipt_sha256'] == sha(ROOT / 'docs/hada-nominal-packaged-checks.json.gz')
    assert source['source_closure_sha256'] == sha(ROOT / 'docs/hada-remaining-source-closure.json')
    assert source['before_cli_sha256'] == release['cli_sha256']
    assert source['dictionary_sha256'] == release['dictionary_sha256']
    assert source['preparation_only'] is True
    assert source['contextual_verdict'] == 'unjudged' and source['independent_review'] == 'pending'
    for field in ['complete_native_entries', 'corpora', 'all_sense_groups', 'words', 'input']:
        assert source[field] == previous[field]
    native = source['complete_native_entries']
    assert len(native) == 138
    verify_native_lmf(read(ROOT / 'tests/fixtures/krdict-hada-six-sense.json'), native)
    suffix = native[source['primary_suffix']]
    roles = {'3': ('adverbial', '부사'), '4': ('adverbial', '부사'), '5': ('root', None), '6': ('bound_noun', '의존 명사')}
    originals = [o for o in previous['owners'] if o['sense_id'] in roles]
    assert source['owners'] == originals and len(originals) == 17
    assert sum(len(o['supported_predicate_classes']) for o in originals) == 19
    for owner in originals:
        sense = next(s for s in suffix['senses'] if s['id'] == owner['sense_id'])
        assert owner['original_group'] == sense['examples'][owner['example_index']]
        assert owner['attachment_notes'] == sense['notes']
        role, pos = roles[owner['sense_id']]
        assert owner['base_role'] == role and owner['whole_head'] == owner['base'] + '하다'
        full = [e for e in native.values() if e['headword'] == owner['whole_head']]
        allowed = ['보조 동사', '보조 형용사'] if owner['sense_id'] == '6' else ['동사', '형용사']
        selected = [e for e in full if e['pos'] in allowed]
        assert sorted(e['id'] for e in selected) == sorted(owner['whole_entries'])
        assert sorted({e['pos'] for e in selected}) == owner['supported_predicate_classes']
        assert sorted(e['id'] for e in full if e['pos'] not in allowed) == sorted(owner['excluded_whole_homonyms'])
        bases = [e for e in native.values() if e['headword'] == owner['base'] and e['pos'] == pos] if pos else []
        assert sorted(e['id'] for e in bases) == sorted(b['id'] for b in owner['base_entries'])
        assert bases or role == 'root'
        expected = sorted({x.removesuffix('하다') for e in selected for x in e['origins']})
        assert expected == owner['whole_expected_base_origins']
        for b in owner['base_entries']:
            e = native[b['id']]
            assert e['origins'] == b['origins']
            relation = 'unknown' if not expected or not e['origins'] else 'recorded_match' if set(expected) & set(e['origins']) else 'recorded_difference'
            assert relation == b['relation']
    assert set(source['runs']) == {'raw', 'headword', 'compatible'}
    for mode, runs in source['runs'].items():
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        for name, run in runs.items():
            assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
            assert run['jsonl'] == release['runs'][mode][name]['jsonl']
        assert source['before'][mode] == runs['NFC-cached']
    assert hashlib.sha256(source['producer']['text'].encode()).hexdigest() == source['producer']['sha256']
    closure = read(ROOT / 'docs/hada-remaining-source-closure.json')
    assert closure['source_sha256'] == source['previous_source_sha256']
    assert [row['source_owner'] for row in closure['remaining_original_examples']] == originals
    for row in closure['remaining_original_examples']:
        owner = row['source_owner']
        assert row['source_sense'] == next(s for s in suffix['senses'] if s['id'] == owner['sense_id'])
        for field, ids in [('whole_entries', owner['whole_entries']), ('base_entries', [b['id'] for b in owner['base_entries']]), ('excluded_whole_homonyms', owner['excluded_whole_homonyms']), ('other_base_homonyms', owner['other_base_homonyms'])]:
            assert row[field] == [native[i] for i in ids]
    fixture = read(FIXTURE)
    assert fixture['source_sha256'] == sha(SOURCE)
    for field in ['owners', 'complete_native_entries', 'corpora']:
        assert fixture[field] == source[field]
    _, before = word_records(source['before']['raw']['jsonl'])
    assert fixture['before_analyses'] == {w: r['analysis'] for w, r in before.items()}
    cases = fixture['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 209
    assert sum(c['judgments'][0]['verdict'] == 'required' for c in cases) == 158
    assert sum(c['judgments'][0]['verdict'] == 'forbidden' for c in cases) == 51
    ledger = read(ROOT / 'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('hada-remaining-')] == cases
    assert ledger['sources']['hada-remaining-krdict'] == suffix['url']
    parents = {p['case_id']: p for p in fixture['required_parents']}
    assert len(parents) == 158
    _, contexts = word_records(fixture['context_before']['jsonl'])
    owners = {(o['base'], ROLES[o['base_role']]): o for o in originals}
    for case in cases:
        j = case['judgments'][0]
        body = {k: v for k, v in j.items() if k != 'id'}
        ident = 'hada-remaining-' + hashlib.sha256(json.dumps([case['surface'], body], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
        assert case['id'] == ident and j['id'] == ident + '-structure'
        if j['verdict'] != 'required':
            continue
        p = parents[ident]
        assert p['surface'] == case['surface']
        frozen = before.get(p['surface'], contexts.get(p['surface']))
        assert frozen is not None and p['before_parent'] in frozen['analysis']['analyses']
        owner = owners[(j['lemmas'][-1], j['lemma_kinds'][-1])]
        parent = p['before_parent']
        assert parent['lemmas'][-1]['text'] == owner['whole_head']
        assert j['lemmas'][:-1] == [l['text'] for l in parent['lemmas'][:-1]]
        assert j['lemma_kinds'][:-1] == [l['kind'] for l in parent['lemmas'][:-1]]
        assert set(j['required_rules']) <= rules_for(owner)
        forms = [m['form'] for m in parent['morphemes']]
        forms.insert(0 if len(parent['lemmas']) == 1 else 1, '하다')
        assert j['morphemes'] == forms
        assert p['whole_pos'] in owner['supported_predicate_classes']
    catalog = read(ROOT / 'web/src/hada-sources.json')
    assert catalog == [{'base': o['base'], 'kind': ROLES[o['base_role']], 'sense': int(o['sense_id']), 'role': o['base_role'], 'rules': [('suffix.auxiliary.' if o['sense_id'] == '6' else 'suffix.') + ('adjective.hada' if '형용사' in p else 'verb.hada') for p in o['supported_predicate_classes']]} for o in originals]
    return owners


def parent_for(owners, word, analysis, before):
    for parent in before:
        if len(analysis['lemmas']) != len(parent['lemmas']):
            continue
        insertions, allowed, good = [], set(), True
        for li, (new, old) in enumerate(zip(analysis['lemmas'], parent['lemmas'], strict=True)):
            if new == old:
                continue
            owner = owners.get((new['text'], new['kind']))
            if owner is None or old['text'] != owner['whole_head'] or old['kind'] not in (['predicate', 'auxiliary'] if owner['sense_id'] == '6' else ['predicate']):
                good = False
                break
            rules = rules_for(owner) & set(analysis['rules'])
            if not rules:
                good = False
                break
            allowed.update(rules)
            insertions.append((li, owner))
        if not good or not insertions or sorted(set(parent['rules']) | allowed) != analysis['rules']:
            continue
        candidates = [mi for mi, m in enumerate(analysis['morphemes']) if m == {'form': '하다', 'kind': 'suffix'}]
        for removed in itertools.combinations(candidates, len(insertions)):
            restored = copy.deepcopy(analysis)
            restored['lemmas'] = copy.deepcopy(parent['lemmas'])
            restored['rules'] = parent['rules']
            restored['morphemes'] = [m for mi, m in enumerate(analysis['morphemes']) if mi not in removed]
            if restored['morphemes'] != parent['morphemes']:
                continue
            valid = True
            for path in restored.get('spelling_paths', []):
                for recovery in path:
                    at = recovery['morpheme_index']
                    if at in removed:
                        valid = False
                        break
                    recovery['morpheme_index'] -= sum(i < at for i in removed)
            if valid and restored == parent:
                return parent, [{'lemma_index': li, 'morpheme_index': mi, 'source_owner': o} for (li, o), mi in zip(insertions, removed, strict=True)]
    raise AssertionError(('No exact independent source parent', word, analysis))


def inspect_comparison(source, report, *, baselines=None, input_text=None):
    owners = inspect_source(source)
    native = source['complete_native_entries']
    assert report['source_sha256'] == sha(SOURCE) and report['fixture_sha256'] == sha(FIXTURE)
    assert report['dictionary_sha256'] == source['dictionary_sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    assert set(report['runs']) == {'raw', 'headword', 'compatible'}
    baselines = source['before'] if baselines is None else baselines
    input_text = source['input'] if input_text is None else input_text
    changes, origin_fields = [], []
    for mode, runs in report['runs'].items():
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        _, before = word_records(baselines[mode]['jsonl'])
        semantic = None
        for name, run in runs.items():
            assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
            records, after = word_records(run['jsonl'])
            assert set(after) == set(before)
            assert ''.join(r['surface'] for r in records) == unicodedata.normalize(name.split('-')[0], input_text)
            current = {w: (r['analysis'], r['dictionary']) for w, r in after.items()}
            if semantic is None:
                semantic = current
            else:
                assert semantic == current
        count, surfaces, retained = 0, [], 0
        for word, record in after.items():
            old = before[word]
            original = old['analysis']['analyses']
            assert [a for a in record['analysis']['analyses'] if a in original] == original
            additions = [a for a in record['analysis']['analyses'] if a not in original]
            count += len(additions)
            if additions:
                surfaces.append(word)
            for i, analysis in enumerate(record['analysis']['analyses']):
                reading = record['dictionary']['readings'][i]
                if analysis in original:
                    assert reading == old['dictionary']['readings'][original.index(analysis)]
                    retained += 1
                    continue
                parent, components = parent_for(owners, word, analysis, original)
                for component in components:
                    owner = component['source_owner']
                    li = component['lemma_index']
                    assessment = next(l for l in reading['lemmas'] if l['lemma_index'] == li)
                    for matched in assessment['entries']:
                        entry = native[matched['id']]
                        identity_evidence = matched.get('derivational_identity')
                        eligible = entry['pos'] == '명사' or (owner['base_role'] == 'bound_noun' and entry['pos'] == '의존 명사') or (owner['base_role'] == 'adverbial' and entry['pos'] == '부사')
                        if owner['base_role'] == 'bound_noun' and entry['pos'] != '의존 명사':
                            assert matched['status'] != 'compatible'
                        if not eligible:
                            assert identity_evidence is None
                            continue
                        complete = all(native[i]['origins'] for i in owner['whole_entries'])
                        expected = owner['whole_expected_base_origins']
                        relation = 'recorded_match' if set(expected) & set(entry['origins']) else 'recorded_difference' if complete and entry['origins'] else 'unknown'
                        assert identity_evidence == {'relation': relation, 'morpheme_index': component['morpheme_index'], 'expected_origins': expected, 'whole_entries': owner['whole_entries'], 'whole_origins_complete': complete}
                identity = hashlib.sha256(json.dumps([mode, word, analysis], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
                changes.append({'id': 'hada-remaining-change-' + identity, 'mode': mode, 'surface': word, 'analysis': analysis, 'parent': parent, 'inserted_components': components, 'reading': reading, 'contextual_verdict': 'unjudged', 'independent_review': 'pending'})
            old_keys = [l['lemma'] for l in old['dictionary']['lemmas']]
            new_lemmas = record['dictionary']['lemmas']
            assert [l['lemma'] for l in new_lemmas if l['lemma'] in old_keys] == old_keys
            for old_l in old['dictionary']['lemmas']:
                new_l = next(l for l in new_lemmas if l['lemma'] == old_l['lemma'])
                assert [e['id'] for e in old_l['entries']] == [e['id'] for e in new_l['entries']]
                for old_e, new_e in zip(old_l['entries'], new_l['entries'], strict=True):
                    if old_e == new_e:
                        continue
                    assert {k: v for k, v in old_e.items() if k != 'origins'} == {k: v for k, v in new_e.items() if k != 'origins'}
                    assert old_e.get('origins') is None and 'origins' in new_e
                    entry = native[new_e['id']]
                    assert new_e['origins'] == entry['origins']
                    owner = owners.get((old_l['lemma']['text'], old_l['lemma']['kind']))
                    assert owner is not None
                    assert any(c['mode'] == mode and c['surface'] == word and any(s['source_owner'] == owner for s in c['inserted_components']) for c in changes)
                    origin_fields.append({'mode': mode, 'surface': word, 'lemma': old_l['lemma'], 'before_entry': old_e, 'after_entry': new_e, 'complete_native_entry': entry, 'source_owner': owner})
        assert count == report['addition_counts'][mode]
        assert surfaces == report['changed_surfaces'][mode]
        assert retained == report['retained_readings'][mode]
    if 'changes' in report:
        assert report['changes'] == changes
    if 'origin_field_changes' in report:
        assert report['origin_field_changes'] == origin_fields
    return changes, origin_fields


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.add_argument('--report', default=str(REPORT))
    args = parser.parse_args()
    changes, fields = inspect_comparison(read(SOURCE), read(args.report))
    print('Verified all 17 source groups, 209 stable cases, twelve streams,', len(changes), 'attributed additions and', len(fields), 'source-bound origin fields.')
