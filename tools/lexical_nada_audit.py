"""Freeze lexical 나다 discoveries before adding missing-space hypotheses.

Native examples and pre-change candidates remain observations, not corrected
gold. Offline verification checks every group/span/entry against the preserved
native data; --dictionary additionally reproduces the complete snapshot scan.
"""

import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/lexical-nada-source-preflight.json.gz"
ORIGINAL = ROOT / "tests/fixtures/continuation-inflection-sources.json"
MAIN = "krdict:62210"
PATTERN = r"(?<![가-힣])([가-힣]+)\s+((?:났|난|날|나)[가-힣]*)"
LIST_PATTERN = r"([가-힣]+)(이|가|을|를) 나다[.]?"
MODES = {"all": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def read(path):
    if path.suffix == ".gz":
        with gzip.open(path, "rt") as file:
            return json.load(file)
    return json.loads(path.read_text())


def write(path, value):
    payload = json.dumps(value, ensure_ascii=False, indent=2).encode() + b"\n"
    with path.open("xb") as file:
        file.write(gzip.compress(payload, mtime=0))


def load_dictionary(path):
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
        return {
            entry["id"]: entry
            for (data,) in db.execute("select data from entries order by id")
            for entry in [json.loads(data)]
        }


def indexes(entries):
    nouns = defaultdict(list)
    heads = defaultdict(list)
    for key, entry in sorted(entries.items()):
        heads[entry["headword"]].append(key)
        if entry["pos"] == "명사":
            nouns[entry["headword"]].append(key)
    return dict(nouns), dict(heads)


def inventory(entries, nouns, heads):
    listed = defaultdict(list)
    for sense in entries[MAIN]["senses"]:
        for group_index, group in enumerate(sense["examples"], 1):
            for text_index, text in enumerate(group):
                match = re.fullmatch(LIST_PATTERN, text)
                if match and match[1] in nouns:
                    listed[match[1]].append(
                        {
                            "sense": sense["id"],
                            "group": group_index,
                            "text_index": text_index,
                            "complete_group": group,
                            "particle": match[2],
                        }
                    )
    return {
        noun: {
            "noun_entries": nouns[noun],
            "case_marked_main_examples": refs,
            "registered_whole_entries": heads.get(noun + "나다", []),
            "bare_pair_license": "unjudged",
        }
        for noun, refs in sorted(listed.items())
    }


def discoveries(entries, nouns, listed):
    hits = []
    for entry in sorted(entries.values(), key=lambda e: e["id"]):
        for sense in entry["senses"]:
            for group_index, group in enumerate(sense["examples"], 1):
                for text_index, text in enumerate(group):
                    for match in re.finditer(PATTERN, text):
                        noun, right = match.group(1, 2)
                        if noun not in nouns:
                            continue
                        identity = [
                            entry["id"],
                            sense["id"],
                            group_index,
                            text_index,
                            match.start(),
                            match.end(),
                        ]
                        hits.append(
                            {
                                "id": "lexical-nada-discovery-" + digest(identity)[:24],
                                "entry": entry["id"],
                                "head": entry["headword"],
                                "sense": sense["id"],
                                "group": group_index,
                                "text_index": text_index,
                                "text": text,
                                "complete_group": group,
                                "match": match[0],
                                "span": {
                                    "start": len(text[: match.start()].encode()),
                                    "end": len(text[: match.end()].encode()),
                                },
                                "char_span": [match.start(), match.end()],
                                "noun": noun,
                                "right": right,
                                "listed_cohort": noun in listed or noun == "교통사고",
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return hits


def original_accidents():
    return [
        review
        for review in read(ORIGINAL)["individual_reviews"]
        if review["disposition"] == "bare_noun_plus_main_nada_alternative"
    ]


def input_surfaces(hits):
    return sorted(
        {
            surface
            for hit in hits
            if hit["listed_cohort"]
            for surface in [hit["right"], hit["noun"] + hit["right"]]
        }
    )


def run(cli, dictionary, surfaces):
    text = "\n".join(surfaces) + "\n"
    outputs = {}
    for mode, flags in MODES.items():
        result = subprocess.run(
            [
                str(cli.resolve()),
                "text",
                "-",
                "--dictionary",
                str(dictionary.resolve()),
                "--suggest-spacing",
                *flags,
            ],
            input=text,
            text=True,
            check=True,
            capture_output=True,
        )
        records = [json.loads(line) for line in result.stdout.splitlines()]
        words = [r for r in records if r["kind"] == "word"]
        assert [r["surface"] for r in words] == surfaces
        assert "".join(r["surface"] for r in records) == text
        outputs[mode] = records
    return text, outputs


def freeze(args):
    assert not SOURCE.exists(), "Refusing to replace pre-change observations"
    entries = load_dictionary(args.dictionary)
    nouns, heads = indexes(entries)
    listed = inventory(entries, nouns, heads)
    hits = discoveries(entries, nouns, listed)
    selected = [h for h in hits if h["listed_cohort"]]
    accidents = original_accidents()
    used = {MAIN, "krdict:62134"}
    used.update(h["entry"] for h in hits)
    used.update(i for h in hits for i in nouns[h["noun"]])
    used.update(i for value in listed.values() for i in value["noun_entries"])
    used.update(
        i
        for noun in {h["noun"] for h in hits} | set(listed)
        for i in heads.get(noun + "나다", [])
    )
    text, before = run(args.cli, args.dictionary, input_surfaces(hits))
    # All dictionary owners behind the original raw analyses are preserved too.
    used.update(
        e["id"]
        for record in before["all"]
        if record["kind"] == "word"
        for lemma in record["dictionary"]["lemmas"]
        for e in lemma["entries"]
    )
    used.update(r["original_discovery"]["entry"] for r in accidents)
    write(
        SOURCE,
        {
            "schema_version": 1,
            "checklist": "COV-020r",
            "before_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "cli_sha256": sha(args.cli),
            "dictionary_sha256": sha(args.dictionary),
            "original_source_sha256": sha(ORIGINAL),
            "entries_scanned": len(entries),
            "patterns": {"discovery": PATTERN, "inventory": LIST_PATTERN},
            "complete_native_entries": {i: entries[i] for i in sorted(used)},
            "main_sense_ids": [s["id"] for s in entries[MAIN]["senses"]],
            "noun_inventory": listed,
            "discoveries": hits,
            "original_accident_reviews": accidents,
            "before_input": text,
            "before_streams": before,
            "counts": {
                "main_senses": len(entries[MAIN]["senses"]),
                "listed_nouns": len(listed),
                "discoveries": len(hits),
                "discovered_nouns": len({h["noun"] for h in hits}),
                "listed_cohort": len(selected),
                "before_surfaces": len(input_surfaces(hits)),
                "preserved_native_entries": len(used),
            },
            "license": {
                "name": "한국어기초사전; CC BY-SA 2.0 KR",
                "url": "https://krdict.korean.go.kr/kor/help/helpCopyRightInfo",
                "scope": "Native dictionary data; examples, spellings, sense order and all translation languages are preserved.",
            },
            "scope": "All known-noun spaced spelling discoveries in the pinned native export, plus the complete main-나다 case-marked noun inventory. Spelling matches, current morphology and listed nouns do not establish bare-pair licenses or contextual correctness.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )


def verify(dictionary=None, cli=None):
    source = read(SOURCE)
    assert source["original_source_sha256"] == sha(ORIGINAL)
    entries = source["complete_native_entries"]
    assert all(key == entry["id"] for key, entry in entries.items())
    main = entries[MAIN]
    assert (main["headword"], main["homonym"], main["pos"]) == ("나다", "1", "동사")
    assert source["main_sense_ids"] == [s["id"] for s in main["senses"]]
    assert source["patterns"] == {"discovery": PATTERN, "inventory": LIST_PATTERN}
    nouns, heads = indexes(entries)
    listed = inventory(entries, nouns, heads)
    assert source["noun_inventory"] == listed
    assert source["discoveries"] == discoveries(entries, nouns, listed)
    hits = source["discoveries"]
    assert len({h["id"] for h in hits}) == len(hits)
    for hit in hits:
        raw = hit["text"].encode()
        assert raw[hit["span"]["start"] : hit["span"]["end"]].decode() == hit["match"]
        assert hit["contextual_verdict"] == "unjudged"
        assert hit["independent_review"] == "pending"
    assert source["original_accident_reviews"] == original_accidents()
    assert len(source["original_accident_reviews"]) == 8
    for review in source["original_accident_reviews"]:
        hit = review["original_discovery"]
        sense = next(
            s for s in entries[hit["entry"]]["senses"] if s["id"] == hit["sense"]
        )
        assert sense["examples"][hit["group"] - 1] == hit["complete_group"]
    surfaces = input_surfaces(hits)
    assert source["before_input"] == "\n".join(surfaces) + "\n"
    for mode in MODES:
        records = source["before_streams"][mode]
        assert "".join(r["surface"] for r in records) == source["before_input"]
        assert [r["surface"] for r in records if r["kind"] == "word"] == surfaces
        for record in records:
            start, end = record["span"]["start"], record["span"]["end"]
            assert (
                source["before_input"].encode()[start:end].decode() == record["surface"]
            )
            if record["kind"] != "word":
                continue
            for lemma in record["dictionary"]["lemmas"]:
                assert all(e["id"] in entries for e in lemma["entries"])
    raw_words = {
        r["surface"]: r for r in source["before_streams"]["all"] if r["kind"] == "word"
    }
    for mode in ["headword", "compatible"]:
        for record in source["before_streams"][mode]:
            if record["kind"] == "word":
                original = raw_words[record["surface"]]
                assert all(
                    a in original["analysis"]["analyses"]
                    for a in record["analysis"]["analyses"]
                )
                assert record["spacing"] == original["spacing"]
    expected = {
        "main_senses": 32,
        "listed_nouns": 185,
        "discoveries": 5218,
        "discovered_nouns": 775,
        "listed_cohort": 631,
        "before_surfaces": len(surfaces),
        "preserved_native_entries": len(entries),
    }
    assert source["counts"] == expected
    assert source["entries_scanned"] == 56555
    assert source["contextual_verdict"] == "unjudged"
    assert source["independent_review"] == "pending"
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        native = load_dictionary(dictionary)
        assert len(native) == source["entries_scanned"]
        assert all(native[i] == e for i, e in entries.items())
        all_nouns, all_heads = indexes(native)
        assert inventory(native, all_nouns, all_heads) == listed
        assert discoveries(native, all_nouns, listed) == hits
    if cli:
        assert dictionary, "Replaying original outputs requires the pinned dictionary"
        assert sha(cli) == source["cli_sha256"]
        text, streams = run(cli, dictionary, surfaces)
        assert text == source["before_input"]
        assert streams == source["before_streams"]
    print(json.dumps(expected, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--cli", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(args.dictionary, args.cli)
    elif args.dictionary and args.cli:
        freeze(args)
        verify(args.dictionary)
    else:
        parser.error("freeze requires --dictionary and --cli")


if __name__ == "__main__":
    main()
