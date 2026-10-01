#!/usr/bin/env python3
"""Record every native sense-3 noun-forming -이 review item without assigning gold.

Combines the preserved discovery snapshot and explicit primary-source review
plan with current read-only dictionary/CLI probes. Writes JSON to stdout; never
changes the candidate ledger, dictionary, corpus annotations or baselines.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs/nominal-i-base-review-plan.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def heads(db, word):
    result = []
    for ident, head, pos, raw in db.execute(
            'SELECT id,headword,pos,data FROM entries WHERE headword=? ORDER BY id',
            (word,)):
        entry = json.loads(raw)
        result.append(dict(
            id=ident, headword=head, pos=pos,
            data_sha256=hashlib.sha256(raw.encode()).hexdigest(),
            senses=[dict(id=sense['id'], definition=sense['definition'],
                         notes=sense['notes']) for sense in entry['senses']]))
    return result


def audit(cli, dictionary, revision):
    plan = read(PLAN)
    discovery_path = ROOT / plan['historical_discovery']
    if digest(discovery_path) != plan['historical_discovery_sha256']:
        raise ValueError('historical discovery snapshot differs from the review plan')
    discovery = read(discovery_path)
    source = discovery['source']
    if digest(ROOT / source['native_fixture']) != source['native_fixture_sha256']:
        raise ValueError('native source fixture differs from the discovery snapshot')
    native = [row for row in discovery['forms'] if row['sense_id'] == '3']
    expected = {row['id']: row for row in native}
    if len(expected) != 30 or len(plan['forms']) != 30:
        raise ValueError('review must retain all thirty native sense-3 examples')
    if {row['discovery_id'] for row in plan['forms']} != set(expected):
        raise ValueError('review IDs do not cover the native source')
    partition = [word for batch in plan['planned_batches'] for word in batch['forms']]
    if Counter(partition) != Counter(row['surface'] for row in native):
        raise ValueError('planned batches must partition every native example once')
    references = {'krdict:88924-s3'} | {
        item['id'] for item in plan['primary_consultations']}
    for row in plan['forms']:
        if row['surface'] != expected[row['discovery_id']]['surface']:
            raise ValueError('review surface differs from original source group')
        if not set(row['primary_basis']) <= references:
            raise ValueError('unknown primary-source reference')
        if not any(row['surface'] in batch['forms']
                   and row['review_class'] == batch['review_class']
                   for batch in plan['planned_batches']):
            raise ValueError('review class differs from its planned batch')
    rows = []
    cli_hash = digest(cli)
    with sqlite3.connect(dictionary.resolve().as_uri() + '?mode=ro', uri=True) as db:
        metadata = dict(db.execute('SELECT key,value FROM metadata'))
        suffix = db.execute('SELECT data FROM entries WHERE id=?',
                            ('krdict:88924',)).fetchone()[0]
        if hashlib.sha256(suffix.encode()).hexdigest() != source['entry_data_sha256']:
            raise ValueError('dictionary noun-suffix entry differs from pinned source')
        for item in plan['forms']:
            original = expected[item['discovery_id']]
            word = item['surface']
            spellings = list(dict.fromkeys(
                [word, original['tail_removed_probe'], original['predicate_head_probe']]
                + item['additional_head_probes']))
            modes = []
            for mode, flag in [('raw', None), ('dict-only', '--dict-only'),
                               ('dict-compatible', '--dict-compatible')]:
                command = [str(cli), 'word', word, '--dictionary', str(dictionary)]
                if flag:
                    command.append(flag)
                output = json.loads(subprocess.check_output(command))
                modes.append(dict(
                    mode=mode, output=output,
                    noun_i_paths=sum('suffix.nominal.i' in a['rules']
                                     for a in output['analyses'])))
            rows.append(dict(
                **item, native_group=original['native_group'],
                head_probes=[dict(spelling=spelling, heads=heads(db, spelling))
                             for spelling in spellings],
                cli_modes=modes,
                judgment='unassigned; dictionary observations and review leads '
                'do not certify segmentation, base role or contextual sense'))
    if digest(cli) != cli_hash:
        raise ValueError('CLI changed while collecting the report')
    return dict(
        schema_version=1, checklist=plan['checklist'], revision=revision,
        status='All thirty native sense-3 examples remain open. Primary '
        'relationships and conflicts refine the implementation plan without '
        'assigning candidate judgments or choosing a theoretical analysis.',
        scope=plan['scope'], source=source,
        plan=dict(path=str(PLAN.relative_to(ROOT)), sha256=digest(PLAN)),
        historical_discovery=dict(path=plan['historical_discovery'],
                                  sha256=plan['historical_discovery_sha256']),
        dictionary_metadata=metadata,
        cli=dict(path=str(cli), sha256=cli_hash),
        primary_consultations=plan['primary_consultations'],
        forms=rows, planned_batches=plan['planned_batches'],
        summary=dict(
            native_forms=len(rows), by_review_class=dict(Counter(
                row['review_class'] for row in rows)),
            cli_probes=sum(len(row['cli_modes']) for row in rows),
            noun_i_paths_by_mode={mode: sum(
                result['noun_i_paths'] for row in rows for result in row['cli_modes']
                if result['mode'] == mode)
                for mode in ['raw', 'dict-only', 'dict-compatible']},
            candidate_judgments_added=0),
        representation_policy=plan['representation_policy'],
        annotation_policy='Earlier complete corpus sentences/rows and original '
        'annotation categories remain in the immutable discovery artifact. '
        'A whole noun, a longer compound or a copula is not suffix gold.',
        runtime_change=False, ledger_change=False, baseline_change=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path,
                        default=ROOT / 'data/dictionaries/krdict/krdict.db')
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.cli.resolve(), args.dictionary.resolve(), args.revision),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
