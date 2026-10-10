"""Verify untouched -려니와/-으려니와 sources and the complete unjudged baseline."""
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
OWNERS = {
    'krdict:86083': '53e025f1777baaa6210d99fcef31db9d764bacdc929d2a69855de9d65fd28ff2',
    'krdict:86084': '7af5bea878be4857ce61a9c12765ccaf7932cea0d37bc88ad744aafbeda03c86',
}
TARGETS = [
    ('어두워지려니와', ['어둡다', '지다']), ('고생이려니와', ['고생', '이다']),
    ('상쾌하려니와', ['상쾌하다']), ('따가우려니와', ['따갑다']),
    ('처리하려니와', ['처리하다']), ('떠나려니와', ['떠나다']),
    ('출발하려니와', ['출발하다']), ('하려니와', ['하다']),
    ('같으려니와', ['같다']), ('않으려니와', ['않다']),
    ('받으려니와', ['받다']), ('괜찮으려니와', ['괜찮다']),
    ('사랑했으려니와', ['사랑하다']), ('맞으려니와', ['맞다']),
    ('주겠으려니와', ['주다']), ('하겠으려니와', ['하다']),
]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def inspect(packet, report, native):
    assert packet['state'] == 'complete-original-conjectural-additive-sources-verified-before-probe' and packet['inputs_unchanged'], 'complete frozen original source preparation'
    assert list(packet['source_entries']) == list(OWNERS), 'original separate ending identities'
    for ident, expected in OWNERS.items():
        owner = packet['source_entries'][ident]
        assert sha(json.dumps(owner, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()) == expected, 'all original dictionary fields'
    groups = []
    for owner in packet['source_entries'].values():
        for sense in owner['senses']:
            for ordinal, lines in enumerate(sense['examples']):
                groups.append({
                    'id': f"conjectural-additive-{owner['id'].split(':')[1]}-sense-{sense['id']}-group-{ordinal+1}",
                    'source_entry_id': owner['id'], 'source_headword': owner['headword'],
                    'sense_id': sense['id'], 'group_ordinal': ordinal,
                    'complete_original_group': lines, 'source_notes': owner['notes'],
                    'sense_notes': sense['notes'], 'definition': sense['definition'],
                })
    assert len(groups) == 16 and groups == packet['complete_groups'], 'all complete original groups'
    assert len(packet['independent_proposals']) == 16, 'all original proposed occurrences'
    assert packet['complete_source_text'] == '\n'.join(line for group in groups for line in group['complete_original_group']), 'all original source text'
    for group, proposal, (surface, lemmas) in zip(groups, packet['independent_proposals'], TARGETS, strict=True):
        assert all(proposal[key] == value for key, value in group.items()), 'original occurrence identity and context'
        assert (proposal['surface'], proposal['proposed_lemmas']) == (surface, lemmas), 'independently authored target lemmas'
        assert proposal['verdict'] == 'proposed-before-probe', 'proposals are not reviewed path judgments'
        raw = '\n'.join(group['complete_original_group']).encode()
        assert raw.count(surface.encode()) == 1 and proposal['surface_byte_offset'] == raw.index(surface.encode()), 'original target byte position'
        assert all(packet['complete_lexical_entries'][word] for word in lemmas), 'original lexical owners retained'
    assert native['state'] == 'complete-original-native-owner-closure-preserved', 'complete original Native preparation'
    expected = dict(packet['source_entries'])
    for owners in packet['complete_lexical_entries'].values():
        for owner in owners:
            if owner['lexical_unit'] == '단어':
                expected[owner['id']] = owner
    assert native['owners'] == len(expected) == 34 and set(native['original_native_entries']) == set(expected), 'all original Native identities'
    assert native['complete_imported_entries'] == expected and {ident: entry(value) for ident, value in native['original_native_entries'].items()} == expected, 'every exact Native projection field'
    assert len(native['original_exports']) == 11 and {ident for value in native['original_exports'].values() for ident in value['ids']} == set(expected), 'all original Native exports'
    assert report['state'] == 'complete-before-observation-passed' and report['inputs_unchanged'], 'terminal frozen baseline observation'
    for record in [packet, report, native]:
        assert sha(record['producer']['text'].encode()) == record['producer']['sha256'], 'actual source and capture producers'
    keys = [(family, encoding, mode, cache) for family in ['complete-original-source', 'all-proposed-targets']
            for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]]
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in report['runs']] == keys, 'complete original Unicode filter cache workloads'
    cached = {}
    recovered = 0
    for run in report['runs']:
        originals = ['\n'.join(group['complete_original_group']) for group in groups] if run['family'] == 'complete-original-source' else [surface for surface, _ in TARGETS]
        text = ('\n' if run['family'] == 'complete-original-source' else ' ').join(originals)
        original = unicodedata.normalize(run['encoding'], text).encode()
        assert sha(original) == run['input_sha256'], 'complete original baseline input'
        assert run['exit_code'] == 0 and run['original_bytes_conserved'] and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'complete successful baseline output'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == run['records'], 'all original baseline frames'
        cursor = 0
        for row in rows:
            assert row['span']['start'] == cursor, 'original byte continuity'
            cursor = row['span']['end']
            assert original[row['span']['start']:cursor].decode() == row['surface'], 'original source byte ownership'
        assert cursor == len(original), 'all original source bytes'
        command = run['command']
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        assert command[0] in report['frozen_inputs'] and command[1:4] == ['text', '-', '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == [*flags, '--cache-bytes', str(run['cache_bytes'])], 'actual baseline filter and cache command'
        key = (run['family'], run['encoding'], run['mode'])
        if key in cached:
            assert cached[key] == run['jsonl'], 'exact cache parity'
        cached[key] = run['jsonl']
        observed = []
        offset = 0
        for group, proposal in zip(originals, packet['independent_proposals'], strict=True):
            raw = unicodedata.normalize(run['encoding'], group).encode()
            target = unicodedata.normalize(run['encoding'], proposal['surface']).encode()
            position = offset + raw.index(target)
            offset += len(raw) + 1
            index, row = next((i, r) for i, r in enumerate(rows) if r['span']['start'] == position)
            assert row['surface'].encode() == target, 'original observed target occurrence'
            paths = (row.get('analysis') or {}).get('analyses', [])
            indices = [i for i, path in enumerate(paths) if [lemma['text'] for lemma in path['lemmas']] == proposal['proposed_lemmas']]
            observed.append({'id': proposal['id'], 'record_index': index, 'proposed_lemma_indices': indices, 'verdict': 'unjudged'})
            recovered += bool(indices)
        assert observed == run['observed_proposals'], 'independently rederived unjudged observations'
    return {'owners': 2, 'senses': 4, 'groups': 16, 'native_owners': 34, 'streams': 24,
            'frames': sum(r['records'] for r in report['runs']), 'proposed_occurrence_checks': 384,
            'proposed_lemma_groups_found': recovered, 'full_coverage_complete': False}


def inputs():
    return (read(ROOT / 'docs/conjectural-additive-source-preparation.json.gz'),
            read(ROOT / 'docs/conjectural-additive-before-streams.json.gz'),
            read(ROOT / 'docs/conjectural-additive-original-native-closure.json.gz'))


if __name__ == '__main__':
    print(inspect(*inputs()))
