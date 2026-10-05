"""Review every native -되다 lead without replacing original source evidence.

Exact noun-origin pairs supply positive lexical identity evidence for finite
nominal formation proposals. Missing, opaque, nested and competing bases retain
individual unresolved dispositions. This is an attributed agent review, not an
independent linguistic review or contextual precision measurement.
"""

import argparse
import hashlib
import json
from collections import Counter, defaultdict

from doeda_suffix_audit import SOURCE
from doeda_suffix_regressions import effective_formations
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-native-review.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-native-formations.json"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def review(source):
    entries = source["complete_native_entries"]
    existing = {p["head"]: p for p in effective_formations()}
    reviews, by_head = [], defaultdict(list)
    for lead in source["native_inventory"]:
        owner = entries[lead["id"]]
        assert (owner["headword"], owner["pos"]) == (lead["head"], lead["native_pos"])
        assert lead["literal_base"] + "되다" == owner["headword"]
        origins = sorted({o[:-2] for o in owner["origins"] if o.endswith("되다")})
        bases = []
        for ident in lead["base_entries"]:
            entry = entries[ident]
            assert entry["headword"] == lead["literal_base"]
            shared = sorted(set(entry["origins"]) & set(origins))
            status = (
                "noun-origin-match"
                if entry["pos"] == "명사" and shared
                else "recorded-origin-difference"
                if entry["origins"] and origins and not shared
                else "role-or-origin-review-needed"
            )
            bases.append(
                {
                    "id": ident,
                    "entry_sha256": digest(entry),
                    "native_pos": entry["pos"],
                    "recorded_origins": entry["origins"],
                    "shared_origins": shared,
                    "evidence_status": status,
                }
            )
        supported = [
            b["id"] for b in bases if b["evidence_status"] == "noun-origin-match"
        ]
        cls = "verb" if owner["pos"] == "동사" else "adjective"
        prior = existing.get(owner["headword"])
        if supported:
            disposition = "nominal-origin-supported"
            reason = (
                "Whole native predicate explicitly records origin + 되다; the same "
                "origin is recorded in a native noun at the literal base. Whole POS "
                "supplies the inflection class. This supports a finite derivational "
                "proposal under suffix 74902, rather than arbitrary noun stripping."
            )
        elif prior and prior["predicate_class"] == cls:
            disposition = "existing-source-listed-role"
            reason = (
                "The earlier suffix example/corpus proposal supplies this base role "
                "and class. Native noun-origin matching adds no independent evidence; "
                "opaque roots, absent bases and competing homonyms stay separately visible."
            )
        else:
            disposition = "unresolved-native-base"
            reason = (
                "The literal head and native POS alone do not establish the intended "
                "noun/root/adverb base. Review full definitions, nested suffixes, "
                "lexical constructions and missing or competing entries before licensing."
            )
        row = {
            "id": "doeda-native-review-" + lead["id"].removeprefix("krdict:"),
            "native_entry_id": lead["id"],
            "native_entry_sha256": digest(owner),
            "head": lead["head"],
            "base": lead["literal_base"],
            "predicate_class": cls,
            "whole_recorded_origins": owner["origins"],
            "suffix_origin_components": origins,
            "base_entry_reviews": bases,
            "matching_noun_entries": supported,
            "disposition": disposition,
            "reason": reason,
            "existing_proposal": prior,
            "source": owner["url"],
            "suffix_source": entries["krdict:74902"]["url"],
            "reviewer": "agent",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        reviews.append(row)
        if supported:
            by_head[lead["head"]].append(row)
    proposals = []
    for head, owners in sorted(by_head.items()):
        classes = {r["predicate_class"] for r in owners}
        assert len(classes) == 1, (head, "different classes need separate ownership")
        cls = next(iter(classes))
        prior = existing.get(head)
        if prior:
            assert (prior["base_kind"], prior["predicate_class"]) == ("nominal", cls)
            continue
        proposals.append(
            {
                "id": "doeda-native-formation-" + digest([head, "nominal", cls])[:24],
                "head": head,
                "base": head[:-2],
                "base_kind": "nominal",
                "predicate_class": cls,
                "whole_entries": [r["native_entry_id"] for r in owners],
                "matching_noun_entries": sorted(
                    {i for r in owners for i in r["matching_noun_entries"]}
                ),
                "review_ids": [r["id"] for r in owners],
                "suffix_source": "krdict:74902",
                "suffix_sense": "1" if cls == "verb" else "2",
                "source_review": "agent review of exact full native whole/noun origins and POS; independent/formal-history review pending",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    assert len(reviews) == 1850
    assert len(proposals) == 1570
    assert all(p["predicate_class"] == "verb" for p in proposals)
    return reviews, proposals


def fixture(proposals):
    variants = [
        {
            "id": "dictionary-form",
            "tail": "되다",
            "morphemes": ["다"],
            "morpheme_kinds": ["ending"],
        },
        {
            "id": "past-final",
            "tail": "되었다",
            "morphemes": ["었", "다"],
            "morpheme_kinds": ["prefinal", "ending"],
        },
        {
            "id": "contracted-past-polite",
            "tail": "됐어요",
            "morphemes": ["었", "어요"],
            "morpheme_kinds": ["prefinal", "ending"],
        },
        {
            "id": "contracted-polite",
            "tail": "돼요",
            "morphemes": ["어요"],
            "morpheme_kinds": ["ending"],
        },
        {
            "id": "formal-polite",
            "tail": "됩니다",
            "morphemes": ["습니다"],
            "morpheme_kinds": ["ending"],
        },
        {
            "id": "conditional",
            "tail": "되면",
            "morphemes": ["으면"],
            "morpheme_kinds": ["ending"],
        },
        {
            "id": "connective",
            "tail": "되어",
            "morphemes": ["어"],
            "morpheme_kinds": ["ending"],
        },
        {
            "id": "nominal-topic",
            "tail": "되기는",
            "morphemes": ["기", "는"],
            "morpheme_kinds": ["ending", "particle"],
        },
        {
            "id": "nominal-copula",
            "tail": "됨이다",
            "morphemes": ["음", "다"],
            "morpheme_kinds": ["ending", "ending"],
            "later_lemmas": [{"text": "이다", "kind": "copula"}],
        },
        {
            "id": "present-adnominal",
            "tail": "되는",
            "morphemes": ["는"],
            "morpheme_kinds": ["ending"],
        },
    ]
    return {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "formations": proposals,
        "variants": variants,
        "case_identity": "formation.id + '-' + variant.id; full path is nominal base, owned 되다 suffix, variant inflections and explicit later lemmas",
        "cases": len(proposals) * len(variants),
        "scope": "15,700 authored structural proposals derived from individually attributed native origin/class reviews. All source data and corpus gold remain unchanged. This manifest does not certify contextual precision, entry sense selection or an independent linguistic review.",
    }


def verify_data(report, cases):
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["source_sha256"] == sha(SOURCE)
    reviews, proposals = review(read(SOURCE))
    assert report["native_reviews"] == reviews
    assert report["formation_proposals"] == proposals
    assert report["disposition_counts"] == dict(
        Counter(r["disposition"] for r in reviews)
    )
    assert cases == fixture(proposals)
    identifiers = [
        p["id"] + "-" + v["id"] for p in proposals for v in cases["variants"]
    ]
    assert len(identifiers) == len(set(identifiers)) == cases["cases"] == 15700


def freeze():
    assert not REPORT.exists() and not FIXTURE.exists()
    reviews, proposals = review(read(SOURCE))
    cases = fixture(proposals)
    FIXTURE.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "fixture_sha256": sha(FIXTURE),
        "native_reviews": reviews,
        "formation_proposals": proposals,
        "disposition_counts": dict(Counter(r["disposition"] for r in reviews)),
        "scope": "Every one of the 1,850 native literal leads has an individual lexical evidence disposition. Full entries remain in the immutable original source archive, with per-entry hashes here. Only exact native noun-origin pairs propose new finite nominal forms; existing roles, origin differences and unresolved bases remain explicit. Proposed forms are not yet production coverage.",
        "reviewer": "agent",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    verify_data(report, cases)
    write(REPORT, report)
    verify()


def verify():
    report = read(REPORT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    verify_data(report, read(FIXTURE))
    print(
        "Verified 1,850 individual native reviews and 1,570 additional formation proposals / 15,700 stable structural case IDs."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    freeze() if args.freeze else verify()
