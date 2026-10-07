"""Reconstruct every old/new legacy frame and verify its captured stream fingerprint."""

import copy
import hashlib
import json

from reported_dana_corpora import ROOT, read, reject, sha
from reported_dana_inputs import verify_frozen_inputs
from reported_dana_legacy import BASELINE, specifications
from reported_dana_parent import actual_parent, frame


def serialized(rows):
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )


def old_rows(spec, deoni, copula, production):
    family, encoding, mode = [spec[key] for key in ["family", "encoding", "mode"]]
    if family == "reported-deoni":
        text = deoni["runs"][encoding][mode]["after"]["jsonl"]
        assert (
            hashlib.sha256(text.encode()).hexdigest() == spec["expected_before_sha256"]
        )
        return [json.loads(line) for line in text.splitlines()]
    previous = copula["reports"][family]["runs"][encoding][mode]
    rows = [json.loads(line) for line in previous["after_jsonl"].splitlines()]
    main = next(
        row
        for row in production["legacy_source_runs"]
        if (row["family"], row["encoding"], row["mode"]) == (family, encoding, mode)
    )
    assert previous["after_sha256"] == main["prior_stream_sha256"]
    for change in main["changed_frames"]:
        assert rows[change["record"]] == change["before"]
        rows[change["record"]] = change["after"]
    assert (
        hashlib.sha256(serialized(rows).encode()).hexdigest()
        == main["sha256"]
        == spec["expected_before_sha256"]
    )
    return rows


def verify(report):
    assert report["state"] == "passed" and report["inputs_unchanged"]
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    for name, value in report["frozen_inputs"].items():
        assert sha(name) == value
    source = read("docs/reported-dana-prototype-source-streams.json.gz")
    assert report["binaries"][str(BASELINE)] == source["frozen_inputs"][str(BASELINE)]
    candidate = "/home/josh/projects/klem/web/test-results/reported-dana-prototype-cargo/debug/klem"
    bridge = json.loads(
        (ROOT / "docs/reported-dana-rebuilt-prototype-production.json").read_bytes()
    )
    assert bridge["state"] == "passed" and bridge["inputs_unchanged"]
    assert report["binaries"][candidate] == bridge["binaries"][candidate]
    verify_frozen_inputs(bridge["frozen_inputs"])
    assert (
        hashlib.sha256(bridge["producer"]["text"].encode()).hexdigest()
        == bridge["producer"]["sha256"]
    )
    expected_sources = [
        (encoding, mode, stages["after"])
        for encoding, modes in source["runs"].items()
        for mode, stages in modes.items()
    ]
    assert len(bridge["source_runs"]) == len(expected_sources) == 6
    for actual, (encoding, mode, original) in zip(
        bridge["source_runs"], expected_sources, strict=True
    ):
        assert (actual["encoding"], actual["mode"]) == (encoding, mode)
        assert actual["exit_code"] == 0 and actual["sha256"] == original["sha256"]
        assert actual["records"] == len(original["jsonl"].splitlines())
        assert actual["command"] == [candidate, *original["command"][1:]]
    broad = read("docs/reported-dana-prototype-broad.json.gz")
    assert len(bridge["broad_runs"]) == len(broad["comparisons"]) == 8
    for actual, original in zip(
        bridge["broad_runs"], broad["comparisons"], strict=True
    ):
        assert all(
            actual[key] == original[key]
            for key in ["source", "source_sha256", "mode", "records"]
        )
        assert (
            actual["exit_code"] == 0
            and actual["sha256"] == original["after_jsonl_sha256"]
        )
        assert actual["command"] == [candidate, *original["commands"][1][1:]]
    corpus = read("docs/reported-dana-prototype-corpora.json.gz")
    assert bridge["corpus_words"] == len(corpus["after_words"]) == 32096
    assert bridge["corpus_word_sha256"] == corpus["after_word_sha256"]
    assert len(bridge["evaluator_runs"]) == len(corpus["corpora"]) == 4
    for actual, original in zip(
        bridge["evaluator_runs"], corpus["corpora"], strict=True
    ):
        assert (
            actual["exit_code"] == 0 and actual["records"] == original["report_lines"]
        )
        assert (
            actual["sha256"]
            == hashlib.sha256(original["after_jsonl"].encode()).hexdigest()
        )
        assert actual["command"][1:] == [original["corpus"], original["source"]]
    dictionary = "/tmp/klem-reported-dana-prototype/data/dictionaries/krdict/krdict.db"
    assert (
        report["binaries"][dictionary]
        == source["frozen_inputs"][
            "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"
        ]
    )
    specs, _ = specifications()
    deoni = read("docs/reported-deoni-prototype-source-streams.json.gz")
    copula = read("docs/copula-expectation-source-streams.json.gz")
    production = json.loads(
        (ROOT / "docs/reported-deoni-main-production.json").read_bytes()
    )
    assert production["frozen_inputs"][
        "docs/copula-expectation-source-streams.json.gz"
    ] == sha("docs/copula-expectation-source-streams.json.gz")
    native = read("docs/reported-dana-observation-native.json.gz")[
        "complete_native_entries"
    ]
    assert len(report["comparisons"]) == len(specs) == 18
    parents = report["actual_prior_companions"]
    expected = []
    needed = set()
    total = 0
    for run, spec in zip(report["comparisons"], specs, strict=True):
        assert all(
            run[key] == spec[key] for key in ["family", "encoding", "mode", "records"]
        )
        assert run["commands"] == [
            [binary, *spec["arguments"]] for binary in [str(BASELINE), candidate]
        ]
        assert run["exit_codes"] == [0, 0] and run["original_bytes_conserved"]
        raw = spec["input"].encode()
        assert hashlib.sha256(raw).hexdigest() == run["input_sha256"]
        before = old_rows(spec, deoni, copula, production)
        assert len(before) == run["records"]
        assert (
            hashlib.sha256(serialized(before).encode()).hexdigest()
            == run["before_sha256"]
            == spec["expected_before_sha256"]
        )
        last = 0
        for changed in run["changed_frames"]:
            record = changed["record"]
            assert last < record <= len(before)
            last = record
            assert before[record - 1] == changed["before"]
            after = changed["after"]
            additions = frame(changed["before"], after, parents)
            assert additions
            for path in additions:
                parent_surface, parent = actual_parent(
                    after["analysis"]["normalized"], path, parents
                )
                assessment = after["dictionary"]["readings"][
                    after["analysis"]["analyses"].index(path)
                ]
                owners = sorted(
                    {
                        owner["id"]
                        for lemma in assessment["lemmas"]
                        for owner in lemma["entries"]
                    }
                )
                assert set(owners) <= set(native)
                needed.update(owners)
                identity = [
                    spec["family"],
                    spec["encoding"],
                    spec["mode"],
                    record,
                    path,
                ]
                ident = hashlib.sha256(
                    json.dumps(identity, ensure_ascii=False, sort_keys=True).encode()
                ).hexdigest()[:24]
                expected.append(
                    {
                        "id": "reported-dana-legacy-" + ident,
                        "family": spec["family"],
                        "encoding": spec["encoding"],
                        "mode": spec["mode"],
                        "record": record,
                        "surface": after["surface"],
                        "normalized": after["analysis"]["normalized"],
                        "span": after["span"],
                        "analysis": path,
                        "dictionary_assessment": assessment,
                        "native_entry_ids": owners,
                        "parent_surface": parent_surface,
                        "exact_parent": parent,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
            before[record - 1] = after
        offset = 0
        for row in before:
            span = row["span"]
            assert (
                span["start"] == offset
                and raw[span["start"] : span["end"]].decode() == row["surface"]
            )
            offset = span["end"]
        assert offset == len(raw)
        assert (
            hashlib.sha256(serialized(before).encode()).hexdigest()
            == run["after_sha256"]
        )
        total += len(before)
    assert report["individual_additions"] == expected
    assert len(expected) == len({row["id"] for row in expected}) == 20
    assert report["observed_native_ids"] == sorted(needed)
    assert total == 688434
    return total, len(expected), len(needed)


if __name__ == "__main__":
    report = read("docs/reported-dana-prototype-legacy.json.gz")
    print(
        "Verified complete original/new legacy streams, exact old parents and Native owner closure:",
        verify(report),
        flush=True,
    )
    changed = copy.deepcopy(report)
    changed["individual_additions"].pop()
    reject(lambda: verify(changed), "missing individual legacy observation")
    changed = copy.deepcopy(report)
    changed["comparisons"][0]["after_sha256"] = "0" * 64
    reject(lambda: verify(changed), "altered full new stream fingerprint")
    changed = copy.deepcopy(report)
    changed["individual_additions"][0]["contextual_verdict"] = "correct"
    reject(lambda: verify(changed), "invented contextual certification")
    changed = copy.deepcopy(report)
    row = next(r for r in changed["comparisons"] if r["changed_frames"])
    row["changed_frames"][0]["after"]["dictionary"]["readings"][0]["lemmas"][0][
        "status"
    ] = "fabricated"
    reject(lambda: verify(changed), "changed existing dictionary reading")
