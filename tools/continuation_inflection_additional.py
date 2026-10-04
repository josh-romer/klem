"""Preserve missing lexical owners and original guide-example diagnostics.

The original source freeze is immutable. This explicitly attributed supplement
provides every known headword behind its before observations for offline parity.
"""

import argparse
import copy
import json
import sqlite3
import subprocess
from pathlib import Path

from continuation_inflection_audit import MODES, ROOT, SOURCE, project_lmf, sha, write

ADDITIONAL = ROOT / "tests/fixtures/continuation-inflection-additional.json"
LMF = ROOT / "tests/fixtures/krdict-continuation-inflection-additional.json"
DIAGNOSTICS = [
    "먹고났어요",
    "먹고나세요",
    "먹고나시다",
    "먹고나시면",
    "먹고나셨으면",
    "먹고났으면",
    "먹고나겠으면",
    "먹고났었다",
    "읽었어버려요",
    "읽겠어버려요",
    "읽어버렸어요",
    "읽어버리겠어요",
    "아프지않고나서",
    "아파버리다",
    "아파내다",
]


def projection(entries):
    result = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in result:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    return result


def freeze(args):
    assert not ADDITIONAL.exists() and not LMF.exists(), (
        "Refusing to replace supplemental evidence"
    )
    original = json.loads(SOURCE.read_text())
    words = {
        s: {
            mode: json.loads(
                subprocess.check_output(
                    [
                        str(args.cli.resolve()),
                        "word",
                        s,
                        "--dictionary",
                        str(args.dictionary.resolve()),
                        *flags,
                    ]
                )
            )
            for mode, flags in MODES.items()
        }
        for s in DIAGNOSTICS
    }
    ids = {
        e["id"]
        for w in [*original["before_words"].values(), *words.values()]
        for l in w["all"]["dictionary"]["lemmas"]
        for e in l["entries"]
    }
    ids -= original["complete_native_entries"].keys()
    with sqlite3.connect(
        args.dictionary.resolve().as_uri() + "?mode=ro", uri=True
    ) as db:
        entries = {
            i: json.loads(
                db.execute("select data from entries where id=?", (i,)).fetchone()[0]
            )
            for i in sorted(ids)
        }
    raw, hashes = project_lmf(entries)
    write(
        LMF,
        {
            "LexicalResource": {
                "Lexicon": {"LexicalEntry": [raw[i] for i in sorted(raw)]}
            }
        },
    )
    write(
        ADDITIONAL,
        {
            "schema_version": 1,
            "checklist": "COV-019ae",
            "original_source_sha256": sha(SOURCE),
            "lmf_sha256": sha(LMF),
            "raw_source_sha256": hashes,
            "cli": str(args.cli),
            "cli_sha256": sha(args.cli),
            "dictionary_sha256": sha(args.dictionary),
            "complete_native_entries": entries,
            "source_entries": projection(entries),
            "before_words": words,
            "scope": "Every known entry behind the original and supplemental before words; added guide-example spellings are separate diagnostics, not repairs of any input.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    verify()


def verify():
    original = json.loads(SOURCE.read_text())
    extra = json.loads(ADDITIONAL.read_text())
    assert extra["original_source_sha256"] == sha(SOURCE)
    assert extra["lmf_sha256"] == sha(LMF)
    assert extra["cli_sha256"] == original["cli_sha256"]
    assert extra["dictionary_sha256"] == original["dictionary_sha256"]
    assert extra["source_entries"] == projection(extra["complete_native_entries"])
    assert (
        not extra["complete_native_entries"].keys()
        & original["complete_native_entries"].keys()
    )
    assert set(extra["before_words"]) == set(DIAGNOSTICS)
    known = (
        original["complete_native_entries"].keys()
        | extra["complete_native_entries"].keys()
    )
    for w in [*original["before_words"].values(), *extra["before_words"].values()]:
        for lemma in w["all"]["dictionary"]["lemmas"]:
            assert all(e["id"] in known for e in lemma["entries"])
    assert (
        extra["contextual_verdict"] == "unjudged"
        and extra["independent_review"] == "pending"
    )
    print(
        f"{len(extra['source_entries'])} supplemental complete native entries and {len(DIAGNOSTICS)} original diagnostic words verified"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    args = p.parse_args()
    if args.verify:
        verify()
    elif args.cli and args.dictionary:
        freeze(args)
    else:
        p.error("freeze requires --cli and --dictionary")
