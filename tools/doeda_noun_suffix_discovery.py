"""Retain the observed noun/-되다 dictionary gap without inventing new gold."""

import argparse
import json
import sqlite3
import subprocess
from pathlib import Path

from doeda_complement_audit import SOURCE
from doeda_complement_corpora import REPORT as CORPORA
from doeda_complement_diagnostics import REPORT as DIAGNOSTICS
from doeda_complement_diagnostics import ComplementAudit
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-noun-suffix-discovery.json.gz"
SURFACE = "타도되었다"
SOURCES = {"krdict:74902": "-되다", "krdict:79461": "타도", "krdict:79462": "타도하다"}


def referenced(value):
    result = set()
    if isinstance(value, dict):
        ident = value.get("id")
        if isinstance(ident, str) and ident.startswith("krdict:"):
            result.add(ident)
        for item in value.values():
            result.update(referenced(item))
    elif isinstance(value, list):
        for item in value:
            result.update(referenced(item))
    return result


def inspect(report):
    corpus, source, diagnostics = read(CORPORA), read(SOURCE), read(DIAGNOSTICS)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["corpus_report_sha256"] == sha(CORPORA)
    assert report["source_preflight_sha256"] == sha(SOURCE)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["cli_sha256"] == diagnostics["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    target = corpus["changed_words"][SURFACE]
    assert report["original_occurrences"] == target["occurrences"]
    audit = ComplementAudit()
    assert set(report["streams"]) == {"all", "headword", "compatible"}
    for mode, pair in report["streams"].items():
        audit.word(pair["before"], pair["after"])
        for name in ("before", "after"):
            record = pair[name]
            assert (
                record["dictionary"]["fingerprint"] == report["dictionary_fingerprint"]
            )
            if mode == "all":
                assert {k: v for k, v in record.items() if k != "dictionary"} == target[
                    name
                ]
            else:
                raw = report["streams"]["all"][name]
                wanted = [
                    (a, r)
                    for a, r in zip(
                        raw["analyses"], raw["dictionary"]["readings"], strict=True
                    )
                    if all(
                        any(
                            slot["lemma"] == lemma and slot["entries"]
                            for slot in raw["dictionary"]["lemmas"]
                        )
                        for lemma in a["lemmas"]
                    )
                    and (mode == "headword" or r["status"] != "incompatible")
                ]
                assert record["analyses"] == [a for a, _ in wanted]
                assert record["dictionary"]["readings"] == [r for _, r in wanted]
                assert record["dictionary"]["lemmas"] == [
                    slot
                    for slot in raw["dictionary"]["lemmas"]
                    if any(slot["lemma"] in a["lemmas"] for a, _ in wanted)
                ]
    assert report["headword_lookup"] == {"타도되다": []}
    ids = referenced(report["streams"]) | SOURCES.keys()
    assert ids == report["complete_native_entries"].keys()
    for ident, entry in report["complete_native_entries"].items():
        assert entry["id"] == ident and entry["senses"]
        if ident in SOURCES:
            assert entry["headword"] == SOURCES[ident]
        for prior in (
            source["complete_native_entries"],
            diagnostics["additional_native_entries"],
        ):
            if ident in prior:
                assert entry == prior[ident]
    assert report["complete_native_entries"]["krdict:74902"]["pos"] == "접사"
    assert report["disposition"] == "unimplemented-source-and-representation-audit"
    assert report["contextual_verdict"] == "unjudged"
    assert report["independent_review"] == "pending"
    print(
        "Verified original 타도되었다 context, three before/after native filter streams, complete suffix/noun sources and the missing whole head; no gold or global candidate ban added."
    )


def freeze(before, cli, dictionary, output):
    assert not output.exists()
    source, diagnostics = read(SOURCE), read(DIAGNOSTICS)
    assert sha(before) == source["cli_sha256"]
    assert sha(cli) == diagnostics["cli_sha256"]
    assert sha(dictionary) == source["dictionary_sha256"]
    streams = {}
    for mode, flags in (
        ("all", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        streams[mode] = {
            name: json.loads(
                subprocess.check_output(
                    [
                        str(binary),
                        "word",
                        SURFACE,
                        "--dictionary",
                        str(dictionary),
                        *flags,
                    ]
                )
            )
            for name, binary in (("before", before), ("after", cli))
        }
    ids = referenced(streams) | SOURCES.keys()
    native = {}
    with sqlite3.connect(dictionary.resolve().as_uri() + "?mode=ro", uri=True) as db:
        for ident in sorted(ids):
            (raw,) = db.execute(
                "SELECT data FROM entries WHERE id=?", (ident,)
            ).fetchone()
            native[ident] = json.loads(raw)
        absent = [
            json.loads(raw)
            for (raw,) in db.execute(
                "SELECT data FROM entries WHERE headword=?", ("타도되다",)
            )
        ]
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "id": "doeda-noun-suffix-ta-do-gold-filter-gap",
        "corpus_report_sha256": sha(CORPORA),
        "source_preflight_sha256": sha(SOURCE),
        "before_cli_sha256": sha(before),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "dictionary_fingerprint": streams["all"]["after"]["dictionary"]["fingerprint"],
        "original_occurrences": read(CORPORA)["changed_words"][SURFACE]["occurrences"],
        "streams": streams,
        "complete_native_entries": native,
        "headword_lookup": {"타도되다": absent},
        "disposition": "unimplemented-source-and-representation-audit",
        "scope": "One original held-out token. Dictionary presence/POS compatibility retain grammatically possible 타다 + 되다 paths while the annotated whole derived head is missing. Review noun/root/adverb attachment and suffix-owned inflections against both complete -되다 senses; do not replace the original annotation or globally forbid the homographic alternatives.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    inspect(report)
    write(output, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--before-cli", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        inspect(read(REPORT))
    else:
        assert args.before_cli and args.cli and args.dictionary and args.output
        freeze(
            args.before_cli.resolve(),
            args.cli.resolve(),
            args.dictionary.resolve(),
            args.output,
        )
