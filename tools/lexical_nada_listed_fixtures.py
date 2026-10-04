"""Freeze listed-cohort before outputs and complete native adapters before extension."""

import argparse
import json
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import (
    MAIN,
    MODES,
    ROOT,
    SOURCE,
    load_dictionary,
    read,
    sha,
    write,
)
from lexical_nada_listed_review import LISTED, NEW_PAIRS
from lexical_nada_review import REVIEW
from native_lmf import verify_native_lmf

FIXTURE = ROOT / "tests/fixtures/lexical-nada-listed.json"
LMF = ROOT / "tests/fixtures/krdict-lexical-nada-listed.json"
BEFORE = ROOT / "docs/lexical-nada-listed-preflight.json.gz"
RULE = "spacing.bare_noun_main_nada"
# Separate follow-up ending dependencies, not false pair exclusions.
PENDING_RIGHT = {"날지도": "ending + 도", "났다던데": "retrospective reported ending"}


def cases(source, original, review):
    identities = {p["noun"]: p["noun_entry"] for p in original["finite_pair_proposals"]}
    identities.update(
        {p["noun"]: p["noun_entry"] for p in review["new_finite_pair_proposals"]}
    )
    reviewed = {
        h["id"]
        for p in original["finite_pair_proposals"]
        for h in p["reviewed_native_examples"]
    } | {
        h["discovery_id"]
        for h in review["reviews"]
        if h["disposition"] == "native_bare_main_nada_pair"
    }
    result = []

    def add(ident, noun, right, source_ids, prefix=""):
        result.append(
            {
                "id": ident,
                "surface": prefix + noun + right,
                "segments": ([prefix] if prefix else []) + [noun, right],
                "noun_entry": identities[noun],
                "main_entry": MAIN,
                "rule": RULE,
                "source_discovery_ids": source_ids,
                "verdict": "pending_right_morphology"
                if right in PENDING_RIGHT
                else "required",
                "dependency": PENDING_RIGHT.get(right),
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    for hit in source["discoveries"]:
        if hit["id"] in reviewed:
            add(hit["id"] + "-listed-pair", hit["noun"], hit["right"], [hit["id"]])
    for noun in NEW_PAIRS:
        references = [
            h["id"]
            for p in review["new_finite_pair_proposals"]
            if p["noun"] == noun
            for h in p["reviewed_native_examples"]
        ]
        for right in ["나다", "난다", "났다", "나셨다"]:
            add(
                "lexical-nada-listed-inflection-" + noun + right,
                noun,
                right,
                references,
            )
        add("lexical-nada-listed-prefix-" + noun, noun, "났다", references, "학교에서")
    for supersession in review["superseded_exclusions"]:
        noun, right = supersession["replacement_segments"]
        add(
            supersession["original_case_id"] + "-source-supersession",
            noun,
            right,
            supersession["source_discovery_ids"],
        )
        result[-1]["supersedes"] = supersession["original_case_id"]
    assert len(result) == len({c["id"] for c in result}) == 266
    assert sum(c["verdict"] == "pending_right_morphology" for c in result) == 2
    return result


def freeze(cli, dictionary):
    assert not any(p.exists() for p in [FIXTURE, LMF, BEFORE]), (
        "Refusing to replace frozen evidence"
    )
    source, original, review = read(SOURCE), read(REVIEW), read(LISTED)
    rows = cases(source, original, review)
    surfaces = {
        h["noun"] + h["right"] for h in source["discoveries"] if h["listed_cohort"]
    }
    surfaces.update(c["surface"] for c in rows)
    surfaces.update(c["segments"][-1] for c in rows)
    text = " ".join(sorted(surfaces))
    streams = {
        mode: list(
            map(
                json.loads,
                subprocess.check_output(
                    [
                        str(cli.resolve()),
                        "text",
                        "-",
                        "--dictionary",
                        str(dictionary.resolve()),
                        "--suggest-spacing",
                        *flags,
                    ],
                    input=text.encode(),
                ).splitlines(),
            )
        )
        for mode, flags in MODES.items()
    }
    native = load_dictionary(dictionary)
    used = {c["noun_entry"] for c in rows} | {MAIN, "krdict:62134", "krdict:83815"}
    used.update(
        h["entry"]
        for h in source["discoveries"]
        if h["id"] in {i for c in rows for i in c["source_discovery_ids"]}
    )

    def visit(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                used.add(ident)
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)

    visit(streams)
    entries = {ident: native[ident] for ident in sorted(used)}
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    before = {
        "schema_version": 1,
        "checklist": "COV-020r",
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "source_sha256": sha(SOURCE),
        "listed_review_sha256": sha(LISTED),
        "before_input": text,
        "before_streams": streams,
        "complete_native_entries": entries,
        "raw_source_sha256": hashes,
        "license": source["license"],
        "scope": "Immutable pre-extension outputs for all listed source spellings and finite regressions. No contextual or independent judgments are implied.",
    }
    write(BEFORE, before)
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "checklist": "COV-020r",
                "cases": rows,
                "preflight_sha256": sha(BEFORE),
                "lmf_sha256": sha(LMF),
                "complete_native_entries": entries,
                "before_raw_words": {
                    r["surface"]: r["analysis"]
                    for r in streams["all"]
                    if r["kind"] == "word"
                },
                "superseded_exclusions": review["superseded_exclusions"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    selected = {c["surface"] for c in rows if c["segments"][-2] in NEW_PAIRS}
    priority_path = ROOT / "tests/fixtures/lexical-nada-listed-priority.json"
    assert not priority_path.exists()
    priority_path.write_text(
        json.dumps(
            {
                "preflight_sha256": sha(BEFORE),
                "before_words": {
                    r["surface"]: r
                    for r in streams["all"]
                    if r["kind"] == "word" and r["surface"] in selected
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify():
    fixture, before = read(FIXTURE), read(BEFORE)
    assert fixture["preflight_sha256"] == sha(BEFORE)
    assert fixture["lmf_sha256"] == sha(LMF)
    assert before["source_sha256"] == sha(SOURCE)
    assert before["listed_review_sha256"] == sha(LISTED)
    assert fixture["cases"] == cases(read(SOURCE), read(REVIEW), read(LISTED))
    assert fixture["superseded_exclusions"] == read(LISTED)["superseded_exclusions"]
    assert fixture["complete_native_entries"] == before["complete_native_entries"]
    assert fixture["before_raw_words"] == {
        r["surface"]: r["analysis"]
        for r in before["before_streams"]["all"]
        if r["kind"] == "word"
    }
    for c in fixture["cases"]:
        assert c["surface"] in fixture["before_raw_words"]
        assert (
            c["contextual_verdict"] == "unjudged"
            and c["independent_review"] == "pending"
        )
    verify_native_lmf(read(LMF), before["complete_native_entries"])
    priority = read(ROOT / "tests/fixtures/lexical-nada-listed-priority.json")
    assert priority["preflight_sha256"] == sha(BEFORE)
    selected = {
        c["surface"] for c in fixture["cases"] if c["segments"][-2] in NEW_PAIRS
    }
    assert priority["before_words"] == {
        r["surface"]: r
        for r in before["before_streams"]["all"]
        if r["kind"] == "word" and r["surface"] in selected
    }
    print(
        f"Verified 266 individual listed cases (264 required, two ending dependencies), {len(fixture['before_raw_words'])} original raw words and {len(before['complete_native_entries'])} complete native entries."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli-before", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli_before and args.dictionary:
        freeze(args.cli_before, args.dictionary)
        verify()
    else:
        parser.error("freeze requires --cli-before and --dictionary")
