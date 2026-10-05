"""Capture the complete supplemental API cohort with the shared runtime checks."""

import argparse
from pathlib import Path

from doeda_originless_runtime import capture
from doeda_partial_origin_diagnostics import REPORT as DIAGNOSTICS
from doeda_partial_origins import FIXTURE
from doeda_partial_origins import REPORT as PREFLIGHT

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    capture(
        parser.parse_args(),
        preflight=PREFLIGHT,
        diagnostics=DIAGNOSTICS,
        fixture_path=FIXTURE,
        expected_words=44,
    )
