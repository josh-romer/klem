import argparse
import gzip
import hashlib
import json
import unicodedata
import urllib.request
from pathlib import Path

p = argparse.ArgumentParser(
    description="Verify full native HTTP entries and individual reported-ending paths."
)
p.add_argument("--url", required=True)
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
settings = p.parse_args()
assert not settings.output.exists()
url = settings.url


def read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt") as stream:
            return json.load(stream)
    return json.loads(Path(path).read_text())


assert (
    hashlib.sha256(settings.cli.read_bytes()).hexdigest()
    == read("docs/reported-retrospective-observations.json.gz")["cli_sha256"]
)
source = read("docs/reported-retrospective-source-preflight.json.gz")
core = read("tests/fixtures/reported-retrospective-sources.json")
correction = read("tests/fixtures/reported-retrospective-corrections.json")
followers = read("tests/fixtures/reported-retrospective-followers.json")
boundaries = read("tests/fixtures/reported-retrospective-boundaries.json")
additional = read("tests/fixtures/reported-retrospective-additional-native.json")
native = (
    source["complete_native_entries"]
    | correction["complete_native_entries"]
    | additional["complete_native_entries"]
)
changes = {x["original"]["id"]: x["replacement"] for x in correction["superseded"]}
cases = (
    [changes.get(c["id"], c) for c in core["cases"] + followers["cases"]]
    + correction["cases"]
    + boundaries["cases"]
)


def post(route, body):
    req = urllib.request.Request(
        url + "/api/" + route,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    return json.load(urllib.request.urlopen(req, timeout=60))


for ident, entry in native.items():
    assert post("entry", {"id": ident})["entry"] == entry, ident
print(len(native), "full native endpoints verified", flush=True)
judgments = []
for encoding in ["NFC", "NFD"]:
    chunks = []
    current = []
    for surface in sorted({c["surface"] for c in cases}):
        word = unicodedata.normalize(encoding, surface)
        if len(" ".join(current + [word]).encode()) > 7000:
            chunks.append(" ".join(current))
            current = []
        current.append(word)
    if current:
        chunks.append(" ".join(current))
    records = {}
    for chunk in chunks:
        response = post(
            "analyze", {"text": "前🙂「" + chunk + "」", "suggest_spacing": True}
        )
        for record in response["records"]:
            if record.get("analysis"):
                records[record["analysis"]["normalized"]] = record
    for case in cases:
        record = records[case["surface"]]
        paths = record["analysis"]["analyses"]
        found = []
        for i, a in enumerate(paths):
            if (
                [l["text"] for l in a["lemmas"]] == case["lemmas"]
                and [l["kind"] for l in a["lemmas"]] == case["lemma_kinds"]
                and [m["form"] for m in a["morphemes"]] == case["morphemes"]
            ):
                found.append(i)
        assert bool(found) == (case["verdict"] == "required"), case["id"]
        for i in found:
            assert "ending.reporting_retrospective" in paths[i]["rules"]
            if "ending_owner_status" in case:
                assert (
                    record["dictionary"]["readings"][i]["lemmas"][-1]["status"]
                    == case["ending_owner_status"]
                ), case["id"]
        judgments.append(
            {
                "id": case["id"],
                "encoding": encoding,
                "verdict": case["verdict"],
                "passed": True,
            }
        )
    print(encoding, len(cases), "individual candidate judgments verified", flush=True)
settings.output.write_text(
    json.dumps(
        {
            "schema_version": 1,
            "native_entries": len(native),
            "judgments": judgments,
            "cli_sha256": read("docs/reported-retrospective-observations.json.gz")[
                "cli_sha256"
            ],
            "source_sha256": hashlib.sha256(
                Path(
                    "docs/reported-retrospective-source-preflight.json.gz"
                ).read_bytes()
            ).hexdigest(),
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n"
)
