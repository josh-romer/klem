"""Reproduce stable, unjudged alternatives from the frozen excluded-field cohort."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def report():
    path = ROOT / "tests/fixtures/excluded-paradigm-sources.json"
    source = json.loads(path.read_text())
    items, judged = [], 0
    for case in source["cases"]:
        word, judgment = source["before_words"][case["surface"]], case["judgments"][0]
        lemmas = [
            dict(text=t, kind=k)
            for t, k in zip(judgment["lemmas"], judgment["lemma_kinds"], strict=True)
        ]
        morphemes = [
            dict(form=t, kind=k)
            for t, k in zip(
                judgment["morphemes"], judgment["morpheme_kinds"], strict=True
            )
        ]
        for index, analysis in enumerate(word["all"]["analyses"]):
            if analysis["unchanged"]:
                continue
            if analysis["lemmas"] == lemmas and analysis["morphemes"] == morphemes:
                assert judgment["verdict"] == "required"
                judged += 1
                continue
            digest = hashlib.sha256(
                json.dumps(
                    analysis, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                ).encode()
            ).hexdigest()
            items.append(
                dict(
                    id=case["id"] + "/unjudged/" + digest[:24],
                    case_id=case["id"],
                    surface=case["surface"],
                    raw_index=index,
                    analysis=analysis,
                    dictionary_assessment=word["all"]["dictionary"]["readings"][index],
                    filter_membership={
                        mode: analysis in word[mode]["analyses"]
                        for mode in ["headword", "compatible"]
                    },
                    disposition="unjudged_existing_alternative",
                    scope="Existing raw path retained. The named written-form judgment does not "
                    "establish this alternative, its contextual sense, mood, register or lexical membership.",
                )
            )
    assert len({item["id"] for item in items}) == len(items)
    assert (judged, len(items)) == (57, 329)
    return dict(
        schema_version=1,
        checklist="COV-021r",
        generator_source="tools/excluded_paradigm_queue.py",
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        fixture=str(path.relative_to(ROOT)),
        fixture_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        cases=len(source["cases"]),
        required_paths=judged,
        unjudged_existing_alternatives=len(items),
        newly_emitted_paths=0,
        items=items,
        limitation="These are word-level existing candidates, not new discovery misses, contextual "
        "false positives or added grammar paths. Original source/gold and previous judgment scope remain unchanged.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = report()
    if args.verify:
        assert current == json.loads(
            (ROOT / "docs/excluded-paradigm-review-queue.json").read_text()
        )
        print(
            "329 individually tracked existing alternatives remain unjudged; stable IDs, indices, assessments and filters verified."
        )
    else:
        print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
