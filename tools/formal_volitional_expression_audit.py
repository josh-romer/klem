"""Verify separate expression identities and every independently authored source target."""
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
OWNERS = ['krdict:89455', 'krdict:89456']
TARGETS = [('가시렵니까', '가다', ['시']), ('배우렵니까', '배우다', []),
           ('빌리렵니까', '빌리다', []), ('가시렵니까', '가다', ['시']),
           ('모으렵니까', '모으다', []), ('참으렵니까', '참다', []),
           ('숨으렵니까', '숨다', []), ('먹으렵니까', '먹다', [])]


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inspect(packet, suite):
    assert packet['state'] == 'complete-original-expression-sources-and-independent-targets-before-probe', 'independent source preparation'
    producer = packet['producer']
    assert hashlib.sha256(producer['text'].encode()).hexdigest() == producer['sha256'], 'actual source producer'
    owners = packet['expression_entries']
    assert list(owners) == OWNERS, 'separate expression identities'
    assert [(o['id'], o['headword'], o['homonym'], o['pos'], o['lexical_unit']) for o in owners.values()] == [
        ('krdict:89455', '-렵니까', '2', '품사 없음', '문법‧표현'),
        ('krdict:89456', '-으렵니까', '2', '품사 없음', '문법‧표현')], 'expression homonym POS and lexical unit'
    imported = {ident: entry(value) for ident, value in packet['original_native_entries'].items()}
    assert imported == packet['complete_imported_entries'], 'every complete original Native field'
    assert all(imported[ident] == owner for ident, owner in owners.items()), 'complete expression owners'
    assert {'krdict:86548', 'krdict:86549', 'krdict:86604', 'krdict:86605'} <= imported.keys(), 'separate ending owners retained'
    assert all(imported[ident]['pos'] == '어미' for ident in ['krdict:86548', 'krdict:86549', 'krdict:86604', 'krdict:86605']), 'ending owner POS preserved'
    assert set(imported) == {ident for export in packet['original_exports'].values() for ident in export['ids']}, 'all original export identities'
    groups = []
    for ident, owner in owners.items():
        for sense in owner['senses']:
            for ordinal, lines in enumerate(sense['examples']):
                groups.append({'id': f'formal-volitional-expression-{ident.split(":")[1]}-sense-{sense["id"]}-group-{ordinal+1}',
                               'source_entry_id': ident, 'source_headword': owner['headword'], 'sense_id': sense['id'],
                               'group_ordinal': ordinal, 'complete_original_group': lines,
                               'source_notes': owner['notes'], 'sense_notes': sense['notes'], 'definition': sense['definition']})
    assert len(groups) == 8 and packet['complete_groups'] == groups, 'all complete original groups'
    assert packet['complete_source_text'] == '\n'.join(line for group in groups for line in group['complete_original_group']), 'all original source bytes'
    assert suite['schema_version'] == 1 and suite['sources'] == {ident: owner['url'] for ident, owner in owners.items()}, 'original expression source attribution'
    assert len(suite['cases']) == len(packet['independent_proposals']) == 8, 'all eight independent targets'
    for group, target, case, proposal in zip(groups, TARGETS, suite['cases'], packet['independent_proposals'], strict=True):
        surface, lemma, prefinals = target
        judgment = case['judgments'][0]
        assert case['id'] == group['id'] and case['surface'] == surface and len(case['judgments']) == 1, 'stable original target identity'
        assert {key: proposal[key] for key in group} == group, 'complete target context'
        original = '\n'.join(group['complete_original_group']).encode()
        assert original.count(surface.encode()) == 1 and proposal['surface_byte_offset'] == original.index(surface.encode()), 'original target byte position'
        assert proposal['surface'] == surface and proposal['judgment'] == judgment, 'unchanged authored judgment'
        assert judgment['verdict'] == 'required' and judgment['source'] == group['source_entry_id'], 'original required source'
        assert judgment['lemmas'] == [lemma] and judgment['lemma_kinds'] == ['predicate'], 'independent lexical target'
        assert judgment['morphemes'] == [*prefinals, '으렵니까'] and judgment['morpheme_kinds'] == ['prefinal'] * len(prefinals) + ['ending'], 'independent canonical roles'
        assert judgment['required_rules'] == ['ending.formal_volitional'], 'existing question rule provenance'
        assert any(owner['headword'] == lemma and owner['lexical_unit'] == '단어' for owner in imported.values()), 'original lexical owner retained'
    assert [owner['senses'][0]['notes'] for owner in owners.values()] == [["'-려고 합니까'가 줄어든 말이다."], ["'-으려고 합니까'가 줄어든 말이다."]], 'separate original contraction notes'
    tension = packet['source_tensions']
    assert len(tension) == 1 and tension[0]['source_entry_id'] == 'krdict:89456' and tension[0]['surface'] == '모으렵니까' and tension[0]['lexical_target'] == '모으다' and tension[0]['complete_original_group'] == groups[4]['complete_original_group'], 'original vowel stem source tension'
    return {'expression_owners': 2, 'complete_groups': 8, 'independent_targets': 8,
            'native_owners': len(imported), 'source_tensions': 1, 'full_coverage_complete': False}


def inputs():
    return (read(ROOT / 'docs/formal-volitional-expression-source-preparation.json.gz'),
            read(ROOT / 'tests/fixtures/formal-volitional-expression-validity.json'))


if __name__ == '__main__':
    print(inspect(*inputs()))
