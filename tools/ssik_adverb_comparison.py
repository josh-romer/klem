"""Check actual -씩 streams and invert every new path to a frozen raw parent."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unicodedata

from ssik_audit import ROOT, read
from ssik_adverb_audit import BASES, inspect as inspect_source


def parent_for(analysis, surface, originals):
    assert len(analysis['lemmas']) == 1
    assert analysis['lemmas'][0]['kind'] == 'adverbial'
    assert analysis['lemmas'][0]['text'] in BASES
    assert analysis['morphemes'][0] == {'form': '씩', 'kind': 'suffix'}
    assert sum(m == {'form': '씩', 'kind': 'suffix'} for m in analysis['morphemes']) == 1
    assert 'suffix.distributive.ssik' in analysis['rules']
    assert 'suffix.distributive.ssik.adverbial_base' in analysis['rules']
    parent = copy.deepcopy(analysis)
    parent['lemmas'][0]['kind'] = 'nominal'
    parent['rules'].remove('suffix.distributive.ssik.adverbial_base')
    assert parent in originals, (surface, analysis, parent)
    return parent, 0


def inspect(report):
    inspect_source()
    preflight = read('docs/ssik-adverb-preflight.json.gz')
    assert report['source_sha256'] == hashlib.sha256((ROOT / 'docs/ssik-adverb-preflight.json.gz').read_bytes()).hexdigest()
    assert report['fixture_sha256'] == hashlib.sha256((ROOT / 'tests/fixtures/ssik-adverb-sources.json').read_bytes()).hexdigest()
    assert report['before_cli_sha256'] == preflight['before_cli_sha256']
    assert report['dictionary_sha256'] == preflight['dictionary_sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    raw = [json.loads(line) for line in preflight['runs']['raw']['NFC-cached']['jsonl'].splitlines()]
    changes, parents = [], []
    assert set(report['runs']) == {'raw', 'headword', 'compatible'}
    for mode, runs in report['runs'].items():
        before = [json.loads(line) for line in preflight['runs'][mode]['NFC-cached']['jsonl'].splitlines()]
        assert set(runs) == {'NFC-cached', 'NFC-uncached', 'NFD-cached', 'NFD-uncached'}
        semantic = None
        for name, run in runs.items():
            assert run['exit_code'] == 0
            assert hashlib.sha256(run['jsonl'].encode()).hexdigest() == run['sha256']
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            assert ''.join(r['surface'] for r in rows) == unicodedata.normalize(name.split('-')[0], preflight['input'])
            offset = 0
            for row in rows:
                assert row['span'] == {'start': offset, 'end': offset + len(row['surface'].encode())}
                offset = row['span']['end']
            current = [(r.get('analysis'), r.get('dictionary')) for r in rows]
            if semantic is None:
                semantic = current
            else:
                assert current == semantic
        after = [json.loads(line) for line in runs['NFC-cached']['jsonl'].splitlines()]
        assert len(before) == len(after)
        added = words = 0
        for ordinal, (old, new) in enumerate(zip(before, after, strict=True)):
            assert (old['kind'], old['surface'], old['span']) == (new['kind'], new['surface'], new['span'])
            if new['kind'] != 'word':
                assert new == old
                continue
            words += 1
            original = old['analysis']['analyses']
            assert [a for a in new['analysis']['analyses'] if a in original] == original
            old_flat = old['dictionary']['lemmas']
            assert [l for l in new['dictionary']['lemmas'] if l['lemma'] in [x['lemma'] for x in old_flat]] == old_flat
            for index, analysis in enumerate(new['analysis']['analyses']):
                reading = new['dictionary']['readings'][index]
                if analysis in original:
                    assert reading == old['dictionary']['readings'][original.index(analysis)]
                    continue
                identity = hashlib.sha256(json.dumps([mode, ordinal, analysis], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
                change = {'id': 'ssik-adverb-change-' + identity, 'mode': mode, 'record_index': ordinal, 'surface': new['surface'], 'analysis': analysis, 'reading': reading, 'original_analyses': original, 'contextual_verdict': 'unjudged', 'independent_review': 'pending'}
                changes.append(change)
                parent, mi = parent_for(analysis, new['surface'], raw[ordinal]['analysis']['analyses'])
                parents.append({'id': change['id'], 'before_raw_parent': parent, 'parent_retained_in_filter': parent in original, 'quantity_morpheme_index': mi, 'quantity_base_hypothesis': analysis['lemmas'][0], 'base_class_scope': 'Conditional source-listed adverb base; no contextual POS or word-class change inferred', 'source_entry': 'krdict:72043', 'source_sense_ids': ['1'], 'contextual_verdict': 'unjudged', 'independent_review': 'pending'})
                added += 1
        assert report['statistics'][mode] == {'records': len(after), 'word_records': words, 'added_candidates': added}
    assert report['changes'] == changes
    return parents


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, default=ROOT / 'docs/ssik-adverb-diagnostics.json.gz')
    args = parser.parse_args()
    report = json.loads(gzip.decompress(args.report.read_bytes()))
    parents = inspect(report)
    receipt = read('docs/ssik-adverb-parent-checks.json.gz')
    assert receipt['diagnostics_sha256'] == hashlib.sha256(args.report.read_bytes()).hexdigest()
    assert receipt['source_sha256'] == report['source_sha256']
    assert receipt['parents'] == parents
    print('Verified complete twelve-stream preservation and exact raw-parent inversion for', len(parents), 'new paths.')
