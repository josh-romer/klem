"""Freeze source-backed bare-noun spacing evidence before implementation.

The complete lexical 내다 sense lists sixteen nouns. Three have independently
attested bare-noun + 내다 examples. Registered whole verbs and other pairs stay
individually tracked; a spelling substring is never treated as a source lemma.
"""

import argparse
import copy
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/bare-noun-spacing-sources.json"
LMF = ROOT / "tests/fixtures/krdict-bare-noun-spacing.json"
LEDGER = ROOT / "tests/fixtures/bare-noun-spacing-validity.json"
APPROVED = {"신경질", "용기", "짜증"}
MODES = {"all": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def write(path, value):
    with path.open("x") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def cases():
    result = []

    def add(tag, surface, words, heads, kinds, forms, verdict, reason):
        result.append(
            dict(
                id="bare-noun-spacing-" + tag,
                surface=surface,
                source="krdict-bare-object",
                judgments=[
                    dict(
                        id="segmentation",
                        verdict=verdict,
                        rule="spacing.bare_noun_lexical_verb",
                        segments=[
                            dict(surface=w, lemmas=h, lemma_kinds=k, morphemes=m)
                            for w, h, k, m in zip(
                                words, heads, kinds, forms, strict=True
                            )
                        ],
                        reason=reason,
                    )
                ],
            )
        )

    for head in sorted(APPROVED):
        for tail, forms in [
            ("낼", ["을"]),
            ("내시네", ["시", "네"]),
            ("내다", ["다"]),
            ("냈어요", ["었", "어요"]),
            ("내겠어요", ["겠", "어요"]),
            ("내세요", ["시", "어요"]),
            ("내며", ["으며"]),
            ("내서", ["어서"]),
            ("내", ["어"]),
            ("내지않다", ["지", "다"]),
            ("내어버렸다", ["어", "었", "다"]),
        ]:
            add(
                head + "-" + tail,
                head + tail,
                [head, tail],
                [
                    [head],
                    ["내다"]
                    + (
                        ["않다"]
                        if tail == "내지않다"
                        else ["버리다"]
                        if tail == "내어버렸다"
                        else []
                    ),
                ],
                [
                    ["unclassified"],
                    ["predicate"]
                    + (["auxiliary"] if tail in {"내지않다", "내어버렸다"} else []),
                ],
                [[], forms],
                "required",
                "Agent-authored spacing hypothesis licensed by an independently attested "
                "bare-noun/main-verb pair. Right inflections are independently analyzed; "
                "context, intent, register and sense remain unjudged. Identity keeps its "
                "original unclassified raw role; a known noun entry is required separately.",
            )
    for head in sorted(APPROVED):
        add(
            head + "-case-prefix",
            "학교에서" + head + "낼",
            ["학교에서", head, "낼"],
            [["학교"], [head], ["내다"]],
            [["nominal"], ["unclassified"], ["predicate"]],
            [["에서"], [], ["을"]],
            "required",
            "Existing independently analyzed case phrase followed by the named bare pair. "
            "This is a structural suggestion, not an attested whole sentence.",
        )
    for head in [
        "겁",
        "기분",
        "넌더리",
        "분위기",
        "샘",
        "싫증",
        "역정",
        "염증",
        "욕심",
        "진절머리",
        "탐",
        "호기심",
        "화",
        "쀍",
    ]:
        add(
            head + "-unreviewed",
            head + "내다",
            [head, "내다"],
            [[head], ["내다"]],
            [["unclassified"], ["predicate"]],
            [[], ["다"]],
            "forbidden",
            "Outside this finite source-attested bare-pair template. This is not a "
            "linguistic ban or a ban on legacy case-phrase suggestions, whole lexical "
            "heads, future independent source evidence or contextual readings.",
        )
    for head in sorted(APPROVED):
        for tail, heads in [
            ("나다", ["나다"]),
            ("읽다", ["읽다"]),
            ("내키는", ["내키다"]),
        ]:
            add(
                head + "-other-" + tail,
                head + tail,
                [head, tail],
                [[head], heads],
                [["unclassified"], ["predicate"]],
                [[], []],
                "forbidden",
                "The named bare-pair source licenses lexical 내다, not an arbitrary "
                "verb or another spelling beginning with 내. Morpheme details are "
                "not used for this template-level exclusion.",
            )
    return dict(
        schema_version=1,
        review_status="Agent source-scoped spacing hypotheses; every contextual interpretation and independent Korean review remain pending.",
        sources={
            "krdict-bare-object": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89906",
            "nikl-spacing": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=325415",
        },
        cases=result,
    )


def verify():
    source = json.loads(SOURCE.read_text())
    assert source["lmf_sha256"] == sha(LMF)
    assert json.loads(LEDGER.read_text()) == cases()
    assert source["approved_heads"] == sorted(APPROVED)
    assert len(source["pair_reviews"]) == 16
    for entry in source["source_entries"]:
        projected = copy.deepcopy(source["complete_native_entries"][entry["id"]])
        for sense in projected["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
        assert projected == entry
    seen = set()
    for head, hits in source["discovery"]["hits"].items():
        for hit in hits:
            entry = source["complete_native_entries"][hit["entry"]]
            sense = next(s for s in entry["senses"] if s["id"] == hit["sense"])
            assert hit["text"] in sense["examples"][hit["group"] - 1]
            word = source["before_words"][hit["right_surface"]]["all"]
            supported = any(
                a["lemmas"][0] == {"text": "내다", "kind": "predicate"}
                for a in word["analyses"]
            )
            if supported:
                seen.add(head)
            else:
                assert (head, hit["right_surface"]) == ("기분", "내키는")
    assert seen == APPROVED
    assert source["original_residual_preflight_sha256"] == sha(
        ROOT / "docs/continuation-gold-residual-preflight.json"
    )
    assert len(cases()["cases"]) == 59
    updates = json.loads(
        (ROOT / "tests/fixtures/bare-noun-spacing-judgment-updates.json").read_text()
    )
    assert len(updates["corrections"]) == 3
    original = {c["id"]: c for c in cases()["cases"]}
    for update in updates["corrections"]:
        assert update["original_case"] == original[update["id"]]
        expected = copy.deepcopy(update["original_case"])
        expected["judgments"][0]["segments"][1]["morphemes"] = ["으세요"]
        expected["judgments"][0]["reason"] = update["updated_case"]["judgments"][0][
            "reason"
        ]
        assert expected == update["updated_case"]
        assert update["contextual_verdict"] == "unjudged"
    print(
        "Sixteen original source pairs, five bare examples, one lexical false positive and 59 spacing cases verified."
    )


def freeze(args):
    if any(p.exists() for p in [SOURCE, LMF, LEDGER]):
        raise SystemExit("Refusing to overwrite source/before evidence.")
    dbpath = args.dictionary.resolve()
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
        lexical = json.loads(
            db.execute(
                "select data from entries where id=?", ("krdict:89906",)
            ).fetchone()[0]
        )
        sense = next(s for s in lexical["senses"] if s["id"] == "13")
        heads = [
            g[0].removesuffix("을 내다.").removesuffix("를 내다.")
            for g in sense["examples"]
            if len(g) == 1 and (g[0].endswith("을 내다.") or g[0].endswith("를 내다."))
        ]
        assert len(heads) == len(set(heads)) == 16
        pattern = re.compile(
            r"(?<![가-힣])("
            + "|".join(heads)
            + r") ((?:내|냈|낼|낸|냅니다)[가-힣]*)(?![가-힣])"
        )
        hits = {h: [] for h in heads}
        entries, scanned = {}, 0
        wanted = set(heads) | {h + "내다" for h in heads} | {"내다"}
        for ident, head, raw in db.execute("select id,headword,data from entries"):
            scanned += 1
            entry = json.loads(raw)
            if head in wanted:
                entries[ident] = entry
            for s in entry["senses"]:
                for index, group in enumerate(s["examples"]):
                    for text in group:
                        for match in pattern.finditer(text):
                            hits[match[1]].append(
                                dict(
                                    entry=ident,
                                    head=head,
                                    sense=s["id"],
                                    group=index + 1,
                                    right_surface=match[2],
                                    text=text,
                                )
                            )
                            entries[ident] = entry
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / "data/dictionaries/krdict/json").glob("*.json")):
        for raw in array(
            json.loads(path.read_text())["LexicalResource"]["Lexicon"]["LexicalEntry"]
        ):
            ident = "krdict:" + str(raw["val"])
            if ident not in entries:
                continue
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
            for s in raw["Sense"]:
                if "Equivalent" in s:
                    s["Equivalent"] = [
                        e
                        for e in array(s["Equivalent"])
                        if any(
                            f["att"] == "language" and f["val"] == "영어"
                            for f in array(e.get("feat", []))
                        )
                    ]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == set(entries)
    write(
        LMF,
        dict(
            LexicalResource=dict(
                Lexicon=dict(LexicalEntry=[raw_entries[i] for i in sorted(entries)])
            )
        ),
    )
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for s in entry["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
    surfaces = {c["surface"] for c in cases()["cases"]}
    surfaces.update(hit["right_surface"] for found in hits.values() for hit in found)
    surfaces.update(
        ["짜증", "신경질", "용기", "짜증을낼", "짜증내", "내다", "기분내키는"]
    )
    surfaces.update(
        c["surface"]
        for c in json.loads(
            (ROOT / "tests/fixtures/spacing-validity.json").read_text()
        )["cases"]
    )
    cli = args.cli.resolve()
    words = {
        surface: {
            mode: json.loads(
                subprocess.check_output(
                    [
                        str(cli),
                        "word",
                        surface,
                        "--dictionary",
                        str(dbpath),
                        *flags,
                        "--suggest-spacing",
                    ]
                )
            )
            for mode, flags in MODES.items()
        }
        for surface in sorted(surfaces)
    }
    reviews = []
    for head in heads:
        whole = [e["id"] for e in entries.values() if e["headword"] == head + "내다"]
        reviews.append(
            dict(
                head=head,
                noun_entries=[
                    e["id"] for e in entries.values() if e["headword"] == head
                ],
                whole_verb_entries=whole,
                bare_observations=hits[head],
                disposition="attested_bare_pair"
                if head in APPROVED
                else "whole_verb_registered_bare_pair_unjudged"
                if whole
                else "bare_pair_not_established_by_this_scan",
                contextual_verdict="unjudged",
                independent_review="pending",
            )
        )
    write(LEDGER, cases())
    write(
        SOURCE,
        dict(
            schema_version=1,
            checklist="COV-020q",
            before_revision=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            cli=str(cli),
            cli_sha256=sha(cli),
            dictionary_sha256=sha(dbpath),
            lmf_sha256=sha(LMF),
            raw_source_sha256=hashes,
            complete_native_entries=entries,
            source_entries=projected,
            approved_heads=sorted(APPROVED),
            discovery=dict(
                entries_scanned=scanned,
                scope="Every imported entry and complete Korean Sense.examples group. Spelling regex discovery is followed by independent lexical-head inspection; zero hits do not prove impossibility.",
                hits=hits,
            ),
            pair_reviews=reviews,
            before_words=words,
            original_residual_preflight_sha256=sha(
                ROOT / "docs/continuation-gold-residual-preflight.json"
            ),
            license="KRDict: CC BY-SA 2.0 KR. English adapter preserves native fields; RelatedForm omitted.",
            rule_scope="Only the three independently attested bare objects before separately analyzed lexical 내다. Keep raw identity roles and actual known noun/verb dictionary evidence; existing case-phrase paths and every whole-head alternative remain.",
            limitations="Five whole verbs and eight other unestablished bare pairs are individually tracked, not linguistically rejected. NIKL 325415 separately requires 짜증 내다 spacing. Corpus gold, spelling, contextual senses and independent review stay unchanged.",
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli and args.dictionary:
        freeze(args)
    else:
        parser.error(
            "Freeze requires --cli and --dictionary; --verify uses committed evidence."
        )


if __name__ == "__main__":
    main()
