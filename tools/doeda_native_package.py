"""Verify archived release/API coverage and representative browser diagrams.

The complete encoded API cohort is separate from the six browser examples.
Historical source snapshots identify the verified implementation; contextual
precision and independent linguistic review remain unjudged.
"""

import argparse
import hashlib
import re
import unicodedata
from functools import cache
from pathlib import Path

from doeda_native_audit import FIXTURE
from doeda_native_diagnostics import REPORT as DIAGNOSTICS
from doeda_native_preflight import REPORT as PREFLIGHT
from doeda_native_preflight import expected
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-native-packaged-checks.json.gz"
MODES = {"raw", "headword", "compatible"}
VARIANTS = (
    "past-final",
    "contracted-polite",
    "nominal-topic",
    "nominal-copula",
    "present-adnominal",
    "formal-polite",
)


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


@cache
def sources():
    return read(PREFLIGHT), read(DIAGNOSTICS), read(FIXTURE)


def browser_cases(fixture):
    result = []
    for i, name in enumerate(VARIANTS):
        formation = fixture["formations"][i * len(fixture["formations"]) // 6]
        variant = next(v for v in fixture["variants"] if v["id"] == name)
        result.append(
            {
                "id": formation["id"] + "-" + name,
                "word": formation["base"] + variant["tail"],
                "forms": [
                    formation["base"],
                    "되",
                    *(
                        ["음", "이", "다"]
                        if name == "nominal-copula"
                        else variant["morphemes"]
                    ),
                ],
            }
        )
    return result


def verify_data(report):
    source, diagnostic, fixture = sources()
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    api, browser = report["api"], report["browser"]
    assert api["preflight_sha256"] == sha(PREFLIGHT)
    assert api["diagnostics_sha256"] == sha(DIAGNOSTICS)
    assert browser["fixture_sha256"] == sha(FIXTURE)
    assert api["cli_sha256"] == browser["cli_sha256"] == report["cli_sha256"]
    assert (
        api["dictionary_sha256"]
        == browser["dictionary_sha256"]
        == source["dictionary_sha256"]
    )
    assert api["implementation_files"] == diagnostic["implementation_files"]
    for snap in [
        *api["implementation_files"].values(),
        api["producer"],
        report["browser_producer"],
        report["nix_log"],
        *report["frontend_sources"].values(),
    ]:
        assert digest(snap["text"]) == snap["sha256"]
    tests = re.findall(
        r"test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;",
        report["nix_log"]["text"],
    )
    assert len(tests) == 193
    assert tuple(sum(int(t[i]) for t in tests) for i in range(3)) == (890, 0, 1)
    assert "Verified 94,200 native source records" in report["nix_log"]["text"]
    assert set(api["source_release_parity"]) == MODES
    for mode, parity in api["source_release_parity"].items():
        assert parity["records"] == len(diagnostic["after_streams"][mode]) == 31400
        assert re.fullmatch(r"[a-f0-9]{64}", parity["jsonl_sha256"])
    indexed = {c["id"]: c for c in source["cases"]}
    by_surface = {c["surface"]: c for c in indexed.values()}
    original = {
        r["analysis"]["normalized"]: r
        for r in diagnostic["after_streams"]["raw"]
        if r["kind"] == "word"
    }
    seen = set()
    for batch in api["batches"]:
        encoding, text = batch["encoding"], batch["text"]
        assert encoding in ("NFC", "NFD")
        assert unicodedata.normalize(encoding, text) == text
        assert 0 < len(text.encode()) <= 7500
        records, orders = batch["api"]["records"], batch["api"]["breakdowns"]
        assert "".join(r["surface"] for r in records) == text
        offset = 0
        for record in records:
            size = len(record["surface"].encode())
            assert record["span"] == {"start": offset, "end": offset + size}
            offset += size
        case_ids = []
        for record, order in zip(records, orders, strict=True):
            if record["kind"] != "word":
                assert order is None
                assert record == {
                    "surface": " ",
                    "kind": "whitespace",
                    "span": record["span"],
                    "analysis": None,
                    "dictionary": None,
                }
                continue
            surface = record["analysis"]["normalized"]
            frozen = original[surface]
            assert record["surface"] == unicodedata.normalize(encoding, surface)
            assert record["analysis"] == frozen["analysis"]
            assert record["dictionary"] == frozen["dictionary"]
            assert len(order) == len(record["analysis"]["analyses"])
            for a, components in zip(
                record["analysis"]["analyses"], order, strict=True
            ):
                assert all(set(c) in ({"lemma"}, {"morpheme"}) for c in components)
                for kind, field in (("lemma", "lemmas"), ("morpheme", "morphemes")):
                    assert [c[kind] for c in components if kind in c] == list(
                        range(len(a[field]))
                    )
            case = by_surface[surface]
            case_ids.append(case["id"])
            assert (encoding, case["id"]) not in seen
            seen.add((encoding, case["id"]))
            matches = [
                i
                for i, a in enumerate(record["analysis"]["analyses"])
                if expected(a, case)
            ]
            assert matches
            wanted = [{"lemma": 0}, {"morpheme": 0}]
            if len(case["lemmas"]) == 2:
                wanted += [{"morpheme": 1}, {"lemma": 1}, {"morpheme": 2}]
            else:
                wanted += [{"morpheme": i} for i in range(1, len(case["morphemes"]))]
            for i in matches:
                assert order[i] == wanted
                assert record["dictionary"]["readings"][i]["status"] == "compatible"
        assert case_ids == batch["cases"]
        assert re.fullmatch(r"[a-f0-9]{64}", batch["cli_jsonl_sha256"])
    assert seen == {(encoding, i) for encoding in ("NFC", "NFD") for i in indexed}
    assert api["case_judgments"] == len(seen) == 31400
    assert api["native_endpoint_entries"] == source["complete_native_entries"]
    samples = browser_cases(fixture)
    ids = [c["id"] for c in samples]
    assert [(c["encoding"], c["mode"]) for c in browser["checks"]] == [
        (encoding, mode)
        for encoding in ("NFC", "NFD")
        for mode in ("raw", "headword", "compatible")
    ]
    assert all(c["cases"] == ids and c["records"] == 11 for c in browser["checks"])
    assert browser["diagrams"] == [
        {
            "word": c["word"],
            "case_id": c["id"],
            "forms": c["forms"],
            "suffix_entry_id": "krdict:74902",
        }
        for c in samples
    ]
    assert browser["browser_errors"] == []
    assert report["desktop_inspected"] and report["mobile_inspected"]
    assert len(report["screenshots_sha256"]) == 2
    assert report["asset_files_sha256"]
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", v)
        for mapping in (report["screenshots_sha256"], report["asset_files_sha256"])
        for v in mapping.values()
    )
    assert api["contextual_verdict"] == report["contextual_verdict"] == "unjudged"
    assert api["independent_review"] == report["independent_review"] == "pending"
    return {
        "rust_passed": 890,
        "api_case_judgments": len(seen),
        "native_endpoints": len(api["native_endpoint_entries"]),
        "browser_exports": 6,
        "diagrams": 6,
    }


def snapshot(path):
    return {"text": path.read_text(), "sha256": sha(path)}


def freeze(args):
    assert not REPORT.exists()
    api = read(args.api)
    assert all(
        sha(ROOT / p) == s["sha256"] for p, s in api["implementation_files"].items()
    )
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "cli_sha256": api["cli_sha256"],
        "api": api,
        "browser": read(args.browser),
        "browser_producer": snapshot(args.browser_tool),
        "nix_log": snapshot(args.nix_log),
        "frontend_sources": {
            str(p.relative_to(ROOT)): snapshot(p)
            for p in sorted((ROOT / "web/src").rglob("*"))
            if p.is_file()
        },
        "asset_files_sha256": {
            str(p.relative_to(args.assets)): sha(p)
            for p in sorted(args.assets.rglob("*"))
            if p.is_file()
        },
        "screenshots_sha256": {p.name: sha(p) for p in args.screenshots},
        "desktop_inspected": True,
        "mobile_inspected": True,
        "scope": "Complete 31,400 NFC/NFD API case checks, 94,200 release/debug records, 4,319 full native endpoints; six representative browser diagrams and six Unicode/filter exports with spacing, suffix source clicks and visually inspected desktop/mobile layout. Corpus, broad streams, timing and contextual precision are separate.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    print(verify_data(report), flush=True)
    write(REPORT, report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("api", "browser", "browser-tool", "nix-log", "assets"):
        parser.add_argument("--" + name, type=Path)
    parser.add_argument("--screenshots", nargs="+", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(verify_data(read(REPORT)))
    else:
        assert all(
            (
                args.api,
                args.browser,
                args.browser_tool,
                args.nix_log,
                args.assets,
                args.screenshots,
            )
        )
        freeze(args)
