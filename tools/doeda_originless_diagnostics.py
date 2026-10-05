"""Attribute finite semantic suffix additions to complete original whole owners."""

import argparse
import copy
import hashlib
import json
import subprocess
import unicodedata
from itertools import pairwise
from pathlib import Path

from doeda_native_preflight import expected, words
from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as PREFLIGHT
from doeda_suffix_diagnostics import SuffixAudit, components_for, validate_components
from lexical_nada_audit import ROOT, read, sha, write
from lexical_nada_compare import canon

REPORT = ROOT / "docs/doeda-originless-diagnostics.json.gz"


class OriginlessAudit(SuffixAudit):
    def __init__(self, source):
        super().__init__(
            source["original_parent_components"],
            original_words=words(source["before_streams"]["raw"]),
        )
        self.formations = {f["head"]: f for f in read(FIXTURE)["formations"]}
        self.upgrades = []

    def word(self, before, after):
        adjusted = copy.deepcopy(after)
        bases = {f["base"]: f for f in self.formations.values()}
        # Lookup origin data is shared by word-local slots. Only explicitly
        # sourced empty noun origins may upgrade a previously lightweight slot.
        for old in before["dictionary"]["lemmas"]:
            new = next(
                s
                for s in adjusted["dictionary"]["lemmas"]
                if s["lemma"] == old["lemma"]
            )
            if old == new:
                continue
            f = bases.get(old["lemma"]["text"])
            assert f and old["lemma"]["kind"] == "nominal"
            assert [e["id"] for e in old["entries"]] == [
                e["id"] for e in new["entries"]
            ]
            for b, a in zip(old["entries"], new["entries"], strict=True):
                if b == a:
                    continue
                assert b["id"] in f["noun_entries"] and a["pos"] == "명사"
                assert "origins" not in b and a["origins"] == []
                self.upgrades.append(
                    {
                        "surface": before["normalized"],
                        "before": b,
                        "after": copy.deepcopy(a),
                    }
                )
                del a["origins"]
                assert a == b
        return super().word(before, adjusted)

    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        key = canon([category, surface, before, after])
        self.changes[key]["id"] = (
            "doeda-originless-"
            + category
            + "-"
            + hashlib.sha256(key.encode()).hexdigest()[:24]
        )


def check_identity(stream, components, forms):
    by_base = {f["base"]: f for f in forms}
    total = 0
    for record in stream:
        if record["kind"] != "word":
            continue
        for analysis, reading in zip(
            record["analysis"]["analyses"],
            record["dictionary"]["readings"],
            strict=True,
        ):
            order = components[canon(analysis)]
            if order is None:
                continue
            for left, right in pairwise(order):
                if "lemma" not in left or "morpheme" not in right:
                    continue
                index, at = left["lemma"], right["morpheme"]
                lemma, morph = analysis["lemmas"][index], analysis["morphemes"][at]
                if (
                    lemma["kind"] != "nominal"
                    or lemma["text"] not in by_base
                    or morph != {"form": "되다", "kind": "suffix"}
                ):
                    continue
                assert "suffix.verb.doeda" in analysis["rules"]
                f = by_base[lemma["text"]]
                assessment = next(
                    l for l in reading["lemmas"] if l["lemma_index"] == index
                )
                for ident in f["noun_entries"]:
                    entry = next(e for e in assessment["entries"] if e["id"] == ident)
                    assert entry["derivational_identity"] == {
                        "relation": "unknown",
                        "morpheme_index": at,
                        "expected_origins": [],
                        "whole_entries": f["whole_entries"],
                        "whole_origins_complete": False,
                    }
                    total += 1
    return total


def inspect(report):
    source, fixture = read(PREFLIGHT), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    audit = OriginlessAudit(source)
    streams = report["after_streams"]
    assert set(streams) == set(source["before_streams"])
    audit.words = words(streams["raw"])
    validate_components(report["owned_components"], streams)
    comparisons = []
    for mode, after in streams.items():
        before = source["before_streams"][mode]
        assert len(before) == len(after)
        assert "".join(r["surface"] for r in after) == source["before_input"]
        mapping = words(after)
        for case in source["cases"]:
            assert any(
                expected(a, case) for a in mapping[case["surface"]]["analyses"]
            ), (mode, case["id"])
        for c in fixture["controls"]:
            for v in fixture["variants"]:
                assert not any(
                    a["lemmas"][0] == {"text": c["base"], "kind": "nominal"}
                    and a["morphemes"][:1] == [{"form": "되다", "kind": "suffix"}]
                    and "suffix.verb.doeda" in a["rules"]
                    for a in mapping[c["base"] + v["tail"]]["analyses"]
                )
        changed = 0
        for index, (b, a) in enumerate(zip(before, after, strict=True)):
            if b != a:
                audit.record(
                    b, a, mode, {"mode": mode, "record": index, "span": a["span"]}
                )
                changed += 1
        identity = check_identity(
            after, report["owned_components"], fixture["formations"]
        )
        assert identity > 0
        comparisons.append(
            {
                "mode": mode,
                "records": len(after),
                "changed_records": changed,
                "unknown_identity_assessments": identity,
            }
        )
        assert report["uncached_streams"][mode] == after
        nfd = report["nfd_streams"][mode]
        assert len(nfd) == len(after)
        offset = 0
        for a, n in zip(after, nfd, strict=True):
            surface = unicodedata.normalize("NFD", a["surface"])
            assert n["surface"] == surface and n["kind"] == a["kind"]
            end = offset + len(surface.encode())
            assert n["span"] == {"start": offset, "end": end}
            assert {k: v for k, v in n.items() if k not in {"surface", "span"}} == {
                k: v for k, v in a.items() if k not in {"surface", "span"}
            }
            offset = end
    assert report["comparisons"] == comparisons
    assert report["changes"] == list(audit.changes.values())
    assert report["origin_lookup_upgrades"] == audit.upgrades
    assert set(report["implementation_files"]) == {
        "src/lib.rs",
        "src/doeda_identity.rs",
        "src/doeda_originless_forms.rs",
        "src/doeda_suffix.rs",
        "src/engine.rs",
        "src/breakdown.rs",
        "src/dictionary.rs",
        "src/dictionary/attachment.rs",
    }
    for snapshot in report["implementation_files"].values():
        assert (
            snapshot["sha256"] == hashlib.sha256(snapshot["text"].encode()).hexdigest()
        )
    return comparisons, list(audit.changes.values()), audit.upgrades


def freeze(args):
    assert not REPORT.exists()
    source, fixture = read(PREFLIGHT), read(FIXTURE)
    assert sha(args.dictionary) == source["dictionary_sha256"]
    streams, nfd, uncached = {}, {}, {}
    for mode, flags in (
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        command = [
            str(args.cli),
            "text",
            "-",
            "--dictionary",
            str(args.dictionary),
            *flags,
        ]

        def run(text, cache, command=command):
            out = subprocess.run(
                [*command, "--cache-bytes", str(cache)],
                input=text,
                text=True,
                capture_output=True,
                check=True,
            )
            return [json.loads(s) for s in out.stdout.splitlines()]

        streams[mode] = run(source["before_input"], 8388608)
        uncached[mode] = run(source["before_input"], 0)
        nfd[mode] = run(unicodedata.normalize("NFD", source["before_input"]), 8388608)
    components = components_for(streams, args.bridge)
    audit = OriginlessAudit(source)
    audit.words = words(streams["raw"])
    comparisons = []
    for mode, after in streams.items():
        changed = 0
        for index, (b, a) in enumerate(
            zip(source["before_streams"][mode], after, strict=True)
        ):
            if b != a:
                audit.record(
                    b, a, mode, {"mode": mode, "record": index, "span": a["span"]}
                )
                changed += 1
        comparisons.append(
            {
                "mode": mode,
                "records": len(after),
                "changed_records": changed,
                "unknown_identity_assessments": check_identity(
                    after, components, fixture["formations"]
                ),
            }
        )
    paths = (
        "src/lib.rs",
        "src/doeda_identity.rs",
        "src/doeda_originless_forms.rs",
        "src/doeda_suffix.rs",
        "src/engine.rs",
        "src/breakdown.rs",
        "src/dictionary.rs",
        "src/dictionary/attachment.rs",
    )
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(PREFLIGHT),
        "fixture_sha256": sha(FIXTURE),
        "before_cli_sha256": source["cli_sha256"],
        "cli_sha256": sha(args.cli),
        "bridge_sha256": sha(args.bridge),
        "dictionary_sha256": sha(args.dictionary),
        "implementation_files": {
            p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)} for p in paths
        },
        "after_streams": streams,
        "nfd_streams": nfd,
        "uncached_streams": uncached,
        "owned_components": components,
        "comparisons": comparisons,
        "changes": list(audit.changes.values()),
        "origin_lookup_upgrades": audit.upgrades,
        "scope": "All 254 source-cohort words across three filters, NFC/NFD and cache parity. Every added hypothesis is reconstructed from original whole owners; native origin upgrades and unknown identity evidence are separate. Packaged HTTP/browser, broad streams, full corpora and independent/contextual review remain required.",
    }
    inspect(report)
    write(REPORT, report)
    verify()


def verify():
    comparisons, changes, upgrades = inspect(read(REPORT))
    print(
        "Verified",
        comparisons,
        len(changes),
        "individual changes and",
        len(upgrades),
        "origin lookup upgrades.",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("cli", "dictionary", "bridge"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary and args.bridge
        freeze(args)
