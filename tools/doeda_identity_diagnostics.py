"""Verify identity evidence additions without replacing earlier lexical fields.

Every original candidate, grammar assessment, native entry and filter choice
must survive. Only sourced origin payloads and separately typed identity
relations may be added to the frozen records.
"""

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_identity_audit import FIXTURE
from doeda_identity_audit import REPORT as PREFLIGHT
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-identity-diagnostics.json.gz"


def inspect_record(before, after, heads, entries):
    """Compare one frozen record, requiring evidence on each owned noun reading.

    This cohort has the nominal base at lemma 0 and its owned suffix at
    morpheme 0. Later copulas and auxiliaries must never borrow that evidence.
    """
    stripped = copy.deepcopy(after)
    seen = set()
    if after["kind"] == "word":
        annotation = after["dictionary"]
        old_slots = {
            (s["lemma"]["text"], s["lemma"]["kind"]): s
            for s in before["dictionary"]["lemmas"]
        }
        sourced_bases = set()
        for i, (reading, stripped_reading) in enumerate(
            zip(annotation["readings"], stripped["dictionary"]["readings"], strict=True)
        ):
            analysis = after["analysis"]["analyses"][i]
            first = analysis["lemmas"][0]
            owned = (
                first["kind"] == "nominal"
                and first["text"] in heads
                and "suffix.verb.doeda" in analysis["rules"]
                and analysis["morphemes"][0] == {"form": "되다", "kind": "suffix"}
            )
            head = heads[first["text"]] if owned else None
            if owned:
                sourced_bases.add(first["text"])
            for lemma, copy_lemma in zip(
                reading["lemmas"], stripped_reading["lemmas"], strict=True
            ):
                for entry, copy_entry in zip(
                    lemma["entries"], copy_lemma["entries"], strict=True
                ):
                    expected_entry = (
                        next(
                            (
                                e
                                for e in head["base_entries"]
                                if e["entry_id"] == entry["id"]
                            ),
                            None,
                        )
                        if owned and lemma["lemma_index"] == 0
                        else None
                    )
                    if expected_entry is None:
                        assert "derivational_identity" not in entry
                        continue
                    assert entry.get("derivational_identity") == {
                        "relation": expected_entry["relation"],
                        "morpheme_index": 0,
                        "expected_origins": head["expected_origins"],
                        "whole_entries": head["whole_entries"],
                        "whole_origins_complete": head["whole_origins_complete"],
                    }
                    seen.add((head["id"], expected_entry["id"]))
                    del copy_entry["derivational_identity"]
        for slot, copy_slot in zip(
            annotation["lemmas"], stripped["dictionary"]["lemmas"], strict=True
        ):
            key = (slot["lemma"]["text"], slot["lemma"]["kind"])
            old = old_slots[key]
            for entry, copy_entry, old_entry in zip(
                slot["entries"], copy_slot["entries"], old["entries"], strict=True
            ):
                if (
                    key[0] in sourced_bases
                    and key[1] == "nominal"
                    and entry["pos"] == "명사"
                ):
                    assert entry.get("origins") == entries[entry["id"]]["origins"]
                if "origins" in entry and "origins" not in old_entry:
                    assert key[0] in sourced_bases and key[1] == "nominal"
                    assert entry["pos"] == "명사"
                    assert entry.get("origins") == entries[entry["id"]]["origins"]
                    del copy_entry["origins"]
    assert stripped == before, "unrelated original field changed"
    return seen


def inspect(report, source, fixture):
    heads = {h["base"]: h for h in fixture["heads"]}
    entries = source["complete_native_entries"]
    seen = set()
    comparisons = []
    assert set(report["after_streams"]) == set(source["before_streams"])
    for mode, current in report["after_streams"].items():
        before = source["before_streams"][mode]
        assert len(before) == len(current)
        changed = 0
        for ordinal, (b, a) in enumerate(zip(before, current, strict=True)):
            try:
                seen.update(inspect_record(b, a, heads, entries))
            except AssertionError as error:
                raise AssertionError((mode, ordinal, a["surface"])) from error
            changed += b != a
        comparisons.append(
            {"mode": mode, "records": len(current), "changed_records": changed}
        )
    assert seen == {
        (h["id"], e["id"]) for h in fixture["heads"] for e in h["base_entries"]
    }
    assert report["comparisons"] == comparisons
    return comparisons


def freeze(args):
    assert not REPORT.exists()
    source, fixture = read(PREFLIGHT), read(FIXTURE)
    assert sha(args.dictionary) == source["dictionary_sha256"]
    streams, comparisons = {}, []
    for mode, flags in (
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        out = subprocess.run(
            [str(args.cli), "text", "-", "--dictionary", str(args.dictionary), *flags],
            input=source["before_input"],
            text=True,
            capture_output=True,
            check=True,
        )
        rows = [json.loads(line) for line in out.stdout.splitlines()]
        streams[mode] = rows
        comparisons.append(
            {
                "mode": mode,
                "records": len(rows),
                "changed_records": sum(
                    b != a
                    for b, a in zip(source["before_streams"][mode], rows, strict=True)
                ),
            }
        )
    paths = (
        "src/lib.rs",
        "src/doeda_identity.rs",
        "src/dictionary.rs",
        "src/dictionary/attachment.rs",
        "web/src/model.ts",
        "web/src/breakdown.ts",
    )
    report = {
        "schema_version": 1,
        "preflight_sha256": sha(PREFLIGHT),
        "fixture_sha256": sha(FIXTURE),
        "before_cli_sha256": source["cli_sha256"],
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "after_streams": streams,
        "comparisons": comparisons,
        "implementation_files": {
            p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)} for p in paths
        },
        "scope": "All original records across three filters. Raw analyses, grammar assessments, entry/POS values, slots and relative order remain exact; only finite source origin/identity payloads are added. This debug checkpoint does not establish release/browser, broad/corpus/performance or contextual coverage.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    print(inspect(report, source, fixture), flush=True)
    write(REPORT, report)


def verify():
    report, source, fixture = read(REPORT), read(PREFLIGHT), read(FIXTURE)
    assert report["schema_version"] == 1
    assert report["preflight_sha256"] == sha(PREFLIGHT) and report[
        "fixture_sha256"
    ] == sha(FIXTURE)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    for snap in report["implementation_files"].values():
        assert hashlib.sha256(snap["text"].encode()).hexdigest() == snap["sha256"]
    print(inspect(report, source, fixture))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    args = p.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary
        freeze(args)
