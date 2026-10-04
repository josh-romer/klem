"""Track each changed candidate/spacing option in the complete source cohort.

This checkpoint covers the frozen 155 words and all three dictionary filters.
Broader candidate/novel streams and packaged API/browser checks are separate.
"""

import argparse
import hashlib
from pathlib import Path

from emphatic_ending_audit import FIXTURE, SOURCE
from lexical_nada_audit import ROOT, read, run, sha, write
from lexical_nada_compare import Audit, canon, native_owners

REPORT = ROOT / "docs/emphatic-ending-diagnostics.json.gz"
RULES = {"ending.emphatic_purpose", "ending.emphatic_affirmation"}


class EmphaticAudit(Audit):
    def __init__(self, cli, dictionary):
        review = read(ROOT / "docs/lexical-nada-source-review.json")
        super().__init__(
            cli,
            dictionary,
            {r["noun"]: r["noun_entry"] for r in review["finite_pair_proposals"]},
            "ending",
            ("게끔", "고말고", "다마다"),
        )

    def word(self, before, after):
        added = super().word(before, after)
        assert all(RULES.intersection(a["rules"]) for a in added)
        return added

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "emphatic-ending-"
            + category
            + "-"
            + hashlib.sha256(key.encode()).hexdigest()[:24]
        )


def inspect(source, streams, audit):
    counts = []
    fixture = read(FIXTURE)
    for mode in ("all", "headword", "compatible"):
        before, after = source["before_streams"][mode], streams[mode]
        assert len(before) == len(after)
        changed = 0
        for index, (old, new) in enumerate(zip(before, after, strict=True)):
            if old == new:
                continue
            changed += 1
            surface = new["surface"]
            audit.record(
                old,
                new,
                mode,
                {
                    "mode": mode,
                    "record": index,
                    "span": new["span"],
                    "context": surface,
                    "source_discovery_ids": [
                        r["id"]
                        for r in source["discoveries"]
                        if r["surface"] == surface
                    ],
                    "source_case_ids": [
                        r["id"] for r in fixture["cases"] if r["surface"] == surface
                    ],
                },
            )
        counts.append({"mode": mode, "records": len(after), "changed_records": changed})
    return counts


def freeze(cli, dictionary, output):
    assert not output.exists()
    source, fixture = read(SOURCE), read(FIXTURE)
    assert sha(dictionary) == source["dictionary_sha256"]
    text, streams = run(cli, dictionary, sorted(fixture["before_words"]))
    assert text == source["before_input"]
    audit = EmphaticAudit(cli, dictionary)
    comparisons = inspect(source, streams, audit)
    changes = list(audit.changes.values())
    native = native_owners(
        changes
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
            "fixture_sha256": sha(FIXTURE),
            "before_cli_sha256": source["cli_sha256"],
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "scope": "Complete 155-word source diagnostics in three filters, preserving every old candidate/reading/native field and spacing order. Broad streams and packaged API/browser verification remain separate.",
            "comparisons": comparisons,
            "source_diagnostic_streams": streams,
            "independent_words": audit.words,
            "changes": changes,
            "complete_native_entries": native,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(f"Archived {len(changes)} distinct source-diagnostic changes: {comparisons}")


def verify():
    report, source = read(REPORT), read(SOURCE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bw"
    assert report["source_sha256"] == sha(SOURCE) and report["fixture_sha256"] == sha(
        FIXTURE
    )
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    audit = EmphaticAudit(None, None)
    audit.words = report["independent_words"].copy()
    assert (
        inspect(source, report["source_diagnostic_streams"], audit)
        == report["comparisons"]
    )
    assert list(audit.changes.values()) == report["changes"]
    assert all(
        r["contextual_verdict"] == "unjudged" and r["independent_review"] == "pending"
        for r in report["changes"]
    )
    # Every retained native identity must have its full preserved source.
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

    for r in report["changes"]:
        if r["category"] != "work":
            visit(r["before"])
            visit(r["after"])
    visit(report["independent_words"])
    assert identifiers == report["complete_native_entries"].keys()
    for ident, entry in report["complete_native_entries"].items():
        assert ident == entry["id"] and entry["senses"]
        if ident in source["complete_native_entries"]:
            assert entry == source["complete_native_entries"][ident]
    print(
        f"Verified {len(report['changes'])} individually tracked source-diagnostic changes in all three filters; broad/runtime/contextual verification remains separate."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.cli and a.dictionary and a.output
        freeze(a.cli.resolve(), a.dictionary.resolve(), a.output)
