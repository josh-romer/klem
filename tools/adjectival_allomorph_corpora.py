"""Archive and verify all four held-out reports after canonical alias removal.

This bounded audit preserves every original gold row and recovered component
set. Candidate-count summaries may decrease; contextual correctness remains a
separate review. The complete before/after JSONL is retained for offline replay.
"""

import argparse
import hashlib
import json
from pathlib import Path

from lexical_nada_audit import ROOT, read, sha, write

PREVIOUS = ROOT / "docs/reported-retrospective-corpora.json"
REPORT = ROOT / "docs/adjectival-allomorph-corpora.json.gz"
CANDIDATE_FIELDS = {"mean_candidates", "p95_candidates", "max_candidates"}


def inspect(previous, reports):
    assert len(previous["corpora"]) == len(reports) == 4
    total = 0
    for old, row in zip(previous["corpora"], reports, strict=True):
        for key in (
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ):
            assert row[key] == old[key], (key, row["corpus"], row["partition"])
        before, after = [], []
        for name, parsed in (("before", before), ("after", after)):
            raw = row[name + "_jsonl"]
            assert (
                hashlib.sha256(raw.encode()).hexdigest() == row[name + "_report_sha256"]
            )
            parsed.extend(json.loads(line) for line in raw.splitlines())
            assert len(parsed) == row["report_lines"] == row["converted_rows"] + 1
            assert parsed[0]["input_sha256"] == row["source_sha256"]
            assert parsed[0]["corpus"] == row["corpus"]
            assert parsed[0]["converted_rows"] == row["converted_rows"]
            ids = [item["id"] for item in parsed[1:]]
            assert len(ids) == len(set(ids))
            assert parsed[0]["grouped_matches"] == sum(
                item["matched"] for item in parsed[1:]
            )
            assert parsed[0]["gold_lemmas"] == sum(
                len(item["expected"]) for item in parsed[1:]
            )
            assert parsed[0]["recovered_gold_lemmas"] == sum(
                item["recovered"] for item in parsed[1:]
            )
        assert row["before_report_sha256"] == old["after_report_sha256"]
        # Full ordered rows, including unsuccessful gold groups, must be equal.
        assert before[1:] == after[1:], (
            row["corpus"],
            row["partition"],
            "gold-row change",
        )
        differences = {
            key: {"before": before[0][key], "after": after[0][key]}
            for key in before[0]
            if before[0][key] != after[0][key]
        }
        assert before[0].keys() == after[0].keys()
        assert differences == row["changed_summary_fields"]
        assert differences.keys() <= CANDIDATE_FIELDS
        assert all(value["after"] <= value["before"] for value in differences.values())
        total += row["converted_rows"]
    assert total == 66570
    return total


def freeze(evaluator, reports_dir, output):
    previous = read(PREVIOUS)
    rows = []
    for old in previous["corpora"]:
        assert sha(ROOT / old["source"]) == old["source_sha256"]
        suffix = old["corpus"] + "-" + old["partition"] + ".jsonl"
        before = (reports_dir / ("klem-reported-" + suffix)).read_text()
        after = (reports_dir / ("klem-adjectival-allomorph-" + suffix)).read_text()
        b, a = json.loads(before.splitlines()[0]), json.loads(after.splitlines()[0])
        rows.append(
            {
                **{
                    key: old[key]
                    for key in (
                        "corpus",
                        "partition",
                        "source",
                        "source_sha256",
                        "converted_rows",
                        "report_lines",
                    )
                },
                "before_report_sha256": hashlib.sha256(before.encode()).hexdigest(),
                "after_report_sha256": hashlib.sha256(after.encode()).hexdigest(),
                "changed_summary_fields": {
                    key: {"before": b[key], "after": a[key]}
                    for key in b
                    if b[key] != a[key]
                },
                "before_jsonl": before,
                "after_jsonl": after,
            }
        )
    total = inspect(previous, rows)
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-017bu",
            "previous_report_sha256": sha(PREVIOUS),
            "evaluator_sha256": sha(evaluator),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "adapter_sha256": sha(ROOT / "tools/corpus.rs"),
            "scope": "Four complete KAIST/GSD dev/test reports; original ordered gold rows and component sets preserved, candidate-count changes recorded. This does not establish contextual correctness or packaged runtime/browser behavior.",
            "converted_rows": total,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
            "corpora": rows,
        },
    )
    print(
        f"Archived {total} identical original gold rows and all candidate-summary changes."
    )


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bu"
    assert report["previous_report_sha256"] == sha(PREVIOUS)
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert report["converted_rows"] == inspect(read(PREVIOUS), report["corpora"])
    print(
        "Verified all 66,570 original held-out gold rows/component sets; candidate-count summaries are tracked separately."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--evaluator", type=Path)
    parser.add_argument("--reports-dir", type=Path, default=Path("/tmp"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.evaluator and args.output
        freeze(args.evaluator, args.reports_dir, args.output)


if __name__ == "__main__":
    main()
