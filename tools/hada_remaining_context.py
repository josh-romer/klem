"""Verify contextual suffix parents using the unchanged frozen raw readings."""
import argparse
import copy
import hashlib
import json

import hada_remaining_audit as audit

REPORT = audit.ROOT / 'docs/hada-remaining-context-checks.json.gz'


def filtered(record, mode):
    result = copy.deepcopy(record)
    if not result.get('analysis') or mode == 'raw':
        return result
    annotation = result['dictionary']
    retained, readings = [], []
    for analysis, reading in zip(result['analysis']['analyses'], annotation['readings'], strict=True):
        if not all(any(m['lemma'] == lemma and m['entries'] for m in annotation['lemmas']) for lemma in analysis['lemmas']):
            continue
        if mode == 'compatible' and reading['status'] == 'incompatible':
            continue
        retained.append(analysis)
        readings.append(reading)
    result['analysis']['analyses'] = retained
    annotation['readings'] = readings
    annotation['lemmas'] = [m for m in annotation['lemmas'] if any(m['lemma'] in a['lemmas'] for a in retained)]
    return result


def inspect(report):
    source, fixture = audit.read(audit.SOURCE), audit.read(audit.FIXTURE)
    original = fixture['context_before']
    assert report['fixture_sha256'] == audit.sha(audit.FIXTURE)
    assert report['before_cli_sha256'] == source['before_cli_sha256']
    assert report['after_cli_sha256'] == audit.read(audit.REPORT)['cli_sha256']
    assert report['words'] == original['words'] and len(report['words']) == 17
    assert report['input'] == ' '.join(original['words'])
    records, _ = audit.word_records(original['jsonl'])
    for mode, run in report['before'].items():
        assert run['exit_code'] == 0 and hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
        actual, _ = audit.word_records(run['jsonl'])
        assert actual == [filtered(r, mode) for r in records]
    enriched = copy.deepcopy(report)
    enriched['source_sha256'] = audit.sha(audit.SOURCE)
    enriched['addition_counts'], enriched['changed_surfaces'], enriched['retained_readings'] = {}, {}, {}
    for mode, runs in report['runs'].items():
        _, before = audit.word_records(report['before'][mode]['jsonl'])
        _, after = audit.word_records(runs['NFC-cached']['jsonl'])
        counts = {w: len(a['analysis']['analyses']) - len(before[w]['analysis']['analyses']) for w, a in after.items()}
        enriched['addition_counts'][mode] = sum(counts.values())
        enriched['changed_surfaces'][mode] = [w for w in after if counts[w]]
        enriched['retained_readings'][mode] = sum(len(a['analysis']['analyses']) for a in before.values())
    changes, fields = audit.inspect_comparison(source, enriched, baselines=report['before'], input_text=report['input'])
    assert enriched['addition_counts'] == {'raw':52, 'headword':13, 'compatible':13}
    assert fields == []
    return changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', required=True)
    parser.add_argument('--report', default=str(REPORT))
    args = parser.parse_args()
    print('Verified 17 contexts and', len(inspect(audit.read(args.report))), 'source-parent additions across twelve streams.')
