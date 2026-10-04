"""Compare the full pinned text streams with explicit ordered-owner removals.

Retain changed records, native assessments, contexts and individual removal IDs.
The Rust development bridge supplies component order; never infer ownership
from the last lemma. Contextual and independent Korean review remain open.
"""

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

from adjectival_allomorph_audit import OWNERS, SOURCE
from lexical_nada_audit import ROOT, digest, read, sha, write
from lexical_nada_compare import native_owners

PREVIOUS = ROOT / "docs/reported-retrospective-observations.json.gz"
REPORT = ROOT / "docs/adjectival-allomorph-observations.json.gz"
BRIDGE = ROOT / "examples/audit_adjectival_allomorph.rs"
OWNER = ROOT / "tools/adjectival_allomorph.rs"
ADDITIONAL = ROOT / "tests/fixtures/adjectival-allomorph-additional-native.json"
REGRESSIONS = ROOT / "tests/fixtures/adjectival-allomorph-stream-removals.json"


def diagnostic_baselines(source):
    text = source["before_input"].encode()
    return [
        {
            "mode": "diagnostic-" + mode,
            "source": str(SOURCE.relative_to(ROOT)) + "#before_input",
            "source_sha256": hashlib.sha256(text).hexdigest(),
            "records": len(rows),
            "after_jsonl_sha256": hashlib.sha256(
                "".join(
                    json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
                    for r in rows
                ).encode()
            ).hexdigest(),
        }
        for mode, rows in source["before_streams"].items()
    ]


def boundary(analysis, proof):
    """Check Rust's actual ordered components against the native coda rule."""
    canonical = any(
        m["kind"] == "ending" and m["form"] in OWNERS for m in analysis["morphemes"]
    )
    if not canonical:
        assert not proof["reviewed_removal"]
        return False
    components = proof["components"]
    assert components is not None
    assert sorted(c["lemma"] for c in components if "lemma" in c) == list(
        range(len(analysis["lemmas"]))
    )
    assert sorted(c["morpheme"] for c in components if "morpheme" in c) == list(
        range(len(analysis["morphemes"]))
    )
    owner = None
    invalid = False
    for component in components:
        if "lemma" in component:
            lemma = analysis["lemmas"][component["lemma"]]
            owner = (
                lemma["text"][:-1]
                if lemma["kind"] in {"predicate", "auxiliary", "copula"}
                else None
            )
            if owner is not None:
                assert lemma["text"].endswith("다") and owner
        else:
            morpheme = analysis["morphemes"][component["morpheme"]]
            if morpheme["kind"] == "suffix" and morpheme["form"] == "답다":
                owner = "답"
            if morpheme["kind"] == "ending" and morpheme["form"] in OWNERS:
                assert owner
                last = ord(owner[-1])
                invalid |= 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 in {0, 8}
    assert invalid == proof["reviewed_removal"]
    return invalid


def analyses_in(record):
    if record.get("analysis") is not None:
        yield from record["analysis"]["analyses"]
    for option in record.get("spacing", {}).get("alternatives", []):
        for segment in option["records"]:
            yield from analyses_in(segment)


class Comparison:
    def __init__(self, proofs):
        self.proofs = proofs
        self.changes = {}
        self.retained = 0

    def word(self, before, after, location):
        assert before.keys() == after.keys()
        ignored = {"analyses", "dictionary", "breakdowns"}
        assert {k: v for k, v in before.items() if k not in ignored} == {
            k: v for k, v in after.items() if k not in ignored
        }
        old, new = before["analyses"], after["analyses"]
        expected = [a for a in old if not boundary(a, self.proofs[digest(a)]["proof"])]
        assert new == expected, (
            location,
            "unexplained candidate removal/addition/order",
        )
        bd, ad = before["dictionary"], after["dictionary"]
        assert {k: v for k, v in bd.items() if k not in {"readings", "lemmas"}} == {
            k: v for k, v in ad.items() if k not in {"readings", "lemmas"}
        }
        assert len(bd["readings"]) == len(old) and len(ad["readings"]) == len(new)
        referenced = {digest(lemma) for a in new for lemma in a["lemmas"]}
        assert ad["lemmas"] == [
            slot for slot in bd["lemmas"] if digest(slot["lemma"]) in referenced
        ], (location, "native lemma-slot change")
        for i, analysis in enumerate(old):
            reading = bd["readings"][i]
            if analysis in new:
                self.retained += 1
                j = new.index(analysis)
                assert ad["readings"][j] == reading, (location, "assessment change")
                if "breakdowns" in before:
                    assert before["breakdowns"][i] == after["breakdowns"][j]
                continue
            ident = (
                "adjectival-allomorph-removal-"
                + digest([before["normalized"], analysis, reading])[:24]
            )
            if ident not in self.changes:
                self.changes[ident] = {
                    "id": ident,
                    "category": "candidate-removal",
                    "surface": before["normalized"],
                    "before": {"analysis": analysis, "reading": reading},
                    "after": None,
                    "canonical_sources": {
                        form: [f"krdict:{i}" for i in OWNERS[form]]
                        for form in sorted(
                            {
                                m["form"]
                                for m in analysis["morphemes"]
                                if m["kind"] == "ending" and m["form"] in OWNERS
                            }
                        )
                    },
                    "ordered_owner_proof": digest(analysis),
                    "occurrences": [],
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            self.changes[ident]["occurrences"].append(
                {**location, "before_analysis_index": i}
            )

    def record(self, before, after, location):
        assert before.keys() == after.keys()
        ignored = {"analysis", "dictionary", "breakdowns", "spacing"}
        assert {k: v for k, v in before.items() if k not in ignored} == {
            k: v for k, v in after.items() if k not in ignored
        }
        assert (before.get("analysis") is None) == (after.get("analysis") is None)
        if before.get("analysis") is not None:

            def word(r):
                return {
                    **r["analysis"],
                    "dictionary": r["dictionary"],
                    **({"breakdowns": r["breakdowns"]} if "breakdowns" in r else {}),
                }

            self.word(word(before), word(after), location)
        if "spacing" in before:
            bs, ns = before["spacing"], after["spacing"]
            assert {k: v for k, v in bs.items() if k != "alternatives"} == {
                k: v for k, v in ns.items() if k != "alternatives"
            }, (location, "spacing work/limit change")
            assert len(bs["alternatives"]) == len(ns["alternatives"]), (
                location,
                "spacing option loss/addition",
            )
            for i, (b, a) in enumerate(
                zip(bs["alternatives"], ns["alternatives"], strict=True)
            ):
                assert {k: v for k, v in b.items() if k != "records"} == {
                    k: v for k, v in a.items() if k != "records"
                }, (location, "spacing option/order change")
                for j, (br, ar) in enumerate(
                    zip(b["records"], a["records"], strict=True)
                ):
                    self.record(br, ar, {**location, "spacing_option": i, "segment": j})


def summarize(records, proofs):
    check = Comparison(proofs)
    for row in records:
        check.record(row["before"], row["after"], row["location"])
    changes = sorted(check.changes.values(), key=lambda r: r["id"])
    return {
        "retained_candidate_occurrences_in_changed_records": check.retained,
        "changes": changes,
    }


def freeze(before, cli, bridge, output):
    previous, source = read(PREVIOUS), read(SOURCE)
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    assert sha(before) == previous["cli_sha256"] == source["cli_sha256"]
    assert sha(db) == previous["dictionary_sha256"] == source["dictionary_sha256"]
    records, streams, diagnostics = [], [], []
    for old in diagnostic_baselines(source):
        mode = old["mode"].removeprefix("diagnostic-")
        flags = (
            ["--dict-compatible"]
            if mode == "compatible"
            else ["--dict-only"]
            if mode == "headword"
            else []
        )
        command = ["text", "-", "--dictionary", str(db), "--suggest-spacing", *flags]
        text = source["before_input"].encode()
        outputs = [
            subprocess.check_output([str(c), *command], input=text)
            for c in (before, cli)
        ]
        b, a = [[json.loads(line) for line in raw.splitlines()] for raw in outputs]
        assert b == source["before_streams"][mode]
        assert hashlib.sha256(outputs[0]).hexdigest() == old["after_jsonl_sha256"]
        changed = 0
        for index, (br, ar) in enumerate(zip(b, a, strict=True)):
            if br == ar:
                continue
            span = br["span"]
            records.append(
                {
                    "before": br,
                    "after": ar,
                    "location": {
                        "mode": old["mode"],
                        "record": index,
                        "span": span,
                        "context": text[
                            max(0, span["start"] - 120) : min(
                                len(text), span["end"] + 120
                            )
                        ].decode(errors="replace"),
                    },
                }
            )
            changed += 1
        diagnostics.append(
            {
                **{k: old[k] for k in ("mode", "source", "source_sha256", "records")},
                "before_jsonl_sha256": hashlib.sha256(outputs[0]).hexdigest(),
                "after_jsonl_sha256": hashlib.sha256(outputs[1]).hexdigest(),
                "changed_records": changed,
            }
        )
        print(
            old["mode"],
            len(b),
            "complete source records;",
            changed,
            "changed",
            flush=True,
        )
    for old in previous["comparisons"]:
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
        command = ["text", str(path), "--dictionary", str(db), *flags]
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
                    span = br["span"]
                    records.append(
                        {
                            "before": br,
                            "after": ar,
                            "location": {
                                "mode": mode,
                                "record": count,
                                "span": span,
                                "context": text[
                                    max(0, span["start"] - 120) : min(
                                        len(text), span["end"] + 120
                                    )
                                ].decode(errors="replace"),
                            },
                        }
                    )
                    changed += 1
                count += 1
                if count % 25000 == 0:
                    print(mode, count, "records checked", flush=True)
            assert all(proc.wait() == 0 for proc in procs)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait()
        assert (
            count == old["records"]
            and hashes[0].hexdigest() == old["after_jsonl_sha256"]
        )
        streams.append(
            {
                **{k: old[k] for k in ("mode", "source", "source_sha256", "records")},
                "before_jsonl_sha256": hashes[0].hexdigest(),
                "after_jsonl_sha256": hashes[1].hexdigest(),
                "changed_records": changed,
            }
        )
        print(mode, count, "complete records;", changed, "changed", flush=True)
    unique = {digest(a): a for row in records for a in analyses_in(row["before"])}
    keys = sorted(unique)
    output_proofs = subprocess.check_output(
        [str(bridge)],
        input="".join(
            json.dumps(unique[k], ensure_ascii=False) + "\n" for k in keys
        ).encode(),
    )
    proofs = {
        key: {"analysis": unique[key], "proof": json.loads(raw)}
        for key, raw in zip(keys, output_proofs.splitlines(), strict=True)
    }
    for row in proofs.values():
        boundary(row["analysis"], row["proof"])
    summary = summarize(records, proofs)
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-017bu",
            "previous_report_sha256": sha(PREVIOUS),
            "source_sha256": sha(SOURCE),
            "before_cli_sha256": sha(before),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(db),
            "bridge_sha256": sha(bridge),
            "bridge_source_sha256": sha(BRIDGE),
            "ordered_owner_source_sha256": sha(OWNER),
            "scope": "Eight complete pinned candidate/novel streams, including both filtered spacing modes, plus all three frozen 1,399-word diagnostic streams. Changed records retain complete before/after fields, native assessments and contexts; identical records are covered by full stream hashes. Contextual interpretations and independent Korean review remain open.",
            "comparisons": streams,
            "diagnostics": diagnostics,
            "changed_records": records,
            "ordered_owner_proofs": proofs,
            "complete_native_entries": native_owners(summary["changes"], db),
            **summary,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(
        "Tracked",
        len(summary["changes"]),
        "individual removals across",
        sum(r["records"] for r in streams),
        "records.",
        flush=True,
    )


def verify():
    report, previous = read(REPORT), read(PREVIOUS)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bu"
    assert report["previous_report_sha256"] == sha(PREVIOUS) and report[
        "source_sha256"
    ] == sha(SOURCE)
    assert (
        report["before_cli_sha256"] == previous["cli_sha256"]
        and report["dictionary_sha256"] == previous["dictionary_sha256"]
    )
    assert report["bridge_source_sha256"] == sha(BRIDGE) and report[
        "ordered_owner_source_sha256"
    ] == sha(OWNER)
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    source = read(SOURCE)
    baselines = previous["comparisons"] + diagnostic_baselines(source)
    for row, old in zip(
        report["comparisons"] + report["diagnostics"], baselines, strict=True
    ):
        assert all(
            row[k] == old[k] for k in ("mode", "source", "source_sha256", "records")
        )
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        selected = [
            r for r in report["changed_records"] if r["location"]["mode"] == row["mode"]
        ]
        assert len(selected) == row["changed_records"]
        assert len({r["location"]["record"] for r in selected}) == len(selected)
        assert all(0 <= r["location"]["record"] < row["records"] for r in selected)
        assert all(
            r["before"] != r["after"]
            and r["location"]["span"] == r["before"]["span"]
            and r["location"]["context"]
            for r in selected
        )
        if row["mode"].startswith("diagnostic-"):
            mode = row["mode"].removeprefix("diagnostic-")
            original = source["before_streams"][mode]
            assert all(
                r["before"] == original[r["location"]["record"]] for r in selected
            )
    assert (
        len(report["comparisons"]) == 8
        and sum(r["records"] for r in report["comparisons"]) == 1128312
    )
    for key, row in report["ordered_owner_proofs"].items():
        assert key == digest(row["analysis"])
        boundary(row["analysis"], row["proof"])
    summary = summarize(report["changed_records"], report["ordered_owner_proofs"])
    assert all(report[k] == v for k, v in summary.items())
    assert all(
        ident == entry["id"]
        for ident, entry in report["complete_native_entries"].items()
    )
    additional = read(ADDITIONAL)
    assert additional["schema_version"] == 1
    assert additional["source_sha256"] == sha(SOURCE)
    assert additional["dictionary_sha256"] == report["dictionary_sha256"]
    assert not (
        additional["complete_native_entries"].keys()
        & source["complete_native_entries"].keys()
    )
    retained = source["complete_native_entries"] | additional["complete_native_entries"]
    assert all(
        retained[ident] == entry
        for ident, entry in report["complete_native_entries"].items()
    )
    regressions = read(REGRESSIONS)
    assert regressions["schema_version"] == 1
    assert regressions["source_sha256"] == report["source_sha256"]
    assert regressions["before_cli_sha256"] == report["before_cli_sha256"]
    assert regressions["cases"] == [
        {"id": c["id"], "surface": c["surface"], "analysis": c["before"]["analysis"]}
        for c in summary["changes"]
    ]
    print(
        f"Verified {len(summary['changes'])} individual source-scoped removals across 1,128,312 full records; all other candidate/assessment/spacing fields preserved."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--before-cli", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.before_cli and args.cli and args.bridge and args.output
        freeze(
            args.before_cli.resolve(),
            args.cli.resolve(),
            args.bridge.resolve(),
            args.output,
        )


if __name__ == "__main__":
    main()
