#!/usr/bin/env python3
"""Persistent KRDict review queue; evidence links never imply complete coverage.

Generate with --dictionary PATH; verify the committed queue offline with --verify.
Both operations validate manual reviews against current evidence. Verification
without a dictionary checks stored source integrity, not the upstream snapshot.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
POSITIONS = ('어미', '조사', '보조 동사', '보조 형용사')
REVIEWS = 'docs/inventory-reviews.json'
QUEUE = 'docs/inventory-review-queue.json'
CATALOG = 'web/src/grammar-labels.json'
LEDGER = 'tests/fixtures/validity.json'
AUXILIARIES = 'docs/auxiliary-inventory.json'


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read(root, path):
    return json.loads((root / path).read_text(encoding='utf-8'))


def source_entry(data):
    """Keep every sense and attachment note, with two example groups per sense."""
    entry = {k: data[k] for k in ('id', 'headword', 'homonym', 'pos', 'url',
                                  'lexical_unit', 'notes', 'forms')}
    entry['senses'] = [dict(
        id=s['id'], definition=s['definition'], notes=s['notes'],
        patterns=s['patterns'], examples=s['examples'][:2],
        total_example_groups=len(s['examples']),
    ) for s in data['senses']]
    return entry


def dictionary_entries(path):
    with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
        metadata = dict(db.execute('SELECT key,value FROM metadata'))
        entries = []
        for ident, headword, pos, raw in db.execute(
            'SELECT id,headword,pos,data FROM entries WHERE pos IN (?,?,?,?)', POSITIONS
        ):
            data = json.loads(raw)
            if (ident, headword, pos) != (data['id'], data['headword'], data['pos']):
                raise ValueError(f'dictionary index mismatch: {ident}')
            entries.append(source_entry(data))
    return metadata, entries


def source_id(url):
    parsed = urlparse(url)
    if parsed.hostname != 'krdict.korean.go.kr':
        return None
    ids = parse_qs(parsed.query).get('ParaWordNo', [])
    return f'krdict:{ids[0]}' if len(ids) == 1 and ids[0].isdigit() else None


def evidence_file(root, path):
    if Path(path).is_absolute() or '..' in Path(path).parts:
        raise ValueError(f'evidence must be a repository-relative path: {path}')
    return (root / path).read_bytes()


def build_queue(root, metadata, entries):
    entries = sorted(entries, key=lambda e: (e['pos'], e['headword'], e['id']))
    indexed = {e['id']: e for e in entries}
    if len(indexed) != len(entries):
        raise ValueError('duplicate source entry ID')
    if any(e['pos'] not in POSITIONS or source_id(e['url']) != e['id'] for e in entries):
        raise ValueError('invalid inventory source identity or POS')

    catalog = defaultdict(list)
    for form, label in read(root, CATALOG).items():
        for source in label['sources']:
            ident = f"krdict:{source['id']}"
            if ident in indexed:
                entry = indexed[ident]
                if (entry['headword'], entry['pos']) != (source['headword'], source['pos']):
                    raise ValueError(f'catalog identity mismatch: {ident}')
                catalog[ident].append(dict(form=form, kind=label['kind']))

    ledger = read(root, LEDGER)
    judgments = {}
    citations = defaultdict(list)
    case_ids = set()
    for case in ledger['cases']:
        if case['id'] in case_ids:
            raise ValueError(f'duplicate case: {case["id"]}')
        case_ids.add(case['id'])
        for judgment in case['judgments']:
            key = (case['id'], judgment['id'])
            if key in judgments:
                raise ValueError(f'duplicate judgment: {key}')
            url = ledger['sources'][judgment['source']]
            ident = source_id(url)
            judgments[key] = ident
            citations[ident].append(dict(case=case['id'], judgment=judgment['id'],
                                        verdict=judgment['verdict']))

    aux = {e['id']: e for e in read(root, AUXILIARIES)['entries']}
    reviews = read(root, REVIEWS)
    if reviews['schema_version'] != 1:
        raise ValueError('unsupported review schema')
    reviewed = {}
    evidence_paths = {REVIEWS, CATALOG, LEDGER, AUXILIARIES}
    for review in reviews['entries']:
        ident = review['id']
        if ident in reviewed:
            raise ValueError(f'duplicate review: {ident}')
        if ident not in indexed:
            raise ValueError(f'unknown reviewed entry: {ident}')
        if review['source_sha256'] != digest(indexed[ident]):
            raise ValueError(f'stale source review: {ident}')
        if review['status'] not in ('scoped', 'gap', 'deferred'):
            raise ValueError(f'invalid review status: {ident}')
        for field in ('scope', 'remaining', 'checklist', 'evidence'):
            if not review[field]:
                raise ValueError(f'missing review {field}: {ident}')
        checklist = evidence_file(root, 'docs/coverage-checklist.md').decode()
        for item in review['checklist']:
            if not re.search(r'\*\*' + re.escape(item) + r' —', checklist):
                raise ValueError(f'unknown checklist item: {item}')
        evidence_paths.add('docs/coverage-checklist.md')
        for ref in review['evidence']:
            content = evidence_file(root, ref['path']).decode()
            evidence_paths.add(ref['path'])
            if 'test' in ref and not re.search(
                r'\bfn\s+' + re.escape(ref['test']) + r'\s*\(', content
            ):
                raise ValueError(f'unknown Rust test: {ref}')
        if review['status'] == 'scoped' and not review['judgments']:
            raise ValueError(f'scoped review needs judgments: {ident}')
        for ref in review['judgments']:
            key = (ref['case'], ref['judgment'])
            if key not in judgments or judgments[key] != ident:
                raise ValueError(f'judgment does not cite reviewed entry: {ident}: {key}')
        reviewed[ident] = review

    rows = []
    for entry in entries:
        ident = entry['id']
        hints = []
        if ident in aux:
            previous = aux[ident]
            if any(entry[k] != previous[k] for k in ('headword', 'homonym', 'pos', 'notes')):
                raise ValueError(f'auxiliary inventory mismatch: {ident}')
            if previous['sense_notes'] != [dict(sense=s['id'], notes=s['notes'])
                                           for s in entry['senses']]:
                raise ValueError(f'auxiliary sense notes mismatch: {ident}')
            hints.append(AUXILIARIES)
        rows.append(dict(
            source=entry, source_sha256=digest(entry),
            catalog=sorted(catalog[ident], key=lambda c: (c['form'], c['kind'])),
            cited_judgments=sorted(citations[ident], key=lambda j: (j['case'], j['judgment'])),
            inventory_evidence=hints,
            review=reviewed.get(ident, {'status': 'unreviewed'}),
        ))
    return dict(
        schema_version=1,
        interpretation='Source inventory with evidence links, not a coverage or precision score. '
                       'Scoped reviews retain explicit limitations. Unreviewed means no manual '
                       'disposition in this ledger; it does not mean unimplemented. '
                       'Independent Korean-language review is pending.',
        attribution='National Institute of Korean Language, Korean Basic Dictionary. '
                    'Source notes and definitions retained; at most two example groups per sense.',
        license='CC BY-SA 2.0 KR',
        license_url='https://creativecommons.org/licenses/by-sa/2.0/kr/',
        dictionary_metadata=metadata,
        evidence_sha256={p: hashlib.sha256(evidence_file(root, p)).hexdigest()
                         for p in sorted(evidence_paths)},
        counts=dict(entries=len(rows), by_pos=dict(Counter(e['pos'] for e in entries)),
                    by_review=dict(Counter(r['review']['status'] for r in rows)),
                    with_catalog_links=sum(bool(r['catalog']) for r in rows),
                    with_judgment_citations=sum(bool(r['cited_judgments']) for r in rows)),
        entries=rows,
    )


def verify_queue(root, queue):
    if queue['schema_version'] != 1:
        raise ValueError('unsupported queue schema')
    for row in queue['entries']:
        if digest(row['source']) != row['source_sha256']:
            raise ValueError(f'stored source hash mismatch: {row["source"]["id"]}')
    rebuilt = build_queue(root, queue['dictionary_metadata'],
                          [row['source'] for row in queue['entries']])
    if rebuilt != queue:
        raise ValueError('stale queue: regenerate from the pinned dictionary')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dictionary', type=Path)
    mode.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        queue = read(ROOT, QUEUE)
        verify_queue(ROOT, queue)
        print(json.dumps(queue['counts'], ensure_ascii=False))
    else:
        metadata, entries = dictionary_entries(args.dictionary)
        print(json.dumps(build_queue(ROOT, metadata, entries), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
