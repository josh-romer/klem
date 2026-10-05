"""Verify all eight supplemental same-CPU novel timing workloads."""

import argparse

from doeda_originless_package import REPORT as PREVIOUS
from doeda_originless_performance import inspect as inspect_timing
from doeda_partial_origin_observations import REPORT as COMPARISON
from doeda_partial_origin_package import REPORT as PACKAGE
from lexical_nada_audit import ROOT, read

REPORT = ROOT / "docs/doeda-partial-origin-performance.json"


def inspect(report):
    return inspect_timing(
        report, comparison_path=COMPARISON, package_path=PACKAGE, previous_path=PREVIOUS
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified supplemental same-CPU timing samples:", inspect(read(REPORT)))
