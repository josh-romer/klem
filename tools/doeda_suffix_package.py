"""Verify complete packaged API/browser evidence against its frozen sources.

Historical implementation text is retained so later engine changes do not
silently certify older package checks as current coverage. Original corpus gold
and contextual/formal-history/independent judgments remain separate.
"""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from doeda_suffix_audit import FIXTURE, SOURCE
from doeda_suffix_diagnostics import REPORT as DIAGNOSTICS
from doeda_suffix_regressions import CORRECTIONS, effective_cases
from emphatic_ending_runtime import verify_stream
from lexical_nada_audit import ROOT, read, sha, write

REPORT = ROOT / "docs/doeda-suffix-packaged-checks.json.gz"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def matched(a, c):
    return (
        [l["text"] for l in a["lemmas"]] == c["lemmas"]
        and [l["kind"] for l in a["lemmas"]] == c["lemma_kinds"]
        and [m["form"] for m in a["morphemes"]] == c["morphemes"]
        and [m["kind"] for m in a["morphemes"]] == c["morpheme_kinds"]
        and set(c["required_rules"]) <= set(a["rules"])
    )


def verify_data(report):
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    api, browser = report["api"], report["browser"]
    source, diagnostic = read(SOURCE), read(DIAGNOSTICS)
    for key, path in (
        ("source_sha256", SOURCE),
        ("fixture_sha256", FIXTURE),
        ("corrections_sha256", CORRECTIONS),
        ("diagnostics_sha256", DIAGNOSTICS),
    ):
        assert api[key] == sha(path)
    assert (
        api["dictionary_sha256"]
        == browser["dictionary_sha256"]
        == source["dictionary_sha256"]
    )
    assert api["cli_sha256"] == browser["cli_sha256"] == report["cli_sha256"]
    for snap in [
        *api["implementation_files"].values(),
        api["api_check_source"],
        report["nix_log"],
    ]:
        assert digest(snap["text"]) == snap["sha256"]
    assert (
        api["implementation_files"]["src/engine.rs"]["sha256"]
        == diagnostic["engine_sha256"]
    )
    assert (
        api["implementation_files"]["src/dictionary/attachment.rs"]["sha256"]
        == diagnostic["attachment_sha256"]
    )
    rows = re.findall(
        r"test result: .*? (\d+) passed; (\d+) failed; (\d+) ignored;",
        report["nix_log"]["text"],
    )
    assert len(rows) == 192
    assert tuple(sum(int(r[i]) for r in rows) for i in range(3)) == (887, 0, 1)
    assert (
        "Verified 2953 individually attributed suffix changes"
        in report["nix_log"]["text"]
    )
    for mode, stream in diagnostic["source_diagnostic_streams"].items():
        expected = {
            "records": len(stream),
            "passed": True,
            "sha256": digest(json.dumps(stream, ensure_ascii=False, sort_keys=True)),
        }
        assert api["source_release_parity"][mode] == expected
    cases = effective_cases()
    base_heads = {
        p["base"]: p["base_entries"] for p in read(FIXTURE)["formation_proposals"]
    }
    indexed = {c["id"]: c for c in cases}
    seen = set()
    judgments = 0
    for batch in api["batches"]:
        encoding, ordinal, text = batch["encoding"], batch["batch"], batch["text"]
        assert encoding in ("NFC", "NFD")
        assert unicodedata.normalize(encoding, text) == text
        assert 0 < batch["bytes"] == len(text.encode()) <= 7500
        streams = batch["cli_streams"]
        assert batch["api"]["records"] == streams["all"]
        for mode in ("all", "headword", "compatible"):
            verify_stream(streams[mode], streams["all"], mode, text)
        for record, order in zip(
            batch["api"]["records"], batch["api"]["breakdowns"], strict=True
        ):
            if record.get("analysis") is None:
                assert order is None
                continue
            assert len(order) == len(record["analysis"]["analyses"])
            for a, components in zip(
                record["analysis"]["analyses"], order, strict=True
            ):
                assert components is not None
                for kind, field in (("lemma", "lemmas"), ("morpheme", "morphemes")):
                    assert [c[kind] for c in components if kind in c] == list(
                        range(len(a[field]))
                    )
        found = {
            r["analysis"]["normalized"]: r
            for r in streams["all"]
            if r["kind"] == "word"
        }
        expected_ids = [c["id"] for c in cases if c["surface"] in found]
        assert batch["cases"] == expected_ids
        for ident in batch["cases"]:
            assert (encoding, ident) not in seen
            seen.add((encoding, ident))
            case = indexed[ident]
            paths = found[case["surface"]]["analysis"]["analyses"]
            assert any(matched(a, case) for a in paths) == (
                case["verdict"] == "required"
            )
            for mode in ("headword", "compatible"):
                filtered = next(
                    r
                    for r in streams[mode]
                    if r["kind"] == "word"
                    and r["analysis"]["normalized"] == case["surface"]
                )
                expected = case["verdict"] == "required" and bool(
                    base_heads[case["lemmas"][0]]
                )
                if mode == "compatible" and case["lemmas"][0] == "속":
                    expected = False
                assert (
                    any(matched(a, case) for a in filtered["analysis"]["analyses"])
                    == expected
                ), (encoding, mode, ident)
            judgments += 1
        exports = [
            r
            for r in browser["checks"]
            if (r["encoding"], r["batch"]) == (encoding, ordinal)
        ]
        assert [r["mode"] for r in exports] == ["all", "headword", "compatible"]
        assert all(
            r["cases"] == batch["cases"] and r["records"] == len(streams[r["mode"]])
            for r in exports
        )
    assert seen == {(encoding, c["id"]) for encoding in ("NFC", "NFD") for c in cases}
    assert judgments == api["case_judgments"] == 3200
    assert len(browser["checks"]) == 3 * len(api["batches"])
    assert (
        browser["case_count"] == len(cases) == 1600 and browser["browser_errors"] == []
    )
    expected_words = ["타도되었다", "고돼요", "못돼요", "속된", "가결됨이다", "한갓된"]
    expected_forms = [
        ["타도", "되", "었", "다"],
        ["고", "되", "어요"],
        ["못", "되", "어요"],
        ["속", "되", "은"],
        ["가결", "되", "음", "이", "다"],
        ["한갓", "되", "은"],
    ]
    assert [d["word"] for d in browser["diagrams"]] == expected_words
    for diagram, forms in zip(browser["diagrams"], expected_forms, strict=True):
        assert diagram["passed"] and diagram["suffix_entry_id"] == "krdict:74902"
        c = indexed[diagram["case_id"]]
        assert c["surface"] == diagram["word"] and c["verdict"] == "required"
        assert diagram["forms"] == forms
    native = api["native_endpoint_entries"]
    for ident, entry in native.items():
        assert ident == entry["id"] and entry["senses"]
    for ident, entry in source["complete_native_entries"].items():
        if ident in native:
            assert native[ident] == entry
    assert native["krdict:74902"]["headword"] == "-되다"
    assert native["krdict:64223"]["origins"] == ["俗되다"]
    assert report["desktop_inspected"] and report["mobile_inspected"]
    assert (
        report["contextual_verdict"]
        == report["api"]["contextual_verdict"]
        == report["browser"]["contextual_verdict"]
        == "unjudged"
    )
    assert report["independent_review"] == "pending"
    return {
        "rust_passed": 887,
        "api_case_judgments": judgments,
        "native_endpoints": len(native),
        "browser_exports": len(browser["checks"]),
        "diagrams": len(browser["diagrams"]),
    }


def freeze(args):
    assert not args.output.exists()
    api, browser = read(args.api), read(args.browser)
    nix_text = args.nix_log.read_text()
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "cli_sha256": api["cli_sha256"],
        "api": api,
        "browser": browser,
        "nix_log": {"text": nix_text, "sha256": digest(nix_text)},
        "asset_files_sha256": {
            str(p.relative_to(args.assets)): sha(p)
            for p in sorted(args.assets.rglob("*"))
            if p.is_file()
        },
        "desktop_inspected": True,
        "mobile_inspected": True,
        "screenshots_sha256": {str(p): sha(p) for p in args.screenshots},
        "scope": "Complete finite suffix cases and controls, Unicode, three native filters, exact CLI/API/browser export parity, full source-cohort debug/release parity, native dictionary endpoints and six visually inspected diagrams. Broad streams, held-out corpora, performance and native formation/context/formal-history/independent review remain separate.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    # Actual Rust component parity was executed by the retained API harness.
    # The offline gate also guards completeness/ownership of every stored order.
    print(verify_data(report))
    write(args.output, report)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--api", type=Path)
    p.add_argument("--browser", type=Path)
    p.add_argument("--nix-log", type=Path)
    p.add_argument("--assets", type=Path)
    p.add_argument("--screenshots", type=Path, nargs="+")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    if args.verify:
        print(verify_data(read(REPORT)))
    else:
        assert (
            args.api
            and args.browser
            and args.nix_log
            and args.assets
            and args.screenshots
            and args.output
        )
        freeze(args)
