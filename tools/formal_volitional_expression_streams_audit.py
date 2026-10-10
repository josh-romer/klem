"""Rederive original expression paths, byte spans and cache parity from complete captures."""
import hashlib
import json
import unicodedata

import formal_volitional_expression_audit as source_audit

ROOT = source_audit.ROOT
read = source_audit.read
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inspect(packet, suite, report):
    source = source_audit.inspect(packet, suite)
    assert report['state'] == 'passed' and report['inputs_unchanged'], 'terminal frozen stream capture'
    assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual stream producer'
    keys = [(family, encoding, mode, cache) for family in ['complete-original-source', 'all-individual-cases']
            for encoding in ['NFC', 'NFD'] for mode in ['raw', 'headword', 'compatible'] for cache in [0, 4096]]
    assert [(r['family'], r['encoding'], r['mode'], r['cache_bytes']) for r in report['runs']] == keys, 'all complete Unicode filter cache streams'
    previous = {}
    for run in report['runs']:
        family, encoding = run['family'], run['encoding']
        groups = ['\n'.join(g['complete_original_group']) for g in packet['complete_groups']] if family == 'complete-original-source' else [c['surface'] for c in suite['cases']]
        text = ('\n' if family == 'complete-original-source' else ' ').join(groups)
        original = unicodedata.normalize(encoding, text).encode()
        assert sha(original) == run['input_sha256'], 'complete original input'
        assert run['exit_code'] == 0 and run['original_bytes_conserved'] and sha(run['jsonl'].encode()) == run['jsonl_sha256'], 'complete successful output'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert len(rows) == run['records'], 'complete frame count'
        cursor = 0
        for row in rows:
            assert row['span']['start'] == cursor, 'original span continuity'
            cursor = row['span']['end']
            assert original[row['span']['start']:cursor].decode() == row['surface'], 'original byte ownership'
        assert cursor == len(original), 'all original input bytes'
        key = (family, encoding, run['mode'])
        if key in previous:
            assert previous[key] == run['jsonl'], 'exact cache output parity'
        previous[key] = run['jsonl']
        flags = {'raw': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}[run['mode']]
        command = run['command']
        assert command[0] in report['frozen_inputs'] and command[1:4] == ['text', '-', '--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == [*flags, '--cache-bytes', str(run['cache_bytes'])], 'actual filter cache command'
        matched = []
        group_offset = 0
        for group, case in zip(groups, suite['cases'], strict=True):
            raw = unicodedata.normalize(encoding, group).encode()
            target = unicodedata.normalize(encoding, case['surface']).encode()
            position = group_offset + raw.index(target)
            group_offset += len(raw) + 1
            found = [(i, row) for i, row in enumerate(rows) if row['span']['start'] == position]
            assert len(found) == 1 and found[0][1]['surface'].encode() == target, 'exact original target occurrence'
            index, row = found[0]
            judgment = case['judgments'][0]
            paths = row['analysis']['analyses']
            indices = [i for i, path in enumerate(paths)
                       if [l['text'] for l in path['lemmas']] == judgment['lemmas']
                       and [l['kind'] for l in path['lemmas']] == judgment['lemma_kinds']
                       and [m['form'] for m in path['morphemes']] == judgment['morphemes']
                       and [m['kind'] for m in path['morphemes']] == judgment['morpheme_kinds']
                       and set(judgment['required_rules']) <= set(path['rules'])]
            assert indices, 'every independently authored expression path'
            matched.append({'case_id': case['id'], 'record_index': index, 'analysis_indices': indices})
        assert run['matched_independent_targets'] == matched, 'all independently rederived target occurrences'
    return {**source, 'streams': len(report['runs']), 'frames': sum(run['records'] for run in report['runs']),
            'target_checks': len(report['runs']) * 8}


def inputs():
    return (*source_audit.inputs(), read(ROOT / 'docs/formal-volitional-expression-source-streams.json.gz'))


if __name__ == '__main__':
    print(inspect(*inputs()))
