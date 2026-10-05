"""Verify the finite 잘 + 되다 compound against preserved sources and CLI evidence."""

import argparse
import copy
import gzip
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from native_lmf import verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/well-doeda-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/well-doeda-sources.json"
LMF = ROOT / "tests/fixtures/krdict-well-doeda.json"
LEDGER = ROOT / "tests/fixtures/validity.json"
RULE = "compound.predicate.well_doeda"
MODES = {"raw": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}


def read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf8") as stream:
            return json.load(stream)
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def word_records(text):
    records = [json.loads(line) for line in text.splitlines()]
    words = {r["analysis"]["normalized"]: r for r in records if r.get("analysis")}
    assert len(words) == sum(bool(r.get("analysis")) for r in records)
    return records, words


def inspect_source(source):
    assert source["schema_version"] == 1 and source["checklist"] == "COV-022m"
    primary = source["primary_source"]
    assert primary["listed_pair"] == "잘-잘되다"
    assert primary["short_excerpt"] == "부사+서술어 구성"
    assert primary["printed_page"] == 54 and primary["pdf_page_zero_based"] == 63
    assert primary["url"].startswith("https://www.korean.go.kr/common/download.do?")
    assert source["reviewer"] == "agent" and source["independent_review"] == "pending"
    assert source["contextual_verdict"] == "unjudged"
    native = source["complete_native_entries"]
    assert source["native_sha256"] == digest(native) and len(native) == 39
    for ident, head, pos in [("krdict:58939", "잘", "부사"),
                             ("krdict:62302", "잘되다", "동사"),
                             ("krdict:89858", "되다", "동사"),
                             ("krdict:48214", "되다", "형용사")]:
        assert (native[ident]["headword"], native[ident]["pos"]) == (head, pos)
    assert source["fixture_sha256"] == sha(LMF)
    verify_native_lmf(read(LMF), native)
    fixture = read(FIXTURE)
    assert fixture["primary_source"] == primary
    assert fixture["cases"] == source["cases"]
    assert fixture["corpora"] == source["corpora"]
    ledger = read(LEDGER)
    assert [c for c in ledger["cases"] if c["id"].startswith("well-doeda-")] == source["cases"]
    assert len(source["cases"]) == 44
    assert len({c["id"] for c in source["cases"]}) == 44
    assert sum(c["judgments"][0]["verdict"] == "required" for c in source["cases"]) == 30
    assert ledger["sources"]["well-doeda-nikl-compound"] == primary["url"]
    assert len(source["words"]) == len(set(source["words"])) == 46
    assert source["input"] == " ".join(source["words"])
    assert set(source["before"]) == set(MODES)
    for mode, before in source["before"].items():
        assert hashlib.sha256(before["jsonl"].encode()).hexdigest() == before["sha256"]
        records, words = word_records(before["jsonl"])
        assert words == before["words"] and set(words) == set(source["words"])
        assert "".join(r["surface"] for r in records) == source["input"]
        assert all(RULE not in a["rules"] for r in words.values() for a in r["analysis"]["analyses"])
        if mode == "raw":
            assert fixture["before_analyses"] == {w: r["analysis"] for w, r in words.items()}
    assert len(source["corpora"]) == 6
    rows = []
    for corpus in source["corpora"]:
        path = ROOT / corpus["source"]
        if path.exists():
            assert sha(path) == corpus["sha256"]
            original = path.read_text()
        for row in corpus["rows"]:
            assert len(row["original_row"]) == 10
            assert "\t".join(row["original_row"]) in row["complete_sentence"].splitlines()
            assert row["original_lemma"].startswith(("잘되+", "잘+되+"))
            if path.exists():
                assert row["complete_sentence"] in original
            rows.append(row["id"])
    assert len(rows) == len(set(rows)) == 8
    return 44, 46, 39, 8


def inspect_comparison(source, report):
    assert report["source_sha256"] == sha(SOURCE)
    assert set(report["runs"]) == set(MODES)
    changes = []
    for mode, runs in report["runs"].items():
        assert set(runs) == {"NFC-cached", "NFC-uncached", "NFD-cached", "NFD-uncached"}
        current = None
        for name, run in runs.items():
            assert hashlib.sha256(run["jsonl"].encode()).hexdigest() == run["sha256"]
            records, words = word_records(run["jsonl"])
            encoding = name.split("-")[0]
            assert "".join(r["surface"] for r in records) == unicodedata.normalize(encoding, source["input"])
            assert set(words) == set(source["words"])
            values = {w: (r["analysis"], r["dictionary"]) for w, r in words.items()}
            if current is None:
                current = values
            else:
                assert current == values, name
        for word, (after, annotation) in current.items():
            before = source["before"][mode]["words"][word]
            original = before["analysis"]["analyses"]
            retained = [a for a in after["analyses"] if RULE not in a["rules"]]
            assert retained == original, (mode, word, "original candidates/order drift")
            for i, a in enumerate(after["analyses"]):
                if RULE not in a["rules"]:
                    j = original.index(a)
                    assert annotation["readings"][i] == before["dictionary"]["readings"][j]
                    continue
                assert a["lemmas"][:2] == [{"text": "잘", "kind": "adverbial"},
                                             {"text": "되다", "kind": "predicate"}]
                assert not any(r in a["rules"] for r in ["suffix.verb.doeda", "suffix.adjective.doeda"])
                parent = copy.deepcopy(a)
                parent["lemmas"] = [{"text": "잘되다", "kind": "predicate"}] + parent["lemmas"][2:]
                parent["rules"].remove(RULE)
                assert parent in source["before"]["raw"]["words"][word]["analysis"]["analyses"]
                owner = annotation["readings"][i]["lemmas"][1]
                verb = next(e for e in owner["entries"] if e["id"] == "krdict:89858")
                adjective = next(e for e in owner["entries"] if e["id"] == "krdict:48214")
                assert adjective["status"] == "incompatible"
                assert "derivational_identity" not in verb
                change = {"id": "well-doeda-change-" + digest((word, a)),
                          "mode": mode, "surface": word, "analysis": a,
                          "parent": parent, "reading": annotation["readings"][i],
                          "contextual_verdict": "unjudged", "independent_review": "pending"}
                changes.append(change)
    assert report["changes"] == changes
    assert changes
    return len(changes), len({c["id"] for c in changes})


def capture(args, source):
    report = {"schema_version": 1, "source_sha256": sha(SOURCE),
              "cli_sha256": sha(args.cli), "dictionary_sha256": sha(args.dictionary), "runs": {}}
    for mode, flags in MODES.items():
        report["runs"][mode] = {}
        for encoding in ["NFC", "NFD"]:
            for cache in [8388608, 0]:
                command = [str(args.cli.resolve()), "text", "-", "--dictionary",
                           str(args.dictionary.resolve()), *flags, "--cache-bytes", str(cache)]
                encoded = subprocess.check_output(command, input=unicodedata.normalize(encoding, source["input"]).encode())
                name = encoding + ("-cached" if cache else "-uncached")
                report["runs"][mode][name] = {"command": command, "jsonl": encoded.decode(),
                                             "sha256": hashlib.sha256(encoded).hexdigest()}
    # Derive the ledger from the actual records, then independently verify it.
    changes = []
    for mode, runs in report["runs"].items():
        _, words = word_records(runs["NFC-cached"]["jsonl"])
        for word, r in words.items():
            for i, a in enumerate(r["analysis"]["analyses"]):
                if RULE not in a["rules"]:
                    continue
                parent = copy.deepcopy(a)
                parent["lemmas"] = [{"text": "잘되다", "kind": "predicate"}] + parent["lemmas"][2:]
                parent["rules"].remove(RULE)
                changes.append({"id": "well-doeda-change-" + digest((word, a)), "mode": mode,
                                "surface": word, "analysis": a, "parent": parent,
                                "reading": r["dictionary"]["readings"][i],
                                "contextual_verdict": "unjudged", "independent_review": "pending"})
    report["changes"] = changes
    result = inspect_comparison(source, report)
    assert not args.output.exists(), "Preserve historical evidence; choose a new output path."
    with gzip.open(args.output, "wt", encoding="utf8") as stream:
        json.dump(report, stream, ensure_ascii=False)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path, default=ROOT / "data/dictionaries/krdict/krdict.db")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--comparison", type=Path)
    args = parser.parse_args()
    source = read(SOURCE)
    print("Verified source/cases, words, native owners and original corpus rows:", inspect_source(source))
    if args.cli:
        print("Captured individually tracked candidate additions:", capture(args, source))
    if args.comparison:
        print("Verified candidate additions:", inspect_comparison(source, read(args.comparison)))
