"""Verify paired full-novel measurements for the packaged remaining primary -하다 implementation."""
import argparse

from doeda_originless_performance import inspect as inspect_timing
from hada_remaining_audit import ROOT, read

REPORT = ROOT / "docs/hada-remaining-performance.json"


def inspect(report):
    count = inspect_timing(
        report,
        comparison_path=ROOT / "docs/hada-remaining-packaged-observations.json.gz",
        package_path=ROOT / "docs/hada-remaining-packaged-checks.json.gz",
        previous_path=ROOT / "docs/hada-nominal-packaged-checks.json.gz",
        checklist="COV-022t",
    )
    parity = read(ROOT / "docs/hada-remaining-cache-parity.json")
    assert parity["cli_sha256"] == report["cli_sha256"]
    assert parity["book_sha256"] == report["input_sha256"]
    assert parity["dictionary_sha256"] == report["dictionary_sha256"]
    assert [s["mode"] for s in parity["streams"]] == ["raw", "headword", "compatible"]
    comparison = read(ROOT / "docs/hada-remaining-packaged-observations.json.gz")
    package = read(ROOT / "docs/hada-remaining-packaged-checks.json.gz")
    for stream in parity["streams"]:
        mode, checks = stream["mode"], stream["checks"]
        assert len(checks) == 2
        assert checks[0]["sha256"] == checks[1]["sha256"]
        broad = next(c for c in comparison["comparisons"] if c["mode"] == "novel-" + mode)
        assert checks[0]["sha256"] == broad["after_jsonl_sha256"]
        for cache, check in zip([0, 8388608], checks, strict=True):
            assert check["exit_code"] == 0 and check["records"] == 179112
            command = check["command"]
            assert command[0] == package["nix_outputs"]["klem"] + "/bin/klem"
            assert command[1] == "text" and command[2].endswith("/data/books/mujeong.txt")
            assert command[3] == "--dictionary" and command[4].endswith("/data/dictionaries/krdict/krdict.db")
            flags = [] if mode == "raw" else ["--dict-only"] if mode == "headword" else ["--dict-compatible"]
            assert command[5:] == flags + ["--cache-bytes", str(cache)]
    return count


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    args = parser.parse_args()
    print("Verified eighty paired novel measurements:", inspect(read(REPORT)))
