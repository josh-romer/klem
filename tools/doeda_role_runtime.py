"""Verify packaged API/CLI parity, filters and actual ordered Rust components."""

import argparse
import copy
import hashlib
import itertools
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from adjectival_allomorph_runtime import post
from doeda_role_audit import FIXTURE, SOURCE
from doeda_role_compare import REPORT as OBSERVATIONS
from doeda_role_diagnostics import REPORT as DIAGNOSTICS
from lexical_nada_audit import ROOT, digest, read, sha, write

REPORT = ROOT / "docs/doeda-role-packaged-runtime.json.gz"
SOURCE_FILES = {
    "engine_sha256": "src/engine.rs",
    "grammar_sha256": "src/grammar.rs",
    "catalog_sha256": "web/src/grammar-labels.json",
    "runtime_tool_sha256": "tools/doeda_role_runtime.py",
    "browser_tool_sha256": "web/tests/doeda-role.mjs",
    "breakdown_sha256": "src/breakdown.rs",
    "attachment_sha256": "src/dictionary/attachment.rs",
}


def native_entries():
    result = {}
    for path, key in (
        (SOURCE, "complete_native_entries"),
        (DIAGNOSTICS, "additional_native_entries"),
        (OBSERVATIONS, "complete_native_entries"),
    ):
        for ident, entry in read(path)[key].items():
            if ident in result:
                assert result[ident] == entry
            result[ident] = entry
    return result


def matched(analysis, case):
    return (
        [l["text"] for l in analysis["lemmas"]] == case["lemmas"]
        and [l["kind"] for l in analysis["lemmas"]] == case["lemma_kinds"]
        and [m["form"] for m in analysis["morphemes"]] == case["morphemes"]
        and [m["kind"] for m in analysis["morphemes"]] == case["morpheme_kinds"]
        and set(case["required_rules"]) <= set(analysis["rules"])
    )


def judgments(records, encoding):
    found = {r["analysis"]["normalized"]: r for r in records if r["kind"] == "word"}
    rows = []
    for case in read(FIXTURE)["cases"]:
        matches = [
            a
            for a in found[case["surface"]]["analysis"]["analyses"]
            if matched(a, case)
        ]
        assert bool(matches) == (case["verdict"] == "required"), (encoding, case["id"])
        for analysis in matches:
            index = found[case["surface"]]["analysis"]["analyses"].index(analysis)
            reading = found[case["surface"]]["dictionary"]["readings"][index]
            assert reading["status"] != "incompatible"
            for owner, lemma in enumerate(analysis["lemmas"]):
                if owner > 0 and lemma == {"text": "되다", "kind": "predicate"}:
                    entries = reading["lemmas"][owner]["entries"]
                    assert (
                        next(e for e in entries if e["id"] == "krdict:89858")["status"]
                        == "compatible"
                    )
                    assert (
                        next(e for e in entries if e["id"] == "krdict:48214")["status"]
                        == "incompatible"
                    )
        rows.append(
            {
                "id": case["id"],
                "encoding": encoding,
                "verdict": case["verdict"],
                "passed": True,
            }
        )
    return rows


def verify_stream(records, original, mode, text):
    assert len(records) == len(original)
    assert "".join(r["surface"] for r in records) == text
    offset = 0
    for actual, base in zip(records, original, strict=True):
        assert actual["span"]["start"] == offset
        offset += len(actual["surface"].encode())
        assert actual["span"]["end"] == offset
        assert (
            text.encode()[actual["span"]["start"] : offset].decode()
            == actual["surface"]
        )
        expected = copy.deepcopy(base)
        if mode != "all" and base["kind"] == "word":
            annotation = base["dictionary"]
            slots = {
                (s["lemma"]["text"], s["lemma"]["kind"]): s
                for s in annotation["lemmas"]
            }
            indices = [
                i
                for i, a in enumerate(base["analysis"]["analyses"])
                if all(slots[(l["text"], l["kind"])]["entries"] for l in a["lemmas"])
                and (
                    mode != "compatible"
                    or annotation["readings"][i]["status"] != "incompatible"
                )
            ]
            expected["analysis"]["analyses"] = [
                base["analysis"]["analyses"][i] for i in indices
            ]
            expected["dictionary"]["readings"] = [
                annotation["readings"][i] for i in indices
            ]
            retained = {
                (l["text"], l["kind"])
                for a in expected["analysis"]["analyses"]
                for l in a["lemmas"]
            }
            expected["dictionary"]["lemmas"] = [
                s
                for s in annotation["lemmas"]
                if (s["lemma"]["text"], s["lemma"]["kind"]) in retained
            ]
        assert actual == expected, (
            mode,
            actual["surface"],
            "filter/native/order parity",
        )
    assert offset == len(text.encode())


def freeze(cli, web, bridge, url, output):
    assert not output.exists()
    fixture, observations = read(FIXTURE), read(OBSERVATIONS)
    dictionary = ROOT / "data/dictionaries/krdict/krdict.db"
    assert sha(cli) == observations["cli_sha256"]
    assert sha(dictionary) == observations["dictionary_sha256"]
    with urllib.request.urlopen(url + "/api/status", timeout=20) as response:
        status = json.load(response)
    words = sorted(fixture["before_case_words"])
    native = native_entries()
    endpoints = []
    for ident, entry in native.items():
        assert post(url, "/api/entry", {"id": ident})["entry"] == entry
        endpoints.append({"id": ident, "sha256": digest(entry), "passed": True})
    print(len(native), "complete native endpoints verified", flush=True)
    api, checks, cases, shapes = [], [], [], {}
    for encoding in ("NFC", "NFD"):
        text = (
            "前🙂「"
            + " ".join(unicodedata.normalize(encoding, w) for w in words)
            + "」"
        )
        assert len(text.encode()) <= 8000
        actual = post(url, "/api/analyze", {"text": text, "suggest_spacing": True})
        plain = post(url, "/api/analyze", {"text": text})
        assert plain["records"] == [
            {k: v for k, v in r.items() if k != "spacing"} for r in actual["records"]
        ]
        assert len(actual["records"]) == len(actual["breakdowns"])
        cases.extend(judgments(actual["records"], encoding))
        for record, components in zip(
            actual["records"], actual["breakdowns"], strict=True
        ):
            if record["kind"] != "word":
                assert components is None
                continue
            assert len(components) == len(record["analysis"]["analyses"])
            for analysis, ordered in zip(
                record["analysis"]["analyses"], components, strict=True
            ):
                key = digest(analysis)
                value = {"analysis": analysis, "components": ordered}
                if key in shapes:
                    assert shapes[key] == value
                shapes[key] = value
        api.append(
            {
                "encoding": encoding,
                "input": text,
                "records": actual["records"],
                "breakdowns": actual["breakdowns"],
            }
        )
        for cache, (mode, flags) in itertools.product(
            (0, 1, 4096),
            (
                ("all", []),
                ("headword", ["--dict-only"]),
                ("compatible", ["--dict-compatible"]),
            ),
        ):
            command = [
                str(cli),
                "text",
                "-",
                "--dictionary",
                str(dictionary),
                "--cache-bytes",
                str(cache),
            ]
            spacing = [
                json.loads(l)
                for l in subprocess.check_output(
                    [*command, "--suggest-spacing", *flags], input=text.encode()
                ).splitlines()
            ]
            plain_cli = [
                json.loads(l)
                for l in subprocess.check_output(
                    [*command, *flags], input=text.encode()
                ).splitlines()
            ]
            assert plain_cli == [
                {k: v for k, v in r.items() if k != "spacing"} for r in spacing
            ]
            if mode == "all":
                assert spacing == actual["records"]
            verify_stream(spacing, actual["records"], mode, text)
            # Full filtered streams are retained; compare cache budgets exactly.
            previous = next(
                (r for r in checks if r["encoding"] == encoding and r["mode"] == mode),
                None,
            )
            if previous:
                assert previous["records_sha256"] == digest(spacing)
            checks.append(
                {
                    "encoding": encoding,
                    "cache_bytes": cache,
                    "mode": mode,
                    "record_count": len(spacing),
                    "records_sha256": digest(spacing),
                    "records": spacing,
                }
            )
    keys = sorted(shapes)
    proofs = subprocess.check_output(
        [str(bridge)],
        input="".join(
            json.dumps(shapes[k]["analysis"], ensure_ascii=False) + "\n" for k in keys
        ).encode(),
    )
    for key, line in zip(keys, proofs.splitlines(), strict=True):
        proof = json.loads(line)
        assert not proof["reviewed_removal"]
        assert (
            proof["components"] is not None
            and proof["components"] == shapes[key]["components"]
        )
    report = {
        "schema_version": 1,
        "checklist": "COV-019ag",
        "source_sha256": sha(SOURCE),
        "fixture_sha256": sha(FIXTURE),
        "diagnostics_sha256": sha(DIAGNOSTICS),
        "observations_sha256": sha(OBSERVATIONS),
        **{field: sha(ROOT / path) for field, path in SOURCE_FILES.items()},
        "implementation_files": {
            path: (ROOT / path).read_text() for path in SOURCE_FILES.values()
        },
        "cli_sha256": sha(cli),
        "web_sha256": sha(web),
        "bridge_sha256": sha(bridge),
        "dictionary_sha256": sha(dictionary),
        "status": status,
        "words": words,
        "native_endpoints": endpoints,
        "api_checks": api,
        "cases": cases,
        "checks": checks,
        "ordered_shapes": shapes,
        "all_api_components_match_rust": True,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(output, report)
    print(
        f"Verified {len(words)} words, {len(cases)} encoded judgments, 18 cache/filter streams and {len(shapes)} distinct ordered Rust shapes."
    )


def verify():
    report, observations, fixture = read(REPORT), read(OBSERVATIONS), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-019ag"
    for field, path in (
        ("source_sha256", SOURCE),
        ("fixture_sha256", FIXTURE),
        ("diagnostics_sha256", DIAGNOSTICS),
        ("observations_sha256", OBSERVATIONS),
    ):
        assert report[field] == sha(path)
    assert report["cli_sha256"] == observations["cli_sha256"]
    assert report["dictionary_sha256"] == observations["dictionary_sha256"]
    assert report["words"] == sorted(fixture["before_case_words"])
    assert set(report["implementation_files"]) == set(SOURCE_FILES.values())
    for field, path in SOURCE_FILES.items():
        assert (
            hashlib.sha256(report["implementation_files"][path].encode()).hexdigest()
            == report[field]
        )
    assert report["native_endpoints"] == [
        {"id": i, "sha256": digest(e), "passed": True}
        for i, e in native_entries().items()
    ]
    assert [r["encoding"] for r in report["api_checks"]] == ["NFC", "NFD"]
    assert report["cases"] == [
        j for r in report["api_checks"] for j in judgments(r["records"], r["encoding"])
    ]
    shapes = {}
    for row in report["api_checks"]:
        expected_input = (
            "前🙂「"
            + " ".join(
                unicodedata.normalize(row["encoding"], w) for w in report["words"]
            )
            + "」"
        )
        assert row["input"] == expected_input
        verify_stream(row["records"], row["records"], "all", row["input"])
        assert len(row["records"]) == len(row["breakdowns"])
        for record, components in zip(row["records"], row["breakdowns"], strict=True):
            if record["kind"] != "word":
                assert components is None
                continue
            for a, ordered in zip(
                record["analysis"]["analyses"], components, strict=True
            ):
                assert ordered is not None
                key = digest(a)
                if key in shapes:
                    assert shapes[key] == {"analysis": a, "components": ordered}
                shapes[key] = {"analysis": a, "components": ordered}
    assert (
        shapes == report["ordered_shapes"] and report["all_api_components_match_rust"]
    )
    assert [
        (r["encoding"], r["cache_bytes"], r["mode"]) for r in report["checks"]
    ] == list(
        itertools.product(
            ("NFC", "NFD"), (0, 1, 4096), ("all", "headword", "compatible")
        )
    )
    for row in report["checks"]:
        assert row["record_count"] == len(row["records"])
        assert row["records_sha256"] == digest(row["records"])
        original = next(
            r
            for r in report["checks"]
            if r["encoding"] == row["encoding"] and r["mode"] == row["mode"]
        )
        assert original["records"] == row["records"]
        api = next(r for r in report["api_checks"] if r["encoding"] == row["encoding"])
        verify_stream(row["records"], api["records"], row["mode"], api["input"])
        if row["mode"] == "all":
            api = next(
                r for r in report["api_checks"] if r["encoding"] == row["encoding"]
            )
            assert api["records"] == row["records"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        f"Verified packaged 되다-role evidence: {len(report['native_endpoints'])} full native endpoints, {len(report['cases'])} encoded judgments, 18 cache/filter streams and {len(shapes)} ordered shapes; historical implementation sources retained."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--web", type=Path)
    p.add_argument("--bridge", type=Path)
    p.add_argument("--url")
    p.add_argument("--output", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.cli and a.web and a.bridge and a.url and a.output
        freeze(a.cli.resolve(), a.web.resolve(), a.bridge.resolve(), a.url, a.output)
