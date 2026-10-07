"""Verify actual main/package identity and complete packaged CLI/browser parity."""

import gzip
import hashlib
import json
import re
import unicodedata

from copula_expectation_production import ROOT, read, sha
from reported_dana_inputs import verify_frozen_inputs
from reported_dana_legacy import specifications
from reported_dana_sources import inspect as verify_sources


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def verify_build(receipt, log):
    assert receipt["state"] == "passed" and receipt["exit_code"] == 0
    assert receipt["snapshot_unchanged"]
    assert digest(log) == receipt["log_sha256"]
    batches = re.findall(
        r"test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log
    )
    assert (
        sum(int(n) for n, i in batches),
        sum(int(i) for n, i in batches),
        len(batches),
    ) == (1005, 1, 212)
    for line in log.splitlines():
        assert "FAILED" not in line
        if "error:" in line:
            # These are substituter warnings followed by a successful local build.
            assert re.fullmatch(
                r"warning: error: unable to download 'https://attic\.xuyh0120\.win/lantian/"
                r"[a-z0-9]+\.narinfo': [^\n]+ \(curl error code=28\); "
                r"retrying in \d+ ms \(attempt \d+/5\)",
                line,
            )


def verify_legacy(report, previous, cli, cli_sha256, dictionary_sha256):
    assert report["state"] == "passed" and report["inputs_unchanged"]
    assert report["cli"] == cli and report["cli_sha256"] == cli_sha256
    assert report["dictionary_sha256"] == dictionary_sha256
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    for name, expected in report["frozen_inputs"].items():
        assert sha(ROOT / name) == expected
    specs, _ = specifications()
    assert len(report["runs"]) == len(previous["comparisons"]) == len(specs) == 18
    for run, old, spec in zip(
        report["runs"], previous["comparisons"], specs, strict=True
    ):
        assert all(
            run[key] == old[key]
            for key in ["family", "encoding", "mode", "input_sha256", "records"]
        )
        assert run["command"] == [cli, *spec["arguments"]]
        assert run["exit_code"] == 0 and run["sha256"] == old["after_sha256"]
    assert sum(run["records"] for run in report["runs"]) == 688434


def verify_binding(binding, sources, receipt):
    assert binding["state"] == receipt["state"] == "passed"
    assert binding["exit_code"] == receipt["exit_code"] == 0
    assert (
        set(binding["outputs"]) == set(receipt["outputs"])
        and len(binding["outputs"]) == 2
    )
    assert binding["source"] == sources["source"]
    assert binding["files"] == sources["files"] and len(binding["files"]) == 859


def verify_cli(report, source, broad, corpus, cli):
    assert report["state"] == "passed" and report["inputs_unchanged"]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    expected = [
        (encoding, mode, stage["after"])
        for encoding, modes in source["runs"].items()
        for mode, stage in modes.items()
    ]
    assert len(report["source_runs"]) == len(expected) == 6
    for run, (encoding, mode, original) in zip(
        report["source_runs"], expected, strict=True
    ):
        assert (run["encoding"], run["mode"]) == (encoding, mode)
        request = unicodedata.normalize(encoding, source["input"])
        assert run["input_sha256"] == digest(request)
        assert run["command"] == [cli, *original["command"][1:]]
        assert run["exit_code"] == 0 and run["sha256"] == original["sha256"]
        assert run["records"] == len(original["jsonl"].splitlines())
    assert sum(run["records"] for run in report["source_runs"]) == 247698
    assert len(report["broad_runs"]) == len(broad["comparisons"]) == 8
    for run, original in zip(report["broad_runs"], broad["comparisons"], strict=True):
        assert all(
            run[key] == original[key]
            for key in ["source", "source_sha256", "mode", "records"]
        )
        assert run["command"] == [cli, *original["commands"][1][1:]]
        assert run["exit_code"] == 0 and run["sha256"] == original["after_jsonl_sha256"]
    assert sum(run["records"] for run in report["broad_runs"]) == 1128312
    assert report["corpus_words"] == len(corpus["after_words"]) == 32096
    assert (
        report["corpus_word_sha256"]
        == corpus["after_word_sha256"]
        == digest(json.dumps(corpus["after_words"], ensure_ascii=False, sort_keys=True))
    )
    assert report["evaluator_runs"] == []
    assert report["corpus_validation"] == {
        "method": "Exact CLI WordAnalysis equality for every original gold surface, tied to independently verified captured evaluator results; no evaluator execution claimed.",
        "verified_gold_rows": 66570,
    }
    assert len(report["corpus_reference_runs"]) == len(corpus["corpora"]) == 4
    for run, old in zip(
        report["corpus_reference_runs"], corpus["corpora"], strict=True
    ):
        assert all(
            run[key] == old[key]
            for key in [
                "corpus",
                "partition",
                "source",
                "source_sha256",
                "report_lines",
            ]
        )
        assert run["reference_evaluator_jsonl_sha256"] == digest(old["after_jsonl"])


def verify_browser(actual, previous, closure):
    assert (
        actual["state"] == "passed"
        and actual["exit_code"] == 0
        and actual["owned_preview_stopped"]
    )
    current, old = actual["browser"], previous["browser"]
    for key in ["diagrams", "records", "native", "errors"]:
        assert current[key] == old[key]
    assert (
        len(current["diagrams"]) == 220
        and len(current["native"]) == 208
        and len(current["records"]) == 6
    )
    assert actual["prior_diagrams_verified"] == 148 and current["errors"] == []
    assert len(current["responses"]) == len(old["responses"]) == 2
    for response, original in zip(current["responses"], old["responses"], strict=True):
        assert (
            response["encoding"] == original["encoding"]
            and response["request"] == original["request"]
        )
        assert {k: v for k, v in response["response"].items() if k != "elapsed_ms"} == {
            k: v for k, v in original["response"].items() if k != "elapsed_ms"
        }
    assert {
        row["id"]: row["response"]["entry"] for row in current["native"]
    } == closure["complete_native_entries"]


def inspect():
    source_result = verify_sources()
    package = read("docs/reported-dana-packaged-checks.json")
    for name, expected in package["captures"].items():
        assert sha(ROOT / name) == expected
    sources = read("docs/reported-dana-package-sources.json")
    receipt = read("docs/reported-dana-package-nix.json")
    log = gzip.decompress(
        (ROOT / "docs/reported-dana-package-nix.log.gz").read_bytes()
    ).decode()
    verify_build(receipt, log)
    binding = read("docs/reported-dana-main-package-binding.json")
    assert binding["package_source_receipt_sha256"] == sha(
        ROOT / "docs/reported-dana-package-sources.json"
    )
    assert (
        digest(
            gzip.decompress(
                (ROOT / "docs/reported-dana-main-package-binding.log.gz").read_bytes()
            ).decode()
        )
        == binding["log_sha256"]
    )
    verify_binding(binding, sources, receipt)
    cli = package["nix_outputs"]["klem"] + "/bin/klem"
    assert package["nix_outputs"]["klem"] == sources["package"]
    production = read("docs/reported-dana-packaged-production.json")
    verify_frozen_inputs(production["frozen_inputs"])
    verify_cli(
        production,
        read("docs/reported-dana-prototype-source-streams.json.gz"),
        read("docs/reported-dana-prototype-broad.json.gz"),
        read("docs/reported-dana-prototype-corpora.json.gz"),
        cli,
    )
    browser = read("docs/reported-dana-packaged-browser.json.gz")
    assert browser["cli_sha256"] == production["binaries"][cli]
    assert browser["command"][0] == package["nix_outputs"]["klem"] + "/bin/klem-web"
    assert (
        browser["command"][2]
        == package["nix_outputs"]["web-assets"] + "/share/klem-web"
    )
    assert browser["native_source_sha256"] == sha(
        ROOT / "docs/reported-dana-browser-native.json.gz"
    )
    verify_browser(
        browser,
        read("docs/reported-dana-prototype-browser-focused.json.gz"),
        read("docs/reported-dana-browser-native.json.gz"),
    )
    verify_legacy(
        read("docs/reported-dana-packaged-legacy.json"),
        read("docs/reported-dana-prototype-legacy.json.gz"),
        cli,
        production["binaries"][cli],
        read("docs/reported-dana-prototype-source-streams.json.gz")["frozen_inputs"][
            "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"
        ],
    )
    return {
        "source_files": source_result["source_files"],
        "rust_passed": 1005,
        "source_frames": 247698,
        "broad_frames": 1128312,
        "gold_rows": 66570,
        "diagrams": 220,
        "native_entries": 208,
        "legacy_frames": 688434,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified actual integrated-source packaged release:", inspect())
