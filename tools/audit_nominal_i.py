#!/usr/bin/env python3
"""Discover remaining native noun-forming -이 examples without assigning gold.

Requires the pinned local dictionary/corpora and a built CLI. Writes JSON to
stdout; it never changes the source fixtures, candidate ledger or baselines.
Pass the report's revision to reproduce its historical source identity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def heads(db, word):
    return [dict(id=ident, headword=head, pos=pos,
                 data_sha256=hashlib.sha256(raw.encode()).hexdigest())
            for ident, head, pos, raw in db.execute(
                'SELECT id,headword,pos,data FROM entries WHERE headword=? ORDER BY id',
                (word,))]


def scan_corpora(forms):
    reports = []
    for corpus in ('kaist', 'gsd'):
        for part in ('train', 'dev', 'test'):
            path = ROOT / f'data/corpora/{corpus}/ko_{corpus}-ud-{part}.conllu'
            text = path.read_bytes().decode('utf-8')
            hits = []
            for sentence in text.split('\n\n'):
                matched = []
                for line in sentence.splitlines():
                    if not line or line.startswith('#'):
                        continue
                    columns = line.split('\t')
                    if not columns[0].isdigit():
                        continue
                    found = [form for form in forms if columns[1].startswith(form)]
                    if found:
                        matched.append(dict(forms=found, row=columns))
                if matched:
                    sent_id = next((line.removeprefix('# sent_id = ')
                                    for line in sentence.splitlines()
                                    if line.startswith('# sent_id = ')), None)
                    hits.append(dict(sent_id=sent_id, sentence=sentence,
                                     matches=matched))
            reports.append(dict(
                path=str(path.relative_to(ROOT)), sha256=digest(path),
                matching_sentences=len(hits),
                matching_rows=sum(len(hit['matches']) for hit in hits), hits=hits))
    return reports


def audit(cli, dictionary, revision):
    manifest = json.loads((ROOT / 'tests/fixtures/nominal-i-sources.json').read_text())
    fixture_path = ROOT / manifest['native_fixture']
    if digest(fixture_path) != manifest['native_fixture_sha256']:
        raise ValueError('native fixture differs from its pinned manifest')
    fixture = json.loads(fixture_path.read_text())
    entry = next(entry for entry in fixture['LexicalResource']['Lexicon']['LexicalEntry']
                 if entry['val'] == '88924')
    groups = [group for group in manifest['source_groups']
              if group['sense_id'] in ('2', '3')]
    native_groups = {(sense['val'], index + 1): group
                     for sense in entry['Sense'] if sense['val'] in ('2', '3')
                     for index, group in enumerate(sense['SenseExample'])}
    if len(native_groups) != len(groups):
        raise ValueError('remaining groups do not cover the native source')
    for group in groups:
        key = (group['sense_id'], group['example_group'])
        if native_groups.get(key) != group['native_group']:
            raise ValueError(f'manifest/native group mismatch: {key}')
    forms = [group['examples'][0] for group in groups]
    if len(set(forms)) != 36 or len(groups) != 36:
        raise ValueError('unexpected remaining native example inventory')
    with sqlite3.connect(dictionary.resolve().as_uri() + '?mode=ro', uri=True) as db:
        metadata = dict(db.execute('SELECT key,value FROM metadata'))
        source = db.execute('SELECT data FROM entries WHERE id=?',
                            ('krdict:88924',)).fetchone()[0]
        suffix = json.loads(source)
        rows = []
        for group in groups:
            word = group['examples'][0]
            base = word[:-1]
            rows.append(dict(
                id=f"nominal-i-remaining-88924-s{group['sense_id']}-g{group['example_group']}",
                sense_id=group['sense_id'], source_group=group['example_group'],
                native_group=group['native_group'], surface=word,
                tail_removed_probe=base, whole_heads=heads(db, word),
                tail_removed_heads=heads(db, base), predicate_head_probe=base + '다',
                predicate_heads=heads(db, base + '다'),
                interpretation='Tail removal and headword/POS membership are discovery '
                'probes, not certified segmentation, productive suffix attachment or '
                'contextual sense selection. Missing heads do not establish Root status.'))
    probes = []
    for row in rows:
        modes = []
        for name, flag in (('raw', None), ('dict-only', '--dict-only'),
                           ('dict-compatible', '--dict-compatible')):
            command = [str(cli), 'word', row['surface'], '--dictionary', str(dictionary)]
            if flag:
                command.append(flag)
            result = json.loads(subprocess.check_output(command))
            modes.append(dict(
                mode=name, output=result,
                noun_i_paths=sum('suffix.nominal.i' in analysis['rules']
                                 for analysis in result['analyses'])))
        probes.append(dict(id=row['id'], surface=row['surface'], modes=modes))
    corpora = scan_corpora(forms)
    return dict(
        schema_version=1, checklist=['COV-022', 'COV-022e'],
        status='Discovery audit; remaining native sense-2/3 noun formations need '
        'implementation and classification review. No correctness judgments or '
        'required decompositions are assigned.',
        revision=revision,
        scope='All six sense-2 and thirty sense-3 native example groups of pinned '
        'KRDict 88924. Exact native forms in three CLI/filter modes and literal '
        'prefix occurrences across six pinned corpus partitions. This is not an '
        'exhaustive dictionary derivational inventory or acceptability audit.',
        source=dict(
            manifest='tests/fixtures/nominal-i-sources.json',
            native_fixture=manifest['native_fixture'],
            native_fixture_sha256=manifest['native_fixture_sha256'],
            entry_id='krdict:88924',
            entry_data_sha256=hashlib.sha256(source.encode()).hexdigest(),
            url=suffix['url'], attachment_notes=[
                dict(sense=sense['id'], definition=sense['definition'], notes=sense['notes'])
                for sense in suffix['senses']],
            license=manifest['license'], license_url=manifest['license_url'],
            attribution=manifest['attribution']),
        dictionary_metadata=metadata,
        cli=dict(path=str(cli), sha256=digest(cli)),
        forms=rows, probes=probes, corpus_search=corpora,
        findings=[
            dict(id='compound-boundary', status='implementation and primary segmentation review pending',
                 finding='Sense 2 licenses selected noun-plus-verb combinations. '
                 '길잡이/목걸이/옷걸이/젖먹이 merit review of nominal-plus-predicate '
                 'lookup groups before the noun suffix, with particles/copulas owned '
                 'after the whole formation. Existing breakdown logic consumes suffixes '
                 'after the first nominal and needs an explicit boundary for such groups.'),
            dict(id='mixed-sense-examples', status='primary segmentation review pending',
                 finding='The same sense-2 list also includes 떠돌이 and 미닫이. '
                 'The class note alone does not settle their internal component choices, '
                 'shortened stems or historical relationships. They remain explicit '
                 'unresolved examples rather than assuming every sense-2 form has a noun '
                 'as its first component.'),
            dict(id='base-classes', status='class and representation review pending',
                 finding='Sense 3 lists selected nouns, roots and sound/manner words as '
                 'bases. Raw suffix removal and POS lookups do not distinguish all of '
                 'these classes or prove a related predicate. Every example keeps its '
                 'own discovery ID.')],
        summary=dict(
            native_forms=len(forms), sense_2_forms=sum(row['sense_id'] == '2' for row in rows),
            sense_3_forms=sum(row['sense_id'] == '3' for row in rows),
            cli_word_probes=sum(len(probe['modes']) for probe in probes),
            noun_i_paths_by_mode={mode: sum(result['noun_i_paths']
                                          for probe in probes for result in probe['modes']
                                          if result['mode'] == mode)
                                  for mode in ('raw', 'dict-only', 'dict-compatible')},
            corpus_files=len(corpora),
            matching_sentences=sum(corpus['matching_sentences'] for corpus in corpora),
            matching_rows=sum(corpus['matching_rows'] for corpus in corpora)),
        annotation_policy='Complete matching corpus sentence bodies and original rows '
        'are retained unchanged. Literal prefix hits may be longer lexical compounds or '
        'annotation differences; they are observations, not gold for suffix segmentation. '
        'No frozen baseline or candidate judgment ledger is modified.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path,
                        default=ROOT / 'data/dictionaries/krdict/krdict.db')
    parser.add_argument('--revision')
    args = parser.parse_args()
    revision = args.revision or subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    print(json.dumps(audit(args.cli.resolve(), args.dictionary.resolve(), revision),
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
