"""Freeze the four native -감 finals before adding parser candidates.

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

SOURCE = ROOT / "docs/gam-question-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/gam-question-sources.json"
LMF = ROOT / "tests/fixtures/krdict-gam-question.json"
OWNERS = {"은감": [73878, 73888], "는감": [73879], "던감": [73880]}
RULE = "ending.refuting_question"
WORD = re.compile(r"[가-힣]+")


def relevant(word):
    return word.endswith(("는감", "던감", "은감")) or (
        word.endswith("감") and len(word) > 1 and (ord(word[-2]) - 0xAC00) % 28 == 4
    )


def cases():
    rows = []

    def add(
        surface,
        heads,
        kinds,
        forms,
        source,
        verdict="required",
        origin="authored_structural_case",
    ):
        row = {
            "id": "gam-question-" + digest([surface, heads, kinds, forms])[:24],
            "surface": surface,
            "lemmas": heads,
            "lemma_kinds": kinds,
            "morphemes": forms,
            "morpheme_kinds": [
                "suffix"
                if f == "답다"
                else "prefinal"
                if f in {"시", "었", "겠"}
                else "ending"
                for f in forms
            ],
            "verdict": verdict,
            "source": f"gam-question-{source}",
            "required_rules": [RULE],
            "origin": origin,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        assert row["id"] not in {r["id"] for r in rows}
        rows.append(row)

    for stem, head in [
        ("좋", "좋다"),
        ("넓", "넓다"),
        ("많", "많다"),
        ("적", "적다"),
        ("짧", "짧다"),
    ]:
        add(stem + "은감", [head], ["predicate"], ["은감"], 73888)
    for surface, head in [
        ("예쁜감", "예쁘다"),
        ("큰감", "크다"),
        ("긴감", "길다"),
        ("먼감", "멀다"),
        ("고운감", "곱다"),
        ("더운감", "덥다"),
        ("추운감", "춥다"),
        ("어떤감", "어떻다"),
        ("하얀감", "하얗다"),
        ("아닌감", "아니다"),
    ]:
        add(surface, [head], ["predicate"], ["은감"], 73878)
    for surface, head in [
        ("먹으신감", "먹다"),
        ("가신감", "가다"),
        ("좋으신감", "좋다"),
    ]:
        add(surface, [head], ["predicate"], ["시", "은감"], 73878)
    for noun in ["학생", "의사", "탓"]:
        add(noun + "인감", [noun, "이다"], ["nominal", "copula"], ["은감"], 73878)
    for surface, head, prefs in [
        ("먹는감", "먹다", []),
        ("가는감", "가다", []),
        ("사는감", "살다", []),
        ("만드는감", "만들다", []),
        ("돕는감", "돕다", []),
        ("듣는감", "듣다", []),
        ("있는감", "있다", []),
        ("없는감", "없다", []),
        ("계시는감", "계시다", []),
        ("하는감", "하다", []),
        ("모르는감", "모르다", []),
        ("멀었는감", "멀다", ["었"]),
        ("좋았는감", "좋다", ["었"]),
        ("가겠는감", "가다", ["겠"]),
        ("먹으시는감", "먹다", ["시"]),
        ("먹으셨겠는감", "먹다", ["시", "었", "겠"]),
    ]:
        add(surface, [head], ["predicate"], prefs + ["는감"], 73879)
    add("학생이었는감", ["학생", "이다"], ["nominal", "copula"], ["었", "는감"], 73879)
    for surface, head, prefs in [
        ("하던감", "하다", []),
        ("싸던감", "싸다", []),
        ("되던감", "되다", []),
        ("살던감", "살다", []),
        ("좋던감", "좋다", []),
        ("아니던감", "아니다", []),
        ("먹었던감", "먹다", ["었"]),
        ("않았던감", "않다", ["었"]),
        ("먹으셨던감", "먹다", ["시", "었"]),
        ("가겠던감", "가다", ["겠"]),
    ]:
        add(surface, [head], ["predicate"], prefs + ["던감"], 73880)
    add("학생이던감", ["학생", "이다"], ["nominal", "copula"], ["던감"], 73880)
    add("학생이었던감", ["학생", "이다"], ["nominal", "copula"], ["었", "던감"], 73880)
    for surface, right, connector, ending, owner in [
        ("먹고있는감", "있다", "고", "는감", 73879),
        ("먹고싶은감", "싶다", "고", "은감", 73888),
        ("먹어보는감", "보다", "어", "는감", 73879),
        ("먹어보던감", "보다", "어", "던감", 73880),
    ]:
        add(
            surface,
            ["먹다", right],
            ["predicate", "auxiliary"],
            [connector, ending],
            owner,
        )
    add("아이다운감", ["아이"], ["nominal"], ["답다", "은감"], 73878)
    add("아이다웠는감", ["아이"], ["nominal"], ["답다", "었", "는감"], 73879)
    add("아이다웠던감", ["아이"], ["nominal"], ["답다", "었", "던감"], 73880)
    # Exact spelling controls do not reject a competing lexical or noun path.
    for surface, head, ending, owner in [
        ("좋감", "좋다", "은감", 73888),
        ("먹감", "먹다", "은감", 73888),
        ("예쁘은감", "예쁘다", "은감", 73888),
        ("길은감", "길다", "은감", 73888),
        ("멀은감", "멀다", "은감", 73888),
        ("크은감", "크다", "은감", 73888),
        ("살는감", "살다", "는감", 73879),
        ("만들는감", "만들다", "는감", 73879),
        ("갈는감", "가다", "는감", 73879),
    ]:
        add(
            surface,
            [head],
            ["predicate"],
            [ending],
            owner,
            "forbidden",
            "written_boundary_control",
        )
    for surface, noun in [("학생감", "학생"), ("학생은감", "학생"), ("의사감", "의사")]:
        add(
            surface,
            [noun, "이다"],
            ["nominal", "copula"],
            ["은감"],
            73878,
            "forbidden",
            "missing_copula_or_attached_coda_control",
        )
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
                                "id": "gam-question-native-"
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


def freeze(cli, dictionary):
    assert not any(path.exists() for path in (SOURCE, FIXTURE, LMF))
    native = load_dictionary(dictionary)
    hits, rows, corpora = discover(native), cases(), corpus_observations()
    surfaces = sorted(
        {r["surface"] for r in hits + rows}
        | {r[1] for c in corpora for s in c["sentences"] for r in s["original_rows"]}
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
        "checklist": "COV-017bv",
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
        f"Verified immutable -감 preflight: {len(fixture['cases'])} proposals, {len(source['discoveries'])} native observations, {len(fixture['before_words'])} words and {len(source['complete_native_entries'])} complete owners; contextual review pending."
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
