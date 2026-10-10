"""Check original owners, unchanged independent judgments and evaluation layers."""
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = 'c98ed537976fa5b7ed894cc400a2a5a6e92860214d394b8193fb4266a212f1f6'
SUITE_SHA = '4baa4c4bc9da65a9a9c493b7aadd537afd82ff3464daf586dc3e59823d9cd181'
RULE = 'ending.formal_volitional'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
fields_sha = lambda value: sha(json.dumps(value, ensure_ascii=False, sort_keys=True).encode())


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inspect(prepared, proposals, authored, closure, suite, native, owners,
            gaps, labels, label_native, policy):
    assert prepared['state'] == 'complete-original-sources-and-independent-proposals-before-baseline', 'source-first preparation'
    assert sha(prepared['producer']['text'].encode()) == prepared['producer']['sha256'], 'source producer bytes'
    originals = prepared['original_native_entries']
    assert len(originals) == 33, 'all initial Native identities'
    assert {i: entry(value) for i, value in originals.items()} == prepared['complete_imported_entries'], 'initial lossless Native fields'
    expressions = prepared['expression_entries']
    assert list(expressions) == ['krdict:86548', 'krdict:86549', 'krdict:86604', 'krdict:86605'], 'separate ending owners'
    assert expressions == {i: prepared['complete_imported_entries'][i] for i in expressions}, 'original expression identity'
    groups = []
    for ident, headword, note in [
        ('krdict:86548', '-렵니까', "받침이 없거나 'ㄹ' 받침인 동사 또는 '-으시-' 뒤에 붙여 쓴다."),
        ('krdict:86549', '-렵니다', "받침이 없거나 'ㄹ' 받침인 동사 또는 '-으시-' 뒤에 붙여 쓴다."),
        ('krdict:86604', '-으렵니까', '‘ㄹ’을 제외한 받침 있는 동사 뒤에 붙여 쓴다.'),
        ('krdict:86605', '-으렵니다', '‘ㄹ’을 제외한 받침 있는 동사 뒤에 붙여 쓴다.'),
    ]:
        owner = expressions[ident]
        homonym = '1' if headword.endswith('니까') else '0'
        assert (owner['headword'], owner['pos'], owner['homonym']) == (headword, '어미', homonym), 'original source POS and homonym'
        assert owner['notes'] == [note], 'original attachment note'
        assert len(owner['senses']) == 1 and owner['senses'][0]['id'] == '1', 'complete original sense identities'
        for sense in owner['senses']:
            for ordinal, lines in enumerate(sense['examples']):
                groups.append({'id': f'formal-volitional-{ident.split(":")[1]}-sense-{sense["id"]}-group-{ordinal + 1}',
                               'source_entry_id': ident, 'source_headword': headword, 'sense_id': sense['id'],
                               'group_ordinal': ordinal, 'complete_original_group': lines,
                               'source_notes': owner['notes'], 'sense_notes': sense['notes'], 'definition': sense['definition']})
    assert groups == prepared['complete_groups'] and len(groups) == 17, 'every complete original source group'
    assert '\n'.join(line for group in groups for line in group['complete_original_group']) == prepared['complete_source_text'], 'complete original source bytes'
    assert proposals['state'] == 'authored-before-baseline-and-implementation', 'independent proposal timing'
    assert proposals['source_preparation_sha256'] == SOURCE_SHA, 'immutable original source binding'
    targets = proposals['proposals']
    assert targets == prepared['independent_proposals'] and len(targets) == 17, 'unchanged independent targets'
    for target, group in zip(targets, groups, strict=True):
        assert all(target[key] == group[key] for key in ['id', 'source_entry_id', 'sense_id', 'complete_original_group']), 'target context ownership'
        raw = '\n'.join(group['complete_original_group']).encode()
        offset = target['surface_byte_offset']
        assert raw[offset:offset + len(target['surface'].encode())] == target['surface'].encode(), 'target exact original byte span'
        canonical = '으렵니까' if group['source_headword'].endswith('니까') else '으렵니다'
        assert target['proposed_morphemes'][-1] == canonical and target['proposed_morpheme_kinds'][-1] == 'ending', 'separate canonical ending target'
        assert target['proposed_required_rules'] == [RULE], 'independent target rule ownership'
    assert authored['state'] == 'authored-before-implementation', 'independent boundary timing'
    assert (authored['cases'], authored['required'], authored['forbidden'], authored['native_owners'], authored['complete_original_groups']) == (59, 33, 26, 43, 17), 'independent boundary scope'
    assert authored['suite_sha256'] == closure['authored_validity_sha256'] == SUITE_SHA, 'immutable authored judgment binding'
    assert closure['initial_preparation_sha256'] == SOURCE_SHA, 'original Native closure binding'
    assert closure['state'] == 'complete-independent-source-and-boundary-native-closure-before-implementation', 'source-first Native closure'
    assert sha(closure['producer']['text'].encode()) == closure['producer']['sha256'], 'Native authoring producer'
    cases = suite['cases']
    assert len(cases) == len({case['id'] for case in cases}) == 59, 'all stable authored case IDs'
    assert {verdict: sum(j['verdict'] == verdict for c in cases for j in c['judgments']) for verdict in ['required', 'forbidden']} == {'required': 33, 'forbidden': 26}, 'required and forbidden boundaries'
    assert suite['sources'] == {i: owner['url'] for i, owner in expressions.items()}, 'all four original source citations'
    for target, case in zip(targets, cases[:17], strict=True):
        assert (case['id'], case['surface']) == (target['id'], target['surface']), 'original case identity'
        judgment = case['judgments'][0]
        assert judgment['verdict'] == 'required', 'independent original required verdict'
        assert all(judgment[key] == target['proposed_' + key] for key in ['lemmas', 'lemma_kinds', 'morphemes', 'morpheme_kinds', 'required_rules']), 'independent lexical role and canonical target'
        assert judgment['source'] == target['source_entry_id'], 'individual judgment source ownership'
    for case in cases:
        for judgment in case['judgments']:
            assert judgment['source'] in expressions, 'boundary source ownership'
            source = expressions[judgment['source']]
            canonical = '으렵니까' if source['headword'].endswith('니까') else '으렵니다'
            assert judgment['morphemes'][-1] == canonical and judgment['morpheme_kinds'][-1] == 'ending', 'all authored ending roles'
            assert RULE in judgment['required_rules'], 'all named boundary provenance'
    assert owners == closure['entries'] and len(owners) == 43, 'complete authored Native owners'
    assert all(closure['original_native_entries'][i] == value for i, value in originals.items()), 'initial original fields retained'
    projected = {entry(value)['id']: value for value in native['LexicalResource']['Lexicon']['LexicalEntry']}
    assert projected == closure['original_native_entries'], 'all original authored Native fields'
    assert {i: entry(value) for i, value in projected.items()} == owners, 'lossless authored Native projection'
    assert policy['state'] == 'evaluation-policy-authored-before-implementation-and-prototype-observation', 'independent evaluation policy timing'
    assert policy['authored_suite_sha256'] == SUITE_SHA, 'unchanged policy judgment binding'
    conditional = [case['id'] for case in cases if any(case['id'].endswith('-forbidden-' + suffix) for suffix in ['adjective', 'honorific-adjective', 'negative-copula'])]
    assert policy['dictionary_required_case_ids'] == conditional and len(conditional) == 6, 'exact dictionary POS judgments'
    assert (policy['raw_cases'], policy['raw_required'], policy['raw_forbidden'], policy['dictionary_cases'], policy['dictionary_required'], policy['dictionary_forbidden']) == (53, 33, 20, 59, 33, 26), 'complete raw and dictionary evaluation scopes'
    assert gaps['state'] == 'actual-installed-baseline-observed-after-independent-source-proposals' and gaps['inputs_unchanged'] and gaps['exact_prior_baseline_records'], 'actual terminal installed baseline'
    assert SOURCE_SHA in gaps['frozen_inputs'].values(), 'baseline bound to original source'
    keys = [(target['id'], encoding, mode) for target in targets for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible']]
    assert [(run['id'], run['encoding'], run['mode']) for run in gaps['runs']] == keys, 'all 102 original baseline observations'
    for run in gaps['runs']:
        target = next(target for target in targets if target['id'] == run['id'])
        assert run['surface'] == target['surface'] and run['exit_code'] == 0, 'successful original baseline surface'
        command = run['command']
        assert command[0].startswith('/nix/store/') and command[0] in gaps['frozen_inputs'], 'actual immutable installed baseline CLI'
        assert command[1:3] == ['word', unicodedata.normalize(run['encoding'], run['surface'])], 'actual Unicode baseline command'
        flags = [] if run['mode'] == 'raw' else ['--dict-only'] if run['mode'] == 'headword' else ['--dict-compatible']
        assert command[3:] == ['--dictionary', command[4], *flags], 'actual baseline filter command'
        assert run['record']['normalized'] == target['surface'], 'baseline normalized surface'
        assert run['lexical_target_matches'] == run['structural_target_matches'] == 0, 'recorded independent missing targets'
        assert not any([lemma['text'] for lemma in path['lemmas']] == target['proposed_lemmas'] for path in run['record']['analyses']), 'independently missing lexical baseline'
    for canonical, short, full, label in [('-으렵니까', 86548, 86604, 'Intention question'), ('-으렵니다', 86549, 86605, 'Intention statement')]:
        value = labels[canonical]
        assert value['kind'] == 'ending' and value['sources'] == [{'id': i, 'headword': expressions[f'krdict:{i}']['headword'], 'pos': '어미'} for i in [short, full]], 'original label ending owners'
        assert value['label'] == label, 'distinct question and statement labels'
        assert canonical[1:] not in labels and canonical.replace('-으', '-') not in labels, 'canonical typed component key'
    assert {entry(value)['id']: value for value in label_native['LexicalResource']['Lexicon']['LexicalEntry']} == {i: originals[i] for i in expressions}, 'complete original label source fields'
    assert fields_sha(prepared) == 'd8a8948070d92b442088aa6f78d919b4a65818e54913eb161f482aa6902af8ec', 'immutable original preparation fields'
    assert fields_sha(suite) == 'e5b5fb27da4318233ecca2445512468a533fbc8a5e793e96b9f46c21c0ee706e', 'immutable independently authored judgments'
    assert fields_sha(gaps) == '75590ec9dd4a8b90acd92c6eb29f08b4ca4e1bb928a4629087ae0fcfcbfe5081', 'immutable complete baseline observations'
    assert fields_sha(policy) == '78e1adf379ccfd0645afabe827c9fed73031e36b81170117a3fd6ac1b6b28dfd', 'immutable pre-implementation evaluation policy'
    assert fields_sha(closure) == '547727f251a05616bdd42bb154f7710f5f865a72c3ba3bcd0036fadd32a8a699', 'immutable authored Native closure fields'
    return {'source_groups': 17, 'baseline_observations': 102, 'required': 33, 'forbidden': 26,
            'raw_cases': 53, 'dictionary_cases': 59, 'original_native_owners': 33,
            'authored_native_owners': 43, 'contextual_review': 'pending', 'full_coverage_complete': False}


def inputs():
    docs = ROOT / 'docs'
    source = docs / 'formal-volitional-source-preparation.json.gz'
    suite = ROOT / 'tests/fixtures/formal-volitional-validity.json'
    assert sha(source.read_bytes()) == SOURCE_SHA, 'immutable original source bytes'
    assert sha(suite.read_bytes()) == SUITE_SHA, 'immutable pre-implementation suite bytes'
    paths = [source, docs / 'formal-volitional-independent-source-proposals.json.gz',
             docs / 'formal-volitional-independent-authoring.json.gz', docs / 'formal-volitional-authored-native-closure.json.gz',
             suite, ROOT / 'tests/fixtures/formal-volitional-native.json', ROOT / 'tests/fixtures/formal-volitional-native-entries.json',
             docs / 'formal-volitional-latest-baseline-gap.json.gz', ROOT / 'web/src/grammar-labels.json',
             ROOT / 'tests/fixtures/krdict-formal-volitional-labels.json', ROOT / 'tests/fixtures/formal-volitional-evaluation-policy.json']
    return [read(path) for path in paths]


if __name__ == '__main__':
    print(inspect(*inputs()))
