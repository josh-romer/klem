"""Freeze recorded noun/whole-head origin relationships before adding hints.

These relations are lexical evidence, not bans on productive derivation or
contextual sense judgments. Both matching entries and all origin-difference
leads remain individually visible; absent origins are inconclusive.
"""

import argparse
import hashlib
import json
import subprocess
from collections import defaultdict
from pathlib import Path

from doeda_native_audit import FIXTURE as NATIVE
from doeda_native_package import REPORT as PACKAGE
from doeda_native_performance import REPORT as PERFORMANCE
from doeda_native_preflight import REPORT as SOURCE
from doeda_suffix_regressions import effective_formations
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-identity-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-identity-sources.json"


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def relationships(source):
    entries = source["complete_native_entries"]
    by_head = defaultdict(list)
    for entry in entries.values():
        by_head[entry["headword"]].append(entry)
    result = []
    formations = [*effective_formations(), *read(NATIVE)["formations"]]
    for formation in sorted(formations, key=lambda f: f["head"]):
        if formation["base_kind"] != "nominal":
            continue
        pos = {"verb": "동사", "adjective": "형용사"}[formation["predicate_class"]]
        whole = sorted(
            (e for e in by_head[formation["head"]] if e["pos"] == pos),
            key=lambda e: e["id"],
        )
        origins = sorted(
            {o[:-2] for e in whole for o in e["origins"] if o.endswith("되다")}
        )
        complete = bool(whole) and all(
            any(o.endswith("되다") for o in e["origins"]) for e in whole
        )
        bases = sorted(
            (e for e in by_head[formation["base"]] if e["pos"] == "명사"),
            key=lambda e: e["id"],
        )
        different = [
            e
            for e in bases
            if origins and e["origins"] and not set(origins) & set(e["origins"])
        ]
        if not different:
            continue
        rows = []
        for entry in bases:
            shared = sorted(set(origins) & set(entry["origins"]))
            relation = (
                "recorded_match"
                if shared
                else "recorded_difference"
                if complete and entry["origins"]
                else "unknown"
            )
            rows.append(
                {
                    "id": "doeda-identity-entry-"
                    + digest([formation["head"], entry["id"]])[:24],
                    "entry_id": entry["id"],
                    "entry_sha256": digest(entry),
                    "recorded_origins": entry["origins"],
                    "shared_origins": shared,
                    "relation": relation,
                    "interpretation": "Recorded source relationship only. Different origins do not prove that another productive derivation is ungrammatical; contextual sense selection and independent review remain pending.",
                }
            )
        result.append(
            {
                "id": "doeda-identity-head-" + digest(formation["head"])[:24],
                "head": formation["head"],
                "base": formation["base"],
                "predicate_class": formation["predicate_class"],
                "whole_entries": [e["id"] for e in whole],
                "whole_entry_sha256": {e["id"]: digest(e) for e in whole},
                "expected_origins": origins,
                "whole_origins_complete": complete,
                "base_entries": rows,
            }
        )
    assert len(result) == 192
    assert (
        sum(
            e["relation"] == "recorded_difference"
            for r in result
            for e in r["base_entries"]
        )
        == 232
    )
    assert all(r["predicate_class"] == "verb" for r in result)
    return result


def fixture(source):
    return {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "native_fixture_sha256": sha(NATIVE),
        "heads": relationships(source),
        "variants": read(NATIVE)["variants"],
        "scope": "All 232 recorded origin-difference pairs across 192 implemented nominal/verb heads, plus every noun alternative at those bases. Relationship evidence is independent of POS/grammar compatibility and selects no contextual sense.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }


def cohort(data):
    return sorted(
        {
            word
            for f in data["heads"]
            for word in [
                f["base"],
                f["base"] + "은",
                *[f["base"] + v["tail"] for v in data["variants"]],
            ]
        }
    )


def inspect(report, data):
    source = read(SOURCE)
    assert data == fixture(source)
    assert report["schema_version"] == 1
    assert report["source_sha256"] == sha(SOURCE)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["package_sha256"] == sha(PACKAGE)
    assert report["cli_sha256"] == read(PERFORMANCE)["cli_sha256"]
    text = "\n".join(cohort(data)) + "\n"
    assert report["before_input"] == text
    assert set(report["before_streams"]) == {"raw", "headword", "compatible"}
    for stream in report["before_streams"].values():
        assert len(stream) == 2 * len(cohort(data))
        assert "".join(r["surface"] for r in stream) == text
    ids = {
        i
        for r in data["heads"]
        for i in [*r["whole_entries"], *[e["entry_id"] for e in r["base_entries"]]]
    }
    assert report["complete_native_entries"] == {
        i: source["complete_native_entries"][i] for i in sorted(ids)
    }
    for snapshot in report["implementation_files"].values():
        assert (
            hashlib.sha256(snapshot["text"].encode()).hexdigest() == snapshot["sha256"]
        )
    print(
        len(data["heads"]),
        "heads / 232 difference leads /",
        len(cohort(data)),
        "original words verified",
        flush=True,
    )


def freeze(args):
    assert not REPORT.exists() and not FIXTURE.exists()
    source, perf = read(SOURCE), read(PERFORMANCE)
    assert perf["package_sha256"] == sha(PACKAGE)
    assert sha(args.cli) == perf["cli_sha256"]
    assert sha(args.dictionary) == source["dictionary_sha256"]
    data = fixture(source)
    FIXTURE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    text = "\n".join(cohort(data)) + "\n"
    streams = {}
    for mode, flags in (
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        output = subprocess.run(
            [str(args.cli), "text", "-", "--dictionary", str(args.dictionary), *flags],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        streams[mode] = [json.loads(line) for line in output.stdout.splitlines()]
        print(mode, len(streams[mode]), "original records", flush=True)
    ids = {
        i
        for r in data["heads"]
        for i in [*r["whole_entries"], *[e["entry_id"] for e in r["base_entries"]]]
    }
    paths = (
        "src/lib.rs",
        "src/dictionary.rs",
        "src/dictionary/attachment.rs",
        "src/doeda_suffix.rs",
        "web/src/breakdown.ts",
        "web/src/model.ts",
    )
    report = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "fixture_sha256": sha(FIXTURE),
        "package_sha256": sha(PACKAGE),
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "before_input": text,
        "before_streams": streams,
        "complete_native_entries": {
            i: source["complete_native_entries"][i] for i in sorted(ids)
        },
        "implementation_files": {
            p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)} for p in paths
        },
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    inspect(report, data)
    write(REPORT, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        inspect(read(REPORT), read(FIXTURE))
    else:
        assert args.cli and args.dictionary
        freeze(args)
