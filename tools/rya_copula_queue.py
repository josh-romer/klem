"""Verify immutable omitted-copula Rya sources and individual engineering evidence.

This offline gate validates recorded evidence, not a live browser/corpus rerun
or a contextual/independent Korean-language review.
"""

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon, native_owners
from rya_copula_audit import ADDITIONAL, FIXTURE, SOURCE
from rya_copula_audit import OBSERVATIONS as PRIOR
from rya_copula_audit import verify as verify_source


def verify(dictionary=None):
    verify_source(dictionary)
    source, fixture = read(SOURCE), read(FIXTURE)
    native = dict(
        source["complete_native_entries"], **read(ADDITIONAL)["complete_native_entries"]
    )
    report = read(ROOT / "docs/rya-copula-observations.json.gz")
    previous = read(PRIOR)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_observations_sha256"] == sha(PRIOR)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert len(report["comparisons"]) == len(previous["comparisons"]) == 8
    streams = {}
    for row, old in zip(report["comparisons"], previous["comparisons"], strict=True):
        for key in ["mode", "source", "source_sha256", "records"]:
            assert row[key] == old[key]
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        streams[row["mode"]] = row
    assert sum(row["records"] for row in streams.values()) == 1128312
    assert len(report["diagnostics"]) == 3
    for row in report["diagnostics"]:
        assert row["records"] == len(
            source["before_streams"][row["mode"].removeprefix("diagnostic-")]
        )
        streams[row["mode"]] = row
    observed = {mode: set() for mode in streams}
    ids = set()
    for row in report["changes"]:
        category = row["category"]
        assert category in ["candidate", "spacing", "spacing-update", "work"]
        expected = (
            "rya-copula-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == expected and expected not in ids
        ids.add(expected)
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["independent_review"] == "pending"
        )
        if category == "candidate":
            assert row["before"] is None
            a = row["after"]["analysis"]
            assert all(
                r in a["rules"]
                for r in ["ending.rya", "copula.omitted_ending", "copula.omitted_rya"]
            )
            assert any(
                m["kind"] == "ending" and m["form"] == "으랴" for m in a["morphemes"]
            )
            for slot in row["after"]["reading"]["lemmas"]:
                if a["lemmas"][slot["lemma_index"]]["kind"] == "copula":
                    assert all(e["status"] != "compatible" for e in slot["entries"])
        assert row["occurrences"]
        for location in row["occurrences"]:
            assert location["mode"] in streams and location["context"]
            observed[location["mode"]].add(location["record"])
    for mode, indices in observed.items():
        assert len(indices) == streams[mode]["changed_records"], mode
    if dictionary:
        assert (
            native_owners(report["changes"], dictionary)
            == report["complete_native_entries"]
        )
    assert all(native[i] == e for i, e in report["complete_native_entries"].items())
    assert (
        set(report["complete_native_entries"])
        - source["complete_native_entries"].keys()
        == read(ADDITIONAL)["complete_native_entries"].keys()
    )
    assert report["old_raw_paths_native_fields_and_known_conflicts_preserved"]
    assert (
        report["old_spacing_options_and_order_preserved"]
        and report["all_baseline_stream_hashes_verified"]
    )
    runtime = read(ROOT / "docs/rya-copula-packaged-runtime.json")
    assert (
        runtime["source_sha256"] == sha(SOURCE)
        and runtime["cli_sha256"] == report["cli_sha256"]
    )
    assert runtime["dictionary_sha256"] == source["dictionary_sha256"]
    assert runtime["words"] == len(fixture["before_words"])
    assert runtime["native_entries"] == len(native)
    assert len(runtime["checks"]) == 18
    assert {(c["id"], c["encoding"], c["verdict"]) for c in runtime["cases"]} == {
        (c["id"], e, c["verdict"]) for c in fixture["cases"] for e in ["NFC", "NFD"]
    }
    assert all(c["passed"] for c in runtime["cases"])
    browser = read(ROOT / "docs/rya-copula-packaged-browser.json")
    assert browser["words"] == len(fixture["before_words"]) and browser["cases"] == len(
        fixture["cases"]
    )
    assert len(browser["checks"]) == 6 and browser["errors"] == []
    assert (
        browser["allExportsMatchCli"]
        and browser["omittedCopulaBreakdowns"]
        and browser["mobileNoHorizontalOverflow"]
    )
    assert browser["copulaEntryIds"] == ["86232"]
    assert browser["lexicalAlternativeSelection"]
    corpora = read(ROOT / "docs/rya-copula-corpora.json")
    old_corpora = read(ROOT / "docs/rya-boundary-corpora.json")
    assert corpora["previous_report_sha256"] == sha(
        ROOT / "docs/rya-boundary-corpora.json"
    )
    assert len(corpora["corpora"]) == len(old_corpora["corpora"]) == 4
    for current, old in zip(corpora["corpora"], old_corpora["corpora"], strict=True):
        for key in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert current[key] == old[key]
        assert (
            current["before_report_sha256"]
            == current["after_report_sha256"]
            == old["after_report_sha256"]
        )
        assert current["all_gold_rows_and_summaries_identical"]
    assert sum(c["converted_rows"] for c in corpora["corpora"]) == 66570
    print(
        f"{len(ids)} individual changes, 128 original words, eight full streams and packaged API/browser evidence verified; contextual/independent judgments pending"
    )
    print(dict(Counter(r["category"] for r in report["changes"])))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    verify(a.dictionary)
