"""Track every suffix candidate/filter/spacing change against frozen source gold.

Additions must reconstruct from original whole-predicate owners with exactly
attributed base roles, suffix indices, rules and spelling recovery evidence.
Original streams, complete native entries and corpus annotations are preserved.
"""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_suffix_audit import FIXTURE, SOURCE, referenced
from doeda_suffix_regressions import CORRECTIONS, effective_cases, effective_formations
from emphatic_ending_runtime import verify_stream
from lexical_nada_audit import ROOT, read, run, sha, write
from lexical_nada_compare import RULE, Audit, canon, native_owners

REPORT = ROOT / "docs/doeda-suffix-diagnostics.json.gz"
RULES = {"suffix.verb.doeda", "suffix.adjective.doeda"}


def owned_derivation(parent, added, order, formations):
    """Reconstruct from old owners; never accept a global rule flag alone."""
    if order is None or len(parent["lemmas"]) != len(added["lemmas"]):
        return None
    owners = []
    for position, component in enumerate(order):
        if "lemma" not in component:
            continue
        index = component["lemma"]
        old, new = parent["lemmas"][index], added["lemmas"][index]
        if old == new:
            continue
        if old["kind"] != "predicate" or old["text"] not in formations:
            return None
        proposal = formations[old["text"]]
        if new != {"text": proposal["base"], "kind": proposal["base_kind"]}:
            return None
        rest = order[position + 1 :]
        end = next((i for i, c in enumerate(rest) if "lemma" in c), len(rest))
        if not rest or "morpheme" not in rest[0]:
            return None
        at = rest[0]["morpheme"]
        if parent["morphemes"][at]["kind"] not in ("prefinal", "ending") or not any(
            parent["morphemes"][c["morpheme"]]["kind"] == "ending" for c in rest[:end]
        ):
            return None
        owners.append((index, at, proposal))
    if not owners:
        return None
    expected = copy.deepcopy(parent)
    for index, at, proposal in reversed(owners):
        expected["lemmas"][index] = {
            "text": proposal["base"],
            "kind": proposal["base_kind"],
        }
        expected["morphemes"].insert(at, {"form": "되다", "kind": "suffix"})
        for path in expected.get("spelling_paths", []):
            for recovery in path:
                if recovery["morpheme_index"] >= at:
                    recovery["morpheme_index"] += 1
        expected["rules"].append("suffix." + proposal["predicate_class"] + ".doeda")
    expected["rules"] = sorted(set(expected["rules"]))
    if {k: v for k, v in expected.items() if k not in {"rules", "spelling_paths"}} != {
        k: v for k, v in added.items() if k not in {"rules", "spelling_paths"}
    }:
        return None
    return expected


def attributable(parents, added, components, formations):
    assert RULES & set(added["rules"]), "unattributed addition"
    derived = [
        d
        for p in parents
        if (d := owned_derivation(p, added, components[canon(p)], formations))
        is not None
    ]
    assert derived, (added, "no original whole-head owner")
    # Engine uniqueness may union evidence from several original parents.
    assert sorted({r for d in derived for r in d["rules"]}) == added["rules"], (
        "invented/lost rules"
    )
    paths = (
        []
        if any(not d.get("spelling_paths") for d in derived)
        else [path for d in derived for path in d["spelling_paths"]]
    )
    actual = added.get("spelling_paths", [])
    assert {canon(p) for p in paths} == {canon(p) for p in actual}, (
        "invented/lost spelling evidence"
    )
    assert len(actual) == len({canon(p) for p in actual})
    assert all(
        0 <= r["morpheme_index"] < len(added["morphemes"]) for p in actual for r in p
    )


class SuffixAudit(Audit):
    def __init__(self, components, cli=None, dictionary=None, original_words=None):
        super().__init__(cli, dictionary, {}, "suffix.verb.doeda")
        self.components = components
        self.original_words = original_words or {}
        self.formations = {p["head"]: p for p in effective_formations()}

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "doeda-suffix-"
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
        parents = self.original_words.get(before["normalized"], before)["analyses"]
        for a in added:
            # A newly matched base can survive a filter that removed its
            # missing/conflicting whole head. Attribute to original RAW
            # parents, while retaining every prior filtered candidate below.
            attributable(parents, a, self.components, self.formations)
        for key in before.keys() - {"analyses", "dictionary", "breakdowns"}:
            assert before[key] == after[key], key
        for bi, parent in enumerate(old):
            ai = new.index(parent)
            assert (
                before["dictionary"]["readings"][bi]
                == after["dictionary"]["readings"][ai]
            )
            if "breakdowns" in before:
                assert before["breakdowns"][bi] == after["breakdowns"][ai]
        bd, ad = before["dictionary"], after["dictionary"]
        for key in bd.keys() - {"readings", "lemmas"}:
            assert bd[key] == ad[key]
        assert [slot for slot in ad["lemmas"] if slot in bd["lemmas"]] == bd[
            "lemmas"
        ], "native slot loss/order"
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


def analyses_in(value):
    if isinstance(value, dict):
        if "lemmas" in value and "morphemes" in value and "rules" in value:
            yield value
        else:
            for child in value.values():
                yield from analyses_in(child)
    elif isinstance(value, list):
        for child in value:
            yield from analyses_in(child)


def components_for(streams, bridge):
    unique = {canon(a): a for a in analyses_in(streams)}
    result = subprocess.run(
        [str(bridge)],
        input="".join(
            json.dumps(a, ensure_ascii=False) + "\n" for a in unique.values()
        ),
        text=True,
        capture_output=True,
        check=True,
    )
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(rows) == len(unique)
    return {key: row["components"] for key, row in zip(unique, rows, strict=True)}


def validate_components(components, streams):
    unique = {canon(a): a for a in analyses_in(streams)}
    assert set(components) == set(unique)
    for key, order in components.items():
        a = unique[key]
        # Some historical speculative paths have no displayable order. They
        # must still be retained, but cannot license a suffix expansion.
        if order is None:
            continue
        assert all(len(c) == 1 and set(c) <= {"lemma", "morpheme"} for c in order)
        for kind, field in (("lemma", "lemmas"), ("morpheme", "morphemes")):
            assert [c[kind] for c in order if kind in c] == list(range(len(a[field])))


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
                    "record_index": index,
                    "span": new["span"],
                    "context": new["surface"],
                },
            )
        comparisons.append(
            {"mode": mode, "records": len(after), "changed_records": changed}
        )
    return comparisons


def original_words(source, independent):
    words = {
        r["analysis"]["normalized"]: r["analysis"]
        for r in source["before_streams"]["all"]
        if r["kind"] == "word" and r.get("analysis") is not None
    }
    return independent | words


def freeze(cli, before_cli, dictionary, bridge, output):
    assert not output.exists()
    source = read(SOURCE)
    assert sha(dictionary) == source["dictionary_sha256"]
    assert sha(before_cli) == source["cli_sha256"]
    words = [
        r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
    ]
    text, streams = run(cli, dictionary, words)
    assert text == source["before_input"]
    # Every segment is independently analyzed by the exact old executable;
    # filtered spacing records may omit its whole-predicate parent as well.
    segments = sorted(
        {
            r["surface"]
            for stream in streams.values()
            for row in stream
            for h in row.get("spacing", {}).get("alternatives", [])
            for r in h["records"]
        }
    )
    result = subprocess.run(
        [str(before_cli), "text", "-", "--dictionary", str(dictionary)],
        input="\n".join(segments) + "\n",
        text=True,
        capture_output=True,
        check=True,
    )
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    before_words = {
        r["analysis"]["normalized"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in rows
        if r["kind"] == "word"
    }
    assert sorted(before_words) == segments
    component_inputs = [source["before_streams"], before_words]
    components = components_for(component_inputs, bridge)
    validate_components(components, component_inputs)
    audit = SuffixAudit(
        components, cli, dictionary, original_words(source, before_words)
    )
    comparisons = inspect(source, streams, audit)
    changes = list(audit.changes.values())
    native = native_owners(
        changes
        + [
            {"category": "candidate", "before": w, "after": None}
            for w in before_words.values()
        ]
        + [
            {"category": "candidate", "before": None, "after": w}
            for w in audit.words.values()
        ],
        dictionary,
    )
    shared = source["complete_native_entries"]
    assert all(shared[i] == e for i, e in native.items() if i in shared)
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-022m",
            "source_sha256": sha(SOURCE),
            "fixture_sha256": sha(FIXTURE),
            "corrections_sha256": sha(CORRECTIONS),
            "before_cli_sha256": source["cli_sha256"],
            "cli_sha256": sha(cli),
            "bridge_sha256": sha(bridge),
            "dictionary_sha256": sha(dictionary),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "attachment_sha256": sha(ROOT / "src/dictionary/attachment.rs"),
            "comparisons": comparisons,
            "source_diagnostic_streams": streams,
            "original_parent_components": components,
            "independent_before_words": before_words,
            "independent_words": audit.words,
            "changes": changes,
            "native_ids": sorted(native),
            "additional_native_entries": {
                i: e for i, e in native.items() if i not in shared
            },
            "scope": "All 6,873 frozen source words in three filters, including spacing. Every original candidate/native field/assessment and relative order retained. Each addition reconstructs from original whole-predicate owners with attributed base class and exact suffix/spelling index shifts. Original proposals/gold remain separately frozen. Contextual senses and independent/formal-history judgments are not certified.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(
        "Archived", len(changes), "individual suffix changes:", comparisons, flush=True
    )


def verify():
    source, report = read(SOURCE), read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    for key, path in (
        ("source_sha256", SOURCE),
        ("fixture_sha256", FIXTURE),
        ("corrections_sha256", CORRECTIONS),
    ):
        assert report[key] == sha(path)
    effective_cases()
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    validate_components(
        report["original_parent_components"],
        [source["before_streams"], report["independent_before_words"]],
    )
    audit = SuffixAudit(
        report["original_parent_components"],
        original_words=original_words(source, report["independent_before_words"]),
    )
    audit.words = report["independent_words"].copy()
    assert (
        inspect(source, report["source_diagnostic_streams"], audit)
        == report["comparisons"]
    )
    assert list(audit.changes.values()) == report["changes"]
    ids = (
        referenced(report["changes"])
        | referenced(report["independent_words"])
        | referenced(report["independent_before_words"])
    )
    assert sorted(ids) == report["native_ids"]
    shared = source["complete_native_entries"]
    assert set(report["additional_native_entries"]) == ids - shared.keys()
    assert all(
        e["id"] == i and e["senses"]
        for i, e in report["additional_native_entries"].items()
    )
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified",
        len(report["changes"]),
        "individually attributed suffix changes; original paths/native order retained.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--before-cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert (
            args.cli
            and args.before_cli
            and args.dictionary
            and args.bridge
            and args.output
        )
        freeze(
            args.cli.resolve(),
            args.before_cli.resolve(),
            args.dictionary.resolve(),
            args.bridge.resolve(),
            args.output,
        )
