"""Archive original corpus gold and each recovered emphatic-ending miss."""

import argparse
import hashlib
import json
from pathlib import Path

from emphatic_ending_audit import SOURCE
from lexical_nada_audit import ROOT, read, sha, write

PREVIOUS = ROOT / "docs/gam-question-corpora.json.gz"
REPORT = ROOT / "docs/emphatic-ending-corpora.json.gz"
SUMMARY_FIELDS = {
    "mean_candidates",
    "p95_candidates",
    "max_candidates",
    "grouped_matches",
    "recovered_gold_lemmas",
    "transformed_matches",
    "grouped_lemma_recall",
    "lemma_recall",
    "transformed_grouped_recall",
}


def original_rows():
    result = {}
    for corpus in read(SOURCE)["corpora"]:
        for sentence in corpus["sentences"]:
            sent_id = next(
                l.removeprefix("# sent_id = ")
                for l in sentence["complete_sentence"].splitlines()
                if l.startswith("# sent_id = ")
            )
            for row in sentence["original_rows"]:
                result[(corpus["source"], f"id:{sent_id}/{row[0]}")] = row
    assert len(result) == 14
    return result


def inspect(previous, reports):
    assert len(previous["corpora"]) == len(reports) == 4
    originals = original_rows()
    total, changed = 0, []
    for old, row in zip(previous["corpora"], reports, strict=True):
        for key in (
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ):
            assert row[key] == old[key]
        assert row["before_jsonl"] == old["after_jsonl"]
        assert row["before_report_sha256"] == old["after_report_sha256"]
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
            ids = [r["id"] for r in parsed[1:]]
            assert len(ids) == len(set(ids))
            assert parsed[0]["grouped_matches"] == sum(r["matched"] for r in parsed[1:])
            assert parsed[0]["gold_lemmas"] == sum(
                len(r["expected"]) for r in parsed[1:]
            )
            assert parsed[0]["recovered_gold_lemmas"] == sum(
                r["recovered"] for r in parsed[1:]
            )
        rows = []
        for b, a in zip(before[1:], after[1:], strict=True):
            assert b.keys() == a.keys()
            assert all(
                b[k] == a[k]
                for k in b.keys() - {"matched", "recovered", "recovered_sets"}
            )
            assert a["recovered"] >= b["recovered"] and (
                not b["matched"] or a["matched"]
            )
            assert all(
                any(set(s) <= set(t) for t in a["recovered_sets"])
                for s in b["recovered_sets"]
            )
            if b != a:
                original = originals[(row["source"], a["id"])]
                assert original[1] == a["surface"] and "게끔" in a["surface"]
                assert not b["matched"] and a["matched"]
                assert b["recovered"] == 0 and a["recovered"] == 1
                rows.append(
                    {
                        "id": a["id"],
                        "source": row["source"],
                        "original_row": original,
                        "before": b,
                        "after": a,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        assert rows == row["changed_gold_outcomes"]
        changed.extend(rows)
        assert before[0].keys() == after[0].keys()
        differences = {
            k: {"before": before[0][k], "after": after[0][k]}
            for k in before[0]
            if before[0][k] != after[0][k]
        }
        assert differences == row["changed_summary_fields"]
        assert differences.keys() <= SUMMARY_FIELDS
        assert all(v["after"] >= v["before"] for v in differences.values())
        total += row["converted_rows"]
    assert total == 66570
    assert {r["after"]["surface"] for r in changed} == {
        "살게끔",
        "타당하게끔",
        "생각하게끔",
        "자각하게끔",
        "없게끔",
    }
    assert len(changed) == 5
    return total


def freeze(evaluator, directory, output):
    assert not output.exists()
    previous, originals = read(PREVIOUS), original_rows()
    rows = []
    for old in previous["corpora"]:
        assert sha(ROOT / old["source"]) == old["source_sha256"]
        after = (
            directory
            / ("klem-emphatic-" + old["corpus"] + "-" + old["partition"] + ".jsonl")
        ).read_text()
        before = old["after_jsonl"]
        b, a = [[json.loads(l) for l in s.splitlines()] for s in (before, after)]
        changes = []
        for prior, current in zip(b[1:], a[1:], strict=True):
            if prior != current:
                changes.append(
                    {
                        "id": current["id"],
                        "source": old["source"],
                        "original_row": originals[(old["source"], current["id"])],
                        "before": prior,
                        "after": current,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        rows.append(
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
                "before_report_sha256": hashlib.sha256(before.encode()).hexdigest(),
                "after_report_sha256": hashlib.sha256(after.encode()).hexdigest(),
                "before_jsonl": before,
                "after_jsonl": after,
                "changed_gold_outcomes": changes,
                "changed_summary_fields": {
                    k: {"before": b[0][k], "after": a[0][k]}
                    for k in b[0]
                    if b[0][k] != a[0][k]
                },
            }
        )
    total = inspect(previous, rows)
    write(
        output,
        {
            "schema_version": 1,
            "checklist": "COV-017bw",
            "source_sha256": sha(SOURCE),
            "previous_report_sha256": sha(PREVIOUS),
            "evaluator_sha256": sha(evaluator),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "adapter_sha256": sha(ROOT / "tools/corpus.rs"),
            "scope": "Four complete KAIST/GSD held-out reports retain every original ordered gold identity and prior recovered component set. Five previously missed 게끔 tokens recover. This is grouped lemma recall evidence, not contextual grammar precision or dictionary-filter certification.",
            "converted_rows": total,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
            "corpora": rows,
        },
    )


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bw"
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_report_sha256"] == sha(PREVIOUS)
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert report["converted_rows"] == inspect(read(PREVIOUS), report["corpora"])
    print(
        "Verified all 66,570 original held-out gold rows and prior component recovery; five individually tracked 게끔 misses now recover."
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
        freeze(a.evaluator, a.reports_dir, a.output)
