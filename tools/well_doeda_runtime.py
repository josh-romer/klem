"""Verify captured API, browser exports, compound ownership and screenshots."""
import argparse
import base64
import copy
import hashlib
import json
from pathlib import Path

from well_doeda_audit import ROOT, RULE, SOURCE, read, sha, word_records

DIAGNOSTICS = ROOT / "docs/well-doeda-diagnostics.json.gz"
REPORT = ROOT / "docs/well-doeda-runtime-checks.json.gz"


def inspect(report):
    source, diagnostic = read(SOURCE), read(DIAGNOSTICS)
    assert report["source_sha256"] == sha(SOURCE)
    assert report["diagnostics_sha256"] == sha(DIAGNOSTICS)
    api, browser = report["api"], report["browser"]
    assert api["cli_sha256"] == browser["cli_sha256"] == diagnostic["cli_sha256"]
    assert api["source_sha256"] == sha(SOURCE)
    assert browser["dictionary_sha256"] == diagnostic["dictionary_sha256"]
    assert browser["fixture_sha256"] == sha(ROOT / "tests/fixtures/well-doeda-sources.json")
    before = api["before_response"]
    assert before["records"] == [json.loads(l) for l in source["before"]["raw"]["jsonl"].splitlines()]
    original = {r["analysis"]["normalized"]: (r, orders)
                for r, orders in zip(before["records"], before["breakdowns"], strict=True)
                if r.get("analysis")}
    assert len(original) == 46
    assert [b["encoding"] for b in api["batches"]] == ["NFC", "NFD"]
    total, compounds = 0, 0
    expected_words = diagnostic["runs"]["raw"]["NFC-cached"]["jsonl"]
    _, expected_words = word_records(expected_words)
    for batch in api["batches"]:
        assert hashlib.sha256(batch["cli_jsonl"].encode()).hexdigest() == batch["cli_jsonl_sha256"]
        cli, words = word_records(batch["cli_jsonl"])
        response = batch["response"]
        assert cli == response["records"]
        assert set(words) == set(original)
        for word, record in words.items():
            assert record["analysis"] == expected_words[word]["analysis"]
            assert record["dictionary"] == expected_words[word]["dictionary"]
        for record, orders in zip(response["records"], response["breakdowns"], strict=True):
            if not record.get("analysis"):
                continue
            total += 1
            old, old_orders = original[record["analysis"]["normalized"]]
            for analysis, order in zip(record["analysis"]["analyses"], orders, strict=True):
                if RULE not in analysis["rules"]:
                    assert order == old_orders[old["analysis"]["analyses"].index(analysis)]
                    continue
                parent = copy.deepcopy(analysis)
                parent["lemmas"] = [{"text": "잘되다", "kind": "predicate"}] + parent["lemmas"][2:]
                parent["rules"].remove(RULE)
                parent_order = old_orders[old["analysis"]["analyses"].index(parent)]
                expected = [{"lemma": 0}] + [{"lemma": c["lemma"] + 1} if "lemma" in c else c
                                              for c in parent_order]
                assert order == expected
                compounds += 1
    assert total == 92 and compounds == api["compound_orders"] == 78
    assert api["complete_native_entries"] == source["complete_native_entries"]
    assert browser["browser_errors"] == []
    assert len(browser["checks"]) == len(browser["diagrams"]) == 6
    assert {(c["encoding"], c["mode"]) for c in browser["checks"]} == {
        (encoding, mode) for encoding in ["NFC", "NFD"] for mode in ["raw", "headword", "compatible"]
    }
    for check in browser["checks"]:
        assert check["cli_records"] == check["exported_records"]
        for record in check["exported_records"]:
            if not record.get("analysis"):
                continue
            word = record["analysis"]["normalized"]
            _, expected = word_records(diagnostic["runs"][check["mode"]]["NFC-cached"]["jsonl"])
            assert record["analysis"] == expected[word]["analysis"]
            assert record["dictionary"] == expected[word]["dictionary"]
    assert {(d["encoding"], d["word"]) for d in browser["diagrams"]} == {
        (encoding, word) for encoding in ["NFC", "NFD"] for word in ["잘됐어요", "잘되는", "잘됨은"]
    }
    for diagram in browser["diagrams"]:
        assert diagram["parts"][:2] == ["잘", "되"]
        assert diagram["entry"] == "krdict:58939"
        assert diagram["selected"] != diagram["whole_selected"]
        assert next(e for e in diagram["owner"]["entries"] if e["id"] == "krdict:89858")["status"] == "compatible"
        assert next(e for e in diagram["owner"]["entries"] if e["id"] == "krdict:48214")["status"] == "incompatible"
    assert set(report["screenshots"]) == {"desktop", "mobile"}
    for snap in report["screenshots"].values():
        raw = base64.b64decode(snap["base64"], validate=True)
        assert raw.startswith(b"\x89PNG\r\n\x1a\n")
        assert hashlib.sha256(raw).hexdigest() == snap["sha256"]
    return total, compounds, len(api["complete_native_entries"]), len(browser["diagrams"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args()
    print("Verified API words, compound orders, native endpoints and browser diagrams:", inspect(read(args.report)))
