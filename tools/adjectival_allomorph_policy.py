"""Archive and correct eight older dictionary-policy canonical aliases.

Use the pinned pre-change CLI even when the working parser has changed. Preserve
the original policy ledger, native sources and all three original filter modes.
"""

import argparse
import copy
import json
from pathlib import Path

from adjectival_allomorph_audit import OWNERS, SOURCE, coda
from lexical_nada_audit import ROOT, load_dictionary, read, run, sha, write

POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
PREFLIGHT = ROOT / "docs/adjectival-allomorph-policy-preflight.json.gz"
CORRECTIONS = ROOT / "tests/fixtures/adjectival-allomorph-policy-corrections.json"


def proposals(ledger):
    result = []
    for case in ledger["cases"]:
        for judgment in case["judgments"]:
            if judgment["verdict"] != "required" or not any(
                f in OWNERS for f in judgment.get("morphemes") or []
            ):
                continue
            head = judgment["lemmas"][-1]
            if not head.endswith("다") or coda(head.removesuffix("다")) not in {0, 8}:
                continue
            assert "답다" not in judgment["morphemes"]
            replacement = copy.deepcopy(case)
            target = next(
                j for j in replacement["judgments"] if j["id"] == judgment["id"]
            )
            canonical = next(f for f in judgment["morphemes"] if f in OWNERS)
            target.update(
                verdict="forbidden",
                reason=f"Explicit archived policy correction: -{canonical} requires a non-ㄹ closed underlying owner; {head} has an open or ㄹ stem. The general -{canonical[1:]} reading retains the intended dictionary-role test. Lexical POS evidence does not license this incorrect canonical allomorph.",
            )
            result.append(
                {
                    "original": case,
                    "replacement": replacement,
                    "original_source_url": ledger["sources"][judgment["source"]],
                    "canonical_owner": f"krdict:{OWNERS[canonical][0]}",
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    return result


def freeze(cli, dictionary):
    assert not PREFLIGHT.exists() and not CORRECTIONS.exists()
    source = read(SOURCE)
    assert (
        sha(cli) == source["cli_sha256"]
        and sha(dictionary) == source["dictionary_sha256"]
    )
    original = read(POLICY)
    changes = proposals(original)
    assert len(changes) == 8
    text, streams = run(
        cli, dictionary, sorted({r["original"]["surface"] for r in changes})
    )
    native = load_dictionary(dictionary)
    identifiers = {r["canonical_owner"] for r in changes}

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and value["id"].startswith("krdict:"):
                identifiers.add(value["id"])
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)

    visit(streams)
    archive = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "before_cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "original_policy_sha256": sha(POLICY),
        "original_policy": original,
        "complete_native_entries": {i: native[i] for i in sorted(identifiers)},
        "before_input": text,
        "before_streams": streams,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(PREFLIGHT, archive)
    CORRECTIONS.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "preflight_sha256": sha(PREFLIGHT),
                "superseded": changes,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify(dictionary=None, cli=None):
    archive, changes = read(PREFLIGHT), read(CORRECTIONS)
    assert archive["source_sha256"] == sha(SOURCE)
    assert changes["preflight_sha256"] == sha(PREFLIGHT)
    assert changes["superseded"] == proposals(archive["original_policy"])
    assert len(changes["superseded"]) == 8
    indexed = {c["id"]: c for c in read(POLICY)["cases"]}
    for change in changes["superseded"]:
        assert indexed[change["replacement"]["id"]] == change["replacement"]
    if dictionary:
        assert sha(dictionary) == archive["dictionary_sha256"]
        native = load_dictionary(dictionary)
        assert all(
            native[i] == e for i, e in archive["complete_native_entries"].items()
        )
    if cli:
        assert dictionary and sha(cli) == archive["before_cli_sha256"]
        text, streams = run(
            cli,
            dictionary,
            sorted({r["original"]["surface"] for r in changes["superseded"]}),
        )
        assert text == archive["before_input"] and streams == archive["before_streams"]
    print(
        "Verified eight explicit dictionary-policy corrections against the archived original policy and pinned pre-change CLI."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli-before", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.freeze:
        assert args.cli_before and args.dictionary
        freeze(args.cli_before, args.dictionary)
    elif args.verify:
        verify(args.dictionary, args.cli_before)
    else:
        parser.error("choose --freeze or --verify")
