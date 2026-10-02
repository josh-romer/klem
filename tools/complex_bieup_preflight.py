"""Freeze COV-021o sources and pre-change output without overwriting evidence."""
import argparse
import copy
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli', type=Path, required=True)
parser.add_argument('--dictionary', type=Path, default=ROOT / 'data/dictionaries/krdict/krdict.db')
args = parser.parse_args()
cli, dictionary = args.cli.resolve(), args.dictionary.resolve()
outputs = ['complex-bieup-sources.json', 'krdict-complex-bieup.json', 'kaist-complex-bieup.conllu']
existing = [name for name in outputs if (ROOT / 'tests/fixtures' / name).exists()]
if existing:
    parser.error('Refusing to overwrite frozen fixtures: ' + ', '.join(existing))


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def dump(path, value):
    with path.open('x') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write('\n')


preflight_path = ROOT / 'docs/complex-bieup-source-preflight.json'
preflight = json.load(preflight_path.open())
primary = preflight['complete_native_entries']
entries = {entry['id']: entry for entry in primary}
cases, contrasts, profiles, corpus_rows = [], [], [], []
controls = set(preflight['before_words'])


def add(name, surface, entry, forms, lemmas=None, kinds=None):
    cases.append(dict(
        id='complex-bieup-' + name, surface=surface,
        lemmas=[dict(text=head, kind=kind) for head, kind in zip(
            lemmas or [entry['headword']], kinds or ['predicate'])],
        morphemes=[dict(form=form, kind='prefinal' if form in ['었', '겠', '시'] else
                       'particle' if form == '도' else 'ending') for form in forms],
        source_id=entry['id'], source=entry['url'], verdict='required',
        reason='Native written paradigm at the stated existing suffix boundary; contextual sense, mood and register are not judged.'))


for entry in primary:
    ident = entry['id'].split(':')[1]
    stem = entry['headword'][:-1]
    irregular = stem[:-1] + chr(ord(stem[-1]) - 3) + '우'
    written = [f['written'].strip() for f in entry['forms'] if f['kind'] == '활용']
    regular_ni, irregular_ni = stem + '으니', irregular + '니'
    profile = 'regular' if regular_ni in written else 'irregular' if irregular_ni in written else 'unknown'
    assert profile != 'unknown', entry['id']
    profiles.append(dict(entry=entry['id'], class_from_written_forms=profile,
                         regular=regular_ni, irregular=irregular_ni))
    for index, surface in enumerate(written):
        if surface.endswith('은') or surface.endswith('운'):
            suffix = '은'
        elif surface.endswith('는'):
            suffix = '는'
        elif surface.endswith('으니') or surface.endswith('우니'):
            suffix = '으니'
        elif surface.endswith('습니다'):
            suffix = '습니다'
        else:
            suffix = {'아': '어', '어': '어', '워': '어', '고': '고', '지': '지'}[surface[-1]]
        add(ident + '-native-' + str(index), surface, entry, [suffix])
    # Opposite paradigms remain raw hypotheses, but the native entry's written
    # evidence contradicts these exact spellings. This is dictionary-policy
    # evidence, not a universal judgment about every lemma or context.
    vowel = '아' if (ord(stem[-1]) - 0xAC00) // 28 % 21 in [0, 2, 8] else '어'
    regular_aeo, irregular_aeo = stem + vowel, irregular[:-1] + '워'
    for spelling, surface, suffix in [
        ('regular', regular_ni, '으니'), ('irregular', irregular_ni, '으니'),
        ('regular', regular_aeo, '어'), ('irregular', irregular_aeo, '어'),
        ('regular', stem + '은', '은'), ('irregular', irregular[:-1] + '운', '은')]:
        contrasts.append(dict(id='complex-bieup-contrast-' + ident + '-' + spelling + '-' + suffix,
                              surface=surface, entry=entry['id'], headword=entry['headword'],
                              forms=[suffix], spelling=spelling, compatible=profile == spelling))
        controls.add(surface)

seolb = entries['krdict:63307']
for name, surface, forms in [
    ('polite', '설워요', ['어요']), ('expanded', '설우어', ['어']),
    ('expanded-polite', '설우어요', ['어요']), ('concessive', '설워도', ['어도']),
    ('reason', '설워서', ['어서']), ('conditional', '설우면', ['으면']),
    ('honorific', '설우시다', ['시', '다']), ('past', '설웠다', ['었', '다']),
    ('past-polite', '설웠어요', ['었', '어요']), ('past-modal', '설웠겠지', ['었', '겠', '지']),
    ('adnominal-future', '설울', ['을']), ('nominal', '설움', ['음']),
    ('nominal-particle', '설움도', ['음', '도'])]:
    add('63307-' + name, surface, seolb, forms)
# Composition probes have owner assertions but no new contextual gold.
controls.update(['설워졌다', '설워보였다', '넓어보였다', '설워서러웠다',
                 '얇아설웠다', '설와', '설오니', '설오어', '널와', '발와',
                 '서러워', '서러우니', '섧다', '섧고', '섧지'])
for entry in primary:
    controls.add(entry['headword'])
    controls.add(entry['headword'][:-1] + '고')

# Preserve the first unchanged training sentence for each regular native root.
# No 섧다 training annotation is present; do not fabricate a corpus gold row.
corpus_path = ROOT / 'data/corpora/kaist/ko_kaist-ud-train.conllu'
sentences, seen = {}, set()
roots = {entry['headword'][:-1]: entry for entry in primary}
for block in corpus_path.read_text().split('\n\n'):
    for line in block.splitlines():
        row = line.split('\t')
        if len(row) != 10:
            continue
        parts = row[2].split('+')
        if len(parts) != 2 or parts[0] not in roots or parts[0] in seen:
            continue
        if row[4].split('+')[0] not in ['paa', 'pvg']:
            continue
        entry = roots[parts[0]]
        sid = next(l.split(' = ', 1)[1] for l in block.splitlines() if l.startswith('# sent_id = '))
        seen.add(parts[0])
        sentences[sid] = block
        controls.add(row[1])
        corpus_rows.append(dict(path=str(corpus_path.relative_to(ROOT)), source_sha256=sha(corpus_path),
                                sentence_id=sid, token_id=row[0], surface=row[1], headword=entry['headword'],
                                original_row=line, original_sentence=block))

surfaces = sorted(controls | {case['surface'] for case in cases})
words = {surface: json.loads(subprocess.check_output(
    [str(cli), 'word', surface, '--dictionary', str(dictionary)])) for surface in surfaces}
with sqlite3.connect(dictionary.as_uri() + '?mode=ro', uri=True) as db:
    for word in words.values():
        for analysis in word['analyses']:
            for lemma in analysis['lemmas']:
                for raw, in db.execute('select data from entries where headword=?', (lemma['text'],)):
                    entry = json.loads(raw)
                    entries[entry['id']] = entry

raw_entries, source_hashes = {}, {}
for path in sorted((ROOT / 'data/dictionaries/krdict/json').glob('*.json')):
    for entry in array(json.load(path.open())['LexicalResource']['Lexicon']['LexicalEntry']):
        ident = 'krdict:' + str(entry['val'])
        if ident not in entries:
            continue
        head = next(f['val'] for lemma in array(entry['Lemma']) for f in array(lemma['feat']) if f['att'] == 'writtenForm')
        pos = next((f['val'] for f in array(entry.get('feat', [])) if f['att'] == 'partOfSpeech'), '품사 없음')
        if (head, pos) != (entries[ident]['headword'], entries[ident]['pos']):
            continue
        assert ident not in raw_entries
        raw = copy.deepcopy(entry)
        raw.pop('RelatedForm', None)
        raw['Sense'] = array(raw.get('Sense', []))
        for sense in raw['Sense']:
            if 'Equivalent' in sense:
                sense['Equivalent'] = [e for e in array(sense['Equivalent']) if any(
                    f['att'] == 'language' and f['val'] == '영어' for f in array(e.get('feat', [])))]
        raw_entries[ident] = raw
        source_hashes[str(path.relative_to(ROOT))] = sha(path)
assert set(raw_entries) == set(entries)
full = copy.deepcopy(list(entries.values()))
for entry in full:
    for sense in entry['senses']:
        sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
report = dict(schema_version=1, checklist=['COV-021o'],
              before_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              before_cli=str(cli), before_cli_sha256=sha(cli), dictionary_sha256=sha(dictionary),
              original_preflight=str(preflight_path.relative_to(ROOT)), original_preflight_sha256=sha(preflight_path),
              primary_entry_ids=[e['id'] for e in primary], profiles=profiles,
              source_entries=full, source_hashes=source_hashes, cases=cases, contrasts=contrasts,
              corpus_rows=corpus_rows, before_words=words, unjudged_controls=sorted(controls),
              primary_source_review=preflight['primary_source_review'] + [dict(
                  url='https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=322819',
                  published='2025-10-27', review='Full Article 18 and explanation read. Section 6 distinguishes lexical regular and irregular ㅂ paradigms and restricted 오. Extending retained ㄹ + 우 recovery to ㄼ is an inference from the complete native 섧다 paradigm and the explicit NIKL FAQ, not a claim that every ㄼ stem is irregular.')],
              attribution='NIKL Korean Basic Dictionary; UD Korean-Kaist r2.15',
              license='KRDict CC BY-SA 2.0 KR; UD CC BY-SA 4.0')
dump(ROOT / 'tests/fixtures/complex-bieup-sources.json', report)
dump(ROOT / 'tests/fixtures/krdict-complex-bieup.json', dict(LexicalResource=dict(
    Lexicon=dict(LexicalEntry=[raw_entries[i] for i in sorted(raw_entries)]))))
with (ROOT / 'tests/fixtures/kaist-complex-bieup.conllu').open('x') as file:
    file.write('\n\n'.join(sentences.values()) + '\n\n')
print(json.dumps(dict(sources=len(full), cases=len(cases), contrasts=len(contrasts),
                      surfaces=len(words), corpus_rows=len(corpus_rows)), ensure_ascii=False))
