"""Verify exact source ownership, native LMF and frozen adverb-base regressions."""
import copy
import hashlib
import json
import re
import unicodedata

from lexical_nada_audit import ROOT, read, sha
from native_lmf import array, entry, verify_native_lmf

BASES = {"가끔", "살짝", "이따금", "이만큼", "잠깐", "조금", "하나하나", "한바탕", "한발"}


def inspect():
    inventory_path = ROOT / "docs/ssik-adverb-inventory.json.gz"
    dispositions_path = ROOT / "docs/ssik-adverb-dispositions.json.gz"
    lmf_path = ROOT / "docs/ssik-adverb-lmf-source.json.gz"
    preflight_path = ROOT / "docs/ssik-adverb-preflight.json.gz"
    inventory, dispositions, lmf, preflight = map(read, [inventory_path, dispositions_path, lmf_path, preflight_path])
    fixture = read(ROOT / "tests/fixtures/ssik-adverb-sources.json")
    for report in [inventory, dispositions, preflight]:
        assert report["schema_version"] == 1 and report["checklist"] == "COV-022v"
        assert report["preparation_only"] is True
    assert dispositions["inventory_sha256"] == preflight["inventory_sha256"] == fixture["inventory_sha256"] == sha(inventory_path)
    assert lmf["source_sha256"] == preflight["dispositions_sha256"] == fixture["dispositions_sha256"] == sha(dispositions_path)
    assert preflight["lmf_source_sha256"] == fixture["lmf_source_sha256"] == sha(lmf_path)
    assert fixture["source_sha256"] == sha(preflight_path)
    assert fixture["complete_native_entries"] == dispositions["complete_native_entries"] == lmf["complete_native_entries"]
    native = fixture["complete_native_entries"]
    assert len(native) == 349
    assert all(native[k] == v for k, v in inventory["complete_native_entries"].items())
    original_path = ROOT / "tests/fixtures/krdict-ssik-adverb-original.json"
    english_path = ROOT / "tests/fixtures/krdict-ssik-adverb-english.json"
    assert lmf["lmf_sha256"] == {"original": sha(original_path), "english": sha(english_path)}
    original, english = read(original_path), read(english_path)
    assert {entry(raw)["id"]: entry(raw) for raw in array(original["LexicalResource"]["Lexicon"]["LexicalEntry"])} == native
    expected = copy.deepcopy(original)
    for raw in array(expected["LexicalResource"]["Lexicon"]["LexicalEntry"]):
        for sense in array(raw.get("Sense")):
            if "Equivalent" in sense:
                sense["Equivalent"] = [value for value in array(sense["Equivalent"]) if any(f["att"] == "language" and f["val"] == "영어" for f in array(value.get("feat")))]
    assert english == expected
    verify_native_lmf(english, native)
    heads = {}
    for key in sorted(native):
        value = native[key]
        if value["pos"] == "부사":
            heads.setdefault(value["headword"], []).append(key)
    observations, groups = [], {}
    for key in sorted(native):
        for sense in native[key]["senses"]:
            for index, group in enumerate(sense["examples"]):
                for text_index, text in enumerate(group):
                    for match in re.finditer(r"(?<![가-힣])([가-힣]+)씩(?![가-힣])", text):
                        base = match[1]
                        if base not in heads:
                            continue
                        observations.append({"source_entry": key, "source_sense": sense["id"], "example_index": index, "text_index": text_index, "original_group": group, "base": base, "adverb_base_entries": heads[base], "surface": match[0], "character_span": [match.start(), match.end()], "contextual_verdict": "unjudged", "independent_review": "pending"})
                        groups[(key, sense["id"], index)] = {"source_entry": key, "source_sense": sense["id"], "example_index": index, "original_group": group}
    assert observations == inventory["observations"] and len(observations) == 362
    assert fixture["all_original_groups"] == preflight["all_original_groups"] == [groups[key] for key in sorted(groups)]
    assert len(groups) == 359
    assert set(dispositions["eligible_bases"]) == set(fixture["eligible_bases"]) == BASES
    assert fixture["dispositions"] == dispositions["dispositions"]
    assert set(dispositions["dispositions"]) == BASES | {"통", "정", "단", "씩"}
    for base, disposition in dispositions["dispositions"].items():
        assert disposition["adverb_base_entries"] == inventory["adverb_base_inventory"][base]
        assert disposition["observation_indices"] == [i for i, item in enumerate(observations) if item["base"] == base]
        expected = "candidate_adverb_base" if base in BASES else "opaque_whole_word_not_suffix_license" if base == "씩" else "counting_unit_homonym_not_adverb_license"
        assert disposition["disposition"] == expected
        assert disposition["contextual_verdict"] == "unjudged" and disposition["independent_review"] == "pending"
    assert preflight["before_cli_sha256"] == dispositions["before_cli_sha256"] == read(ROOT / "docs/ssik-packaged-checks.json.gz")["cli_sha256"]
    assert inventory["dictionary_sha256"] == dispositions["dictionary_sha256"] == preflight["dictionary_sha256"]
    assert len(preflight["words"]) == 207
    text = "\n".join(preflight["words"] + [text for group in preflight["all_original_groups"] for text in group["original_group"]]) + "\n"
    assert text == preflight["input"] and hashlib.sha256(text.encode()).hexdigest() == preflight["input_sha256"]
    assert set(preflight["runs"]) == {"raw", "headword", "compatible"}
    for runs in preflight["runs"].values():
        assert set(runs) == {"NFC-cached", "NFC-uncached", "NFD-cached", "NFD-uncached"}
        semantic = None
        for name, capture in runs.items():
            assert capture["exit_code"] == 0 and hashlib.sha256(capture["jsonl"].encode()).hexdigest() == capture["sha256"]
            rows = [json.loads(line) for line in capture["jsonl"].splitlines()]
            assert "".join(row["surface"] for row in rows) == unicodedata.normalize(name.split("-")[0], text)
            offset = 0
            for row in rows:
                assert row["span"] == {"start": offset, "end": offset + len(row["surface"].encode())}
                offset = row["span"]["end"]
            value = [(row.get("analysis"), row.get("dictionary")) for row in rows]
            if semantic is None:
                semantic = value
            else:
                assert semantic == value
    records = [json.loads(line) for line in preflight["runs"]["raw"]["NFC-cached"]["jsonl"].splitlines()]
    assert fixture["before_analyses"] == {row["analysis"]["normalized"]: row["analysis"] for row in records if row["kind"] == "word"}
    assert len(fixture["before_analyses"]) == 2509
    cases = fixture["cases"]
    assert len(cases) == len({case["id"] for case in cases}) == 130
    assert sum(case["judgments"][0]["verdict"] == "required" for case in cases) == 45
    assert sum(case["judgments"][0]["verdict"] == "forbidden" for case in cases) == 85
    ledger = read(ROOT / "tests/fixtures/validity.json")
    assert [case for case in ledger["cases"] if case["id"].startswith("ssik-adverb-")] == cases
    for key, url in fixture["sources"].items():
        assert ledger["sources"][key] == url
    for report in [inventory, dispositions, lmf, preflight]:
        assert hashlib.sha256(report["producer"]["text"].encode()).hexdigest() == report["producer"]["sha256"]
    return len(native), len(observations), len(groups), len(cases), len(fixture["before_analyses"])


if __name__ == "__main__":
    print("Verified exact source closure, all native projections, base dispositions, original groups, stable cases and twelve frozen streams:", inspect())
