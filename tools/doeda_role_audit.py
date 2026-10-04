"""Freeze -게/-게끔 되다 source observations before introducing role alternatives.

Dictionary/corpus occurrences are observations, not repaired contextual gold.
The proposed lexical role follows KRDict; NIKL independently supports retaining
the existing auxiliary representation. Other 되다 complements are dependencies.
"""

import argparse
import copy
import itertools
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from emphatic_ending_runtime import verify_stream
from lexical_nada_audit import ROOT, digest, load_dictionary, read, run, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/doeda-role-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-role-sources.json"
LMF = ROOT / "tests/fixtures/krdict-doeda-role.json"
MAIN = "krdict:89858"
ADJECTIVE = "krdict:48214"
PATTERN = re.compile(
    r"(?<![가-힣])(?P<left>[가-힣]+?(?:게끔|게))"
    r"(?P<gap>\s*)(?P<right>(?:되|돼|됐|된|될|됩)[가-힣]*)"
)
LEFT = re.compile(r"[가-힣]+(?:게끔|게)$")
RIGHT = re.compile(r"(?:되|돼|됐|된|될|됩)[가-힣]*$")
NOVEL = ROOT / "data/books/mujeong.txt"
GUIDANCE = {
    "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&qna_seq=312009&pageIndex=1",
    "title": "본용언 보조용언",
    "publisher": "국립국어원 온라인가나다",
    "question_date": "2025-03-27",
    "answer_date": "2025-03-28",
    "accessed": "2026-10-04",
    "summary": "The answer describes -게 하다 and -게 되다 as main-plus-auxiliary constructions. Its cited 되다 auxiliary-verb sense permits a verb or adjective before -게 and denotes realization of an action or state. This supports retaining the existing auxiliary role; it does not supply an auxiliary POS entry in the pinned KRDict snapshot.",
    "limits": "No literal -게끔 classification or broader connector license is inferred from this answer. The original annotated 게끔 compositions and the emphatic ending preflight remain separate evidence. Sentence meaning, spelling and spacing intentions remain unjudged.",
}


def cases():
    rows = []

    def add(surface, heads, kinds, forms, source, required=True):
        rows.append(
            {
                "id": "doeda-role-" + digest([surface, heads, kinds, forms])[:24],
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "morpheme_kinds": [
                    "prefinal" if f in {"시", "었", "겠"} else "ending" for f in forms
                ],
                "verdict": "required" if required else "forbidden",
                "source": source,
                "scope": "lexical_role_alternative"
                if required
                else "connector_projection_boundary",
                "required_rules": ["lexical.doeda.complement"],
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    # Positive lexical alternatives preserve both predicates and each owner's
    # own endings. Consonant connectors retain the actual closed stem.
    for stem, head in [
        ("먹", "먹다"),
        ("가", "가다"),
        ("살", "살다"),
        ("좋", "좋다"),
        ("없", "없다"),
        ("타당하", "타당하다"),
    ]:
        for connector in ("게", "게끔"):
            for right, forms in [
                ("되다", ["다"]),
                ("된다", ["는다"]),
                ("되었다", ["었", "다"]),
                ("됐다", ["었", "다"]),
                ("됩니다", ["습니다"]),
                ("되는", ["는"]),
            ]:
                add(
                    stem + connector + right,
                    [head, "되다"],
                    ["predicate", "predicate"],
                    [connector, *forms],
                    MAIN if connector == "게" else "emphatic-ending-corpus-composition",
                )
    for connector in ("게", "게끔"):
        add(
            "살" + connector + "되어있다",
            ["살다", "되다", "있다"],
            ["predicate", "predicate", "auxiliary"],
            [connector, "어", "다"],
            MAIN if connector == "게" else "emphatic-ending-corpus-composition",
        )
        add(
            "먹" + connector + "되지않는다",
            ["먹다", "되다", "않다"],
            ["predicate", "predicate", "auxiliary"],
            [connector, "지", "는다"],
            MAIN if connector == "게" else "emphatic-ending-corpus-composition",
        )
        add(
            "먹으시" + connector + "되었습니다",
            ["먹다", "되다"],
            ["predicate", "predicate"],
            ["시", connector, "었", "습니다"],
            MAIN if connector == "게" else "emphatic-ending-corpus-composition",
        )
    # These are scoped projection controls, not declarations that a sentence
    # with another native complement is grammatically impossible.
    for word, forms in [
        ("먹고되다", ["고", "다"]),
        ("먹어되다", ["어", "다"]),
        ("먹지되다", ["지", "다"]),
    ]:
        add(word, ["먹다", "되다"], ["predicate", "predicate"], forms, MAIN, False)
    return rows


def discoveries(entries):
    hits = []
    for entry in sorted(entries.values(), key=lambda e: e["id"]):
        for sense in entry["senses"]:
            for gi, group in enumerate(sense["examples"]):
                for ti, text in enumerate(group):
                    for m in PATTERN.finditer(text):
                        hits.append(
                            {
                                "id": "doeda-role-native-"
                                + digest([entry["id"], sense["id"], gi, ti, m.span()])[
                                    :24
                                ],
                                "entry": entry["id"],
                                "sense": sense["id"],
                                "group": gi,
                                "text_index": ti,
                                "complete_group": group,
                                "text": text,
                                "surface": m[0],
                                "left": m["left"],
                                "gap": m["gap"],
                                "right": m["right"],
                                "char_span": list(m.span()),
                                "span": {
                                    "start": len(text[: m.start()].encode()),
                                    "end": len(text[: m.end()].encode()),
                                },
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return hits


def corpus_observations():
    result = []
    for path in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for text in path.read_text().strip().split("\n\n"):
            rows = [l.split("\t") for l in text.splitlines() if not l.startswith("#")]
            rows = [r for r in rows if len(r) == 10 and r[0].isdigit()]
            joined = [
                r for r in rows if (m := PATTERN.fullmatch(r[1])) and not m["gap"]
            ]
            pairs = [
                [a, b]
                for a, b in itertools.pairwise(rows)
                if LEFT.fullmatch(a[1]) and RIGHT.fullmatch(b[1])
            ]
            if joined or pairs:
                sentences.append(
                    {
                        "complete_sentence": text,
                        "joined_rows": joined,
                        "spaced_pairs": pairs,
                    }
                )
        result.append(
            {
                "source": str(path.relative_to(ROOT)),
                "sha256": sha(path),
                "sentences": sentences,
            }
        )
    assert len(result) == 6
    return result


def novel_observations():
    text = NOVEL.read_text()
    fingerprint = sha(NOVEL)
    hits = []
    for m in PATTERN.finditer(text):
        start = text.rfind("\n\n", 0, m.start()) + 2
        if start == 1:
            start = 0
        end = text.find("\n\n", m.end())
        if end < 0:
            end = len(text)
        hits.append(
            {
                "id": "doeda-role-novel-" + digest([fingerprint, m.span()])[:24],
                "surface": m[0],
                "left": m["left"],
                "gap": m["gap"],
                "right": m["right"],
                "char_span": list(m.span()),
                "span": {
                    "start": len(text[: m.start()].encode()),
                    "end": len(text[: m.end()].encode()),
                },
                "paragraph_char_span": [start, end],
                "paragraph_byte_span": [
                    len(text[:start].encode()),
                    len(text[:end].encode()),
                ],
                "complete_paragraph": text[start:end],
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return {
        "path": str(NOVEL.relative_to(ROOT)),
        "sha256": fingerprint,
        "discoveries": hits,
    }


def surfaces(hits, corpora, novel):
    words = {c["surface"] for c in cases()}
    for h in hits + novel["discoveries"]:
        words.update([h["left"], h["right"], h["left"] + h["right"]])
    for c in corpora:
        for s in c["sentences"]:
            words.update(r[1] for r in s["joined_rows"])
            for left, right in s["spaced_pairs"]:
                words.update([left[1], right[1], left[1] + right[1]])
    return sorted(words)


def referenced_ids(value):
    result = set()
    if isinstance(value, dict):
        ident = value.get("id")
        if isinstance(ident, str) and ident.startswith("krdict:"):
            result.add(ident)
        for item in value.values():
            result |= referenced_ids(item)
    elif isinstance(value, list):
        for item in value:
            result |= referenced_ids(item)
    return result


def freeze(cli, dictionary):
    assert not any(p.exists() for p in (SOURCE, FIXTURE, LMF))
    native = load_dictionary(dictionary)
    hits, corpora, novel = (
        discoveries(native),
        corpus_observations(),
        novel_observations(),
    )
    words = surfaces(hits, corpora, novel)
    print(
        f"Freezing {len(hits)} native occurrences and {len(words)} words.", flush=True
    )
    text, streams = run(cli, dictionary, words)
    before_words = {r["surface"]: r for r in streams["all"] if r["kind"] == "word"}
    assert len(before_words) == len(words)
    headword_ids = sorted(i for i, e in native.items() if e["headword"] == "되다")
    all_ids = set(headword_ids) | {h["entry"] for h in hits} | referenced_ids(streams)
    full = {i: native[i] for i in sorted(all_ids)}
    # Every discovery owner/reading is preserved in the compressed preflight.
    # Importer fixtures cover the finite case cohort; this distinction is
    # explicit rather than claiming a small adapter covers the complete scan.
    case_ids = {MAIN, ADJECTIVE} | referenced_ids(
        [before_words[c["surface"]] for c in cases()]
    )
    case_heads = {h for c in cases() for h in c["lemmas"]}
    case_ids |= {i for i, e in native.items() if e["headword"] in case_heads}
    case_entries = {i: native[i] for i in sorted(case_ids)}
    raw, hashes = project_lmf(case_entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    source = {
        "schema_version": 1,
        "checklist": "COV-019ag",
        "implementation_status": "preflight_only",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "prior_emphatic_source_sha256": sha(
            ROOT / "docs/emphatic-ending-source-preflight.json.gz"
        ),
        "prior_emphatic_runtime_sha256": sha(
            ROOT / "docs/emphatic-ending-packaged-runtime.json.gz"
        ),
        "native_scan_entries": len(native),
        "doeda_headword_ids": headword_ids,
        "pattern": PATTERN.pattern,
        "discoveries": hits,
        "corpora": corpora,
        "novel": novel,
        "primary_guidance": GUIDANCE,
        "complete_native_entries": full,
        "case_native_ids": sorted(case_ids),
        "raw_adapter_source_sha256": hashes,
        "before_input": text,
        "before_streams": streams,
        "other_native_complements": {
            s["id"]: {
                "patterns": s["patterns"],
                "disposition": "separate_connector_dependency",
            }
            for s in native[MAIN]["senses"]
            if any(
                any(f in p for f in ("도록", "기로", "어야", "면", "어도", "어서는"))
                for p in s["patterns"]
            )
        },
        "limits": "Literal spelling matches are source observations, not inferred lemmas, grammatical licenses or contextual gold. All scan owners and before-reading endpoints are complete in this archive. The finite importer fixture is a separately identified subset. Preserve auxiliary-role paths, native adjective conflicts, original annotations and separate connector dependencies.",
        "license": read(ROOT / "docs/emphatic-ending-source-preflight.json.gz")[
            "license"
        ],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(SOURCE, source)
    projected = copy.deepcopy(list(case_entries.values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    fixture = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "lmf_sha256": sha(LMF),
        "cases": cases(),
        "source_entries": projected,
        "before_case_words": {
            w: before_words[w] for w in sorted({c["surface"] for c in cases()})
        },
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    verify()


def verify(dictionary=None, cli=None):
    source, fixture = read(SOURCE), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert source["schema_version"] == 1 and source["checklist"] == "COV-019ag"
    assert (
        source["implementation_status"] == "preflight_only"
        and source["pattern"] == PATTERN.pattern
    )
    assert source["primary_guidance"] == GUIDANCE and fixture["cases"] == cases()
    assert source["prior_emphatic_source_sha256"] == sha(
        ROOT / "docs/emphatic-ending-source-preflight.json.gz"
    )
    assert source["prior_emphatic_runtime_sha256"] == sha(
        ROOT / "docs/emphatic-ending-packaged-runtime.json.gz"
    )
    native = source["complete_native_entries"]
    assert native[MAIN]["pos"] == "동사" and native[ADJECTIVE]["pos"] == "형용사"
    assert source["other_native_complements"] == {
        s["id"]: {
            "patterns": s["patterns"],
            "disposition": "separate_connector_dependency",
        }
        for s in native[MAIN]["senses"]
        if any(
            any(f in p for f in ("도록", "기로", "어야", "면", "어도", "어서는"))
            for p in s["patterns"]
        )
    }
    assert source["doeda_headword_ids"] == sorted(
        i for i, e in native.items() if e["headword"] == "되다"
    )
    assert discoveries(native) == source["discoveries"]
    assert len({h["id"] for h in source["discoveries"]}) == len(source["discoveries"])
    for h in source["discoveries"]:
        a, b = h["char_span"]
        assert h["text"][a:b] == h["surface"] == h["left"] + h["gap"] + h["right"]
        assert (
            h["text"].encode()[h["span"]["start"] : h["span"]["end"]].decode()
            == h["surface"]
        )
    assert len(source["corpora"]) == 6
    for c in source["corpora"]:
        for s in c["sentences"]:
            rows = [
                l.split("\t")
                for l in s["complete_sentence"].splitlines()
                if not l.startswith("#")
            ]
            rows = [r for r in rows if len(r) == 10 and r[0].isdigit()]
            assert s["joined_rows"] == [
                r for r in rows if (m := PATTERN.fullmatch(r[1])) and not m["gap"]
            ]
            assert s["spaced_pairs"] == [
                [a, b]
                for a, b in itertools.pairwise(rows)
                if LEFT.fullmatch(a[1]) and RIGHT.fullmatch(b[1])
            ]
            for row in s["joined_rows"] + [
                r for pair in s["spaced_pairs"] for r in pair
            ]:
                assert (
                    len(row) == 10
                    and "\t".join(row) in s["complete_sentence"].splitlines()
                )
    for h in source["novel"]["discoveries"]:
        a, b = h["char_span"]
        start, end = h["paragraph_char_span"]
        assert start <= a < b <= end
        assert h["complete_paragraph"][a - start : b - start] == h["surface"]
        assert PATTERN.fullmatch(h["surface"])
        byte_start, byte_end = h["paragraph_byte_span"]
        paragraph = h["complete_paragraph"].encode()
        assert byte_end - byte_start == len(paragraph)
        assert (
            paragraph[
                h["span"]["start"] - byte_start : h["span"]["end"] - byte_start
            ].decode()
            == h["surface"]
        )
    words = surfaces(source["discoveries"], source["corpora"], source["novel"])
    assert source["before_input"] == "\n".join(words) + "\n"
    assert set(source["before_streams"]) == {"all", "headword", "compatible"}
    for mode, records in source["before_streams"].items():
        verify_stream(
            records, source["before_streams"]["all"], mode, source["before_input"]
        )
        assert "".join(r["surface"] for r in records) == source["before_input"]
        assert [r["surface"] for r in records if r["kind"] == "word"] == words
        offset = 0
        for r in records:
            assert r["span"]["start"] == offset
            offset += len(r["surface"].encode())
            assert r["span"]["end"] == offset
    assert referenced_ids(source["before_streams"]) <= native.keys()
    assert {
        i
        for i, e in native.items()
        if e["pos"] in {"보조 동사", "보조 형용사"} and e["headword"] == "되다"
    } == set()
    case_entries = {i: native[i] for i in source["case_native_ids"]}
    verify_native_lmf(read(LMF), case_entries)
    projected = copy.deepcopy(list(case_entries.values()))
    for e in projected:
        for s in e["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
    assert fixture["source_entries"] == projected
    before = {
        r["surface"]: r for r in source["before_streams"]["all"] if r["kind"] == "word"
    }
    assert fixture["before_case_words"] == {
        w: before[w] for w in sorted({c["surface"] for c in cases()})
    }
    for report in (source, fixture):
        assert (
            report["contextual_verdict"] == "unjudged"
            and report["independent_review"] == "pending"
        )
    for h in source["discoveries"] + source["novel"]["discoveries"]:
        assert (
            h["contextual_verdict"] == "unjudged"
            and h["independent_review"] == "pending"
        )
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        full = load_dictionary(dictionary)
        assert (
            len(full) == source["native_scan_entries"]
            and discoveries(full) == source["discoveries"]
        )
        assert all(full[i] == e for i, e in native.items())
        assert source["doeda_headword_ids"] == sorted(
            i for i, e in full.items() if e["headword"] == "되다"
        )
        assert (
            corpus_observations() == source["corpora"]
            and novel_observations() == source["novel"]
        )
        raw, hashes = project_lmf(case_entries)
        assert hashes == source["raw_adapter_source_sha256"]
        assert read(LMF)["LexicalResource"]["Lexicon"]["LexicalEntry"] == list(
            raw.values()
        )
    if cli:
        assert dictionary and sha(cli) == source["cli_sha256"]
        text, streams = run(cli, dictionary, words)
        assert text == source["before_input"] and streams == source["before_streams"]
    print(
        f"Verified 되다 role preflight: {len(source['discoveries'])} native observations, {len(words)} words, {len(native)} complete native owners, {len(cases())} proposed paths; original auxiliary roles and contextual/independent limits retained."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    if a.verify:
        verify(
            a.dictionary.resolve() if a.dictionary else None,
            a.cli.resolve() if a.cli else None,
        )
    else:
        assert a.cli and a.dictionary
        freeze(a.cli.resolve(), a.dictionary.resolve())
