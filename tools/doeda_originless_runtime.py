"""Capture all finite originless API words and full native dictionary endpoints."""

import argparse
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as PREFLIGHT
from doeda_originless_diagnostics import REPORT as DIAGNOSTICS
from doeda_originless_diagnostics import check_identity
from lexical_nada_audit import ROOT, read, sha, write
from lexical_nada_compare import canon


def capture(args):
    assert not args.output.exists()
    source, diagnostic, fixture = read(PREFLIGHT), read(DIAGNOSTICS), read(FIXTURE)
    cli = args.cli.resolve()
    db = ROOT / "data/dictionaries/krdict/krdict.db"
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
        rows = [json.loads(line) for line in out.stdout.splitlines()]
        assert rows == diagnostic["after_streams"][mode]
        parity[mode] = {
            "records": len(rows),
            "jsonl": out.stdout,
            "jsonl_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
        }
        print(mode, len(rows), "release/debug records agree", flush=True)

    def post(path, data):
        req = urllib.request.Request(
            args.url + "/api/" + path,
            data=json.dumps(data, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            assert response.status == 200
            return json.load(response)

    expected = {
        r["analysis"]["normalized"]: r
        for r in diagnostic["after_streams"]["raw"]
        if r["kind"] == "word"
    }
    words = sorted(expected)
    assert len(words) == 254
    batches = []
    for encoding in ("NFC", "NFD"):
        chunks, chunk = [], []
        for word in words:
            if (
                chunk
                and len(
                    unicodedata.normalize(encoding, " ".join(chunk + [word])).encode()
                )
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
            assert api["records"] == [
                json.loads(line) for line in out.stdout.splitlines()
            ]
            found = {
                r["analysis"]["normalized"]: (r, orders)
                for r, orders in zip(api["records"], api["breakdowns"], strict=True)
                if r["kind"] == "word"
            }
            assert set(found) == set(chunk)
            components = {}
            for word in chunk:
                record, orders = found[word]
                assert (
                    record["analysis"] == expected[word]["analysis"]
                    and record["dictionary"] == expected[word]["dictionary"]
                )
                for analysis, order in zip(
                    record["analysis"]["analyses"], orders, strict=True
                ):
                    key = canon(analysis)
                    assert key not in components or components[key] == order
                    components[key] = order
                    assert order == diagnostic["owned_components"][key]
            check_identity(api["records"], components, fixture["formations"])
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
            print(
                encoding,
                n,
                len(chunk),
                "API words and ordered components agree",
                flush=True,
            )
    entries = {}
    for ident, entry in source["complete_native_entries"].items():
        actual = post("entry", {"id": ident})["entry"]
        assert actual == entry
        entries[ident] = actual
    print(len(entries), "complete native entries agree", flush=True)
    noun_controls = []
    nouns = [f["base"] for f in fixture["formations"]]
    for encoding in ("NFC", "NFD"):
        text = unicodedata.normalize(encoding, " ".join(nouns))
        api = post("analyze", {"text": text})
        out = subprocess.run(
            [str(cli), "text", "-", "--dictionary", str(db)],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        assert api["records"] == [json.loads(line) for line in out.stdout.splitlines()]
        for r in api["records"]:
            if r["kind"] != "word":
                continue
            assert all(
                "derivational_identity" not in e
                for a in r["dictionary"]["readings"]
                for l in a["lemmas"]
                for e in l["entries"]
            )
            assert all(
                "origins" not in e
                for l in r["dictionary"]["lemmas"]
                if l["lemma"]["kind"] != "root"
                for e in l["entries"]
            )
        noun_controls.append(
            {
                "encoding": encoding,
                "words": nouns,
                "text": text,
                "api": api,
                "cli_jsonl": out.stdout,
                "cli_jsonl_sha256": hashlib.sha256(out.stdout.encode()).hexdigest(),
            }
        )
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
            "ordinary_noun_controls": noun_controls,
            "producer": {"text": script.read_text(), "sha256": sha(script)},
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", type=Path, required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path, required=True)
    capture(parser.parse_args())
