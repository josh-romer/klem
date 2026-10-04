"""Compare all eight pinned broad streams and retain every changed record.

The source diagnostic checkpoint remains immutable. This archive extends it
with complete candidate/novel streams, exact occurrences and full native owners.
"""

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

from emphatic_ending_audit import SOURCE
from emphatic_ending_diagnostics import REPORT as DIAGNOSTICS
from emphatic_ending_diagnostics import EmphaticAudit
from lexical_nada_audit import ROOT, read, sha, write
from lexical_nada_compare import native_owners

PRIOR = ROOT / "docs/gam-question-observations.json.gz"
REPORT = ROOT / "docs/emphatic-ending-observations.json.gz"


def inspect(prior, comparisons, pairs, audit):
    assert len(comparisons) == len(prior["comparisons"]) == 8
    offset = 0
    for old, current in zip(prior["comparisons"], comparisons, strict=True):
        for key in ("mode", "source", "source_sha256", "records"):
            assert current[key] == old[key]
        assert current["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        changed = pairs[offset : offset + current["changed_records"]]
        assert len(changed) == current["changed_records"]
        indices = []
        for row in changed:
            assert row["mode"] == current["mode"]
            location = row["location"]
            assert location["mode"] == row["mode"]
            assert 0 <= location["record"] < current["records"]
            assert location["span"] == row["after"]["span"]
            assert row["before"] != row["after"]
            indices.append(location["record"])
            audit.record(row["before"], row["after"], row["mode"], location)
        assert indices == sorted(set(indices))
        if not changed:
            assert current["before_jsonl_sha256"] == current["after_jsonl_sha256"]
        offset += len(changed)
    assert offset == len(pairs)


def freeze(before, cli, dictionary, output):
    assert not output.exists()
    source, diagnostics, prior = read(SOURCE), read(DIAGNOSTICS), read(PRIOR)
    assert sha(before) == source["cli_sha256"]
    assert sha(cli) == diagnostics["cli_sha256"]
    assert sha(dictionary) == source["dictionary_sha256"]
    audit = EmphaticAudit(cli, dictionary)
    comparisons, pairs = [], []
    for old in prior["comparisons"]:
        mode, path = old["mode"], Path(old["source"])
        assert sha(path) == old["source_sha256"]
        text = path.read_bytes()
        flags = (
            ["--dict-compatible"]
            if "compatible" in mode
            else ["--dict-only"]
            if "headword" in mode
            else []
        )
        command = ["text", str(path), "--dictionary", str(dictionary), *flags]
        if "spacing" in mode:
            command.append("--suggest-spacing")
        procs = [
            subprocess.Popen([str(c), *command], stdout=subprocess.PIPE)
            for c in (before, cli)
        ]
        hashes = [hashlib.sha256(), hashlib.sha256()]
        count = changed = 0
        try:
            for b, a in itertools.zip_longest(*(p.stdout for p in procs)):
                assert b is not None and a is not None
                hashes[0].update(b)
                hashes[1].update(a)
                if b != a:
                    br, ar = json.loads(b), json.loads(a)
                    span = ar["span"]
                    location = {
                        "mode": mode,
                        "record": count,
                        "span": span,
                        "context": text[
                            max(0, span["start"] - 120) : min(
                                len(text), span["end"] + 120
                            )
                        ].decode(errors="replace"),
                    }
                    audit.record(br, ar, mode, location)
                    pairs.append(
                        {"mode": mode, "location": location, "before": br, "after": ar}
                    )
                    changed += 1
                count += 1
                if count % 25000 == 0:
                    print(mode, count, "records checked", flush=True)
            assert all(p.wait() == 0 for p in procs)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait()
        assert (
            count == old["records"]
            and hashes[0].hexdigest() == old["after_jsonl_sha256"]
        )
        comparisons.append(
            {
                "mode": mode,
                "source": old["source"],
                "source_sha256": old["source_sha256"],
                "records": count,
                "before_jsonl_sha256": hashes[0].hexdigest(),
                "after_jsonl_sha256": hashes[1].hexdigest(),
                "changed_records": changed,
            }
        )
        print(mode, count, "records;", changed, "changed", flush=True)
    changes = list(audit.changes.values())
    native = native_owners(
        changes
        + [
            {"category": "candidate", "before": row["before"], "after": row["after"]}
            for row in pairs
        ]
        + [
            {"category": "candidate", "before": None, "after": w}
            for w in audit.words.values()
        ],
        dictionary,
    )
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-017bw",
            "source_sha256": sha(SOURCE),
            "diagnostics_sha256": sha(DIAGNOSTICS),
            "previous_observations_sha256": sha(PRIOR),
            "before_cli_sha256": sha(before),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "comparisons": comparisons,
            "changed_record_pairs": pairs,
            "independent_words": audit.words,
            "changes": changes,
            "complete_native_entries": native,
            "old_candidates_native_readings_fields_and_spacing_order_preserved": True,
            "scope": "Eight complete candidate/novel streams. All changed record pairs and individual hypotheses are retained; contextual and independent judgments remain pending.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print("Tracked broad changes:", len(changes), flush=True)


def verify():
    report, source, diagnostics, prior = (
        read(REPORT),
        read(SOURCE),
        read(DIAGNOSTICS),
        read(PRIOR),
    )
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bw"
    assert report["source_sha256"] == sha(SOURCE)
    assert report["diagnostics_sha256"] == sha(DIAGNOSTICS)
    assert report["previous_observations_sha256"] == sha(PRIOR)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["cli_sha256"] == diagnostics["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    audit = EmphaticAudit(None, None)
    audit.words = report["independent_words"].copy()
    inspect(prior, report["comparisons"], report["changed_record_pairs"], audit)
    assert list(audit.changes.values()) == report["changes"]
    assert all(
        r["contextual_verdict"] == "unjudged" and r["independent_review"] == "pending"
        for r in report["changes"]
    )
    assert report["old_candidates_native_readings_fields_and_spacing_order_preserved"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    identifiers = set()

    def visit(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                identifiers.add(ident)
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    for pair in report["changed_record_pairs"]:
        visit(pair["before"])
        visit(pair["after"])
    for change in report["changes"]:
        if change["category"] != "work":
            visit(change["before"])
            visit(change["after"])
    visit(report["independent_words"])
    assert identifiers == report["complete_native_entries"].keys()
    for ident, entry in report["complete_native_entries"].items():
        assert entry["id"] == ident and entry["senses"]
        if ident in source["complete_native_entries"]:
            assert entry == source["complete_native_entries"][ident]
        if ident in diagnostics["complete_native_entries"]:
            assert entry == diagnostics["complete_native_entries"][ident]
    print(
        f"Verified eight complete broad streams ({sum(r['records'] for r in report['comparisons']):,} records), {len(report['changed_record_pairs'])} changed records and {len(report['changes'])} individual hypotheses; old paths/native fields/spacing order retained."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--before-cli", type=Path)
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.before_cli and a.cli and a.dictionary and a.output
        freeze(
            a.before_cli.resolve(), a.cli.resolve(), a.dictionary.resolve(), a.output
        )
