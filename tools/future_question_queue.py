"""Verify individual future-question engineering evidence without inferring gold."""

import argparse
import hashlib
import json
from collections import Counter

from future_question_additional import ADDITIONAL
from future_question_additional import verify as verify_additional
from future_question_audit import FIXTURE, SOURCE, SUPPLEMENT
from future_question_audit import verify as verify_source
from lexical_nada_audit import ROOT, read, sha
from lexical_nada_compare import canon, native_owners


def verify(dictionary=None):
    verify_source()
    verify_additional()
    source, fixture = read(SOURCE), read(FIXTURE)
    report = read(ROOT / "docs/future-question-observations.json.gz")
    prior_path = ROOT / "docs/lexical-nada-listed-observations.json.gz"
    prior = read(prior_path)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["previous_observations_sha256"] == sha(prior_path)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert report["contextual_verdict"] == "unjudged"
    assert report["independent_review"] == "pending"
    assert len(report["comparisons"]) == len(prior["comparisons"]) == 8
    streams = {}
    for row, old in zip(report["comparisons"], prior["comparisons"], strict=True):
        for field in ["mode", "source", "source_sha256", "records"]:
            assert row[field] == old[field]
        assert row["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        streams[row["mode"]] = row
    assert sum(r["records"] for r in streams.values()) == 1128312
    for row in report["diagnostics"]:
        mode = row["mode"].removeprefix("diagnostic-")
        assert row["records"] == len(source["before_streams"][mode])
        before = "".join(json_line(r) for r in source["before_streams"][mode])
        assert row["before_jsonl_sha256"] == hashlib.sha256(before.encode()).hexdigest()
        streams[row["mode"]] = row
    observed = {mode: set() for mode in streams}
    identities = set()
    for row in report["changes"]:
        category = row["category"]
        expected = (
            "future-question-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, row["surface"], row["before"], row["after"]]).encode()
            ).hexdigest()[:24]
        )
        assert row["id"] == expected and expected not in identities
        identities.add(expected)
        assert category in ["candidate", "spacing", "spacing-update", "work"]
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
        if category == "candidate":
            assert row["before"] is None
            a = row["after"]["analysis"]
            assert "particle.future_question" in a["rules"]
            assert any(
                m["kind"] == "ending" and m["form"] == "을지" for m in a["morphemes"]
            )
        assert row["occurrences"]
        for location in row["occurrences"]:
            assert location["mode"] in streams and location["context"]
            observed[location["mode"]].add(location["record"])
    for mode, indices in observed.items():
        assert len(indices) == streams[mode]["changed_records"], mode
    retained = dict(
        source["complete_native_entries"], **read(ADDITIONAL)["complete_native_entries"]
    )
    assert all(retained[i] == e for i, e in report["complete_native_entries"].items())
    if dictionary:
        assert (
            native_owners(report["changes"], dictionary)
            == report["complete_native_entries"]
        )
    for field in [
        "old_raw_paths_native_fields_and_known_conflicts_preserved",
        "old_spacing_options_and_order_preserved",
        "all_baseline_stream_hashes_verified",
    ]:
        assert report[field]
    runtime = read(ROOT / "docs/future-question-packaged-runtime.json")
    combined = set(fixture["before_words"]) | set(read(SUPPLEMENT)["before_words"])
    assert runtime["source_sha256"] == sha(SOURCE)
    assert runtime["cli_sha256"] == report["cli_sha256"]
    assert runtime["dictionary_sha256"] == source["dictionary_sha256"]
    assert runtime["surfaces"] == len(combined) == 382
    assert runtime["native_entries"] == len(retained) == 1011
    assert len(runtime["checks"]) == 27
    assert {(c["id"], c["encoding"], c["verdict"]) for c in runtime["judgments"]} == {
        (c["id"], encoding, c["verdict"])
        for c in fixture["cases"]
        for encoding in ["NFC", "NFD"]
    }
    assert all(
        c["matched"] == (c["verdict"] == "required") for c in runtime["judgments"]
    )
    browser = read(ROOT / "docs/future-question-packaged-browser.json")
    assert browser["words"] == len(combined) and browser["cases"] == len(
        fixture["cases"]
    )
    assert len(browser["checks"]) == 9 and browser["errors"] == []
    assert browser["endingEntryIds"] == ["86686", "86133"]
    assert browser["allExportsMatchCli"] and browser["mobileNoHorizontalOverflow"]
    assert len(browser["rendered"]) == 7
    corpora = read(ROOT / "docs/future-question-corpora.json")
    prior_corpora_path = ROOT / "docs/lexical-nada-listed-corpora.json"
    assert corpora["previous_report_sha256"] == sha(prior_corpora_path)
    assert len(corpora["corpora"]) == 4
    assert sum(c["converted_rows"] for c in corpora["corpora"]) == 66570
    changes = 0
    for row, old in zip(
        corpora["corpora"], read(prior_corpora_path)["corpora"], strict=True
    ):
        for field in [
            "corpus",
            "partition",
            "source",
            "source_sha256",
            "converted_rows",
            "report_lines",
        ]:
            assert row[field] == old[field]
        assert row["before_report_sha256"] == old["after_report_sha256"]
        assert (
            row["original_ids_surfaces_gold_preserved"]
            and row["prior_component_sets_preserved"]
        )
        assert set(row["changed_summary_fields"]) <= {
            "grouped_matches",
            "recovered_gold_lemmas",
            "transformed_matches",
            "grouped_lemma_recall",
            "lemma_recall",
            "transformed_grouped_recall",
            "mean_candidates",
            "p95_candidates",
            "max_candidates",
        }
        for change in row["changes"]:
            before, after = change["before"], change["after"]
            for field in ["id", "surface", "expected"]:
                assert before[field] == after[field]
            assert not before["matched"] and after["matched"]
            assert after["recovered"] >= before["recovered"]
            assert all(
                any(set(group) <= set(now) for now in after["recovered_sets"])
                for group in before["recovered_sets"]
            )
            assert (
                change["id"]
                == "future-question-corpus-"
                + hashlib.sha256(
                    json.dumps(
                        [row["corpus"], row["partition"], before["id"]], sort_keys=True
                    ).encode()
                ).hexdigest()[:24]
            )
            assert (
                "\t".join(change["source_row"])
                in change["complete_sentence"].splitlines()
            )
            assert change["source_row"][1] == before["surface"]
            assert (
                change["contextual_verdict"] == "unjudged"
                and change["independent_review"] == "pending"
            )
            changes += 1
    assert changes == 5
    print(
        "Verified future-question evidence:",
        dict(Counter(c["category"] for c in report["changes"])),
    )


def json_line(record):
    # CLI serialization follows struct declaration order, retained by JSON load.
    import json

    return json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--dictionary", type=__import__("pathlib").Path)
    args = parser.parse_args()
    verify(args.dictionary)
