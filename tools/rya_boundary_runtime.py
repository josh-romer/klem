"""Check full native HTTP entries and canonical -랴/concessive/unknown case parity."""

import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path.cwd()
p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--url", required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
cli = a.cli.resolve()
db = ROOT / "data/dictionaries/krdict/krdict.db"
with gzip.open(ROOT / "docs/rya-boundary-source-preflight.json.gz", "rt") as f:
    source = json.load(f)
fixture = json.loads((ROOT / "tests/fixtures/rya-boundary-sources.json").read_text())
words = sorted(
    r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
)


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def post(route, body):
    request = urllib.request.Request(
        a.url + "/api/" + route,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def matched(path, case):
    return (
        [l["text"] for l in path["lemmas"]] == case["lemmas"]
        and [l["kind"] for l in path["lemmas"]] == case["lemma_kinds"]
        and [m["form"] for m in path["morphemes"]] == case["morphemes"]
    )


for ident, native in source["complete_native_entries"].items():
    assert post("entry", {"id": ident})["entry"] == native, ident
print(
    len(source["complete_native_entries"]), "full native endpoints verified", flush=True
)
checks = []
cases = []
for encoding in ["NFC", "NFD"]:
    text = "前🙂「" + " ".join(unicodedata.normalize(encoding, w) for w in words) + "」"
    response = post("analyze", {"text": text, "suggest_spacing": True})
    plain = post("analyze", {"text": text})
    assert plain["records"] == [
        {k: v for k, v in r.items() if k != "spacing"} for r in response["records"]
    ]
    records = {
        r["analysis"]["normalized"]: r for r in response["records"] if r.get("analysis")
    }
    for case in fixture["cases"]:
        r = records[case["surface"]]
        paths = r["analysis"]["analyses"]
        if case["verdict"] == "required":
            assert any(matched(path, case) for path in paths), case["id"]
        elif case["verdict"] == "forbidden":
            assert not any(
                any(l["text"] == case["lemma"] for l in path["lemmas"])
                and (
                    (
                        any(m["form"] == "으랴" for m in path["morphemes"])
                        and path["morphemes"][-1]["form"] in ["마는", "요"]
                    )
                    or any(
                        m["kind"] == "particle" and m["form"] == "마는"
                        for m in path["morphemes"]
                    )
                )
                for path in paths
            ), case["id"]
        else:
            found = False
            for path, reading in zip(paths, r["dictionary"]["readings"], strict=True):
                if "ending.rya" not in path["rules"]:
                    continue
                for slot, lemma in enumerate(path["lemmas"]):
                    if lemma["text"] == case["lemma"]:
                        entries = reading["lemmas"][slot]["entries"]
                        assert all(e["status"] != "compatible" for e in entries)
                        found = found or any(e["status"] == "unknown" for e in entries)
            assert found, case["id"]
        cases.append(
            {
                "id": case["id"],
                "encoding": encoding,
                "verdict": case["verdict"],
                "passed": True,
            }
        )
    for cache in [0, 1, 4096]:
        for mode, flags in [
            ("all", []),
            ("headword", ["--dict-only"]),
            ("compatible", ["--dict-compatible"]),
        ]:
            command = [
                str(cli),
                "text",
                "-",
                "--dictionary",
                str(db),
                "--cache-bytes",
                str(cache),
                *flags,
            ]
            raw = subprocess.check_output(command, input=text.encode())
            data = subprocess.check_output(
                command + ["--suggest-spacing"], input=text.encode()
            )
            before = list(map(json.loads, raw.splitlines()))
            after = list(map(json.loads, data.splitlines()))
            assert before == [
                {k: v for k, v in r.items() if k != "spacing"} for r in after
            ]
            for r, api in zip(after, response["records"], strict=True):
                assert (
                    text.encode()[r["span"]["start"] : r["span"]["end"]].decode()
                    == r["surface"]
                )
                if r.get("analysis"):
                    assert r["spacing"] == api["spacing"]
                    assert [
                        p
                        for p in api["analysis"]["analyses"]
                        if p in r["analysis"]["analyses"]
                    ] == r["analysis"]["analyses"]
                    for path, reading in zip(
                        r["analysis"]["analyses"],
                        r["dictionary"]["readings"],
                        strict=True,
                    ):
                        assert (
                            reading
                            == api["dictionary"]["readings"][
                                api["analysis"]["analyses"].index(path)
                            ]
                        )
                if mode == "all":
                    assert r == api
            checks.append(
                {
                    "encoding": encoding,
                    "mode": mode,
                    "cache_bytes": cache,
                    "records": len(after),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    print(
        encoding,
        "finite cases, filters/cache/API/CLI/offset parity verified",
        flush=True,
    )
value = {
    "schema_version": 1,
    "checklist": "COV-017br",
    "source_sha256": sha(ROOT / "docs/rya-boundary-source-preflight.json.gz"),
    "cli_sha256": sha(cli),
    "dictionary_sha256": sha(db),
    "native_entries": len(source["complete_native_entries"]),
    "words": len(words),
    "checks": checks,
    "cases": cases,
    "contextual_verdict": "unjudged",
    "independent_review": "pending",
}
a.output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
