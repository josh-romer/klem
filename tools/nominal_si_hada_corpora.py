"""Verify every held-out gold row and raw word without rewriting original evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from doeda_native_corpora import contexts_text
from nominal_si_hada_audit import ROOT, SOURCE, parent_for, read, sha

PRIOR = ROOT / "docs/nominal-hwa-hada-packaged-corpora.json.gz"
TEXTS = ROOT / "docs/doeda-originless-corpora.json.gz"
REPORT = ROOT / "docs/nominal-si-hada-corpora.json.gz"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def inspect(report):
    prior, source, texts = read(PRIOR), read(SOURCE), read(TEXTS)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022r"
    assert report["previous_report_sha256"] == sha(PRIOR)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["before_cli_sha256"] == prior["cli_sha256"] == source["before_cli_sha256"]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    assert report["adapter_sha256"] == prior["adapter_sha256"]
    before, after = prior["after_words"], report["after_words"]
    assert len(before) == len(after) == report["unique_surfaces"] == 32096
    assert before.keys() == after.keys()
    assert report["before_word_stream_sha256"] == prior["after_word_stream_sha256"]
    assert report["before_word_stream_sha256"] == digest(json.dumps(before, ensure_ascii=False, sort_keys=True))
    assert report["after_word_stream_sha256"] == digest(json.dumps(after, ensure_ascii=False, sort_keys=True))
    locations, total = {}, 0
    assert len(report["corpora"]) == len(prior["corpora"]) == 4
    for old, current in zip(prior["corpora"], report["corpora"], strict=True):
        for field in ("corpus", "partition", "source", "source_sha256", "converted_rows", "report_lines"):
            assert current[field] == old[field]
        original = texts["original_corpus_texts"][current["source"]]
        assert digest(original) == current["source_sha256"]
        path = ROOT / current["source"]
        if path.exists():
            assert path.read_text() == original
        context = contexts_text(original)
        assert current["before_report_sha256"] == old["after_report_sha256"]
        assert digest(current["after_jsonl"]) == current["after_report_sha256"]
        previous_rows = [json.loads(line) for line in old["after_jsonl"].splitlines()]
        rows = [json.loads(line) for line in current["after_jsonl"].splitlines()]
        assert rows[1:] == previous_rows[1:], "Original gold or outcomes changed"
        assert current["changed_gold_outcomes"] == []
        assert len(rows) == current["report_lines"] == current["converted_rows"] + 1
        assert len({r["id"] for r in rows[1:]}) == len(rows) - 1
        counts = [len(after[r["surface"]]["analyses"]) for r in rows[1:]]
        assert counts == current["after_candidate_counts"]
        summary = rows[0]
        assert summary["input_sha256"] == current["source_sha256"]
        assert summary["corpus"] == current["corpus"]
        assert summary["converted_rows"] == current["converted_rows"]
        assert summary["mean_candidates"] == sum(counts) / len(counts)
        assert summary["p95_candidates"] == sorted(counts)[len(counts) * 95 // 100]
        assert summary["max_candidates"] == max(counts)
        assert summary["grouped_matches"] == sum(r["matched"] for r in rows[1:])
        assert summary["gold_lemmas"] == sum(len(r["expected"]) for r in rows[1:])
        assert summary["recovered_gold_lemmas"] == sum(r["recovered"] for r in rows[1:])
        changes = {k: {"before": previous_rows[0][k], "after": summary[k]}
                   for k in summary if previous_rows[0][k] != summary[k]}
        assert set(changes) <= {"mean_candidates", "p95_candidates", "max_candidates"}
        assert changes == current["changed_summary_fields"]
        for row in rows[1:]:
            ctx = context[row["id"]]
            assert ctx["original_row"][1] == row["surface"]
            locations.setdefault(row["surface"], []).append({
                "source": current["source"], "source_sha256": current["source_sha256"],
                "id": row["id"], **ctx,
            })
        total += len(rows) - 1
    assert total == report["converted_rows"] == 66570
    changed, additions = {}, []
    raw_before = {w: {"analysis": value} for w, value in before.items()}
    for word in sorted(before):
        b, a = before[word], after[word]
        if b == a:
            continue
        assert {k: v for k, v in b.items() if k != "analyses"} == {k: v for k, v in a.items() if k != "analyses"}
        assert [p for p in a["analyses"] if p in b["analyses"]] == b["analyses"]
        changed[word] = {"before": b, "after": a, "occurrences": locations[word]}
        for path in a["analyses"]:
            if path in b["analyses"]:
                continue
            _, _, parent = parent_for(source, word, path, raw_before)
            additions.append({
                "id": "si-hada-corpus-" + digest(json.dumps([word, path], ensure_ascii=False, sort_keys=True))[:24],
                "surface": word, "analysis": path, "parent": parent,
                "occurrences": locations[word], "contextual_verdict": "unjudged",
                "independent_review": "pending",
            })
    assert report["changed_words"] == changed
    assert set(changed) == {'적대시해', '문제시하지도', '적대시하지도'}
    assert report["candidate_changes"] == additions and len(additions) == 6
    return total, len(after), len(additions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    print("Verified original gold rows, raw words and additions:", inspect(read(args.report)))
