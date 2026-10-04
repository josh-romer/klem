"""Freeze both -되다 senses, every literal native head and original suffix gold."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from continuation_inflection_audit import project_lmf
from doeda_noun_suffix_discovery import REPORT as DISCOVERY
from doeda_noun_suffix_discovery import referenced
from lexical_nada_audit import ROOT, load_dictionary, read, run, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/doeda-suffix-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-suffix-sources.json"
LMF = ROOT / "tests/fixtures/krdict-doeda-suffix.json"
MAIN = "krdict:74902"
# Bound lookup material is retained independently of unrelated standalone
# homonyms. These are source-listed adjective stems, not a rule assigning Root
# to every missing dictionary head. Historical/base-kind review remains explicit.
ROOTS = {"고", "앳", "외람", "편벽", "허황", "헛", "호"}
ADVERBS = {"덜", "막", "못", "안", "오래", "한갓"}
GUIDANCE = [
    {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=316511",
        "title": "고되다의 어원",
        "answer_date": "2025-06-18",
        "finding": "NIKL analyzes 고되다 as root 고 plus adjective-forming -되다; its etymology is unknown. Do not borrow the unrelated noun homonyms' origins.",
        "limits": "Only 고 is explicitly identified as a root by this answer; other opaque lookup bases retain separate agent proposals and historical review.",
    },
    {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=321537",
        "title": "못되다의 되다",
        "answer_date": "2025-09-30",
        "finding": "NIKL distinguishes passive verb-forming and adjective-forming -되다 and identifies 못되다's suffix as adjective-forming.",
        "limits": "This does not license every noun/adverb/root or select a contextual meaning.",
    },
]


def formation_proposals(entries, heads):
    result = []
    for sense in entries[MAIN]["senses"]:
        for gi, group in enumerate(sense["examples"]):
            for ti, word in enumerate(group):
                assert word.endswith("되다")
                base = word[:-2]
                cls = "verb" if sense["id"] == "1" else "adjective"
                kind = (
                    "nominal"
                    if cls == "verb"
                    else "root"
                    if base in ROOTS
                    else "adverbial"
                    if base in ADVERBS
                    else "nominal"
                )
                result.append(
                    {
                        "head": word,
                        "base": base,
                        "base_kind": kind,
                        "predicate_class": cls,
                        "source": MAIN,
                        "sense": sense["id"],
                        "group": gi,
                        "text_index": ti,
                        "complete_group": group,
                        "whole_entries": heads[word],
                        "base_entries": heads.get(base, []),
                        "base_kind_review": "agent source-backed proposal; independent/formal-history review pending",
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
    assert len(result) == 157
    result.append(
        {
            "head": "타도되다",
            "base": "타도",
            "base_kind": "nominal",
            "predicate_class": "verb",
            "source": MAIN,
            "sense": "1",
            "original_discovery_sha256": sha(DISCOVERY),
            "whole_entries": heads.get("타도되다", []),
            "base_entries": heads["타도"],
            "base_kind_review": "original KAIST ncpa+xsv annotation plus full noun 79461 and suffix 74902; whole gold remains unchanged",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
    )
    return sorted(result, key=lambda r: r["head"])


def cases(proposals):
    result = []
    for i, p in enumerate(proposals):
        variants = [
            ("되다", ["다"]),
            ("되었다", ["었", "다"]),
            ("됐어요", ["었", "어요"]),
            ("돼요", ["어요"]),
            ("됩니다", ["습니다"]),
            ("되면", ["으면"]),
            ("되어", ["어"]),
            ("되기는", ["기", "는"]),
            ("됨이다", ["음", "다"]),
        ]
        variants.append(
            ("되는", ["는"]) if p["predicate_class"] == "verb" else ("된", ["은"])
        )
        for j, (tail, morphs) in enumerate(variants):
            copula = tail == "됨이다"
            result.append(
                {
                    "id": f"doeda-suffix-source-{i:03d}-{j:02d}",
                    "surface": p["base"] + tail,
                    "lemmas": [p["base"]] + (["이다"] if copula else []),
                    "lemma_kinds": [p["base_kind"]] + (["copula"] if copula else []),
                    "morphemes": ["되다", *morphs],
                    "morpheme_kinds": [
                        "suffix",
                        *[
                            "particle"
                            if m == "는" and tail == "되기는"
                            else "prefinal"
                            if m == "었"
                            else "ending"
                            for m in morphs
                        ],
                    ],
                    "required_rules": ["suffix." + p["predicate_class"] + ".doeda"],
                    "verdict": "required",
                    "source": MAIN,
                    "scope": "source-listed formation proposal; agent-authored, independent review pending",
                }
            )
    for i, base in enumerate(("거짓", "고", "못", "오래", "외람")):
        kind = (
            "root" if base in ROOTS else "adverbial" if base in ADVERBS else "nominal"
        )
        for j, tail in enumerate(("된다", "되는")):
            result.append(
                {
                    "id": f"doeda-suffix-adjective-control-{i:02d}-{j}",
                    "surface": base + tail,
                    "lemmas": [base],
                    "lemma_kinds": [kind],
                    "morphemes": ["되다", "는다" if tail == "된다" else "는"],
                    "morpheme_kinds": ["suffix", "ending"],
                    "required_rules": ["suffix.adjective.doeda"],
                    "verdict": "forbidden",
                    "source": MAIN,
                    "scope": "scoped adjective suffix path only; whole lexical and other meanings survive",
                }
            )
    return result


def corpus_observations():
    result = []
    for path in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for text in path.read_text().strip().split("\n\n"):
            rows = [
                line.split("\t")
                for line in text.splitlines()
                if not line.startswith("#")
            ]
            rows = [r for r in rows if len(r) == 10 and r[0].isdigit()]
            hits = [
                r
                for r in rows
                if "되" in r[2].split("+")
                and any(t.lower() in ("xsv", "xsa") for t in r[4].split("+"))
            ]
            if hits:
                sentences.append({"complete_sentence": text, "original_rows": hits})
        result.append(
            {
                "source": str(path.relative_to(ROOT)),
                "sha256": sha(path),
                "sentences": sentences,
            }
        )
    assert len(result) == 6
    return result


def freeze(cli, dictionary):
    assert not any(p.exists() for p in (SOURCE, FIXTURE, LMF))
    discovery = read(DISCOVERY)
    assert (
        sha(cli) == discovery["cli_sha256"]
        and sha(dictionary) == discovery["dictionary_sha256"]
    )
    entries = load_dictionary(dictionary)
    heads = defaultdict(list)
    for ident, entry in entries.items():
        heads[entry["headword"]].append(ident)
    proposals = formation_proposals(entries, heads)
    inventory = [
        {
            "id": ident,
            "head": e["headword"],
            "native_pos": e["pos"],
            "literal_base": e["headword"][:-2],
            "base_entries": heads.get(e["headword"][:-2], []),
            "disposition": "unreviewed-literal-match",
        }
        for ident, e in sorted(entries.items())
        if e["headword"].endswith("되다")
        and e["headword"] != "되다"
        and e["pos"] in ("동사", "형용사")
    ]
    assert len(inventory) == 1850
    corpora = corpus_observations()
    fixture_cases = cases(proposals)
    words = sorted(
        {p["head"] for p in inventory}
        | {c["surface"] for c in fixture_cases}
        | {r[1] for c in corpora for s in c["sentences"] for r in s["original_rows"]}
    )
    print(
        f"Freezing {len(words):,} unique words; 1,850 native leads, 158 formation proposals, {len(fixture_cases)} proposed paths",
        flush=True,
    )
    text, streams = run(cli, dictionary, words)
    before = {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in streams["all"]
        if r["kind"] == "word"
    }
    used = {MAIN, "krdict:79461", "krdict:79462"}
    for row in inventory + proposals:
        used.update(row["base_entries"])
        if "id" in row:
            used.add(row["id"])
        used.update(row.get("whole_entries", []))
    used.update(referenced(streams))
    selected = {MAIN, "krdict:79461", "krdict:79462"}
    for p in proposals:
        selected.update(p["base_entries"] + p["whole_entries"])
    selected.update(
        referenced({c["surface"]: before[c["surface"]] for c in fixture_cases})
    )
    for head in (
        "-었-",
        "-어요",
        "-습니다",
        "-으면",
        "-기",
        "-음",
        "는",
        "-는",
        "-은",
        "-다",
        "이다",
        "되다",
        "않다",
        "있다",
        "-어",
    ):
        selected.update(heads.get(head, []))
    raw_lmf, files = project_lmf({i: entries[i] for i in selected})
    lmf = {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw_lmf.values())}}}
    verify_native_lmf(lmf, {i: entries[i] for i in selected})
    before = {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in streams["all"]
        if r["kind"] == "word"
    }
    fixture = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "discovery_sha256": sha(DISCOVERY),
        "source_entries": [entries[i] for i in sorted(selected)],
        "formation_proposals": proposals,
        "cases": fixture_cases,
        "before_case_words": {
            w: before[w] for w in sorted({c["surface"] for c in fixture_cases})
        },
        "status": "pre-implementation source-backed proposals, not completed coverage or contextual precision",
    }
    LMF.write_text(json.dumps(lmf, ensure_ascii=False, indent=2) + "\n")
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    write(
        SOURCE,
        {
            "schema_version": 1,
            "checklist": "COV-022m",
            "discovery_sha256": sha(DISCOVERY),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "engine_sha256": sha(ROOT / "src/engine.rs"),
            "fixture_sha256": sha(FIXTURE),
            "lmf_sha256": sha(LMF),
            "lmf_source_files_sha256": files,
            "scanned_entries": len(entries),
            "guidance": GUIDANCE,
            "formation_proposals": proposals,
            "native_inventory": inventory,
            "complete_native_entries": {i: entries[i] for i in sorted(used | selected)},
            "corpora": corpora,
            "before_input": text,
            "before_streams": streams,
            "scope": "Both complete suffix senses/all 157 literal examples, 1,850 native head leads and all original KAIST/GSD derivational 되 rows. Only 158 explicitly attributed formations have agent proposals; other native leads remain unreviewed. Original gold, whole lexical paths and homonyms remain unchanged.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    print(
        f"Frozen {len(streams['all']):,} records per filter and {len(used | selected):,} complete native owners",
        flush=True,
    )


def verify():
    source, fixture, lmf = read(SOURCE), read(FIXTURE), read(LMF)
    assert source["schema_version"] == 1 and source["checklist"] == "COV-022m"
    assert source["discovery_sha256"] == fixture["discovery_sha256"] == sha(DISCOVERY)
    assert source["fixture_sha256"] == sha(FIXTURE) and source["lmf_sha256"] == sha(LMF)
    native = source["complete_native_entries"]
    assert referenced(source["before_streams"]) <= native.keys()
    assert referenced(fixture["before_case_words"]) <= {
        e["id"] for e in fixture["source_entries"]
    }
    heads = defaultdict(list)
    for ident, e in native.items():
        assert e["id"] == ident
        heads[e["headword"]].append(ident)
    assert (
        source["formation_proposals"]
        == fixture["formation_proposals"]
        == formation_proposals(native, heads)
    )
    assert fixture["cases"] == cases(source["formation_proposals"])
    verify_native_lmf(lmf, {e["id"]: e for e in fixture["source_entries"]})
    for e in fixture["source_entries"]:
        assert native[e["id"]] == e
    assert len(source["native_inventory"]) == 1850
    for row in source["native_inventory"]:
        e = native[row["id"]]
        assert row["head"] == e["headword"] and row["native_pos"] == e["pos"]
        assert row["literal_base"] + "되다" == row["head"]
        assert row["base_entries"] == heads.get(row["literal_base"], [])
        assert row["disposition"] == "unreviewed-literal-match"
    from emphatic_ending_runtime import verify_stream

    for mode, stream in source["before_streams"].items():
        verify_stream(
            stream, source["before_streams"]["all"], mode, source["before_input"]
        )
    words = {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }
    for word, record in fixture["before_case_words"].items():
        assert words[word] == record
    assert len({c["id"] for c in fixture["cases"]}) == len(fixture["cases"])
    for case in fixture["cases"]:
        assert not any(
            [l["text"] for l in a["lemmas"]] == case["lemmas"]
            and [l["kind"] for l in a["lemmas"]] == case["lemma_kinds"]
            and [m["form"] for m in a["morphemes"]] == case["morphemes"]
            and [m["kind"] for m in a["morphemes"]] == case["morpheme_kinds"]
            and set(case["required_rules"]) <= set(a["rules"])
            for a in fixture["before_case_words"][case["surface"]]["analyses"]
        ), "source checkpoint already contains a proposed scoped suffix path"
    for corpus in source["corpora"]:
        for s in corpus["sentences"]:
            for row in s["original_rows"]:
                assert (
                    len(row) == 10
                    and "\t".join(row) in s["complete_sentence"].splitlines()
                )
        path = ROOT / corpus["source"]
        if path.exists():
            assert sha(path) == corpus["sha256"]
    if all((ROOT / c["source"]).exists() for c in source["corpora"]):
        assert source["corpora"] == corpus_observations()
    assert (
        source["contextual_verdict"] == "unjudged"
        and source["independent_review"] == "pending"
    )
    print(
        f"Verified both -되다 senses, 157 examples, 1,850 unreviewed native leads, 158 attributed formation proposals and {len(fixture['cases'])} stable cases; original corpora and all before filters retained."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.cli and a.dictionary
        freeze(a.cli.resolve(), a.dictionary.resolve())
