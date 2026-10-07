"""Verify actual Nix receipts, all source API orders and release stream parity."""
import argparse
import base64
import hashlib
import math
import re
from pathlib import Path

from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/friendly-command-packaged-checks.json.gz"


def semantic(response):
    elapsed = response["elapsed_ms"]
    assert isinstance(elapsed, (int, float)) and math.isfinite(elapsed) and elapsed >= 0
    return {k: v for k, v in response.items() if k != "elapsed_ms"}


def inspect(report):
    source_path = ROOT / "docs/friendly-command-preflight.json.gz"
    diagnostic_path = ROOT / "docs/friendly-command-diagnostics.json.gz"
    source, diagnostic = read(source_path), read(diagnostic_path)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bx"
    assert report["source_sha256"] == sha(source_path)
    assert report["diagnostics_sha256"] == sha(diagnostic_path)
    frozen_api_path = ROOT / "docs/friendly-command-api.json.gz"
    assert report["frozen_api_sha256"] == sha(frozen_api_path)
    frozen_api = read(frozen_api_path)
    assert report["dictionary_sha256"] == diagnostic["dictionary_sha256"]
    assert report["cli_sha256"] != diagnostic["cli_sha256"]["after"]
    log = report["nix_log"]
    assert log["exit_code"] == 0 and sha_text(log["text"]) == log["sha256"]
    assert "FAILED" not in log["text"] and "error:" not in log["text"]
    counts = re.findall(r"klem> test result: ok\. (\d+) passed; 0 failed; (\d+) ignored;", log["text"])
    assert (sum(int(p) for p, i in counts), sum(int(i) for p, i in counts), len(counts)) == (964, 1, 206)
    assert set(report["nix_outputs"]) == {"klem", "web-assets"}
    for output in report["nix_outputs"].values():
        assert output.startswith("/nix/store/") and output in log["text"].splitlines()
    assert report["runs"].keys() == diagnostic["runs"].keys()
    for mode, runs in report["runs"].items():
        assert runs.keys() == diagnostic["runs"][mode].keys()
        for name, capture in runs.items():
            assert capture["exit_code"] == 0
            assert capture["jsonl"] == diagnostic["runs"][mode][name]["after"]["jsonl"]
            assert sha_text(capture["jsonl"]) == capture["sha256"]
            command = capture["command"]
            assert command[0] == report["nix_outputs"]["klem"] + "/bin/klem"
            assert command[1:4] == ["text", "-", "--dictionary"]
            assert command[4].endswith("/data/dictionaries/krdict/krdict.db")
            flags = [] if mode == "raw" else ["--dict-only"] if mode == "headword" else ["--dict-compatible"]
            assert command[5:] == flags + ["--cache-bytes", "8388608" if name.endswith("-cached") else "0"]
    import copy
    import json
    import unicodedata
    added, words = 0, 0
    batches = report["api_batches"]
    assert {b["encoding"] for b in batches} == {"NFC", "NFD"}
    assert [b["encoding"] for b in batches] == sorted(b["encoding"] for b in batches)
    for encoding in ["NFC", "NFD"]:
        text = unicodedata.normalize(encoding, source["input"])
        encoded = text.encode()
        original = [json.loads(line) for line in diagnostic["runs"]["raw"][encoding + "-cached"]["before"]["jsonl"].splitlines()]
        current = [json.loads(line) for line in report["runs"]["raw"][encoding + "-cached"]["jsonl"].splitlines()]
        next_record, next_byte = 0, 0
        for batch in [b for b in batches if b["encoding"] == encoding]:
            begin, end = batch["source_record_range"]
            span = batch["source_span"]
            assert begin == next_record and begin < end <= len(original)
            assert span == {"start": next_byte, "end": original[end - 1]["span"]["end"]}
            assert original[begin]["span"]["start"] == next_byte
            assert batch["request"] == {"text": encoded[span["start"]:span["end"]].decode()}
            assert len(batch["request"]["text"].encode()) <= 7000
            def relative(rows):
                result = copy.deepcopy(rows[begin:end])
                for row in result:
                    row["span"] = {key: value - span["start"] for key, value in row["span"].items()}
                return result
            before, after = batch["before"], batch["response"]
            frozen_before = next(b for b in frozen_api["runs"][encoding]["before"] if b["source_record_range"] == [begin, end])
            frozen_debug = next(b for b in frozen_api["runs"][encoding]["after"] if b["source_record_range"] == [begin, end])
            assert before == frozen_before["response"] and batch["debug"] == frozen_debug["response"]
            assert batch["request"] == frozen_before["request"] == frozen_debug["request"]
            assert semantic(after) == semantic(batch["debug"])
            assert before["records"] == relative(original)
            assert after["records"] == relative(current)
            assert len(after["breakdowns"]) == len(after["records"])
            for ordinal, (old, record) in enumerate(zip(before["records"], after["records"], strict=True)):
                if record["kind"] != "word":
                    continue
                words += 1
                old_paths = old["analysis"]["analyses"]
                paths, orders = record["analysis"]["analyses"], after["breakdowns"][ordinal]
                assert len(paths) == len(orders)
                for path, order in zip(paths, orders, strict=True):
                    if path in old_paths:
                        assert order == before["breakdowns"][ordinal][old_paths.index(path)]
                        continue
                    assert "ending.friendly_command.n" in path["rules"]
                    assert path["lemmas"][-1]["kind"] in {"predicate", "auxiliary"}
                    assert path["lemmas"][-1]["text"].endswith("오다")
                    assert order is not None
                    assert [c["lemma"] for c in order if "lemma" in c] == list(range(len(path["lemmas"])))
                    assert [c["morpheme"] for c in order if "morpheme" in c] == list(range(len(path["morphemes"])))
                    added += 1
            next_record, next_byte = end, span["end"]
        assert next_record == len(original) == len(current) and next_byte == len(encoded)
    assert added == report["added_orders"] == 1266
    browser, debug_browser = report["browser"], read(ROOT / "docs/friendly-command-browser.json.gz")
    assert browser["cli_sha256"] == report["cli_sha256"]
    for key in ["schema_version", "checklist", "dictionary_sha256", "fixture_sha256", "producer_sha256", "checks", "diagrams", "native", "browser_errors"]:
        assert browser[key] == debug_browser[key]
    assert len(browser["responses"]) == len(debug_browser["responses"]) == 2
    for actual, debug in zip(browser["responses"], debug_browser["responses"], strict=True):
        assert actual["encoding"] == debug["encoding"] and actual["request"] == debug["request"]
        assert semantic(actual["response"]) == semantic(debug["response"])
    assert set(report["screenshots"]) == {"desktop", "mobile"}
    for capture in report["screenshots"].values():
        raw = base64.b64decode(capture["base64"], validate=True)
        assert raw.startswith(b"\x89PNG\r\n\x1a\n") and hashlib.sha256(raw).hexdigest() == capture["sha256"]
    assert sha_text(report["producer"]["text"]) == report["producer"]["sha256"]
    assert sha_text(report["finalizer"]["text"]) == report["finalizer"]["sha256"]
    return words, added, len(browser["diagrams"])


def sha_text(value):
    return hashlib.sha256(value.encode()).hexdigest()


def inspect_streams(package, broad, corpora):
    for actual, path, fields in [
        (broad, "docs/friendly-command-observations.json.gz", ["comparisons", "changed_record_pairs", "candidate_changes", "spacing_component_changes"]),
        (corpora, "docs/friendly-command-corpora.json.gz", ["after_words", "corpora", "changed_words", "candidate_changes", "after_word_stream_sha256"]),
    ]:
        debug = read(ROOT / path)
        assert actual["cli_sha256"] == package["cli_sha256"]
        assert actual["before_cli_sha256"] == debug["before_cli_sha256"]
        for field in fields:
            assert actual[field] == debug[field], field
    assert broad["dictionary_sha256"] == package["dictionary_sha256"]
    return 1128312, 66570, 32096


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    report = read(args.report)
    print("Verified packaged source API words, added orders and browser diagrams:", inspect(report))
    print("Verified independent release CLI broad/corpus parity:", inspect_streams(
        report, read(ROOT / "docs/friendly-command-packaged-observations.json.gz"), read(ROOT / "docs/friendly-command-packaged-corpora.json.gz")))
