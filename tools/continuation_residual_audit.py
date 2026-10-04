"""Freeze and verify the six original continuation-headed corpus residuals.

Gold, spelling and native dictionary fields are evidence, never repairs. Runtime
observations of diagnostic companions are separate from original corpus rows.
"""
import argparse
import copy
import gzip
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / 'docs/continuation-gold-residual-preflight.json'
REPORT = ROOT / 'docs/continuation-gold-residual-source-review.json'
SOURCE = ROOT / 'tests/fixtures/continuation-residual-sources.json'
LMF = ROOT / 'tests/fixtures/krdict-continuation-residual.json'
SUITE = ROOT / 'tests/fixtures/continuation-residual-validity.json'
PDF_URL = ('https://www.korean.go.kr/common/download.do?'
           'c_file_name=0528a905-2eb3-4c5a-978c-f424dd6a6c47_0.pdf&'
           'file_path=reportData&o_file_name=%ED%95%9C%EA%B8%80%EB%A7%9E%EC%B6%A4%EB%B2%95+'
           '%ED%91%9C%EC%A4%80%EC%96%B4%EA%B7%9C%EC%A0%95+%ED%95%B4%EC%84%A4.pdf')
SPACING_URL = ('https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?'
               'mn_id=216&qna_seq=325415')
MODES = {'all': [], 'headword': ['--dict-only'], 'compatible': ['--dict-compatible']}


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def write(path, value):
    with path.open('x') as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write('\n')


def suite():
    cases = []

    def add(surface, heads, kinds, forms, roles, verdict, source, reason):
        cases.append(dict(id='continuation-residual-' + str(len(cases) + 1),
                          surface=surface, judgments=[dict(
                              id='path', lemmas=heads, lemma_kinds=kinds,
                              morphemes=forms, morpheme_kinds=roles,
                              verdict=verdict, source=source, reason=reason)]))

    for surface, ending in [('드러난다', '는다'), ('드러나며', '으며')]:
        add(surface, ['드러나다'], ['predicate'], [ending], ['ending'],
            'required', 'lexicalized-spelling',
            'Native 15034 is the whole modern head; Article 15 supplement 1 '
            'specifically preserves 드러나다 spelling. This is not a judgment '
            'that the corpus decomposition is impossible in another representation.')
    for surface, heads, kinds, forms, roles in [
        ('잘하시네요', ['잘하다'], ['predicate'], ['시', '네요'], ['prefinal', 'ending']),
        ('잘하시네요', ['잘하다'], ['predicate'], ['시', '네', '요'], ['prefinal', 'ending', 'particle']),
        ('편이네요', ['편', '이다'], ['nominal', 'copula'], ['네요'], ['ending']),
        ('편이네요', ['편', '이다'], ['nominal', 'copula'], ['네', '요'], ['ending', 'particle']),
    ]:
        add(surface, heads, kinds, forms, roles, 'required', 'ending-85934',
            'Explicitly entered diagnostic companion, not a correction of the '
            'original corpus input. Native -네요 and -네 retain distinct ending '
            'representations; context and author intent remain unjudged.')
    for surface, heads, kinds, forms, roles in [
        ('잘하시내요', ['잘하다', '내다'], ['predicate', 'auxiliary'],
         ['시', '어', '어', '요'], ['prefinal', 'ending', 'ending', 'particle']),
        ('편이내요', ['편', '이다', '내다'], ['nominal', 'copula', 'auxiliary'],
         ['어', '어', '요'], ['ending', 'ending', 'particle']),
    ]:
        add(surface, heads, kinds, forms, roles, 'forbidden', 'connector-86094',
            'Scoped standard written boundary: the annotated connector cannot '
            'vanish from these exact lemma/morpheme owners. No global 내요 ban '
            'or judgment of author intent follows.')
    for surface in ['잘하셔내요', '잘하시어내요']:
        add(surface, ['잘하다', '내다'], ['predicate', 'auxiliary'],
            ['시', '어', '어', '요'], ['prefinal', 'ending', 'ending', 'particle'],
            'required', 'connector-86094',
            'Represented 시 + 어 connector, contracted or full, licenses the '
            'separate auxiliary candidate. Lexical sense/register is not judged.')
    for surface, forms, roles in [
        ('낼', ['을'], ['ending']),
        ('내시네', ['시', '네'], ['prefinal', 'ending']),
        ('내요', ['어', '요'], ['ending', 'particle']),
    ]:
        add(surface, ['내다'], ['predicate'], forms, roles, 'required', 'verb-89906',
            'Native lexical 내다 89906 remains a main-verb candidate. Shared '
            'headword with auxiliary 60625 does not change the lemma role.')
    return dict(schema_version=1,
                review_status='Agent source-scoped judgments; independent Korean review pending.',
                sources={
                    'lexicalized-spelling': PDF_URL,
                    'ending-85934': 'https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=85934',
                    'connector-86094': 'https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=86094',
                    'verb-89906': 'https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89906',
                }, cases=cases)


def dispositions(original):
    result = []
    for case in original['cases']:
        row = case['original_gold_row']
        surface = row['surface']
        if surface in {'드러난다', '드러나며'}:
            category = 'whole_lexical_head_vs_corpus_decomposition'
            entries = ['krdict:15034', 'krdict:71686', 'krdict:62134', 'krdict:62210']
            next_action = ('Preserve the existing whole-head analysis. Any future '
                           'finite compound decomposition needs an explicit '
                           'representation/role audit; do not infer 들 + 어 → 드러.')
            companion = None
            explanation = ('The dictionary head is 드러나다. Article 15 supplement '
                           '1 and its explanation explicitly distinguish this '
                           'spelling from transparent compounds. The corpus uses '
                           'pvg+ecx+px; modern whole-head recovery is already present.')
        elif surface.endswith('내요'):
            category = 'possible_spelling_and_annotation_difference'
            entries = ['krdict:85934', 'krdict:77333', 'krdict:86094', 'krdict:80330',
                       'krdict:60625', 'krdict:89906']
            entries += ['krdict:70073'] if surface.startswith('잘') else ['krdict:71321', 'krdict:86232']
            companion = surface.removesuffix('내요') + '네요'
            next_action = ('Keep input and gold unchanged. The 네요 companion is '
                           'diagnostic only; source connector evidence does not '
                           'license silent correction or an unrepresented auxiliary boundary.')
            explanation = ('Original GSD annotation supplies an 아 connective '
                           'before VX 내다. Native auxiliary 60625 requires an '
                           '어 connective; after 시 the written connector is 시어 '
                           'or contracted 셔. Native -네요 supplies a distinct '
                           'standard ending reading for the diagnostic companion. '
                           'The original authors’ intended reading is not established.')
        else:
            category = 'missing_space_before_lexical_main_verb'
            entries = ['krdict:71579', 'krdict:89906', 'krdict:60625']
            companion = '짜증 ' + surface.removeprefix('짜증')
            next_action = ('COV-020q: extend optional dictionary-backed spacing '
                           'for audited bare-noun/main-verb pairs. Keep individual '
                           'word candidates, roles, offsets, limits and source identities. '
                           'No arbitrary compound or auxiliary path is justified.')
            explanation = ('Original XPOS is NNG+VV, not VX. Native 짜증 71579 '
                           'and lexical 내다 89906 both exemplify the combination '
                           'with a case particle, while the noun also has an '
                           'unmarked example before 내지. NIKL 325415 explicitly '
                           'requires two words. The current spacing template '
                           'requires a case-marked left segment and misses this pair.')
        result.append(dict(
            id=row['id'], corpus=case['corpus'], partition=case['partition'],
            original_gold_row=copy.deepcopy(row), category=category,
            source_entry_ids=entries, diagnostic_companion=companion,
            explanation=explanation, next_action=next_action,
            evidence_kind='Agent application of named primary sources; not an adjudicated corpus correction.',
            contextual_verdict='unjudged', independent_review='pending'))
    return result


def verify(local_sources=False):
    original = json.loads(PREFLIGHT.read_text())
    report = json.loads(REPORT.read_text())
    source = json.loads(SOURCE.read_text())
    assert report['original_preflight_sha256'] == sha(PREFLIGHT)
    assert report['source_fixture_sha256'] == sha(SOURCE)
    assert source['lmf_sha256'] == sha(LMF)
    assert json.loads(SUITE.read_text()) == suite()
    assert report['reviews'] == dispositions(original)
    with gzip.open(ROOT / 'docs/continuation-left-dictionary-corpora.json.gz', 'rt') as file:
        corpus_audit = json.load(file)
    cases = {(c['corpus'], c['partition'], row['original_gold_row']['id']): row
             for c in corpus_audit['corpora'] for row in c['cases']}
    for case, review in zip(original['cases'], report['reviews'], strict=True):
        row = case['original_gold_row']
        if local_sources:
            path = ROOT / case['source']
            assert sha(path) == case['source_sha256']
            assert case['original_sentence_block'].rstrip('\n') in path.read_text().split('\n\n')
        pinned = cases[case['corpus'], case['partition'], row['id']]
        assert row == pinned['original_gold_row']
        assert case['original_sentence_block'] == pinned['original_sentence_block']
        sid, token_id = row['id'].removeprefix('id:').split('/')
        assert '# sent_id = ' + sid + '\n' in case['original_sentence_block']
        token = next(line.split('\t') for line in case['original_sentence_block'].splitlines()
                     if line.split('\t')[0] == token_id)
        assert token[1] == row['surface']
        assert ('VV' in token[4] and 'VX' not in token[4]) if row['surface'].startswith('짜증') else True
        for mode in MODES:
            assert case['before_words'][mode] == pinned['observations'][mode]['before']
            observed = copy.deepcopy(source['observed_words'][row['surface']][mode])
            observed.pop('spacing')
            assert observed == case['after_words'][mode]
        assert all(i in source['complete_native_entries'] for i in review['source_entry_ids'])
        assert review['contextual_verdict'] == 'unjudged'
    for entry in source['source_entries']:
        projected = copy.deepcopy(source['complete_native_entries'][entry['id']])
        for sense in projected['senses']:
            sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
        assert projected == entry
    assert set(source['absent_heads']) == {'짜증내다', '짜증나다'}
    assert source['observed_words']['짜증낼']['compatible']['spacing']['alternatives'] == []
    assert source['observed_words']['짜증내시네']['compatible']['spacing']['alternatives'] == []
    assert any(a['spaced'] == '짜증을 낼' for a in source['observed_words']['짜증을낼']['compatible']['spacing']['alternatives'])
    assert len(report['reviews']) == 6
    assert {category: sum(r['category'] == category for r in report['reviews'])
            for category in {r['category'] for r in report['reviews']}} == {
                'whole_lexical_head_vs_corpus_decomposition': 2,
                'possible_spelling_and_annotation_difference': 2,
                'missing_space_before_lexical_main_verb': 2,
            }
    print('Six original rows/sentences preserved; 13 scoped judgments and complete source projections verified.')


def freeze(args):
    if any(p.exists() for p in [REPORT, SOURCE, LMF, SUITE]):
        raise SystemExit('Refusing to overwrite frozen residual evidence.')
    original = json.loads(PREFLIGHT.read_text())
    heads = {'드러나다', '들다', '나다', '짜증', '짜증내다', '짜증나다', '내다',
             '잘하다', '편', '이다', '-네요', '-네', '-어요', '-시-', '-어', '-아'}
    dbpath = args.dictionary.resolve()
    with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as db:
        entries = {ident: json.loads(raw) for ident, head, raw in
                   db.execute('select id,headword,data from entries') if head in heads}
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / 'data/dictionaries/krdict/json').glob('*.json')):
        for raw in array(json.loads(path.read_text())['LexicalResource']['Lexicon']['LexicalEntry']):
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
    write(LMF, dict(LexicalResource=dict(Lexicon=dict(
        LexicalEntry=[raw_entries[i] for i in sorted(entries)]))))
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for sense in entry['senses']:
            sense['translations'] = [t for t in sense['translations'] if t['language'] == '영어']
    surfaces = {c['original_gold_row']['surface'] for c in original['cases']}
    surfaces.update(c['surface'] for c in suite()['cases'])
    surfaces.update(['짜증', '짜증을낼', '들어나다', '드러나다'])
    words = {}
    cli = args.cli.resolve()
    for surface in sorted(surfaces):
        words[surface] = {mode: json.loads(subprocess.check_output(
            [str(cli), 'word', surface, '--dictionary', str(dbpath), *flags, '--suggest-spacing']))
            for mode, flags in MODES.items()}
    # Original six observations have no spacing field; compare it independently.
    for case in original['cases']:
        for mode in MODES:
            actual = copy.deepcopy(words[case['original_gold_row']['surface']][mode])
            actual.pop('spacing')
            assert actual == case['after_words'][mode]
    absent = sorted(heads - {e['headword'] for e in entries.values()})
    write(SOURCE, dict(schema_version=1, checklist='COV-019af',
                       dictionary_sha256=sha(dbpath), cli=str(cli), cli_sha256=sha(cli),
                       raw_source_sha256=hashes, lmf_sha256=sha(LMF),
                       complete_native_entries=entries, source_entries=projected,
                       absent_heads=absent, observed_words=words,
                       license='KRDict: CC BY-SA 2.0 KR. Translation-only English importer adapter; RelatedForm omitted.',
                       observation_scope='Discovery baseline, not required output for future spacing coverage.'))
    write(SUITE, suite())
    write(REPORT, dict(
        schema_version=1, checklist='COV-019af', reviewed='2026-10-03',
        original_preflight_sha256=sha(PREFLIGHT), source_fixture_sha256=sha(SOURCE),
        reviews=dispositions(original),
        primary_reviews=[dict(url=PDF_URL, title='한글 맞춤법 표준어 규정 해설',
                              edition='2018', printed_pages='40–43', physical_pages='42–45',
                              sha256=sha(args.norms_pdf), bytes=args.norms_pdf.stat().st_size,
                              scope='Article 15 and supplement 1: written stem boundaries and the explicitly listed lexicalized 드러나다.',
                              access='Complete named text read. Web screenshots failed; local rendering inspected separately.'),
                         dict(url=SPACING_URL, answered='2025-12-22',
                              scope='Complete question and answer read; the answer rejects the premise that 짜증내다/짜증나다 are single standard dictionary words and requires spaces.')],
        counts=dict(original_misses=6, lexicalized_representation=2,
                    possible_spelling_or_annotation=2, missing_bare_noun_space=2,
                    complete_native_entries=len(entries), diagnostic_surfaces=len(words),
                    raw_judgments=13, required=11, forbidden=2, contextual_readings_judged=0),
        remaining=['Independent Korean-language review of original sentences and intended readings.',
                   'COV-020q: optional bare-noun + lexical-main-verb spacing, including these two unchanged corpus inputs.',
                   'Any finite lexicalized decomposition needs a source/role/representation design before generation.'],
        limitations='Agent source audit, not corrected corpus gold or contextual disambiguation. '
                    'No production morphology/filter changes. Original six grouped misses remain six.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--cli', type=Path)
    parser.add_argument('--dictionary', type=Path)
    parser.add_argument('--norms-pdf', type=Path)
    parser.add_argument('--local-sources', action='store_true',
                        help='Also require and verify full pinned original ConLL sources.')
    args = parser.parse_args()
    if args.verify:
        verify(args.local_sources)
    elif args.cli and args.dictionary and args.norms_pdf:
        freeze(args)
    else:
        parser.error('Freeze requires --cli, --dictionary and --norms-pdf; verification is offline.')


if __name__ == '__main__':
    main()
