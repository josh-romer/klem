"""Freeze native -(으)ㄹ라 evidence and original candidates; verify offline.

Spelling discoveries include 르 contractions, loanwords and commands. They are
not caution-ending gold. Source excerpts and authored boundary judgments remain
separate from contextual and independent Korean-language review.
"""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import MODES, ROOT, digest, load_dictionary, read, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/caution-ending-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/caution-ending-sources.json"
LMF = ROOT / "tests/fixtures/krdict-caution-ending.json"
ADDITIONAL = ROOT / "tests/fixtures/caution-ending-additional-native.json"
ADDITIONAL_LMF = ROOT / "tests/fixtures/krdict-caution-ending-additional.json"
PATTERN = r"(?<![가-힣])[가-힣]+라(?![가-힣])"
NATIVE = [
    ("가짜일라", ["가짜", "이다"], ["nominal", "copula"], []),
    ("깨실라", ["깨다"], ["predicate"], ["시"]),
    ("놓칠라", ["놓치다"], ["predicate"], []),
    ("넘어질라", ["넘어지다"], ["predicate"], []),
    ("찢어질라", ["찢어지다"], ["predicate"], []),
    ("들라", ["들다"], ["predicate"], []),
    ("병날라", ["병나다"], ["predicate"], []),
    ("체할라", ["체하다"], ["predicate"], []),
    ("들을라", ["듣다"], ["predicate"], []),
    ("넘을라", ["넘다"], ["predicate"], []),
    ("야단맞을라", ["야단맞다"], ["predicate"], []),
    ("먹을라", ["먹다"], ["predicate"], []),
    ("적을라", ["적다"], ["predicate"], []),
    ("찾을라", ["찾다"], ["predicate"], []),
    ("늦을라", ["늦다"], ["predicate"], []),
]


def cases():
    rows = []

    def add(surface, heads, kinds, forms, verdict="required", status="compatible"):
        rows.append(
            {
                "id": "caution-ending-" + surface + "-" + "-".join(heads),
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms + ["을라"],
                "verdict": verdict,
                "ending_owner_status": status if verdict == "required" else None,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    for surface, heads, kinds, forms in NATIVE:
        add(surface, heads, kinds, forms)
    for surface, head in [
        ("날라", "나다"),
        ("갈라", "가다"),
        ("살라", "살다"),
        ("만들라", "만들다"),
        ("물라", "물다"),
        ("도울라", "돕다"),
        ("부을라", "붓다"),
        ("지을라", "짓다"),
        ("파랄라", "파랗다"),
        ("좋을라", "좋다"),
        ("있을라", "있다"),
        ("없을라", "없다"),
        ("나을라", "낫다"),
        ("알라", "알다"),
    ]:
        add(surface, [head], ["predicate"], [])
    for surface, nominal in [("학생일라", "학생"), ("학교일라", "학교")]:
        add(surface, [nominal, "이다"], ["nominal", "copula"], [])
    for surface, heads, kinds, forms in [
        ("먹었을라", ["먹다"], ["predicate"], ["었"]),
        ("먹으실라", ["먹다"], ["predicate"], ["시"]),
        ("먹으셨을라", ["먹다"], ["predicate"], ["시", "었"]),
        ("학교였을라", ["학교", "이다"], ["nominal", "copula"], ["었"]),
        ("먹어볼라", ["먹다", "보다"], ["predicate", "auxiliary"], ["어"]),
        ("먹어봤을라", ["먹다", "보다"], ["predicate", "auxiliary"], ["어", "었"]),
        ("먹었어볼라", ["먹다", "보다"], ["predicate", "auxiliary"], ["었", "어"]),
        ("먹지않을라", ["먹다", "않다"], ["predicate", "auxiliary"], ["지"]),
        ("먹지않았을라", ["먹다", "않다"], ["predicate", "auxiliary"], ["지", "었"]),
        ("찢어질라", ["찢다", "지다"], ["predicate", "auxiliary"], ["어"]),
        ("학생다울라", ["학생"], ["nominal"], ["답다"]),
        ("먹기일라", ["먹다", "이다"], ["predicate", "copula"], ["기"]),
    ]:
        add(surface, heads, kinds, forms)
    for surface, heads, kinds, forms in [
        ("먹겠을라", ["먹다"], ["predicate"], ["겠"]),
        ("먹어보겠을라", ["먹다", "보다"], ["predicate", "auxiliary"], ["어", "겠"]),
    ]:
        add(surface, heads, kinds, forms, status="unknown")
    # 더 ends in a vowel, so this full 을 allomorph cannot be its boundary.
    add("먹더을라", ["먹다"], ["predicate"], ["더"], "forbidden")
    for surface, head in [
        ("먹라", "먹다"),
        ("가을라", "가다"),
        ("살을라", "살다"),
        ("듣라", "듣다"),
        ("돕라", "돕다"),
        ("붓라", "붓다"),
        ("짓라", "짓다"),
        ("좋라", "좋다"),
        ("가라", "가다"),
        ("낫라", "낫다"),
        ("알을라", "알다"),
    ]:
        add(surface, [head], ["predicate"], [], "forbidden")
    for surface, nominal in [
        ("학교라", "학교"),
        ("학생라", "학생"),
        ("학생을라", "학생"),
    ]:
        add(surface, [nominal, "이다"], ["nominal", "copula"], [], "forbidden")
    # No independent 요 or outer particle license was reviewed for this ending.
    for surface, follower in [("먹을라요", "요"), ("날라도", "도"), ("날라는", "는")]:
        row = dict(rows[0])
        row.update(
            id="caution-ending-follower-" + surface,
            surface=surface,
            lemmas=["먹다" if follower == "요" else "나다"],
            lemma_kinds=["predicate"],
            morphemes=["을라", follower],
            verdict="forbidden",
            ending_owner_status=None,
        )
        rows.append(row)
    return rows


def discover(text, owner):
    hits = []
    for match in re.finditer(PATTERN, text):
        if (ord(match[0][-2]) - 0xAC00) % 28 != 8:
            continue
        identity = [owner, match.start(), match.end()]
        hits.append(
            {
                "id": "caution-ending-discovery-" + digest(identity)[:24],
                "owner": owner,
                "surface": match[0],
                "text": text,
                "span": {
                    "start": len(text[: match.start()].encode()),
                    "end": len(text[: match.end()].encode()),
                },
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return hits


def freeze(cli, dictionary):
    assert not any(p.exists() for p in [SOURCE, FIXTURE, LMF])
    entries = load_dictionary(dictionary)
    hits = []
    for e in entries.values():
        for s in e["senses"]:
            for i, group in enumerate(s["examples"]):
                for j, text in enumerate(group):
                    hits.extend(discover(text, [e["id"], s["id"], i, j]))
    novel = ROOT / "data/books/mujeong.txt"
    novel_text = novel.read_text()
    novel_hits = discover(novel_text, [str(novel.relative_to(ROOT))])
    # Keep bounded context without duplicating an entire novel per occurrence.
    for hit in novel_hits:
        a, b = hit["span"]["start"], hit["span"]["end"]
        hit["text"] = novel_text.encode()[max(0, a - 120) : b + 120].decode(
            errors="replace"
        )
    corpora = []
    for p in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for block in p.read_text().split("\n\n"):
            matched = []
            for line in block.splitlines():
                fields = line.split("\t")
                if (
                    len(fields) == 10
                    and fields[0].isdigit()
                    and (
                        discover(fields[1], [fields[0]])
                        or any(x in fields[2].split("+") for x in ["ㄹ라", "을라"])
                    )
                ):
                    matched.append(fields[0])
            if matched:
                sentences.append(
                    {
                        "conllu": block + "\n\n",
                        "matched_tokens": matched,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        corpora.append(
            {"path": str(p.relative_to(ROOT)), "sha256": sha(p), "sentences": sentences}
        )
    native = [entries["krdict:77345"], entries["krdict:77346"]]
    attestations = []
    for e in native:
        for s in e["senses"]:
            for i, group in enumerate(s["examples"]):
                found = [
                    c for c in cases()[:15] if any(c["surface"] in t for t in group)
                ]
                assert len(found) == 1
                attestations.append(
                    {
                        "entry": e["id"],
                        "sense": s["id"],
                        "example_group": i,
                        "complete_group": group,
                        "case": found[0]["id"],
                        "excerpt": found[0]["surface"],
                    }
                )
    words = sorted(
        {c["surface"] for c in cases()}
        | {h["surface"] for h in hits + novel_hits}
        | {"사고날라", "학교에서사고날라", "날라요"}
    )
    text = " ".join(words)
    streams = {
        mode: list(
            map(
                json.loads,
                subprocess.check_output(
                    [
                        str(cli),
                        "text",
                        "-",
                        "--dictionary",
                        str(dictionary),
                        "--suggest-spacing",
                        *flags,
                    ],
                    input=text.encode(),
                ).splitlines(),
            )
        )
        for mode, flags in MODES.items()
    }
    fixture_ids = {
        "krdict:77345",
        "krdict:77346",
        "krdict:41298",
        "krdict:62210",
        "krdict:62134",
    }
    fixture_ids.update(
        e["id"]
        for r in streams["all"]
        if r["kind"] == "word"
        for slot in r["dictionary"]["lemmas"]
        for e in slot["entries"]
    )
    heads = {h for c in cases() for h in c["lemmas"]}
    fixture_ids.update(e["id"] for e in entries.values() if e["headword"] in heads)
    fixture_native = {i: entries[i] for i in sorted(fixture_ids)}
    raw, hashes = project_lmf(fixture_native)
    lmf = {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}}
    LMF.write_text(json.dumps(lmf, ensure_ascii=False, indent=2) + "\n")
    full_ids = fixture_ids | {h["owner"][0] for h in hits}
    source = {
        "schema_version": 1,
        "checklist": "COV-017bs",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "raw_source_sha256": hashes,
        "pattern": PATTERN,
        "entries_scanned": len(entries),
        "complete_native_entries": {i: entries[i] for i in sorted(full_ids)},
        "discoveries": hits,
        "novel": {
            "path": str(novel.relative_to(ROOT)),
            "sha256": sha(novel),
            "discoveries": novel_hits,
        },
        "annotated_corpora": corpora,
        "before_input": text,
        "before_streams": streams,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(SOURCE, source)
    projected = copy.deepcopy(list(fixture_native.values()))
    for e in projected:
        for s in e["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
    fixture = {
        "schema_version": 1,
        "checklist": "COV-017bs",
        "source_sha256": sha(SOURCE),
        "lmf_sha256": sha(LMF),
        "cases": cases(),
        "attestations": attestations,
        "complete_native_entries": fixture_native,
        "source_entries": projected,
        "before_words": {
            r["surface"]: r for r in streams["all"] if r["kind"] == "word"
        },
    }
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    verify(dictionary)


def verify(dictionary=None):
    source, fixture = read(SOURCE), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert fixture["cases"] == cases()
    verify_native_lmf(read(LMF), fixture["complete_native_entries"])
    if ADDITIONAL.exists():
        additional = read(ADDITIONAL)
        assert additional["source_sha256"] == sha(SOURCE)
        assert additional["lmf_sha256"] == sha(ADDITIONAL_LMF)
        verify_native_lmf(read(ADDITIONAL_LMF), additional["complete_native_entries"])
    assert len(fixture["attestations"]) == 15
    for row in fixture["attestations"]:
        e = source["complete_native_entries"][row["entry"]]
        s = next(s for s in e["senses"] if s["id"] == row["sense"])
        assert s["examples"][row["example_group"]] == row["complete_group"]
        assert any(row["excerpt"] in text for text in row["complete_group"])
    ids = set()
    for hit in source["discoveries"]:
        ident, sense, group, item = hit["owner"]
        entry = source["complete_native_entries"][ident]
        text = next(s for s in entry["senses"] if s["id"] == sense)["examples"][group][
            item
        ]
        assert hit in discover(text, hit["owner"])
        assert hit["id"] not in ids
        ids.add(hit["id"])
    # Reconstruct every discovery from the retained complete native groups.
    # Definitions, spelling patterns and current generated analyses are not gold.
    reconstructed = []
    for e in source["complete_native_entries"].values():
        for s in e["senses"]:
            for i, group in enumerate(s["examples"]):
                for j, text in enumerate(group):
                    reconstructed.extend(discover(text, [e["id"], s["id"], i, j]))
    assert reconstructed == source["discoveries"]
    ledger = read(ROOT / "tests/fixtures/validity.json")
    indexed = {
        c["id"]: c for c in ledger["cases"] if c["id"].startswith("caution-ending-")
    }
    assert indexed.keys() == {c["id"] for c in fixture["cases"]}
    for case in fixture["cases"]:
        recorded = indexed[case["id"]]
        assert recorded["surface"] == case["surface"]
        for field in ["lemmas", "lemma_kinds", "morphemes", "verdict"]:
            assert recorded["judgments"][0][field] == case[field]
    for e in fixture["source_entries"]:
        original = copy.deepcopy(fixture["complete_native_entries"][e["id"]])
        for s in original["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
        assert original == e
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        entries = load_dictionary(dictionary)
        assert len(entries) == source["entries_scanned"]
        assert all(
            entries[i] == e for i, e in source["complete_native_entries"].items()
        )
        if ADDITIONAL.exists():
            assert all(
                entries[i] == e
                for i, e in additional["complete_native_entries"].items()
            )
        for corpus in source["annotated_corpora"]:
            path = ROOT / corpus["path"]
            assert sha(path) == corpus["sha256"]
            blocks = {b + "\n\n" for b in path.read_text().split("\n\n")}
            assert all(row["conllu"] in blocks for row in corpus["sentences"])
        novel = ROOT / source["novel"]["path"]
        assert sha(novel) == source["novel"]["sha256"]
        actual = discover(novel.read_text(), [source["novel"]["path"]])
        assert [{k: v for k, v in h.items() if k != "text"} for h in actual] == [
            {k: v for k, v in h.items() if k != "text"}
            for h in source["novel"]["discoveries"]
        ]
    print(
        f"Verified {len(fixture['cases'])} caution cases, 15 full native groups, {len(ids)} spelling observations"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.freeze:
        assert args.cli and args.dictionary
        freeze(args.cli, args.dictionary)
    else:
        assert args.verify
        verify(args.dictionary)
