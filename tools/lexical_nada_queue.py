"""Verify immutable per-case candidate/spacing observations and runtime evidence.

Offline checks validate source identities and artifact consistency. They do not
rerun CLI/browser jobs or turn contextual observations into linguistic gold.
"""

import argparse
import hashlib
from collections import Counter

from lexical_nada_audit import ROOT, SOURCE, read, sha
from lexical_nada_compare import canon, native_owners
from lexical_nada_review import REVIEW

OBSERVATIONS = ROOT / "docs/lexical-nada-observations.json.gz"
RUNTIME = ROOT / "docs/lexical-nada-packaged-runtime.json"
BROWSER = ROOT / "docs/lexical-nada-packaged-browser.json"
CORPORA = ROOT / "docs/lexical-nada-corpora.json"


def verify(dictionary=None):
    source, review = read(SOURCE), read(REVIEW)
    report = read(OBSERVATIONS)
    prior = read(ROOT / "docs/continuation-inflection-observations.json")
    assert report["source_sha256"] == sha(SOURCE)
    assert report["review_sha256"] == sha(REVIEW)
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
        assert actual["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        assert 0 <= actual["changed_records"] <= actual["records"]
        streams[actual["mode"]] = actual
    assert sum(s["records"] for s in streams.values()) == 1128312
    identities = set()
    observed_records = {mode: set() for mode in streams}
    owner_ids = set()

    def owners(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                owner_ids.add(ident)
            for child in value.values():
                owners(child)
        elif isinstance(value, list):
            for child in value:
                owners(child)

    for row in report["changes"]:
        category = row["category"]
        assert category in {"candidate", "spacing", "spacing-update", "work"}
        expected = (
            "lexical-nada-"
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
        assert row["occurrences"]
        if category == "candidate":
            assert row["before"] is None
            path = row["after"]["analysis"]
            assert "ending.rya" in path["rules"]
            assert any(
                m["form"] == "으랴" and m["kind"] == "ending" for m in path["morphemes"]
            )
            assert len(row["after"]["reading"]["lemmas"]) == len(path["lemmas"])
        elif category == "spacing":
            assert row["before"] is None
            hyp = row["after"]
            if hyp.get("rule") == "spacing.bare_noun_main_nada":
                noun, right = hyp["records"][-2:]
                pair = next(
                    p
                    for p in review["finite_pair_proposals"]
                    if p["noun"] == noun["analysis"]["normalized"]
                )
                assert pair["noun_entry"] in {
                    e["id"]
                    for slot in noun["dictionary"]["lemmas"]
                    for e in slot["entries"]
                }
                assert all(
                    a["lemmas"][0] == {"text": "나다", "kind": "predicate"}
                    for a in right["analysis"]["analyses"]
                )
            else:
                assert any(
                    "ending.rya" in a["rules"]
                    for r in hyp["records"]
                    for a in r["analysis"]["analyses"]
                )
        elif category == "work":
            assert row["before"]["limits"] == row["after"]["limits"]
            assert (
                row["after"]["segment_probes"]
                <= row["after"]["limits"]["segment_probes"]
            )
        if category != "work":
            owners(row["before"])
            owners(row["after"])
        for occurrence in row["occurrences"]:
            stream = streams[occurrence["mode"]]
            assert 0 <= occurrence["record"] < stream["records"]
            span = occurrence["span"]
            assert span["end"] - span["start"] == len(row["surface"].encode())
            assert row["surface"] in occurrence["context"]
            observed_records[occurrence["mode"]].add(occurrence["record"])
    for mode, indices in observed_records.items():
        assert len(indices) == streams[mode]["changed_records"], mode
    assert report["complete_native_entries"].keys() == owner_ids
    for ident, native in report["complete_native_entries"].items():
        assert ident == native["id"]
        if ident in source["complete_native_entries"]:
            assert native == source["complete_native_entries"][ident]
    if dictionary is not None:
        assert sha(dictionary) == source["dictionary_sha256"]
        assert (
            native_owners(report["changes"], dictionary)
            == report["complete_native_entries"]
        )
    assert report["all_baseline_stream_hashes_verified"]
    assert report["original_candidate_paths_assessments_and_order_preserved"]
    assert report["original_spacing_options_and_order_preserved"]

    runtime = read(RUNTIME)
    assert runtime["cli_sha256"] == report["cli_sha256"]
    assert runtime["dictionary_sha256"] == report["dictionary_sha256"]
    assert runtime["native_entries"] == 208 and runtime["surfaces"] == 465
    assert len(runtime["checks"]) == 36
    groups = {}
    for check in runtime["checks"]:
        key = check["encoding"], check["batch"], check["mode"]
        groups.setdefault(key, []).append(check)
    assert len(groups) == 12
    for checks in groups.values():
        assert {c["cache_bytes"] for c in checks} == {0, 1, 4096}
        assert len({c["sha256"] for c in checks}) == 1
        assert len({c["records"] for c in checks}) == 1
    fixture = read(ROOT / "tests/fixtures/lexical-nada-spacing.json")
    judgments = {(j["id"], j["encoding"]): j for j in runtime["judgments"]}
    assert len(judgments) == len(runtime["judgments"]) == 218
    for case in fixture["cases"]:
        for encoding in ["NFC", "NFD"]:
            actual = judgments[case["id"], encoding]
            assert actual["verdict"] == case["verdict"]
            assert actual["matched"] == (case["verdict"] == "required")
    browser = read(BROWSER)
    assert browser["words"] == 465 and browser["errors"] == []
    assert len(browser["submissions"]) == 9 and browser["allExportsMatchCli"]
    assert browser["nativeMainEntry"] == "62210"
    assert set(browser["endingSourceIds"]) == {"79260", "79261", "80306", "80308"}
    old_corpora = read(ROOT / "docs/bare-noun-spacing-corpora.json")["corpora"]
    corpora = read(CORPORA)["corpora"]
    assert len(corpora) == len(old_corpora) == 4
    for actual, old in zip(corpora, old_corpora, strict=True):
        for key in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert actual[key] == old[key]
        assert actual["current_report_sha256"] == old["after_report_sha256"]
        assert actual["current_report_lines"] == old["report_lines"]
        assert actual["all_gold_rows_and_summaries_identical"]
    print(
        f"Eight full streams, {len(identities)} individual changes, {len(owner_ids)} full native owners, 208 API entries, 109 NFC/NFD cases, 36 CLI cache/filter streams, nine browser exports and four unchanged held-out corpus reports verified; contextual judgments remain unjudged."
    )
    print(dict(Counter(r["category"] for r in report["changes"])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--dictionary", type=type(ROOT))
    args = parser.parse_args()
    verify(args.dictionary)
