"""Focused paired runs with a fixed CPU affinity; preserve the first timing archive."""

import datetime
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from copula_expectation_production import ROOT, read, sha

before = Path("/nix/store/p0xh9pk9m2nm8373vzicgdpx5w1yz6z7-klem-0.1.0/bin/klem")
after = Path(sys.argv[1]).resolve()
book = ROOT / "data/books/mujeong.txt"
db = ROOT / "data/dictionaries/krdict/krdict.db"
output = Path(sys.argv[2])
assert not output.exists()
package = ROOT / "docs/reported-dana-performance-inputs.json"
prior = ROOT / "docs/reported-deoni-packaged-checks.json"
assert sha(after) == read(package)["cli_sha256"]
assert sha(before) == read(prior)["cli_sha256"]
allowed = sorted(os.sched_getaffinity(0))
cpu = allowed[-1]


def context():
    p = Path(f"/sys/devices/system/cpu/cpu{cpu}/cpufreq/scaling_cur_freq")
    return {
        "loadavg": Path("/proc/loadavg").read_text().strip(),
        "cpu_frequency_khz": int(p.read_text()) if p.exists() else None,
    }


def pin():
    os.sched_setaffinity(0, {cpu})


workloads = []
with tempfile.TemporaryDirectory(prefix="klem-focused-timing-") as directory:
    stats = Path(directory) / "time.txt"
    for mode, cache in [
        ("novel-unannotated", 0),
        ("novel-unannotated", 8388608),
        ("novel-raw", 0),
        ("novel-raw", 8388608),
        ("novel-headword", 8388608),
        ("novel-compatible", 8388608),
        ("novel-headword-spacing", 8388608),
        ("novel-compatible-spacing", 8388608),
    ]:
        rows = []
        for run in range(5):
            versions = [("before", before), ("after", after)]
            if run % 2:
                versions.reverse()
            for version, cli in versions:
                cmd = [str(cli), "text", str(book), "--cache-bytes", str(cache)]
                if mode != "novel-unannotated":
                    cmd += ["--dictionary", str(db)]
                if mode not in ("novel-unannotated", "novel-raw"):
                    cmd += [
                        "--dict-compatible" if "compatible" in mode else "--dict-only"
                    ]
                if "spacing" in mode:
                    cmd += ["--suggest-spacing"]
                start_context = context()
                start = time.perf_counter()
                subprocess.run(
                    [
                        "/run/current-system/sw/bin/time",
                        "-f",
                        "%U %S %e %M",
                        "-o",
                        str(stats),
                        *cmd,
                    ],
                    stdout=subprocess.DEVNULL,
                    check=True,
                    preexec_fn=pin,
                )
                elapsed = time.perf_counter() - start
                user, system, gnu, rss = stats.read_text().split()
                rows.append(
                    {
                        "run": run + 1,
                        "version": version,
                        "command": cmd,
                        "seconds": elapsed,
                        "user_seconds": float(user),
                        "system_seconds": float(system),
                        "gnu_elapsed_seconds": float(gnu),
                        "peak_rss_kib": int(rss),
                        "start_context": start_context,
                        "end_context": context(),
                        "exit_code": 0,
                    }
                )
                print(mode, run + 1, version, round(elapsed, 4), flush=True)
        summary = {
            v: {
                "median_seconds": statistics.median(
                    r["seconds"] for r in rows if r["version"] == v
                ),
                "median_user_seconds": statistics.median(
                    r["user_seconds"] for r in rows if r["version"] == v
                ),
                "min_seconds": min(r["seconds"] for r in rows if r["version"] == v),
                "max_seconds": max(r["seconds"] for r in rows if r["version"] == v),
            }
            for v in ("before", "after")
        }
        workloads.append(
            {"mode": mode, "cache_bytes": cache, "samples": rows, "summary": summary}
        )
assert sha(before) == read(prior)["cli_sha256"]
assert sha(after) == read(package)["cli_sha256"]
assert sha(db) == read(package)["dictionary_sha256"]
assert sha(book) == read(package)["comparisons"][3]["source_sha256"]
script = Path(__file__)
report = {
    "schema_version": 1,
    "checklist": ["COV-017cc"],
    "measured_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "previous_package_sha256": sha(prior),
    "package_sha256": sha(package),
    "before_cli_sha256": sha(before),
    "cli_sha256": sha(after),
    "input_source": "data/books/mujeong.txt",
    "input_bytes": book.stat().st_size,
    "input_sha256": sha(book),
    "comparison_sha256": sha(ROOT / "docs/reported-dana-performance-inputs.json"),
    "dictionary_sha256": sha(db),
    "allowed_cpus": allowed,
    "cpu_affinity": [cpu],
    "system": platform.platform(),
    "workloads": workloads,
    "producer": {"text": script.read_text(), "sha256": sha(script)},
    "scope": "Five interleaved fresh-process pairs for all eight full-novel workloads, with both versions pinned to the same allowed CPU. Includes startup and serialization to /dev/null. Frequency/load samples provide context, not proof of isolation or constant clocks; no statistical-equivalence claim. All own build/audit jobs must be terminal before timing.",
}
output.write_text(json.dumps(report, indent=2) + "\n")
print("Archived focused timing", output, flush=True)
