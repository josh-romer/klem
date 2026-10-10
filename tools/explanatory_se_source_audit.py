"""Check original ending identities, complete groups and the explicit canonical correction."""
import copy
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inspect(prepared, proposals, authored, native, entries, suite, initial, correction, labels, label_native):
    assert prepared['state'] == 'complete-original-sources-preserved-no-engine-judgments', 'complete original preparation'
    assert sha(prepared['producer']['text'].encode()) == prepared['producer']['sha256'], 'original producer bytes'
    originals = prepared['original_native_entries']
    assert sha(json.dumps(originals, ensure_ascii=False, sort_keys=True).encode()) == '4db0206dc8b1cb4000426b58e5d4c75665adb902c463048f733fa6784f5fa66a', 'pinned initial Native fields'
    assert {i: entry(value) for i, value in originals.items()} == prepared['complete_imported_entries'] and len(originals) == 53, 'complete initial Native projection'
    assert {entry(value)['id']: value for value in native['LexicalResource']['Lexicon']['LexicalEntry']} == authored['original_native_entries'], 'lossless authored Native originals'
    assert sha(json.dumps(authored['original_native_entries'], ensure_ascii=False, sort_keys=True).encode()) == 'f0fc502fe91947274d0b991750203e6a946cfe899217acedda8332241ad750db', 'pinned authored Native fields'
    assert {i: entry(value) for i, value in authored['original_native_entries'].items()} == entries == authored['entries'] and len(entries) == 57, 'complete authored Native projection'
    assert all(authored['original_native_entries'][i] == value for i, value in originals.items()), 'initial original Native owners conserved'
    assert authored['initial_preparation_sha256'] == '5bd231e723182ec467cb8d78e8a1b15a4ea01d8445615e8a4914ce34f5fbd95a', 'immutable initial source binding'
    identities = ['krdict:79278', 'krdict:79279', 'krdict:83914']
    assert list(prepared['expression_entries']) == identities, 'three separate Source identities'
    notes = [['‘이다’, ‘아니다’ 뒤에 붙여 쓴다.'],
             ['‘ㄹ’을 제외한 받침 있는 동사와 형용사 또는 ‘-었-’ 뒤에 붙여 쓴다.'],
             ["'-게', '-오', '-ㅂ니다'와 같은 일부 종결 어미 뒤에 붙여 쓴다."]]
    groups = []
    for ident, expected_notes in zip(identities, notes, strict=True):
        owner = prepared['expression_entries'][ident]
        assert owner == entries[ident] and owner['notes'] == expected_notes, 'original separate attachment notes'
        assert owner['pos'] == ('조사' if ident == 'krdict:83914' else '어미'), 'original Source POS'
        for sense in owner['senses']:
            for ordinal, group in enumerate(sense['examples']):
                groups.append({'id': f'explanatory-se-{ident.split(":")[1]}-sense-{sense["id"]}-group-{ordinal+1}',
                               'source_entry_id': ident, 'source_headword': owner['headword'], 'sense_id': sense['id'],
                               'group_ordinal': ordinal, 'complete_original_group': group, 'source_notes': owner['notes'],
                               'sense_notes': sense['notes'], 'definition': sense['definition']})
    assert prepared['complete_groups'] == groups and len(groups) == 21, 'every complete original group and order'
    assert prepared['complete_source_text'] == '\n'.join(line for group in groups for line in group['complete_original_group']), 'complete source bytes and trailing spaces'
    assert proposals['state'] == 'independent-source-proposals-and-exact-baselines-preserved' and proposals['inputs_unchanged'], 'terminal authored proposals'
    assert sha(proposals['producer']['text'].encode()) == proposals['producer']['sha256'], 'proposal producer bytes'
    rows = proposals['proposals']
    assert len(rows) == 21 and {p['source_group_id'] for p in rows} == {g['id'] for g in groups}, 'all independent source proposals'
    cases = {case['id']: case for case in suite['cases']}
    assert len(cases) == len(suite['cases']) == 46, 'individual stable case IDs'
    assert {v: sum(j['verdict'] == v for c in suite['cases'] for j in c['judgments']) for v in ['required', 'forbidden']} == {'required': 37, 'forbidden': 9}, 'independent judgment counts'
    for proposal, group in zip(rows, groups, strict=True):
        assert all(proposal[key] == group[key] for key in ['source_entry_id', 'complete_original_group']) and proposal['source_group_id'] == group['id'], 'complete original proposal group'
        raw = '\n'.join(group['complete_original_group']).encode()
        start = proposal['surface_byte_offset']
        assert raw[start:start + len(proposal['surface'].encode())] == proposal['surface'].encode(), 'original target byte location'
        assert set(proposal['baseline_records']) == {'raw', 'headword', 'compatible'}, 'complete original baseline filters'
        case = cases[proposal['id']]
        judgment = case['judgments'][0]
        assert case['surface'] == proposal['surface'] and judgment['verdict'] == 'required', 'independent original source judgment'
        assert all(judgment[key] == proposal['proposed_' + key] for key in ['lemmas', 'lemma_kinds', 'morphemes', 'morpheme_kinds', 'required_rules']), 'original authored target identity'
        assert suite['sources'][judgment['source']] == entries[proposal['source_entry_id']]['url'], 'original source judgment link'
        for baseline in proposal['baseline_records'].values():
            assert baseline['exit_code'] == 0 and baseline['analysis']['normalized'] == proposal['surface'], 'actual original source baseline'
            assert not any([lemma['text'] for lemma in path['lemmas']] == proposal['proposed_lemmas'] for path in baseline['analysis']['analyses']), 'actual original missing lemma baseline'
    changed = copy.deepcopy(initial)
    target = next(c for c in changed['cases'] if c['id'] == correction['case_id'])
    assert correction['case_id'] == 'familiar-gryeo-boundary-formal-o', 'exact canonical correction case'
    assert target['judgments'][0]['morphemes'] == correction['original_morphemes'] == ['으오', '그려'], 'retained original canonical typo'
    target['judgments'][0]['morphemes'] = correction['corrected_morphemes']
    target['judgments'][0]['reason'] += ' Canonical-label correction: original83914note explicitly names -오; existing pre-change grammar represents 오 literally, with no 으오 ending. Surface/lemma/judgment scope unchanged.'
    assert correction['corrected_morphemes'] == ['오', '그려'] and changed == suite, 'only source-based canonical naming corrected'
    assert correction['complete_original_source_notes'] == notes[2], 'correction original source note'
    assert correction['original_suite_sha256'] == authored['authored_validity_sha256'] == '72fbbfcaef44bd9df32d198e9cf2d52f359bf612bbaf990429217174564850d8', 'immutable original authored suite binding'
    assert correction['corrected_suite_sha256'] == '3d13d48a6814c40b9a7328f0c2fc748f20590974a57f197a38b375c3a397cad8', 'explicit corrected suite binding'
    for key, kind, owners in [('-을세', 'ending', identities[:2]), ('그려', 'particle', identities[2:])]:
        assert labels[key]['kind'] == kind and labels[key]['sources'] == [{'id': int(i.split(':')[1]), 'headword': entries[i]['headword'], 'pos': entries[i]['pos']} for i in owners], 'actual component key and Source label identities'
    assert '-그려' not in labels, 'particle key separate from ending keys'
    assert {entry(value)['id']: value for value in label_native['LexicalResource']['Lexicon']['LexicalEntry']} == {i: originals[i] for i in identities}, 'complete separate label owners'
    return {'complete_groups': 21, 'initial_native_entries': 53, 'authored_native_entries': 57, 'required': 37, 'forbidden': 9, 'canonical_correction_preserved': True}


def inputs():
    return [read(ROOT / path) for path in ['docs/explanatory-se-source-preparation.json.gz', 'docs/explanatory-se-proposals.json.gz',
            'docs/explanatory-se-authored-native-closure.json.gz', 'tests/fixtures/explanatory-se-native.json',
            'tests/fixtures/explanatory-se-native-entries.json', 'tests/fixtures/explanatory-se-validity.json',
            'docs/explanatory-se-authored-validity-initial-46.json.gz', 'docs/explanatory-se-canonical-o-correction.json.gz',
            'web/src/grammar-labels.json', 'tests/fixtures/krdict-explanatory-se-labels.json']]


if __name__ == '__main__':
    print(inspect(*inputs()))
