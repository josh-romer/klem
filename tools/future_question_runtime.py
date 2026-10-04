"""Validate native entries, finite cases, Unicode offsets and all CLI filters via HTTP."""

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
with gzip.open(ROOT / "docs/future-question-source-preflight.json.gz", "rt") as file:
    source = json.load(file)
fixture = json.loads((ROOT / "tests/fixtures/future-question-sources.json").read_text())
selected = dict(source["complete_native_entries"])
selected.update(
    json.loads(
        (ROOT / "tests/fixtures/future-question-additional-native.json").read_text()
    )["complete_native_entries"]
)
fixture["before_words"].update(
    json.loads(
        (ROOT / "tests/fixtures/future-question-corpus-supplement.json").read_text()
    )["before_words"]
)
surfaces = sorted(fixture["before_words"])


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


def chunks(words, encoding):
    current = []
    for word in words:
        word = unicodedata.normalize(encoding, word)
        if len(("前🙂「" + " ".join(current + [word]) + "」").encode()) > 7000:
            yield "前🙂「" + " ".join(current) + "」"
            current = []
        current.append(word)
    if current:
        yield "前🙂「" + " ".join(current) + "」"


def matched(path, case):
    return (
        [l["text"] for l in path["lemmas"]] == case["lemmas"]
        and [l["kind"] for l in path["lemmas"]] == case["lemma_kinds"]
        and [m["form"] for m in path["morphemes"]] == case["morphemes"]
    )


for ident, native in selected.items():
    assert post("entry", {"id": ident})["entry"] == native, ident
print("Full native entry endpoints:", len(selected), "verified", flush=True)
checks = []
judgments = []
for encoding in ["NFC", "NFD"]:
    for batch, text in enumerate(chunks(surfaces, encoding)):
        response = post("analyze", {"text": text, "suggest_spacing": True})
        plain = post("analyze", {"text": text})
        api = response["records"]
        assert plain["records"] == [
            {k: v for k, v in r.items() if k != "spacing"} for r in api
        ]
        words = {r["analysis"]["normalized"]: r for r in api if r.get("analysis")}
        for canonical, record in words.items():
            if canonical in fixture["before_words"]:
                old = fixture["before_words"][canonical]["analysis"]
                raw = record["analysis"]
                assert [a for a in raw["analyses"] if a in old["analyses"]] == old[
                    "analyses"
                ], canonical
        for case in fixture["cases"]:
            if case["surface"] not in words:
                continue
            record = words[case["surface"]]
            present = any(
                matched(path, case) for path in record["analysis"]["analyses"]
            )
            assert present == (case["verdict"] == "required"), (
                case["id"],
                record["spacing"],
            )
            judgments.append(
                {
                    "id": case["id"],
                    "encoding": encoding,
                    "verdict": case["verdict"],
                    "matched": present,
                    "complete": record["spacing"]["complete"],
                }
            )
        for cache in [0, 1, 4096]:
            for mode, flags in [
                ("all", []),
                ("headword", ["--dict-only"]),
                ("compatible", ["--dict-compatible"]),
            ]:
                cmd = [
                    str(cli),
                    "text",
                    "-",
                    "--dictionary",
                    str(db),
                    "--cache-bytes",
                    str(cache),
                    *flags,
                ]
                before = list(
                    map(
                        json.loads,
                        subprocess.check_output(cmd, input=text.encode()).splitlines(),
                    )
                )
                data = subprocess.check_output(
                    cmd + ["--suggest-spacing"], input=text.encode()
                )
                after = list(map(json.loads, data.splitlines()))
                assert before == [
                    {k: v for k, v in r.items() if k != "spacing"} for r in after
                ]
                for r, ar in zip(after, api, strict=True):
                    assert (
                        text.encode()[r["span"]["start"] : r["span"]["end"]].decode()
                        == r["surface"]
                    )
                    if r.get("analysis"):
                        assert r["spacing"] == ar["spacing"]
                        assert [
                            x
                            for x in ar["analysis"]["analyses"]
                            if x in r["analysis"]["analyses"]
                        ] == r["analysis"]["analyses"]
                        for path, reading in zip(
                            r["analysis"]["analyses"],
                            r["dictionary"]["readings"],
                            strict=True,
                        ):
                            index = ar["analysis"]["analyses"].index(path)
                            assert reading == ar["dictionary"]["readings"][index]
                    if mode == "all":
                        assert r == ar
                checks.append(
                    {
                        "encoding": encoding,
                        "batch": batch,
                        "mode": mode,
                        "cache_bytes": cache,
                        "records": len(after),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
        print(
            encoding, batch, "API/raw/filter/cache/offset parity verified", flush=True
        )
assert len(judgments) == 2 * len(fixture["cases"])
result = {
    "schema_version": 1,
    "source_sha256": sha(ROOT / "docs/future-question-source-preflight.json.gz"),
    "checklist": "COV-018ab / COV-020r",
    "cli": str(cli),
    "cli_sha256": sha(cli),
    "dictionary_sha256": sha(db),
    "url": a.url,
    "native_entries": len(selected),
    "surfaces": len(surfaces),
    "checks": checks,
    "judgments": judgments,
    "contextual_verdict": "unjudged",
    "independent_review": "pending",
}
a.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
