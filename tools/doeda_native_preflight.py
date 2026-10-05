"""Freeze actual before results for all proposed native suffix cases."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_native_audit import FIXTURE
from doeda_native_audit import REPORT as REVIEW
from doeda_native_audit import verify_data as verify_review
from doeda_suffix_audit import SOURCE, referenced
from doeda_suffix_diagnostics import components_for, validate_components
from doeda_suffix_package import REPORT as PACKAGE
from lexical_nada_audit import ROOT, load_dictionary, read, sha, write

REPORT = ROOT / "docs/doeda-native-source-preflight.json.gz"


def cases(fixture):
    result = []
    for formation in fixture["formations"]:
        for variant in fixture["variants"]:
            later = variant.get("later_lemmas", [])
            result.append(
                {
                    "id": formation["id"] + "-" + variant["id"],
                    "formation_id": formation["id"],
                    "surface": formation["base"] + variant["tail"],
                    "lemmas": [{"text": formation["base"], "kind": "nominal"}, *later],
                    "morphemes": [
                        {"form": "되다", "kind": "suffix"},
                        *[
                            {"form": form, "kind": kind}
                            for form, kind in zip(
                                variant["morphemes"],
                                variant["morpheme_kinds"],
                                strict=True,
                            )
                        ],
                    ],
                    "required_rule": "suffix.verb.doeda",
                    "original_whole_lemmas": [
                        {"text": formation["head"], "kind": "predicate"},
                        *later,
                    ],
                    "source_reviews": formation["review_ids"],
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    assert len(result) == len({c["id"] for c in result}) == 15700
    assert len({c["surface"] for c in result}) == len(result)
    return result


def expected(analysis, case):
    return (
        analysis["lemmas"] == case["lemmas"]
        and analysis["morphemes"] == case["morphemes"]
        and case["required_rule"] in analysis["rules"]
    )


def words(stream):
    return {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in stream
        if r["kind"] == "word"
    }


def inspect(report):
    fixture = read(FIXTURE)
    proposed = cases(fixture)
    assert report["cases"] == proposed
    text = "\n".join(sorted(c["surface"] for c in proposed)) + "\n"
    assert report["before_input"] == text
    assert report["before_input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert set(report["before_streams"]) == {"raw", "headword", "compatible"}
    mappings = {}
    for mode, stream in report["before_streams"].items():
        assert len(stream) == 31400
        assert "".join(r["surface"] for r in stream) == text
        mapping = words(stream)
        assert sorted(mapping) == sorted(c["surface"] for c in proposed)
        mappings[mode] = mapping
        for c in proposed:
            assert not any(expected(a, c) for a in mapping[c["surface"]]["analyses"]), (
                c["id"]
            )
    for c in proposed:
        assert any(
            a["lemmas"] == c["original_whole_lemmas"]
            and a["morphemes"] == c["morphemes"][1:]
            for a in mappings["raw"][c["surface"]]["analyses"]
        ), (c["id"], "missing original whole-head parent")
    validate_components(
        report["original_parent_components"], list(mappings["raw"].values())
    )
    referenced_ids = referenced(report["before_streams"])
    source = read(SOURCE)
    # Preserve the complete original native source closure as well as every
    # owner newly referenced by these before streams.
    evidence_ids = set(source["complete_native_entries"])
    for r in read(REVIEW)["native_reviews"]:
        evidence_ids.add(r["native_entry_id"])
        evidence_ids.update(b["id"] for b in r["base_entry_reviews"])
    assert set(report["complete_native_entries"]) == referenced_ids | evidence_ids
    for ident, entry in report["complete_native_entries"].items():
        assert entry["id"] == ident and entry["senses"]
        if ident in source["complete_native_entries"]:
            assert entry == source["complete_native_entries"][ident]
    return len(proposed)


def freeze(args):
    assert not REPORT.exists()
    review, fixture, package = read(REVIEW), read(FIXTURE), read(PACKAGE)
    verify_review(review, fixture)
    assert sha(args.cli) == package["cli_sha256"]
    assert sha(args.dictionary) == read(SOURCE)["dictionary_sha256"]
    proposed = cases(fixture)
    text = "\n".join(sorted(c["surface"] for c in proposed)) + "\n"
    streams = {}
    for mode, flags in (
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        output = subprocess.run(
            [str(args.cli), "text", "-", "--dictionary", str(args.dictionary), *flags],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        streams[mode] = [json.loads(line) for line in output.stdout.splitlines()]
        print(mode, len(streams[mode]), "actual before records captured", flush=True)
    raw = words(streams["raw"])
    components = components_for(list(raw.values()), args.bridge)
    native = load_dictionary(args.dictionary)
    evidence = read(SOURCE)["complete_native_entries"]
    assert all(native[i] == e for i, e in evidence.items())
    ids = referenced(streams) | set(evidence)
    snapshots = {}
    for path in (
        "src/engine.rs",
        "src/doeda_suffix.rs",
        "src/breakdown.rs",
        "src/dictionary/attachment.rs",
    ):
        p = ROOT / path
        assert sha(p) == package["api"]["implementation_files"][path]["sha256"]
        snapshots[path] = {"text": p.read_text(), "sha256": sha(p)}
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "review_sha256": sha(REVIEW),
        "fixture_sha256": sha(FIXTURE),
        "previous_package_sha256": sha(PACKAGE),
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "bridge_sha256": sha(args.bridge),
        "implementation_files": snapshots,
        "before_input": text,
        "before_input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "cases": proposed,
        "before_streams": streams,
        "original_parent_components": components,
        "complete_native_entries": {i: native[i] for i in sorted(ids)},
        "scope": "Actual before results for all 15,700 native structural proposals in three filters (94,200 records), original whole-head parents and ordered components, full referenced native entry closure, and exact packaged implementation. Original source/corpus gold remains unchanged. These hypotheses remain unjudged in context and independently unreviewed.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    inspect(report)
    write(REPORT, report)
    verify()


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    for key, path in (
        ("source_sha256", SOURCE),
        ("review_sha256", REVIEW),
        ("fixture_sha256", FIXTURE),
        ("previous_package_sha256", PACKAGE),
    ):
        assert report[key] == sha(path)
    package = read(PACKAGE)
    assert report["cli_sha256"] == package["cli_sha256"]
    assert report["dictionary_sha256"] == read(SOURCE)["dictionary_sha256"]
    for path, snapshot in report["implementation_files"].items():
        assert (
            hashlib.sha256(snapshot["text"].encode()).hexdigest() == snapshot["sha256"]
        )
        assert snapshot == package["api"]["implementation_files"][path]
    total = inspect(report)
    print(
        "Verified",
        total,
        "native source cases and 94,200 original filter records with complete native closure and whole-head ownership.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("cli", "dictionary", "bridge"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary and args.bridge
        freeze(args)
