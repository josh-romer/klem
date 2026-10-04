"""Track every candidate and spacing change in the complete 되다 complement cohort."""

import argparse
import hashlib
from pathlib import Path

from doeda_complement_audit import FIXTURE, SOURCE, referenced_ids
from doeda_complement_regressions import BOUNDARIES, CORRECTIONS, effective_cases
from emphatic_ending_runtime import verify_stream
from lexical_nada_audit import ROOT, read, run, sha, write
from lexical_nada_compare import RULE, Audit, canon, native_owners

REPORT = ROOT / "docs/doeda-complement-diagnostics.json.gz"
RULES = {"lexical.doeda.extended", "auxiliary.doeda.extended"}


class ComplementAudit(Audit):
    def __init__(self, cli=None, dictionary=None):
        super().__init__(cli, dictionary, {}, "lexical.doeda.extended")

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "doeda-complement-"
            + category
            + "-"
            + hashlib.sha256(key.encode()).hexdigest()[:24]
        )

    def word(self, before, after):
        assert before["normalized"] == after["normalized"]
        old, new = before["analyses"], after["analyses"]
        assert [a for a in new if a in old] == old, (
            before["normalized"],
            "candidate loss/order",
        )
        added = [a for a in new if a not in old]
        for a in added:
            assert RULES & set(a["rules"]), (
                before["normalized"],
                "unattributed addition",
                a,
            )
            assert any(
                l == {"text": "되다", "kind": role}
                for l in a["lemmas"][1:]
                for role in ("predicate", "auxiliary")
            )
        for key in before.keys() - {"analyses", "dictionary", "breakdowns"}:
            assert before[key] == after[key], key
        for b, a in zip(old, [a for a in new if a in old], strict=True):
            bi, ai = old.index(b), new.index(a)
            assert (
                before["dictionary"]["readings"][bi]
                == after["dictionary"]["readings"][ai]
            )
            if "breakdowns" in before:
                assert before["breakdowns"][bi] == after["breakdowns"][ai]
        bd, ad = before["dictionary"], after["dictionary"]
        for k in bd.keys() - {"readings", "lemmas"}:
            assert bd[k] == ad[k]
        for slot in bd["lemmas"]:
            assert slot in ad["lemmas"], (before["normalized"], "native slot change")
        assert len(ad["readings"]) == len(new)
        return added

    def record(self, before, after, mode, location):
        surface = after["surface"]
        ignored = {"analysis", "dictionary", "breakdowns", "spacing"}
        assert {k: v for k, v in before.items() if k not in ignored} == {
            k: v for k, v in after.items() if k not in ignored
        }
        assert (before.get("analysis") is None) == (after.get("analysis") is None)
        if before.get("analysis") is not None:
            b = dict(
                before["analysis"],
                dictionary=before["dictionary"],
                **(
                    {"breakdowns": before["breakdowns"]}
                    if "breakdowns" in before
                    else {}
                ),
            )
            a = dict(
                after["analysis"],
                dictionary=after["dictionary"],
                **(
                    {"breakdowns": after["breakdowns"]} if "breakdowns" in after else {}
                ),
            )
            added = self.word(b, a)
            if added:
                for path in added:
                    i = a["analyses"].index(path)
                    self.remember(
                        "candidate",
                        surface,
                        None,
                        dict(
                            analysis=path,
                            reading=a["dictionary"]["readings"][i],
                            **(
                                {"breakdown": a["breakdowns"][i]}
                                if "breakdowns" in a
                                else {}
                            ),
                        ),
                        location,
                    )
        if "spacing" not in before:
            return
        bs, ns = before["spacing"], after["spacing"]
        assert bs["limits"] == ns["limits"] and bs["rule"] == ns["rule"]
        assert ns["segment_probes"] <= ns["limits"]["segment_probes"]
        assert len(ns["alternatives"]) <= ns["limits"]["alternatives"]
        assert ns["complete"] or ns["limited_by"]
        key = lambda h: (h.get("rule"), h["spaced"], tuple(h["inserted_at"]))
        oldkeys = [key(h) for h in bs["alternatives"]]
        newkeys = [key(h) for h in ns["alternatives"]]
        assert [k for k in newkeys if k in oldkeys] == oldkeys, (
            surface,
            "spacing loss/order",
        )
        for h in ns["alternatives"]:
            self.verify_hyp(h, after)
            k = key(h)
            if k not in oldkeys:
                if h.get("rule") != RULE:
                    assert any(
                        bool(RULES & set(a["rules"]))
                        for r in h["records"]
                        for a in r["analysis"]["analyses"]
                    ), (surface, "unexplained old-family addition")
                self.remember("spacing", surface, None, h, location)
            else:
                old = bs["alternatives"][oldkeys.index(k)]
                if old != h:
                    assert {k: v for k, v in old.items() if k != "records"} == {
                        k: v for k, v in h.items() if k != "records"
                    }
                    for br, ar in zip(old["records"], h["records"], strict=True):
                        self.word(
                            dict(
                                br["analysis"],
                                dictionary=br["dictionary"],
                                breakdowns=br["breakdowns"],
                            ),
                            dict(
                                ar["analysis"],
                                dictionary=ar["dictionary"],
                                breakdowns=ar["breakdowns"],
                            ),
                        )
                        assert {
                            k: v
                            for k, v in br.items()
                            if k not in {"analysis", "dictionary", "breakdowns"}
                        } == {
                            k: v
                            for k, v in ar.items()
                            if k not in {"analysis", "dictionary", "breakdowns"}
                        }
                    self.remember("spacing-update", surface, old, h, location)
        bmeta = {k: v for k, v in bs.items() if k != "alternatives"}
        ameta = {k: v for k, v in ns.items() if k != "alternatives"}
        if bmeta != ameta:
            self.remember("work", surface, bmeta, ameta, location)


def inspect(source, streams, audit):
    comparisons = []
    for mode in ("all", "headword", "compatible"):
        before, after = source["before_streams"][mode], streams[mode]
        verify_stream(after, streams["all"], mode, source["before_input"])
        assert len(before) == len(after)
        changed = 0
        for index, (old, new) in enumerate(zip(before, after, strict=True)):
            if old == new:
                continue
            changed += 1
            audit.record(
                old,
                new,
                mode,
                {
                    "mode": mode,
                    "record": index,
                    "span": new["span"],
                    "context": new["surface"],
                },
            )
        comparisons.append(
            {"mode": mode, "records": len(after), "changed_records": changed}
        )
    return comparisons


def freeze(cli, dictionary, output):
    assert not output.exists()
    source = read(SOURCE)
    assert sha(dictionary) == source["dictionary_sha256"]
    words = [
        r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
    ]
    text, streams = run(cli, dictionary, words)
    assert text == source["before_input"]
    audit = ComplementAudit(cli, dictionary)
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
    shared = source["complete_native_entries"]
    for ident, entry in native.items():
        if ident in shared:
            assert shared[ident] == entry
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-019ah",
            "source_sha256": sha(SOURCE),
            "fixture_sha256": sha(FIXTURE),
            "corrections_sha256": sha(CORRECTIONS),
            "bridge_boundaries_sha256": sha(BOUNDARIES),
            "before_cli_sha256": source["cli_sha256"],
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "attachment_sha256": sha(ROOT / "src/dictionary/attachment.rs"),
            "comparisons": comparisons,
            "source_diagnostic_streams": streams,
            "independent_words": audit.words,
            "changes": changes,
            "native_ids": sorted(native),
            "additional_native_entries": {
                i: e for i, e in native.items() if i not in shared
            },
            "scope": "All 4,565 frozen source surfaces in three filters. Every old candidate, native field/assessment and relative order is checked. Spacing hypotheses are independently replayed. Every addition carries scoped complement provenance; this does not adjudicate contextual senses or independently review Korean correctness. Corrected vowel cases retain the original proposal separately.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print("Archived", len(changes), "individual changes:", comparisons, flush=True)


def verify():
    source, report = read(SOURCE), read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ah"
    for key, path in (
        ("source_sha256", SOURCE),
        ("fixture_sha256", FIXTURE),
        ("corrections_sha256", CORRECTIONS),
        ("bridge_boundaries_sha256", BOUNDARIES),
    ):
        assert report[key] == sha(path)
    effective_cases()
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    audit = ComplementAudit()
    audit.words = report["independent_words"].copy()
    assert (
        inspect(source, report["source_diagnostic_streams"], audit)
        == report["comparisons"]
    )
    assert list(audit.changes.values()) == report["changes"]
    ids = referenced_ids(report["changes"]) | referenced_ids(
        report["independent_words"]
    )
    assert sorted(ids) == report["native_ids"]
    shared = source["complete_native_entries"]
    assert set(report["additional_native_entries"]) == ids - shared.keys()
    assert all(
        e["id"] == ident and e["senses"]
        for ident, e in report["additional_native_entries"].items()
    )
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified",
        len(report["changes"]),
        "attributed candidate/spacing changes; all original paths and native assessments retained.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary and args.output
        freeze(args.cli.resolve(), args.dictionary.resolve(), args.output)
