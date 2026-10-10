"""Verify original particle ownership, independent targets and retained corrections."""
import copy
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
digest = lambda obj: sha(json.dumps(obj, ensure_ascii=False, sort_keys=True).encode())

def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)

def inspect(prepared, full, proposals, decision, authored, initial, correction,
            suite, native, entries, gaps, baselines, labels, label_native):
    for source, count, pinned in [
        (prepared, 21, 'edea882c8a8a712b5ba0b56dad3927a8fa7e3d071bfe707c2941bae4802d8ce3'),
        (full, 45, 'ce22f8da89d7ad269430a0c201d2dfdf6501ba12b0a414145413365efb686e45'),
    ]:
        assert source['state'] == 'complete-original-sources-preserved-no-engine-judgments', 'original preparation state'
        assert sha(source['producer']['text'].encode()) == source['producer']['sha256'], 'original preparation producer'
        originals = source['original_native_entries']
        assert len(originals) == count and digest(originals) == pinned, 'pinned complete original Native fields'
        assert {i: entry(value) for i, value in originals.items()} == source['complete_imported_entries'], 'lossless complete Native projection'
        assert list(source['expression_entries']) == ['krdict:83913'], 'separate particle source identity'
    assert all(full['original_native_entries'][i] == value for i, value in prepared['original_native_entries'].items()), 'initial owners retained'
    assert entries == full['complete_imported_entries'] and len(entries) == 45, 'all authored Native owners'
    assert {entry(value)['id']: value for value in native['LexicalResource']['Lexicon']['LexicalEntry']} == full['original_native_entries'], 'all authored Native original fields'
    owner = entries['krdict:83913']
    assert owner == prepared['expression_entries']['krdict:83913'] == full['expression_entries']['krdict:83913'] == proposals['source_entry'], 'same original particle owner'
    assert (owner['headword'], owner['homonym'], owner['pos']) == ('그래', '2', '조사'), 'particle homonym and POS'
    assert owner['notes'] == proposals['attachment_notes'] == ['‘-구먼’, ‘-군’, ‘-지’와 같은 일부 종결 어미 뒤에 붙여 쓴다.'], 'complete source attachment note'
    groups, plain = [], []
    for sense in owner['senses']:
        for ordinal, lines in enumerate(sense['examples']):
            groups.append({'id': f'familiar-geurae-83913-sense-{sense["id"]}-group-{ordinal+1}', 'source_entry_id': owner['id'],
                           'source_headword': owner['headword'], 'sense_id': sense['id'], 'group_ordinal': ordinal,
                           'complete_original_group': lines, 'source_notes': owner['notes'], 'sense_notes': sense['notes'], 'definition': sense['definition']})
            plain.append({'entry': owner['id'], 'sense': sense['id'], 'group': ordinal+1, 'lines': lines})
    assert len(groups) == 4 and prepared['complete_groups'] == full['complete_groups'] == groups and proposals['complete_groups'] == plain, 'all complete source groups and order'
    text = '\n'.join(line for group in groups for line in group['complete_original_group'])
    assert prepared['complete_source_text'] == full['complete_source_text'] == text, 'complete original source bytes'
    assert proposals['state'] == 'original-source-preserved-before-candidate-observation', 'proposals before candidate observation'
    assert decision['state'] == 'source-based-canonical-decision-before-implementation' and decision['source_particle'] == owner['id'], 'independent canonical decision'
    assert decision['initial_proposal_sha256'] == '9710394615516fd45d277bf20d25086808e1edb322da4be9c1adbb8bf81e0462', 'immutable initial proposal binding'
    assert decision['source_literal'] == '오랜만이구만그래' and decision['literal_group_preserved'], 'original written source retained'
    assert decision['canonical_lemmas'] == ['오랜만', '이다'] and decision['canonical_morphemes'] == ['구먼', '그래'], 'source-based canonical target'
    assert [s['url'] for s in decision['sources']] == [
        'https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=333765&searchCondition=&searchKeyword=',
        'https://www.korean.go.kr/nkview/nklife/1998_4/8-2.html',
        'https://www.korean.go.kr/nkview/nklife/1992_2/2_7.html'], 'separate primary canonical sources'
    assert authored['state'] == 'authored-before-implementation' and authored['native_owners'] == 45, 'independent pre-implementation authoring'
    assert digest(initial) == '81297ef815abf6d1e63019a4c09f32300127daa65636794176126e948e02529d', 'pinned original independent judgments'
    assert sha(authored['producer']['text'].encode()) == authored['producer']['sha256'], 'original authoring producer'
    assert authored['suite_sha256'] == correction['initial_suite_sha256'] == 'b073e0982cd1de45148ee8aa5a8e27dc66fd3f7837727186d21150271fc1b3b7', 'initial authored suite binding'
    assert correction['corrected_suite_sha256'] == 'e2b927b7691731277b429a7322639d26562b9946741d1bcd029943d87d61f9f5', 'corrected suite binding'
    assert correction['initial_marker'] == decision['variant_rule'] == 'written.colloquial_guman' and correction['actual_existing_marker'] == 'ending.exclamation_variant', 'existing variant rule ownership'
    assert correction['linguistic_targets_unchanged'], 'explicit retained target scope'
    expected = copy.deepcopy(initial)
    changed = 0
    for case in expected['cases']:
        for judgment in case['judgments']:
            if correction['initial_marker'] in judgment['required_rules']:
                judgment['required_rules'] = [correction['actual_existing_marker'] if r == correction['initial_marker'] else r for r in judgment['required_rules']]
                changed += 1
    assert changed == 6 and expected == suite, 'only existing rule ownership corrected'
    cases = suite['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 27, 'all stable independent case identities'
    assert {v: sum(j['verdict'] == v for c in cases for j in c['judgments']) for v in ['required', 'forbidden']} == {'required': 19, 'forbidden': 8}, 'independent required and forbidden boundaries'
    assert suite['sources'] == {'particle': owner['url'], 'guman': decision['sources'][0]['url']}, 'separate source judgment provenance'
    for ordinal, (target, case, group) in enumerate(zip(proposals['manual_targets'], cases[:4], plain, strict=True)):
        judgment = case['judgments'][0]
        assert any(target['surface'] in line for line in group['lines']), 'original target in complete source context'
        morphs = decision['canonical_morphemes'] if ordinal == 2 else target['canonical_morphemes']
        assert case['surface'] == target['surface'] and judgment['lemmas'] == target['lemmas'] and judgment['morphemes'] == morphs and judgment['verdict'] == 'required', 'independent original lexical and canonical target'
    assert gaps['state'] == 'baseline-observed-after-independent-source-proposals' and gaps['inputs_unchanged'], 'terminal original baseline'
    keys = [(target['surface'], encoding, mode) for target in proposals['manual_targets'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']]
    assert [(r['surface'], r['encoding'], r['mode']) for r in gaps['runs']] == keys, 'all original baseline Unicode filters'
    for run in gaps['runs']:
        target = next(t for t in proposals['manual_targets'] if t['surface'] == run['surface'])
        assert run['command'][1:3] == ['word', unicodedata.normalize(run['encoding'], run['surface'])], 'actual baseline original Unicode command'
        assert run['record']['normalized'] == run['surface'], 'normalized baseline original target'
        assert not any([l['text'] for l in path['lemmas']] == target['lemmas'] for path in run['record']['analyses']), 'independent missing baseline lexical target'
    assert len(baselines) == authored['baseline_surfaces'] == 32, 'all pre-change regression words'
    assert digest(baselines) == '6fd92b166ab2a5b204d7b3173afba4d7880e118d7c3bb8f50bcede3ebd9ee7c7', 'pinned pre-change regression fields'
    assert labels['그래']['kind'] == 'particle' and labels['그래']['sources'] == [{'id': 83913, 'headword': '그래', 'pos': '조사'}], 'actual particle component key and source'
    assert '-그래' not in labels, 'particle key separate from endings'
    assert {entry(value)['id']: value for value in label_native['LexicalResource']['Lexicon']['LexicalEntry']} == {owner['id']: prepared['original_native_entries'][owner['id']]}, 'complete label original owner'
    assert [(entries[i]['headword'], entries[i]['homonym'], entries[i]['pos']) for i in ['krdict:83913', 'krdict:27656', 'krdict:60238']] == [('그래', '2', '조사'), ('그래', '1', '감탄사'), ('그래', '3', '품사 없음')], 'distinct standalone homonym owners'
    return {'complete_groups': 4, 'original_baseline_records': 24, 'initial_native': 21, 'authored_native': 45,
            'required': 19, 'forbidden': 8, 'existing_rule_correction_only': True, 'full_coverage_complete': False}

def inputs():
    paths = ['docs/familiar-geurae-source-preparation.json.gz', 'docs/familiar-geurae-full-native-preparation.json.gz',
             'docs/familiar-geurae-original-source-proposals.json.gz', 'docs/familiar-geurae-canonical-guman-decision.json.gz',
             'docs/familiar-geurae-independent-authoring.json.gz', 'docs/familiar-geurae-authored-validity-initial-27.json.gz',
             'docs/familiar-geurae-existing-variant-rule-correction.json.gz', 'tests/fixtures/familiar-geurae-validity.json',
             'tests/fixtures/familiar-geurae-native.json', 'tests/fixtures/familiar-geurae-native-entries.json',
             'docs/familiar-geurae-baseline-gap.json.gz', 'tests/fixtures/familiar-geurae-baselines.json',
             'web/src/grammar-labels.json', 'tests/fixtures/krdict-familiar-geurae-labels.json']
    return [read(ROOT / path) for path in paths]

if __name__ == '__main__':
    print(inspect(*inputs()))
