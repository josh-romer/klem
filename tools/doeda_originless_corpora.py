"""Verify original gold, every corpus word, and finite source-parent additions."""

import argparse
import json

from doeda_identity_corpora import REPORT as IDENTITY
from doeda_native_corpora import REPORT as PREVIOUS
from doeda_native_corpora import digest
from doeda_native_corpora import inspect as inspect_corpora
from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as SOURCE
from doeda_originless_package import REPORT as PACKAGE
from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/doeda-originless-corpora.json.gz"


def inspect(report):
    previous, identity, source, fixture = (
        read(PREVIOUS),
        read(IDENTITY),
        read(SOURCE),
        read(FIXTURE),
    )
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["source_sha256"] == sha(SOURCE)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["previous_report_sha256"] == sha(PREVIOUS)
    assert report["previous_identity_sha256"] == sha(IDENTITY)
    assert report["before_cli_sha256"] == identity["cli_sha256"] == source["cli_sha256"]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    for key in ("engine_sha256", "adapter_sha256"):
        assert report[key] == previous[key]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    before, after = report["before_words"], report["after_words"]
    assert set(before) == set(after)
    assert (
        len(before) == report["unique_surfaces"] == previous["unique_surfaces"] == 32096
    )
    assert (
        report["before_word_stream_sha256"]
        == digest(json.dumps(before, ensure_ascii=False, sort_keys=True))
        == previous["after_word_stream_sha256"]
        == identity["word_stream_sha256"]
    )
    assert report["after_word_stream_sha256"] == digest(
        json.dumps(after, ensure_ascii=False, sort_keys=True)
    )
    changed = {w for w in before if before[w] != after[w]}
    assert changed == set(report["changed_words"]) and len(changed) == 6
    for word, pair in report["changed_words"].items():
        assert pair["before"] == before[word] and pair["after"] == after[word]
    for c in report["corpora"]:
        for name, words in (("before", before), ("after", after)):
            rows = [json.loads(line) for line in c[name + "_jsonl"].splitlines()[1:]]
            assert c[name + "_candidate_counts"] == [
                len(words[r["surface"]]["analyses"]) for r in rows
            ]
    total = inspect_corpora(
        previous,
        report,
        formations={f["head"]: f for f in fixture["formations"]},
        change_namespace="doeda-originless-corpus-",
    )
    assert len(report["candidate_changes"]) == 8
    assert all(c["changed_gold_outcomes"] == [] for c in report["corpora"])
    assert all(
        set(c["changed_summary_fields"]) <= {"mean_candidates"}
        for c in report["corpora"]
    )
    return total, len(changed), len(report["candidate_changes"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print(
        "Verified original gold rows, changed words, additions:", inspect(read(REPORT))
    )
