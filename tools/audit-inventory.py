#!/usr/bin/env python3
"""Offline triage, not a grammar coverage or precision score.

Consume fresh version-2 evaluator reports (never overwrite frozen baselines).
Inventory dictionary grammar entries against literal mentions in source tables;
cluster remaining misses by the annotated trailing grammar, with stable IDs.
Run from the repository root. See docs/inventory-audit.md.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sqlite3


def sha(data):
    return hashlib.sha256(data).hexdigest()


def literals(source):
    return set(re.findall(r'"([^"\n]*)"', source))


def corpus_rows(path):
    rows = {}
    sent = None
    ordinal = 0
    active = False
    for line in path.read_text().splitlines():
        if not line:
            sent = None
            active = False
            continue
        if not active:
            ordinal += 1
            active = True
        if line.startswith('# sent_id = '):
            sent = line.removeprefix('# sent_id = ')
        if line.startswith('#'):
            continue
        cols = line.split('\t')
        if len(cols) != 10 or not cols[0].isdigit():
            continue
        key = f'id:{sent}/{cols[0]}' if sent else f'ordinal:{ordinal}/{cols[0]}'
        if key in rows:
            raise ValueError(f'duplicate corpus ID: {key}')
        rows[key] = cols
    return rows


def cluster(cols):
    lemma = cols[2]
    for field in cols[9].split('|'):
        if field.startswith('OrigLemma='):
            lemma = field.removeprefix('OrigLemma=')
    forms, tags = lemma.split('+'), cols[4].split('+')
    if len(forms) != len(tags):
        return 'alignment-review'
    tail = []
    for form, tag in reversed(list(zip(forms, tags))):
        if tag.lower().startswith(('e', 'j')):
            tail.append(f'{form}/{tag}')
        else:
            break
    # These are annotation signatures, not asserted causes of a miss.
    prefix = 'auxiliary|' if any(t in ('px', 'VX') for t in tags) else ''
    return prefix + ('+'.join(reversed(tail)) or 'lexical-or-derivational')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dictionary', type=Path, required=True)
    parser.add_argument('--report', type=Path, action='append', required=True)
    args = parser.parse_args()
    grammar = Path('src/grammar.rs').read_text()
    engine = Path('src/engine.rs').read_text()
    mentions = {
        '어미': literals(grammar.split('fn endings()')[1].split('/// A reverse trie')[0]),
        '조사': literals(grammar.split('fn particles()')[1].split('fn particle_matches')[0]),
        '보조 동사': literals(engine.split('fn aux_allowed(')[1].split('#[derive')[0]),
        '보조 형용사': literals(engine.split('fn aux_allowed(')[1].split('#[derive')[0]),
    }
    inventory = []
    with sqlite3.connect(args.dictionary.resolve().as_uri() + '?mode=ro', uri=True) as db:
        metadata = dict(db.execute('SELECT key,value FROM metadata'))
        for ident, headword, pos in db.execute(
            "SELECT id,headword,pos FROM entries WHERE pos IN "
            "('어미','조사','보조 동사','보조 형용사') ORDER BY pos,headword,id"
        ):
            form = headword.strip('-')
            if pos.startswith('보조 '):
                form = form.removesuffix('다')
            inventory.append(dict(id=ident, headword=headword, pos=pos,
                                  literal_mention=form in mentions[pos]))
    reports = []
    for path in args.report:
        raw = path.read_bytes()
        records = [json.loads(line) for line in raw.splitlines()]
        summary, cases = records[0], records[1:]
        if summary['schema_version'] != 2:
            raise ValueError('expected a version-2 case report')
        source = Path(summary['input'])
        if sha(source.read_bytes()) != summary['input_sha256']:
            raise ValueError(f'corpus hash mismatch: {source}')
        if len(cases) != summary['converted_rows'] or len({c['id'] for c in cases}) != len(cases):
            raise ValueError(f'incomplete or duplicate cases: {path}')
        if sum(c['matched'] for c in cases) != summary['grouped_matches']:
            raise ValueError(f'inconsistent match count: {path}')
        rows = corpus_rows(source)
        groups = defaultdict(list)
        for case in cases:
            if not case['matched']:
                cols = rows[case['id']]
                if cols[1] != case['surface']:
                    raise ValueError(f'surface mismatch: {case["id"]}')
                groups[cluster(cols)].append({k: case[k] for k in ('id', 'surface', 'expected')})
        reports.append(dict(
            corpus=summary['corpus'], input=str(source), input_sha256=summary['input_sha256'],
            report_sha256=sha(raw), converted=len(cases), matched=summary['grouped_matches'],
            misses=sum(map(len, groups.values())),
            clusters=[dict(signature=k, count=len(v), cases=v)
                      for k, v in sorted(groups.items(), key=lambda p: (-len(p[1]), p[0]))],
        ))
    print(json.dumps(dict(
        schema_version=1,
        interpretation='Literal mentions are triage hints, not implemented coverage. '
                       'Allomorphs, homonyms, composition and attachment require review. '
                       'Corpus clusters are annotation signatures, not verified error causes.',
        source_sha256={p: sha(Path(p).read_bytes()) for p in
                       ('src/grammar.rs', 'src/engine.rs', 'tools/audit-inventory.py')},
        dictionary_metadata=metadata,
        dictionary_counts=dict(Counter(e['pos'] for e in inventory)),
        dictionary_inventory=inventory, reports=reports,
    ), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
