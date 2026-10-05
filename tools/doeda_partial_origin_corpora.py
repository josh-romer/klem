"""Verify unchanged gold and all word outputs using the immutable prior maps."""

import argparse
import json

from doeda_native_corpora import digest
from doeda_native_corpora import inspect as inspect_gold
from doeda_originless_corpora import REPORT as PREVIOUS
from doeda_partial_origin_package import REPORT as PACKAGE
from doeda_partial_origins import FIXTURE
from doeda_partial_origins import REPORT as SOURCE
from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/doeda-partial-origin-corpora.json.gz"


def inspect(report):
    previous, source, fixture = read(PREVIOUS), read(SOURCE), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["previous_report_sha256"] == sha(PREVIOUS)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["before_cli_sha256"] == source["cli_sha256"] == previous["cli_sha256"]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    for key in ("engine_sha256", "adapter_sha256"):
        assert report[key] == previous[key]
    words = report["after_words"]
    assert words == previous["after_words"]
    assert len(words) == report["unique_surfaces"] == 32096
    assert report["before_word_stream_sha256"] == previous["after_word_stream_sha256"]
    assert (
        report["after_word_stream_sha256"]
        == report["before_word_stream_sha256"]
        == digest(json.dumps(words, ensure_ascii=False, sort_keys=True))
    )
    assert report["changed_words"] == report["original_parent_components"] == {}
    assert report["candidate_changes"] == []
    assert len(report["corpora"]) == len(previous["corpora"]) == 4
    corpora = []
    for old, current in zip(previous["corpora"], report["corpora"], strict=True):
        assert current["after_jsonl"] == old["after_jsonl"]
        assert current["before_report_sha256"] == old["after_report_sha256"]
        assert current["after_candidate_counts"] == old["after_candidate_counts"]
        assert (
            current["changed_summary_fields"] == {}
            and current["changed_gold_outcomes"] == []
        )
        rows = [json.loads(line) for line in current["after_jsonl"].splitlines()[1:]]
        assert current["after_candidate_counts"] == [
            len(words[r["surface"]]["analyses"]) for r in rows
        ]
        corpora.append(
            dict(
                current,
                before_jsonl=old["after_jsonl"],
                before_candidate_counts=old["after_candidate_counts"],
            )
        )
    expanded = dict(
        report, corpora=corpora, original_corpus_texts=previous["original_corpus_texts"]
    )
    total = inspect_gold(
        previous,
        expanded,
        formations={f["head"]: f for f in fixture["formations"]},
        change_namespace="doeda-partial-origin-corpus-",
    )
    return total, len(words)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified unchanged original gold rows and raw words:", inspect(read(REPORT)))
