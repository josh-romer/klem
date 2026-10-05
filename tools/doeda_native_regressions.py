"""Append native structural cases while retaining both complete original ledgers."""

import argparse
import hashlib
import json
from collections import Counter

from doeda_native_audit import FIXTURE
from doeda_native_preflight import cases
from lexical_nada_audit import ROOT, read, sha, write

RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
BEFORE = ROOT / "docs/doeda-native-ledger-before.json.gz"
SOURCE_KEY = "doeda-native-origin"
SOURCE_URL = "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74902"


def records(policy=False):
    result = []
    for case in cases(read(FIXTURE)):
        ident = case["id"] + ("-policy" if policy else "")
        result.append(
            {
                "id": ident,
                "surface": case["surface"],
                "judgments": [
                    {
                        "id": ident + "-path",
                        "lemmas": [l["text"] for l in case["lemmas"]],
                        "lemma_kinds": [l["kind"] for l in case["lemmas"]],
                        "morphemes": [m["form"] for m in case["morphemes"]],
                        "morpheme_kinds": [m["kind"] for m in case["morphemes"]],
                        "required_rules": [case["required_rule"]],
                        "verdict": "required",
                        "source": SOURCE_KEY,
                        "reason": "Native whole/noun entries record the same origin and whole verb POS. Exact owned suffix/inflection hypothesis; competing dictionary senses, context/register and independent review remain unjudged. Formation evidence and ten variants retain stable IDs in doeda-native-formations.json.",
                    }
                ],
            }
        )
    assert len(result) == len({r["id"] for r in result}) == 15700
    return result


def append():
    assert not BEFORE.exists()
    originals = {}
    for mode, path in (("raw", RAW), ("policy", POLICY)):
        text = path.read_text()
        suite = json.loads(text)
        assert SOURCE_KEY not in suite["sources"]
        additions = records(mode == "policy")
        assert not {r["id"] for r in additions} & {r["id"] for r in suite["cases"]}
        originals[mode] = {"text": text, "sha256": sha(path)}
    write(
        BEFORE,
        {"schema_version": 1, "fixture_sha256": sha(FIXTURE), "ledgers": originals},
    )
    for mode, path in (("raw", RAW), ("policy", POLICY)):
        text = originals[mode]["text"]
        suite = json.loads(text)
        additions = records(mode == "policy")
        start = text.index('"sources": {') + len('"sources": {')
        updated = (
            text[:start]
            + "\n    "
            + json.dumps(SOURCE_KEY)
            + ": "
            + json.dumps(SOURCE_URL)
            + ","
            + text[start:]
        )
        end = updated.rindex("\n  ]")
        updated = (
            updated[:end]
            + ",\n"
            + ",\n".join(
                "    "
                + json.dumps(r, ensure_ascii=False, indent=2).replace("\n", "\n    ")
                for r in additions
            )
            + updated[end:]
        )
        assert json.loads(updated) == dict(
            suite,
            sources=suite["sources"] | {SOURCE_KEY: SOURCE_URL},
            cases=suite["cases"] + additions,
        )
        path.write_text(updated)
    verify()


def verify():
    before = read(BEFORE)
    assert before["schema_version"] == 1 and before["fixture_sha256"] == sha(FIXTURE)
    for mode, path in (("raw", RAW), ("policy", POLICY)):
        saved = before["ledgers"][mode]
        assert hashlib.sha256(saved["text"].encode()).hexdigest() == saved["sha256"]
        original, current = json.loads(saved["text"]), read(path)
        for key in original.keys() - {"sources", "cases"}:
            assert original[key] == current[key]
        assert all(current["sources"][k] == v for k, v in original["sources"].items())
        assert current["sources"][SOURCE_KEY] == SOURCE_URL
        originals = {c["id"]: c for c in original["cases"]}
        assert [c for c in current["cases"] if c["id"] in originals] == original[
            "cases"
        ]
        expected = records(mode == "policy")
        ids = {r["id"] for r in expected}
        assert [c for c in current["cases"] if c["id"] in ids] == expected
        assert len({c["id"] for c in current["cases"]}) == len(current["cases"])
        print(
            mode,
            "retains",
            len(original["cases"]),
            "complete original cases and",
            Counter(j["verdict"] for r in expected for j in r["judgments"]),
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--append", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    append() if args.append else verify()
