"""Verify bounded reported-ending engineering evidence; contextual review stays open."""

import argparse
import hashlib
import json
from collections import Counter

from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon
from reported_retrospective_additional import verify as verify_additional
from reported_retrospective_audit import OWNERS, SOURCE
from reported_retrospective_audit import verify as verify_source


def verify():
    verify_source()
    verify_additional()
    source = read(SOURCE)
    report = read(ROOT / "docs/reported-retrospective-observations.json.gz")
    previous_path = ROOT / "docs/future-question-observations.json.gz"
    previous = read(previous_path)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_observations_sha256"] == sha(previous_path)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert len(report["comparisons"]) == len(previous["comparisons"]) == 8
    streams = {}
    for row, old in zip(report["comparisons"], previous["comparisons"], strict=True):
        assert all(
            row[k] == old[k] for k in ["mode", "source", "source_sha256", "records"]
        )
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        streams[row["mode"]] = row
    assert sum(r["records"] for r in streams.values()) == 1128312
    for row in report["diagnostics"]:
        mode = row["mode"].removeprefix("diagnostic-")
        records = source["before_streams"][mode]
        assert row["records"] == len(records)
        raw = "".join(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
            for r in records
        )
        assert row["before_jsonl_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
        streams[row["mode"]] = row
    identities = set()
    observed = {mode: set() for mode in streams}
    for row in report["changes"]:
        category = row["category"]
        expected = (
            "reported-retrospective-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == expected and expected not in identities
        identities.add(expected)
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["independent_review"] == "pending"
        )
        if category == "candidate":
            a = row["after"]["analysis"]
            assert (
                row["before"] is None and "ending.reporting_retrospective" in a["rules"]
            )
            assert any(
                m["kind"] == "ending" and m["form"] in OWNERS for m in a["morphemes"]
            )
        assert row["occurrences"]
        for location in row["occurrences"]:
            assert location["mode"] in streams and location["context"]
            observed[location["mode"]].add(location["record"])
    assert Counter(r["category"] for r in report["changes"]) == {
        "candidate": 2268,
        "spacing": 31,
    }
    assert all(
        len(observed[mode]) == row["changed_records"] for mode, row in streams.items()
    )
    assert all(
        report[k]
        for k in [
            "old_raw_paths_native_fields_and_known_conflicts_preserved",
            "old_spacing_options_and_order_preserved",
            "all_baseline_stream_hashes_verified",
        ]
    )
    retained = (
        source["complete_native_entries"]
        | read(ROOT / "tests/fixtures/reported-retrospective-corrections.json")[
            "complete_native_entries"
        ]
        | read(ROOT / "tests/fixtures/reported-retrospective-additional-native.json")[
            "complete_native_entries"
        ]
    )
    assert len(retained) == 908 and all(
        retained[i] == e for i, e in report["complete_native_entries"].items()
    )
    corpus = read(ROOT / "docs/reported-retrospective-corpora.json")
    old_path = ROOT / "docs/future-question-corpora.json"
    assert corpus["previous_report_sha256"] == sha(old_path)
    assert sum(r["converted_rows"] for r in corpus["corpora"]) == 66570
    changes = 0
    for row, old in zip(corpus["corpora"], read(old_path)["corpora"], strict=True):
        assert all(
            row[k] == old[k]
            for k in [
                "corpus",
                "partition",
                "source",
                "source_sha256",
                "converted_rows",
                "report_lines",
            ]
        )
        assert row["before_report_sha256"] == old["after_report_sha256"]
        assert (
            row["original_ids_surfaces_gold_preserved"]
            and row["prior_component_sets_preserved"]
        )
        for change in row["changes"]:
            b, a = change["before"], change["after"]
            assert all(b[k] == a[k] for k in ["id", "surface", "expected"])
            assert (
                not b["matched"] and a["matched"] and a["recovered"] >= b["recovered"]
            )
            assert all(
                any(set(g) <= set(now) for now in a["recovered_sets"])
                for g in b["recovered_sets"]
            )
            assert (
                change["contextual_verdict"] == "unjudged"
                and change["independent_review"] == "pending"
            )
            assert (
                "\t".join(change["source_row"])
                in change["complete_sentence"].splitlines()
            )
            changes += 1
    assert changes == 1
    from reported_retrospective_corrections import effective_cases

    cases = (
        effective_cases()
        + read(ROOT / "tests/fixtures/reported-retrospective-boundaries.json")["cases"]
    )
    runtime = read(ROOT / "docs/reported-retrospective-packaged-runtime.json")
    assert runtime["native_entries"] == 908
    assert (
        runtime["source_sha256"] == sha(SOURCE)
        and runtime["cli_sha256"] == report["cli_sha256"]
    )
    assert {(j["id"], j["encoding"], j["verdict"]) for j in runtime["judgments"]} == {
        (c["id"], encoding, c["verdict"]) for c in cases for encoding in ["NFC", "NFD"]
    }
    assert all(j["passed"] for j in runtime["judgments"])
    browser = read(ROOT / "docs/reported-retrospective-packaged-browser.json")
    assert (
        browser["words"] == 612
        and browser["cases"] == 187
        and len(browser["checks"]) == 18
    )
    assert (
        browser["errors"] == []
        and browser["allExportsMatchCli"]
        and browser["mobileNoHorizontalOverflow"]
    )
    assert len(browser["rendered"]) == 9 and browser["endingEntryIds"] == [
        "82037",
        "82038",
    ]
    print(
        "Verified 2,299 individual changes, 908 native sources, four held-out reports and packaged HTTP/browser checks; contextual review remains pending."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", required=True)
    p.parse_args()
    verify()
