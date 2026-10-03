"""Freeze six scoped spelling reviews without rewriting native source fields.

The judgments concern standard written inflections of the named heads only.
Pronunciation, dialect, contextual sense and hypothetical alternate heads are
not judged. Extraction refuses overwrites; old discovery evidence stays intact.
"""
import argparse
import copy
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PDF = ('https://www.korean.go.kr/common/download.do?'
       'c_file_name=0528a905-2eb3-4c5a-978c-f424dd6a6c47_0.pdf&'
       'file_path=reportData&o_file_name=%ED%95%9C%EA%B8%80%EB%A7%9E%EC%B6%A4%EB%B2%95+'
       '%ED%91%9C%EC%A4%80%EC%96%B4%EA%B7%9C%EC%A0%95+%ED%95%B4%EC%84%A4.pdf')
TARGETS = {
    '극악함니다': ('습니다', 'Spelling Article 15; pronunciation Article 18 and NIKL 333779. Nasal pronunciation does not change the written ending.'),
    '뒤얽히여': ('어', 'Spelling Articles 15–16; pronunciation Article 22 and NIKL 329760. The written 어 ending is distinct from permitted [여] pronunciation.'),
    '모라치어': ('어', 'Spelling Article 15 applied to the unchanged complete native 몰아치다 head. Retain its written stem.'),
    '앙뭅니다': ('습니다', 'Spelling Articles 15 and 18 section 1; pronunciation Article 18. Final ㄹ deletes before ㅂ, while initial 악 remains written.'),
    '찌저지어': ('어', 'Spelling Articles 15–16 applied to the unchanged complete native 찢어지다 head. Retain its written stem.'),
    '찌저지니': ('으니', 'Spelling Article 15 applied to the unchanged complete native 찢어지다 head. Retain its written stem; 으니 is the existing canonical ending.'),
}


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path,
                        default=ROOT / 'data/dictionaries/krdict/krdict.db')
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    output = args.output_directory.resolve()
    paths = [output / name for name in
             ('phonetic-paradigm-sources.json', 'krdict-phonetic-paradigm.json')]
    if any(path.exists() for path in paths):
        parser.error('Refusing to overwrite frozen evidence.')
    if not output.is_dir():
        parser.error('Output directory must already exist.')
    cli, dictionary = args.cli.resolve(), args.dictionary.resolve()
    original_path = ROOT / 'docs/remaining-paradigm-source-preflight.json'
    original = json.loads(original_path.read_text())
    assert sha(dictionary) == original['dictionary_sha256']
    observations = [o for o in original['observations'] if o['written'] in TARGETS]
    assert len(observations) == 6
    ids = {o['entry_id'] for o in observations}
    entries = {ident: original['complete_native_entries'][ident] for ident in ids}
    with sqlite3.connect(dictionary.as_uri() + '?mode=ro', uri=True) as db:
        for ident, entry in entries.items():
            assert json.loads(db.execute('select data from entries where id=?',
                                         (ident,)).fetchone()[0]) == entry
    cases, reviews, surfaces = [], [], set()
    for observation in observations:
        ending, basis = TARGETS[observation['written']]
        source_id = 'phonetic-paradigm-' + observation['entry_id'].split(':')[1]
        review = dict(original_observation=copy.deepcopy(observation),
                      disposition='reviewed_written_pronunciation_conflict',
                      standard_written_companion=observation['diagnostic_companion'],
                      basis=basis, evidence_kind='Agent inference from the named primary provisions and the complete native head, not an explicit FAQ judgment of this surface.',
                      scope='Only this standard written head/ending pair; no global input ban, dictionary repair, pronunciation normalization or alternate-head exclusion.')
        reviews.append(review)
        for verdict, surface in [('required', observation['diagnostic_companion']),
                                 ('forbidden', observation['written'])]:
            cases.append(dict(
                id=observation['id'] + '-' + verdict, surface=surface,
                judgments=[dict(id='path', lemmas=[observation['headword']],
                                lemma_kinds=['predicate'], morphemes=[ending],
                                morpheme_kinds=['ending'], verdict=verdict,
                                source=source_id, reason=basis)]))
            surfaces.add(surface)
    for entry in entries.values():
        surfaces.add(entry['headword'])
        surfaces.update(f['written'].strip() for f in entry['forms'] if f['written'])
    words = {surface: json.loads(subprocess.check_output(
        [str(cli), 'word', surface, '--dictionary', str(dictionary)]))
        for surface in sorted(surfaces)}
    for surface, word in words.items():
        assert word == original['before_words'][surface], surface
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / 'data/dictionaries/krdict/json').glob('*.json')):
        data = json.loads(path.read_text())['LexicalResource']['Lexicon']['LexicalEntry']
        for raw in array(data):
            ident = 'krdict:' + str(raw['val'])
            if ident not in ids:
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
    assert set(raw_entries) == ids
    projected = copy.deepcopy([entries[i] for i in sorted(ids)])
    for entry in projected:
        for sense in entry['senses']:
            sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
    report = dict(
        schema_version=1, checklist=['COV-021p'], reviewed='2026-10-02',
        before_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        extractor_source='tools/phonetic_paradigm_preflight.py', extractor_sha256=sha(__file__),
        cli=str(cli), cli_sha256=sha(cli), dictionary_sha256=sha(dictionary),
        original_preflight=str(original_path.relative_to(ROOT)), original_preflight_sha256=sha(original_path),
        original_observations=22, previously_reviewed=1, newly_reviewed=6,
        remaining_unreviewed=15, original_unrecovered_count_unchanged=22,
        complete_native_entries=entries, source_entries=projected, raw_source_hashes=hashes,
        reviews=reviews, cases=cases, before_words=words,
        primary_reviews=[
            dict(url=PDF, title='한글 맞춤법 표준어 규정 해설', edition='2018',
                 printed_pages='40–45, 50 (ㄹ section only), 244–245, 249',
                 scope='Read the named provisions and explanations: stable stem/ending spelling, 아/어 selection, ㄹ loss, nasalization and optional [여] pronunciation. Only the ㅣ environment of Article 22 is used; later explanation revisions are not inferred from this edition.'),
            dict(url='https://m.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=333779',
                 answered='2026-07-14', scope='Full question and answer read; 합니다 is written with ㅂ and pronounced [함니다].'),
            dict(url='https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=329760',
                 answered='2026-04-21', scope='Full question and answer read; ㅣ + 어 permits [여] pronunciation. This does not approve written 여.')],
        source_access='PDF text read; screenshot requests for pages 41, 43 and 51 returned Internal Error. No unseen screenshot is claimed as evidence.',
        attribution='NIKL Korean Basic Dictionary and spelling/pronunciation explanations.',
        license='KRDict entries: CC BY-SA 2.0 KR. English fixture is a translation-only projection; every native spelling, pronunciation, sense and example is preserved.',
        interpretation='Standard written inflection judgments are agent-authored and await independent Korean-language review. The original 22 misses, all source objects and raw outputs remain unchanged. No production rule or alias is added.')
    for path, value in zip(paths, [report, dict(LexicalResource=dict(
            Lexicon=dict(LexicalEntry=[raw_entries[i] for i in sorted(ids)]))) ]):
        with path.open('x') as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write('\n')
    print(json.dumps(dict(reviews=6, cases=len(cases), entries=len(entries), surfaces=len(words))))


if __name__ == '__main__':
    main()
