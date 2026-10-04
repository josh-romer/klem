"""Preserve additional native owners exposed by the full-stream comparison."""

import argparse
import json
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, read, sha
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/reported-retrospective-source-preflight.json.gz"
CORRECTIONS = ROOT / "tests/fixtures/reported-retrospective-corrections.json"
ADDITIONAL = ROOT / "tests/fixtures/reported-retrospective-additional-native.json"
LMF = ROOT / "tests/fixtures/krdict-reported-retrospective-additional.json"
REPORT = ROOT / "docs/reported-retrospective-observations.json.gz"


def missing(report):
    known = (
        read(SOURCE)["complete_native_entries"]
        | read(CORRECTIONS)["complete_native_entries"]
    )
    return {
        i: e for i, e in report["complete_native_entries"].items() if i not in known
    }


def freeze(report):
    assert not ADDITIONAL.exists() and not LMF.exists()
    entries = missing(read(report))
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    ADDITIONAL.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(LMF),
                "dictionary_sha256": read(SOURCE)["dictionary_sha256"],
                "complete_native_entries": entries,
                "raw_source_sha256": hashes,
                "license": read(SOURCE)["license"],
                "scope": "Append-only native owners of new full-stream candidates and spacing options; original sources and judgments remain immutable.",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify(report=REPORT):
    f = read(ADDITIONAL)
    assert f["source_sha256"] == sha(SOURCE) and f["lmf_sha256"] == sha(LMF)
    assert f["dictionary_sha256"] == read(SOURCE)["dictionary_sha256"]
    assert f["complete_native_entries"] == missing(read(report))
    assert len(f["complete_native_entries"]) == 418
    assert (
        f["contextual_verdict"] == "unjudged" and f["independent_review"] == "pending"
    )
    verify_native_lmf(read(LMF), f["complete_native_entries"])
    print("Verified 418 complete additional native owners.")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--freeze", type=Path)
    p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    if a.freeze:
        freeze(a.freeze)
    verify(a.freeze or REPORT)
