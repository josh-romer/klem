"""Verify individual caution-ending engineering evidence without inferring gold."""

import argparse
import hashlib
from collections import Counter

from caution_ending_audit import ADDITIONAL, FIXTURE, SOURCE
from caution_ending_audit import verify as verify_source
from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon, native_owners


def verify(dictionary=None):
    verify_source(dictionary)
    source, fixture = read(SOURCE), read(FIXTURE)
    report = read(ROOT / "docs/caution-ending-observations.json.gz")
    prior_path = ROOT / "docs/rya-copula-observations.json.gz"
    prior = read(prior_path)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_observations_sha256"] == sha(prior_path)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert report["contextual_verdict"] == "unjudged"
    assert report["independent_review"] == "pending"
    assert len(report["comparisons"]) == len(prior["comparisons"]) == 8
    streams = {}
    for row, old in zip(report["comparisons"], prior["comparisons"], strict=True):
        for field in ["mode", "source", "source_sha256", "records"]:
            assert row[field] == old[field]
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        streams[row["mode"]] = row
    assert sum(r["records"] for r in streams.values()) == 1128312
    for row in report["diagnostics"]:
        mode = row["mode"].removeprefix("diagnostic-")
        assert row["records"] == len(source["before_streams"][mode])
        before = "".join(json_line(r) for r in source["before_streams"][mode])
        assert row["before_jsonl_sha256"] == hashlib.sha256(before.encode()).hexdigest()
        streams[row["mode"]] = row
    observed = {mode: set() for mode in streams}
    identities = set()
    for row in report["changes"]:
        category = row["category"]
        expected = (
            "caution-ending-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == expected and expected not in identities
        identities.add(expected)
        assert category in ["candidate", "spacing", "spacing-update", "work"]
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
        if category == "candidate":
            assert row["before"] is None
            a = row["after"]["analysis"]
            assert "ending.caution" in a["rules"]
            assert any(
                m["kind"] == "ending" and m["form"] == "을라" for m in a["morphemes"]
            )
        assert row["occurrences"]
        for location in row["occurrences"]:
            assert location["mode"] in streams and location["context"]
            observed[location["mode"]].add(location["record"])
    for mode, indices in observed.items():
        assert len(indices) == streams[mode]["changed_records"], mode
    retained = dict(
        source["complete_native_entries"], **read(ADDITIONAL)["complete_native_entries"]
    )
    assert all(retained[i] == e for i, e in report["complete_native_entries"].items())
    if dictionary:
        assert (
            native_owners(report["changes"], dictionary)
            == report["complete_native_entries"]
        )
    for field in [
        "old_raw_paths_native_fields_and_known_conflicts_preserved",
        "old_spacing_options_and_order_preserved",
        "all_baseline_stream_hashes_verified",
    ]:
        assert report[field]
    runtime = read(ROOT / "docs/caution-ending-packaged-runtime.json")
    assert runtime["source_sha256"] == sha(SOURCE)
    assert runtime["cli_sha256"] == report["cli_sha256"]
    assert runtime["dictionary_sha256"] == source["dictionary_sha256"]
    assert runtime["words"] == len(fixture["before_words"])
    assert runtime["native_entries"] == len(retained)
    assert len(runtime["checks"]) == 18
    assert {(c["id"], c["encoding"], c["verdict"]) for c in runtime["cases"]} == {
        (c["id"], e, c["verdict"]) for c in fixture["cases"] for e in ["NFC", "NFD"]
    }
    assert all(c["passed"] for c in runtime["cases"])
    browser = read(ROOT / "docs/caution-ending-packaged-browser.json")
    assert browser["words"] == len(fixture["before_words"])
    assert browser["cases"] == len(fixture["cases"])
    assert len(browser["checks"]) == 6 and browser["errors"] == []
    assert browser["endingEntryIds"] == ["77345", "77346"]
    assert browser["allExportsMatchCli"] and browser["mobileNoHorizontalOverflow"]
    assert len(browser["rendered"]) == 8
    corpora = read(ROOT / "docs/caution-ending-corpora.json")
    assert len(corpora["corpora"]) == 4
    assert corpora["previous_report_sha256"] == sha(
        ROOT / "docs/rya-copula-corpora.json"
    )
    for row, old in zip(
        corpora["corpora"],
        read(ROOT / "docs/rya-copula-corpora.json")["corpora"],
        strict=True,
    ):
        for field in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert row[field] == old[field]
        assert row["before_report_sha256"] == old["after_report_sha256"]
        assert row["all_gold_rows_identical"]
        assert set(row["changed_summary_fields"]) <= {
            "mean_candidates",
            "p95_candidates",
            "max_candidates",
        }
    print(
        "Verified caution-ending evidence:",
        dict(Counter(c["category"] for c in report["changes"])),
    )


def json_line(record):
    # CLI serialization follows struct declaration order, retained by JSON load.
    import json

    return json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--dictionary", type=__import__("pathlib").Path)
    args = parser.parse_args()
    verify(args.dictionary)
