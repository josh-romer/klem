"""Preserve the tested -감 source snapshot and guard its implemented candidates.

Packaged reports describe the frozen implementation, not every future revision.
The Rust suite guards the complete implemented cohort against current code;
--cli/--dictionary additionally compares every full current CLI/spacing stream.
"""

import argparse
import copy
import hashlib
import json
from pathlib import Path

from continuation_inflection_audit import project_lmf
from gam_question_audit import SOURCE
from lexical_nada_audit import ROOT, read, run, sha, write
from native_lmf import verify_native_lmf

SNAPSHOT = ROOT / "docs/gam-question-implementation-snapshot.json.gz"
FIXTURE = ROOT / "tests/fixtures/gam-question-implemented.json"
LMF = ROOT / "tests/fixtures/krdict-gam-question-implemented-additional.json"
REPORTS = [
    "docs/gam-question-source-preflight.json.gz",
    "docs/gam-question-observations.json.gz",
    "docs/gam-question-packaged-runtime.json",
    "docs/gam-question-packaged-browser.json",
]
FILES = {
    "engine_sha256": "src/engine.rs",
    "grammar_sha256": "src/grammar.rs",
    "catalog_sha256": "web/src/grammar-labels.json",
}


def freeze(cli, dictionary):
    assert not any(p.exists() for p in (SNAPSHOT, FIXTURE, LMF))
    source = read(SOURCE)
    observed = read(ROOT / REPORTS[1])
    runtime = read(ROOT / REPORTS[2])
    assert sha(cli) == runtime["cli_sha256"]
    assert sha(dictionary) == source["dictionary_sha256"]
    for field, path in FILES.items():
        assert sha(ROOT / path) == runtime[field]
    text, streams = run(
        cli,
        dictionary,
        sorted(read(ROOT / "tests/fixtures/gam-question-sources.json")["before_words"]),
    )
    assert text == source["before_input"]
    assert streams == observed["source_diagnostic_streams"]
    additional = {
        i: e
        for i, e in observed["complete_native_entries"].items()
        if i not in source["complete_native_entries"]
    }
    raw, raw_hashes = project_lmf(additional)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    write(
        SNAPSHOT,
        {
            "schema_version": 1,
            "checklist": "COV-017bv",
            "reports_sha256": {p: sha(ROOT / p) for p in REPORTS},
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "implementation_files": {p: (ROOT / p).read_text() for p in FILES.values()},
            "additional_native_entries": additional,
            "raw_source_sha256": raw_hashes,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
            "license": source["license"],
        },
    )
    projected = copy.deepcopy(list(additional.values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "snapshot_sha256": sha(SNAPSHOT),
                "lmf_sha256": sha(LMF),
                "additional_native_entries": projected,
                "implemented_words": {
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
    verify(cli, dictionary)


def verify(cli=None, dictionary=None):
    snapshot, fixture = read(SNAPSHOT), read(FIXTURE)
    assert snapshot["schema_version"] == fixture["schema_version"] == 1
    assert snapshot["checklist"] == "COV-017bv"
    assert snapshot["contextual_verdict"] == "unjudged"
    assert snapshot["independent_review"] == "pending"
    assert snapshot["reports_sha256"] == {p: sha(ROOT / p) for p in REPORTS}
    assert fixture["snapshot_sha256"] == sha(SNAPSHOT)
    assert fixture["lmf_sha256"] == sha(LMF)
    runtime, browser = read(ROOT / REPORTS[2]), read(ROOT / REPORTS[3])
    observed, source = read(ROOT / REPORTS[1]), read(SOURCE)
    assert snapshot["cli_sha256"] == runtime["cli_sha256"]
    assert snapshot["dictionary_sha256"] == source["dictionary_sha256"]
    assert set(snapshot["implementation_files"]) == set(FILES.values())
    for field, path in FILES.items():
        digest = hashlib.sha256(
            snapshot["implementation_files"][path].encode()
        ).hexdigest()
        assert digest == runtime[field]
        if field != "grammar_sha256":
            assert digest == browser[field]
    additional = {
        i: e
        for i, e in observed["complete_native_entries"].items()
        if i not in source["complete_native_entries"]
    }
    assert snapshot["additional_native_entries"] == additional
    verify_native_lmf(read(LMF), additional)
    projected = copy.deepcopy(list(additional.values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    assert fixture["additional_native_entries"] == projected
    assert fixture["implemented_words"] == {
        r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
        for r in observed["source_diagnostic_streams"]["all"]
        if r["kind"] == "word"
    }
    if cli:
        assert dictionary and sha(dictionary) == snapshot["dictionary_sha256"]
        text, streams = run(cli, dictionary, sorted(fixture["implemented_words"]))
        assert text == source["before_input"]
        assert streams == observed["source_diagnostic_streams"], (
            "current -감 cohort changed: review explicit forward evidence"
        )
    print(
        f"Verified historical -감 source snapshot and {len(fixture['implemented_words'])} complete implemented words with {len(additional)} additional native owners; current CLI replay: {bool(cli)}."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    assert args.freeze != args.verify
    if args.freeze:
        assert args.cli and args.dictionary
        freeze(args.cli, args.dictionary)
    else:
        verify(args.cli, args.dictionary)


if __name__ == "__main__":
    main()
