"""Verify complete rhetorical/reported-question sources and authored cases."""

import gzip
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IDS = [78782, 78786, 78797, 78803, 86563, 86566, 86628, 86630, 80909, 85833]
LABEL_IDS = {
    "-는답니까": [78782, 78786, 86563, 86566],
    "-답니까": [78797, 86628],
    "-랍니까": [78803, 86630],
    "-으랍니까": [86630, 80909],
}


def read(path):
    path = Path(path)
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def inspect(prepared, closure, native, expected_entries, proposals, suite, labels, label_fixture):
    original = prepared["complete_imported_entries"]
    ids = ["krdict:" + str(i) for i in SOURCE_IDS]
    assert set(original) == set(ids), "separate ending/expression identities"
    assert all(original[i]["pos"] == "어미" for i in ids[:4]), "ending roles"
    assert all(original[i]["pos"] == "품사 없음" for i in ids[4:]), "expression roles"
    assert {i: entry(raw) for i, raw in prepared["original_native_entries"].items()} == original, "complete source projections"
    projected = {}
    raw_entries = native["LexicalResource"]["Lexicon"]["LexicalEntry"]
    for raw in raw_entries:
        value = entry(raw)
        assert value["id"] not in projected, "Native identity collision"
        projected[value["id"]] = value
    assert projected == closure["entries"] == expected_entries and len(projected) == 90, "complete Native projection"
    assert all(projected[i] == value for i, value in original.items()), "original source entries"
    assert {e["headword"] for i, e in projected.items() if i not in ids} == set(closure["owner_headwords"]), "complete owner headwords"
    groups = []
    text = ""
    for ident in ids:
        for sense in original[ident]["senses"]:
            for ordinal, examples in enumerate(sense["examples"], 1):
                start = len(text.encode())
                block = "\n".join(examples)
                text += block + "\n"
                groups.append({"id": f"dapnikka-source-{ident.split(':')[1]}-{sense['id']}-{ordinal}", "entry_id": ident, "sense_id": sense["id"], "group": ordinal, "complete_original_examples": examples, "span": {"start": start, "end": start + len(block.encode())}})
    assert groups == prepared["complete_groups"] and len(groups) == 46, "all complete original groups"
    assert text == prepared["complete_source_text"], "complete source text"
    assert proposals == prepared["proposals"] and len(proposals) == 46, "original proposals"
    assert {p["source_group_id"] for p in proposals} == {g["id"] for g in groups}, "complete proposal coverage"
    assert len(suite["cases"]) == len({c["id"] for c in suite["cases"]}) == 62, "stable case identities"
    by_id = {c["id"]: c for c in suite["cases"]}
    for proposal in proposals:
        case = by_id[proposal["id"]]
        assert case["surface"] == proposal["surface"], "case source surface"
        judgment = case["judgments"][0]
        assert judgment["lemmas"] == proposal["proposed_lemmas"] and judgment["verdict"] == "required" and judgment["required_rules"] == ["ending.question_dapnikka"], "authored exact source requirement"
    counts = {v: sum(j["verdict"] == v for c in suite["cases"] for j in c["judgments"]) for v in ["required", "forbidden"]}
    assert counts == {"required": 55, "forbidden": 7}, "finite judgment counts"
    label_sources = set()
    for form, source_ids in LABEL_IDS.items():
        label = labels[form]
        assert label["kind"] == "ending", "display role"
        assert [source["id"] for source in label["sources"]] == source_ids, "display source identities"
        for source in label["sources"]:
            ident = "krdict:" + str(source["id"])
            assert source["headword"] == original[ident]["headword"] and source["pos"] == original[ident]["pos"], "display source roles"
            label_sources.add(ident)
    label_entries = label_fixture["LexicalResource"]["Lexicon"]["LexicalEntry"]
    assert len(label_entries) == len(label_sources) and {entry(e)["id"] for e in label_entries} == label_sources, "label fixture source identities"
    assert all(e == next(raw for raw in raw_entries if raw["val"] == e["val"]) for e in label_entries), "complete label fixture Native entries"
    assert projected["krdict:61181"]["headword"] == projected["krdict:64526"]["headword"] == "늦다", "distinct lexical homonyms"
    assert projected["krdict:61181"]["pos"] == "동사" and projected["krdict:64526"]["pos"] == "형용사", "unchanged lexical roles"
    return {"complete_groups": 46, "native_entries": 90, **counts, "independent_contextual_review_complete": False}


def inputs():
    return [read(p) for p in [
        ROOT / "docs/dapnikka-source-preparation.json.gz",
        ROOT / "docs/dapnikka-native-closure.json.gz",
        ROOT / "tests/fixtures/dapnikka-native.json",
        ROOT / "tests/fixtures/dapnikka-native-entries.json",
        ROOT / "tests/fixtures/dapnikka-proposals.json",
        ROOT / "tests/fixtures/dapnikka-validity.json",
        ROOT / "web/src/grammar-labels.json",
        ROOT / "tests/fixtures/krdict-dapnikka-labels.json",
    ]]


if __name__ == "__main__":
    print(inspect(*inputs()))
