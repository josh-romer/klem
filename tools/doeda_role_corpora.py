"""Retain all original held-out gold and measure ambiguity after role additions."""

import argparse
import hashlib
import json
from pathlib import Path

from doeda_role_audit import SOURCE
from lexical_nada_audit import ROOT, read, sha, write

PREVIOUS = ROOT / "docs/emphatic-ending-corpora.json.gz"
REPORT = ROOT / "docs/doeda-role-corpora.json.gz"
AMBIGUITY = {"mean_candidates", "p95_candidates", "max_candidates"}


def inspect(previous, corpora):
    assert len(previous["corpora"]) == len(corpora) == 4
    total = 0
    for old, current in zip(previous["corpora"], corpora, strict=True):
        for field in (
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ):
            assert current[field] == old[field]
        assert current["before_jsonl"] == old["after_jsonl"]
        assert current["before_report_sha256"] == old["after_report_sha256"]
        parsed = []
        for name in ("before", "after"):
            raw = current[name + "_jsonl"]
            assert (
                hashlib.sha256(raw.encode()).hexdigest()
                == current[name + "_report_sha256"]
            )
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
            assert len({r["id"] for r in rows[1:]}) == len(rows) - 1
            parsed.append(rows)
        before, after = parsed
        # These additions change represented roles, not ordered lemma groups.
        # Require exact unchanged original gold and recovered groups for every
        # row, rather than accepting a monotone aggregate recall score.
        assert before[1:] == after[1:]
        assert before[0].keys() == after[0].keys()
        changed = {
            k: {"before": before[0][k], "after": after[0][k]}
            for k in before[0]
            if before[0][k] != after[0][k]
        }
        assert set(changed) <= AMBIGUITY
        assert current["changed_summary_fields"] == changed
        assert all(after[0][k] >= before[0][k] for k in AMBIGUITY)
        total += current["converted_rows"]
    assert total == 66570
    return total


def freeze(evaluator, reports_dir, output):
    assert not output.exists()
    previous = read(PREVIOUS)
    corpora = []
    for old in previous["corpora"]:
        path = ROOT / old["source"]
        assert sha(path) == old["source_sha256"]
        new = (
            reports_dir / f"klem-doeda-role-{old['corpus']}-{old['partition']}.jsonl"
        ).read_text()
        before_summary = json.loads(old["after_jsonl"].splitlines()[0])
        after_summary = json.loads(new.splitlines()[0])
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
                "after_report_sha256": hashlib.sha256(new.encode()).hexdigest(),
                "changed_summary_fields": {
                    k: {"before": before_summary[k], "after": after_summary[k]}
                    for k in before_summary
                    if before_summary[k] != after_summary[k]
                },
            }
        )
    total = inspect(previous, corpora)
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-019ag",
            "source_sha256": sha(SOURCE),
            "previous_report_sha256": sha(PREVIOUS),
            "evaluator_sha256": sha(evaluator),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "adapter_sha256": sha(ROOT / "tools/corpus.rs"),
            "scope": "Four complete original KAIST/GSD held-out reports. Every ordered gold row and recovered lemma group is unchanged; only aggregate candidate ambiguity may increase with separately represented lexical roles. This does not measure contextual precision or certify dictionary-filter correctness.",
            "converted_rows": total,
            "corpora": corpora,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(
        f"Archived {total:,} unchanged original gold outcomes; ambiguity changes: {[c['changed_summary_fields'] for c in corpora]}"
    )


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ag"
    assert report["source_sha256"] == sha(SOURCE) and report[
        "previous_report_sha256"
    ] == sha(PREVIOUS)
    assert report["converted_rows"] == inspect(read(PREVIOUS), report["corpora"])
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified all 66,570 unchanged original held-out gold rows, recovered lemma groups and recall fields; role ambiguity changes are separately retained."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--evaluator", type=Path)
    p.add_argument("--reports-dir", type=Path, default=Path("/tmp"))
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.evaluator and a.output
        freeze(a.evaluator.resolve(), a.reports_dir.resolve(), a.output)
