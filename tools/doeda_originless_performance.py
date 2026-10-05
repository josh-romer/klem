"""Verify the source anchors, workload commands and all paired novel timings."""

import argparse
import hashlib
import math
import statistics

from doeda_identity_performance import MODES
from doeda_originless_observations import REPORT as COMPARISON
from doeda_originless_package import REPORT as PACKAGE
from lexical_nada_audit import ROOT, read, sha

PREVIOUS = ROOT / "docs/doeda-identity-packaged-checks.json.gz"
REPORT = ROOT / "docs/doeda-originless-performance.json"


def inspect(report):
    comparison, package, previous = read(COMPARISON), read(PACKAGE), read(PREVIOUS)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["comparison_sha256"] == sha(COMPARISON)
    assert report["package_sha256"] == sha(PACKAGE)
    assert report["previous_package_sha256"] == sha(PREVIOUS)
    assert report["before_cli_sha256"] == previous["cli_sha256"]
    assert report["cli_sha256"] == package["cli_sha256"]
    for key in ("before_cli_sha256", "cli_sha256", "dictionary_sha256"):
        assert report[key] == comparison[key]
    assert report["input_source"] == "data/books/mujeong.txt"
    assert report["input_bytes"] == 786078
    novel = [c for c in comparison["comparisons"] if c["mode"].startswith("novel-")]
    assert len(novel) == 5
    assert all(c["source_sha256"] == report["input_sha256"] for c in novel)
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    assert len(report["cpu_affinity"]) == 1
    assert set(report["cpu_affinity"]) <= set(report["allowed_cpus"])
    assert all(isinstance(cpu, int) and cpu >= 0 for cpu in report["allowed_cpus"])
    workloads = report["workloads"]
    assert [(w["mode"], w["cache_bytes"]) for w in workloads] == MODES
    binaries = {}
    for workload in workloads:
        mode, cache, samples = (
            workload["mode"],
            workload["cache_bytes"],
            workload["samples"],
        )
        assert [(r["run"], r["version"]) for r in samples] == [
            (run + 1, version)
            for run in range(5)
            for version in (
                ("before", "after") if run % 2 == 0 else ("after", "before")
            )
        ]
        for row in samples:
            assert row["exit_code"] == 0
            assert isinstance(row["peak_rss_kib"], int) and row["peak_rss_kib"] > 0
            for key in (
                "seconds",
                "user_seconds",
                "system_seconds",
                "gnu_elapsed_seconds",
            ):
                assert math.isfinite(row[key]) and row[key] >= 0
            assert row["seconds"] > 0
            for context in (row["start_context"], row["end_context"]):
                assert isinstance(context["loadavg"], str)
                frequency = context["cpu_frequency_khz"]
                assert frequency is None or isinstance(frequency, int) and frequency > 0
            command = row["command"]
            version = row["version"]
            binaries.setdefault(version, command[0])
            assert command[0] == binaries[version]
            assert command[0].startswith("/nix/store/") and command[0].endswith(
                "/bin/klem"
            )
            assert command[1] == "text" and command[2].endswith(
                "/" + report["input_source"]
            )
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
        for version in ("before", "after"):
            rows = [r for r in samples if r["version"] == version]
            assert workload["summary"][version] == {
                "median_seconds": statistics.median(r["seconds"] for r in rows),
                "median_user_seconds": statistics.median(
                    r["user_seconds"] for r in rows
                ),
                "min_seconds": min(r["seconds"] for r in rows),
                "max_seconds": max(r["seconds"] for r in rows),
            }
    assert binaries["before"] != binaries["after"]
    assert binaries == {
        "before": previous["nix_outputs"]["klem"] + "/bin/klem",
        "after": package["nix_outputs"]["klem"] + "/bin/klem",
    }
    return sum(len(w["samples"]) for w in workloads)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified paired same-CPU full-novel timing samples:", inspect(read(REPORT)))
