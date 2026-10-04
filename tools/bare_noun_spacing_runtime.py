import argparse
import copy
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--cli", required=True)
p.add_argument("--url", required=True)
p.add_argument("--output", required=True)
a = p.parse_args()
db = root / "data/dictionaries/krdict/krdict.db"
source = json.loads(
    (root / "tests/fixtures/bare-noun-spacing-sources.json").read_text()
)
extra = json.loads(
    (root / "tests/fixtures/bare-noun-spacing-additional-pairs.json").read_text()
)
ledger = json.loads(
    (root / "tests/fixtures/bare-noun-spacing-validity.json").read_text()
)
updates = json.loads(
    (root / "tests/fixtures/bare-noun-spacing-judgment-updates.json").read_text()
)
for u in updates["corrections"]:
    i = next(i for i, c in enumerate(ledger["cases"]) if c["id"] == u["id"])
    assert ledger["cases"][i] == u["original_case"]
    ledger["cases"][i] = u["updated_case"]
ledger["cases"] += extra["cases"]
words = dict(source["before_words"])
words.update(extra["before_words"])
surfaces = sorted(words)
entries = dict(source["complete_native_entries"])
entries.update(extra["complete_native_entries"])


def post(route, body):
    req = urllib.request.Request(
        a.url + "/api/" + route,
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def matched(h, j):
    return (
        h.get("rule") == j["rule"]
        and len(h["records"]) == len(j["segments"])
        and all(
            r["surface"] == e["surface"]
            and any(
                [l["text"] for l in x["lemmas"]] == e["lemmas"]
                and [l["kind"] for l in x["lemmas"]] == e["lemma_kinds"]
                and (
                    j["verdict"] == "forbidden"
                    or [m["form"] for m in x["morphemes"]] == e["morphemes"]
                )
                for x in r["analysis"]["analyses"]
            )
            for r, e in zip(h["records"], j["segments"])
        )
    )


for ident, native in entries.items():
    result = post("entry", {"id": ident})["entry"]
    assert result == native, (ident, result.keys())
print("Full native entry endpoints:", len(entries), "verified", flush=True)
checks = []
judgments = 0
cohorts = []
for encoding in ["NFC", "NFD"]:
    input = (
        "前🙂「" + " ".join(unicodedata.normalize(encoding, s) for s in surfaces) + "」"
    )
    api = post("analyze", {"text": input, "suggest_spacing": True})
    plain = post("analyze", {"text": input})
    apiwords = {
        r["surface"]: r for r in api["records"] if r.get("analysis") is not None
    }
    for br, ar in zip(plain["records"], api["records"], strict=True):
        assert br == {k: v for k, v in ar.items() if k != "spacing"}
    for cache in [0, 1, 4096]:
        for mode, flags in [
            ("all", []),
            ("headword", ["--dict-only"]),
            ("compatible", ["--dict-compatible"]),
        ]:
            cmd = [
                a.cli,
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
                    subprocess.check_output(cmd, input=input.encode()).splitlines(),
                )
            )
            after_bytes = subprocess.check_output(
                cmd + ["--suggest-spacing"], input=input.encode()
            )
            after = list(map(json.loads, after_bytes.splitlines()))
            assert before == [
                {k: v for k, v in r.items() if k != "spacing"} for r in after
            ]
            for r in after:
                assert (
                    input.encode()[r["span"]["start"] : r["span"]["end"]].decode()
                    == r["surface"]
                )
                if not r.get("analysis"):
                    continue
                canonical = unicodedata.normalize("NFC", r["surface"])
                if canonical in words:
                    original = copy.deepcopy(words[canonical][mode])
                    original.pop("spacing")
                    dictionary = original.pop("dictionary")
                    assert (
                        r["analysis"] == original and r["dictionary"] == dictionary
                    ), canonical
                ar = apiwords[r["surface"]]
                assert r["spacing"] == ar["spacing"]
                if mode == "all":
                    assert r == ar
            checks.append(
                dict(
                    encoding=encoding,
                    cache_bytes=cache,
                    mode=mode,
                    records=len(after),
                    sha256=hashlib.sha256(after_bytes).hexdigest(),
                )
            )
    for original in ledger["cases"]:
        c = copy.deepcopy(original)
        for j in c["judgments"]:
            for s in j["segments"]:
                s["surface"] = unicodedata.normalize(encoding, s["surface"])
            r = apiwords[unicodedata.normalize(encoding, c["surface"])]
            assert r["spacing"]["complete"]
            assert any(matched(h, j) for h in r["spacing"]["alternatives"]) == (
                j["verdict"] == "required"
            ), c["id"]
            judgments += 1
    for surface in ["짜증낼", "짜증내시네"]:
        r = apiwords[unicodedata.normalize(encoding, surface)]
        assert not any(
            [l["text"] for l in x["lemmas"]] == ["짜증", "내다"]
            for x in r["analysis"]["analyses"]
        )
        assert any(
            h.get("rule") == "spacing.bare_noun_lexical_verb"
            and any(
                x["lemmas"][0]["text"] == "짜증"
                for x in h["records"][0]["analysis"]["analyses"]
            )
            and any(
                x["lemmas"][0]["text"] == "내다"
                for x in h["records"][1]["analysis"]["analyses"]
            )
            for h in r["spacing"]["alternatives"]
        )
    cohorts.append(
        dict(
            encoding=encoding,
            raw_gold_groups_still_missing=2,
            across_separate_words_groups_recovered=2,
            contextual_verdict="unjudged",
        )
    )
    print(
        encoding,
        len(surfaces),
        "surfaces; 9 CLI cache/filter streams and original UTF-8 spans verified",
        flush=True,
    )
residuals = []
preflight = json.loads(
    (root / "docs/continuation-gold-residual-preflight.json").read_text()
)
for case in preflight["cases"]:
    row = case["original_gold_row"]
    observations = {}
    for mode, flags in [
        ("all", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ]:
        result = json.loads(
            subprocess.check_output(
                [
                    a.cli,
                    "word",
                    row["surface"],
                    "--dictionary",
                    str(db),
                    *flags,
                    "--suggest-spacing",
                ]
            )
        )
        spacing = result.pop("spacing")
        assert result == case["after_words"][mode]
        raw = [
            i
            for i, x in enumerate(result["analyses"])
            if [l["text"] for l in x["lemmas"]] == row["expected"]
        ]
        segmented = []
        for i, h in enumerate(spacing["alternatives"]):
            groups = [
                [[l["text"] for l in x["lemmas"]] for x in r["analysis"]["analyses"]]
                for r in h["records"]
            ]
            import itertools

            if any(
                sum(combination, []) == row["expected"]
                for combination in itertools.product(*groups)
            ):
                segmented.append(i)
        assert not raw
        assert bool(segmented) == (row["surface"] in ["짜증낼", "짜증내시네"])
        observations[mode] = dict(
            raw_gold_indices=raw, separate_word_group_indices=segmented
        )
    residuals.append(
        dict(
            original_gold_row=row,
            source=case["source"],
            source_sha256=case["source_sha256"],
            original_sentence_block=case["original_sentence_block"],
            observations=observations,
            contextual_verdict="unjudged",
            independent_review="pending",
        )
    )
print(
    "Six original corpus residuals unchanged; two groups recovered only across proposed separate words.",
    flush=True,
)
report = dict(
    schema_version=1,
    checklist="COV-020q",
    cli=a.cli,
    url=a.url,
    complete_native_entries=len(entries),
    surfaces=len(surfaces),
    judgment_observations=judgments,
    streams=checks,
    corpus_representation_observations=cohorts,
    original_corpus_residuals=residuals,
    default_records_and_native_fields_preserved=True,
    api_spacing_and_cli_equal=True,
    contextual_verdict="unjudged",
)
Path(a.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
