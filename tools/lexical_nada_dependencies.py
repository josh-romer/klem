"""Freeze the native -랴/-으랴 dependency and genuine stress-prefix entries.

The required 연기 나랴 source case exposed an existing ending gap. Preserve its
four ending entries and pre-change words separately, without replacing the
original 389-word freeze or the 109 spacing judgments.
"""

import argparse
import json
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, SOURCE, load_dictionary, read, sha
from native_lmf import verify_native_lmf

DEPENDENCY = ROOT / "tests/fixtures/lexical-nada-dependencies.json"
LMF = ROOT / "tests/fixtures/krdict-lexical-nada-dependencies.json"
ENDING_IDS = ["krdict:79260", "krdict:79261", "krdict:80306", "krdict:80308"]
PREFIX_IDS = ["krdict:27833", "krdict:50559", "krdict:86264", "krdict:90912"]
REQUIRED = {
    "나랴": ("나다", []),
    "하랴": ("하다", []),
    "먹으랴": ("먹다", []),
    "받으랴": ("받다", []),
    "살랴": ("살다", []),
    "놀랴": ("놀다", []),
    "들으랴": ("듣다", []),
    "도우랴": ("돕다", []),
    "지으랴": ("짓다", []),
    "좋으랴": ("좋다", []),
    "아니랴": ("아니다", []),
    "나시랴": ("나다", ["시"]),
    "났으랴": ("나다", ["었"]),
    "나겠으랴": ("나다", ["겠"]),
    "학생이랴": ("이다", []),
}


def freeze(args):
    assert not DEPENDENCY.exists() and not LMF.exists(), (
        "Refusing to replace original dependency evidence"
    )
    source = read(SOURCE)
    assert sha(args.cli_before) == source["cli_sha256"]
    assert sha(args.dictionary) == source["dictionary_sha256"]
    native = load_dictionary(args.dictionary)
    entries = {i: native[i] for i in sorted(ENDING_IDS + PREFIX_IDS)}
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    before = {
        word: json.loads(
            subprocess.check_output(
                [
                    str(args.cli_before.resolve()),
                    "word",
                    word,
                    "--dictionary",
                    str(args.dictionary.resolve()),
                ]
            )
        )
        for word in REQUIRED
    }
    value = {
        "schema_version": 1,
        "checklist": "COV-020r / COV-017br",
        "source_sha256": sha(SOURCE),
        "cli_sha256": sha(args.cli_before),
        "dictionary_sha256": sha(args.dictionary),
        "lmf_sha256": sha(LMF),
        "raw_source_sha256": hashes,
        "complete_native_entries": entries,
        "ending_ids": ENDING_IDS,
        "prefix_ids": PREFIX_IDS,
        "before_words": before,
        "required_ending_cases": [
            {"surface": word, "lemma": head, "prefinals": prefinals, "ending": "으랴"}
            for word, (head, prefinals) in REQUIRED.items()
        ],
        "original_raw_change_surfaces": ["나랴", "연기나랴"],
        "source_license": source["license"],
        "scope": "Complete four native ending entries preserve rhetorical, offer and enumerative senses. Normalize the two surface allomorphs together without selecting a contextual sense; broad register, other particles and novel/corpus candidate changes require separate review. Four genuine prefix entries supply the alternative partitions required by the engineering stress test.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    DEPENDENCY.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def verify():
    value = read(DEPENDENCY)
    assert value["source_sha256"] == sha(SOURCE)
    assert value["lmf_sha256"] == sha(LMF)
    assert value["ending_ids"] == ENDING_IDS and value["prefix_ids"] == PREFIX_IDS
    assert value["required_ending_cases"] == [
        {"surface": word, "lemma": head, "prefinals": prefinals, "ending": "으랴"}
        for word, (head, prefinals) in REQUIRED.items()
    ]
    entries = value["complete_native_entries"]
    assert set(entries) == set(ENDING_IDS + PREFIX_IDS)
    for i in ENDING_IDS:
        assert entries[i]["pos"] == "어미"
        assert entries[i]["headword"] in ["-랴", "-으랴"]
    verify_native_lmf(read(LMF), entries)
    assert set(value["before_words"]) == set(REQUIRED)
    assert value["original_raw_change_surfaces"] == ["나랴", "연기나랴"]
    print(
        "Four full native ending entries, four genuine prefix entries and 15 original dependency words verified"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli-before", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli_before and args.dictionary:
        freeze(args)
        verify()
    else:
        parser.error("freeze requires --cli-before and --dictionary")


if __name__ == "__main__":
    main()
