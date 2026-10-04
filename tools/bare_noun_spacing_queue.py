"""Verify saved source-scoped spacing observations without adjudicating context."""

import argparse
import json
from pathlib import Path
from bare_noun_spacing_audit import verify as verify_original
from bare_noun_spacing_additional import verify as verify_additional

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true", required=True)
    p.parse_args()
    verify_original()
    verify_additional()
    source = read("tests/fixtures/bare-noun-spacing-sources.json")
    additional = read("tests/fixtures/bare-noun-spacing-additional-pairs.json")
    review = read("docs/bare-noun-spacing-source-review.json")
    assert (
        review["contextual_verdict"] == "unjudged"
        and review["independent_review"] == "pending"
    )
    native = dict(source["complete_native_entries"])
    native.update(additional["complete_native_entries"])
    expected_pairs = {
        ("신경질", "내다"),
        ("용기", "내다"),
        ("짜증", "내다"),
        ("기분", "내키다"),
    }
    assert {(p["noun"], p["verb"]) for p in review["pairs"]} == expected_pairs
    for pair in review["pairs"]:
        assert any(
            e["headword"] == pair["noun"] and e["pos"] == "명사"
            for e in native.values()
        )
        assert any(
            e["headword"] == pair["verb"] and e["pos"] == "동사"
            for e in native.values()
        )
        for ref in pair["sources"]:
            entry = native[ref["entry"]]
            sense = next(s for s in entry["senses"] if s["id"] == ref["sense"])
            group = sense["examples"][ref["group"] - 1]
            hits = source["discovery"]["hits"][pair["noun"]]
            assert any(
                h["entry"] == ref["entry"]
                and h["sense"] == ref["sense"]
                and h["group"] == ref["group"]
                and h["text"] in group
                for h in hits
            )
    listed = read("docs/bare-noun-spacing-listed-pairs.json")
    assert (
        len(listed["case_marked_pairs"]) == 16
        and len(listed["registered_whole_verbs"]) == 5
    )
    reviews = {r["head"]: r for r in source["pair_reviews"]}
    assert {c["head"] for c in listed["case_marked_pairs"]} == set(reviews)
    sense = next(s for s in native["krdict:89906"]["senses"] if s["id"] == "13")
    for c in listed["case_marked_pairs"]:
        assert c["native_example"] == sense["examples"][c["group"] - 1][0]
        assert c["surface"] == c["native_example"].replace(" ", "").removesuffix(".")
        for obs in c["observations"].values():
            assert (
                obs["before_spacing"]["alternatives"]
                == obs["after_spacing"]["alternatives"]
            )
            assert obs["before_spacing"]["alternatives"]
            assert all(
                h.get("rule") is None for h in obs["after_spacing"]["alternatives"]
            )
        assert c["contextual_verdict"] == "unjudged"
    for c in listed["registered_whole_verbs"]:
        head = c["surface"].removesuffix("내다")
        assert c["native_entries"] == reviews[head]["whole_verb_entries"]
        for obs in c["observations"].values():
            assert any(x["lemmas"][0]["text"] == c["surface"] for x in obs["analyses"])
            assert not any(h.get("rule") for h in obs["spacing"]["alternatives"])
    observations = read("docs/bare-noun-spacing-observations.json")
    prior = read("docs/continuation-left-observations.json")
    assert (
        observations["before_cli_sha256"] == source["cli_sha256"]
        and observations["dictionary_sha256"] == source["dictionary_sha256"]
    )
    assert (
        observations["default_records_byte_identical"]
        and observations["legacy_spacing_hypotheses_and_order_preserved"]
        and observations["all_baseline_stream_hashes_verified"]
    )
    assert len(observations["comparisons"]) == 8
    for c, old in zip(observations["comparisons"], prior["comparisons"], strict=True):
        for key in ["mode", "source", "source_sha256", "records"]:
            assert c[key] == old[key]
        assert c["before_jsonl_sha256"] == old["after_jsonl_sha256"]
        if "spacing" not in c["mode"]:
            assert (
                c["changed_records"] == 0
                and c["before_jsonl_sha256"] == c["after_jsonl_sha256"]
            )
    assert sum(c["records"] for c in observations["comparisons"]) == 1128312
    assert observations["added_hypotheses"] == []
    assert {c["surface"] for c in observations["work_metadata_changes"]} == {
        "용기가",
        "용기는",
        "용기를",
        "용기도",
    }
    for c in observations["work_metadata_changes"]:
        assert c["before"]["segment_probes"] == 0 and c["after"]["segment_probes"] == 2
        assert {k: v for k, v in c["before"].items() if k != "segment_probes"} == {
            k: v for k, v in c["after"].items() if k != "segment_probes"
        }
    corpus = read("docs/bare-noun-spacing-corpora.json")
    old_corpus = read("docs/continuation-left-corpora.json")
    assert len(corpus["corpora"]) == 4
    for c, old in zip(corpus["corpora"], old_corpus["corpora"], strict=True):
        for key in ["corpus", "partition", "source", "source_sha256"]:
            assert c[key] == old[key]
        assert (
            c["after_report_sha256"]
            == c["before_report_sha256"]
            == old["after_report_sha256"]
        )
        assert (
            c["converted_rows"] == old["rows_compared"]
            and c["all_gold_rows_and_summaries_identical"]
        )
    runtime = read("docs/bare-noun-spacing-runtime.json")
    preflight = read("docs/continuation-gold-residual-preflight.json")
    assert (
        runtime["complete_native_entries"] == 34
        and runtime["surfaces"] == 95
        and runtime["judgment_observations"] == 134
    )
    assert {
        (s["encoding"], s["cache_bytes"], s["mode"]) for s in runtime["streams"]
    } == {
        (e, c, m)
        for e in ["NFC", "NFD"]
        for c in [0, 1, 4096]
        for m in ["all", "headword", "compatible"]
    }
    for c, original in zip(
        runtime["original_corpus_residuals"], preflight["cases"], strict=True
    ):
        for key in [
            "original_gold_row",
            "source",
            "source_sha256",
            "original_sentence_block",
        ]:
            assert c[key] == original[key]
        for obs in c["observations"].values():
            assert obs["raw_gold_indices"] == []
            assert bool(obs["separate_word_group_indices"]) == (
                c["original_gold_row"]["surface"] in ["짜증낼", "짜증내시네"]
            )
        assert (
            c["contextual_verdict"] == "unjudged"
            and c["independent_review"] == "pending"
        )
    print(
        "Four exact pairs, sixteen native case examples, five whole verbs, eight full streams and six unchanged corpus residuals verified; all contextual judgments remain unjudged."
    )


if __name__ == "__main__":
    main()
