"""Verify the packaged -감 evidence and preserve its contextual review limits."""

import argparse
import itertools

from gam_question_audit import FIXTURE, ROOT, SOURCE
from gam_question_implementation import verify as verify_implementation
from lexical_nada_audit import read, sha


def verify():
    # Reports remain tied to the exact historical code that produced them.
    # Current-code compatibility is guarded by the implemented cohort in Rust
    # and the optional full CLI replay, rather than rewriting old reports.
    verify_implementation()
    source = read(SOURCE)
    fixture = read(FIXTURE)
    observations = read(ROOT / "docs/gam-question-observations.json.gz")
    runtime = read(ROOT / "docs/gam-question-packaged-runtime.json")
    browser = read(ROOT / "docs/gam-question-packaged-browser.json")
    for report in (runtime, browser):
        assert report["schema_version"] == 1 and report["checklist"] == "COV-017bv"
        assert report["contextual_verdict"] == "unjudged"
        assert report["independent_review"] == "pending"
        assert report["words"] == len(fixture["before_words"]) == 89
    assert runtime["cli_sha256"] == browser["cli_sha256"]
    assert runtime["source_sha256"] == sha(SOURCE)
    assert runtime["fixture_sha256"] == sha(FIXTURE)
    assert runtime["observations_sha256"] == sha(
        ROOT / "docs/gam-question-observations.json.gz"
    )
    assert runtime["runtime_tool_sha256"] == sha(ROOT / "tools/gam_question_runtime.py")
    assert browser["browser_tool_sha256"] == sha(ROOT / "web/tests/gam-question.mjs")
    native = source["complete_native_entries"] | observations["complete_native_entries"]
    assert runtime["native_entries"] == len(native) == 300
    assert runtime["cases"] == [
        {
            "id": case["id"],
            "encoding": encoding,
            "verdict": case["verdict"],
            "passed": True,
        }
        for encoding in ("NFC", "NFD")
        for case in fixture["cases"]
    ]
    assert [
        (row["encoding"], row["cache_bytes"], row["mode"]) for row in runtime["checks"]
    ] == list(
        itertools.product(
            ("NFC", "NFD"), (0, 1, 4096), ("all", "headword", "compatible")
        )
    )
    assert len({row["records"] for row in runtime["checks"]}) == 1
    assert browser["cases"] == len(fixture["cases"]) == 69
    assert [(row["encoding"], row["mode"]) for row in browser["checks"]] == list(
        itertools.product(("NFC", "NFD"), ("all", "headword", "compatible"))
    )
    assert browser["rendered"] == [
        "더운감",
        "좋은감",
        "하는감",
        "멀었는감",
        "하던감",
        "학생인감",
        "먹으신감",
        "먹고있는감",
        "아이다운감",
    ]
    assert browser["endingEntryIds"] == ["73878", "73888", "73879", "73880"]
    assert browser["errors"] == []
    assert browser["allExportsMatchCli"] and browser["mobileNoHorizontalOverflow"]
    print(
        "Verified packaged -감 evidence: 300 complete native endpoints, 138 encoded judgments, 18 cache/filter streams and six browser exports; contextual/independent review pending."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
