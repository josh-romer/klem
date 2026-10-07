"""Verify every held-out gold row and raw word without rewriting original evidence."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import unicodedata

from doeda_native_corpora import contexts_text, gold_changes
from lexical_nada_audit import ROOT, read, sha
from friendly_command_audit import inspect as inspect_source
from friendly_command_comparison import parent_for

SOURCE = ROOT / "docs/friendly-command-preflight.json.gz"

PRIOR = ROOT / "docs/ssik-adverb-packaged-corpora.json.gz"
TEXTS = ROOT / "docs/doeda-originless-corpora.json.gz"
REPORT = ROOT / "docs/friendly-command-corpora.json.gz"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def outcome(gold, analyses):
    """Recompute grouped matches and maximal co-recovered sets from paths."""
    sets = set()
    matched = False
    for analysis in analyses:
        lemmas = [lemma["text"] for lemma in analysis["lemmas"]]
        matched |= lemmas == gold
        indices = []
        for lemma in lemmas:
            for index, expected in enumerate(gold):
                if expected == lemma and index not in indices:
                    indices.append(index)
                    break
        if indices:
            sets.add(tuple(sorted(indices)))
    maximal = sorted(s for s in sets if not any(set(s) < set(t) for t in sets))
    return matched, max(map(len, maximal), default=0), [list(s) for s in maximal]


def inspect(report):
    prior, source, texts = read(PRIOR), read(SOURCE), read(TEXTS)
    inspect_source()
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bx"
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
        assert current["changed_gold_outcomes"] == gold_changes(previous_rows[1:], rows[1:], context)
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
        assert summary["grouped_lemma_recall"] == summary["grouped_matches"] / current["converted_rows"]
        assert summary["lemma_recall"] == summary["recovered_gold_lemmas"] / summary["gold_lemmas"]
        transformed = [r for r in rows[1:] if r["expected"] != [unicodedata.normalize("NFC", r["surface"])]]
        assert summary["transformed_rows"] == len(transformed)
        assert summary["transformed_matches"] == sum(r["matched"] for r in transformed)
        assert summary["transformed_grouped_recall"] == (summary["transformed_matches"] / len(transformed) if transformed else 0.0)
        misses = Counter((r["surface"], tuple(r["expected"])) for r in rows[1:] if not r["matched"])
        assert summary["common_misses"] == [
            {"surface": surface, "expected": list(expected), "count": count}
            for (surface, expected), count in sorted(misses.items(), key=lambda item: (-item[1], *item[0]))[:30]
        ]
        changes = {k: {"before": previous_rows[0][k], "after": summary[k]}
                   for k in summary if previous_rows[0][k] != summary[k]}
        assert set(changes) <= {"mean_candidates", "p95_candidates", "max_candidates", "grouped_matches", "recovered_gold_lemmas", "grouped_lemma_recall", "lemma_recall", "transformed_matches", "transformed_grouped_recall", "common_misses"}
        assert changes == current["changed_summary_fields"]
        for row in rows[1:]:
            ctx = context[row["id"]]
            assert ctx["original_row"][1] == row["surface"]
            assert (row["matched"], row["recovered"], row["recovered_sets"]) == outcome(
                row["expected"], after[row["surface"]]["analyses"]
            ), row["id"]
            locations.setdefault(row["surface"], []).append({
                "source": current["source"], "source_sha256": current["source_sha256"],
                "id": row["id"], **ctx,
            })
        total += len(rows) - 1
    assert total == report["converted_rows"] == 66570
    changed, additions = {}, []
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
            parent = parent_for(path, b["analyses"])
            additions.append({
                "id": "friendly-command-corpus-" + digest(json.dumps([word, path], ensure_ascii=False, sort_keys=True))[:24],
                "surface": word, "analysis": path, "parent": parent,
                "source_entry": "krdict:73877", "source_sense_ids": ["1"],
                "occurrences": locations[word], "contextual_verdict": "unjudged",
                "independent_review": "pending",
            })
    assert report["changed_words"] == changed
    assert report["candidate_changes"] == additions
    return total, len(after), len(additions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    print("Verified original gold rows, raw words and additions:", inspect(read(args.report)))
