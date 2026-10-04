"""Freeze all held-out gold outcomes and individually track candidate additions."""

import argparse
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from doeda_complement_audit import SOURCE
from doeda_complement_diagnostics import REPORT as DIAGNOSTICS
from doeda_complement_diagnostics import RULES
from lexical_nada_audit import ROOT, read, sha, write

PREVIOUS = ROOT / "docs/doeda-role-corpora.json.gz"
REPORT = ROOT / "docs/doeda-complement-corpora.json.gz"
AMBIGUITY = {"mean_candidates", "p95_candidates", "max_candidates"}
OUTCOMES = {
    "grouped_matches",
    "recovered_gold_lemmas",
    "transformed_matches",
    "grouped_lemma_recall",
    "lemma_recall",
    "transformed_grouped_recall",
    "common_misses",
}


def digest(raw):
    return hashlib.sha256(raw.encode()).hexdigest()


def contexts(path):
    """Use the adapter's stable row identities; retain complete source sentences."""
    result = {}
    for ordinal, sentence in enumerate(path.read_text().strip().split("\n\n"), 1):
        lines = sentence.splitlines()
        ids = [
            line.removeprefix("# sent_id = ")
            for line in lines
            if line.startswith("# sent_id = ")
        ]
        assert len(ids) <= 1
        prefix = "id:" + ids[0] if ids else f"ordinal:{ordinal}"
        for line in lines:
            row = line.split("\t")
            if len(row) == 10 and row[0].isdigit() and int(row[0]) > 0:
                ident = prefix + "/" + row[0]
                assert ident not in result
                result[ident] = {"complete_sentence": sentence, "original_row": row}
    return result


def gold_changes(before, after, context):
    changes = []
    assert len(before) == len(after)
    for b, a in zip(before, after, strict=True):
        assert {k: b[k] for k in ("id", "surface", "expected")} == {
            k: a[k] for k in ("id", "surface", "expected")
        }
        assert not b["matched"] or a["matched"]
        assert a["recovered"] >= b["recovered"]
        for row in (b, a):
            assert isinstance(row["matched"], bool)
            assert row["recovered"] == max(map(len, row["recovered_sets"]), default=0)
            assert all(
                s == sorted(set(s))
                and all(isinstance(i, int) and 0 <= i < len(row["expected"]) for i in s)
                for s in row["recovered_sets"]
            )
        assert all(
            any(set(old) <= set(new) for new in a["recovered_sets"])
            for old in b["recovered_sets"]
        )
        if b != a:
            changes.append({"id": b["id"], "before": b, "after": a, **context[b["id"]]})
    return changes


def candidate_changes(surface, before, after, occurrences):
    assert before.keys() == after.keys()
    assert {k: v for k, v in before.items() if k != "analyses"} == {
        k: v for k, v in after.items() if k != "analyses"
    }
    old, new = before["analyses"], after["analyses"]
    assert [a for a in new if a in old] == old, (surface, "candidate loss/order")
    changes = []
    for a in new:
        if a in old:
            continue
        assert RULES & set(a["rules"]), (surface, "unattributed addition")
        assert any(
            l == {"text": "되다", "kind": role}
            for l in a["lemmas"][1:]
            for role in ("predicate", "auxiliary")
        )
        key = json.dumps([surface, a], ensure_ascii=False, sort_keys=True)
        changes.append(
            {
                "id": "doeda-complement-corpus-" + digest(key)[:24],
                "surface": surface,
                "before": None,
                "after": a,
                "occurrences": occurrences,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return changes


def inspect(previous, report):
    assert len(previous["corpora"]) == len(report["corpora"]) == 4
    # The source preflight predates implementation and independently anchors
    # each changed sentence even inside Nix, where downloaded corpora are absent.
    frozen_corpora = {c["source"]: c for c in read(SOURCE)["corpora"]}
    total = 0
    occurrences = {}
    for old, current in zip(previous["corpora"], report["corpora"], strict=True):
        for field in (
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ):
            assert current[field] == old[field]
        path = ROOT / current["source"]
        # In the offline Nix check the original corpora are not distributed.
        # Complete changed contexts are embedded below; compare to disk when present.
        context = contexts(path) if path.exists() else None
        if context is not None:
            assert sha(path) == current["source_sha256"]
        assert current["before_jsonl"] == old["after_jsonl"]
        assert current["before_report_sha256"] == old["after_report_sha256"]
        parsed = []
        for name in ("before", "after"):
            raw = current[name + "_jsonl"]
            assert digest(raw) == current[name + "_report_sha256"]
            rows = [json.loads(line) for line in raw.splitlines()]
            assert len(rows) == current["report_lines"] == current["converted_rows"] + 1
            summary = rows[0]
            assert summary["input_sha256"] == current["source_sha256"]
            assert summary["corpus"] == current["corpus"]
            assert summary["converted_rows"] == current["converted_rows"]
            assert summary["grouped_matches"] == sum(r["matched"] for r in rows[1:])
            assert summary["gold_lemmas"] == sum(len(r["expected"]) for r in rows[1:])
            assert summary["recovered_gold_lemmas"] == sum(
                r["recovered"] for r in rows[1:]
            )
            assert summary["grouped_lemma_recall"] == summary["grouped_matches"] / len(
                rows[1:]
            )
            assert (
                summary["lemma_recall"]
                == summary["recovered_gold_lemmas"] / summary["gold_lemmas"]
            )
            assert (
                summary["transformed_grouped_recall"]
                == summary["transformed_matches"] / summary["transformed_rows"]
            )
            assert len({r["id"] for r in rows[1:]}) == len(rows) - 1
            counts = current[name + "_candidate_counts"]
            assert len(counts) == len(rows) - 1
            assert all(isinstance(n, int) and n > 0 for n in counts)
            assert sum(counts) / len(counts) == summary["mean_candidates"]
            ordered = sorted(counts)
            assert ordered[len(counts) * 95 // 100] == summary["p95_candidates"]
            assert max(counts) == summary["max_candidates"]
            parsed.append(rows)
        before, after = parsed
        assert before[0].keys() == after[0].keys()
        changes = {
            k: {"before": before[0][k], "after": after[0][k]}
            for k in before[0]
            if before[0][k] != after[0][k]
        }
        assert set(changes) <= AMBIGUITY | OUTCOMES
        assert current["changed_summary_fields"] == changes
        supplied = {
            r["id"]: {k: r[k] for k in ("complete_sentence", "original_row")}
            for r in current["changed_gold_outcomes"]
        }
        assert current["changed_gold_outcomes"] == gold_changes(
            before[1:], after[1:], context if context is not None else supplied
        )
        for b, a, bn, an in zip(
            before[1:],
            after[1:],
            current["before_candidate_counts"],
            current["after_candidate_counts"],
            strict=True,
        ):
            assert an >= bn
            if an != bn:
                pair = report["changed_words"][b["surface"]]
                assert (bn, an) == (
                    len(pair["before"]["analyses"]),
                    len(pair["after"]["analyses"]),
                )
                key = (current["source"], b["id"])
                occurrences[key] = (b["surface"], current["source_sha256"])
        total += current["converted_rows"]
    assert total == report["converted_rows"] == 66570
    seen = {}
    changes = []
    for surface, pair in report["changed_words"].items():
        assert pair["before"] != pair["after"]
        for occurrence in pair["occurrences"]:
            key = (occurrence["source"], occurrence["id"])
            assert key not in seen and occurrences[key] == (
                surface,
                occurrence["source_sha256"],
            )
            seen[key] = (surface, occurrence["source_sha256"])
            row = occurrence["original_row"]
            assert len(row) == 10 and row[1] == surface
            assert "\t".join(row) in occurrence["complete_sentence"].splitlines()
            frozen = frozen_corpora[occurrence["source"]]
            assert occurrence["source_sha256"] == frozen["sha256"]
            assert occurrence["complete_sentence"] in {
                s["complete_sentence"] for s in frozen["sentences"]
            }, "changed context absent from the original source preflight"
            path = ROOT / occurrence["source"]
            if path.exists():
                assert {
                    k: occurrence[k] for k in ("complete_sentence", "original_row")
                } == contexts(path)[occurrence["id"]]
        changes.extend(
            candidate_changes(
                surface, pair["before"], pair["after"], pair["occurrences"]
            )
        )
    assert seen == occurrences
    assert changes == report["candidate_changes"]
    return total


def freeze(evaluator, before_cli, cli, reports_dir, output):
    assert not output.exists()
    previous, source, diagnostics = read(PREVIOUS), read(SOURCE), read(DIAGNOSTICS)
    assert sha(before_cli) == source["cli_sha256"]
    assert sha(cli) == diagnostics["cli_sha256"]
    assert sha(ROOT / "src/engine.rs") == diagnostics["engine_sha256"]
    corpora, locations = [], {}
    for old in previous["corpora"]:
        path = ROOT / old["source"]
        assert sha(path) == old["source_sha256"]
        context = contexts(path)
        new = (
            reports_dir
            / f"klem-doeda-complement-{old['corpus']}-{old['partition']}.jsonl"
        ).read_text()
        before = [json.loads(line) for line in old["after_jsonl"].splitlines()]
        after = [json.loads(line) for line in new.splitlines()]
        changed = gold_changes(before[1:], after[1:], context)
        for row in before[1:]:
            original = context[row["id"]]
            assert original["original_row"][1] == row["surface"]
            locations.setdefault(row["surface"], []).append(
                {
                    "source": old["source"],
                    "source_sha256": old["source_sha256"],
                    "id": row["id"],
                    **original,
                }
            )
        corpora.append(
            {
                **{
                    k: old[k]
                    for k in (
                        "corpus",
                        "partition",
                        "source",
                        "source_sha256",
                        "converted_rows",
                        "report_lines",
                    )
                },
                "before_jsonl": old["after_jsonl"],
                "after_jsonl": new,
                "before_report_sha256": old["after_report_sha256"],
                "after_report_sha256": digest(new),
                "changed_gold_outcomes": changed,
                "changed_summary_fields": {
                    k: {"before": before[0][k], "after": after[0][k]}
                    for k in before[0]
                    if before[0][k] != after[0][k]
                },
            }
        )
    counts, changed_words = {}, {}
    hashes = [hashlib.sha256(), hashlib.sha256()]

    def compare(surface):
        raw = [
            subprocess.run(
                [str(binary), "word", surface], check=True, capture_output=True
            ).stdout
            for binary in (before_cli, cli)
        ]
        return surface, raw, [json.loads(r) for r in raw]

    with ThreadPoolExecutor(max_workers=4) as pool:
        for index, (surface, raw, records) in enumerate(
            pool.map(compare, sorted(locations)), 1
        ):
            for h, data in zip(hashes, raw, strict=True):
                h.update(data)
            b, a = records
            counts[surface] = [len(b["analyses"]), len(a["analyses"])]
            if b != a:
                candidate_changes(surface, b, a, locations[surface])
                changed_words[surface] = {
                    "before": b,
                    "after": a,
                    "occurrences": locations[surface],
                }
            if index % 4000 == 0:
                print(
                    f"Compared {index:,}/{len(locations):,} exact word surfaces",
                    flush=True,
                )
    for c in corpora:
        for index, name in enumerate(("before", "after")):
            rows = [json.loads(line) for line in c[name + "_jsonl"].splitlines()[1:]]
            c[name + "_candidate_counts"] = [counts[r["surface"]][index] for r in rows]
    changes = [
        change
        for surface, pair in changed_words.items()
        for change in candidate_changes(
            surface, pair["before"], pair["after"], pair["occurrences"]
        )
    ]
    report = {
        "schema_version": 1,
        "checklist": "COV-019ah",
        "source_sha256": sha(SOURCE),
        "diagnostics_sha256": sha(DIAGNOSTICS),
        "previous_report_sha256": sha(PREVIOUS),
        "evaluator_sha256": sha(evaluator),
        "before_cli_sha256": sha(before_cli),
        "cli_sha256": sha(cli),
        "engine_sha256": sha(ROOT / "src/engine.rs"),
        "adapter_sha256": sha(ROOT / "tools/corpus.rs"),
        "converted_rows": 66570,
        "unique_surfaces": len(locations),
        "word_stream_order": "unique surfaces sorted by Unicode code point",
        "before_word_stream_sha256": hashes[0].hexdigest(),
        "after_word_stream_sha256": hashes[1].hexdigest(),
        "corpora": corpora,
        "changed_words": changed_words,
        "candidate_changes": changes,
        "scope": "Four complete original held-out gold reports and before/after raw CLI analysis of every distinct convertible surface. Original gold and prior recovered groups are preserved; every candidate-count increase has a complete word pair, individually named alternatives and all original sentence occurrences. No dictionary filtering or contextual precision is certified.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    inspect(previous, report)
    write(output, report)
    print(
        f"Archived {report['converted_rows']:,} original gold outcomes; {len(changed_words)} changed words, {len(changes)} individually tracked candidate additions",
        flush=True,
    )


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ah"
    assert report["source_sha256"] == sha(SOURCE)
    assert report["diagnostics_sha256"] == sha(DIAGNOSTICS)
    assert report["previous_report_sha256"] == sha(PREVIOUS)
    assert report["before_cli_sha256"] == read(SOURCE)["cli_sha256"]
    assert report["cli_sha256"] == read(DIAGNOSTICS)["cli_sha256"]
    assert report["engine_sha256"] == read(DIAGNOSTICS)["engine_sha256"]
    all_surfaces = {
        json.loads(line)["surface"]
        for c in report["corpora"]
        for line in c["before_jsonl"].splitlines()[1:]
    }
    assert report["unique_surfaces"] == len(all_surfaces)
    assert report["contextual_verdict"] == "unjudged"
    assert report["independent_review"] == "pending"
    total = inspect(read(PREVIOUS), report)
    print(
        f"Verified {total:,} original held-out gold rows, per-row candidate counts, {len(report['changed_words'])} changed words and {len(report['candidate_changes'])} named additions with independently frozen original contexts."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--evaluator", type=Path)
    parser.add_argument("--before-cli", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--reports-dir", type=Path, default=Path("/tmp"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.evaluator and args.before_cli and args.cli and args.output
        freeze(
            args.evaluator.resolve(),
            args.before_cli.resolve(),
            args.cli.resolve(),
            args.reports_dir.resolve(),
            args.output,
        )
