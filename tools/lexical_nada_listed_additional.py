"""Retain newly exposed native homonyms without replacing the original source freeze."""

import argparse
import json
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, load_dictionary, read, sha
from lexical_nada_listed_fixtures import BEFORE
from native_lmf import verify_native_lmf

ADDITIONAL = ROOT / "tests/fixtures/lexical-nada-listed-additional-native.json"
LMF = ROOT / "tests/fixtures/krdict-lexical-nada-listed-additional.json"


def freeze(dictionary):
    assert not ADDITIONAL.exists() and not LMF.exists()
    before = read(BEFORE)
    assert sha(dictionary) == before["dictionary_sha256"]
    report = read(ROOT / "docs/lexical-nada-listed-observations.json.gz")
    assert report["dictionary_sha256"] == before["dictionary_sha256"]
    entries = {
        i: e
        for i, e in report["complete_native_entries"].items()
        if i not in before["complete_native_entries"]
    }
    native = load_dictionary(dictionary)
    assert all(e == native[i] for i, e in entries.items())
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
                "source_sha256": sha(BEFORE),
                "dictionary_sha256": sha(dictionary),
                "lmf_sha256": sha(LMF),
                "raw_source_sha256": hashes,
                "complete_native_entries": entries,
                "license": before["license"],
                "scope": "Append-only full native owners exposed by the new spacing records; original pre-extension sources and outputs remain immutable.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify():
    additional = read(ADDITIONAL)
    before = read(BEFORE)
    report = read(ROOT / "docs/lexical-nada-listed-observations.json.gz")
    assert additional["source_sha256"] == sha(BEFORE)
    assert additional["dictionary_sha256"] == before["dictionary_sha256"]
    assert additional["lmf_sha256"] == sha(LMF)
    assert additional["complete_native_entries"] == {
        i: e
        for i, e in report["complete_native_entries"].items()
        if i not in before["complete_native_entries"]
    }
    assert set(additional["complete_native_entries"]) == {
        "krdict:78367",
        "krdict:91736",
    }
    verify_native_lmf(read(LMF), additional["complete_native_entries"])
    print("Verified two complete additional native dictionary owners.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.dictionary:
        freeze(args.dictionary)
        verify()
    else:
        parser.error("freeze requires --dictionary")
