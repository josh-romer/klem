"""Track each native discovery separately from finite attachment judgments."""

import argparse
import collections
import gzip
import hashlib
import json

from continuation_inflection_additional import ADDITIONAL
from continuation_inflection_audit import (
    DISCOVERY,
    ROOT,
    SOURCE,
    classification,
    sha,
    write,
)

REVIEW = ROOT / "docs/continuation-inflection-source-review.json"
QUEUE = ROOT / "docs/continuation-inflection-source-queue.json.gz"
JUDGMENTS = ROOT / "tests/fixtures/continuation-inflection-judgments.json"


def disposition(kind, index, hit):
    if kind == "eo_oda_adjectives":
        if index in {0, 10, 15, 49, 51}:
            return "other_o_word_not_established_as_auxiliary"
        if index == 8:
            return "separate_clause_main_oda_alternative_requires_context"
        if index == 5:
            return "lexical_growth_verb_kkeuda_alternative"
        if index in {23, 30, 46, 56}:
            return "native_future_balka_oda_counterevidence"
        return "native_adjective_change_oda_evidence"
    if kind == "go_nada_spaced":
        return "broad_na_spelling_discovery_requires_individual_lexical_review"
    return classification(kind, hit)


def queue():
    with gzip.open(DISCOVERY, "rt") as file:
        discoveries = json.load(file)
    result = []
    for kind, hits in discoveries["hits"].items():
        for index, hit in enumerate(hits):
            identity = json.dumps([kind, hit], ensure_ascii=False, sort_keys=True)
            result.append(
                {
                    "id": "continuation-inflection-discovery-"
                    + hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "pattern": kind,
                    "discovery_index": index,
                    "disposition": disposition(kind, index, hit),
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    return result


def freeze():
    assert not REVIEW.exists() and not QUEUE.exists(), (
        "Refusing to overwrite source review"
    )
    rows = queue()
    QUEUE.write_bytes(
        gzip.compress(
            json.dumps(
                {
                    "schema_version": 1,
                    "checklist": "COV-019ae",
                    "discovery_sha256": sha(DISCOVERY),
                    "scope": "Every original spelling discovery has a stable individual ID. Dispositions distinguish evidence and alternative spellings; they are not contextual gold.",
                    "cases": rows,
                },
                ensure_ascii=False,
                indent=2,
            ).encode(),
            mtime=0,
        )
    )
    source = json.loads(SOURCE.read_text())
    judgments = json.loads(JUDGMENTS.read_text())
    write(
        REVIEW,
        {
            "schema_version": 1,
            "checklist": "COV-019ae",
            "status": "partial_finite_policy_with_preserved_source_tensions",
            "source_sha256": sha(SOURCE),
            "additional_sha256": sha(ADDITIONAL),
            "queue_sha256": sha(QUEUE),
            "judgments_sha256": sha(JUDGMENTS),
            "guide": source["guide"],
            "primary_online_entries": [
                "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=62134",
                "https://krdict.korean.go.kr/jpn/dicSearch/SearchView?ParaWordNo=80110",
            ],
            "rules": [
                {
                    "rule": "continuation_left_tense",
                    "native_entries": ["krdict:62601", "krdict:62134"],
                    "connectors": ["어 버리다", "고 나다"],
                    "printed_pages": [373, 527],
                    "ownership": "Only immediate connector-owner canonical prefinals 었/겠; earlier owners and right-side 어 버리다 tense remain independent.",
                },
                {
                    "rule": "go_nada_honorific",
                    "native_entries": ["krdict:62134"],
                    "connectors": ["고"],
                    "printed_pages": [372, 373],
                    "ownership": "Right-owner canonical 시; left 시 allowed. Other humble honorific forms remain unreviewed.",
                },
                {
                    "rule": "go_nada_future",
                    "native_entries": ["krdict:62134"],
                    "connectors": ["고"],
                    "printed_pages": [373],
                    "ownership": "Right-owner canonical 겠; 어 나다 and unrelated lexical verbs remain independent.",
                },
                {
                    "rule": "go_nada_final_ending",
                    "native_entries": ["krdict:62134"],
                    "connectors": ["고"],
                    "printed_pages": [372],
                    "ownership": "Canonical finite 는다/어요/으세요 and the alternate 어 + polite 요 path. Bare citation 다, plain connective 어 and other final forms are not newly adjudicated.",
                },
            ],
            "source_tensions": [
                {
                    "id": "continuation-inflection-right-past-tension",
                    "guide_printed_page": 373,
                    "native_examples": 17,
                    "policy": "Unknown for right-owner 었 on native 고 나다; a separately known honorific/future/final-ending conflict still takes precedence.",
                    "counterexample_disposition": "native_retrospective_go_nada_counterevidence",
                },
                {
                    "id": "continuation-inflection-apheuda-class-tension",
                    "guide_printed_page": 373,
                    "native_parent_entries": ["krdict:91874", "krdict:601155"],
                    "lexical_entry": "krdict:62239",
                    "auxiliary_entry": "krdict:62134",
                    "policy": "Unknown for this native adjective directly before native 고 나다. Preserve adjective POS, all original translations, existing conflicts and separate homonyms. No inheritance across a negative, suffix or other auxiliary.",
                },
                {
                    "id": "continuation-inflection-oda-time-and-class-tension",
                    "guide_printed_page": 544,
                    "native_auxiliary": "krdict:69517",
                    "policy": "No blanket adjective or future ban. Complete examples distinguish adjective changes, verbal growth 커 온, false 오-word spelling hits, possible separate main-verb clauses and future 밝아 올/닥쳐올. Sense and time reference need context.",
                },
            ],
            "discoveries": {
                "total": len(rows),
                "per_disposition": dict(
                    collections.Counter(r["disposition"] for r in rows)
                ),
                "spelling_hits_are_not_gold": True,
            },
            "authored_policy_cases": len(judgments["cases"]),
            "contextual_judgments": 0,
            "original_evidence": "Original four preflight outputs, raw validity, corpus annotations and COV-019ad policy judgments are retained byte for byte. New finite policy cases are separate.",
            "remaining": [
                "Other final endings, humble prefinals, noncanonical contractions and register need individual source review.",
                "All 2,010 broad spaced 고 나… discoveries remain individually queued; no automatic auxiliary interpretation.",
                "아프다/right-past guide versus dictionary tension requires independent Korean-language review; Unknown is not a grammatical license.",
                "오다 lexical combinations and temporal/guess/directional senses require context and individual entries.",
                "Eight accident-noun/main-나다 alternatives expose the separately tracked COV-020r spacing gap.",
                "Full streams, corpus evaluation and packaged CLI/API/browser checks must verify this policy before release.",
            ],
            "independent_review": "pending",
        },
    )
    verify()


def verify():
    review = json.loads(REVIEW.read_text())
    with gzip.open(QUEUE, "rt") as file:
        saved = json.load(file)
    assert review["source_sha256"] == sha(SOURCE)
    assert review["additional_sha256"] == sha(ADDITIONAL)
    assert review["queue_sha256"] == sha(QUEUE)
    assert review["judgments_sha256"] == sha(JUDGMENTS)
    assert saved["discovery_sha256"] == sha(DISCOVERY)
    assert saved["cases"] == queue()
    assert len(saved["cases"]) == len({r["id"] for r in saved["cases"]}) == 2122
    original = json.loads(SOURCE.read_text())
    assert {r["id"] for r in original["individual_reviews"]} <= {
        r["id"] for r in saved["cases"]
    }
    assert (
        review["contextual_judgments"] == 0
        and review["independent_review"] == "pending"
    )
    cases = json.loads(JUDGMENTS.read_text())["cases"]
    assert review["authored_policy_cases"] == len(cases) == 34
    assert len({c["id"] for c in cases}) == 34
    assert all(
        c["contextual_verdict"] == "unjudged" and c["independent_review"] == "pending"
        for c in cases
    )
    print(
        "2,122 individually tracked source discoveries, 34 finite policy cases and three unresolved source tensions verified"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        freeze()
