"""Verify each immutable -랴/concessive candidate/entry observation and runtime artifact.

The offline gate checks source identity and recorded evidence consistency. Live
CLI/API/browser jobs have separate reproducible scripts; contextual judgments
and independent review remain unjudged rather than being inferred from checks.
"""

import argparse
import hashlib
from collections import Counter
from pathlib import Path

from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon, native_owners
from rya_boundary_audit import FIXTURE, SOURCE
from rya_boundary_audit import verify as verify_source
from rya_boundary_regressions import REGRESSIONS, generate

OBSERVATIONS = ROOT / "docs/rya-boundary-observations.json.gz"
RUNTIME = ROOT / "docs/rya-boundary-packaged-runtime.json"
BROWSER = ROOT / "docs/rya-boundary-packaged-browser.json"
CORPORA = ROOT / "docs/rya-boundary-corpora.json"


def verify(dictionary=None):
    verify_source()
    assert read(REGRESSIONS) == generate()
    source, fixture = read(SOURCE), read(FIXTURE)
    report = read(OBSERVATIONS)
    prior = read(ROOT / "docs/lexical-nada-observations.json.gz")
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_observations_sha256"] == sha(
        ROOT / "docs/lexical-nada-observations.json.gz"
    )
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert len(report["comparisons"]) == len(prior["comparisons"]) == 8
    streams = {}
    for actual, old in zip(report["comparisons"], prior["comparisons"], strict=True):
        for key in ["mode", "source", "source_sha256", "records"]:
            assert actual[key] == old[key]
        assert (
            actual["before_jsonl_sha256"]
            == actual["after_jsonl_sha256"]
            == old["after_jsonl_sha256"]
        )
        assert actual["changed_records"] == 0
        streams[actual["mode"]] = actual
    assert sum(s["records"] for s in streams.values()) == 1128312
    assert len(report["diagnostics"]) == 3
    for diagnostic in report["diagnostics"]:
        mode = diagnostic["mode"]
        plain = mode.removeprefix("diagnostic-")
        assert plain in {"all", "headword", "compatible"}
        assert diagnostic["records"] == len(source["before_streams"][plain]) == 176
        streams[mode] = diagnostic
    identities = set()
    observed = {mode: set() for mode in streams}
    owners = set()

    def owner_ids(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                owners.add(ident)
            for child in value.values():
                owner_ids(child)
        elif isinstance(value, list):
            for child in value:
                owner_ids(child)

    for row in report["changes"]:
        category = row["category"]
        assert category in {
            "candidate",
            "assessment",
            "spacing",
            "spacing-update",
            "work",
        }
        expected = (
            "rya-boundary-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == expected and expected not in identities
        identities.add(expected)
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["independent_review"] == "pending"
        )
        if category == "candidate":
            assert row["before"] is None
            path = row["after"]["analysis"]
            assert (
                "ending.rya" in path["rules"] and "particle.concessive" in path["rules"]
            )
            assert any(
                m["kind"] == "ending" and m["form"] == "으랴" for m in path["morphemes"]
            )
            assert any(
                m["kind"] == "particle" and m["form"] in ["마는", "만"]
                for m in path["morphemes"]
            )
        elif category == "assessment":
            before, after = row["before"], row["after"]
            assert before["analysis"] == after["analysis"]
            assert before["lemma_index"] == after["lemma_index"]
            assert before["entry"]["id"] == after["entry"]["id"]
            assert (
                before["entry"]["status"] == "compatible"
                and after["entry"]["status"] == "unknown"
            )
            assert before["entry"]["conflicts"] == after["entry"]["conflicts"]
            assert "ending.rya" in after["analysis"]["rules"]
            assert any(
                m["kind"] == "prefinal" and m["form"] not in ["시", "었", "겠"]
                for m in after["analysis"]["morphemes"]
            )
        assert row["occurrences"]
        if category != "work":
            owner_ids(row["before"])
            owner_ids(row["after"])
        for location in row["occurrences"]:
            mode = location["mode"]
            assert mode.startswith("diagnostic-")
            plain = mode.removeprefix("diagnostic-")
            original = source["before_streams"][plain][location["record"]]
            assert (
                original["surface"] == row["surface"]
                and original["span"] == location["span"]
            )
            assert location["context"] == row["surface"]
            assert location["source_discovery_ids"] == [
                h["id"] for h in source["discoveries"] if h["surface"] == row["surface"]
            ]
            observed[mode].add(location["record"])
    for mode, indices in observed.items():
        assert len(indices) == streams[mode]["changed_records"], mode
    assert report["complete_native_entries"].keys() == owners
    for ident, native in report["complete_native_entries"].items():
        assert native == source["complete_native_entries"][ident]
    if dictionary is not None:
        assert sha(dictionary) == source["dictionary_sha256"]
        assert (
            native_owners(report["changes"], dictionary)
            == report["complete_native_entries"]
        )
    assert report["old_raw_paths_native_fields_and_known_conflicts_preserved"]
    assert (
        report["old_spacing_options_and_order_preserved"]
        and report["all_baseline_stream_hashes_verified"]
    )
    runtime = read(RUNTIME)
    assert runtime["source_sha256"] == sha(SOURCE)
    assert (
        runtime["cli_sha256"] == report["cli_sha256"]
        and runtime["dictionary_sha256"] == source["dictionary_sha256"]
    )
    assert runtime["native_entries"] == len(source["complete_native_entries"]) == 110
    assert runtime["words"] == 88 and len(runtime["checks"]) == 18
    groups = {}
    for check in runtime["checks"]:
        groups.setdefault((check["encoding"], check["mode"]), []).append(check)
    assert len(groups) == 6
    for checks in groups.values():
        assert {c["cache_bytes"] for c in checks} == {0, 1, 4096}
        assert (
            len({c["sha256"] for c in checks})
            == len({c["records"] for c in checks})
            == 1
        )
    cases = {(c["id"], c["encoding"]): c for c in runtime["cases"]}
    assert len(cases) == len(runtime["cases"]) == 126
    for case in fixture["cases"]:
        for encoding in ["NFC", "NFD"]:
            actual = cases[case["id"], encoding]
            assert actual["verdict"] == case["verdict"] and actual["passed"]
    browser = read(BROWSER)
    assert browser["words"] == 88 and browser["cases"] == 63
    assert (
        browser["errors"] == []
        and len(browser["checks"]) == 6
        and browser["allExportsMatchCli"]
    )
    assert (
        browser["concessiveEntryIds"] == ["86552", "86555"]
        and browser["mobileNoHorizontalOverflow"]
    )
    corpora = read(CORPORA)
    assert corpora["previous_report_sha256"] == sha(
        ROOT / "docs/lexical-nada-corpora.json"
    )
    old_corpora = read(ROOT / "docs/lexical-nada-corpora.json")["corpora"]
    assert len(corpora["corpora"]) == len(old_corpora) == 4
    for actual, old in zip(corpora["corpora"], old_corpora, strict=True):
        for key in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert actual[key] == old[key]
        assert (
            actual["before_report_sha256"]
            == actual["after_report_sha256"]
            == old["current_report_sha256"]
        )
        assert actual["all_gold_rows_and_summaries_identical"]
    print(
        f"{len(identities)} individual changes/{sum(len(r['occurrences']) for r in report['changes'])} occurrences, {len(owners)} complete native owners, eight unchanged full streams, 110 API entries, 63 NFC/NFD cases, 18 cache/filter streams, six browser exports and four unchanged held-out corpus reports verified; contextual/independent review pending."
    )
    print(dict(Counter(r["category"] for r in report["changes"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    verify(args.dictionary)
