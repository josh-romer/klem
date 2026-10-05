"""Track every supplemental candidate change against its original whole owner."""

import argparse
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from doeda_native_preflight import expected, words
from doeda_originless_diagnostics import REPORT as PREVIOUS
from doeda_originless_diagnostics import OriginlessAudit, check_identity
from doeda_partial_origins import FIXTURE
from doeda_partial_origins import REPORT as PREFLIGHT
from doeda_suffix_diagnostics import components_for, validate_components
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-partial-origin-diagnostics.json.gz"
MODES = {"raw": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}


def audit_for(source, fixture, components):
    return OriginlessAudit(
        dict(source, original_parent_components=components),
        formations=fixture["formations"],
        change_namespace="doeda-partial-origin-",
    )


def inspect(report):
    source, fixture = read(PREFLIGHT), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["before_cli_sha256"] == source["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    assert report["before_bridge_sha256"] == read(PREVIOUS)["bridge_sha256"]
    validate_components(report["original_parent_components"], source["before_streams"])
    validate_components(report["owned_components"], report["after_streams"])
    audit = audit_for(source, fixture, report["original_parent_components"])
    audit.words = words(report["after_streams"]["raw"])
    comparisons = []
    assert (
        set(report["after_streams"])
        == set(report["nfd_streams"])
        == set(report["uncached_streams"])
        == set(report["after_jsonl"])
        == set(report["after_jsonl_sha256"])
        == set(MODES)
    )
    for mode, after in report["after_streams"].items():
        encoded = report["after_jsonl"][mode]
        assert (
            hashlib.sha256(encoded.encode()).hexdigest()
            == report["after_jsonl_sha256"][mode]
        )
        assert [json.loads(line) for line in encoded.splitlines()] == after
        assert "".join(r["surface"] for r in after) == source["before_input"]
        mapping = words(after)
        for case in fixture["cases"]:
            assert any(
                expected(a, case) for a in mapping[case["surface"]]["analyses"]
            ), (mode, case["id"])
        for case in fixture["controls"]:
            assert not any(
                a["lemmas"]
                and a["lemmas"][0] == {"text": case["base"], "kind": "nominal"}
                and case["forbidden_rule"] in a["rules"]
                for a in mapping[case["surface"]]["analyses"]
            ), case["id"]
        changed = 0
        for index, (before, current) in enumerate(
            zip(source["before_streams"][mode], after, strict=True)
        ):
            if before != current:
                audit.record(
                    before,
                    current,
                    mode,
                    {"mode": mode, "record": index, "span": current["span"]},
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
        assert len(report["nfd_streams"][mode]) == len(after)
        offset = 0
        for nfc, nfd in zip(after, report["nfd_streams"][mode], strict=True):
            surface = unicodedata.normalize("NFD", nfc["surface"])
            end = offset + len(surface.encode())
            assert nfd["surface"] == surface and nfd["span"] == {
                "start": offset,
                "end": end,
            }
            assert {k: v for k, v in nfc.items() if k not in {"surface", "span"}} == {
                k: v for k, v in nfd.items() if k not in {"surface", "span"}
            }
            offset = end
    assert report["comparisons"] == comparisons
    assert report["changes"] == list(audit.changes.values())
    assert report["origin_lookup_upgrades"] == audit.upgrades
    assert report["changes"] and all(
        c["id"].startswith("doeda-partial-origin-") for c in report["changes"]
    )
    assert set(report["implementation_files"]) == set(
        read(PREVIOUS)["implementation_files"]
    )
    for snap in report["implementation_files"].values():
        assert hashlib.sha256(snap["text"].encode()).hexdigest() == snap["sha256"]
    return comparisons, len(report["changes"])


def freeze(args):
    source, fixture = read(PREFLIGHT), read(FIXTURE)
    assert not args.output.exists()
    assert sha(args.dictionary) == source["dictionary_sha256"]
    assert sha(args.before_bridge) == read(PREVIOUS)["bridge_sha256"]
    original = components_for(source["before_streams"], args.before_bridge)
    streams, encoded, nfd, uncached = {}, {}, {}, {}
    for mode, flags in MODES.items():
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
            return out.stdout, [json.loads(line) for line in out.stdout.splitlines()]

        encoded[mode], streams[mode] = run(source["before_input"], 8388608)
        _, uncached[mode] = run(source["before_input"], 0)
        _, nfd[mode] = run(
            unicodedata.normalize("NFD", source["before_input"]), 8388608
        )
    owned = components_for(streams, args.bridge)
    audit = audit_for(source, fixture, original)
    audit.words = words(streams["raw"])
    comparisons = []
    for mode, after in streams.items():
        changed = 0
        for index, (before, current) in enumerate(
            zip(source["before_streams"][mode], after, strict=True)
        ):
            if before != current:
                audit.record(
                    before,
                    current,
                    mode,
                    {"mode": mode, "record": index, "span": current["span"]},
                )
                changed += 1
        comparisons.append(
            {
                "mode": mode,
                "records": len(after),
                "changed_records": changed,
                "unknown_identity_assessments": check_identity(
                    after, owned, fixture["formations"]
                ),
            }
        )
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(PREFLIGHT),
        "fixture_sha256": sha(FIXTURE),
        "before_cli_sha256": source["cli_sha256"],
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "before_bridge_sha256": sha(args.before_bridge),
        "bridge_sha256": sha(args.bridge),
        "original_parent_components": original,
        "owned_components": owned,
        "after_streams": streams,
        "after_jsonl": encoded,
        "after_jsonl_sha256": {
            m: hashlib.sha256(t.encode()).hexdigest() for m, t in encoded.items()
        },
        "uncached_streams": uncached,
        "nfd_streams": nfd,
        "comparisons": comparisons,
        "changes": list(audit.changes.values()),
        "origin_lookup_upgrades": audit.upgrades,
        "implementation_files": {
            p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)}
            for p in read(PREVIOUS)["implementation_files"]
        },
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
        "scope": "Actual finite-source CLI captures in all filters, NFC/NFD and cached/uncached modes; all additions attributed to unchanged original whole parents. Full release/browser/broad/corpus checks are separate.",
    }
    inspect(report)
    write(args.output, report)
    print(comparisons, len(report["changes"]), "individual changes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--before-bridge", type=Path)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args()
    freeze(args) if args.freeze else print(inspect(read(REPORT)))
