"""Append native owners missing from the frozen legacy spacing fixture."""

import argparse
import json
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, SOURCE, load_dictionary, read, sha
from native_lmf import verify_native_lmf

FIXTURE = ROOT / "tests/fixtures/lexical-nada-spacing.json"
DEPENDENCY = ROOT / "tests/fixtures/lexical-nada-dependencies.json"
SUPPLEMENT = ROOT / "tests/fixtures/lexical-nada-priority-supplement.json"
LMF = ROOT / "tests/fixtures/krdict-lexical-nada-priority.json"


def missing():
    fixture = read(FIXTURE)
    known = {e["id"] for e in fixture["source_entries"]} | read(DEPENDENCY)[
        "complete_native_entries"
    ].keys()
    required = {
        e["id"]
        for word in fixture["before_legacy_words"].values()
        for h in word["spacing"]["alternatives"]
        for record in h["records"]
        for lemma in record["dictionary"]["lemmas"]
        for e in lemma["entries"]
    }
    return required - known


def freeze(dictionary):
    assert not SUPPLEMENT.exists() and not LMF.exists()
    source = read(SOURCE)
    assert sha(dictionary) == source["dictionary_sha256"]
    native = load_dictionary(dictionary)
    entries = {i: native[i] for i in sorted(missing())}
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    value = {
        "schema_version": 1,
        "checklist": "COV-020r",
        "original_fixture_sha256": sha(FIXTURE),
        "dependency_sha256": sha(DEPENDENCY),
        "dictionary_sha256": sha(dictionary),
        "lmf_sha256": sha(LMF),
        "raw_source_sha256": hashes,
        "complete_native_entries": entries,
        "license": source["license"],
        "scope": "Append-only native owners for every frozen legacy spacing segment. The omitted 으 noun is the name of the Hangul vowel; preserving its existing contracted-object hypothesis does not adjudicate a sentence context.",
    }
    SUPPLEMENT.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def verify():
    value = read(SUPPLEMENT)
    assert value["original_fixture_sha256"] == sha(FIXTURE)
    assert value["dependency_sha256"] == sha(DEPENDENCY)
    assert value["dictionary_sha256"] == read(SOURCE)["dictionary_sha256"]
    assert value["lmf_sha256"] == sha(LMF)
    assert set(value["complete_native_entries"]) == missing() == {"krdict:68795"}
    entry = value["complete_native_entries"]["krdict:68795"]
    assert (entry["headword"], entry["pos"], entry["homonym"]) == ("으", "명사", "0")
    verify_native_lmf(read(LMF), value["complete_native_entries"])
    print("Every frozen legacy spacing segment now has its full native owner")


def main():
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


if __name__ == "__main__":
    main()
