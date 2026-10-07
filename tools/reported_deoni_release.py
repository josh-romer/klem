"""Offline verification of actual packaged build, CLI and complete browser parity."""

import base64, hashlib, json, re
from copula_expectation_production import ROOT, read, sha


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def verify_build(receipt, archive, rust, formatting, sources, log):
    assert (
        receipt["state"] == "passed"
        and receipt["exit_code"] == 0
        and receipt["snapshot_unchanged"]
    )
    assert digest(log) == receipt["log_sha256"]
    batches = re.findall(
        r"test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log
    )
    assert (
        sum(int(n) for n, i in batches),
        sum(int(i) for n, i in batches),
        len(batches),
    ) == (1000, 1, 211)
    assert "FAILED" not in log and "error:" not in log
    assert sources["package"] in receipt["outputs"]
    assert digest(sources["derivation_json_text"]) == sources["derivation_json_sha256"]
    assert json.loads(sources["derivation_json_text"]) == sources["derivation_json"]
    assert set(sources["derivation_json"]) == {sources["derivation"]}
    drv = sources["derivation_json"][sources["derivation"]]
    assert (
        drv["env"]["src"] == sources["source"]
        and drv["outputs"]["out"]["path"] == sources["package"]
    )
    assert set(sources["files"]) == set(archive["files"]) == set(rust["frozen_inputs"])
    assert len(sources["files"]) == 661
    assert set(formatting["files"]) == {
        "tests/counterfactual_ryeon.rs",
        "tests/degree_rimankeum.rs",
    }
    old = '#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;\n#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;'
    new = '#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;\n#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;'
    for path, original in archive["files"].items():
        text = original["text"]
        before = digest(text)
        assert before == original["sha256"] == rust["frozen_inputs"][path]
        source = sources["files"][path]
        assert source["full_rust_input_sha256"] == before
        assert source["formatting_only"] == (path in formatting["files"])
        if path in formatting["files"]:
            assert (
                text.count(old) == 1
                and formatting["files"][path]["before_sha256"] == before
            )
            text = text.replace(old, new)
            assert digest(text) == formatting["files"][path]["after_sha256"]
        assert source["sha256"] == digest(text) and source["bytes"] == len(
            text.encode()
        )
        if path in receipt["snapshot"]["files"]:
            assert receipt["snapshot"]["files"][path]["sha256"] == source["sha256"]


def verify_cli(report, main, corpus, cli):
    assert (
        report["state"] == "passed"
        and report["inputs_unchanged"]
        and report["prototype_parity"]
    )
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    for field, key_fields, count, total in [
        ("source_runs", ["encoding", "mode", "input_sha256"], 6, 378774),
        ("broad_runs", ["source", "source_sha256", "mode"], 8, 1128312),
        (
            "legacy_source_runs",
            ["family", "encoding", "mode", "input_sha256", "prior_stream_sha256"],
            12,
            309660,
        ),
    ]:
        assert len(report[field]) == len(main[field]) == count
        assert sum(row["records"] for row in report[field]) == total
        for actual, old in zip(report[field], main[field], strict=True):
            assert all(actual[key] == old[key] for key in key_fields)
            assert (
                actual["command"] == [cli, *old["command"][1:]]
                and actual["exit_code"] == 0
            )
            assert actual["sha256"] == actual["expected_sha256"] == old["sha256"]
            assert actual["records"] == old["records"]
    assert "corpus_runs" not in report
    assert report["corpus_validation"] == {
        "method": "Exact packaged CLI WordAnalysis equality for every original gold surface, tied to the independently verified evaluator results; no packaged evaluator executable is claimed.",
        "verified_gold_rows": 66570,
    }
    assert len(report["corpus_reference_runs"]) == len(corpus["corpora"]) == 4
    for actual, old in zip(
        report["corpus_reference_runs"], corpus["corpora"], strict=True
    ):
        assert all(
            actual[key] == old[key]
            for key in [
                "corpus",
                "partition",
                "source",
                "source_sha256",
                "report_lines",
            ]
        )
        assert actual["reference_evaluator_jsonl_sha256"] == digest(old["after_jsonl"])
    assert (
        sum(row["report_lines"] - 1 for row in report["corpus_reference_runs"]) == 66570
    )
    assert report["corpus_words"] == len(corpus["after_words"]) == 32096
    expected = digest(
        json.dumps(corpus["after_words"], ensure_ascii=False, sort_keys=True)
    )
    assert report["corpus_word_sha256"] == main["corpus_word_sha256"] == expected


def verify_browser(actual, main, closure):
    assert (
        actual["state"] == "passed"
        and actual["exit_code"] == 0
        and actual["owned_preview_stopped"]
    )
    assert actual["prior_diagrams_verified"] == 146
    assert digest(actual["producer"]["text"]) == actual["producer"]["sha256"]
    current, old = actual["browser"], main["browser"]
    for field in ["diagrams", "records", "native", "errors"]:
        assert current[field] == old[field], field
    assert (
        len(current["diagrams"]) == 148
        and len(current["records"]) == 6
        and len(current["native"]) == 167
    )
    assert (
        current["errors"] == []
        and len(current["responses"]) == len(old["responses"]) == 2
    )
    for response, previous in zip(current["responses"], old["responses"], strict=True):
        assert (
            response["encoding"] == previous["encoding"]
            and response["request"] == previous["request"]
        )
        assert {k: v for k, v in response["response"].items() if k != "elapsed_ms"} == {
            k: v for k, v in previous["response"].items() if k != "elapsed_ms"
        }
    assert {r["id"]: r["response"]["entry"] for r in current["native"]} == closure[
        "complete_native_entries"
    ]
    assert set(actual["screenshots"]) == {"desktop", "mobile"}
    for image in actual["screenshots"].values():
        raw = base64.b64decode(image["base64"], validate=True)
        assert (
            raw.startswith(b"\x89PNG\r\n\x1a\n")
            and hashlib.sha256(raw).hexdigest() == image["sha256"]
        )


def inspect():
    from reported_deoni_complete_sources import inspect as inspect_complete_sources

    complete_sources = inspect_complete_sources()
    package = read("docs/reported-deoni-packaged-checks.json")
    receipt = read("docs/reported-deoni-package-nix.json")
    sources = read("docs/reported-deoni-package-sources.json")
    archive = read("docs/reported-deoni-main-rust-sources.json.gz")
    rust = read("docs/reported-deoni-main-rust.json")
    formatting = read("docs/reported-deoni-main-formatting.json")
    import gzip

    log = gzip.decompress(
        (ROOT / "docs/reported-deoni-package-nix.log.gz").read_bytes()
    ).decode()
    verify_build(receipt, archive, rust, formatting, sources, log)
    assert sources["package"] == package["nix_outputs"]["klem"]
    assert set(receipt["outputs"]) == set(package["nix_outputs"].values())
    assert sources["package_receipt_sha256"] == sha(
        ROOT / "docs/reported-deoni-package-nix.json"
    )
    assert sources["full_rust_archive_sha256"] == sha(
        ROOT / "docs/reported-deoni-main-rust-sources.json.gz"
    )
    assert sources["formatting_receipt_sha256"] == sha(
        ROOT / "docs/reported-deoni-main-formatting.json"
    )
    assert archive["rust_receipt_sha256"] == sha(
        ROOT / "docs/reported-deoni-main-rust.json"
    )
    for path, expected in package["capture_sha256"].items():
        assert sha(ROOT / path) == expected
    cli = package["nix_outputs"]["klem"] + "/bin/klem"
    production = read("docs/reported-deoni-packaged-production.json")
    assert production["nix_outputs"] == package["nix_outputs"]
    assert production["package_receipt_sha256"] == sha(
        ROOT / "docs/reported-deoni-package-nix.json"
    )
    assert production["binaries"][cli] == package["cli_sha256"]
    for path, expected in production["frozen_inputs"].items():
        assert sha(ROOT / path) == expected
    verify_cli(
        production,
        read("docs/reported-deoni-main-production.json"),
        read("docs/reported-deoni-prototype-corpora.json.gz"),
        cli,
    )
    browser = read("docs/reported-deoni-packaged-browser.json.gz")
    assert (
        browser["cli_sha256"] == package["cli_sha256"]
        and browser["web_sha256"] == package["web_sha256"]
    )
    assert browser["native_source_sha256"] == sha(
        ROOT / "docs/reported-deoni-observation-native.json.gz"
    )
    verify_browser(
        browser,
        read("docs/reported-deoni-main-browser.json.gz"),
        read("docs/reported-deoni-observation-native.json.gz"),
    )
    return {
        "package_source_files": complete_sources["files"],
        "rust_passed": 1000,
        "source_frames": 378774,
        "legacy_source_frames": 309660,
        "gold_rows": 66570,
        "broad_frames": 1128312,
        "diagrams": 148,
        "native_entries": 167,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified actual packaged reported-ending release:", inspect())
