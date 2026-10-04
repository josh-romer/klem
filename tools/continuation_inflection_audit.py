"""Freeze source tensions before changing continuation attachment policy.

Source text and spelling discoveries are evidence, not corrected gold. In
particular, native 고 났더니 examples prevent a blanket right-past exclusion.
"""

import argparse
import copy
import gzip
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests/fixtures/continuation-inflection-sources.json"
LMF = ROOT / "tests/fixtures/krdict-continuation-inflection.json"
DISCOVERY = ROOT / "docs/continuation-inflection-native-discovery.json.gz"
PREFLIGHT = ROOT / "docs/continuation-inflection-source-preflight.json"
MODES = {"all": [], "headword": ["--dict-only"], "compatible": ["--dict-compatible"]}
PATTERNS = {
    "tense_before_beorida": r"[가-힣]*(?:었|았|였|겠)어\s*버[가-힣]+",
    "tense_before_go_nada": r"[가-힣]*(?:었|았|였|겠)고\s*나[가-힣]+",
    "right_tense_go_nada": r"[가-힣]+고\s*(?:났|나겠)[가-힣]*",
    "right_honorific_go_nada": r"[가-힣]+고\s*나(?:시|셔|셨)[가-힣]*",
    "go_nada_spaced": r"[가-힣]+고 (?:나[가-힣]+|난(?=[ .,!/?]))",
    "eo_oda_adjectives": r"(?:가까워|아파|시려|많아|커|바빠|나빠|밝아|어두워|깊어) (?:오[가-힣]+|온(?=[ .,!/?])|올(?=[ .,!/?])|와[가-힣]*|왔[가-힣]+)",
}


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def write(path, value):
    with path.open("x") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")


def classification(kind, hit):
    text = hit["match"]
    if kind == "tense_before_go_nada":
        return "other_na_word_or_pronoun_not_established_as_auxiliary"
    if "타고" in text:
        return "registered_lexical_tagonada_alternative"
    if "들고났" in text:
        return "registered_lexical_deulgonada_alternative"
    if "사고" in text:
        return "bare_noun_plus_main_nada_alternative"
    if text.endswith("났더니"):
        return "native_retrospective_go_nada_counterevidence"
    return "unjudged_spelling_discovery"


def diagnostics():
    result = set()
    # Immediate owners and distinct connectors, without adjudicating contexts.
    for prefix in [
        "먹어",
        "먹었어",
        "먹겠어",
        "먹으셔",
        "먹었지않아",
        "먹지않았어",
        "먹었어보아",
    ]:
        for right in ["버리다", "버렸다", "버리겠어요", "버리시다"]:
            result.add(prefix + right)
    for prefix in [
        "먹고",
        "먹었고",
        "먹겠고",
        "먹으시고",
        "먹었지않고",
        "먹지않았고",
        "좋아지고",
    ]:
        for right in [
            "나다",
            "난다",
            "나서",
            "나면",
            "난",
            "나니",
            "났더니",
            "나셨다",
            "나셔서",
            "나겠어서",
            "났어서",
        ]:
            result.add(prefix + right)
    for prefix in ["먹어", "넘쳐", "늘어"]:
        for right in ["나다", "났다", "나겠어요", "나시다", "나니"]:
            result.add(prefix + right)
    for prefix in ["아프고", "크고", "좋고"]:
        for right in ["난", "나서", "났더니", "나셨다"]:
            result.add(prefix + right)
    for prefix in [
        "가까워",
        "아파",
        "시려",
        "많아",
        "커",
        "바빠",
        "나빠",
        "밝아",
        "어두워",
        "깊어",
    ]:
        for right in ["오다", "왔다", "올", "오겠다"]:
            result.add(prefix + right)
    result.update(
        [
            "밝아올것이다",
            "타고났다",
            "타고나셨다",
            "들고났다",
            "사고났다",
            "교통사고났었다며",
            "나다",
            "났더니",
            "버렸다",
            "오셨다",
        ]
    )
    return result


def verify():
    source = json.loads(SOURCE.read_text())
    with gzip.open(DISCOVERY, "rt") as file:
        discovery = json.load(file)
    assert source["original_preflight_sha256"] == sha(PREFLIGHT)
    assert source["lmf_sha256"] == sha(LMF)
    assert source["discovery_sha256"] == sha(DISCOVERY)
    assert discovery["patterns"] == PATTERNS
    assert discovery["entries_scanned"] == 56555
    expected = {
        "tense_before_beorida": 0,
        "tense_before_go_nada": 8,
        "right_tense_go_nada": 42,
        "right_honorific_go_nada": 2,
        "go_nada_spaced": 2010,
        "eo_oda_adjectives": 60,
    }
    assert {key: len(hits) for key, hits in discovery["hits"].items()} == expected
    assert all(surface in source["before_words"] for surface in diagnostics())
    historical = json.loads(PREFLIGHT.read_text())
    assert all(source["before_words"][s] == w for s, w in historical["words"].items())
    for entry in source["source_entries"]:
        original = copy.deepcopy(source["complete_native_entries"][entry["id"]])
        for sense in original["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
        assert original == entry
    for review in source["individual_reviews"]:
        hit = review["original_discovery"]
        assert review["disposition"] == classification(review["pattern"], hit)
        entry = source["complete_native_entries"][hit["entry"]]
        sense = next(s for s in entry["senses"] if s["id"] == hit["sense"])
        assert sense["examples"][hit["group"] - 1] == hit["complete_group"]
        assert hit["text"] in hit["complete_group"]
        assert (
            review["contextual_verdict"] == "unjudged"
            and review["independent_review"] == "pending"
        )
    assert len(source["individual_reviews"]) == 52
    from collections import Counter

    dispositions = Counter(r["disposition"] for r in source["individual_reviews"])
    assert dispositions == {
        "other_na_word_or_pronoun_not_established_as_auxiliary": 8,
        "registered_lexical_tagonada_alternative": 18,
        "registered_lexical_deulgonada_alternative": 1,
        "bare_noun_plus_main_nada_alternative": 8,
        "native_retrospective_go_nada_counterevidence": 17,
    }
    assert source["contextual_verdict"] == "unjudged"
    print(
        f"Original four tensions, {len(source['before_words'])} frozen surfaces, {len(source['source_entries'])} full native entries and 52 individually tracked discoveries verified."
    )


def project_lmf(entries):
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / "data/dictionaries/krdict/json").glob("*.json")):
        for raw in array(
            json.loads(path.read_text())["LexicalResource"]["Lexicon"]["LexicalEntry"]
        ):
            head = next(
                f["val"]
                for l in array(raw["Lemma"])
                for f in array(l["feat"])
                if f["att"] == "writtenForm"
            )
            unit = next(
                (
                    f["val"]
                    for f in array(raw.get("feat", []))
                    if f["att"] == "lexicalUnit"
                ),
                "",
            )
            ident = "krdict:" + str(raw["val"])
            if unit in {"관용구", "속담"}:
                ident += ":" + hashlib.sha256((unit + "\0" + head).encode()).hexdigest()
            if ident not in entries:
                continue
            pos = next(
                (
                    f["val"]
                    for f in array(raw.get("feat", []))
                    if f["att"] == "partOfSpeech"
                ),
                "",
            )
            if (head, pos) != (entries[ident]["headword"], entries[ident]["pos"]):
                continue
            assert ident not in raw_entries
            raw = copy.deepcopy(raw)
            raw.pop("RelatedForm", None)
            raw["Sense"] = array(raw.get("Sense", []))
            for sense in raw["Sense"]:
                if "Equivalent" in sense:
                    sense["Equivalent"] = [
                        e
                        for e in array(sense["Equivalent"])
                        if any(
                            f["att"] == "language" and f["val"] == "영어"
                            for f in array(e.get("feat", []))
                        )
                    ]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == set(entries), set(entries) - set(raw_entries)
    return raw_entries, hashes


def freeze(args):
    if any(p.exists() for p in [SOURCE, LMF, DISCOVERY]):
        raise SystemExit("Refusing to overwrite source/before evidence.")
    cli, dbpath = args.cli.resolve(), args.dictionary.resolve()
    patterns = {k: re.compile(v) for k, v in PATTERNS.items()}
    hits = {key: [] for key in patterns}
    entries, scanned = {}, 0
    previous = json.loads(
        (ROOT / "tests/fixtures/continuation-left-sources.json").read_text()
    )
    heads = {e["headword"] for e in previous["source_entries"]} | {
        "아프다",
        "가깝다",
        "시리다",
        "많다",
        "바쁘다",
        "나쁘다",
        "타고나다",
        "들고나다",
        "사고",
        "교통사고",
        "것",
        "뒤",
        "후",
        "다음",
        "건강",
        "최저치",
        "중요성",
        "-아 오다",
        "-어 오다",
    }
    with sqlite3.connect(dbpath.as_uri() + "?mode=ro", uri=True) as db:
        for ident, raw in db.execute("select id,data from entries"):
            entry = json.loads(raw)
            scanned += 1
            if entry["headword"] in heads:
                entries[ident] = entry
            for sense in entry["senses"]:
                for index, group in enumerate(sense["examples"]):
                    for text in group:
                        for key, pattern in patterns.items():
                            for match in pattern.finditer(text):
                                hits[key].append(
                                    {
                                        "entry": ident,
                                        "head": entry["headword"],
                                        "sense": sense["id"],
                                        "group": index + 1,
                                        "text": text,
                                        "match": match.group(),
                                        "complete_group": group,
                                    }
                                )
                                if key not in {"go_nada_spaced"}:
                                    entries[ident] = entry
    # All 2,010 broad discoveries remain separately captured; selected source
    # tensions also retain complete native entries rather than clipped examples.
    reviews = []
    for key in [
        "tense_before_beorida",
        "tense_before_go_nada",
        "right_tense_go_nada",
        "right_honorific_go_nada",
    ]:
        for hit in hits[key]:
            identity = json.dumps([key, hit], ensure_ascii=False, sort_keys=True)
            reviews.append(
                {
                    "id": "continuation-inflection-discovery-"
                    + hashlib.sha256(identity.encode()).hexdigest()[:24],
                    "pattern": key,
                    "original_discovery": hit,
                    "disposition": classification(key, hit),
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    raw_entries, hashes = project_lmf(entries)
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    surfaces = diagnostics()
    historical = json.loads(PREFLIGHT.read_text())
    surfaces.update(historical["words"])
    for review in reviews:
        surfaces.add(review["original_discovery"]["match"].replace(" ", ""))
    for ledger in ["validity.json", "dictionary-attachments.json"]:
        for case in json.loads((ROOT / "tests/fixtures" / ledger).read_text())["cases"]:
            if case["id"].startswith(
                ("continuation-aux", "aux-inventory-nada", "continuation-left-")
            ):
                surfaces.add(case["surface"])
    words = {
        surface: {
            mode: json.loads(
                subprocess.check_output(
                    [str(cli), "word", surface, "--dictionary", str(dbpath), *flags]
                )
            )
            for mode, flags in MODES.items()
        }
        for surface in sorted(surfaces)
    }
    assert all(words[s] == w for s, w in historical["words"].items())
    discovery = {
        "schema_version": 1,
        "entries_scanned": scanned,
        "patterns": PATTERNS,
        "hits": hits,
        "scope": "Spelling discovery only; all lexical interpretations and contexts require separate review. Zero hits do not prove impossibility.",
    }
    payload = json.dumps(discovery, ensure_ascii=False, indent=2).encode()
    DISCOVERY.write_bytes(gzip.compress(payload, mtime=0))
    write(
        LMF,
        {
            "LexicalResource": {
                "Lexicon": {"LexicalEntry": [raw_entries[i] for i in sorted(entries)]}
            }
        },
    )
    write(
        SOURCE,
        {
            "schema_version": 1,
            "checklist": "COV-019ae",
            "before_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "cli": str(cli),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dbpath),
            "original_preflight_sha256": sha(PREFLIGHT),
            "lmf_sha256": sha(LMF),
            "discovery_sha256": sha(DISCOVERY),
            "raw_source_sha256": hashes,
            "complete_native_entries": entries,
            "source_entries": projected,
            "before_words": words,
            "individual_reviews": reviews,
            "guide": {
                "url": historical["guide_url"],
                "sha256": historical["guide_sha256"],
                "printed_pages": historical["printed_pages"],
            },
            "license": "KRDict CC BY-SA 2.0 KR; English projection is an importer adapter, not a corrected source.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
            "limitations": "Preserve original raw/corpus/policy judgments. Seventeen native 고 났더니 occurrences and two 아프다 constructions require source-tension review, not blanket tense/adjective exclusions. Future 오다 uses require sense/time-reference review. Bare 사고 + main 나다 is distinct from auxiliary 고 나다 and registered whole lexical verbs.",
        },
    )
    verify()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli and args.dictionary:
        freeze(args)
    else:
        parser.error("freeze requires --cli and --dictionary")


if __name__ == "__main__":
    main()
