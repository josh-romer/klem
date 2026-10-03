"""Freeze the final fifteen written-source reviews, preserving earlier evidence.

Primary review metadata is explicit input. No source field, spelling alias or
dictionary entry is repaired. Alternate heads missing from KRDict remain raw
candidates; a missing dictionary match is recorded separately from validity.
"""
import argparse
import copy
import json
import sqlite3
import subprocess
from pathlib import Path
from phonetic_paradigm_preflight import PDF, array, sha

ROOT = Path(__file__).resolve().parents[1]
ENDINGS = {
    '격하되는': '는', '결항됩니': '습니다', '고착되는': '는',
    '고하는': '는', '뜯깊어': '어', '뜯깊으니': '으니',
    '발그르세합니다': '습니다', '블러내어': '어',
    '삐뚤빼뚤한': '은', '삐뚤빼뚤하여': '어',
    '삐뚤빼뚤하니': '으니', '삐뚤빼뚤합니다': '습니다',
    '자로잡히니': '으니', '얃잡는': '는', '졸래매니': '으니',
}
ALTERNATES = {'격하되는': ('격하되다', 'krdict:29660'),
              '고착되는': ('고착되다', 'krdict:27281'),
              '고하는': ('고하다', 'krdict:18394')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path,
                        default=ROOT / 'data/dictionaries/krdict/krdict.db')
    parser.add_argument('--primary-reviews', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    paths = [output / name for name in
             ('source-head-sources.json', 'krdict-source-head.json')]
    if any(path.exists() for path in paths):
        parser.error('Refusing to overwrite frozen evidence.')
    if not output.is_dir():
        parser.error('Output directory must already exist.')
    cli, dictionary = args.cli.resolve(), args.dictionary.resolve()
    preflight_path = ROOT / 'docs/remaining-paradigm-source-preflight.json'
    previous_path = ROOT / 'docs/phonetic-paradigm-evaluation.json'
    preflight = json.loads(preflight_path.read_text())
    previous = json.loads(previous_path.read_text())
    primary = json.loads(args.primary_reviews.read_text())
    assert sha(dictionary) == preflight['dictionary_sha256']
    observations = previous['remaining_source_observations']
    assert {o['written'] for o in observations} == set(ENDINGS)
    assert all(o in preflight['observations'] for o in observations)
    entries = {o['entry_id']: preflight['complete_native_entries'][o['entry_id']]
               for o in observations}
    with sqlite3.connect(dictionary.as_uri() + '?mode=ro', uri=True) as db:
        for ident in sorted(entries):
            assert json.loads(db.execute('select data from entries where id=?',
                                         (ident,)).fetchone()[0]) == entries[ident]
        for head, ident in ALTERNATES.values():
            entry = json.loads(db.execute('select data from entries where id=?',
                                         (ident,)).fetchone()[0])
            assert entry['headword'] == head
            entries[ident] = entry
        assert not db.execute('select id from entries where headword=?',
                              ('삐뚤빼뚤하다',)).fetchall()
    cases, reviews, sources, surfaces = [], [], {}, set()

    def add(observation, label, surface, head, ending, verdict, source, reason,
            filtered_required=True):
        cases.append(dict(
            id=observation['id'] + '-' + label, surface=surface,
            judgments=[dict(id='path', lemmas=[head], lemma_kinds=['predicate'],
                            morphemes=[ending], morpheme_kinds=['ending'],
                            verdict=verdict, source=source, reason=reason)]))
        surfaces.add(surface)
        return dict(case=cases[-1]['id'], raw_required=verdict == 'required',
                    filtered_required=verdict == 'required' and filtered_required)

    dictionary_expectations = []
    for o in observations:
        written, ident = o['written'], o['entry_id']
        ending = ENDINGS[written]
        source = 'source-head-written-' + ident.split(':')[1]
        sources[source] = PDF
        reason = ('Agent application of spelling Article 15 to the complete named native head and ending; '
                  'standard written inflection only, not a global spelling ban or explicit FAQ token judgment.')
        if written == '결항됩니':
            disposition = 'reviewed_truncated_form'
            reason = ('The source field omits final 다 from the named formal ending. '
                      'Agent application to the complete ending; truncation is preserved as source evidence, not normalized.')
        elif written in ALTERNATES or ident == 'krdict:601920':
            disposition = 'reviewed_source_head_discrepancy'
        else:
            disposition = 'reviewed_written_base_conflict'
        expectations = [
            add(o, 'companion-required', o['diagnostic_companion'], o['headword'],
                ending, 'required', source, reason),
            add(o, 'listed-head-forbidden', written, o['headword'], ending,
                'forbidden', source, reason)]
        alternate = None
        if written in ALTERNATES:
            head, alt_id = ALTERNATES[written]
            alt_source = 'source-head-alternate-' + alt_id.split(':')[1]
            sources[alt_source] = entries[alt_id]['url']
            alternate = dict(headword=head, entry_id=alt_id, present_in_pinned_dictionary=True)
        elif ident == 'krdict:601920':
            head, alt_source = '삐뚤빼뚤하다', 'source-head-alternate-opendict'
            sources[alt_source] = primary['alternate_head']['senses'][2]['url']
            alternate = dict(headword=head, sense_ids=[s['sense_no'] for s in
                             primary['alternate_head']['senses']], present_in_pinned_dictionary=False)
        if alternate:
            expectations.append(add(
                o, 'alternate-head-required', written, head, ending, 'required',
                alt_source, 'The independently attested alternate head retains its own written stem; '
                'the ending boundary is agent morphological inference without contextual sense selection.',
                alternate['present_in_pinned_dictionary']))
        reviews.append(dict(original_observation=o, disposition=disposition,
                            alternate=alternate, primary_basis=reason,
                            interpretation='Only the specified head/ending path is judged. Unknown alternate roots, identity, historical/dialect readings and contextual sense remain unjudged.'))
        dictionary_expectations.extend(expectations)
    for entry in entries.values():
        surfaces.add(entry['headword'])
        surfaces.update(f['written'].strip() for f in entry['forms'] if f['written'])
    surfaces.add('삐뚤빼뚤하다')
    words = {s: json.loads(subprocess.check_output(
        [str(cli), 'word', s, '--dictionary', str(dictionary)])) for s in sorted(surfaces)}
    for s, word in words.items():
        if s in preflight['before_words']:
            assert word == preflight['before_words'][s], s
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / 'data/dictionaries/krdict/json').glob('*.json')):
        data = json.loads(path.read_text())['LexicalResource']['Lexicon']['LexicalEntry']
        for raw in array(data):
            ident = 'krdict:' + str(raw['val'])
            if ident not in entries:
                continue
            head = next(f['val'] for lemma in array(raw['Lemma'])
                        for f in array(lemma['feat']) if f['att'] == 'writtenForm')
            pos = next((f['val'] for f in array(raw.get('feat', []))
                        if f['att'] == 'partOfSpeech'), '품사 없음')
            if (head, pos) != (entries[ident]['headword'], entries[ident]['pos']):
                continue
            assert ident not in raw_entries
            raw = copy.deepcopy(raw)
            raw.pop('RelatedForm', None)
            raw['Sense'] = array(raw.get('Sense', []))
            for sense in raw['Sense']:
                if 'Equivalent' in sense:
                    sense['Equivalent'] = [e for e in array(sense['Equivalent'])
                                           if any(f['att'] == 'language' and f['val'] == '영어'
                                                  for f in array(e.get('feat', [])))]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == set(entries)
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for sense in entry['senses']:
            sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
    report = dict(
        schema_version=1, checklist=['COV-021p'],
        before_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        extractor_source='tools/source_head_preflight.py', extractor_sha256=sha(__file__),
        cli=str(cli), cli_sha256=sha(cli), dictionary_sha256=sha(dictionary),
        original_preflight=dict(path=str(preflight_path.relative_to(ROOT)), sha256=sha(preflight_path)),
        previous_review=dict(path=str(previous_path.relative_to(ROOT)), sha256=sha(previous_path)),
        primary_review_path=str(args.primary_reviews.resolve().relative_to(ROOT)),
        primary_review_sha256=sha(args.primary_reviews), primary_reviews=primary,
        complete_native_entries=entries, source_entries=projected, raw_source_hashes=hashes,
        reviews=reviews, cases=cases, sources=sources, dictionary_expectations=dictionary_expectations,
        before_words=words, previous_reviewed_ids=previous['reviewed_source_observation_ids'],
        original_observations=22, newly_reviewed=15, total_reviewed=22,
        remaining_unreviewed=0, original_unrecovered_count_unchanged=22,
        separate_pos_observation=dict(entry_id='krdict:600930', headword='발그스레하다',
            original_native_pos=entries['krdict:600930']['pos'], primary_pos='형용사',
            primary_source=primary['separate_pos_observation'],
            disposition='Independently sourced POS discrepancy; annotation policy and its contextual/class consequences remain open. Do not overwrite the native label.'),
        attribution='NIKL Korean Basic Dictionary and expert-reviewed 우리말샘 entries; NIKL spelling explanation.',
        license='KRDict fixture CC BY-SA 2.0 KR. English-only projection preserves every native sense, form, pronunciation and example. External review facts are not represented as a KRDict export or complete dictionary entry.',
        scope='All original written entry/form observations have scoped agent judgments; independent Korean-language review, full-entry POS/sense review and the broader checklist remain open. No production code or alias changes.')
    for path, value in zip(paths, [report, dict(LexicalResource=dict(
            Lexicon=dict(LexicalEntry=[raw_entries[i] for i in sorted(raw_entries)])))]):
        with path.open('x') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n')
    print(json.dumps(dict(reviews=len(reviews), cases=len(cases),
                         native_entries=len(entries), surfaces=len(words))))


if __name__ == '__main__':
    main()
