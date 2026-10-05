"""Verify complete broad captures and every individually attributed addition."""

import argparse
from collections import Counter

from doeda_identity_observations import REPORT as PREVIOUS
from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as PREFLIGHT
from doeda_originless_diagnostics import OriginlessAudit, check_identity
from doeda_originless_package import REPORT as PACKAGE
from doeda_suffix_audit import SOURCE as NATIVE
from doeda_suffix_diagnostics import validate_components
from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/doeda-originless-observations.json.gz"


def word_records(value):
    if isinstance(value, dict):
        if value.get("kind") == "word":
            yield value
        for child in value.values():
            yield from word_records(child)
    elif isinstance(value, list):
        for child in value:
            yield from word_records(child)


def inspect(report):
    source, previous, fixture = read(PREFLIGHT), read(PREVIOUS), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["prior_sha256"] == sha(PREVIOUS)
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["before_cli_sha256"] == previous["cli_sha256"] == source["cli_sha256"]
    assert (
        report["dictionary_sha256"]
        == previous["dictionary_sha256"]
        == source["dictionary_sha256"]
    )
    from doeda_originless_package import digest

    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    words = report["original_words"]
    validate_components(report["original_parent_components"], list(words.values()))
    after = [p["after"] for p in report["changed_record_pairs"]]
    validate_components(report["owned_components"], after)
    audit = OriginlessAudit(source)
    audit.components = report["original_parent_components"]
    audit.original_words = words
    audit.words = {
        r["analysis"]["normalized"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in word_records(after)
    }
    counts, positions = Counter(), set()
    for pair in report["changed_record_pairs"]:
        mode, location = pair["mode"], pair["location"]
        assert mode == location["mode"]
        key = (mode, location["record"])
        assert key not in positions
        positions.add(key)
        assert pair["before"] != pair["after"]
        assert pair["before"]["span"] == pair["after"]["span"] == location["span"]
        audit.record(pair["before"], pair["after"], mode, location)
        counts[mode] += 1
    assert len(report["comparisons"]) == len(previous["comparisons"]) == 8
    for old, current in zip(
        previous["comparisons"], report["comparisons"], strict=True
    ):
        for key in old.keys() - {
            "before_jsonl_sha256",
            "after_jsonl_sha256",
            "changed_records",
        }:
            assert current[key] == old[key]
        assert current["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        assert current["changed_records"] == counts[current["mode"]]
        assert all(
            0 <= n < current["records"] for m, n in positions if m == current["mode"]
        )
        if not current["changed_records"]:
            assert current["after_jsonl_sha256"] == current["before_jsonl_sha256"]
    assert sum(c["records"] for c in report["comparisons"]) == 1128312
    assert dict(counts) == {
        "candidate-raw": 6,
        "candidate-headword": 6,
        "candidate-compatible": 6,
    }
    assert (
        report["changes"] == list(audit.changes.values())
        and len(report["changes"]) == 8
    )
    assert report["origin_lookup_upgrades"] == audit.upgrades
    identity = sum(
        check_identity([r], report["owned_components"], fixture["formations"])
        for r in word_records(after)
    )
    assert report["unknown_identity_assessments"] == identity
    native = {
        **read(NATIVE)["complete_native_entries"],
        **source["complete_native_entries"],
    }
    owners = set()

    def collect(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and value["id"].startswith("krdict:"):
                owners.add(value["id"])
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(report["changes"])
    assert set(report["complete_native_entries"]) == owners
    assert report["complete_native_entries"] == {i: native[i] for i in owners}
    return len(report["changed_record_pairs"]), len(report["changes"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print(
        "Verified complete broad record pairs and individual changes:",
        inspect(read(REPORT)),
    )
