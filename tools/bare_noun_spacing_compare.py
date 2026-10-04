"""Compare complete baseline streams for opt-in, additive spacing hypotheses."""

import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAIRS = {"신경질": "내다", "용기": "내다", "짜증": "내다", "기분": "내키다"}
RULE = "spacing.bare_noun_lexical_verb"


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def canon(v):
    return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--before-cli", type=Path, required=True)
p.add_argument("--cli", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
assert not a.output.exists()
a.cli = a.cli.resolve()
a.before_cli = a.before_cli.resolve()
db = ROOT / "data/dictionaries/krdict/krdict.db"
source = json.loads(
    (ROOT / "tests/fixtures/bare-noun-spacing-sources.json").read_text()
)
assert sha(db) == source["dictionary_sha256"]
assert sha(a.before_cli) == source["cli_sha256"]
prior = json.loads((ROOT / "docs/continuation-left-observations.json").read_text())
words = {}
changes = {}
metadata = {}
comparisons = []


def independent(surface):
    if surface not in words:
        words[surface] = json.loads(
            subprocess.check_output(
                [str(a.cli), "word", surface, "--dictionary", str(db)]
            )
        )
    return words[surface]


def known(record, pos):
    w = record["analysis"]
    d = record["dictionary"]
    for path, reading, breakdown in zip(
        w["analyses"], d["readings"], record["breakdowns"], strict=True
    ):
        raw = independent(record["surface"])
        i = raw["analyses"].index(path)
        assert reading == raw["dictionary"]["readings"][i]
        assert breakdown is not None
        head = path["lemmas"][0]
        slots = [s for s in d["lemmas"] if s["lemma"] == head]
        assert len(slots) == 1
        assert any(
            e["entry"]["headword"] == head["text"]
            and e["entry"]["pos"] == pos
            and any(
                r["id"] == e["entry"]["id"] and r["status"] != "incompatible"
                for r in reading["lemmas"][0]["entries"]
            )
            for e in slots[0]["entries"]
        )


def verify_hyp(h, record):
    assert h["rule"] == RULE
    rs = h["records"]
    assert len(rs) >= 2
    noun, right = rs[-2:]
    head = noun["analysis"]["normalized"]
    assert head in PAIRS
    assert all(
        x["unchanged"]
        and len(x["lemmas"]) == 1
        and x["lemmas"][0] == {"text": head, "kind": "unclassified"}
        and not x["morphemes"]
        for x in noun["analysis"]["analyses"]
    )
    assert all(
        x["lemmas"][0] == {"text": PAIRS[head], "kind": "predicate"}
        for x in right["analysis"]["analyses"]
    )
    known(noun, "명사")
    known(right, "동사")
    assert "".join(r["surface"] for r in rs) == record["surface"]
    assert h["spaced"] == " ".join(r["surface"] for r in rs)
    assert h["inserted_at"] == [r["span"]["start"] for r in rs[1:]]
    start = record["span"]["start"]
    raw = record["surface"].encode()
    for r in rs:
        assert r["span"]["start"] == start
        assert (
            raw[
                r["span"]["start"] - record["span"]["start"] : r["span"]["end"]
                - record["span"]["start"]
            ].decode()
            == r["surface"]
        )
        start = r["span"]["end"]
    assert start == record["span"]["end"]


def compare(b, a, mode, location, context):
    assert {k: v for k, v in b.items() if k != "spacing"} == {
        k: v for k, v in a.items() if k != "spacing"
    }, (mode, location, "default analysis changed")
    bs, ns = b["spacing"], a["spacing"]
    assert bs["rule"] == ns["rule"] and bs["limits"] == ns["limits"]
    assert ns["segment_probes"] >= bs["segment_probes"]
    assert ns["segment_probes"] <= ns["limits"]["segment_probes"]
    assert len(ns["alternatives"]) <= ns["limits"]["alternatives"]
    assert [h for h in ns["alternatives"] if h.get("rule") is None] == bs[
        "alternatives"
    ], (mode, location, "legacy hypotheses changed")
    for h in ns["alternatives"]:
        if h.get("rule") is None:
            continue
        verify_hyp(h, a)
        key = canon([a["surface"], h])
        ident = (
            "bare-noun-spacing-change-" + hashlib.sha256(key.encode()).hexdigest()[:24]
        )
        if key not in changes:
            changes[key] = dict(
                id=ident,
                surface=a["surface"],
                hypothesis=h,
                occurrences=[],
                contextual_verdict="unjudged",
                independent_review="pending",
            )
        changes[key]["occurrences"].append(
            dict(mode=mode, record=location, span=a["span"], context=context)
        )
    bm = {k: v for k, v in bs.items() if k != "alternatives"}
    am = {k: v for k, v in ns.items() if k != "alternatives"}
    if bm != am:
        key = canon([a["surface"], bm, am])
        ident = (
            "bare-noun-spacing-work-" + hashlib.sha256(key.encode()).hexdigest()[:24]
        )
        if key not in metadata:
            metadata[key] = dict(
                id=ident, surface=a["surface"], before=bm, after=am, occurrences=[]
            )
        metadata[key]["occurrences"].append(
            dict(mode=mode, record=location, span=a["span"])
        )
    if not ns["complete"]:
        assert ns["limited_by"]
    if not bs["complete"]:
        assert bs == ns


for old in prior["comparisons"]:
    mode, path = old["mode"], Path(old["source"])
    assert sha(path) == old["source_sha256"]
    content = path.read_bytes()
    flags = (
        ["--dict-compatible"]
        if "compatible" in mode
        else ["--dict-only"]
        if "headword" in mode
        else []
    )
    cmd = ["text", str(path), "--dictionary", str(db), *flags] + (
        ["--suggest-spacing"] if "spacing" in mode else []
    )
    procs = [
        subprocess.Popen([str(cli), *cmd], stdout=subprocess.PIPE)
        for cli in [a.before_cli, a.cli]
    ]
    hashes = [hashlib.sha256(), hashlib.sha256()]
    count = changed = 0
    try:
        for b, after in itertools.zip_longest(*(p.stdout for p in procs)):
            assert b is not None and after is not None
            count += 1
            hashes[0].update(b)
            hashes[1].update(after)
            if b != after:
                assert "spacing" in mode
                bj, aj = json.loads(b), json.loads(after)
                span = aj["span"]
                context = content[
                    max(0, span["start"] - 120) : min(len(content), span["end"] + 120)
                ].decode(errors="replace")
                compare(bj, aj, mode, count - 1, context)
                changed += 1
            if count % 25000 == 0:
                print(mode, count, "records checked", flush=True)
        assert all(p.wait() == 0 for p in procs)
    finally:
        for process in procs:
            if process.poll() is None:
                process.terminate()
            process.wait()
    assert (
        count == old["records"] and hashes[0].hexdigest() == old["after_jsonl_sha256"]
    ), (mode, count, hashes[0].hexdigest())
    comparisons.append(
        dict(
            mode=mode,
            source=str(path),
            source_sha256=sha(path),
            records=count,
            before_jsonl_sha256=hashes[0].hexdigest(),
            after_jsonl_sha256=hashes[1].hexdigest(),
            changed_records=changed,
        )
    )
    print(mode, count, "records;", changed, "changed", flush=True)
report = dict(
    schema_version=1,
    checklist="COV-020q",
    before_revision=source["before_revision"],
    before_cli=str(a.before_cli),
    before_cli_sha256=sha(a.before_cli),
    cli=str(a.cli),
    cli_sha256=sha(a.cli),
    dictionary_sha256=sha(db),
    comparisons=comparisons,
    added_hypotheses=list(changes.values()),
    work_metadata_changes=list(metadata.values()),
    default_records_byte_identical=True,
    legacy_spacing_hypotheses_and_order_preserved=True,
    all_baseline_stream_hashes_verified=True,
    contextual_verdict="unjudged",
)
a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(
    "Verified",
    sum(c["records"] for c in comparisons),
    "records;",
    len(changes),
    "new hypotheses;",
    len(metadata),
    "work metadata changes",
    flush=True,
)
