"""Verify complete packaged semantic formation API coverage and browser exports."""

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as PREFLIGHT
from doeda_originless_diagnostics import REPORT as DIAGNOSTICS
from doeda_originless_diagnostics import check_identity
from lexical_nada_audit import ROOT, read, sha, write
from lexical_nada_compare import canon

REPORT = ROOT / "docs/doeda-originless-packaged-checks.json.gz"


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def inspect_evidence(report):
    source, diagnostic, fixture = read(PREFLIGHT), read(DIAGNOSTICS), read(FIXTURE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["diagnostics_sha256"] == sha(DIAGNOSTICS)
    assert report["fixture_sha256"] == sha(FIXTURE)
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    runtime, browser = report["runtime"], report["browser"]
    for capture in (runtime, browser):
        assert capture["cli_sha256"] == report["cli_sha256"]
        assert capture["dictionary_sha256"] == report["dictionary_sha256"]
        assert capture["fixture_sha256"] == sha(FIXTURE)
    assert runtime["preflight_sha256"] == sha(PREFLIGHT)
    assert runtime["diagnostics_sha256"] == sha(DIAGNOSTICS)
    assert runtime["native_entries"] == source["complete_native_entries"]
    assert set(runtime["release_parity"]) == {"raw", "headword", "compatible"}
    for mode, receipt in runtime["release_parity"].items():
        rows = diagnostic["after_streams"][mode]
        assert receipt["records"] == len(rows)
        assert digest(receipt["jsonl"]) == receipt["jsonl_sha256"]
        assert [json.loads(line) for line in receipt["jsonl"].splitlines()] == rows
    expected = {
        r["analysis"]["normalized"]: r
        for r in diagnostic["after_streams"]["raw"]
        if r["kind"] == "word"
    }
    coverage = {encoding: [] for encoding in ("NFC", "NFD")}
    for batch in runtime["batches"]:
        encoding = batch["encoding"]
        assert encoding in coverage
        coverage[encoding].extend(batch["words"])
        assert batch["text"] == unicodedata.normalize(
            encoding, " ".join(batch["words"])
        )
        api = batch["api"]
        assert "".join(r["surface"] for r in api["records"]) == batch["text"]
        assert digest(batch["cli_jsonl"]) == batch["cli_jsonl_sha256"]
        assert [json.loads(line) for line in batch["cli_jsonl"].splitlines()] == api[
            "records"
        ]
        found = {
            r["analysis"]["normalized"] for r in api["records"] if r["kind"] == "word"
        }
        assert found == set(batch["words"])
        components = {}
        for record, orders in zip(api["records"], api["breakdowns"], strict=True):
            if record["kind"] != "word":
                continue
            old = expected[record["analysis"]["normalized"]]
            assert (
                record["analysis"] == old["analysis"]
                and record["dictionary"] == old["dictionary"]
            )
            for a, reading, order in zip(
                record["analysis"]["analyses"],
                record["dictionary"]["readings"],
                orders,
                strict=True,
            ):
                components[canon(a)] = order
                assert order == diagnostic["owned_components"][canon(a)]
                for lemma in reading["lemmas"]:
                    for entry in lemma["entries"]:
                        identity = entry.get("derivational_identity")
                        if identity:
                            assert order[:2] == [
                                {"lemma": lemma["lemma_index"]},
                                {"morpheme": identity["morpheme_index"]},
                            ]
                            assert a["morphemes"][identity["morpheme_index"]] == {
                                "form": "되다",
                                "kind": "suffix",
                            }
        check_identity(api["records"], components, fixture["formations"])
    assert all(words == sorted(expected) for words in coverage.values())
    assert runtime["words_checked"] == sum(map(len, coverage.values())) == 508
    controls = runtime["ordinary_noun_controls"]
    assert [c["encoding"] for c in controls] == ["NFC", "NFD"]
    nouns = [f["base"] for f in fixture["formations"]]
    for control in controls:
        assert control["words"] == nouns
        assert control["text"] == unicodedata.normalize(
            control["encoding"], " ".join(nouns)
        )
        assert digest(control["cli_jsonl"]) == control["cli_jsonl_sha256"]
        assert [
            json.loads(line) for line in control["cli_jsonl"].splitlines()
        ] == control["api"]["records"]
        words = [r for r in control["api"]["records"] if r["kind"] == "word"]
        assert [r["analysis"]["normalized"] for r in words] == nouns
        for r in words:
            assert all(
                "derivational_identity" not in e
                for a in r["dictionary"]["readings"]
                for l in a["lemmas"]
                for e in l["entries"]
            )
            assert all(
                "origins" not in e
                for l in r["dictionary"]["lemmas"]
                if l["lemma"]["kind"] != "root"
                for e in l["entries"]
            )
    selected = [
        ("되풀이됐어요", "되풀이"),
        ("마무리돼요", "마무리"),
        ("풀이되는", "풀이"),
    ]
    text = " ".join(word for word, _ in selected)
    responses, checks, diagrams = (
        browser["responses"],
        browser["checks"],
        browser["diagrams"],
    )
    assert [r["encoding"] for r in responses] == ["NFC", "NFD"]
    for response in responses:
        assert response["request"] == {
            "text": unicodedata.normalize(response["encoding"], text)
        }
    assert [(c["encoding"], c["mode"]) for c in checks] == [
        (e, m) for e in ("NFC", "NFD") for m in ("raw", "headword", "compatible")
    ]
    for check in checks:
        assert check["exported_records"] == check["cli_records"]
        assert check["records"] == len(check["exported_records"]) == 5
        assert "".join(
            r["surface"] for r in check["exported_records"]
        ) == unicodedata.normalize(check["encoding"], text)
        if check["mode"] == "raw":
            api = next(
                r["response"] for r in responses if r["encoding"] == check["encoding"]
            )
            assert check["exported_records"] == api["records"]
    assert [(d["encoding"], d["word"]) for d in diagrams] == [
        (e, w) for e in ("NFC", "NFD") for w, _ in selected
    ]
    forms = {f["base"]: f for f in fixture["formations"]}
    for d in diagrams:
        api = next(r["response"] for r in responses if r["encoding"] == d["encoding"])
        base = dict(selected)[d["word"]]
        f = forms[base]
        record = next(
            r
            for r in api["records"]
            if (r.get("analysis") or {}).get("normalized") == d["word"]
        )
        index = next(
            i
            for i, a in enumerate(record["analysis"]["analyses"])
            if a["lemmas"][0]["text"] == base and "suffix.verb.doeda" in a["rules"]
        )
        entry = next(
            e
            for e in record["dictionary"]["readings"][index]["lemmas"][0]["entries"]
            if e["id"] == f["noun_entries"][0]
        )
        assert (
            d["selected"] == index and d["identity"] == entry["derivational_identity"]
        )
        assert d["identity"] == {
            "relation": "unknown",
            "morpheme_index": 0,
            "expected_origins": [],
            "whole_entries": f["whole_entries"],
            "whole_origins_complete": False,
        }
        assert d["base"] == base and d["entry"] == f["noun_entries"][0]
        assert d["label"] == (api["glosses"][d["entry"]] or "No English gloss")
        assert "Dictionary hint only" in d["title"]
        assert d["parts"][0:2] == [base, "되"]
        whole = record["analysis"]["analyses"][d["whole_selected"]]
        assert whole["lemmas"][0] == {"text": f["head"], "kind": "predicate"}
        assert d["whole_form"] == f["head"][:-1]
    assert browser["browser_errors"] == []
    return {
        "api_words": runtime["words_checked"],
        "native_entries": len(runtime["native_entries"]),
        "browser_exports": len(checks),
        "browser_diagrams": len(diagrams),
    }


def inspect(report):
    result = inspect_evidence(report)
    diagnostic = read(DIAGNOSTICS)
    runtime = report["runtime"]
    assert report["implementation_files"] == diagnostic["implementation_files"]
    for snap in [
        *report["implementation_files"].values(),
        *report["frontend_sources"].values(),
        report["nix_log"],
        runtime["producer"],
        report["browser_producer"],
    ]:
        assert digest(snap["text"]) == snap["sha256"]
    log = report["nix_log"]["text"]
    counts = re.findall(
        r"klem> test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log
    )
    assert report["rust_passed"] == sum(int(p) for p, _ in counts) == 899
    assert report["rust_ignored"] == sum(int(i) for _, i in counts) == 1
    assert report["rust_batches"] == len(counts) == 195
    assert report["nix_exit_code"] == 0
    assert report["desktop_inspected"] and report["mobile_inspected"]
    assert set(report["screenshots"]) == {"desktop", "mobile"}
    assert report["asset_files_sha256"]
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", v) for v in report["asset_files_sha256"].values()
    )
    for package in ("klem", "web-assets", "inventory-review"):
        assert report["nix_outputs"][package] in log
    return {"rust_passed": report["rust_passed"], **result}


def freeze(args):
    assert not REPORT.exists()
    runtime, browser = read(args.runtime), read(args.browser)
    log = args.nix_log.read_text()
    counts = re.findall(
        r"klem> test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log
    )
    producer = ROOT / "web/tests/doeda-originless.mjs"
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(PREFLIGHT),
        "diagnostics_sha256": sha(DIAGNOSTICS),
        "fixture_sha256": sha(FIXTURE),
        "cli_sha256": runtime["cli_sha256"],
        "dictionary_sha256": runtime["dictionary_sha256"],
        "runtime": runtime,
        "browser": browser,
        "nix_log": {"text": log, "sha256": sha(args.nix_log)},
        "nix_exit_code": args.nix_exit_code,
        "nix_outputs": {
            "klem": str(args.klem),
            "web-assets": str(args.assets),
            "inventory-review": str(args.inventory),
        },
        "rust_passed": sum(int(p) for p, _ in counts),
        "rust_ignored": sum(int(i) for _, i in counts),
        "rust_batches": len(counts),
        "implementation_files": {
            p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)}
            for p in read(DIAGNOSTICS)["implementation_files"]
        },
        "browser_producer": {"text": producer.read_text(), "sha256": sha(producer)},
        "desktop_inspected": args.desktop_inspected,
        "mobile_inspected": args.mobile_inspected,
        "asset_files_sha256": {
            str(p.relative_to(args.assets / "share/klem-web")): sha(p)
            for p in sorted((args.assets / "share/klem-web").rglob("*"))
            if p.is_file()
        },
        "frontend_sources": {
            str(p.relative_to(ROOT)): {"text": p.read_text(), "sha256": sha(p)}
            for p in sorted((ROOT / "web/src").rglob("*"))
            if p.is_file()
        },
        "screenshots": {
            name: {"sha256": sha(Path("/tmp/klem-doeda-originless-" + name + ".png"))}
            for name in ("desktop", "mobile")
        },
        "scope": "Complete finite semantic source API cohort in NFC/NFD, ordinary noun controls, release/debug parity, complete native endpoints, actual browser alternatives/source clicks and six exports. Broad/corpus/timing and contextual or independent review remain separate.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    assert sha(args.klem / "bin/klem") == report["cli_sha256"]
    print(inspect(report))
    write(REPORT, report)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--desktop-inspected", action="store_true")
    p.add_argument("--mobile-inspected", action="store_true")
    p.add_argument("--runtime", type=Path)
    p.add_argument("--browser", type=Path)
    p.add_argument("--nix-log", type=Path)
    p.add_argument("--nix-exit-code", type=int)
    p.add_argument("--klem", type=Path)
    p.add_argument("--assets", type=Path)
    p.add_argument("--inventory", type=Path)
    args = p.parse_args()
    if args.verify:
        print(inspect(read(REPORT)))
    else:
        freeze(args)
