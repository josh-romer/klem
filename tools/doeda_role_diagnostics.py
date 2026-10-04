"""Track every changed candidate in the complete frozen 되다 source cohort."""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_role_audit import FIXTURE, SOURCE, referenced_ids
from lexical_nada_audit import ROOT, read, run, sha, write
from lexical_nada_compare import Audit, canon, native_owners

REPORT = ROOT / "docs/doeda-role-diagnostics.json.gz"
RULE = "lexical.doeda.complement"


class DoedaAudit(Audit):
    def __init__(self, cli=None, dictionary=None, before_cli=None, parents=None):
        super().__init__(cli, dictionary, {}, RULE, ("게", "게끔"))
        self.before_cli = before_cli
        self.parents = {} if parents is None else parents
        self.before_independent_words = {}

    def parent(self, surface):
        if surface in self.parents:
            return self.parents[surface]
        if surface not in self.before_independent_words:
            assert self.before_cli is not None
            self.before_independent_words[surface] = json.loads(
                subprocess.check_output(
                    [
                        str(self.before_cli),
                        "word",
                        surface,
                        "--dictionary",
                        str(self.db),
                    ]
                )
            )
        return self.before_independent_words[surface]["analyses"]

    def word(self, before, after):
        added = super().word(before, after)
        for analysis in added:
            # The new path is an attributed role alternative of an original
            # raw analysis, including when filtering had excluded that parent.
            parent = copy.deepcopy(analysis)
            for index, lemma in enumerate(parent["lemmas"]):
                # Retain independently lexical token-initial 되다. Only
                # following roles can be a projection of an auxiliary.
                if index > 0 and lemma == {"text": "되다", "kind": "predicate"}:
                    lemma["kind"] = "auxiliary"
            parent["rules"] = sorted(set(parent["rules"]) - {RULE})
            if "auxiliary" not in parent["rules"]:
                parent["rules"].append("auxiliary")
                parent["rules"].sort()
            assert parent in self.parent(before["normalized"]), (
                before["normalized"],
                "new role lacks original structural parent",
                analysis,
            )
        return added

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "doeda-role-"
            + category
            + "-"
            + hashlib.sha256(key.encode()).hexdigest()[:24]
        )


def parents(source):
    return {
        r["surface"]: r["analysis"]["analyses"]
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }


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
                        h["id"]
                        for h in source["discoveries"]
                        if surface in (h["left"], h["right"], h["left"] + h["right"])
                    ],
                    "source_case_ids": [
                        c["id"] for c in fixture["cases"] if c["surface"] == surface
                    ],
                },
            )
        counts.append({"mode": mode, "records": len(after), "changed_records": changed})
    return counts


def freeze(cli, dictionary, before_cli, output):
    assert not output.exists()
    source = read(SOURCE)
    assert sha(dictionary) == source["dictionary_sha256"]
    assert sha(before_cli) == source["cli_sha256"]
    surfaces = list(parents(source))
    text, streams = run(cli, dictionary, surfaces)
    assert text == source["before_input"]
    audit = DoedaAudit(cli, dictionary, before_cli, parents(source))
    comparisons = inspect(source, streams, audit)
    changes = list(audit.changes.values())
    # Full native entries for independent spacing words not already archived
    # are retained separately; shared entries are checked exactly.
    all_native = native_owners(
        changes
        + [
            {"category": "candidate", "before": None, "after": w}
            for w in audit.words.values()
        ]
        + [
            {"category": "candidate", "before": None, "after": w}
            for w in audit.before_independent_words.values()
        ],
        dictionary,
    )
    shared = source["complete_native_entries"]
    for ident, entry in all_native.items():
        if ident in shared:
            assert shared[ident] == entry
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-019ag",
            "source_sha256": sha(SOURCE),
            "fixture_sha256": sha(FIXTURE),
            "before_cli_sha256": sha(before_cli),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "attachment_sha256": sha(ROOT / "src/dictionary/attachment.rs"),
            "scope": "Complete 4,787-word preflight cohort in three filters, preserving prior candidates/native fields/spacing order. Every new role has an exact original raw parent. Broad streams, full held-out recall and packaged reader checks are separate.",
            "comparisons": comparisons,
            "source_diagnostic_streams": streams,
            "independent_words": audit.words,
            "before_independent_words": audit.before_independent_words,
            "changes": changes,
            "native_ids": sorted(all_native),
            "additional_native_entries": {
                i: e for i, e in all_native.items() if i not in shared
            },
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(f"Archived {len(changes)} distinct role/spacing changes: {comparisons}")


def verify():
    source, report = read(SOURCE), read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ag"
    assert report["source_sha256"] == sha(SOURCE) and report["fixture_sha256"] == sha(
        FIXTURE
    )
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    audit = DoedaAudit(parents=parents(source))
    audit.words = report["independent_words"].copy()
    audit.before_independent_words = report["before_independent_words"].copy()
    assert (
        inspect(source, report["source_diagnostic_streams"], audit)
        == report["comparisons"]
    )
    assert list(audit.changes.values()) == report["changes"]
    ids = referenced_ids(report["independent_words"]) | referenced_ids(
        report["before_independent_words"]
    )
    for change in report["changes"]:
        if change["category"] != "work":
            ids |= referenced_ids(change["before"]) | referenced_ids(change["after"])
    assert sorted(ids) == report["native_ids"]
    native = source["complete_native_entries"]
    assert set(report["additional_native_entries"]) == ids - native.keys()
    for ident, entry in report["additional_native_entries"].items():
        assert entry["id"] == ident and entry["senses"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert all(
        c["contextual_verdict"] == "unjudged" and c["independent_review"] == "pending"
        for c in report["changes"]
    )
    print(
        f"Verified {len(report['changes'])} individual role/spacing changes in three complete source streams, exact original parents and unchanged prior native assessments; broader/contextual review remains separate."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--before-cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.cli and a.before_cli and a.dictionary and a.output
        freeze(
            a.cli.resolve(), a.dictionary.resolve(), a.before_cli.resolve(), a.output
        )
