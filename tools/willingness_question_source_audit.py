"""Verify original owners, preauthored judgments and observed prior alternatives."""
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import array, entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def inputs():
    fixtures = ROOT / 'tests/fixtures'
    proof = lambda name: read(ROOT / 'docs' / ('willingness-question-source-proof-' + name))
    source_raw = (fixtures / 'willingness-question-source.json').read_bytes()
    original_raw = {name: gzip.decompress((ROOT / 'docs' / ('willingness-question-source-proof-' + name + '.json.gz')).read_bytes()) for name in ['original-native-closure', 'supplemental-pos-native-closure', 'original-installed-baseline']}
    return {
        'original_raw': original_raw,
        'source_raw': source_raw, 'source': json.loads(source_raw),
        'gold': read(fixtures / 'willingness-question-validity.json'),
        'boundaries': read(fixtures / 'willingness-question-boundaries.json'),
        'boundary_gold': read(fixtures / 'willingness-question-boundary-validity.json'),
        'native': read(fixtures / 'willingness-question-native.json'),
        'entries': read(fixtures / 'willingness-question-native-entries.json'),
        'original_native': proof('original-native-closure.json.gz'),
        'pos_native': read(fixtures / 'willingness-question-pos-native.json'),
        'original_pos': proof('supplemental-pos-native-closure.json.gz'),
        'baseline': proof('original-installed-baseline.json.gz'),
        'label': read(ROOT / 'web/src/grammar-labels.json')['-으련'],
    }


def inspect(v):
    assert sha(v['source_raw']) == 'd9cd3cc984bd14df26013928d99065161ec0739f6fd35cdcfb4c321330206bad', 'original authored source bytes'
    source = v['source']
    assert source == json.loads(v['source_raw']), 'original authored source fields'
    assert {name: sha(raw) for name, raw in v['original_raw'].items()} == {
        'original-native-closure': 'f78d6b1dfaea676dd5b320d7e5c657f1ed0feda36f8cb401c275cf6a56cb31ba',
        'supplemental-pos-native-closure': 'ec34e9638c1986b7f1aaf8f7c2c99e7aa94caa8a68b6e071011979c7cbb2c5f7',
        'original-installed-baseline': '4a5cbb4d83612c6fee6f021375a1d8ddc17a9e9f816173ba29d441bd0f2388c0',
    }, 'original Native and baseline archive bytes'
    assert source['ending_owner_ids'] == ['krdict:76564', 'krdict:76567'] and source['expression_owner_ids'] == ['krdict:86640', 'krdict:86631'], 'all four separate source owners'
    assert {ident: entry(raw) for ident, raw in source['original_lmf'].items()} == source['owners'], 'every original ending and expression Native field'
    assert len(source['source_exports']) == 11, 'all original source export hashes'
    items = source['items'] + source['separate_expression_groups']
    assert len(items) == 18 and len(source['items']) == 10, 'all original source groups'
    for item in items:
        owner = source['owners'][item['entry_id']]
        sense = next(s for s in owner['senses'] if s['id'] == item['sense_id'])
        assert item['complete_original_group'] == sense['examples'][item['example_group'] - 1], 'complete original group and dialogue bytes'
        raw, target = '\n'.join(item['complete_original_group']).encode(), item['surface'].encode()
        assert raw[item['local_span']['start']:item['local_span']['end']] == target, 'original target source span'
    assert len(v['gold']['cases']) == 10, 'all ten original ending cases'
    for case, item in zip(v['gold']['cases'], source['items'], strict=True):
        target = dict(item['typed_target'])
        target.update(required_rules=['ending.willingness_question'], source='original-willingness-ending-' + item['entry_id'].split(':')[1])
        assert case == {'id': item['id'], 'surface': item['surface'], 'judgments': [target]}, 'every independent source judgment unchanged'
    assert len(v['boundaries']) == len(v['boundary_gold']['cases']) == 12, 'all twelve authored boundary cases'
    for number, (case, boundary) in enumerate(zip(v['boundary_gold']['cases'], v['boundaries'], strict=True), 1):
        assert case['id'] == 'willingness-question-stem-boundary-' + str(number) and case['surface'] == boundary['surface'], 'original boundary case identity'
        judgments = case['judgments']
        assert len(judgments) == 1 and judgments[0]['lemmas'] == [boundary['lemma']] and judgments[0]['lemma_kinds'] == ['predicate'] and judgments[0]['morphemes'] == ['으련'] and judgments[0]['morpheme_kinds'] == ['ending'] and judgments[0]['required_rules'] == ['ending.willingness_question'], 'exact boundary path only'
        assert judgments[0]['verdict'] == ('required' if boundary['expected'] else 'forbidden') and judgments[0]['reason'] == boundary['reason'], 'original boundary verdict and reason'
    assert sum(case['judgments'][0]['verdict'] == 'required' for case in v['boundary_gold']['cases']) == 5, 'five required seven forbidden boundaries'
    projected = {entry(raw)['id']: entry(raw) for raw in array(v['native']['LexicalResource']['Lexicon']['LexicalEntry'])}
    originals = v['original_native']
    assert originals == json.loads(v['original_raw']['original-native-closure']), 'original Native archive fields'
    assert len(projected) == len(v['entries']) == len(originals['complete_imported_entries']) == 29, 'all twenty-nine original Native owners'
    assert projected == v['entries'] == originals['complete_imported_entries'] == {ident: entry(raw) for ident, raw in originals['original_native_entries'].items()}, 'every complete original Native field'
    assert all(projected[ident] == owner for ident, owner in source['owners'].items()), 'separate expression owners retained'
    pos = {entry(raw)['id']: entry(raw) for raw in array(v['pos_native']['LexicalResource']['Lexicon']['LexicalEntry'])}
    assert v['original_pos'] == json.loads(v['original_raw']['supplemental-pos-native-closure']), 'original supplemental POS archive fields'
    assert len(pos) == 1 and pos == v['original_pos']['complete_imported_entries'] and all(e['headword'] == '예쁘다' and e['pos'] == '형용사' for e in pos.values()), 'complete original supplemental adjective owner'
    label = v['label']
    assert label['kind'] == 'ending' and label['sources'] == [{'id': 76564, 'headword': '-련', 'pos': '어미'}, {'id': 76567, 'headword': '-으련', 'pos': '어미'}], 'label does not borrow expression ownership'
    baseline = v['baseline']
    assert baseline['state'] == 'complete-original-baseline-observed' and baseline['inputs_unchanged'] and len(baseline['runs']) == 24, 'complete prior installed baseline'
    policies = {(family, encoding, mode, cache) for family in ['complete-original-source', 'all-individual-targets'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]}
    assert {(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in baseline['runs']} == policies, 'all original Unicode filter cache policies'
    for run in baseline['runs']:
        assert run['exit_code'] == 0 and run['original_bytes_conserved'] and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'complete prior ordered output bytes'
        records = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(records) == run['records'] and len(run['observations']) == 18, 'all original baseline targets'
        for observation, item in zip(run['observations'], items, strict=True):
            assert observation['id'] == item['id'] and observation['entry_id'] == item['entry_id'] and observation['actual_record'] == records[observation['record_index']], 'complete original observed target'
            paths = observation['actual_record']['analysis']['analyses']
            proposed = item['typed_target']['lemmas'] if 'typed_target' in item else item['independent_lexical_proposal']
            lexical = [index for index, path in enumerate(paths) if [head['text'] for head in path['lemmas']] == proposed]
            typed = [index for index in lexical if [m['form'] for m in paths[index]['morphemes']] == ['으련']]
            assert lexical == observation['lexical_path_indices'] and lexical, 'prior lexical alternatives already present'
            assert typed == observation['typed_ending_path_indices'] == [], 'baseline decomposition gap is separate from lexical recall'
    assert baseline == json.loads(v['original_raw']['original-installed-baseline']), 'every original baseline field retained'
    return {'state': 'original-willingness-source-and-judgments-passed', 'source_groups': 18,
            'source_cases': 10, 'boundary_cases': 12, 'required': 15, 'forbidden': 7,
            'native_owners': 29, 'supplemental_pos_owners': 1, 'baseline_streams': 24,
            'contextual_review_complete': False, 'full_coverage_complete': False}


if __name__ == '__main__':
    print(inspect(inputs()))
