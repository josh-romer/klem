"""Verify listed noun/main-나다 engineering evidence and retain pending judgments."""

import argparse
import hashlib
import json
from collections import Counter

from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon
from lexical_nada_listed_additional import ADDITIONAL
from lexical_nada_listed_additional import verify as verify_additional
from lexical_nada_listed_fixtures import BEFORE, FIXTURE
from lexical_nada_listed_fixtures import verify as verify_fixtures
from lexical_nada_listed_review import NEW_PAIRS
from lexical_nada_listed_review import verify as verify_review


def verify():
    verify_review()
    verify_fixtures()
    verify_additional()
    source, fixture = read(BEFORE), read(FIXTURE)
    report = read(ROOT / "docs/lexical-nada-listed-observations.json.gz")
    prior_path = ROOT / "docs/caution-ending-observations.json.gz"
    prior = read(prior_path)
    assert report["source_sha256"] == sha(BEFORE)
    assert report["previous_observations_sha256"] == sha(prior_path)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    streams = {}
    assert len(report["comparisons"]) == len(prior["comparisons"]) == 8
    for row, old in zip(report["comparisons"], prior["comparisons"], strict=True):
        for field in ["mode", "source", "source_sha256", "records"]:
            assert row[field] == old[field]
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        if "spacing" not in row["mode"]:
            assert row["changed_records"] == 0
            assert row["before_jsonl_sha256"] == row["after_jsonl_sha256"]
        streams[row["mode"]] = row
    assert sum(row["records"] for row in streams.values()) == 1128312
    for row in report["diagnostics"]:
        mode = row["mode"].removeprefix("diagnostic-")
        before = source["before_streams"][mode]
        assert row["records"] == len(before)
        encoded = "".join(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n"
            for r in before
        ).encode()
        assert row["before_jsonl_sha256"] == hashlib.sha256(encoded).hexdigest()
        streams[row["mode"]] = row
    indices = {mode: set() for mode in streams}
    seen = set()
    for row in report["changes"]:
        category = row["category"]
        assert category in ["spacing", "work"]
        ident = (
            "lexical-nada-listed-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == ident and ident not in seen
        seen.add(ident)
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["independent_review"] == "pending"
        )
        if category == "spacing":
            assert row["before"] is None
            h = row["after"]
            assert h["rule"] == "spacing.bare_noun_main_nada"
            assert "".join(r["surface"] for r in h["records"]) == row["surface"]
            noun, right = h["records"][-2:]
            head = noun["analysis"]["normalized"]
            ident, hom, _ = NEW_PAIRS[head]
            for r, expected, pos, homonym in [
                (noun, ident, "명사", hom),
                (right, "krdict:62210", "동사", "1"),
            ]:
                for a, assessment in zip(
                    r["analysis"]["analyses"], r["dictionary"]["readings"], strict=True
                ):
                    if r is noun:
                        assert a["unchanged"] and not a["morphemes"]
                        assert a["lemmas"] == [{"text": head, "kind": "unclassified"}]
                    else:
                        assert a["lemmas"][0] == {"text": "나다", "kind": "predicate"}
                    assert any(
                        e["id"] == expected and e["status"] != "incompatible"
                        for e in assessment["lemmas"][0]["entries"]
                    )
                    slot = next(
                        s
                        for s in r["dictionary"]["lemmas"]
                        if s["lemma"] == a["lemmas"][0]
                    )
                    assert any(
                        e["id"] == expected
                        and e["pos"] == pos
                        and e["homonym"] == homonym
                        for e in slot["entries"]
                    )
        else:
            assert [
                key for key in row["before"] if row["before"][key] != row["after"][key]
            ] == ["segment_probes"]
            assert (
                row["after"]["segment_probes"]
                <= row["after"]["limits"]["segment_probes"]
            )
        assert row["occurrences"]
        for occurrence in row["occurrences"]:
            assert occurrence["context"]
            indices[occurrence["mode"]].add(occurrence["record"])
    for mode, changed in indices.items():
        assert len(changed) == streams[mode]["changed_records"], mode
    retained = dict(
        source["complete_native_entries"], **read(ADDITIONAL)["complete_native_entries"]
    )
    for ident, entry in report["complete_native_entries"].items():
        assert entry == retained[ident]
    for field in [
        "old_raw_paths_native_fields_and_known_conflicts_preserved",
        "old_spacing_options_and_order_preserved",
        "all_baseline_stream_hashes_verified",
    ]:
        assert report[field]
    runtime = read(ROOT / "docs/lexical-nada-listed-packaged-runtime.json")
    assert runtime["source_sha256"] == sha(BEFORE)
    assert runtime["cli_sha256"] == report["cli_sha256"]
    assert runtime["dictionary_sha256"] == source["dictionary_sha256"]
    assert runtime["native_entries"] == len(retained)
    assert runtime["surfaces"] == len(fixture["before_raw_words"])
    assert {(r["id"], r["encoding"], r["verdict"]) for r in runtime["judgments"]} == {
        (c["id"], e, c["verdict"]) for c in fixture["cases"] for e in ["NFC", "NFD"]
    }
    assert all(
        r["complete"] and r["matched"] == (r["verdict"] == "required")
        for r in runtime["judgments"]
    )
    assert {r["encoding"] for r in runtime["checks"]} == {"NFC", "NFD"}
    assert {r["cache_bytes"] for r in runtime["checks"]} == {0, 1, 4096}
    assert {r["mode"] for r in runtime["checks"]} == {"all", "headword", "compatible"}
    browser = read(ROOT / "docs/lexical-nada-listed-packaged-browser.json")
    assert browser["words"] == len(fixture["before_raw_words"])
    assert browser["errors"] == [] and browser["allExportsMatchCli"]
    assert browser["wholePiVerbPreserved"] and browser["mobileNoHorizontalOverflow"]
    assert browser["nativeMainEntry"] == "62210" and len(browser["rendered"]) == 5
    assert {r["nounId"] for r in browser["rendered"]} == {
        v[0].removeprefix("krdict:") for v in NEW_PAIRS.values()
    }
    corpora = read(ROOT / "docs/lexical-nada-listed-corpora.json")
    prior_path = ROOT / "docs/caution-ending-corpora.json"
    assert corpora["previous_report_sha256"] == sha(prior_path)
    assert len(corpora["corpora"]) == 4
    for row, old in zip(corpora["corpora"], read(prior_path)["corpora"], strict=True):
        for field in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert row[field] == old[field]
        assert (
            row["before_report_sha256"]
            == row["after_report_sha256"]
            == old["after_report_sha256"]
        )
        assert row["all_gold_rows_identical"] and row["all_summary_fields_identical"]
        assert row["changed_summary_fields"] == []
    print(
        "Verified listed source/implementation evidence:",
        dict(Counter(r["category"] for r in report["changes"])),
        "; two ending dependencies and independent/contextual review remain pending.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
