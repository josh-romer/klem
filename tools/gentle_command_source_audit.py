"""Verify independently authored gentle-command paths and complete original owners."""
import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inputs():
    fixtures, docs = ROOT / 'tests/fixtures', ROOT / 'docs'
    proof = lambda name: gzip.decompress((docs / ('gentle-command-proof-' + name + '.gz')).read_bytes())
    raw = {name: proof(name) for name in ['gentle-command-original-source.json', 'gentle-command-installed-baseline.json', 'gentle-command-original-native-closure.json', 'gentle-command-boundary-native-closure.json']}
    return {'raw': raw, 'source_raw': (fixtures / 'gentle-command-source.json').read_bytes(),
            'suite_raw': (fixtures / 'gentle-command-validity.json').read_bytes(),
            'source': json.loads(raw['gentle-command-original-source.json']),
            'suite': json.loads((fixtures / 'gentle-command-validity.json').read_bytes()),
            'closures': [json.loads(raw[name]) for name in ['gentle-command-original-native-closure.json', 'gentle-command-boundary-native-closure.json']],
            'native': [json.loads((fixtures / name).read_bytes()) for name in ['gentle-command-native.json', 'gentle-command-boundary-native.json']],
            'entries': [json.loads((fixtures / name).read_bytes()) for name in ['gentle-command-native-entries.json', 'gentle-command-boundary-native-entries.json']],
            'ending_native': json.loads((fixtures / 'gentle-command-ending-native.json').read_bytes()),
            'baseline': json.loads(raw['gentle-command-installed-baseline.json']),
            'label': json.loads((ROOT / 'web/src/grammar-labels.json').read_bytes())['-으렴']}


def inspect(v):
    assert {name: sha(raw) for name, raw in v['raw'].items()} == {
        'gentle-command-original-source.json': 'fc42b29d511ee3fe53c19006c5d6581d61763e5a2a162768ff221eb079db80c0',
        'gentle-command-installed-baseline.json': '118ea2cea4de2de7aac44702c6663d98f0ef6f1ec9013747cae07a82ca25e16d',
        'gentle-command-original-native-closure.json': 'b51486294830f542314fd48a9b28a3fb62b397caf192d6416bd561f232f09073',
        'gentle-command-boundary-native-closure.json': 'ae1595bf159d670f0b12e9f5c50abc1a858d69444da616c48e8975c6a0e52aae',
    }, 'exact original source Native and installed baseline bytes'
    assert v['source_raw'] == v['raw']['gentle-command-original-source.json'], 'exact source fixture retained'
    assert sha(v['suite_raw']) == 'bd886ed1a45ebcf67e2cfbc3e123f33ca3f0cb33b449cc88a99f58bab6b21fb7', 'exact independently authored private judgments'
    source, suite = v['source'], v['suite']
    assert source == json.loads(v['source_raw']), 'original source fields retained'
    assert suite == json.loads(v['suite_raw']), 'original private judgment fields retained'
    assert source['ending_owner_ids'] == ['krdict:79340', 'krdict:79343'] and source['expression_homonyms_seen'] == [], 'both separate original ending owners'
    assert not source['observed_runtime'] and not source['linguistic_judgments_promoted'], 'source proposals precede runtime observation'
    merged = {}
    for closure, native, expected in zip(v['closures'], v['native'], v['entries'], strict=True):
        originals = closure['original_native_entries']
        assert len(closure['original_exports']) == 11, 'all original Native exports retained'
        assert {ident: entry(raw) for ident, raw in originals.items()} == closure['complete_imported_entries'] == expected, 'every original imported Native field'
        assert native['LexicalResource']['Lexicon']['LexicalEntry'] == list(originals.values()), 'every original Native fixture field and order'
        assert not merged.keys() & expected.keys(), 'separate Native closure identities'
        merged.update(expected)
    assert [len(e) for e in v['entries']] == [40, 7] and len(merged) == 47, 'all forty-seven complete original owners'
    assert {ident: merged[ident] for ident in source['ending_owner_ids']} == source['owners'], 'both source owners retain complete Native fields'
    assert v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'] == [v['closures'][0]['original_native_entries'][ident] for ident in source['ending_owner_ids']], 'offline catalog imports both exact ending owners'
    items = source['items']
    assert len(items) == 8 and len(suite['cases']) == 23, 'all source groups and independently authored cases'
    for item, case in zip(items, suite['cases'][:8], strict=True):
        owner = source['owners'][item['entry_id']]
        sense = next(s for s in owner['senses'] if s['id'] == item['sense_id'])
        assert item['complete_original_group'] == sense['examples'][item['example_group'] - 1], 'complete original source groups and dialogue'
        raw = '\n'.join(item['complete_original_group']).encode()
        assert raw[item['local_span']['start']:item['local_span']['end']].decode() == item['surface'], 'original source target byte span'
        expected = dict(item['independent_typed_proposal'], id='lexical-path', verdict='required', required_rules=['ending.gentle_command'], source='gentle-command-' + item['entry_id'].split(':')[1])
        assert case['id'] == item['id'] and case['surface'] == item['surface'] and len(case['judgments']) == 1 and all(case['judgments'][0][key] == value for key, value in expected.items()), 'all independently proposed source paths retained'
    counts = {kind: sum(j['verdict'] == kind for case in suite['cases'] for j in case['judgments']) for kind in ['required', 'forbidden']}
    assert counts == {'required': 15, 'forbidden': 8}, 'all independent required and forbidden paths'
    label = v['label']
    assert label['kind'] == 'ending' and label['sources'] == [{'id': 79340, 'headword': '-렴', 'pos': '어미'}, {'id': 79343, 'headword': '-으렴', 'pos': '어미'}], 'label cites its original ending owners'
    baseline = v['baseline']
    assert baseline == json.loads(v['raw']['gentle-command-installed-baseline.json']), 'every original installed observation retained'
    assert baseline['state'] == 'complete-original-installed-baseline-observed' and baseline['inputs_unchanged'] and not baseline['linguistic_judgments_promoted'], 'complete original baseline scope'
    expected_policies = {(family, encoding, mode, cache) for family in ['complete-source', 'individual-targets'] for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]}
    assert len(baseline['runs']) == 24 and {(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in baseline['runs']} == expected_policies, 'all original Unicode filter and cache policies'
    for run in baseline['runs']:
        assert run['exit_code'] == 0 and run['original_bytes_conserved'] and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'every complete original installed output byte'
        frames = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(frames) == run['records'] and len(run['observations']) == 8, 'all original baseline source observations'
        for observation, item in zip(run['observations'], items, strict=True):
            assert observation['id'] == item['id'] and observation['actual_record'] == frames[observation['record_index']], 'original complete observed record'
            paths = observation['actual_record']['analysis']['analyses']
            lexical = [i for i, p in enumerate(paths) if [h['text'] for h in p['lemmas']] == item['independent_typed_proposal']['lemmas']]
            assert lexical == observation['lexical_path_indices'] == [] and observation['typed_ending_path_indices'] == [], 'original observed lemma and decomposition gap'
    assert sum(r['records'] for r in baseline['runs']) == 1620, 'all original baseline frames'
    return {'state': 'original-gentle-command-source-and-judgments-passed', 'source_groups': 8, 'cases': 23, **counts, 'native_owners': 47, 'baseline_streams': 24, 'baseline_frames': 1620, 'prior_lexical_proposals_present': 0, 'contextual_and_independent_review': 'pending', 'full_coverage_complete': False}


if __name__ == '__main__':
    print(inspect(inputs()))
