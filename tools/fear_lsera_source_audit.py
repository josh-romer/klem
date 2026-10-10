"""Verify source ownership and independently authored targets, without running the engine."""
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = 'fc0c6aca06bd0d1a4c51a8cfcc7c4cc824742b5bacbc417198dbc57d30ce23a6'
SUITE_SHA = '2ccc67014adcae61861ee24774ddd2eae92bf82c7a9f3d138179460851390f25'
RULE = 'ending.apprehensive_lsera'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inspect(prepared, proposals, authored, closure, suite, native, owners,
            gaps, labels, label_native):
    assert prepared['state'] == 'complete-original-sources-and-independent-proposals-before-baseline', 'source-first preparation'
    assert sha(prepared['producer']['text'].encode()) == prepared['producer']['sha256'], 'source producer bytes'
    originals = prepared['original_native_entries']
    assert len(originals) == 50, 'all initial Native identities'
    assert {i: entry(v) for i, v in originals.items()} == prepared['complete_imported_entries'], 'initial lossless Native fields'
    expressions = prepared['expression_entries']
    assert list(expressions) == ['krdict:86497', 'krdict:86619'], 'separate ending owners'
    assert expressions == {i: prepared['complete_imported_entries'][i] for i in expressions}, 'original expression identity'
    groups = []
    for ident, headword, note in [
        ('krdict:86497', '-ㄹ세라', '‘이다’, 받침이 없거나 ‘ㄹ’ 받침인 동사와 형용사 또는 ‘-으시-’ 뒤에 붙여 쓴다.'),
        ('krdict:86619', '-을세라', '‘ㄹ’을 제외한 받침 있는 동사와 형용사 또는 ‘-었-’ 뒤에 붙여 쓴다.'),
    ]:
        owner = expressions[ident]
        assert (owner['headword'], owner['pos'], owner['homonym']) == (headword, '어미', '0'), 'separate source POS and homonym'
        assert owner['notes'] == [note], 'original allomorph attachment note'
        assert len(owner['senses']) == 3, 'all connective final and exclamation senses'
        assert [s['id'] for s in owner['senses']] == ['1', '2', '3'], 'original sense identities and order'
        for sense in owner['senses']:
            for ordinal, lines in enumerate(sense['examples']):
                groups.append({'id': f'fear-lsera-{ident.split(":")[1]}-sense-{sense["id"]}-group-{ordinal+1}',
                               'source_entry_id': ident, 'source_headword': headword, 'sense_id': sense['id'],
                               'group_ordinal': ordinal, 'complete_original_group': lines,
                               'source_notes': owner['notes'], 'sense_notes': sense['notes'], 'definition': sense['definition']})
    assert len(groups) == 25 and groups == prepared['complete_groups'], 'every complete original source group'
    text = '\n'.join(line for group in groups for line in group['complete_original_group'])
    assert text == prepared['complete_source_text'], 'complete original source bytes'
    assert proposals['state'] == 'authored-before-baseline-and-implementation', 'independent proposal timing'
    assert proposals['source_preparation_sha256'] == SOURCE_SHA, 'immutable pre-implementation source binding'
    targets = proposals['proposals']
    assert targets == prepared['independent_proposals'] and len(targets) == 25, 'unchanged independent targets'
    assert len({p['id'] for p in targets}) == 25, 'stable independent target IDs'
    for target, group in zip(targets, groups, strict=True):
        for key in ['id', 'source_entry_id', 'sense_id', 'complete_original_group']:
            assert target[key] == group[key], 'target original context ownership'
        original = '\n'.join(group['complete_original_group']).encode()
        offset = target['surface_byte_offset']
        assert original[offset:offset+len(target['surface'].encode())] == target['surface'].encode(), 'target exact original byte span'
        assert target['proposed_morphemes'][-1] == '을세라' and target['proposed_morpheme_kinds'][-1] == 'ending', 'independent canonical ending role'
        assert target['proposed_required_rules'] == [RULE], 'independent rule ownership'
    assert authored['state'] == 'authored-before-implementation', 'independent boundary timing'
    assert (authored['cases'], authored['required'], authored['forbidden'], authored['native_owners'], authored['complete_original_groups']) == (46, 37, 9, 69, 25), 'independent boundary scope'
    assert authored['suite_sha256'] == closure['authored_validity_sha256'] == SUITE_SHA, 'immutable authored judgment binding'
    assert closure['initial_preparation_sha256'] == SOURCE_SHA, 'initial Native closure binding'
    assert closure['state'] == 'complete-independent-source-and-boundary-native-closure-before-implementation', 'source-first Native closure'
    assert sha(closure['producer']['text'].encode()) == closure['producer']['sha256'], 'Native authoring producer'
    cases = suite['cases']
    assert len(cases) == len({c['id'] for c in cases}) == 46, 'all stable authored case IDs'
    assert {v: sum(j['verdict'] == v for c in cases for j in c['judgments']) for v in ['required', 'forbidden']} == {'required': 37, 'forbidden': 9}, 'required and forbidden boundaries'
    assert suite['sources'] == {'fear-lsera-short': expressions['krdict:86497']['url'], 'fear-lsera-full': expressions['krdict:86619']['url']}, 'separate source citations'
    for target, case in zip(targets, cases[:25], strict=True):
        assert case['id'] == target['id'] and case['surface'] == target['surface'], 'original case identity'
        judgment = case['judgments'][0]
        assert judgment['verdict'] == 'required', 'independent original required verdict'
        for name in ['lemmas', 'lemma_kinds', 'morphemes', 'morpheme_kinds', 'required_rules']:
            assert judgment[name] == target['proposed_'+name], 'independent lexical role and canonical target'
        expected = 'fear-lsera-short' if target['source_entry_id'] == 'krdict:86497' else 'fear-lsera-full'
        assert judgment['source'] == expected, 'individual judgment source ownership'
    for case in cases:
        for judgment in case['judgments']:
            assert judgment['morphemes'][-1] == '을세라' and judgment['morpheme_kinds'][-1] == 'ending', 'all authored ending roles'
            assert RULE in judgment['required_rules'], 'all named boundary paths'
    assert owners == closure['entries'] and len(owners) == 69, 'complete authored Native owners'
    assert all(closure['original_native_entries'][i] == value for i, value in originals.items()), 'initial original fields retained'
    projected = {entry(v)['id']: v for v in native['LexicalResource']['Lexicon']['LexicalEntry']}
    assert projected == closure['original_native_entries'], 'all original authored Native fields'
    assert {i: entry(v) for i, v in projected.items()} == owners, 'lossless authored Native projection'
    assert gaps['state'] == 'actual-installed-baseline-observed-after-independent-source-proposals' and gaps['inputs_unchanged'], 'actual terminal installed baseline'
    assert SOURCE_SHA in gaps['frozen_inputs'].values(), 'baseline bound to original source'
    keys = [(p['id'], encoding, mode) for p in targets for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']]
    assert [(r['id'], r['encoding'], r['mode']) for r in gaps['runs']] == keys, 'all 150 original baseline observations'
    for run in gaps['runs']:
        target = next(p for p in targets if p['id'] == run['id'])
        assert run['surface'] == target['surface'] and run['exit_code'] == 0, 'successful original baseline surface'
        assert run['command'][1:3] == ['word', unicodedata.normalize(run['encoding'], run['surface'])], 'actual Unicode baseline command'
        flags = [] if run['mode'] == 'raw' else ['--dict-only'] if run['mode'] == 'headword' else ['--dict-compatible']
        assert run['command'][3:] == ['--dictionary', run['command'][4], *flags], 'actual baseline filter command'
        assert run['record']['normalized'] == target['surface'], 'baseline normalized surface'
        assert not any([l['text'] for l in path['lemmas']] == target['proposed_lemmas'] for path in run['record']['analyses']), 'independently missing lexical baseline'
    label = labels['-을세라']
    assert label['kind'] == 'ending' and label['sources'] == [{'id': 86497, 'headword': '-ㄹ세라', 'pos': '어미'}, {'id': 86619, 'headword': '-을세라', 'pos': '어미'}], 'original label ending owners'
    assert label['label'] == 'Concern / exclamation', 'separate source senses remain visible'
    assert '-ㄹ세라' not in labels and '을세라' not in labels, 'canonical typed component key'
    assert {entry(v)['id']: v for v in label_native['LexicalResource']['Lexicon']['LexicalEntry']} == {i: originals[i] for i in expressions}, 'complete original label source fields'
    assert sha(json.dumps(prepared, ensure_ascii=False, sort_keys=True).encode()) == '8b1e0c2cdd54ab603c51b14327672e27c069c04a0c8ae04e6cf299123635feb4', 'immutable original preparation fields'
    assert sha(json.dumps(suite, ensure_ascii=False, sort_keys=True).encode()) == '428f72f72877026c7169b1e5da4d11731a4d66418e544ee53b32b61938a148d8', 'immutable independently authored judgments'
    return {'source_groups': 25, 'baseline_observations': 150, 'required': 37, 'forbidden': 9,
            'original_native_owners': 50, 'authored_native_owners': 69, 'contextual_review': 'pending', 'full_coverage_complete': False}


def inputs():
    docs = ROOT / 'docs'
    source = docs / 'fear-lsera-source-preparation.json.gz'
    assert sha(source.read_bytes()) == SOURCE_SHA, 'immutable original source bytes'
    suite = ROOT / 'tests/fixtures/fear-lsera-validity.json'
    assert sha(suite.read_bytes()) == SUITE_SHA, 'immutable pre-implementation suite bytes'
    paths = [source, docs / 'fear-lsera-independent-source-proposals.json.gz',
             docs / 'fear-lsera-independent-authoring.json.gz', docs / 'fear-lsera-authored-native-closure.json.gz',
             suite, ROOT / 'tests/fixtures/fear-lsera-native.json', ROOT / 'tests/fixtures/fear-lsera-native-entries.json',
             docs / 'fear-lsera-baseline-gap.json.gz', ROOT / 'web/src/grammar-labels.json',
             ROOT / 'tests/fixtures/krdict-fear-lsera-labels.json']
    return [read(path) for path in paths]


if __name__ == '__main__':
    print(inspect(*inputs()))
