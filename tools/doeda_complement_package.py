"""Verify the bounded packaged checks against their historical implementation."""

import argparse
import hashlib
import re
import unicodedata

from doeda_complement_audit import SOURCE
from doeda_complement_diagnostics import REPORT as DIAGNOSTICS
from doeda_complement_regressions import BOUNDARIES, CORRECTIONS, effective_cases
from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/doeda-complement-packaged-checks.json.gz"


def verify():
    report = read(REPORT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ah"
    for key, path in (
        ("source_sha256", SOURCE),
        ("diagnostics_sha256", DIAGNOSTICS),
        ("corrections_sha256", CORRECTIONS),
        ("bridge_boundaries_sha256", BOUNDARIES),
    ):
        assert report[key] == sha(path)
    snapshots = report["implementation_files"]
    for data in list(snapshots.values()) + [report["api_check_source"]]:
        assert hashlib.sha256(data["text"].encode()).hexdigest() == data["sha256"]
    assert snapshots["src/engine.rs"]["sha256"] == read(DIAGNOSTICS)["engine_sha256"]
    assert (
        snapshots["src/dictionary/attachment.rs"]["sha256"]
        == read(DIAGNOSTICS)["attachment_sha256"]
    )
    browser, api = report["browser"], report["api"]
    assert (
        api["cli_sha256"]
        == browser["cli_sha256"]
        == report["cli_sha256"]
        == read(DIAGNOSTICS)["cli_sha256"]
    )
    assert browser["engine_sha256"] == snapshots["src/engine.rs"]["sha256"]
    assert (
        browser["catalog_sha256"] == snapshots["web/src/grammar-labels.json"]["sha256"]
    )
    assert (
        browser["browser_tool_sha256"]
        == snapshots["web/tests/doeda-complement.mjs"]["sha256"]
    )
    cases = effective_cases()
    words = sorted({c["surface"] for c in cases})
    assert (
        browser["cases"] == len(cases) == 415 and browser["words"] == len(words) == 236
    )
    seen = set()
    for check in api["checks"]:
        encoding, batch = check["encoding"], check["batch"]
        matches = [
            c
            for c in browser["checks"]
            if (c["encoding"], c["batch"]) == (encoding, batch)
        ]
        assert [c["mode"] for c in matches] == ["all", "headword", "compatible"]
        assert check["passed"] and 0 < check["bytes"] <= 7500
        assert all(c["records"] == check["records"] for c in matches)
        assert len(matches[0]["input"].encode()) == check["bytes"]
        assert all(c["input"] == matches[0]["input"] for c in matches)
        for word in matches[0]["input"].split():
            assert unicodedata.normalize(encoding, word) == word
            key = (encoding, unicodedata.normalize("NFC", word))
            assert key not in seen
            seen.add(key)
    assert seen == {(encoding, word) for encoding in ("NFC", "NFD") for word in words}
    assert (
        len(browser["checks"]) == 9
        and api["case_judgments"] == 830
        and api["native_endpoints"] == 95
    )
    diagrams = [
        "출발하기로되었다",
        "행복해야된다",
        "학생이면된다",
        "먹어도된다",
        "먹어서는안된다",
        "표시하도록되어있다",
    ]
    assert browser["rendered"] == diagrams
    assert browser["endingEntryIds"] == ["71372"]
    assert all(c["passed"] for c in browser["roleChecks"])
    assert [
        c["word"] for c in browser["roleChecks"] if c.get("lexicalEntryId")
    ] == diagrams
    assert all(
        c["lexicalEntryId"] == "89858"
        for c in browser["roleChecks"]
        if c.get("lexicalEntryId")
    )
    assert (
        browser["errors"] == []
        and browser["allExportsMatchCli"]
        and browser["mobileNoHorizontalOverflow"]
    )
    assert (
        report["desktop_breakdown_inspected"] and report["mobile_breakdown_inspected"]
    )
    results = re.findall(
        r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;",
        report["nix_test_log"],
    )
    assert tuple(sum(int(row[i]) for row in results) for i in range(3)) == (880, 0, 1)
    assert (
        len(results) == 191
        and "FAILED" not in report["nix_test_log"]
        and "error:" not in report["nix_test_log"]
    )
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified bounded packaged evidence: Nix 880 passing tests; 830 encoded API judgments, 95 native endpoints, nine browser exports and six visually inspected diagrams. Broad corpus/contextual review remains separate."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
