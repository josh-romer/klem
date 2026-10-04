"""Audit every altered candidate/entry/filter/spacing result against frozen outputs.

Observations retain original contexts and stable IDs; they do not adjudicate
meaning, register or the independent guide-versus-dictionary source tensions.
"""

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if not (ROOT / "Cargo.toml").exists():
    ROOT = Path.cwd()
NEW_RULES = {
    "continuation_left_tense",
    "go_nada_honorific",
    "go_nada_future",
    "go_nada_final_ending",
}


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Audit:
    def __init__(self, before_cli, cli, db, frozen):
        self.before_cli, self.cli, self.db = before_cli, cli, db
        self.before = {s: modes["all"] for s, modes in frozen.items()}
        self.after = {}
        self.entries, self.memberships, self.spacing = {}, {}, {}

    def raw(self, surface, after):
        cache, cli = (self.after, self.cli) if after else (self.before, self.before_cli)
        if surface not in cache:
            cache[surface] = json.loads(
                subprocess.check_output(
                    [str(cli), "word", surface, "--dictionary", str(self.db)]
                )
            )
        return cache[surface]

    def remember(self, collection, prefix, identity, row, location):
        key = canon(identity)
        if key not in collection:
            collection[key] = dict(
                id=prefix + hashlib.sha256(key.encode()).hexdigest()[:24],
                **row,
                occurrences=[],
                contextual_verdict="unjudged",
                independent_review="pending",
            )
        collection[key]["occurrences"].append(location)

    def raw_pair(self, surface, location):
        before, after = self.raw(surface, False), self.raw(surface, True)
        assert {k: v for k, v in before.items() if k != "dictionary"} == {
            k: v for k, v in after.items() if k != "dictionary"
        }, (surface, "raw candidate change")
        bd, ad = before["dictionary"], after["dictionary"]
        assert {k: v for k, v in bd.items() if k != "readings"} == {
            k: v for k, v in ad.items() if k != "readings"
        }, (surface, "native annotation change")
        assert len(bd["readings"]) == len(ad["readings"]) == len(after["analyses"])
        for raw_index, (analysis, old, new) in enumerate(
            zip(after["analyses"], bd["readings"], ad["readings"], strict=True)
        ):
            assert [s["lemma_index"] for s in old["lemmas"]] == [
                s["lemma_index"] for s in new["lemmas"]
            ]
            altered = False
            for bslot, aslot in zip(old["lemmas"], new["lemmas"], strict=True):
                assert [e["id"] for e in bslot["entries"]] == [
                    e["id"] for e in aslot["entries"]
                ]
                for b, a in zip(bslot["entries"], aslot["entries"], strict=True):
                    if b == a:
                        continue
                    slot = aslot["lemma_index"]
                    head = analysis["lemmas"][slot]
                    if b["status"] == "incompatible":
                        assert b["id"] == "krdict:62239" and head["text"] == "아프다"
                        assert b["conflicts"] == [
                            {"rule": "continuation_verb", "morpheme_index": 0}
                        ]
                        assert a["status"] == "unknown" and not a["conflicts"]
                        assert analysis["lemmas"][slot + 1] == {
                            "text": "나다",
                            "kind": "auxiliary",
                        }
                    elif a["status"] == "unknown":
                        assert (
                            b["status"] == "compatible"
                            and a["id"] == "krdict:62134"
                            and head == {"text": "나다", "kind": "auxiliary"}
                        )
                        assert not b["conflicts"] and not a["conflicts"]
                        assert any(
                            m["kind"] == "prefinal" and m["form"] == "었"
                            for m in analysis["morphemes"]
                        )
                    else:
                        assert (
                            b["status"] in {"compatible", "unknown"}
                            and a["status"] == "incompatible"
                        )
                        assert a["conflicts"][: len(b["conflicts"])] == b["conflicts"]
                        added = a["conflicts"][len(b["conflicts"]) :]
                        assert added
                        assert (
                            a["id"] in {"krdict:62134", "krdict:62601"}
                            and head["kind"] == "auxiliary"
                        )
                        for c in added:
                            assert c["rule"] in NEW_RULES
                            m = analysis["morphemes"][c["morpheme_index"]]
                            if c["rule"] == "continuation_left_tense":
                                assert (m["kind"], m["form"]) in {
                                    ("prefinal", "었"),
                                    ("prefinal", "겠"),
                                }
                            elif c["rule"] == "go_nada_honorific":
                                assert (m["kind"], m["form"]) == ("prefinal", "시")
                            elif c["rule"] == "go_nada_future":
                                assert (m["kind"], m["form"]) == ("prefinal", "겠")
                            else:
                                assert m["kind"] == "ending" and m["form"] in {
                                    "는다",
                                    "어요",
                                    "으세요",
                                    "어",
                                }
                    self.remember(
                        self.entries,
                        "continuation-inflection-entry-",
                        [surface, analysis, slot, b["id"]],
                        {
                            "surface": surface,
                            "analysis": analysis,
                            "raw_index": raw_index,
                            "lemma_index": slot,
                            "entry_id": b["id"],
                            "before": b,
                            "after": a,
                        },
                        location,
                    )
                    altered = True
            assert old == new or altered, (surface, "unexplained aggregate change")
        return before, after

    def word(self, before, after, mode, location):
        surface = before["normalized"]
        assert after["normalized"] == surface
        br, ar = self.raw_pair(surface, location)
        for word, raw in [(before, br), (after, ar)]:
            assert [a for a in raw["analyses"] if a in word["analyses"]] == word[
                "analyses"
            ], (surface, "filter order")
            assert word["dictionary"]["source"] == raw["dictionary"]["source"]
            assert word["dictionary"]["fingerprint"] == raw["dictionary"]["fingerprint"]
            assert all(
                m in raw["dictionary"]["lemmas"] for m in word["dictionary"]["lemmas"]
            )
            for a, r in zip(
                word["analyses"], word["dictionary"]["readings"], strict=True
            ):
                assert r == raw["dictionary"]["readings"][raw["analyses"].index(a)]
        if "compatible" not in mode:
            assert before["analyses"] == after["analyses"], (
                surface,
                "raw/headword candidates changed",
            )
        for index, analysis in enumerate(ar["analyses"]):
            b = analysis in before["analyses"]
            a = analysis in after["analyses"]
            if b == a:
                continue
            assert "compatible" in mode
            old, new = (
                br["dictionary"]["readings"][index],
                ar["dictionary"]["readings"][index],
            )
            assert (old["status"] == "incompatible") == a and (
                new["status"] == "incompatible"
            ) == b
            self.remember(
                self.memberships,
                "continuation-inflection-filter-",
                [surface, analysis],
                {
                    "surface": surface,
                    "analysis": analysis,
                    "raw_index": index,
                    "before_retained": b,
                    "after_retained": a,
                    "before_assessment": old,
                    "after_assessment": new,
                },
                location,
            )

    def record(self, before, after, mode, location):
        ignored = {"analysis", "dictionary", "spacing", "breakdowns"}
        assert {k: v for k, v in before.items() if k not in ignored} == {
            k: v for k, v in after.items() if k not in ignored
        }, "input/offset change"
        bw, aw = before.get("analysis"), after.get("analysis")
        assert (bw is None) == (aw is None)
        if bw is not None:
            self.word(
                dict(bw, dictionary=before["dictionary"]),
                dict(aw, dictionary=after["dictionary"]),
                mode,
                location,
            )
        bs, ns = before.get("spacing"), after.get("spacing")
        assert (bs is None) == (ns is None)
        if ns is not None:
            assert bs["rule"] == ns["rule"] and bs["limits"] == ns["limits"]
            assert ns["segment_probes"] <= ns["limits"]["segment_probes"]
            assert len(ns["alternatives"]) <= ns["limits"]["alternatives"]
            if bs != ns:
                self.remember(
                    self.spacing,
                    "continuation-inflection-spacing-",
                    [after["surface"], bs, ns],
                    {"surface": after["surface"], "before": bs, "after": ns},
                    location,
                )
            for hyp in ns["alternatives"]:
                assert "".join(r["surface"] for r in hyp["records"]) == after["surface"]
                assert hyp["spaced"] == " ".join(r["surface"] for r in hyp["records"])
                assert hyp["inserted_at"] == [
                    r["span"]["start"] for r in hyp["records"][1:]
                ]
                for r in hyp["records"]:
                    start, end = (
                        r["span"]["start"] - after["span"]["start"],
                        r["span"]["end"] - after["span"]["start"],
                    )
                    assert after["surface"].encode()[start:end].decode() == r["surface"]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before-cli", type=Path, required=True)
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    args.cli = args.cli.resolve()
    args.before_cli = args.before_cli.resolve()
    source = json.loads(
        (ROOT / "tests/fixtures/continuation-inflection-sources.json").read_text()
    )
    additional = json.loads(
        (ROOT / "tests/fixtures/continuation-inflection-additional.json").read_text()
    )
    frozen = dict(source["before_words"])
    frozen.update(additional["before_words"])
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    assert (
        sha(db) == source["dictionary_sha256"]
        and sha(args.before_cli) == source["cli_sha256"]
    )
    audit = Audit(args.before_cli, args.cli, db, frozen)
    diagnostics = []
    for surface, modes in frozen.items():
        changed = []
        for mode, flags in [
            ("all", []),
            ("headword", ["--dict-only"]),
            ("compatible", ["--dict-compatible"]),
        ]:
            after = json.loads(
                subprocess.check_output(
                    [str(args.cli), "word", surface, "--dictionary", str(db), *flags]
                )
            )
            audit.word(
                modes[mode],
                after,
                mode,
                {"cohort": "diagnostic", "surface": surface, "mode": mode},
            )
            if modes[mode] != after:
                changed.append(mode)
        diagnostics.append({"surface": surface, "changed_modes": changed})
    print("Frozen diagnostics:", len(diagnostics), "surfaces verified", flush=True)
    prior = json.loads((ROOT / "docs/bare-noun-spacing-observations.json").read_text())
    comparisons = []
    for old in prior["comparisons"]:
        mode, path = old["mode"], Path(old["source"])
        assert sha(path) == old["source_sha256"]
        content = path.read_bytes()
        flags = (
            ["--dict-compatible"]
            if "compatible" in mode
            else ["--dict-only"]
            if "headword" in mode
            else []
        )
        cmd = ["text", str(path), "--dictionary", str(db), *flags] + (
            ["--suggest-spacing"] if "spacing" in mode else []
        )
        procs = [
            subprocess.Popen([str(cli), *cmd], stdout=subprocess.PIPE)
            for cli in [args.before_cli, args.cli]
        ]
        hashes = [hashlib.sha256(), hashlib.sha256()]
        count = changed = 0
        try:
            for b, a in itertools.zip_longest(*(p.stdout for p in procs)):
                assert b is not None and a is not None
                count += 1
                hashes[0].update(b)
                hashes[1].update(a)
                if b != a:
                    bj, aj = json.loads(b), json.loads(a)
                    span = aj["span"]
                    context = content[
                        max(0, span["start"] - 120) : min(
                            len(content), span["end"] + 120
                        )
                    ].decode(errors="replace")
                    audit.record(
                        bj,
                        aj,
                        mode,
                        {
                            "cohort": mode,
                            "record": count - 1,
                            "span": span,
                            "context": context,
                        },
                    )
                    changed += 1
                if count % 25000 == 0:
                    print(mode, count, "records checked", flush=True)
            assert all(p.wait() == 0 for p in procs)
        finally:
            for process in procs:
                if process.poll() is None:
                    process.terminate()
                process.wait()
        assert (
            count == old["records"]
            and hashes[0].hexdigest() == old["after_jsonl_sha256"]
        ), (mode, "baseline hash")
        comparisons.append(
            {
                "mode": mode,
                "source": str(path),
                "source_sha256": sha(path),
                "records": count,
                "before_jsonl_sha256": hashes[0].hexdigest(),
                "after_jsonl_sha256": hashes[1].hexdigest(),
                "changed_records": changed,
            }
        )
        print(mode, count, "records;", changed, "changed", flush=True)
    result = {
        "schema_version": 1,
        "checklist": "COV-019ae",
        "before_cli": str(args.before_cli),
        "before_cli_sha256": sha(args.before_cli),
        "cli": str(args.cli),
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(db),
        "diagnostics": diagnostics,
        "comparisons": comparisons,
        "entry_changes": list(audit.entries.values()),
        "filter_changes": list(audit.memberships.values()),
        "spacing_changes": list(audit.spacing.values()),
        "raw_candidates_and_native_fields_preserved": True,
        "all_baseline_stream_hashes_verified": True,
        "contextual_verdict": "unjudged",
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        len(audit.entries),
        "individual entry changes;",
        len(audit.memberships),
        "filter changes;",
        len(audit.spacing),
        "spacing changes",
        flush=True,
    )


if __name__ == "__main__":
    main()
