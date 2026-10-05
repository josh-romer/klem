"""Verify actual supplemental packaged CLI/API/browser evidence."""

import argparse
from pathlib import Path

from doeda_originless_package import freeze as freeze_package
from doeda_originless_package import inspect as inspect_package
from doeda_partial_origin_diagnostics import REPORT as DIAGNOSTICS
from doeda_partial_origins import FIXTURE
from doeda_partial_origins import REPORT as PREFLIGHT
from lexical_nada_audit import ROOT, read

REPORT = ROOT / "docs/doeda-partial-origin-packaged-checks.json.gz"
SCOPE = {
    "preflight": PREFLIGHT,
    "diagnostics": DIAGNOSTICS,
    "fixture_path": FIXTURE,
    "expected_words": 44,
    "rust_expected": (904, 1, 196),
    "nix_checks": ("klem", "web-assets"),
    "selected": [("첨삭됐어요", "첨삭"), ("대칭돼요", "대칭"), ("첨삭되는", "첨삭")],
}


def inspect(report):
    return inspect_package(report, **SCOPE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--desktop-inspected", action="store_true")
    parser.add_argument("--mobile-inspected", action="store_true")
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument("--nix-log", type=Path)
    parser.add_argument("--nix-exit-code", type=int)
    parser.add_argument("--klem", type=Path)
    parser.add_argument("--assets", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(inspect(read(REPORT)))
    else:
        freeze_package(
            args,
            report_path=REPORT,
            screenshot_prefix="/tmp/klem-doeda-partial-origin",
            **SCOPE,
        )
