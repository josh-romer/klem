"""Freeze emphatic purpose and affirmative endings before adding parser candidates.

Native examples and original corpus rows are observations, never repaired gold.
The matrix proposes source-backed structural paths and exact boundary controls;
POS conflicts and contextual interpretation remain separate from raw parsing.
"""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, digest, load_dictionary, read, run, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/emphatic-ending-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/emphatic-ending-sources.json"
LMF = ROOT / "tests/fixtures/krdict-emphatic-ending.json"
OWNERS = {"게끔": [88382], "고말고": [66991], "다마다": [75968]}
WORD = re.compile(r"[가-힣]+")
NOVEL = ROOT / "data/books/mujeong.txt"
GUIDANCE = {
    "url": "https://www.korean.go.kr/common/download.do?c_file_name=5a2db2bc-a7ad-49f4-84a4-34b20ad33ffc_0.pdf&file_path=reportData&o_file_name=한국어교육%20문법표현%20내용개발%20연구_3단계.pdf",
    "title": "한국어교육 문법 · 표현 내용 개발 연구(3단계)",
    "publisher": "국립국어원",
    "publication": "2014-01-49",
    "submitted": "2014-12-12",
    "accessed": "2026-10-04",
    "pdf_sha256": "f6558a802b61115ead3ed20af9ecd7cf7b56f94e4c5a3342bf67f40bf0811268",
    "findings": [
        {
            "printed_page": 365,
            "pdf_page_index": 378,
            "section": "-게 하다1 / 확장 ④",
            "summary": "The verbal causative construction permits emphatic -게끔 하다.",
            "original_target_words": ["보게끔", "않게끔"],
        },
        {
            "printed_page": 370,
            "pdf_page_index": 383,
            "section": "-게 하다2 / 확장 ②",
            "summary": "The adjectival causative construction also permits -게끔 하다. KRDict's 주로 동사 note is not a categorical adjective exclusion.",
            "original_target_words": ["편리하게끔", "슬프게끔"],
        },
        {
            "printed_pages": [364, 369],
            "pdf_page_indexes": [377, 382],
            "section": "-게 하다1 / 제약 정보 ①; -게 하다2 / 문장 구성 정보 ➂",
            "summary": "In these causative constructions, past inflection belongs to right-hand 하다, not the immediately preceding predicate. The emphatic extension supplies a scoped immediate-owner past control; it does not ban standalone past + 게끔 or earlier-owner past.",
        },
    ],
    "limits": "The report does not establish -게끔 되다 or -게끔 생기다. Original annotated corpus compositions independently support 되다. Context, register, other auxiliary connectors and unlisted prefinals remain unjudged.",
}


def relevant(word):
    return any(form in word for form in OWNERS)


def cases():
    rows = []

    def add(
        word,
        heads,
        kinds,
        forms,
        source,
        verdict="required",
        origin="authored_structural_case",
    ):
        rows.append(
            {
                "id": "emphatic-ending-" + digest([word, heads, kinds, forms])[:24],
                "surface": word,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "morpheme_kinds": [
                    "suffix"
                    if f == "답다"
                    else "prefinal"
                    if f in {"시", "었", "겠"}
                    else "particle"
                    if f == "요"
                    else "ending"
                    for f in forms
                ],
                "verdict": verdict,
                "source": f"emphatic-ending-{source}",
                "required_rules": [
                    "ending.emphatic_purpose"
                    if "게끔" in forms
                    else "ending.emphatic_affirmation"
                ],
                "origin": origin,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    for ending, source in [("게끔", 88382), ("고말고", 66991), ("다마다", 75968)]:
        for stem, head in [
            ("먹", "먹다"),
            ("가", "가다"),
            ("살", "살다"),
            ("알", "알다"),
            ("하", "하다"),
            ("읽", "읽다"),
            ("듣", "듣다"),
            ("돕", "돕다"),
            ("좋", "좋다"),
            ("예쁘", "예쁘다"),
            ("그렇", "그렇다"),
            ("없", "없다"),
            ("있", "있다"),
        ]:
            add(stem + ending, [head], ["predicate"], [ending], source)
        for surface, head in [
            ("먹으시", "먹다"),
            ("가시", "가다"),
            ("아시", "알다"),
            ("좋으시", "좋다"),
        ]:
            add(surface + ending, [head], ["predicate"], ["시", ending], source)
        add(
            "먹고있" + ending,
            ["먹다", "있다"],
            ["predicate", "auxiliary"],
            ["고", ending],
            source,
        )
        add(
            "먹고싶" + ending,
            ["먹다", "싶다"],
            ["predicate", "auxiliary"],
            ["고", ending],
            source,
        )
        add(
            "먹어보" + ending,
            ["먹다", "보다"],
            ["predicate", "auxiliary"],
            ["어", ending],
            source,
        )
        add(
            "아이다우시" + ending, ["아이"], ["nominal"], ["답다", "시", ending], source
        )
        add("아이답" + ending, ["아이"], ["nominal"], ["답다", ending], source)
        for bad, head in [
            ("들어", "듣다"),
            ("도와", "돕다"),
            ("더워", "덥다"),
            ("그래", "그렇다"),
            ("아", "알다"),
        ]:
            add(
                bad + ending,
                [head],
                ["predicate"],
                [ending],
                source,
                "forbidden",
                "exact_consonant_boundary_control",
            )
        add(
            "알으시" + ending,
            ["알다"],
            ["predicate"],
            ["시", ending],
            source,
            "forbidden",
            "exact_honorific_boundary_control",
        )
    for ending, source in [("고말고", 66991), ("다마다", 75968)]:
        for surface, head, prefs in [
            ("먹었", "먹다", ["었"]),
            ("갔", "가다", ["었"]),
            ("좋았", "좋다", ["었"]),
            ("먹으셨", "먹다", ["시", "었"]),
        ]:
            add(surface + ending, [head], ["predicate"], prefs + [ending], source)
        for noun in ["학생", "의사", "미인"]:
            add(
                noun + "이" + ending,
                [noun, "이다"],
                ["nominal", "copula"],
                [ending],
                source,
            )
        add(
            "학생이었" + ending,
            ["학생", "이다"],
            ["nominal", "copula"],
            ["었", ending],
            source,
        )
        add("아이다웠" + ending, ["아이"], ["nominal"], ["답다", "었", ending], source)
    add(
        "그렇고말고요",
        ["그렇다"],
        ["predicate"],
        ["고말고", "요"],
        66991,
        origin="original_novel_spelling",
    )
    for word, head in [
        ("들리게끔", "들리다"),
        ("나게끔", "나다"),
        ("생각하게끔", "생각하다"),
        ("타당하게끔", "타당하다"),
        ("자각하게끔", "자각하다"),
        ("서러워하게끔", "서러워하다"),
        ("되게끔", "되다"),
        ("선호하게끔", "선호하다"),
        ("인식하게끔", "인식하다"),
        ("인식되게끔", "인식되다"),
        ("않게끔", "않다"),
        ("들어오게끔", "들어오다"),
    ]:
        add(
            word,
            [head],
            ["predicate"],
            ["게끔"],
            88382,
            origin="source_observation_structural_target",
        )
    add(
        "들어오게끔",
        ["들다", "오다"],
        ["predicate", "auxiliary"],
        ["어", "게끔"],
        88382,
        origin="original_corpus_auxiliary_target",
    )
    for word, heads, kinds, forms in [
        ("먹게끔한다", ["먹다", "하다"], ["predicate", "auxiliary"], ["게끔", "는다"]),
        ("좋게끔한다", ["좋다", "하다"], ["predicate", "auxiliary"], ["게끔", "는다"]),
        (
            "먹게끔했다",
            ["먹다", "하다"],
            ["predicate", "auxiliary"],
            ["게끔", "었", "다"],
        ),
        (
            "먹으시게끔했습니다",
            ["먹다", "하다"],
            ["predicate", "auxiliary"],
            ["시", "게끔", "었", "습니다"],
        ),
        (
            "슬프게끔한다",
            ["슬프다", "하다"],
            ["predicate", "auxiliary"],
            ["게끔", "는다"],
        ),
        (
            "편리하게끔해줍니다",
            ["편리하다", "하다", "주다"],
            ["predicate", "auxiliary", "auxiliary"],
            ["게끔", "어", "습니다"],
        ),
        (
            "먹었다싶게끔했다",
            ["먹다", "싶다", "하다"],
            ["predicate", "auxiliary", "auxiliary"],
            ["었", "다", "게끔", "었", "다"],
        ),
        (
            "살게끔되어있다",
            ["살다", "되다", "있다"],
            ["predicate", "auxiliary", "auxiliary"],
            ["게끔", "어", "다"],
        ),
        (
            "타당하게끔되었다",
            ["타당하다", "되다"],
            ["predicate", "auxiliary"],
            ["게끔", "었", "다"],
        ),
    ]:
        add(
            word,
            heads,
            kinds,
            forms,
            88382,
            origin="source_backed_joined_owner_control",
        )
    add(
        "먹게끔하고말고",
        ["먹다", "하다"],
        ["predicate", "auxiliary"],
        ["게끔", "고말고"],
        88382,
    )
    add(
        "먹게끔하다마다",
        ["먹다", "하다"],
        ["predicate", "auxiliary"],
        ["게끔", "다마다"],
        88382,
    )
    for word, heads, forms in [
        ("먹었게끔한다", ["먹다", "하다"], ["었", "게끔", "는다"]),
        ("먹었게끔했다", ["먹다", "하다"], ["었", "게끔", "었", "다"]),
        ("좋았게끔한다", ["좋다", "하다"], ["었", "게끔", "는다"]),
        ("먹게끔보았다", ["먹다", "보다"], ["게끔", "었", "다"]),
        ("먹게끔싶다", ["먹다", "싶다"], ["게끔", "다"]),
    ]:
        add(
            word,
            heads,
            ["predicate", "auxiliary"],
            forms,
            88382,
            "forbidden",
            "immediate_owner_or_connector_control",
        )
    assert len({r["id"] for r in rows}) == len(rows)
    return rows


def discover(entries):
    hits = []
    for entry in entries.values():
        for sense in entry["senses"]:
            for gi, group in enumerate(sense["examples"]):
                for ti, text in enumerate(group):
                    for match in WORD.finditer(text):
                        if not relevant(match[0]):
                            continue
                        hits.append(
                            {
                                "id": "emphatic-ending-native-"
                                + digest(
                                    [
                                        entry["id"],
                                        sense["id"],
                                        gi,
                                        ti,
                                        match.start(),
                                        match.end(),
                                    ]
                                )[:24],
                                "entry": entry["id"],
                                "sense": sense["id"],
                                "group": gi,
                                "text_index": ti,
                                "surface": match[0],
                                "complete_group": group,
                                "text": text,
                                "char_span": [match.start(), match.end()],
                                "span": {
                                    "start": len(text[: match.start()].encode()),
                                    "end": len(text[: match.end()].encode()),
                                },
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return hits


def corpus_observations():
    result = []
    for path in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for sentence in path.read_text().strip().split("\n\n"):
            rows = [
                line.split("\t")
                for line in sentence.splitlines()
                if not line.startswith("#")
            ]
            matches = [
                r for r in rows if len(r) == 10 and r[0].isdigit() and relevant(r[1])
            ]
            if matches:
                sentences.append(
                    {"complete_sentence": sentence, "original_rows": matches}
                )
        result.append(
            {
                "source": str(path.relative_to(ROOT)),
                "sha256": sha(path),
                "sentences": sentences,
            }
        )
    assert len(result) == 6
    return result


def novel_observations():
    text = NOVEL.read_text()
    hits = []
    for match in WORD.finditer(text):
        if not relevant(match[0]):
            continue
        start = text.rfind("\n\n", 0, match.start()) + 2
        if start == 1:
            start = 0
        end = text.find("\n\n", match.end())
        if end < 0:
            end = len(text)
        hits.append(
            {
                "id": "emphatic-ending-novel-"
                + digest([sha(NOVEL), match.start(), match.end()])[:24],
                "surface": match[0],
                "char_span": [match.start(), match.end()],
                "span": {
                    "start": len(text[: match.start()].encode()),
                    "end": len(text[: match.end()].encode()),
                },
                "paragraph_char_span": [start, end],
                "complete_paragraph": text[start:end],
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return {
        "path": str(NOVEL.relative_to(ROOT)),
        "sha256": sha(NOVEL),
        "discoveries": hits,
    }


def freeze(cli, dictionary):
    assert not any(path.exists() for path in (SOURCE, FIXTURE, LMF))
    native = load_dictionary(dictionary)
    hits, rows, corpora = discover(native), cases(), corpus_observations()
    novel = novel_observations()
    surfaces = sorted(
        {r["surface"] for r in hits + rows}
        | {r[1] for c in corpora for s in c["sentences"] for r in s["original_rows"]}
        | {r["surface"] for r in novel["discoveries"]}
        | {w for f in GUIDANCE["findings"] for w in f.get("original_target_words", [])}
    )
    text, streams = run(cli, dictionary, surfaces)
    owners = {f"krdict:{i}" for ids in OWNERS.values() for i in ids} | {
        h["entry"] for h in hits
    }
    heads = {h for row in rows for h in row["lemmas"]} | {"답다"}
    owners |= {
        i
        for i, e in native.items()
        if e["headword"] in heads or e["id"] == "krdict:92145"
    }

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and value["id"].startswith("krdict:"):
                owners.add(value["id"])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(streams)
    entries = {i: native[i] for i in sorted(owners)}
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    source = {
        "schema_version": 1,
        "checklist": "COV-017bw",
        "implementation_status": "preflight_only",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "owners": OWNERS,
        "native_scan_entries": len(native),
        "discoveries": hits,
        "corpora": corpora,
        "novel": novel,
        "primary_guidance": GUIDANCE,
        "complete_native_entries": entries,
        "raw_source_sha256": hashes,
        "before_input": text,
        "before_streams": streams,
        "license": read(ROOT / "docs/adjectival-allomorph-source-preflight.json.gz")[
            "license"
        ],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(SOURCE, source)
    projected = copy.deepcopy(list(entries.values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(LMF),
                "cases": rows,
                "source_entries": projected,
                "corpora": corpora,
                "novel": novel,
                "primary_guidance": GUIDANCE,
                "before_words": {
                    r["surface"]: {
                        "analysis": r["analysis"],
                        "dictionary": r["dictionary"],
                    }
                    for r in streams["all"]
                    if r["kind"] == "word"
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    verify()


def verify(dictionary=None, cli=None):
    source, fixture = read(SOURCE), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert (
        source["owners"] == OWNERS
        and source["implementation_status"] == "preflight_only"
    )
    assert fixture["cases"] == cases() and fixture["corpora"] == source["corpora"]
    assert fixture["novel"] == source["novel"]
    assert fixture["primary_guidance"] == source["primary_guidance"] == GUIDANCE
    assert all(
        r["contextual_verdict"] == "unjudged" and r["independent_review"] == "pending"
        for r in source["discoveries"]
    )
    for row in source["discoveries"]:
        entry = source["complete_native_entries"][row["entry"]]
        sense = next(s for s in entry["senses"] if s["id"] == row["sense"])
        group = sense["examples"][row["group"]]
        assert (
            row["complete_group"] == group and group[row["text_index"]] == row["text"]
        )
        a, b = row["char_span"]
        assert row["text"][a:b] == row["surface"] and relevant(row["surface"])
        assert (
            row["text"].encode()[row["span"]["start"] : row["span"]["end"]].decode()
            == row["surface"]
        )
    verify_native_lmf(read(LMF), source["complete_native_entries"])
    projected = copy.deepcopy(list(source["complete_native_entries"].values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    assert fixture["source_entries"] == projected
    assert len(source["corpora"]) == 6
    for corpus in source["corpora"]:
        for sentence in corpus["sentences"]:
            for row in sentence["original_rows"]:
                assert len(row) == 10 and row[0].isdigit() and relevant(row[1])
                assert "\t".join(row) in sentence["complete_sentence"].splitlines()
    for hit in source["novel"]["discoveries"]:
        a, b = hit["char_span"]
        start, end = hit["paragraph_char_span"]
        assert start <= a < b <= end
        assert hit["complete_paragraph"][a - start : b - start] == hit["surface"]
        assert relevant(hit["surface"])
        assert hit["contextual_verdict"] == "unjudged"
        assert hit["independent_review"] == "pending"
    assert fixture["before_words"] == {
        r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        native = load_dictionary(dictionary)
        assert (
            len(native) == source["native_scan_entries"]
            and discover(native) == source["discoveries"]
        )
        assert all(native[i] == e for i, e in source["complete_native_entries"].items())
        assert corpus_observations() == source["corpora"]
        assert novel_observations() == source["novel"]
        raw, hashes = project_lmf(source["complete_native_entries"])
        assert hashes == source["raw_source_sha256"]
        assert read(LMF)["LexicalResource"]["Lexicon"]["LexicalEntry"] == list(
            raw.values()
        )
    if cli:
        assert sha(cli) == source["cli_sha256"] and dictionary
        text, streams = run(cli, dictionary, sorted(fixture["before_words"]))
        assert text == source["before_input"] and streams == source["before_streams"]
    print(
        f"Verified immutable emphatic-ending preflight: {len(fixture['cases'])} proposals, {len(source['discoveries'])} native observations, {len(fixture['before_words'])} words, {len(source['complete_native_entries'])} complete owners, {sum(len(s['original_rows']) for c in source['corpora'] for s in c['sentences'])} corpus rows and {len(source['novel']['discoveries'])} novel occurrences; contextual review pending."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(args.dictionary, args.cli)
    else:
        assert args.cli and args.dictionary
        freeze(args.cli.resolve(), args.dictionary.resolve())


if __name__ == "__main__":
    main()
