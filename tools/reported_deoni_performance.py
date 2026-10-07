"""Verify all paired full-novel samples and uncached/cached packaged stream parity."""

import argparse
import hashlib

from doeda_originless_performance import inspect as inspect_timing
from copula_expectation_production import ROOT, read

REPORT = "docs/reported-deoni-performance.json"
PACKAGE = "docs/reported-deoni-packaged-checks.json"


def inspect(report):
    count = inspect_timing(
        report,
        comparison_path=ROOT / PACKAGE,
        package_path=ROOT / PACKAGE,
        previous_path=ROOT / "docs/copula-expectation-packaged-checks.json",
        checklist=["COV-017ca", "COV-017cb"],
    )
    package = read(PACKAGE)
    parity = read("docs/reported-deoni-cache-parity.json")
    assert (
        parity["package_sha256"]
        == hashlib.sha256((ROOT / PACKAGE).read_bytes()).hexdigest()
    )
    assert parity["cli_sha256"] == report["cli_sha256"]
    assert parity["book_sha256"] == report["input_sha256"]
    assert parity["dictionary_sha256"] == report["dictionary_sha256"]
    assert (
        hashlib.sha256(parity["producer"]["text"].encode()).hexdigest()
        == parity["producer"]["sha256"]
    )
    assert [s["mode"] for s in parity["streams"]] == ["raw", "headword", "compatible"]
    for stream in parity["streams"]:
        mode, checks = stream["mode"], stream["checks"]
        assert len(checks) == 2 and checks[0]["sha256"] == checks[1]["sha256"]
        comparison = next(
            c for c in package["comparisons"] if c["mode"] == "novel-" + mode
        )
        assert checks[0]["sha256"] == comparison["after_jsonl_sha256"]
        for cache, check in zip([0, 8388608], checks, strict=True):
            assert (
                check["exit_code"] == 0
                and check["records"] == comparison["records"] == 179112
            )
            command = check["command"]
            assert command[0] == package["nix_outputs"]["klem"] + "/bin/klem"
            assert command[1] == "text" and command[2].endswith(
                "/data/books/mujeong.txt"
            )
            assert command[3] == "--dictionary" and command[4].endswith(
                "/data/dictionaries/krdict/krdict.db"
            )
            flags = (
                []
                if mode == "raw"
                else ["--dict-only"]
                if mode == "headword"
                else ["--dict-compatible"]
            )
            assert command[5:] == flags + ["--cache-bytes", str(cache)]
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified paired full-novel measurements:", inspect(read(REPORT)))
