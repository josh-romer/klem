"""Attribute every native source-cohort change to original whole-head owners."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_native_audit import FIXTURE
from doeda_native_preflight import REPORT as PREFLIGHT
from doeda_native_preflight import expected, words
from doeda_suffix_diagnostics import SuffixAudit
from doeda_suffix_regressions import effective_formations
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-native-diagnostics.json.gz"


class NativeAudit(SuffixAudit):
    def __init__(self, components, original_words):
        super().__init__(components, original_words=original_words)
        self.formations = {
            f["head"]: f
            for f in [*effective_formations(), *read(FIXTURE)["formations"]]
        }

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        from lexical_nada_compare import canon

        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "doeda-native-"
            + category
            + "-"
            + hashlib.sha256(key.encode()).hexdigest()[:24]
        )


def inspect(source, streams):
    assert set(streams) == set(source["before_streams"])
    audit = NativeAudit(
        source["original_parent_components"], words(source["before_streams"]["raw"])
    )
    audit.words = words(streams["raw"])
    comparisons = []
    for mode, stream in streams.items():
        before = source["before_streams"][mode]
        assert len(before) == len(stream) == 31400
        assert "".join(r["surface"] for r in stream) == source["before_input"]
        mapping = words(stream)
        for case in source["cases"]:
            assert any(
                expected(a, case) for a in mapping[case["surface"]]["analyses"]
            ), (mode, case["id"])
        changed = 0
        for index, (b, a) in enumerate(zip(before, stream, strict=True)):
            if b == a:
                continue
            audit.record(b, a, mode, {"mode": mode, "record": index, "span": a["span"]})
            changed += 1
        assert changed == 15700
        comparisons.append(
            {"mode": mode, "records": len(stream), "changed_records": changed}
        )
    return comparisons, list(audit.changes.values())


def freeze(args):
    assert not REPORT.exists()
    source = read(PREFLIGHT)
    assert sha(args.dictionary) == source["dictionary_sha256"]
    streams = {}
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
        streams[mode] = [json.loads(line) for line in out.stdout.splitlines()]
        print(mode, len(streams[mode]), "actual after records captured", flush=True)
    comparisons, changes = inspect(source, streams)
    paths = (
        "src/lib.rs",
        "src/doeda_native_forms.rs",
        "src/doeda_suffix.rs",
        "src/engine.rs",
        "src/breakdown.rs",
        "src/dictionary/attachment.rs",
    )
    snapshots = {
        p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)} for p in paths
    }
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(PREFLIGHT),
        "fixture_sha256": sha(FIXTURE),
        "before_cli_sha256": source["cli_sha256"],
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "implementation_files": snapshots,
        "comparisons": comparisons,
        "after_streams": streams,
        "changes": changes,
        "scope": "All 94,200 original native source records compared across three filters. Every addition reconstructs from original whole-head owners with correct source roles, suffix/morpheme indices, rules and recovery evidence. Original candidates/native slots/readings/order survive. All 15,700 exact structural paths survive both filters. This debug capture does not substitute for packaged, broad/corpus, contextual or independent review.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(REPORT, report)
    verify()


def verify():
    report, source = read(REPORT), read(PREFLIGHT)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    for snapshot in report["implementation_files"].values():
        assert (
            hashlib.sha256(snapshot["text"].encode()).hexdigest() == snapshot["sha256"]
        )
    comparisons, changes = inspect(source, report["after_streams"])
    assert comparisons == report["comparisons"]
    assert changes == report["changes"]
    print(
        "Verified 94,200 native source records and",
        len(changes),
        "individually attributed changes; original candidate/native order retained.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("cli", "dictionary"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary
        freeze(args)
