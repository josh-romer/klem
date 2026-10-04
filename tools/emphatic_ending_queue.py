"""Bind emphatic-ending browser evidence to its frozen implementation."""

import argparse
import itertools

from emphatic_ending_audit import FIXTURE, ROOT
from emphatic_ending_corpora import REPORT as CORPORA
from emphatic_ending_runtime import REPORT as RUNTIME
from lexical_nada_audit import read

BROWSER = ROOT / "docs/emphatic-ending-packaged-browser.json"


def verify():
    runtime, browser, fixture = read(RUNTIME), read(BROWSER), read(FIXTURE)
    assert browser["schema_version"] == 1 and browser["checklist"] == "COV-017bw"
    # Historical reports stay attached to their exact frozen implementation,
    # rather than blocking subsequent changes to shared parser/catalog code.
    for field in (
        "cli_sha256",
        "engine_sha256",
        "catalog_sha256",
        "browser_tool_sha256",
    ):
        assert browser[field] == runtime[field]
    assert (
        browser["words"] == len(runtime["words"]) == len(fixture["before_words"]) == 155
    )
    assert browser["cases"] == len(fixture["cases"]) == 132
    assert [(r["encoding"], r["mode"]) for r in browser["checks"]] == list(
        itertools.product(("NFC", "NFD"), ("all", "headword", "compatible"))
    )
    assert all(r["records"] == 309 for r in browser["checks"])
    assert browser["rendered"] == [
        "먹게끔",
        "슬프게끔한다",
        "편리하게끔해줍니다",
        "먹으시게끔했습니다",
        "먹고싶게끔",
        "학생이고말고",
        "먹었고말고",
        "그렇고말고요",
        "아이다우시다마다",
    ]
    assert browser["endingEntryIds"] == ["88382", "66991", "75968"]
    assert browser["errors"] == []
    assert browser["allExportsMatchCli"] and browser["mobileNoHorizontalOverflow"]
    corpora = read(CORPORA)
    assert corpora["source_sha256"] == runtime["source_sha256"]
    assert corpora["engine_sha256"] == runtime["engine_sha256"]
    for report in (runtime, browser, corpora):
        assert report["contextual_verdict"] == "unjudged"
        assert report["independent_review"] == "pending"
    print(
        "Verified emphatic-ending browser evidence: six exports, nine rendered "
        "diagrams, three ending-source clicks and mobile layout; bound to frozen "
        "runtime/corpus implementation, contextual and independent review pending."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
