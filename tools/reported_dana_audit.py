"""Portable audit of captured Native/source streams with targeted corruption controls."""

import copy, gzip, hashlib, json, unicodedata
from pathlib import Path
from native_lmf import entry
from reported_dana_parent import frame, actual_parent

parents = {}
ROOT = Path(__file__).resolve().parents[1]
P = ROOT
read = lambda p: (
    json.loads(gzip.decompress(Path(p).read_bytes()))
    if str(p).endswith(".gz")
    else json.loads(Path(p).read_text())
)
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def verify_captured_inputs(report):
    paths = {
        "/tmp/klem-reported-dana-native-preparation.json.gz": ROOT
        / "docs/reported-dana-native-preparation.json.gz",
        "/tmp/klem-reported-dana-prototype/tests/fixtures/reported-dana-validity.json": ROOT
        / "tests/fixtures/reported-dana-validity.json",
        "/tmp/klem_reported_dana_parent.py": ROOT
        / "docs/reported-dana-prototype-parent.py.txt",
    }
    for original, path in paths.items():
        assert report["frozen_inputs"][original] == sha(path)
    corpus = read(ROOT / "docs/reported-dana-prototype-corpora.json.gz")
    broad = read(ROOT / "docs/reported-dana-prototype-broad.json.gz")
    candidate = "/home/josh/projects/klem/web/test-results/reported-dana-prototype-cargo/debug/klem"
    assert (
        report["frozen_inputs"][candidate]
        == corpus["cli_sha256"]
        == broad["cli_sha256"]
    )
    before = "/nix/store/p0xh9pk9m2nm8373vzicgdpx5w1yz6z7-klem-0.1.0/bin/klem"
    assert (
        report["frozen_inputs"][before]
        == corpus["before_cli_sha256"]
        == broad["before_cli_sha256"]
    )
    native = read(ROOT / "docs/reported-dana-observation-native.json.gz")
    for original, path in [
        (
            "/tmp/klem-reported-dana-native-preparation.json.gz",
            ROOT / "docs/reported-dana-native-preparation.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-source-streams.json.gz",
            ROOT / "docs/reported-dana-prototype-source-streams.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-broad.json.gz",
            ROOT / "docs/reported-dana-prototype-broad.json.gz",
        ),
        (
            "/tmp/klem-reported-dana-prototype-corpora.json.gz",
            ROOT / "docs/reported-dana-prototype-corpora.json.gz",
        ),
    ]:
        assert native["frozen_inputs"][original] == sha(path)
    dictionary = "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"
    assert native["frozen_inputs"][dictionary] == report["frozen_inputs"][dictionary]


def check_observation(row):
    assert (
        row["contextual_verdict"] == "unjudged"
        and row["independent_review"] == "pending"
    )
    surface, parent = actual_parent(row["surface"], row["analysis"], parents)
    assert surface == row["parent_surface"] and parent == row["exact_parent"]
    assert row["occurrences"]
    for occurrence in row["occurrences"]:
        assert occurrence["span"]["end"] > occurrence["span"]["start"]
        assert isinstance(occurrence["record"], int) and occurrence["record"] >= 0


def check_sources(report):
    source_paths = [ROOT / "docs/reported-dana-native-preparation.json.gz"]
    original = {}
    for path in source_paths:
        data = read(path)
        assert data["original_lmf"].keys() == data["complete_native_entries"].keys()
        for ident, raw in data["original_lmf"].items():
            native = entry(raw)
            assert native == data["complete_native_entries"][ident]
            original[ident] = native
    assert report["complete_native_entries"] == original
    groups = [
        {
            "id": ident + ":" + sense["id"] + ":" + str(i),
            "entry_id": ident,
            "sense_id": sense["id"],
            "group_index": i,
            "original_group": group,
        }
        for ident, native in sorted(original.items())
        for sense in native["senses"]
        for i, group in enumerate(sense["examples"])
    ]
    assert groups == report["source_groups"]
    cases = read(ROOT / "tests/fixtures/reported-dana-validity.json")["cases"]
    text = (
        "\n".join(
            [c["surface"] for c in cases]
            + [line for group in groups for line in group["original_group"]]
        )
        + "\n"
    )
    assert (
        report["input"] == text
        and report["input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    )
    return len(original), len(groups)


def verify(report):
    assert report["prototype"] and report["inputs_unchanged"]
    verify_captured_inputs(report)
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    native_count, groups = check_sources(report)
    parents.clear()
    parents.update(report["actual_prior_companions"])
    observed = {}
    unique_words = set()
    frames = 0
    test_frame = None
    assert set(report["runs"]) == {"NFC", "NFD"}
    for encoding, modes in report["runs"].items():
        assert set(modes) == {"raw", "headword", "compatible"}
        request = unicodedata.normalize(encoding, report["input"]).encode()
        for mode, stages in modes.items():
            assert set(stages) == {"before", "after"}
            for stage in stages.values():
                assert stage["exit_code"] == 0
                assert (
                    hashlib.sha256(stage["jsonl"].encode()).hexdigest()
                    == stage["sha256"]
                )
            before = [json.loads(l) for l in stages["before"]["jsonl"].splitlines()]
            after = [json.loads(l) for l in stages["after"]["jsonl"].splitlines()]
            assert len(before) == len(after)
            offset = changed = added_count = 0
            for index, (b, a) in enumerate(zip(before, after, strict=True)):
                span = a["span"]
                assert span["start"] == offset
                assert request[span["start"] : span["end"]].decode() == a["surface"]
                offset = span["end"]
                additions = frame(b, a, parents)
                changed += b != a
                added_count += len(additions)
                if a["kind"] == "word":
                    unique_words.add(a["analysis"]["normalized"])
                if additions and test_frame is None:
                    test_frame = (b, a)
                if encoding == "NFC" and mode == "raw":
                    for path in additions:
                        key = json.dumps(
                            [a["analysis"]["normalized"], path],
                            sort_keys=True,
                            ensure_ascii=False,
                        )
                        observed.setdefault(key, []).append(
                            {
                                "record": index,
                                "span": span,
                                "dictionary_assessment": a["dictionary"]["readings"][
                                    a["analysis"]["analyses"].index(path)
                                ],
                            }
                        )
            assert offset == len(request)
            assert report["counts"][encoding + ":" + mode] == {
                "frames": len(after),
                "changed_frames": changed,
                "added_paths": added_count,
            }
            frames += len(after)
    keys = []
    for row in report["individual_additions"]:
        check_observation(row)
        key = json.dumps(
            [row["surface"], row["analysis"]], sort_keys=True, ensure_ascii=False
        )
        keys.append(key)
        assert (
            row["id"]
            == "reported-dana-source-" + hashlib.sha256(key.encode()).hexdigest()[:24]
        )
        assert observed[key] == row["occurrences"]
    assert len(keys) == len(set(keys)) and set(keys) == set(observed)
    assert len(unique_words) == report["unique_words"]
    print(
        "Offline source audit:",
        native_count,
        "complete Native/LMF owners;",
        groups,
        "original groups;",
        frames,
        "complete frames;",
        len(keys),
        "individual additions.",
        flush=True,
    )
    return test_frame


def rejected(action, label):
    try:
        action()
    except (AssertionError, KeyError):
        print("Rejected corruption:", label, flush=True)
        return
    raise AssertionError("Corruption accepted: " + label)


def controls(report, pair):
    b, a = pair
    changed = copy.deepcopy(a)
    path = b["analysis"]["analyses"][0]
    index = changed["analysis"]["analyses"].index(path)
    changed["dictionary"]["readings"][index]["status"] = "corrupted"
    rejected(lambda: frame(b, changed, parents), "retained dictionary reading changed")
    row = copy.deepcopy(report["individual_additions"][0])
    row["exact_parent"]["lemmas"][0]["text"] = "invalid-parent"
    rejected(lambda: check_observation(row), "wrong exact parent")
    row = copy.deepcopy(report["individual_additions"][0])
    row["contextual_verdict"] = "required"
    rejected(
        lambda: check_observation(row),
        "contextual certification inferred from structural parent",
    )
    native = report["complete_native_entries"]
    key = next(iter(native))
    saved = native.pop(key)
    try:
        rejected(lambda: check_sources(report), "missing complete Native owner")
    finally:
        native[key] = saved


if __name__ == "__main__":
    report = read(ROOT / "docs/reported-dana-prototype-source-streams.json.gz")
    pair = verify(report)
    controls(report, pair)
