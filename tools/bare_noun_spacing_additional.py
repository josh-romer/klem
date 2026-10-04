"""Preserve the additional independently attested 기분 + 내키다 pair.

The original 내다 discovery and judgment ledger remain immutable. This separate
ledger records the actual lexical head behind its one spelling false positive.
"""

import argparse
import copy
import json
import sqlite3
import subprocess
from pathlib import Path

from bare_noun_spacing_audit import ROOT, SOURCE, MODES, array, sha, write

EVIDENCE = ROOT / "tests/fixtures/bare-noun-spacing-additional-pairs.json"
LMF = ROOT / "tests/fixtures/krdict-bare-noun-spacing-additional.json"


def cases():
    result = []
    for tail, forms in [
        ("내키는", ["는"]),
        ("내키다", ["다"]),
        ("내켜", ["어"]),
        ("내켜서", ["어서"]),
        ("내켰다", ["었", "다"]),
        ("내키니", ["으니"]),
        ("내키겠어요", ["겠", "어요"]),
        ("내키시네요", ["시", "네요"]),
    ]:
        result.append(
            dict(
                id="bare-noun-spacing-기분-" + tail,
                surface="기분" + tail,
                source="krdict-bare-object-additional",
                judgments=[
                    dict(
                        id="segmentation",
                        verdict="required",
                        rule="spacing.bare_noun_lexical_verb",
                        segments=[
                            dict(
                                surface="기분",
                                lemmas=["기분"],
                                lemma_kinds=["unclassified"],
                                morphemes=[],
                            ),
                            dict(
                                surface=tail,
                                lemmas=["내키다"],
                                lemma_kinds=["predicate"],
                                morphemes=forms,
                            ),
                        ],
                        reason="Agent-authored spacing hypothesis based on the complete "
                        "native example 기분 내키는 대로. Inflections are analyzed "
                        "independently; context, register and intended spacing remain "
                        "unjudged. This evidence licenses 내키다, not lexical 내다.",
                    )
                ],
            )
        )
    return result


def verify():
    original = json.loads(SOURCE.read_text())
    source = json.loads(EVIDENCE.read_text())
    assert source["original_source_sha256"] == sha(SOURCE)
    assert source["lmf_sha256"] == sha(LMF)
    assert source["source_discovery"] == original["discovery"]["hits"]["기분"][0]
    assert source["pairs"] == [["기분", "내키다"]]
    assert source["cases"] == cases()
    assert len(source["complete_native_entries"]) == 2
    for entry in source["source_entries"]:
        projected = copy.deepcopy(source["complete_native_entries"][entry["id"]])
        for sense in projected["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
        assert entry == projected
    assert (
        source["complete_native_entries"]["krdict:20192"]
        == original["complete_native_entries"]["krdict:20192"]
    )
    assert (
        source["before_words"]["기분내키는"] == original["before_words"]["기분내키는"]
    )
    for case in source["cases"]:
        for mode in MODES:
            assert case["surface"] in source["before_words"]
            assert (
                source["before_words"][case["surface"]][mode]["normalized"]
                == case["surface"]
            )
    assert source["cli_sha256"] == original["cli_sha256"]
    assert source["dictionary_sha256"] == original["dictionary_sha256"]
    print(
        "Additional 기분 + 내키다 pair, two complete native entries and eight original before observations verified."
    )


def freeze(cli, dictionary):
    if EVIDENCE.exists() or LMF.exists():
        raise SystemExit("Refusing to overwrite additional source/before evidence.")
    original = json.loads(SOURCE.read_text())
    assert sha(cli) == original["cli_sha256"]
    assert sha(dictionary) == original["dictionary_sha256"]
    with sqlite3.connect(dictionary.resolve().as_uri() + "?mode=ro", uri=True) as db:
        entries = {
            row[0]: json.loads(row[1])
            for row in db.execute(
                "select id,data from entries where headword in ('기분','내키다')"
            )
        }
    assert {(e["headword"], e["pos"]) for e in entries.values()} == {
        ("기분", "명사"),
        ("내키다", "동사"),
    }
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / "data/dictionaries/krdict/json").glob("*.json")):
        for raw in array(
            json.loads(path.read_text())["LexicalResource"]["Lexicon"]["LexicalEntry"]
        ):
            ident = "krdict:" + str(raw["val"])
            if ident not in entries:
                continue
            # Export metadata can reuse val: require the actual lexical identity.
            head = next(
                f["val"]
                for lemma in array(raw["Lemma"])
                for f in array(lemma["feat"])
                if f["att"] == "writtenForm"
            )
            pos = next(
                (
                    f["val"]
                    for f in array(raw.get("feat", []))
                    if f["att"] == "partOfSpeech"
                ),
                "품사 없음",
            )
            if (head, pos) != (entries[ident]["headword"], entries[ident]["pos"]):
                continue
            assert ident not in raw_entries
            raw = copy.deepcopy(raw)
            raw.pop("RelatedForm", None)
            raw["Sense"] = array(raw.get("Sense", []))
            for sense in raw["Sense"]:
                if "Equivalent" in sense:
                    sense["Equivalent"] = [
                        e
                        for e in array(sense["Equivalent"])
                        if any(
                            f["att"] == "language" and f["val"] == "영어"
                            for f in array(e.get("feat", []))
                        )
                    ]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == set(entries)
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    words = {
        case["surface"]: {
            mode: json.loads(
                subprocess.check_output(
                    [
                        str(cli),
                        "word",
                        case["surface"],
                        "--dictionary",
                        str(dictionary),
                        *flags,
                        "--suggest-spacing",
                    ]
                )
            )
            for mode, flags in MODES.items()
        }
        for case in cases()
    }
    assert words["기분내키는"] == original["before_words"]["기분내키는"]
    write(
        LMF,
        dict(
            LexicalResource=dict(
                Lexicon=dict(LexicalEntry=[raw_entries[i] for i in sorted(entries)])
            )
        ),
    )
    write(
        EVIDENCE,
        dict(
            schema_version=1,
            checklist="COV-020q",
            pairs=[["기분", "내키다"]],
            before_revision=original["before_revision"],
            cli=str(cli),
            cli_sha256=sha(cli),
            dictionary_sha256=sha(dictionary),
            original_source_sha256=sha(SOURCE),
            lmf_sha256=sha(LMF),
            raw_source_sha256=hashes,
            source_discovery=original["discovery"]["hits"]["기분"][0],
            interpretation="The spelling scan false positive for lexical 내다 is an independently attested bare pair with the different main verb 내키다.",
            complete_native_entries=entries,
            source_entries=projected,
            before_words=words,
            cases=cases(),
            source_url="https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=20192",
            license=original["license"],
            contextual_verdict="unjudged",
            independent_review="pending",
        ),
    )
    verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        if not args.cli or not args.dictionary:
            parser.error("--cli and --dictionary are required to freeze")
        freeze(args.cli.resolve(), args.dictionary.resolve())


if __name__ == "__main__":
    main()
