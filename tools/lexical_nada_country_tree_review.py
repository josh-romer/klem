"""Verify authored country/tree source-context dispositions, without inferring gold."""

import argparse

from lexical_nada_audit import ROOT, SOURCE, read, sha


def verify():
    source = read(SOURCE)
    review = read(ROOT / "docs/lexical-nada-country-tree-review.json")
    assert review["original_source_sha256"] == sha(SOURCE)
    hits = {
        h["id"]: h
        for h in source["discoveries"]
        if h["listed_cohort"]
        and h["noun"] == "이"
        and (h["right"].startswith("나라") or h["right"].startswith("나무"))
    }
    assert len(hits) == len(review["reviews"]) == 203
    seen = set()
    for row in review["reviews"]:
        ident = row["discovery_id"]
        assert ident not in seen
        seen.add(ident)
        original = hits[ident]
        for field in ["entry", "sense", "group", "text_index", "complete_group"]:
            assert row[field] == original[field]
        assert row["original_match"] == original["match"]
        assert row["right_lexeme"] in ["나라", "나무"]
        assert original["right"].startswith(row["right_lexeme"])
        assert row["disposition"] == "other_right_lexeme_not_main_nada_pair_evidence"
        assert row["reason"]
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
    assert seen == hits.keys()
    print(
        "Verified 203 source-context dispositions; independent/contextual gold remains pending."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
