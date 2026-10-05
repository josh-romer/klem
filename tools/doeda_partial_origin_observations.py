"""Verify all unchanged broad streams against the prior packaged snapshot."""

import argparse

from doeda_originless_observations import REPORT as PREVIOUS
from doeda_originless_observations import inspect as inspect_broad
from doeda_partial_origin_package import REPORT as PACKAGE
from doeda_partial_origins import FIXTURE
from doeda_partial_origins import REPORT as PREFLIGHT
from lexical_nada_audit import ROOT, read

REPORT = ROOT / "docs/doeda-partial-origin-observations.json.gz"


def inspect(report):
    return inspect_broad(
        report,
        preflight=PREFLIGHT,
        previous_path=PREVIOUS,
        fixture_path=FIXTURE,
        package_path=PACKAGE,
        expected_counts={},
        expected_additions=0,
        change_namespace="doeda-partial-origin-",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified complete supplemental broad streams:", inspect(read(REPORT)))
