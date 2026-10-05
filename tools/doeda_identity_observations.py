"""Verify identity-only changes in all eight frozen candidate and novel streams."""

import argparse
from collections import Counter

from doeda_identity_audit import FIXTURE
from doeda_identity_audit import REPORT as PREFLIGHT
from doeda_identity_diagnostics import inspect_record
from doeda_identity_package import REPORT as PACKAGE
from doeda_identity_package import digest
from doeda_native_compare import REPORT as PREVIOUS
from doeda_suffix_diagnostics import validate_components
from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon

REPORT = ROOT / "docs/doeda-identity-observations.json.gz"


def inspect(report):
    previous, source, fixture = read(PREVIOUS), read(PREFLIGHT), read(FIXTURE)
    assert report["prior_sha256"] == sha(PREVIOUS)
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["before_cli_sha256"] == previous["cli_sha256"] == source["cli_sha256"]
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    heads = {h["base"]: h for h in fixture["heads"]}
    seen_owners = {}

    def record(before, after):
        inspect_record(
            {k: v for k, v in before.items() if k != "spacing"},
            {k: v for k, v in after.items() if k != "spacing"},
            heads,
            source["complete_native_entries"],
        )
        if after["kind"] == "word":
            for analysis, reading in zip(
                after["analysis"]["analyses"],
                after["dictionary"]["readings"],
                strict=True,
            ):
                for lemma in reading["lemmas"]:
                    for entry in lemma["entries"]:
                        if identity := entry.get("derivational_identity"):
                            key = canon(analysis)
                            owner = seen_owners.setdefault(
                                key, {"analysis": analysis, "owned_pairs": set()}
                            )
                            owner["owned_pairs"].add(
                                (lemma["lemma_index"], identity["morpheme_index"])
                            )
        if "spacing" in before:
            old, new = before["spacing"], after["spacing"]
            assert {k: v for k, v in old.items() if k != "alternatives"} == {
                k: v for k, v in new.items() if k != "alternatives"
            }
            for b, a in zip(old["alternatives"], new["alternatives"], strict=True):
                assert {k: v for k, v in b.items() if k != "records"} == {
                    k: v for k, v in a.items() if k != "records"
                }
                for br, ar in zip(b["records"], a["records"], strict=True):
                    record(br, ar)

    counts = Counter()
    ordinals = set()
    for pair in report["changed_record_pairs"]:
        mode, location = pair["mode"], pair["location"]
        assert location["mode"] == mode
        assert location["span"] == pair["before"]["span"] == pair["after"]["span"]
        key = (mode, location["record"])
        assert key not in ordinals
        ordinals.add(key)
        assert pair["before"] != pair["after"]
        record(pair["before"], pair["after"])
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
            0 <= n < current["records"]
            for mode, n in ordinals
            if mode == current["mode"]
        )
    assert sum(c["records"] for c in report["comparisons"]) == 1128312
    for owner in seen_owners.values():
        owner["owned_pairs"] = sorted(map(list, owner["owned_pairs"]))
    assert seen_owners == report["identity_owners"]
    analyses = [owner["analysis"] for owner in seen_owners.values()]
    validate_components(report["owned_components"], analyses)
    for key, owner in seen_owners.items():
        order = report["owned_components"][key]
        assert order is not None
        for lemma, morpheme in owner["owned_pairs"]:
            at = order.index({"lemma": lemma})
            assert order[at + 1] == {"morpheme": morpheme}
    return len(report["changed_record_pairs"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print(
        inspect(read(REPORT)), "identity metadata records; all original fields retained"
    )
