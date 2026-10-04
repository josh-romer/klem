"""Bind 되다-role browser evidence to its frozen implementation."""

import argparse
import itertools

from doeda_role_audit import FIXTURE, ROOT
from doeda_role_corpora import REPORT as CORPORA
from doeda_role_runtime import REPORT as RUNTIME
from lexical_nada_audit import read

BROWSER = ROOT / "docs/doeda-role-packaged-browser.json"


def verify():
    runtime, browser, fixture = read(RUNTIME), read(BROWSER), read(FIXTURE)
    assert browser["schema_version"] == 1 and browser["checklist"] == "COV-019ag"
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
        browser["words"]
        == len(runtime["words"])
        == len(fixture["before_case_words"])
        == 81
    )
    assert browser["cases"] == len(fixture["cases"]) == 81
    assert [(r["encoding"], r["mode"]) for r in browser["checks"]] == list(
        itertools.product(("NFC", "NFD"), ("all", "headword", "compatible"))
    )
    assert all(r["records"] == 161 for r in browser["checks"])
    words = ["먹게되었다", "좋게됩니다", "살게끔되어있다", "먹으시게끔되었습니다"]
    assert browser["rendered"] == words
    assert browser["endingEntryIds"] == ["88382", "88382"]
    assert browser["roleChecks"] == [
        {
            "word": words[0],
            "lexicalEntryId": "89858",
            "kind": "predicate",
            "passed": True,
        },
        {
            "word": words[0],
            "historicalAuxiliaryRetained": True,
            "compatibleLexicalRetained": True,
            "passed": True,
        },
        *[
            {
                "word": word,
                "lexicalEntryId": "89858",
                "kind": "predicate",
                "passed": True,
            }
            for word in words[1:]
        ],
    ]
    assert browser["errors"] == []
    assert browser["allExportsMatchCli"] and browser["mobileNoHorizontalOverflow"]
    corpora = read(CORPORA)
    assert corpora["source_sha256"] == runtime["source_sha256"]
    assert corpora["engine_sha256"] == runtime["engine_sha256"]
    for report in (runtime, browser, corpora):
        assert report["contextual_verdict"] == "unjudged"
        assert report["independent_review"] == "pending"
    print(
        "Verified 되다-role browser evidence: six exports, four rendered "
        "diagrams, lexical/auxiliary selection, source clicks and mobile layout; bound to frozen "
        "runtime/corpus implementation, contextual and independent review pending."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
