"""Capture release/debug parity and the complete Unicode identity API cohort."""

import argparse
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from doeda_identity_audit import FIXTURE, cohort
from doeda_identity_audit import REPORT as PREFLIGHT
from doeda_identity_diagnostics import REPORT as DIAGNOSTICS
from lexical_nada_audit import ROOT, read, sha, write

p = argparse.ArgumentParser()
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--url", required=True)
p.add_argument("--output", type=Path, required=True)
args = p.parse_args()
assert not args.output.exists()
source, diagnostic, fixture = read(PREFLIGHT), read(DIAGNOSTICS), read(FIXTURE)
cli = args.cli.resolve()
db = ROOT / "data/dictionaries/krdict/krdict.db"
assert sha(db) == source["dictionary_sha256"]
parity = {}
for mode, flags in [
    ("raw", []),
    ("headword", ["--dict-only"]),
    ("compatible", ["--dict-compatible"]),
]:
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
    print(mode, len(rows), "debug/release records agree", flush=True)


def post(path, data):
    req = urllib.request.Request(
        args.url + "/api/" + path,
        data=json.dumps(data, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as res:
        assert res.status == 200
        return json.load(res)


expected = {
    r["analysis"]["normalized"]: r
    for r in diagnostic["after_streams"]["raw"]
    if r["kind"] == "word"
}
words = cohort(fixture)
assert sorted(expected) == words
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
        assert api["records"] == [json.loads(l) for l in out.stdout.splitlines()]
        found = {
            r["analysis"]["normalized"]: (r, orders)
            for r, orders in zip(api["records"], api["breakdowns"], strict=True)
            if r["kind"] == "word"
        }
        assert set(found) == set(chunk)
        for word in chunk:
            record, orders = found[word]
            old = expected[word]
            assert (
                record["analysis"] == old["analysis"]
                and record["dictionary"] == old["dictionary"]
            )
            for a, r, order in zip(
                record["analysis"]["analyses"],
                record["dictionary"]["readings"],
                orders,
                strict=True,
            ):
                for lemma in r["lemmas"]:
                    for entry in lemma["entries"]:
                        identity = entry.get("derivational_identity")
                        if identity:
                            assert order[:2] == [
                                {"lemma": lemma["lemma_index"]},
                                {"morpheme": identity["morpheme_index"]},
                            ]
                            assert a["morphemes"][identity["morpheme_index"]] == {
                                "form": "되다",
                                "kind": "suffix",
                            }
        batches.append(
            {
                "encoding": encoding,
                "batch": n,
                "words": chunk,
                "text": text,
                "api": api,
                "cli_jsonl": out.stdout,
                "cli_jsonl_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
            }
        )
        print(encoding, n, len(chunk), "API words exactly agree", flush=True)
entries = {}
for ident, entry in source["complete_native_entries"].items():
    actual = post("entry", {"id": ident})["entry"]
    assert actual == entry
    entries[ident] = actual
print(len(entries), "full native entries agree", flush=True)
script = Path(__file__)
write(
    args.output,
    {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(PREFLIGHT),
        "diagnostics_sha256": sha(DIAGNOSTICS),
        "fixture_sha256": sha(FIXTURE),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(db),
        "release_parity": parity,
        "batches": batches,
        "words_checked": sum(len(b["words"]) for b in batches),
        "native_entries": entries,
        "producer": {"text": script.read_text(), "sha256": sha(script)},
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    },
)
