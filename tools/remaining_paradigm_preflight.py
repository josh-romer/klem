"""Freeze remaining native paradigm observations without treating them as gold.

The source entry, exact form index and immutable discovery object are retained.
Diagnostic companion spellings are author proposals, not corrections to the
dictionary or requirements for new spelling-normalization rules.
"""
import argparse
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path,
                        default=ROOT / 'data/dictionaries/krdict/krdict.db')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Refusing to overwrite frozen evidence: ' + str(args.output))
    cli, dictionary = args.cli.resolve(), args.dictionary.resolve()
    discovery_path = ROOT / 'docs/written-paradigm-discovery.json'
    rescan_path = ROOT / 'docs/complex-bieup-original-paradigm-rescan.json'
    discovery = json.loads(discovery_path.read_text())
    rescan = json.loads(rescan_path.read_text())
    assert sha(dictionary) == discovery['dictionary_sha256']
    companions = {
        '격하되는': '격화되는', '결항됩니': '결항됩니다',
        '고착되는': '고찰되는', '고하는': '곡하는',
        '극악함니다': '극악합니다', '뒤얽히여': '뒤얽히어',
        '뜯깊어': '뜻깊어', '뜯깊으니': '뜻깊으니',
        '모라치어': '몰아치어', '발그르세합니다': '발그스레합니다',
        '블러내어': '불러내어', '삐뚤빼뚤한': '삐뚤삐뚤한',
        '삐뚤빼뚤하여': '삐뚤삐뚤하여', '삐뚤빼뚤하니': '삐뚤삐뚤하니',
        '삐뚤빼뚤합니다': '삐뚤삐뚤합니다', '자로잡히니': '사로잡히니',
        '서툰': '서투른', '앙뭅니다': '악뭅니다', '얃잡는': '얕잡는',
        '졸래매니': '졸라매니', '찌저지어': '찢어지어',
        '찌저지니': '찢어지니',
    }
    assert {r['written'] for r in rescan['remaining']} == set(companions)
    entries, observations, surfaces, input_preparation = {}, [], set(), []
    with sqlite3.connect(dictionary.as_uri() + '?mode=ro', uri=True) as db:
        for remaining in rescan['remaining']:
            ident, index = remaining['entry_id'], remaining['form_index']
            original = next(m for m in discovery['misses']
                            if m['entry_id'] == ident and m['form_index'] == index)
            entry = json.loads(db.execute('select data from entries where id=?',
                                         (ident,)).fetchone()[0])
            assert entry == original['complete_native_entry']
            assert all(original[k] == v for k, v in remaining.items())
            assert entry['forms'][index]['written'] == remaining['written']
            entries[ident] = entry
            stable_key = json.dumps([ident, index, remaining['written']],
                                    ensure_ascii=False, separators=(',', ':'))
            record = dict(
                id='remaining-paradigm-' + hashlib.sha256(stable_key.encode()).hexdigest()[:20],
                **remaining, original_discovery_case=dict(
                    path=str(discovery_path.relative_to(ROOT)),
                    sha256=sha(discovery_path), entry_id=ident, form_index=index),
                diagnostic_companion=companions[remaining['written']],
                companion_status='Authored diagnostic only; not a source repair or a contextual judgment.',
                disposition='unreviewed', next_action='Review primary written spelling evidence, the complete native paradigm, and alternative heads independently before judging a missing rule.')
            if ident == 'krdict:29043':
                record.update(
                    disposition='reviewed_source_head_discrepancy',
                    review_source='nikl-324385', correct_inflection_head='서툴다',
                    next_action='Preserve the short-head reading and both native entries. Do not add 서투르다 as a lemma of 서툰 or rewrite the original discovery miss. This does not resolve the other source observations.')
            observations.append(record)
            surfaces.update([entry['headword'], remaining['written'], record['diagnostic_companion']])
            surfaces.update(f['written'].strip() for f in entry['forms']
                            if f['kind'] == '활용' and f['written'])
            for form_index, form in enumerate(entry['forms']):
                if form['kind'] == '활용' and form['written'] != form['written'].strip():
                    input_preparation.append(dict(
                        entry_id=ident, form_index=form_index,
                        original_written=form['written'], cli_input=form['written'].strip(),
                        reason='The word command rejects whitespace; only surrounding whitespace is trimmed for this diagnostic call. The complete native entry retains the original field.'))
        # The reviewed alternate head needs its own complete source, not an alias.
        entries['krdict:29045'] = json.loads(db.execute(
            'select data from entries where id=?', ('krdict:29045',)).fetchone()[0])
        surfaces.update(['서툴다', '서투니', '서투르니', '서툴러', '서툴어'])
    words = {}
    for surface in sorted(surfaces):
        words[surface] = json.loads(subprocess.check_output(
            [str(cli), 'word', surface, '--dictionary', str(dictionary)]))
    for record in observations:
        def matches(surface):
            return [i for i, a in enumerate(words[surface]['analyses'])
                    if any(l['text'] == record['headword'] for l in a['lemmas'])]
        record['current_listed_head_indices'] = matches(record['written'])
        record['diagnostic_companion_head_indices'] = matches(record['diagnostic_companion'])
        assert not record['current_listed_head_indices'], record['id']
        assert record['diagnostic_companion_head_indices'], record['id']
    report = dict(
        schema_version=1, checklist=['COV-021p'],
        status='All 22 remaining original observations frozen; one explicit source-head discrepancy reviewed, 21 observations remain unreviewed. No production spelling or alias rule changed.',
        revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        extractor_source=str(Path(__file__).resolve().relative_to(ROOT)),
        extractor_source_sha256=sha(__file__),
        cli=str(cli), cli_sha256=sha(cli), dictionary_sha256=sha(dictionary),
        original_discovery=str(discovery_path.relative_to(ROOT)), original_discovery_sha256=sha(discovery_path),
        current_rescan=str(rescan_path.relative_to(ROOT)), current_rescan_sha256=sha(rescan_path),
        complete_native_entries=entries, before_words=words, observations=observations,
        input_preparation=input_preparation,
        reviewed_regression_cases=[
            'remaining-paradigm-seotun-short-required',
            'remaining-paradigm-seotun-long-forbidden',
            'remaining-paradigm-seotureun-long-required'],
        primary_reviews=[dict(
            id='nikl-324385',
            url='https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=324385',
            title='-는 탓에', answered='2025-12-01', reviewed='2026-10-02',
            scope='Full question and answer read. The answer explicitly assigns 서툰 to 서툴다, excludes 서투르다, and explains ㄹ deletion before ㄴ. The two pinned complete entries remain unchanged; this review judges only the named inflection, not synonyms in general.'), dict(
            id='nikl-2007-short-stems', url='https://www.korean.go.kr/nkview/nklife/2007_3/2007_0311.pdf',
            pages='125–126', reviewed='2026-10-02',
            scope='Complete answer and paradigm tables on PDF pages 1–2 read. 서투른 is assigned to 서투르다 and 서툰 to 서툴다; the separate 어 restrictions are already implemented by COV-021h. Unrelated questions on later pages are outside this review.')],
        upstream_checks=[dict(
            entry='krdict:29043', url='https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaNationCode=7&ParaWordNo=29043&captchaNumber=&commentTitle=&comment_user_name=&divSearch=defViewGlobal&nation=jpn&nationCode=7&viewTypes=on&wordComment=',
            status='Full entry read via equivalent Japanese view with additional query parameters. The application still lists 서툰, while its examples use 서투른; the discrepancy is preserved.'), dict(
            entry='krdict:29045', url='https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaWordNo=29045&nation=jpn',
            status='Full entry read; 서툰 and the separate short-head examples are retained. Its 서툴어 conflicts with the already reviewed short-stem restriction.'), dict(
            entry='krdict:58039', url='https://krdict.korean.go.kr/m/eng/searchResultView?ParaSenseSeq=&ParaWordNo=58039&fileNo=&imgCount=&multiMediaSeq=&nation=eng&searchKind=&searchKindValue=&shortenUrl=&studySeq=',
            status='Full mobile entry read with additional query parameters. 뒤얽히여 is still a written application, accompanied by separate 어/여 pronunciations and shortened 뒤얽혀. This persistence does not establish a standard written 여 inflection; further orthographic evidence is required.')],
        attribution='NIKL Korean Basic Dictionary, unchanged pinned native entries; NIKL online language answers and 새국어생활.',
        license='Pinned KRDict entries: CC BY-SA 2.0 KR.',
        interpretation='Companion success demonstrates existing structural recovery for the authored control. It does not prove that the listed source form is a typo, authorize correcting user input, establish contextual accuracy, or reduce the original unrecovered count of 22.')
    with args.output.open('x') as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write('\n')
    print(json.dumps(dict(observations=len(observations), original_entries=len(entries)-1,
                         complete_entries=len(entries), surfaces=len(words),
                         reviewed=1, unreviewed=len(observations)-1), ensure_ascii=False))


if __name__ == '__main__':
    main()
