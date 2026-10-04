"""Track every candidate removal in the pinned 314-word regression cohort.

Rust's ordered-owner regression independently permits exactly these 703 raw
removals. This checkpoint preserves each original reading and native lemma slot
in all three filters; broader native/novel/spacing streams remain separate work.
"""

import argparse
import json
from pathlib import Path

from adjectival_allomorph_audit import DERIVED, FIXTURE, OWNERS, SOURCE
from adjectival_allomorph_corrections import CORRECTIONS
from lexical_nada_audit import ROOT, digest, read, run, sha, write

REPORT = ROOT / "docs/adjectival-allomorph-checkpoint.json.gz"


def baseline():
    source, supplement = read(SOURCE), read(DERIVED)
    selected = set(read(FIXTURE)["before_words"]) | {
        r["surface"] for r in supplement["additional_proposals"]
    }
    streams = {}
    for mode, records in source["before_streams"].items():
        words = {
            r["surface"]: r
            for r in records
            if r["kind"] == "word" and r["surface"] in selected
        }
        for record in supplement["before_streams"][mode]:
            if record["kind"] == "word":
                assert record["surface"] not in words
                words[record["surface"]] = record
        assert set(words) == selected and len(words) == 314
        streams[mode] = words
    return source, streams


def compare(source, streams, actual):
    changes = {}
    kept = 0
    for mode, words in streams.items():
        for surface, before in words.items():
            after = actual[mode][surface]
            assert before["analysis"]["normalized"] == after["analysis"]["normalized"]
            old, new = before["analysis"]["analyses"], after["analysis"]["analyses"]
            assert new == [a for a in old if a in new], (
                mode,
                surface,
                "addition or reordered candidate",
            )
            assert len(before["dictionary"]["readings"]) == len(old)
            assert len(after["dictionary"]["readings"]) == len(new)
            assert {
                k: v
                for k, v in before["dictionary"].items()
                if k not in {"readings", "lemmas"}
            } == {
                k: v
                for k, v in after["dictionary"].items()
                if k not in {"readings", "lemmas"}
            }
            referenced = {digest(l) for a in new for l in a["lemmas"]}
            assert after["dictionary"]["lemmas"] == [
                s
                for s in before["dictionary"]["lemmas"]
                if digest(s["lemma"]) in referenced
            ]
            for index, analysis in enumerate(old):
                reading = before["dictionary"]["readings"][index]
                if analysis in new:
                    kept += 1
                    assert (
                        after["dictionary"]["readings"][new.index(analysis)] == reading
                    ), (mode, surface, "retained assessment changed")
                    continue
                forms = {
                    m["form"]
                    for m in analysis["morphemes"]
                    if m["kind"] == "ending" and m["form"] in OWNERS
                }
                assert forms, (mode, surface, "unrelated removal")
                key = [surface, analysis, reading]
                ident = "adjectival-allomorph-removal-" + digest(key)[:24]
                if ident not in changes:
                    changes[ident] = {
                        "id": ident,
                        "surface": surface,
                        "before": {"analysis": analysis, "reading": reading},
                        "after": None,
                        "canonical_sources": {
                            f: [f"krdict:{i}" for i in OWNERS[f]] for f in sorted(forms)
                        },
                        "review_basis": "tests/adjectival_allomorphs.rs::every_prior_path_changes_only_for_its_ordered_open_or_rieul_owner; tools/adjectival_allomorph.rs::reviewed_removal",
                        "occurrences": [],
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                changes[ident]["occurrences"].append(
                    {
                        "mode": mode,
                        "before_span": before["span"],
                        "before_analysis_index": index,
                    }
                )
    ordered = sorted(changes.values(), key=lambda r: r["id"])
    assert (
        sum(any(o["mode"] == "all" for o in r["occurrences"]) for r in ordered) == 703
    )
    return {
        "scope": "314 frozen matrix/original-ledger/supplement words; complete candidate and dictionary fields in three filters. Spacing and broader eight-stream/corpus/package evidence remain outside this checkpoint.",
        "retained_candidate_occurrences": kept,
        "removals_by_filter": {
            mode: sum(o["mode"] == mode for r in ordered for o in r["occurrences"])
            for mode in streams
        },
        "changes": ordered,
        "after_words": {
            mode: {
                s: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
                for s, r in words.items()
            }
            for mode, words in actual.items()
        },
    }


def freeze(cli, dictionary, output):
    source, streams = baseline()
    assert sha(dictionary) == source["dictionary_sha256"] and not output.exists()
    _, records = run(cli, dictionary, sorted(streams["all"]))
    actual = {
        mode: {r["surface"]: r for r in rows if r["kind"] == "word"}
        for mode, rows in records.items()
    }
    report = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "derived_sha256": sha(DERIVED),
        "corrections_sha256": sha(CORRECTIONS),
        "ordered_owner_verifier_sha256": sha(ROOT / "tools/adjectival_allomorph.rs"),
        "regression_test_sha256": sha(ROOT / "tests/adjectival_allomorphs.rs"),
        "before_cli_sha256": source["cli_sha256"],
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
        **compare(source, streams, actual),
    }
    write(output, report)
    print(
        json.dumps(
            {
                "words": 314,
                "removals": report["removals_by_filter"],
                "retained": report["retained_candidate_occurrences"],
            }
        )
    )


def verify():
    report = read(REPORT)
    source, streams = baseline()
    assert report["source_sha256"] == sha(SOURCE) and report["derived_sha256"] == sha(
        DERIVED
    )
    assert report["corrections_sha256"] == sha(CORRECTIONS)
    assert report["ordered_owner_verifier_sha256"] == sha(
        ROOT / "tools/adjectival_allomorph.rs"
    )
    assert report["regression_test_sha256"] == sha(
        ROOT / "tests/adjectival_allomorphs.rs"
    )
    assert (
        report["before_cli_sha256"] == source["cli_sha256"]
        and report["dictionary_sha256"] == source["dictionary_sha256"]
    )
    actual = {
        mode: {s: {"surface": s, **word} for s, word in words.items()}
        for mode, words in report["after_words"].items()
    }
    expected = compare(source, streams, actual)
    assert all(report[k] == v for k, v in expected.items())
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        "Verified 314-word checkpoint, 703 individually tracked raw removals and all retained candidate/native fields; broader stream/corpus/package comparisons remain open."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli and args.dictionary and args.output:
        freeze(args.cli.resolve(), args.dictionary.resolve(), args.output)
    else:
        parser.error("generate with --cli, --dictionary and --output, or use --verify")
