"""Preserve source-backed spacing cases and pre-change native/raw fixtures.

Required boundaries are authored from the reviewed source groups. Their right
word keeps all independent raw readings; this ledger does not select a sentence
sense. Unlisted-pair exclusions bound this finite template, not Korean grammar.
"""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import MAIN, ROOT, SOURCE, load_dictionary, read, sha
from lexical_nada_review import REVIEW
from native_lmf import verify_native_lmf

FIXTURE = ROOT / "tests/fixtures/lexical-nada-spacing.json"
LMF = ROOT / "tests/fixtures/krdict-lexical-nada-spacing.json"
RULE = "spacing.bare_noun_main_nada"
EXTRA_REQUIRED = [
    ("사고", "나다"),
    ("사고", "나"),
    ("사고", "난"),
    ("사고", "날"),
    ("사고", "났어요"),
    ("사고", "나겠어요"),
    ("사고", "나셨다"),
    ("교통사고", "났었다며"),
    ("실감", "나고"),
    ("생각", "났다"),
    ("냄새", "나는"),
    ("짜증", "나버렸어요"),
]
FORBIDDEN = [
    "불났다",
    "들통났다",
    "화났다",
    "열났다",
    "피난다",
    "소문난",
    "기억난다",
    "겨울났다",
    "집나다",
    "발표날짜",
    "전쟁난민",
    "계단난간",
    "가스난로",
    "싹나았다",
    "사고내다",
    "교통사고읽다",
    "실감내키다",
    "ZZZ났다",
]
LEGACY = [
    "신경질내다",
    "용기내서",
    "짜증낼",
    "기분내키는",
    "학교에서짜증낼",
    "학교에서용기내서",
    "학교에서지식인들을봐요",
]


def cases(source, review):
    pairs = {p["noun"]: p for p in review["finite_pair_proposals"]}
    result = []

    def required(identity, noun, right, origin, prefix=""):
        result.append(
            {
                "id": identity,
                "surface": prefix + noun + right,
                "verdict": "required",
                "rule": RULE,
                "segments": ([prefix] if prefix else []) + [noun, right],
                "noun_entry": pairs[noun]["noun_entry"],
                "main_entry": MAIN,
                "source": origin,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    for pair in review["finite_pair_proposals"]:
        for hit in pair["reviewed_native_examples"]:
            required(
                hit["id"] + "-required-pair",
                pair["noun"],
                hit["right"],
                {"kind": "reviewed_native_example", "discovery_id": hit["id"]},
            )
    for original in source["original_accident_reviews"]:
        match = re.fullmatch(
            r"(교통사고|사고)\s+([가-힣]+)", original["original_discovery"]["match"]
        )
        assert match
        required(
            original["id"] + "-required-pair",
            match[1],
            match[2],
            {"kind": "original_accident", "case_id": original["id"]},
        )
    for i, (noun, right) in enumerate(EXTRA_REQUIRED, 1):
        required(
            f"lexical-nada-inflection-{i:02}",
            noun,
            right,
            {"kind": "authored_independent_inflection", "pair": noun},
        )
    for noun in pairs:
        required(
            "lexical-nada-case-prefix-" + noun,
            noun,
            "났다",
            {"kind": "existing_case_phrase_before_reviewed_pair", "pair": noun},
            prefix="학교에서",
        )
    for i, surface in enumerate(FORBIDDEN, 1):
        result.append(
            {
                "id": f"lexical-nada-excluded-template-{i:02}",
                "surface": surface,
                "verdict": "forbidden",
                "rule": RULE,
                "scope": "No hypothesis under this finite pair rule. This does not exclude a registered whole word, another template or every sentence interpretation.",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    assert len(result) == len({c["id"] for c in result})
    return result


def projection(entries):
    result = copy.deepcopy([entries[key] for key in sorted(entries)])
    for entry in result:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    return result


def freeze(args):
    assert not FIXTURE.exists() and not LMF.exists(), (
        "Refusing to replace frozen fixtures"
    )
    source, review = read(SOURCE), read(REVIEW)
    assert sha(args.cli_before) == source["cli_sha256"]
    assert sha(args.dictionary) == source["dictionary_sha256"]
    native = load_dictionary(args.dictionary)
    originals = {
        r["surface"]: r["analysis"]
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }
    legacy = {}
    for surface in LEGACY:
        legacy[surface] = json.loads(
            subprocess.check_output(
                [
                    str(args.cli_before.resolve()),
                    "word",
                    surface,
                    "--dictionary",
                    str(args.dictionary.resolve()),
                    "--suggest-spacing",
                ]
            )
        )
    used = {
        e["id"]
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
        for lemma in r["dictionary"]["lemmas"]
        for e in lemma["entries"]
    }
    used.update(p["noun_entry"] for p in review["finite_pair_proposals"])
    used.update(
        h["entry"]
        for p in review["finite_pair_proposals"]
        for h in p["reviewed_native_examples"]
    )
    used.update(
        i
        for p in review["finite_pair_proposals"]
        for i in p["registered_whole_entries"]
    )
    # Preserve homonyms, whole words and existing case/auxiliary/old-pair owners.
    heads = {
        "학교",
        "지식인",
        "신경질",
        "용기",
        "짜증",
        "기분",
        "내다",
        "내키다",
        "버리다",
        "나다",
    }
    used.update(i for i, e in native.items() if e["headword"] in heads)
    used.update(
        e["id"]
        for word in legacy.values()
        for lemma in word["dictionary"]["lemmas"]
        for e in lemma["entries"]
    )
    entries = {i: native[i] for i in sorted(used)}
    raw, source_hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    supplemental = {
        i: e for i, e in entries.items() if i not in source["complete_native_entries"]
    }
    result = {
        "schema_version": 1,
        "checklist": "COV-020r",
        "rule": RULE,
        "source_sha256": sha(SOURCE),
        "review_sha256": sha(REVIEW),
        "lmf_sha256": sha(LMF),
        "raw_source_sha256": source_hashes,
        "source_entries": projection(entries),
        "supplemental_native_entries": supplemental,
        "license": source["license"],
        "before_raw_words": originals,
        "before_legacy_words": legacy,
        "cases": cases(source, review),
        "scope": "Native per-entry fixtures and finite structural judgments. Every contextual interpretation and independent Korean review remains pending.",
    }
    FIXTURE.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


def verify():
    source, review, fixture = read(SOURCE), read(REVIEW), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE)
    assert fixture["review_sha256"] == sha(REVIEW)
    assert fixture["lmf_sha256"] == sha(LMF)
    assert fixture["cases"] == cases(source, review)
    assert fixture["before_raw_words"] == {
        r["surface"]: r["analysis"]
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }
    entries = dict(source["complete_native_entries"])
    entries.update(fixture["supplemental_native_entries"])
    selected = {e["id"]: entries[e["id"]] for e in fixture["source_entries"]}
    assert fixture["source_entries"] == projection(selected)
    verify_native_lmf(read(LMF), selected)
    assert set(fixture["before_legacy_words"]) == set(LEGACY)
    assert (
        not source["complete_native_entries"].keys()
        & fixture["supplemental_native_entries"].keys()
    )
    print(
        f"{len(selected)} native entries, 389 raw words, seven legacy spacing baselines and {len(fixture['cases'])} individual structural cases verified"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli-before", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli_before and args.dictionary:
        freeze(args)
        verify()
    else:
        parser.error("freeze requires --cli-before and --dictionary")


if __name__ == "__main__":
    main()
