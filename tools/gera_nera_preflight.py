#!/usr/bin/env python3
"""Freeze native -거라/-너라 evidence before changing candidate generation.

Requires the local licensed KRDict snapshot and an explicitly selected baseline
CLI. Refuses to overwrite observations; later comparisons belong in new files.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def freeze(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', required=True, type=Path)
    parser.add_argument('--dictionary', required=True, type=Path)
    args = parser.parse_args()
    destinations = [ROOT / p for p in (
        'docs/gera-nera-source-preflight.json',
        'tests/fixtures/gera-nera-sources.json',
        'tests/fixtures/krdict-gera-nera.json',
    )]
    if any(p.exists() for p in destinations):
        parser.error('frozen observations already exist; do not overwrite them')
    with sqlite3.connect(args.dictionary.resolve().as_uri() + '?mode=ro', uri=True) as db:
        entries = {ident: json.loads(raw) for ident, raw in db.execute('select id,data from entries')}
    native = [dict(entry_id=e['id'], headword=e['headword'], pos=e['pos'],
                   written=f['written'], form_index=i)
              for e in entries.values() if e['pos'] in ('동사', '보조 동사', '형용사', '보조 형용사')
              for i, f in enumerate(e['forms'])
              if f['kind'] == '활용' and f['written'].endswith(('거라', '너라'))]
    native.sort(key=lambda f: (f['entry_id'], f['form_index']))
    original = json.loads((ROOT / 'docs/written-paradigm-discovery.json').read_text())
    original_pairs = {(m['entry_id'], m['written']) for m in original['misses']}
    assert len(native) == 46
    assert all((n['entry_id'], n['written']) in original_pairs for n in native)
    selected = {n['entry_id'] for n in native} | {'krdict:66953', 'krdict:68835'}
    controls = ('가다', '오다', '먹다', '살다', '듣다', '닫다', '돕다', '짓다', '하다',
                '들다', '말다', '버리다', '보다', '있다', '없다', '계시다', '예쁘다',
                '행복하다', '아니다', '이다', '싶다', '-어', '-지', '-시-', '-었-', '-겠-')
    selected.update(e['id'] for e in entries.values() if e['headword'] in controls)
    cases = []

    def case(surface, head, ending, source, selection, kind='predicate', verdict='required'):
        ident = f'gera-nera-{len(cases) + 1:04}'
        cases.append(dict(id=ident, surface=surface,
                          lemmas=[dict(text=head, kind=kind)],
                          morphemes=[dict(form=ending, kind='ending')],
                          source_id=source, verdict=verdict, selection=selection))

    for n in native:
        case(n['written'], n['headword'], n['written'][-2:], n['entry_id'],
             'Complete native written 활용 form; original discovery miss. Auxiliary entries remain distinct from lexical verb entries.')
        if n['written'].endswith('너라'):
            case(n['headword'][:-1] + '거라', n['headword'], '거라', 'krdict:66953',
                 'NIKL 305262/FAQ 6416: -거라 is independent of -너라 and also attaches to 오다 verbs.')
    for head in ('가다', '오다', '먹다', '살다', '듣다', '닫다', '돕다', '짓다', '하다', '들다', '말다'):
        case(head[:-1] + '거라', head, '거라', 'krdict:66953',
             'Authored consonant-boundary control from modern broad verb attachment; retain ㄹ/ㄷ/ㅂ/ㅅ before ㄱ, without vowel irregularity.')
    case('오너라', '오다', '너라', 'krdict:68835', 'Native ending examples and modern regular attachment to 오다.')
    for surface, head in [('가너라', '가다'), ('먹너라', '먹다'), ('살너라', '살다'),
                          ('오너라', '올다'), ('살거라', '사다'), ('들거라', '드다'),
                          ('살으거라', '살다'), ('들어거라', '들다')]:
        ending = '너라' if surface.endswith('너라') else '거라'
        case(surface, head, ending, 'krdict:68835' if ending == '너라' else 'krdict:66953',
             'Specific direct-boundary hypothesis only: -너라 requires an 오다 stem; -거라 does not delete ㄹ, insert 으, or introduce an 어 connective.',
             verdict='forbidden')
    unjudged = [dict(surface=s, scope=scope) for s, scope in (
        ('가시거라', 'Honorific + command register has not been independently reviewed.'),
        ('먹었거라', 'Past + command interpretation has not been independently reviewed.'),
        ('가겠거라', 'Modal + command interpretation has not been independently reviewed.'),
        ('가더거라', 'Retrospective + command interpretation has not been independently reviewed.'),
        ('오시너라', 'Intervening honorific versus the source-required immediate 오 stem remains independently unjudged.'),
        ('행복하거라', 'Adjectival wishes cannot be globally rejected from the dictionary verb-only note.'),
        ('예쁘거라', 'Adjectival mood/register requires separate evidence.'),
        ('있거라', 'Lexical existential verb/adjective homonyms and contextual sense remain separate.'),
        ('학생이거라', 'Copular wishes/register require separate evidence.'),
        ('싶거라', 'Auxiliary adjective mood requires separate evidence.'),
        ('가거라요', 'Outer polite-particle attachment/register remains unreviewed.'),
        ('가거라고', 'Quoted command composition requires independent source review.'),
    )]
    train = []
    for file in sorted((ROOT / 'data/corpora').glob('*/*train.conllu')):
        for sentence in file.read_text().strip().split('\n\n'):
            lines = sentence.splitlines()
            sid = next((l.removeprefix('# sent_id = ') for l in lines if l.startswith('# sent_id = ')), None)
            for line in lines:
                fields = line.split('\t')
                if len(fields) != 10 or not fields[0].isdigit() or not fields[1].endswith(('거라', '너라')):
                    continue
                train.append(dict(path=str(file.relative_to(ROOT)), source_sha256=digest(file),
                                  sentence_id=sid, token_id=fields[0], surface=fields[1],
                                  original_row=line, original_sentence=sentence,
                                  judgment='unjudged: original gold and segmentation preserved for individual review'))
    surfaces = {c['surface'] for c in cases} | {c['surface'] for c in unjudged} | {c['surface'] for c in train}
    words = {s: json.loads(subprocess.check_output([str(args.cli), 'word', s, '--dictionary', str(args.dictionary)]))
             for s in sorted(surfaces)}
    for c in cases:
        c['before_candidate_indices'] = [i for i, a in enumerate(words[c['surface']]['analyses'])
                                         if a['lemmas'] == c['lemmas'] and a['morphemes'] == c['morphemes']]
    raw, source_hashes = {}, {}
    for file in sorted((ROOT / 'data/dictionaries/krdict/json').glob('*.json')):
        for e in array(json.loads(file.read_text())['LexicalResource']['Lexicon']['LexicalEntry']):
            ident = 'krdict:' + str(e['val'])
            if ident not in selected:
                continue
            headword = next(f['val'] for lemma in array(e['Lemma'])
                            for f in array(lemma['feat']) if f['att'] == 'writtenForm')
            pos = next((f['val'] for f in array(e.get('feat', []))
                        if f['att'] == 'partOfSpeech'), '품사 없음')
            # Idioms reuse their parent entry's ID in the native export.
            # The imported dictionary deliberately excludes those records.
            if (headword, pos) != (entries[ident]['headword'], entries[ident]['pos']):
                continue
            v = copy.deepcopy(e)
            v.pop('RelatedForm', None)
            v['Sense'] = array(v.get('Sense', []))
            for sense in v['Sense']:
                if 'Equivalent' in sense:
                    sense['Equivalent'] = [t for t in array(sense['Equivalent'])
                                           if any(f['att'] == 'language' and f['val'] == '영어'
                                                  for f in array(t.get('feat', [])))]
            raw[ident] = v
            source_hashes[str(file.relative_to(ROOT))] = digest(file)
    assert set(raw) == selected
    fixture = dict(LexicalResource=dict(Lexicon=dict(LexicalEntry=[raw[i] for i in sorted(raw)])))
    sources = copy.deepcopy([entries[i] for i in sorted(selected)])
    for e in sources:
        for sense in e['senses']:
            sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
    report = dict(schema_version=1, checklist=['COV-021l'],
                  before_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  before_cli=str(args.cli), before_cli_sha256=digest(args.cli),
                  dictionary_sha256=digest(args.dictionary), source_hashes=source_hashes,
                  original_discovery_sha256=digest(ROOT / 'docs/written-paradigm-discovery.json'),
                  native_forms=native, complete_native_entries=[entries[i] for i in sorted(selected)],
                  train_rows=train, unjudged=unjudged,
                  primary_sources=[dict(url='https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=305262',
                                        scope='Full answer and reproduced Article 18 section reviewed: separate modern regular endings; 오거라 and 오너라 both valid; -너라 requires 오다 or an 오다-final verb.'),
                                   dict(url='https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6416&mn_id=62&pageIndex=1',
                                        scope='Full answer reviewed: modern -거라 attaches broadly to verbs, including 오다; old 가다-only restriction must not be propagated.')],
                  attribution='National Institute of Korean Language, Korean Basic Dictionary',
                  license='CC BY-SA 2.0 KR; official commentary is summarized by URL, not reproduced',
                  limits='This is a source preflight, not implementation or contextual precision evidence. Original corpus gold, original discovery, spelling observations and raw ledger are unchanged. Honorific/past/modal/retrospective, adjectival wishes, existential senses, polite followers and quotation are separately unjudged.')
    freeze(destinations[0], report)
    freeze(destinations[1], dict(schema_version=1, checklist=['COV-021l'], source_entries=sources,
                                 native_forms=native, cases=cases, before_words=words,
                                 unjudged=unjudged, attribution=report['attribution'], license=report['license']))
    freeze(destinations[2], fixture)
    print(json.dumps(dict(native_forms=len(native), sources=len(sources), cases=len(cases),
                          surfaces=len(words), train_rows=len(train),
                          before_present=sum(bool(c['before_candidate_indices']) for c in cases))))


if __name__ == '__main__':
    main()
