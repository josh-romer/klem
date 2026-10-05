"""Verify actual typed morphology recoveries while preserving original projections."""
import hashlib
import json

from lexical_nada_audit import ROOT, read, sha


def inspect():
    source_path = ROOT / "docs/ssik-morphology-projection.json"
    report = read(ROOT / "docs/ssik-adverb-morphology-outcomes.json")
    source = read(source_path)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022v"
    assert report["original_projection_sha256"] == sha(source_path)
    diagnostic = read(ROOT / "docs/ssik-adverb-diagnostics.json.gz")
    assert report["cli_sha256"] == diagnostic["cli_sha256"]
    assert report["dictionary_sha256"] == diagnostic["dictionary_sha256"]
    rows = [row for row in source["rows"] if row["expected"] is not None]
    assert len(rows) == len(report["outcomes"]) == 9
    assert len(source["rows"]) - len(rows) == 3
    assert set(report["words"]) == {row["original_row"][1] for row in rows}
    for row, current in zip(rows, report["outcomes"], strict=True):
        surface, expected = row["original_row"][1], row["expected"]
        capture = report["words"][surface]
        assert hashlib.sha256(capture["json"].encode()).hexdigest() == capture["sha256"]
        word = json.loads(capture["json"])
        assert word == capture["result"] and word["normalized"] == surface
        assert capture["command"][1:4] == ["word", surface, "--dictionary"]
        assert capture["command"][4].endswith("/data/dictionaries/krdict/krdict.db")
        matching = [path for path in word["analyses"]
                    if path["lemmas"] == expected["lemmas"] and path["morphemes"] == expected["morphemes"]]
        assert matching
        assert current == {"id": row["id"], "original_id": row["original_id"], "surface": surface,
                           "expected": expected, "matching_paths": matching}
    return len(rows), len(source["rows"]) - len(rows)


if __name__ == "__main__":
    print("Verified recovered original typed cases and retained unprojected rows:", inspect())
