"""Retain explicit source-backed corrections without changing the original freeze."""

import argparse
import copy
import json
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import MODES, ROOT, digest, load_dictionary, read, sha
from native_lmf import verify_native_lmf

FIXTURE = ROOT / "tests/fixtures/reported-retrospective-corrections.json"
LMF = ROOT / "tests/fixtures/krdict-reported-retrospective-corrections.json"
CORE = ROOT / "tests/fixtures/reported-retrospective-sources.json"
SOURCE = ROOT / "docs/reported-retrospective-source-preflight.json.gz"
TARGET = "reported-retrospective-3713e8cf6d77ad4ece986e29"


def proposals():
    rows = []
    for surface, heads, kinds, forms in [
        ("이기리라던", ["이기다"], ["predicate"], ["으리", "라던"]),
        ("나누리라던", ["나누다"], ["predicate"], ["으리", "라던"]),
        ("아팠더라던데", ["아프다"], ["predicate"], ["었", "더", "라던데"]),
    ]:
        rows.append(
            {
                "id": "reported-retrospective-"
                + digest([surface, heads, kinds, forms])[:24],
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "verdict": "required",
                "ending_owner_status": "compatible",
                "required_rule": "ending.reporting_retrospective",
                "origin": "native_conjectural_report"
                if forms[-1] == "라던"
                else "past_before_source_listed_retrospective",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return rows


def freeze(cli, dictionary):
    assert not FIXTURE.exists() and not LMF.exists()
    core, source = read(CORE), read(SOURCE)
    assert (
        sha(cli) == source["cli_sha256"]
        and sha(dictionary) == source["dictionary_sha256"]
    )
    original = next(c for c in core["cases"] if c["id"] == TARGET)
    replacement = dict(
        original,
        verdict="required",
        ending_owner_status="unknown",
        origin="copular_extension_of_native_conjectural_report_unjudged",
    )
    native = load_dictionary(dictionary)
    owners = {
        i: e
        for i, e in native.items()
        if e["headword"] in {h for c in proposals() for h in c["lemmas"]}
        and i not in source["complete_native_entries"]
    }
    raw, hashes = project_lmf(owners)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    words = sorted({c["surface"] for c in proposals()} | {replacement["surface"]})
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
                    input=" ".join(words).encode(),
                ).splitlines(),
            )
        )
        for mode, flags in MODES.items()
    }
    hits = [
        h for h in source["discoveries"] if h["surface"] in {"이기리라던", "나누리라던"}
    ]
    assert len(hits) == 2
    value = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "lmf_sha256": sha(LMF),
        "before_cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "superseded": [
            {
                "original": original,
                "replacement": replacement,
                "reason": "The narrower -라던 note alone does not justify excluding conjectural reports: native complete groups attest 이기리라던 and 나누리라던. The copular extension remains Unknown.",
            }
        ],
        "native_evidence": hits,
        "cases": proposals(),
        "before_streams": streams,
        "before_words": {
            r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
            for r in streams["all"]
            if r["kind"] == "word"
        },
        "complete_native_entries": owners,
        "raw_source_sha256": hashes,
        "license": source["license"],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    FIXTURE.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def verify():
    f, source, core = read(FIXTURE), read(SOURCE), read(CORE)
    assert f["source_sha256"] == sha(SOURCE) and f["lmf_sha256"] == sha(LMF)
    assert f["before_cli_sha256"] == source["cli_sha256"]
    assert f["dictionary_sha256"] == source["dictionary_sha256"]
    assert f["cases"] == proposals()
    assert f["native_evidence"] == [
        h for h in source["discoveries"] if h["surface"] in {"이기리라던", "나누리라던"}
    ]
    assert len(f["superseded"]) == 1
    change = f["superseded"][0]
    assert change["original"] == next(c for c in core["cases"] if c["id"] == TARGET)
    assert change["replacement"] == dict(
        change["original"],
        verdict="required",
        ending_owner_status="unknown",
        origin="copular_extension_of_native_conjectural_report_unjudged",
    )
    assert (
        f["contextual_verdict"] == "unjudged" and f["independent_review"] == "pending"
    )
    verify_native_lmf(read(LMF), f["complete_native_entries"])
    for surface, before in f["before_words"].items():
        if surface in core["before_words"]:
            assert before == core["before_words"][surface]
    print(
        "Verified one explicit correction, three new structural cases and two immutable native groups."
    )


def effective_cases():
    cases = copy.deepcopy(read(CORE)["cases"])
    cases.extend(
        read(ROOT / "tests/fixtures/reported-retrospective-followers.json")["cases"]
    )
    corrections = read(FIXTURE)
    for change in corrections["superseded"]:
        index = next(
            i for i, c in enumerate(cases) if c["id"] == change["original"]["id"]
        )
        assert cases[index] == change["original"]
        cases[index] = change["replacement"]
    return cases + corrections["cases"]


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli-before", type=Path)
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    if not a.verify:
        assert a.cli_before and a.dictionary
        freeze(a.cli_before, a.dictionary)
    verify()
