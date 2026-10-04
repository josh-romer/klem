"""Track every changed raw/filter/spacing result in the eight pinned streams.

Retain stable individual identities and contexts; structural checks do not
adjudicate contextual meanings or certify independent Korean review.
"""

import argparse
import gzip
import hashlib
import itertools
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path.cwd()
RULE = "spacing.bare_noun_main_nada"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def native_owners(changes, dictionary):
    """Keep full native sources for every entry involved in candidate/options changes."""
    identifiers = set()

    def visit(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                identifiers.add(ident)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for row in changes:
        if row["category"] != "work":
            visit(row["before"])
            visit(row["after"])
    with sqlite3.connect(dictionary.resolve().as_uri() + "?mode=ro", uri=True) as db:
        return {
            ident: json.loads(
                db.execute("SELECT data FROM entries WHERE id=?", (ident,)).fetchone()[
                    0
                ]
            )
            for ident in sorted(identifiers)
        }


class Audit:
    def __init__(
        self, cli, db, pairs, dependency_rule="ending.rya", dependency_form="으랴"
    ):
        self.cli, self.db, self.pairs = cli, db, pairs
        self.dependency_rule, self.dependency_form = dependency_rule, dependency_form
        self.words, self.changes = {}, {}

    def remember(self, category, surface, before, after, location):
        identity = [category, surface, before, after]
        key = canon(identity)
        if key not in self.changes:
            self.changes[key] = {
                "id": "lexical-nada-"
                + category
                + "-"
                + hashlib.sha256(key.encode()).hexdigest()[:24],
                "category": category,
                "surface": surface,
                "before": before,
                "after": after,
                "occurrences": [],
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        self.changes[key]["occurrences"].append(location)

    def independent(self, surface):
        if surface not in self.words:
            self.words[surface] = json.loads(
                subprocess.check_output(
                    [
                        str(self.cli),
                        "word",
                        surface,
                        "--dictionary",
                        str(self.db),
                    ]
                )
            )
        return self.words[surface]

    def word(self, before, after):
        assert before["normalized"] == after["normalized"]
        old, new = before["analyses"], after["analyses"]
        assert [a for a in new if a in old] == old, (
            before["normalized"],
            "candidate loss/order",
        )
        added = [a for a in new if a not in old]
        forms = (
            (self.dependency_form,)
            if isinstance(self.dependency_form, str)
            else self.dependency_form
        )
        for a in added:
            assert self.dependency_rule in a["rules"] and any(
                m["form"] in forms for m in a["morphemes"]
            ), a
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

    def verify_hyp(self, h, outer):
        records = h["records"]
        assert "".join(r["surface"] for r in records) == outer["surface"]
        assert h["spaced"] == " ".join(r["surface"] for r in records)
        assert h["inserted_at"] == [r["span"]["start"] for r in records[1:]]
        start = outer["span"]["start"]
        for r in records:
            assert r["span"]["start"] == start
            start = r["span"]["end"]
            assert (
                outer["surface"]
                .encode()[
                    r["span"]["start"] - outer["span"]["start"] : start
                    - outer["span"]["start"]
                ]
                .decode()
                == r["surface"]
            )
            raw = self.independent(r["surface"])
            assert [a for a in raw["analyses"] if a in r["analysis"]["analyses"]] == r[
                "analysis"
            ]["analyses"]
            for a, reading in zip(
                r["analysis"]["analyses"], r["dictionary"]["readings"], strict=True
            ):
                i = raw["analyses"].index(a)
                assert reading == raw["dictionary"]["readings"][i]
            for slot in r["dictionary"]["lemmas"]:
                assert slot in raw["dictionary"]["lemmas"]
            assert all(b is not None for b in r["breakdowns"])
        assert start == outer["span"]["end"]
        if h.get("rule") == RULE:
            noun, right = records[-2:]
            head = noun["analysis"]["normalized"]
            assert head in self.pairs
            for a in noun["analysis"]["analyses"]:
                assert (
                    a["unchanged"]
                    and not a["morphemes"]
                    and a["lemmas"] == [{"text": head, "kind": "unclassified"}]
                )
            for r, ident, pos, hom in [
                (noun, self.pairs[head], "명사", None),
                (right, "krdict:62210", "동사", "1"),
            ]:
                for analysis, reading in zip(
                    r["analysis"]["analyses"], r["dictionary"]["readings"], strict=True
                ):
                    first = analysis["lemmas"][0]
                    if r is right:
                        assert first == {"text": "나다", "kind": "predicate"}
                    slot = next(
                        s for s in r["dictionary"]["lemmas"] if s["lemma"] == first
                    )
                    owner = next(e for e in slot["entries"] if e["id"] == ident)
                    assert owner["pos"] == pos and owner["headword"] == first["text"]
                    if hom is not None:
                        assert owner["homonym"] == hom
                    assert any(
                        e["id"] == ident and e["status"] != "incompatible"
                        for e in reading["lemmas"][0]["entries"]
                    )

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
                        self.dependency_rule in a["rules"]
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before-cli", type=Path, required=True)
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    assert not args.output.exists()
    before, cli = args.before_cli.resolve(), args.cli.resolve()
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    with gzip.open(ROOT / "docs/lexical-nada-source-preflight.json.gz", "rt") as file:
        source = json.load(file)
    assert (
        sha(before) == source["cli_sha256"] and sha(db) == source["dictionary_sha256"]
    )
    review = json.loads((ROOT / "docs/lexical-nada-source-review.json").read_text())
    pairs = {p["noun"]: p["noun_entry"] for p in review["finite_pair_proposals"]}
    audit = Audit(cli, db, pairs)
    prior = json.loads(
        (ROOT / "docs/continuation-inflection-observations.json").read_text()
    )
    comparisons = []
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
        cmd = ["text", str(path), "--dictionary", str(db), *flags] + (
            ["--suggest-spacing"] if "spacing" in mode else []
        )
        procs = [
            subprocess.Popen([str(c), *cmd], stdout=subprocess.PIPE)
            for c in [before, cli]
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
                    context = text[
                        max(0, span["start"] - 120) : min(len(text), span["end"] + 120)
                    ].decode(errors="replace")
                    audit.record(
                        br,
                        ar,
                        mode,
                        {
                            "mode": mode,
                            "record": count,
                            "span": span,
                            "context": context,
                        },
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
        ), (mode, count, hashes[0].hexdigest())
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
    value = {
        "schema_version": 1,
        "checklist": "COV-020r / COV-017br",
        "before_cli": str(before),
        "before_cli_sha256": sha(before),
        "cli": str(cli),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(db),
        "source_sha256": sha(ROOT / "docs/lexical-nada-source-preflight.json.gz"),
        "review_sha256": sha(ROOT / "docs/lexical-nada-source-review.json"),
        "comparisons": comparisons,
        "changes": list(audit.changes.values()),
        "complete_native_entries": native_owners(audit.changes.values(), db),
        "all_baseline_stream_hashes_verified": True,
        "original_candidate_paths_assessments_and_order_preserved": True,
        "original_spacing_options_and_order_preserved": True,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    args.output.write_bytes(
        gzip.compress(
            (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(), mtime=0
        )
    )
    print("Individual changes:", len(audit.changes), flush=True)


if __name__ == "__main__":
    main()
