"""Verify complete primary provenance and every matched source owner offline."""

import copy
import gzip
import hashlib
import json
import re
from pathlib import Path
from native_lmf import entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    path = ROOT / name
    return json.loads(
        gzip.decompress(path.read_bytes())
        if path.suffix == ".gz"
        else path.read_bytes()
    )


def sha(name):
    return hashlib.sha256((ROOT / name).read_bytes()).hexdigest()


def projection(report):
    assert set(report["original_lmf"]) == set(report["complete_native_entries"])
    assert {
        ident: entry(raw) for ident, raw in report["original_lmf"].items()
    } == report["complete_native_entries"]
    verify_native_lmf(report["english_projection"], report["complete_native_entries"])
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )


def primary(report):
    projection(report)
    assert (
        report["preparation_only"]
        and report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    assert (
        set(report["primary_entry_ids"])
        == set(report["complete_native_entries"])
        == {"krdict:74691", "krdict:74697", "krdict:74698"}
    )
    native = report["complete_native_entries"]
    groups = [
        {
            "source_entry": ident,
            "source_sense": sense["id"],
            "example_index": i,
            "original_group": group,
        }
        for ident in sorted(native)
        for sense in native[ident]["senses"]
        for i, group in enumerate(sense["examples"])
    ]
    assert groups == report["all_original_groups"] and len(groups) == 28
    expected = []
    for group in groups:
        for i, text in enumerate(group["original_group"]):
            for match in re.finditer(r"[가-힣]+다나(?![가-힣])", text):
                expected.append(
                    {
                        **group,
                        "text_index": i,
                        "surface": match[0],
                        "character_span": [match.start(), match.end()],
                    }
                )
    observations = report["literal_observations"]
    assert len(observations) == len(expected) == 31
    mismatches = []
    for row, original in zip(observations, expected, strict=True):
        assert all(row[key] == value for key, value in original.items())
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["target_form_present"] is False
        )
        word = row["surface"]
        companion = word[:-1] + "고"
        assert row["actual_companion"] == companion
        before = report["actual_cli_captures"][word]
        parent = report["actual_cli_captures"][companion]
        for surface, capture in [(word, before), (companion, parent)]:
            assert json.loads(capture["json"]) == capture["response"]
            assert capture["response"]["normalized"] == surface
            assert capture["command"][1:] == ["word", surface]
        assert row["existing_analysis"] == before["response"]
        own_form = "다고" if row["source_entry"] == "krdict:74698" else "는다고"
        own = [
            p
            for p in parent["response"]["analyses"]
            if p["morphemes"]
            and p["morphemes"][-1] == {"form": own_form, "kind": "ending"}
        ]
        all_paths = [
            p
            for p in parent["response"]["analyses"]
            if p["morphemes"]
            and p["morphemes"][-1]
            in [
                {"form": "다고", "kind": "ending"},
                {"form": "는다고", "kind": "ending"},
            ]
        ]
        assert (
            row["actual_companion_paths"] == own
            and row["all_statement_report_companion_paths"] == all_paths
            and all_paths
        )
        if not own:
            mismatches.append(word)
    assert report["source_group_allomorph_mismatches"] == mismatches == ["어쨌다나"]
    return len(groups), len(observations)


def closure(initial, source, broad, corpus, actual):
    projection(initial)
    projection(actual)
    assert (
        actual["inputs_unchanged"]
        and actual["source_hashes"] == initial["source_hashes"]
    )
    needed = set(initial["complete_native_entries"])
    assert initial["complete_native_entries"] == source["complete_native_entries"]
    for row in source["individual_additions"]:
        for occurrence in row["occurrences"]:
            for lemma in occurrence["dictionary_assessment"]["lemmas"]:
                needed.update(owner["id"] for owner in lemma["entries"])
    assert broad["individual_additions"] == [] and corpus["changed_words"] == {}
    assert actual["corpus_dictionary_calls"] == []
    assert set(actual["complete_native_entries"]) == needed and len(needed) == 85
    assert actual["additional_to_required_closure"] == sorted(
        needed - set(initial["complete_native_entries"])
    )
    for ident, value in initial["complete_native_entries"].items():
        assert actual["complete_native_entries"][ident] == value
    for original, archived in [
        (
            "/tmp/klem-reported-dana-native-preparation.json.gz",
            "docs/reported-dana-native-preparation.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-source-streams.json.gz",
            "docs/reported-dana-prototype-source-streams.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-broad.json.gz",
            "docs/reported-dana-prototype-broad.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-corpora.json.gz",
            "docs/reported-dana-prototype-corpora.json.gz",
        ),
    ]:
        assert actual["frozen_inputs"][original] == sha(archived)
    return len(needed)


def rejected(action, label):
    try:
        action()
    except (AssertionError, KeyError):
        print("Rejected corruption:", label)
        return
    raise AssertionError("Accepted corruption: " + label)


if __name__ == "__main__":
    preparation = read("docs/reported-dana-source-preparation.json.gz")
    initial = read("docs/reported-dana-native-preparation.json.gz")
    source = read("docs/reported-dana-prototype-source-streams.json.gz")
    broad = read("docs/reported-dana-prototype-broad.json.gz")
    corpus = read("docs/reported-dana-prototype-corpora.json.gz")
    actual = read("docs/reported-dana-observation-native.json.gz")
    print(
        "Verified primary provenance:",
        primary(preparation),
        "; complete observation owners:",
        closure(initial, source, broad, corpus, actual),
    )
    changed = copy.deepcopy(preparation)
    changed["all_original_groups"].pop()
    rejected(lambda: primary(changed), "missing original primary example group")
    changed = copy.deepcopy(preparation)
    changed["source_group_allomorph_mismatches"] = []
    rejected(
        lambda: primary(changed),
        "incidental allomorph assigned the example-group owner",
    )
    changed = copy.deepcopy(actual)
    ident = changed["additional_to_required_closure"][0]
    changed["complete_native_entries"].pop(ident)
    changed["original_lmf"].pop(ident)
    rejected(
        lambda: closure(initial, source, broad, corpus, changed),
        "missing matched source dictionary owner",
    )
    changed = copy.deepcopy(actual)
    changed["complete_native_entries"][ident]["notes"].append("invented")
    rejected(
        lambda: closure(initial, source, broad, corpus, changed),
        "altered full Native attachment notes",
    )
