"""Check packaged HTTP/CLI parity, candidate judgments and complete native entries."""

import argparse
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from adjectival_allomorph_audit import DERIVED, SOURCE, matches
from adjectival_allomorph_compare import ADDITIONAL
from adjectival_allomorph_compare import REPORT as OBSERVATIONS
from adjectival_allomorph_corrections import CORRECTIONS
from lexical_nada_audit import ROOT, digest, read, sha

POLICY = ROOT / "tests/fixtures/adjectival-allomorph-policy-corrections.json"
REPORT = ROOT / "docs/adjectival-allomorph-packaged-runtime.json"


def cases_and_words():
    source, corrections = read(SOURCE), read(CORRECTIONS)
    cases = (
        corrections["matrix_cases"]
        + [r["replacement"] for r in corrections["superseded"]]
        + [r["replacement"] for r in read(POLICY)["superseded"]]
    )
    words = {
        r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
    }
    words |= {r["surface"] for r in read(DERIVED)["additional_proposals"]}
    words |= {r["surface"] for r in read(OBSERVATIONS)["changes"]}
    words |= {r["surface"] for r in cases}
    return cases, sorted(words)


def chunks(words, encoding):
    current = []
    for word in words:
        word = unicodedata.normalize(encoding, word)
        if len(" ".join(current + [word]).encode()) > 7000:
            yield " ".join(current)
            current = []
        current.append(word)
    if current:
        yield " ".join(current)


def native_entries():
    return (
        read(SOURCE)["complete_native_entries"]
        | read(DERIVED)["complete_native_entries"]
        | read(ADDITIONAL)["complete_native_entries"]
    )


def post(url, route, body):
    request = urllib.request.Request(
        url + route,
        json.dumps(body, ensure_ascii=False).encode(),
        {"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        assert response.status == 200
        return json.load(response)


def freeze(cli, web, bridge, url, output):
    assert not output.exists()
    cases, words = cases_and_words()
    observations = read(OBSERVATIONS)
    assert sha(cli) == observations["cli_sha256"]
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    assert sha(db) == observations["dictionary_sha256"]
    with urllib.request.urlopen(url + "/api/status") as response:
        status = json.load(response)
    records_by_encoding, comparisons, components, unique = {}, [], {}, {}
    for encoding in ("NFC", "NFD"):
        found = {}
        for index, text in enumerate(chunks(words, encoding)):
            actual = post(url, "/api/analyze", {"text": text, "suggest_spacing": True})
            expected = [
                json.loads(line)
                for line in subprocess.check_output(
                    [
                        str(cli),
                        "text",
                        "-",
                        "--dictionary",
                        str(db),
                        "--suggest-spacing",
                    ],
                    input=text.encode(),
                ).splitlines()
            ]
            assert actual["records"] == expected, (encoding, index, "API/CLI parity")
            assert len(actual["breakdowns"]) == len(expected)
            for record, ordered in zip(expected, actual["breakdowns"], strict=True):
                if record["kind"] != "word":
                    assert ordered is None
                    continue
                surface = record["analysis"]["normalized"]
                assert surface not in found
                found[surface] = record
                assert len(ordered) == len(record["analysis"]["analyses"])
                for analysis, breakdown in zip(
                    record["analysis"]["analyses"], ordered, strict=True
                ):
                    key = digest(analysis)
                    unique[key] = analysis
                    if key in components:
                        assert components[key] == breakdown
                    components[key] = breakdown
            comparisons.append(
                {
                    "encoding": encoding,
                    "batch": index,
                    "input_sha256": digest(text),
                    "records": len(expected),
                    "cli_records_sha256": digest(expected),
                    "api_records_sha256": digest(actual["records"]),
                    "passed": True,
                }
            )
        assert set(found) == set(words)
        records_by_encoding[encoding] = found
    keys = sorted(unique)
    raw = subprocess.check_output(
        [str(bridge)],
        input="".join(
            json.dumps(unique[k], ensure_ascii=False) + "\n" for k in keys
        ).encode(),
    )
    for key, line in zip(keys, raw.splitlines(), strict=True):
        proof = json.loads(line)
        assert not proof["reviewed_removal"] and components[key] == proof["components"]
    judgments = []
    for encoding, found in records_by_encoding.items():
        for case in cases:
            analyses = found[case["surface"]]["analysis"]["analyses"]
            for judgment in case["judgments"]:
                present = any(matches(a, judgment) for a in analyses)
                assert present == (judgment["verdict"] == "required"), (
                    encoding,
                    case["id"],
                    judgment["id"],
                )
                judgments.append(
                    {
                        "id": case["id"],
                        "judgment": judgment["id"],
                        "encoding": encoding,
                        "verdict": judgment["verdict"],
                        "passed": True,
                    }
                )
    entries = native_entries()
    for ident, entry in entries.items():
        assert post(url, "/api/entry", {"id": ident})["entry"] == entry, ident
    report = {
        "schema_version": 1,
        "checklist": "COV-017bu",
        "source_sha256": sha(SOURCE),
        "observations_sha256": sha(OBSERVATIONS),
        "corrections_sha256": sha(CORRECTIONS),
        "policy_sha256": sha(POLICY),
        "cli_sha256": sha(cli),
        "web_sha256": sha(web),
        "bridge_sha256": sha(bridge),
        "dictionary_sha256": sha(db),
        "status": status,
        "words": words,
        "comparisons": comparisons,
        "judgments": judgments,
        "native_entries": len(entries),
        "native_entries_sha256": digest(entries),
        "ordered_candidate_shapes": len(unique),
        "all_api_components_match_rust": True,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"Verified packaged API/CLI parity for {len(words)} words in NFC/NFD, {len(judgments)} judgments and {len(entries)} complete native endpoints."
    )


def verify():
    report, observations = read(REPORT), read(OBSERVATIONS)
    cases, words = cases_and_words()
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bu"
    for field, path in (
        ("source_sha256", SOURCE),
        ("observations_sha256", OBSERVATIONS),
        ("corrections_sha256", CORRECTIONS),
        ("policy_sha256", POLICY),
    ):
        assert report[field] == sha(path)
    assert report["cli_sha256"] == observations["cli_sha256"]
    assert report["dictionary_sha256"] == observations["dictionary_sha256"]
    assert report["words"] == words
    expected = {
        (c["id"], j["id"], e, j["verdict"])
        for c in cases
        for j in c["judgments"]
        for e in ("NFC", "NFD")
    }
    actual = {
        (j["id"], j["judgment"], j["encoding"], j["verdict"])
        for j in report["judgments"]
    }
    assert expected == actual and len(report["judgments"]) == len(expected)
    assert all(j["passed"] for j in report["judgments"])
    for encoding in ("NFC", "NFD"):
        selected = [r for r in report["comparisons"] if r["encoding"] == encoding]
        texts = list(chunks(words, encoding))
        assert len(selected) == len(texts)
        for i, (row, text) in enumerate(zip(selected, texts, strict=True)):
            assert row["batch"] == i and row["input_sha256"] == digest(text)
            assert (
                row["passed"] and row["cli_records_sha256"] == row["api_records_sha256"]
            )
    entries = native_entries()
    assert report["native_entries"] == len(entries) and report[
        "native_entries_sha256"
    ] == digest(entries)
    assert report["all_api_components_match_rust"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    print(
        f"Verified packaged runtime evidence: {len(words)} words, {len(expected)} encoded judgments and {len(entries)} complete native endpoints."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--web", type=Path)
    parser.add_argument("--bridge", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.web and args.bridge and args.url and args.output
        freeze(
            args.cli.resolve(),
            args.web.resolve(),
            args.bridge.resolve(),
            args.url,
            args.output,
        )


if __name__ == "__main__":
    main()
