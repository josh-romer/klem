"""Packaged native cohort parity and exact Unicode/API ownership checks."""

import argparse
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from doeda_native_diagnostics import REPORT as DIAGNOSTICS
from doeda_native_preflight import REPORT as PREFLIGHT
from doeda_native_preflight import expected
from lexical_nada_audit import ROOT, read, sha, write

p = argparse.ArgumentParser()
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--url", required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
assert not args.output.exists()
cli = args.cli.resolve()
db = ROOT / "data/dictionaries/krdict/krdict.db"
source = read(PREFLIGHT)
diagnostic = read(DIAGNOSTICS)
assert sha(db) == source["dictionary_sha256"]
parity = {}
for mode, flags in (
    ("raw", []),
    ("headword", ["--dict-only"]),
    ("compatible", ["--dict-compatible"]),
):
    out = subprocess.run(
        [str(cli), "text", "-", "--dictionary", str(db), *flags],
        input=source["before_input"],
        text=True,
        capture_output=True,
        check=True,
    )
    rows = [json.loads(l) for l in out.stdout.splitlines()]
    assert rows == diagnostic["after_streams"][mode]
    parity[mode] = {
        "records": len(rows),
        "jsonl_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
    }
    print(mode, len(rows), "complete debug/release records agree", flush=True)


def post(path, data):
    req = urllib.request.Request(
        args.url + "/api/" + path,
        data=json.dumps(data, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        assert res.status == 200
        return json.load(res)


case_by_word = {c["surface"]: c for c in source["cases"]}
words = sorted(case_by_word)
batches = []
for encoding in ("NFC", "NFD"):
    chunks = []
    chunk = []
    for word in words:
        if (
            chunk
            and len(unicodedata.normalize(encoding, " ".join(chunk + [word])).encode())
            > 7500
        ):
            chunks.append(chunk)
            chunk = []
        chunk.append(word)
    if chunk:
        chunks.append(chunk)
    for n, chunk in enumerate(chunks):
        text = unicodedata.normalize(encoding, " ".join(chunk))
        api = post("analyze", {"text": text})
        out = subprocess.run(
            [str(cli), "text", "-", "--dictionary", str(db)],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        actual = [json.loads(l) for l in out.stdout.splitlines()]
        assert api["records"] == actual
        selected = [case_by_word[word] for word in chunk]
        found = {
            r["analysis"]["normalized"]: (r, orders)
            for r, orders in zip(api["records"], api["breakdowns"], strict=True)
            if r["kind"] == "word"
        }
        for c in selected:
            record, orders = found[c["surface"]]
            indices = [
                i
                for i, a in enumerate(record["analysis"]["analyses"])
                if expected(a, c)
            ]
            assert indices, c["id"]
            for i in indices:
                a = record["analysis"]["analyses"][i]
                order = orders[i]
                assert order[:2] == [{"lemma": 0}, {"morpheme": 0}], c["id"]
                assert [x["lemma"] for x in order if "lemma" in x] == list(
                    range(len(a["lemmas"]))
                )
                assert [x["morpheme"] for x in order if "morpheme" in x] == list(
                    range(len(a["morphemes"]))
                )
                assert record["dictionary"]["readings"][i]["status"] == "compatible", c[
                    "id"
                ]
        batches.append(
            {
                "encoding": encoding,
                "batch": n,
                "text": text,
                "cases": [c["id"] for c in selected],
                "api": api,
                "cli_jsonl_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
            }
        )
        print(
            encoding,
            n,
            len(selected),
            "API cases match CLI and owned order",
            flush=True,
        )
assert sum(len(b["cases"]) for b in batches) == 31400
entries = {}
for ident, expected_entry in source["complete_native_entries"].items():
    actual = post("entry", {"id": ident})["entry"]
    assert actual == expected_entry, ident
    entries[ident] = actual
print(len(entries), "complete native endpoints agree", flush=True)
files = {
    p: {"text": (ROOT / p).read_text(), "sha256": sha(ROOT / p)}
    for p in diagnostic["implementation_files"]
}
report = {
    "schema_version": 1,
    "checklist": "COV-022m",
    "preflight_sha256": sha(PREFLIGHT),
    "diagnostics_sha256": sha(DIAGNOSTICS),
    "cli_sha256": sha(cli),
    "dictionary_sha256": sha(db),
    "source_release_parity": parity,
    "case_judgments": 31400,
    "batches": batches,
    "native_endpoint_entries": entries,
    "implementation_files": files,
    "producer": {"text": Path(__file__).read_text(), "sha256": sha(Path(__file__))},
    "contextual_verdict": "unjudged",
    "independent_review": "pending",
}
write(args.output, report)
print("Archived packaged native API evidence", flush=True)
