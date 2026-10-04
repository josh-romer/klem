"""Verify individual listed-cohort source reviews without inferring contextual gold."""

import argparse
from collections import Counter

from lexical_nada_audit import MAIN, ROOT, SOURCE, read, sha
from lexical_nada_review import PAIRS, REVIEW

LISTED = ROOT / "docs/lexical-nada-listed-review.json"
NEW_PAIRS = {
    "집": ("krdict:71358", "1", "13"),
    "사람": ("krdict:58161", "0", "15"),
    "돈": ("krdict:17204", "1", "14"),
    "피": ("krdict:73269", "1", "18"),
}


def verify():
    source, original, review = read(SOURCE), read(REVIEW), read(LISTED)
    country_path = ROOT / "docs/lexical-nada-country-tree-review.json"
    country = read(country_path)
    assert review["original_source_sha256"] == sha(SOURCE)
    assert review["original_review_sha256"] == sha(REVIEW)
    assert review["country_tree_review_sha256"] == sha(country_path)
    previous_pairs = {
        h["id"]
        for p in original["finite_pair_proposals"]
        for h in p["reviewed_native_examples"]
    }
    prior = previous_pairs | {h["discovery_id"] for h in country["reviews"]}
    assert len(prior) == 239
    assert review["prior_reviewed_discovery_ids"] == sorted(prior)
    listed = {h["id"]: h for h in source["discoveries"] if h["listed_cohort"]}
    entries = source["complete_native_entries"]
    senses = {s["id"]: s for s in entries[MAIN]["senses"]}
    seen = set()
    for row in review["reviews"]:
        ident = row["discovery_id"]
        assert ident not in seen | prior
        seen.add(ident)
        hit = listed[ident]
        for field in [
            "entry",
            "head",
            "sense",
            "group",
            "text_index",
            "complete_group",
            "noun",
            "right",
            "span",
            "char_span",
        ]:
            assert row[field] == hit[field], (ident, field)
        assert row["original_match"] == hit["match"]
        assert row["reason"]
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
        disposition = row["disposition"]
        if disposition == "native_bare_main_nada_pair":
            noun = row["noun"]
            identity = NEW_PAIRS.get(noun)
            if identity:
                noun_id, homonym, sense = identity
            else:
                noun_id, sense = PAIRS[noun][:2]
                noun_id = "krdict:" + noun_id
                homonym = entries[noun_id]["homonym"]
            assert row["noun_entry"] == noun_id
            assert (
                entries[noun_id]["headword"],
                entries[noun_id]["pos"],
                entries[noun_id]["homonym"],
            ) == (noun, "명사", homonym)
            assert row["main_entry"] == MAIN
            assert row["source_sense_reference"] == sense
        elif disposition == "registered_whole_construction_review_pending":
            assert (
                row["registered_whole_entries"]
                == source["noun_inventory"][row["noun"]]["registered_whole_entries"]
            )
            assert row["registered_whole_entries"]
            for ident in row["registered_whole_entries"]:
                assert entries[ident]["headword"] == row["noun"] + "나다"
            for key in row["guidance"]:
                assert key in review["primary_guidance"]
        else:
            assert disposition == "other_role_or_right_lexeme"
            assert row["left_role"] and row["right_lexeme"]
    assert seen | prior == listed.keys()
    counts = Counter(row["disposition"] for row in review["reviews"])
    assert review["counts"] == {
        "prior_reviewed": len(prior),
        "newly_reviewed": len(seen),
        "listed_total": len(listed),
        "new_dispositions": dict(counts),
        "listed_bare_pair_occurrences": len(previous_pairs)
        + counts["native_bare_main_nada_pair"],
        "listed_registered_whole_boundaries": counts[
            "registered_whole_construction_review_pending"
        ],
        "listed_other_roles": len(country["reviews"])
        + counts["other_role_or_right_lexeme"],
        "broad_outside_listed_pending": sum(
            not h["listed_cohort"] for h in source["discoveries"]
        ),
    }
    proposals = review["new_finite_pair_proposals"]
    assert len(proposals) == 4
    assert {p["noun"] for p in proposals} == NEW_PAIRS.keys()
    new_hits = set()
    for p in proposals:
        noun_id, homonym, sense = NEW_PAIRS[p["noun"]]
        assert (p["noun_entry"], p["noun_homonym"], p["main_sense_reference"]) == (
            noun_id,
            homonym,
            sense,
        )
        assert (p["main_entry"], p["main_homonym"]) == (MAIN, "1")
        assert p["main_sense_definition"] == senses[sense]["definition"]
        assert p["main_sense_complete_groups"] == senses[sense]["examples"]
        assert (
            p["contextual_verdict"] == "unjudged"
            and p["independent_review"] == "pending"
        )
        assert p["scope"]
        for hit in p["reviewed_native_examples"]:
            assert hit == listed[hit["id"]]
            assert hit["noun"] == p["noun"]
            assert hit["id"] not in new_hits
            new_hits.add(hit["id"])
    assert len(new_hits) == 7
    fixture_path = ROOT / "tests/fixtures/lexical-nada-spacing.json"
    old_cases = {c["id"]: c for c in read(fixture_path)["cases"]}
    superseded = review["superseded_exclusions"]
    assert {s["original_case_id"] for s in superseded} == {
        "lexical-nada-excluded-template-05",
        "lexical-nada-excluded-template-09",
    }
    for row in superseded:
        original = old_cases[row["original_case_id"]]
        assert (
            original["verdict"] == "forbidden" and original["surface"] == row["surface"]
        )
        assert row["original_fixture_sha256"] == sha(fixture_path)
        assert "".join(row["replacement_segments"]) == row["surface"]
        assert (
            row["source_discovery_ids"] and set(row["source_discovery_ids"]) <= new_hits
        )
        for ident in row["source_discovery_ids"]:
            assert listed[ident]["noun"] == row["replacement_segments"][0]
    print(
        "Verified all 631 listed source-context dispositions and four new pair licenses; contextual/independent review remains pending."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    verify()
