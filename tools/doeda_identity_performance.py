"""Verify source-anchored full-novel samples and recompute their summaries."""

import argparse
import hashlib
import math
import statistics

from lexical_nada_audit import ROOT, read, sha

COMPARISON = ROOT / "docs/doeda-identity-observations.json.gz"
PACKAGE = ROOT / "docs/doeda-identity-packaged-checks.json.gz"

REPORT = ROOT / "docs/doeda-identity-performance.json"
MODES = [
    ("novel-unannotated", 0),
    ("novel-unannotated", 8388608),
    ("novel-raw", 0),
    ("novel-raw", 8388608),
    ("novel-headword", 8388608),
    ("novel-compatible", 8388608),
    ("novel-headword-spacing", 8388608),
    ("novel-compatible-spacing", 8388608),
]


def verify_data(report):
    comparison = read(COMPARISON)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["comparison_sha256"] == sha(COMPARISON)
    assert report["package_sha256"] == sha(PACKAGE)
    for key in ("before_cli_sha256", "cli_sha256", "dictionary_sha256"):
        assert report[key] == comparison[key]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    novel = {
        c["mode"]: c
        for c in comparison["comparisons"]
        if c["source"] == report["input_source"]
        or c["source"].endswith("/" + report["input_source"])
    }
    assert len(novel) == 5
    assert report["input_source"] == "data/books/mujeong.txt"
    assert report["input_bytes"] == 786078
    assert all(c["source_sha256"] == report["input_sha256"] for c in novel.values())
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    expected_parity = {
        (mode, version)
        for mode in ("novel-raw", "novel-headword", "novel-compatible")
        for version in ("before", "after")
    }
    parity = report["cache_parity"]
    assert len(parity) == len(expected_parity)
    assert {(r["mode"], r["version"]) for r in parity} == expected_parity
    for row in parity:
        baseline = novel[row["mode"]]
        assert row["cache_bytes"] == 0
        assert row["jsonl_sha256"] == baseline[row["version"] + "_jsonl_sha256"]
        assert row["records"] == baseline["records"] == 179112
        assert isinstance(row["output_bytes"], int) and row["output_bytes"] > 0
    workloads = report["workloads"]
    assert [(w["mode"], w["cache_bytes"]) for w in workloads] == MODES
    for workload in workloads:
        mode, cache = workload["mode"], workload["cache_bytes"]
        samples = workload["samples"]
        expected_order = [
            (run + 1, version)
            for run in range(5)
            for version in (
                ("before", "after") if run % 2 == 0 else ("after", "before")
            )
        ]
        assert [(r["run"], r["version"]) for r in samples] == expected_order
        for row in samples:
            assert row["exit_code"] == 0
            assert isinstance(row["peak_rss_kib"], int) and row["peak_rss_kib"] > 0
            for key in (
                "seconds",
                "gnu_elapsed_seconds",
                "user_seconds",
                "system_seconds",
            ):
                assert math.isfinite(row[key]) and row[key] >= 0
            assert row["seconds"] > 0
            # Match the actual CLI interface: raw dictionary annotations and
            # unannotated output are separate workloads.
            command = row["command"]
            binary = (
                report["before_cli"] if row["version"] == "before" else report["cli"]
            )
            assert command[0] == binary
            assert command[1:2] == ["text"]
            assert command[2].endswith("/" + report["input_source"])
            assert command[3:5] == ["--cache-bytes", str(cache)]
            flags = command[5:]
            expected = []
            if mode != "novel-unannotated":
                assert flags[:1] == ["--dictionary"]
                assert flags[1].endswith("/data/dictionaries/krdict/krdict.db")
                expected = ["--dictionary", flags[1]]
                if mode != "novel-raw":
                    expected += [
                        "--dict-compatible" if "compatible" in mode else "--dict-only"
                    ]
            if "spacing" in mode:
                expected += ["--suggest-spacing"]
            assert flags == expected
        expected_summary = {}
        for version in ("before", "after"):
            rows = [r for r in samples if r["version"] == version]
            median = statistics.median(r["seconds"] for r in rows)
            expected_summary[version] = {
                "median_seconds": median,
                "mib_per_second": report["input_bytes"] / 1048576 / median,
                "max_peak_rss_kib": max(r["peak_rss_kib"] for r in rows),
            }
        assert workload["summary"] == expected_summary


def verify():
    report = read(REPORT)
    verify_data(report)
    print(
        "Verified 80 full-novel timing samples, eight workloads and six exact cache-parity streams."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
