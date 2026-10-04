"""Record finite source-supported pair proposals without rejudging all discoveries.

The table records an author's review of specific complete native groups. Every
other spelling discovery keeps its individual pending status; this is source
preparation, not a claim that the spacing implementation or corpus gold changed.
"""

import argparse
import json

from lexical_nada_audit import MAIN, ROOT, SOURCE, read, sha

REVIEW = ROOT / "docs/lexical-nada-source-review.json"

# noun -> (native noun ID, main-나다 sense, reviewed example entry/sense/group)
# Homonyms are deliberately identified: 경사 is celebration, 상처 is injury,
# 연기 is smoke, 탈 is illness/trouble, and 사고 is accident rather than thought.
PAIRS = {
    "경사": ("30554", "7", "64934", "1", 8),
    "구멍": ("34923", "3", "34923", "1", 2),
    "구역질": ("35687", "20", "66530", "1", 10),
    "몸살": ("54741", "20", "86240", "1", 4),
    "물난리": ("56191", "6", "56191", "1", 8),
    "발표": ("62470", "10", "62210", "10", 10),
    "배탈": ("58720", "20", "60049", "2", 8),
    "산사태": ("61775", "6", "91140", "2", 8),
    "상처": ("62979", "3", "32546", "3", 4),
    "소리": ("62379", "16", "38419", "1", 5),
    "수염": ("64609", "1", "66818", "3", 8),
    "시간": ("62841", "22", "17856", "2", 4),
    "식은땀": ("90744", "18", "82857", "3", 7),
    "신경질": ("66150", "12", "86863", "1", 9),
    "신명": ("65770", "12", "62210", "12", 23),
    "실감": ("14080", "12", "66054", "1", 7),
    "싸움": ("24286", "7", "31376", "1", 4),
    "여드름": ("67696", "1", "75763", "2", 6),
    "연기": ("67478", "17", "79260", "1", 5),
    "윤기": ("71077", "26", "55380", "1", 1),
    "전쟁": ("29551", "7", "76613", "1", 10),
    "짜증": ("71579", "12", "71579", "1", 9),
    "큰일": ("72174", "7", "62210", "7", 15),
    "탄로": ("80290", "10", "80290", "1", 8),
    "탈": ("81494", "20", "23595", "1", 8),
    "털": (
        "71477",
        "1",
        "66234:9561905d42d5f81d23f65e775ec98fd9ab50fa3aa482d38b65f704f347656227",
        "1",
        1,
    ),
    "토막": ("80558", "3", "51578", "1", 1),
    "폼": ("83727", "23", "62210", "23", 7),
    "감칠맛": ("22602", "27", "22602", "2", 6),
    "코피": ("72169", "18", "82629", "1", 9),
    "멀미": ("54969", "20", "86920", "1", 7),
    "사고": ("66370", "7", "84406", "1", 7),
    "교통사고": ("35968", "7", "14121", "1", 9),
    "생각": ("58162", "21", "82137", "6", 8),
    "냄새": ("58180", "16", "18770", "1", 8),
}

GUIDANCE = {
    "thought": {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=327160",
        "answered": "2026-02-05",
        "finding": "Noun + main 나다 and whole 생각나다 can express different omitted-subject structures. Keep both alternatives without deciding the intended subject.",
    },
    "smell": {
        "url": "https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5877&mn_id=217&pageIndex=1",
        "published": "2019-12-06",
        "finding": "The bad-smell compound is a whole word. A modified 냄새 noun phrase can instead precede main 나다. An optional split must not replace the compound or infer a modifier from a single token.",
    },
    "realism": {
        "url": "https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=6573",
        "published": "2019-12-06",
        "finding": "NIKL treats 실감 + 나다 as a phrase with a lexical verb, rather than a compound or adjective-forming suffix.",
    },
    "dictionary_scope": {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=305102",
        "answered": "2024-10-30",
        "finding": "NIKL again uses the separated 실감 phrase and notes that dictionaries may differ in deciding whether an expression is one word. This review follows the pinned native dictionary and records other-dictionary disagreements.",
    },
    "deultong": {
        "url": "https://www.korean.go.kr/common/download.do?c_file_name=2ba9ace9-775f-4325-b849-5944ae5bb4c1_0.pdf&file_path=notice&o_file_name=%ED%91%9C%EC%A4%80%EA%B5%AD%EC%96%B4%EB%8C%80%EC%82%AC%EC%A0%84+2015%EB%85%84+2%EB%B6%84%EA%B8%B0+%EC%88%98%EC%A0%95+%EB%82%B4%EC%9A%A9.pdf",
        "published": "2015-Q2",
        "page": 1,
        "finding": "The standard dictionary added 들통나다 as a whole verb in 2015. Spaced export examples alone do not justify discarding that registered whole-word analysis; this pair remains outside the proposed list pending a construction review.",
    },
}


def generate():
    source = read(SOURCE)
    entries = source["complete_native_entries"]
    main = entries[MAIN]
    senses = {s["id"]: s for s in main["senses"]}
    proposals = []
    reviewed = set()
    for noun, (noun_id, sense_id, example_id, example_sense, group) in sorted(
        PAIRS.items()
    ):
        noun_entry = entries["krdict:" + noun_id]
        assert (noun_entry["headword"], noun_entry["pos"]) == (noun, "명사")
        examples = [
            h
            for h in source["discoveries"]
            if (h["noun"], h["entry"], h["sense"], h["group"])
            == (noun, "krdict:" + example_id, example_sense, group)
        ]
        assert examples, noun
        reviewed.update(h["id"] for h in examples)
        proposals.append(
            {
                "noun": noun,
                "noun_entry": noun_entry["id"],
                "noun_homonym": noun_entry["homonym"],
                "main_entry": MAIN,
                "main_homonym": main["homonym"],
                "main_sense": sense_id,
                "main_sense_definition": senses[sense_id]["definition"],
                "main_sense_complete_groups": senses[sense_id]["examples"],
                "reviewed_native_examples": examples,
                "registered_whole_entries": source["noun_inventory"]
                .get(noun, {})
                .get("registered_whole_entries", []),
                "guidance": {
                    "생각": ["thought"],
                    "냄새": ["smell"],
                    "실감": ["realism", "dictionary_scope"],
                }.get(noun, []),
                "judgment": "author_reviewed_finite_pair_source_license",
                "implementation": "pending",
                "scope": "Optional unchanged noun + lexical main-나다 reading. Native examples license a pair; they do not certify every ending, homonym, sense or sentence interpretation. Registered whole words and original raw paths remain separate alternatives.",
                "independent_review": "pending",
            }
        )
    assert len(proposals) == 35
    return {
        "schema_version": 1,
        "checklist": "COV-020r",
        "source_sha256": sha(SOURCE),
        "reviewed": "2026-10-04",
        "primary_guidance": GUIDANCE,
        "sense_inventory": [
            {
                "id": s["id"],
                "definition": s["definition"],
                "patterns": s["patterns"],
                "complete_example_groups": len(s["examples"]),
            }
            for s in main["senses"]
        ],
        "finite_pair_proposals": proposals,
        "individual_discovery_review": [
            {
                "id": h["id"],
                "noun": h["noun"],
                "right": h["right"],
                "listed_cohort": h["listed_cohort"],
                "disposition": "reviewed_native_bare_pair_example"
                if h["id"] in reviewed
                else "pending_source_context_review",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
            for h in source["discoveries"]
        ],
        "original_accident_case_ids": [
            r["id"] for r in source["original_accident_reviews"]
        ],
        "remaining": [
            "Implement the finite pairs with exact native identities and main-verb role; auxiliary 나다 cannot supply the right identity.",
            "Keep original raw candidates, registered whole words, existing case-phrase and four-pair spacing priority, shared bounds, cache behavior and explicit truncation.",
            "Add individual required/forbidden regressions, NFC/NFD UTF-8 spans, filter/CLI/API/browser checks and full before/after corpus observations.",
            "Review every other listed and broad discovery individually; current main-나다 morphology or a known noun is not a contextual verdict.",
            "Review other registered whole-word construction alternatives and dictionary conflicts; this is not an arbitrary-compound or contextual-ranking rule.",
        ],
        "independent_review": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    result = generate()
    if args.verify:
        assert json.loads(REVIEW.read_text()) == result
    else:
        with REVIEW.open("x") as file:
            json.dump(result, file, ensure_ascii=False, indent=2)
            file.write("\n")
    print(
        f"35 finite pair source proposals; {len(result['individual_discovery_review'])} individual discoveries retained"
    )


if __name__ == "__main__":
    main()
