"""Publish explicit original-to-replacement judgments for COV-017bu.

The original preflight and historical fixtures remain immutable. Ordered owners
are recorded for these individually reviewed selectors, not inferred from an
arbitrary analysis's last lemma. General 냐 readings remain separate.
"""

import argparse
import copy
import json

from adjectival_allomorph_audit import OWNERS, SOURCE, coda, effective_proposals
from lexical_nada_audit import ROOT, read, sha

CORRECTIONS = ROOT / "tests/fixtures/adjectival-allomorph-corrections.json"


def corrections():
    source = read(SOURCE)
    rows = []
    originals = {c["id"]: c for c in source["original_ledger"]["cases"]}
    for flagged in source["flagged_originals"]:
        original = originals[flagged["case_id"]]
        judgment = flagged["original_judgment"]
        # These 26 paths have no adjective-forming suffix and end in the
        # questioned predicate/copula itself. Reject neither a nominal before
        # 답다 nor a different earlier predicate in a compound analysis.
        assert "답다" not in judgment["morphemes"]
        ending_index = next(
            i for i, form in enumerate(judgment["morphemes"]) if form in OWNERS
        )
        assert not any(
            form in OWNERS for form in judgment["morphemes"][ending_index + 1 :]
        )
        head = judgment["lemmas"][-1]
        assert head.endswith("다")
        stem = head.removesuffix("다")
        assert coda(stem) in {0, 8}
        canonical = judgment["morphemes"][ending_index]
        ident = OWNERS[canonical][0]
        replacement = copy.deepcopy(original)
        target = next(j for j in replacement["judgments"] if j["id"] == judgment["id"])
        target.update(
            verdict="forbidden",
            source=f"adjectival-allomorph-{ident}",
            reason=f"Explicit correction of the archived required path: canonical -{canonical} takes a non-ㄹ closed underlying adjective owner, but its ordered owner here is {head}. The distinct general -{canonical[1:]} reading remains available. This component boundary is not a contextual sentence judgment.",
        )
        rows.append(
            {
                "original": original,
                "replacement": replacement,
                "ordered_owner": {
                    "lemma_index": len(judgment["lemmas"]) - 1,
                    "lemma": head,
                    "underlying_stem": stem,
                    "coda": coda(stem),
                    "canonical_morpheme_index": ending_index,
                    "canonical_form": canonical,
                },
                "original_source_url": flagged["original_source_url"],
                "replacement_source_url": source["complete_native_entries"][
                    f"krdict:{ident}"
                ]["url"],
                "citation_correction": original["id"]
                == "danda-composition-기냔다-으냔다",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return rows


def matrix_cases():
    source = read(SOURCE)
    rows = []
    for proposal in effective_proposals():
        form = next(
            f
            for f, kind in reversed(
                list(
                    zip(proposal["morphemes"], proposal["morpheme_kinds"], strict=True)
                )
            )
            if kind == "ending"
        )
        ident = source["grammar_inventory"][form][0]
        rows.append(
            {
                "id": proposal["id"],
                "surface": proposal["surface"],
                "judgments": [
                    {
                        "id": "path",
                        **{
                            key: proposal[key]
                            for key in [
                                "lemmas",
                                "lemma_kinds",
                                "morphemes",
                                "morpheme_kinds",
                            ]
                        },
                        "verdict": proposal["proposed_verdict"],
                        "source": "adjectival-allomorph-"
                        + ident.removeprefix("krdict:"),
                        "reason": "Source-backed structural allomorph proposal: "
                        + proposal["origin"]
                        + ". Original draft and derived-spelling correction are archived separately; contextual and independent review remain pending.",
                    }
                ],
            }
        )
    return rows


def freeze():
    assert not CORRECTIONS.exists()
    CORRECTIONS.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "original_ledger_sha256": read(SOURCE)["ledger_sha256"],
                "superseded": corrections(),
                "matrix_cases": matrix_cases(),
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify():
    data = read(CORRECTIONS)
    source = read(SOURCE)
    assert data["source_sha256"] == sha(SOURCE)
    assert data["original_ledger_sha256"] == source["ledger_sha256"]
    assert data["superseded"] == corrections()
    assert data["matrix_cases"] == matrix_cases()
    assert len(data["superseded"]) == 26 and len(data["matrix_cases"]) == 396
    ledger = read(ROOT / "tests/fixtures/validity.json")
    indexed = {c["id"]: c for c in ledger["cases"]}
    for case in [r["replacement"] for r in data["superseded"]] + data["matrix_cases"]:
        assert indexed[case["id"]] == case
        for judgment in case["judgments"]:
            ident = "krdict:" + judgment["source"].removeprefix("adjectival-allomorph-")
            assert (
                ledger["sources"][judgment["source"]]
                == source["complete_native_entries"][ident]["url"]
            )
    print(
        "Verified 26 explicit ledger corrections and 396 effective structural cases; original source artifacts remain unchanged."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        freeze()
    elif args.verify:
        verify()
    else:
        parser.error("choose --freeze or --verify")
