"""Audit original present-prefinal sources and bounded structural judgments offline.

The named 45 owners are finite provenance, not closure of every speculative
candidate. Archived commands are evidence; this verifier never executes them.
"""

import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]
PRIMARY = {"krdict:66461", "krdict:85852"}
TARGETS = [
    ("하신다", "하다", ["시", "는다"]),
    ("만든다고", "만들다", ["는다고"]),
    ("다닌다는", "다니다", ["는다는"]),
    ("온대요", "오다", ["는대", "요"]),
    ("나간다던데", "나가다", ["는다던데"]),
    ("먹는군", "먹다", ["는군"]),
    ("입는다니", "입다", ["는다니"]),
    ("찾는다나", "찾다", ["는다나"]),
    ("읽는다고", "읽다", ["는다고"]),
    ("근무하시는구나", "근무하다", ["시", "는구나"]),
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(name):
    data = (ROOT / name).read_bytes()
    return json.loads(gzip.decompress(data) if name.endswith(".gz") else data)


def producer(report):
    assert sha(report["producer"]["text"].encode()) == report["producer"]["sha256"]


def verify_sources(discovery, owners, draft, native, english):
    for report in (discovery, owners, draft):
        producer(report)
        assert report["preparation_only"] is True
    for report in (discovery, owners):
        assert report["contextual_verdict"] == "unjudged"
        assert report["independent_review"] == "pending"
    assert set(owners["primary_entry_ids"]) == PRIMARY
    assert len(native) == 45 and native == owners["complete_native_entries"]
    assert {key: entry(raw) for key, raw in owners["original_lmf"].items()} == native
    assert english == owners["english_projection"]
    verify_native_lmf(english, native)
    assert discovery["sqlite_entries"] == {key: native[key] for key in PRIMARY}
    groups = [
        {"source": key, "sense": sense["id"], "index": i, "original": group}
        for key in sorted(PRIMARY)
        for sense in native[key]["senses"]
        for i, group in enumerate(sense["examples"])
    ]
    assert len(groups) == 9 and groups == discovery["all_original_groups"]
    assert discovery["input"] == "\n".join(
        text for group in groups for text in group["original"]
    ) + "\n"
    positive = [case for case in draft["cases"] if "source_occurrence" in case]
    assert len(positive) == len(TARGETS) == 10
    for case, (surface, lemma, forms) in zip(positive, TARGETS, strict=True):
        occurrence = case["source_occurrence"]
        group = {key: occurrence[key] for key in ("source", "sense", "index", "original")}
        assert group in groups
        text = group["original"][occurrence["text_index"]]
        start, end = occurrence["character_span"]
        assert text[start:end] == case["surface"] == surface
        judgment, = case["judgments"]
        assert judgment["verdict"] == "required"
        assert judgment["lemmas"] == [lemma] and judgment["morphemes"] == forms
        assert draft["sources"][judgment["source"]] == native[group["source"]]["url"]
    assert "다니는" in groups[-1]["original"][0]
    assert all(case["surface"] != "다니는" for case in positive)
    # Full-family notes govern final declaratives; exclamations license honorifics.
    assert native["krdict:85033"]["notes"] == [
        "받침이 없거나 ‘ㄹ’ 받침인 동사 또는 '-으시-' 뒤에 붙여 쓴다."
    ]
    assert native["krdict:85037"]["notes"] == [
        "‘ㄹ’을 제외한 받침 있는 동사 뒤에 붙여 쓴다."
    ]
    assert native["krdict:74697"]["notes"] == [
        "주로 구어에서 쓰고, ‘ㄹ’을 제외한 받침 있는 동사 뒤에 붙여 쓴다."
    ]
    for key in ("krdict:81573", "krdict:79273"):
        assert "동사 또는" in native[key]["notes"][0]
        assert "으시" in native[key]["notes"][0]
    assert native["krdict:79033"]["headword"] == "좋다"
    assert native["krdict:79033"]["pos"] == "형용사"


def verify_cases(draft, raw, policy, ledger):
    expected = [{key: case[key] for key in ("id", "surface", "judgments")}
                for case in draft["cases"]]
    assert raw["cases"] == expected and raw["sources"] == draft["sources"]
    assert policy["cases"][:-1] == expected and policy["sources"] == raw["sources"]
    assert len(expected) == 15
    negatives = [case for case in expected if case["judgments"][0]["verdict"] == "forbidden"]
    assert [case["surface"] for case in negatives] == [
        "하는다", "살는다", "하시는다", "먹으시는다", "하는다나"
    ]
    for i, case in enumerate(negatives):
        judgment, = case["judgments"]
        owner = "74697" if i == 4 else "85037"
        assert judgment["source"] == "present-prefinal-ending-" + owner
    extra = policy["cases"][-1]
    assert extra["surface"] == draft["policy_followup"]["surface"] == "좋는다"
    judgment, = extra["judgments"]
    assert judgment["lemmas"] == ["좋다"] and judgment["morphemes"] == ["는다"]
    assert judgment["verdict"] == "forbidden"
    assert judgment["source"] == "present-prefinal-ending-85037"
    indexed = {case["id"]: case for case in ledger["cases"]}
    assert all(indexed[case["id"]] == case for case in expected)
    assert all(ledger["sources"][key] == value for key, value in raw["sources"].items())
    assert extra["id"] not in indexed, "Dictionary-only policy cannot be a raw prohibition"


def verify_streams(discovery):
    assert discovery["inputs_unchanged"] is True
    assert len(discovery["frozen_inputs"]) == 3
    assert len(discovery["runs"]) == 6
    assert {(r["encoding"], r["mode"]) for r in discovery["runs"]} == {
        (encoding, mode) for encoding in ("NFC", "NFD")
        for mode in ("raw", "headword", "compatible")
    }
    for run in discovery["runs"]:
        data = unicodedata.normalize(run["encoding"], discovery["input"]).encode()
        assert sha(data) == run["input_sha256"]
        assert set(run["stages"]) == {"before", "after"}
        streams = []
        for capture in run["stages"].values():
            assert capture["exit_code"] == 0
            assert sha(capture["jsonl"].encode()) == capture["sha256"]
            command = capture["command"]
            assert command[0] in discovery["frozen_inputs"]
            assert command[1:4] == ["text", "-", "--dictionary"]
            assert command[4] in discovery["frozen_inputs"]
            assert command[5:] == {
                "raw": [], "headword": ["--dict-only"],
                "compatible": ["--dict-compatible"],
            }[run["mode"]]
            frames = [json.loads(line) for line in capture["jsonl"].splitlines()]
            assert len(frames) == capture["records"] == 134
            cursor = 0
            for frame in frames:
                assert frame["span"]["start"] == cursor
                cursor = frame["span"]["end"]
                assert data[frame["span"]["start"]:cursor] == frame["surface"].encode()
            assert cursor == len(data)
            streams.append(frames)
        changed = []
        for before, after in zip(*streams, strict=True):
            if before == after:
                continue
            assert before["surface"] == after["surface"]
            assert unicodedata.normalize("NFC", after["surface"]) == "찾는다나"
            assert before["span"] == after["span"] and before["kind"] == after["kind"]
            old = before["analysis"]["analyses"]
            new = after["analysis"]["analyses"]
            assert (len(old), len(new)) == ((16, 20) if run["mode"] == "raw" else (1, 2))
            for i, path in enumerate(old):
                j = new.index(path)
                assert before["dictionary"]["readings"][i] == after["dictionary"]["readings"][j]
            changed.append(after["surface"])
        assert len(changed) == 1


def verify():
    discovery = read("docs/present-prefinal-source-discovery.json.gz")
    owners = read("docs/present-prefinal-owner-preparation.json.gz")
    draft = read("docs/present-prefinal-judgment-draft.json")
    history = read("docs/present-prefinal-preparation-history.json.gz")
    for archived in history.values():
        data = bytes.fromhex(archived["content"]) if archived["encoding"] == "hex" else archived["content"].encode()
        assert sha(data) == archived["sha256"]
    binding = json.loads(history["klem-present-prefinal-review-source-binding.json"]["content"])
    assert sha((ROOT / "docs/present-prefinal-judgment-draft.json").read_bytes()) == binding["effective_draft_sha256"]
    for kind in ("raw", "policy"):
        name = "isolated-present-prefinal-" + ("validity" if kind == "raw" else kind) + ".json"
        assert history[name]["sha256"] == binding[kind + "_fixture_sha256"]
    assert history["klem-present-prefinal-review-rust.json"]["sha256"] == binding["isolated_rust_receipt_sha256"]
    assert sha(gzip.decompress((ROOT / "docs/present-prefinal-source-discovery.json.gz").read_bytes())) == draft["source_capture_sha256"] == owners["source_capture_sha256"]
    assert sha((ROOT / "docs/present-prefinal-owner-preparation.json.gz").read_bytes()) == draft["owner_preparation_sha256"]
    native = read("tests/fixtures/present-prefinal-native.json")
    english = read("tests/fixtures/krdict-present-prefinal-english.json")
    verify_sources(discovery, owners, draft, native, english)
    verify_cases(draft, read("tests/fixtures/present-prefinal-validity.json"),
                 read("tests/fixtures/present-prefinal-policy.json"), read("tests/fixtures/validity.json"))
    verify_streams(discovery)
    return {"primary_entries": 2, "named_native_owners": 45, "original_groups": 9,
            "source_occurrences": 10, "raw_forbidden": 5, "policy_forbidden": 6,
            "archived_streams": 12, "frames_per_stream": 134,
            "contextual_verdict": "unjudged", "independent_review": "pending"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
