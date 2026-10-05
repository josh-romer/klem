"""Attribute all changes in the eight fully captured broad candidate/novel streams.

The capture preserves complete paired records and original stream hashes. This
second stage independently replays original raw parents and spacing segments,
checks exact suffix ownership, and retains complete native entry evidence.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_complement_compare import inspect
from doeda_native_diagnostics import REPORT as DIAGNOSTICS
from doeda_native_diagnostics import NativeAudit
from doeda_native_package import REPORT as PACKAGE
from doeda_native_preflight import REPORT as SOURCE
from doeda_suffix_audit import referenced
from doeda_suffix_diagnostics import components_for, validate_components
from lexical_nada_audit import ROOT, read, sha, write
from lexical_nada_compare import native_owners

PRIOR = ROOT / "docs/doeda-suffix-observations.json.gz"
REPORT = ROOT / "docs/doeda-native-observations.json.gz"


def surfaces(pairs):
    result = set()

    def visit(value):
        if isinstance(value, dict):
            if value.get("analysis") is not None and "surface" in value:
                result.add(value["surface"])
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(pairs)
    return sorted(result)


def replay(cli, dictionary, words):
    out = subprocess.run(
        [str(cli), "text", "-", "--dictionary", str(dictionary)],
        input="\n".join(words) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    records = [json.loads(line) for line in out.stdout.splitlines()]
    result = {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in records
        if r["kind"] == "word"
    }
    assert sorted(result) == words
    return result


def freeze(args):
    assert not args.output.exists()
    source, prior, package = read(SOURCE), read(PRIOR), read(PACKAGE)
    receipt = read(args.capture)
    assert receipt["prior_sha256"] == sha(PRIOR)
    assert (
        receipt["before_cli_sha256"]
        == sha(args.before_cli)
        == source["cli_sha256"]
        == prior["cli_sha256"]
    )
    assert receipt["cli_sha256"] == sha(args.cli) == package["cli_sha256"]
    assert (
        receipt["dictionary_sha256"]
        == sha(args.dictionary)
        == source["dictionary_sha256"]
    )
    assert receipt["changed_pairs_sha256"] == sha(args.pairs)
    with gzip.open(args.pairs, "rt") as file:
        pairs = [json.loads(line) for line in file]
    words = surfaces(pairs)
    before = replay(args.before_cli, args.dictionary, words)
    after = replay(args.cli, args.dictionary, words)
    components = components_for([pairs, before], args.bridge)
    validate_components(components, [pairs, before])
    audit = NativeAudit(components, original_words=before)
    audit.words = after.copy()
    inspect(prior, receipt["comparisons"], pairs, audit)
    changes = list(audit.changes.values())
    native = native_owners(
        changes + [{"category": "candidate", "before": before, "after": after}],
        args.dictionary,
    )
    tool = args.capture_tool.read_text()
    write(
        args.output,
        {
            "schema_version": 1,
            "checklist": "COV-022m",
            "source_sha256": sha(SOURCE),
            "diagnostics_sha256": sha(DIAGNOSTICS),
            "package_sha256": sha(PACKAGE),
            "previous_observations_sha256": sha(PRIOR),
            "before_cli_sha256": receipt["before_cli_sha256"],
            "cli_sha256": receipt["cli_sha256"],
            "dictionary_sha256": receipt["dictionary_sha256"],
            "capture_receipt": receipt,
            "capture_tool": {
                "text": tool,
                "sha256": hashlib.sha256(tool.encode()).hexdigest(),
            },
            "comparisons": receipt["comparisons"],
            "changed_record_pairs": pairs,
            "original_parent_components": components,
            "independent_before_words": before,
            "independent_words": after,
            "changes": changes,
            "complete_native_entries": native,
            "old_candidates_native_readings_fields_and_spacing_order_preserved": True,
            "scope": "All eight native-expansion full streams (1,128,312 original records); complete changed pairs, exact source/old CLI stream hashes, individually named additions/occurrences, independently replayed original raw whole-head parents, source suffix owners, native slots/readings/relative order and complete native evidence. Original contexts retained. This is not contextual precision or independent/formal-history review.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(
        "Archived",
        len(pairs),
        "changed broad records and",
        len(changes),
        "individual changes, with",
        len(native),
        "complete native owners.",
    )


def verify():
    report, prior, source = read(REPORT), read(PRIOR), read(SOURCE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    for key, path in [
        ("source_sha256", SOURCE),
        ("diagnostics_sha256", DIAGNOSTICS),
        ("package_sha256", PACKAGE),
        ("previous_observations_sha256", PRIOR),
    ]:
        assert report[key] == sha(path)
    assert report["before_cli_sha256"] == source["cli_sha256"] == prior["cli_sha256"]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    receipt = report["capture_receipt"]
    assert receipt["comparisons"] == report["comparisons"]
    assert receipt["prior_sha256"] == sha(PRIOR)
    for key in ["before_cli_sha256", "cli_sha256", "dictionary_sha256"]:
        assert receipt[key] == report[key]
    assert (
        hashlib.sha256(report["capture_tool"]["text"].encode()).hexdigest()
        == report["capture_tool"]["sha256"]
    )
    pairs = report["changed_record_pairs"]
    assert (
        sorted(report["independent_before_words"])
        == sorted(report["independent_words"])
        == surfaces(pairs)
    )
    validate_components(
        report["original_parent_components"],
        [pairs, report["independent_before_words"]],
    )
    audit = NativeAudit(
        report["original_parent_components"],
        original_words=report["independent_before_words"],
    )
    audit.words = report["independent_words"].copy()
    inspect(prior, report["comparisons"], pairs, audit)
    assert list(audit.changes.values()) == report["changes"]
    ids = (
        referenced(report["changes"])
        | referenced(report["independent_before_words"])
        | referenced(report["independent_words"])
    )
    assert set(report["complete_native_entries"]) == ids
    shared = source["complete_native_entries"]
    for ident, entry in report["complete_native_entries"].items():
        assert entry["id"] == ident and entry["senses"]
        if ident in shared:
            assert entry == shared[ident]
    assert sum(c["records"] for c in report["comparisons"]) == 1128312
    assert report["old_candidates_native_readings_fields_and_spacing_order_preserved"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified eight complete broad streams,",
        len(pairs),
        "changed records,",
        len(report["changes"]),
        "attributed changes and",
        len(ids),
        "complete native owners; original candidate/native/slot/spacing order retained.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in [
        "capture",
        "pairs",
        "capture-tool",
        "before-cli",
        "cli",
        "dictionary",
        "bridge",
        "output",
    ]:
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert all(
            getattr(args, n.replace("-", "_"))
            for n in [
                "capture",
                "pairs",
                "capture-tool",
                "before-cli",
                "cli",
                "dictionary",
                "bridge",
                "output",
            ]
        )
        freeze(args)
