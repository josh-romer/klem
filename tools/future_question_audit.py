"""Freeze future-question noun-clause sources and prior readings before extension.

Written discoveries are not contextual gold. Complete native groups and original
annotated sentences remain separate from authored structural regressions.
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

SOURCE = ROOT / "docs/future-question-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/future-question-sources.json"
LMF = ROOT / "tests/fixtures/krdict-future-question.json"
RULE = "particle.future_question"
SUPPLEMENT = ROOT / "tests/fixtures/future-question-corpus-supplement.json"
PARTICLES = [
    "에서",
    "에게",
    "보다",
    "부터",
    "조차",
    "마저",
    "까지",
    "에",
    "의",
    "와",
    "과",
    "가",
    "를",
    "는",
    "은",
    "도",
    "만",
]
PATTERN = r"(?<![가-힣])[가-힣]+지(?:" + "|".join(PARTICLES) + r")[가-힣]*(?![가-힣])"
GUIDANCE = {
    "noun_clause": {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=315739",
        "answered": "2025-06-04",
        "finding": "NIKL identifies the question ending -ㄹ지 in 달지의 and describes a noun-clause analysis that permits a following particle. This licenses a structural alternative, not contextual or register selection.",
    },
    "explicit_copula_do": {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=27&pageIndex=1&qna_seq=318654",
        "answered": "2025-07-24",
        "finding": "NIKL analyzes 것일지도 as bound noun 것, overt copula 이, ending -ㄹ지 and particle 도. No unseen 모르다 or nominalizer 기 is restored.",
    },
}


def cases():
    rows = []

    def add(
        surface,
        heads,
        kinds,
        forms,
        verdict="required",
        origin="authored_structural_extension",
    ):
        rows.append(
            {
                "id": "future-question-"
                + surface
                + "-"
                + "-".join(heads)
                + "-"
                + "-".join(forms),
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "verdict": verdict,
                "required_rule": RULE,
                "origin": origin,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    for surface, head, origin in [
        ("날지도", "나다", "tracked_native_accident_dependency"),
        ("될지는", "되다", "native_14136_1_11"),
        ("처리할지에", "처리하다", "native_14940_1_8"),
        ("좋아질지를", "좋아지다", "native_14983_1_7"),
        ("지낼지가", "지내다", "native_17173_4_8"),
        ("달지의", "달다", "nikl_noun_clause"),
    ]:
        particle = next(
            p for p in ["도", "는", "에", "를", "가", "의"] if surface.endswith(p)
        )
        add(surface, [head], ["predicate"], ["을지", particle], origin=origin)
    add(
        "것일지도",
        ["것", "이다"],
        ["nominal", "copula"],
        ["을지", "도"],
        origin="nikl_explicit_copula",
    )
    for surface, head in [
        ("갈지", "가다"),
        ("먹을지", "먹다"),
        ("살지", "살다"),
        ("들을지", "듣다"),
        ("도울지", "돕다"),
        ("부을지", "붓다"),
        ("지을지", "짓다"),
        ("파랄지", "파랗다"),
        ("좋을지", "좋다"),
        ("있을지", "있다"),
        ("없을지", "없다"),
        ("나을지", "낫다"),
    ]:
        for particle in ["도", "는"]:
            add(surface + particle, [head], ["predicate"], ["을지", particle])
    for particle in [
        "에",
        "의",
        "와",
        "가",
        "를",
        "보다",
        "에서",
        "만",
        "까지",
        "부터",
        "조차",
        "마저",
    ]:
        add("갈지" + particle, ["가다"], ["predicate"], ["을지", particle])
    for surface, heads, kinds, forms in [
        ("먹었을지도", ["먹다"], ["predicate"], ["었"]),
        ("먹으실지도", ["먹다"], ["predicate"], ["시"]),
        ("먹으셨을지도", ["먹다"], ["predicate"], ["시", "었"]),
        ("먹겠을지도", ["먹다"], ["predicate"], ["겠"]),
        ("먹어볼지도", ["먹다", "보다"], ["predicate", "auxiliary"], ["어"]),
        ("먹어봤을지도", ["먹다", "보다"], ["predicate", "auxiliary"], ["어", "었"]),
        ("먹었어볼지도", ["먹다", "보다"], ["predicate", "auxiliary"], ["었", "어"]),
        ("먹지않을지도", ["먹다", "않다"], ["predicate", "auxiliary"], ["지"]),
        ("먹지않았을지도", ["먹다", "않다"], ["predicate", "auxiliary"], ["지", "었"]),
        ("학생다울지도", ["학생"], ["nominal"], ["답다"]),
        ("학생일지도", ["학생", "이다"], ["nominal", "copula"], []),
        ("학교일지도", ["학교", "이다"], ["nominal", "copula"], []),
        ("학교였을지도", ["학교", "이다"], ["nominal", "copula"], ["었"]),
        ("학생이실지도", ["학생", "이다"], ["nominal", "copula"], ["시"]),
        ("먹기일지도", ["먹다", "이다"], ["predicate", "copula"], ["기"]),
    ]:
        add(surface, heads, kinds, forms + ["을지", "도"])
    for surface, head in [
        ("가을지도", "가다"),
        ("먹ㄹ지도", "먹다"),
        ("살을지도", "살다"),
        ("듣ㄹ지도", "듣다"),
        ("돕ㄹ지도", "돕다"),
        ("붓ㄹ지도", "붓다"),
        ("짓ㄹ지도", "짓다"),
        ("좋ㄹ지도", "좋다"),
    ]:
        add(surface, [head], ["predicate"], ["을지", "도"], "forbidden")
    add("갈지은", ["가다"], ["predicate"], ["을지", "은"], "forbidden")
    add("갈지도은", ["가다"], ["predicate"], ["을지", "도", "은"], "forbidden")
    add(
        "갈지도",
        ["가다"],
        ["predicate"],
        ["을지", "기", "도"],
        "forbidden",
        "no_unwritten_nominalizer",
    )
    add(
        "것일지도",
        ["것", "이다", "모르다"],
        ["nominal", "copula", "predicate"],
        ["을지", "도"],
        "forbidden",
        "no_unwritten_following_predicate",
    )
    assert len(rows) == len({r["id"] for r in rows})
    return rows


def discover(entries):
    hits = []
    for e in entries.values():
        for s in e["senses"]:
            for gi, group in enumerate(s["examples"], 1):
                for ti, text in enumerate(group):
                    for match in re.finditer(PATTERN, text):
                        word = match[0]
                        pos = next(
                            i
                            for i in range(len(word) - 2, -1, -1)
                            if word[i] == "지"
                            and any(word[i + 1 :].startswith(p) for p in PARTICLES)
                        )
                        if not pos or (ord(word[pos - 1]) - 0xAC00) % 28 != 8:
                            continue
                        identity = [
                            e["id"],
                            s["id"],
                            gi,
                            ti,
                            match.start(),
                            match.end(),
                        ]
                        hits.append(
                            {
                                "id": "future-question-native-" + digest(identity)[:24],
                                "entry": e["id"],
                                "sense": s["id"],
                                "group": gi,
                                "text_index": ti,
                                "surface": word,
                                "text": text,
                                "complete_group": group,
                                "char_span": [match.start(), match.end()],
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
    native = load_dictionary(dictionary)
    hits = discover(native)
    assert len(hits) == 589
    corpora = []
    for p in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        selected = []
        for block in p.read_text().split("\n\n"):
            rows = [
                line.split("\t")
                for line in block.splitlines()
                if len(line.split("\t")) == 10 and line.split("\t")[0].isdigit()
            ]
            matched = [
                r
                for r in rows
                if ("ㄹ지" in r[2] or "을지" in r[2])
                and any(
                    re.fullmatch(r"[가-힣]+지" + ending, r[1]) for ending in PARTICLES
                )
            ]
            if matched:
                selected.append(
                    {
                        "complete_sentence": block,
                        "matched_tokens": matched,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        corpora.append(
            {
                "source": str(p.relative_to(ROOT)),
                "source_sha256": sha(p),
                "sentences": selected,
            }
        )
    rows = cases()
    surfaces = {h["surface"] for h in hits} | {c["surface"] for c in rows}
    surfaces.update(
        r[1] for c in corpora for s in c["sentences"] for r in s["matched_tokens"]
    )
    surfaces.update(["사고날지도", "학교에서사고날지도", "났다던데"])
    # Freeze the independent ending owner before any follower is added.
    cores = {
        c["surface"][: -len(c["morphemes"][-1])]
        for c in rows
        if c["verdict"] == "required"
    }
    surfaces.update(cores)
    text = " ".join(sorted(surfaces))
    streams = {
        mode: list(
            map(
                json.loads,
                subprocess.check_output(
                    [
                        str(cli.resolve()),
                        "text",
                        "-",
                        "--dictionary",
                        str(dictionary.resolve()),
                        "--suggest-spacing",
                        *flags,
                    ],
                    input=text.encode(),
                ).splitlines(),
            )
        )
        for mode, flags in MODES.items()
    }
    used = {
        "krdict:86686",
        "krdict:86133",
        "krdict:68853",
        "krdict:62210",
        "krdict:66370",
        "krdict:27500",
    } | {h["entry"] for h in hits}
    heads = {head for c in rows for head in c["lemmas"]} | {"학교", "나다", "사고"}
    used.update(i for i, e in native.items() if e["headword"] in heads)

    def visit(value):
        if isinstance(value, dict):
            ident = value.get("id")
            if isinstance(ident, str) and ident.startswith("krdict:"):
                used.add(ident)
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)

    visit(streams)
    entries = {i: native[i] for i in sorted(used)}
    raw, hashes = project_lmf(entries)
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
        "checklist": "COV-018ab / COV-020r",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "complete_native_entries": entries,
        "raw_source_sha256": hashes,
        "primary_guidance": GUIDANCE,
        "native_pattern": PATTERN,
        "discoveries": hits,
        "corpora": corpora,
        "before_input": text,
        "before_streams": streams,
        "scope": "Source and spelling observations; noun-clause structural inferences are separately tested. No contextual or independent judgment is inferred.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(SOURCE, source)
    finish_fixture()
    freeze_corpus_supplement(cli, dictionary)


def freeze_corpus_supplement(cli, dictionary):
    """Retain original morphology in MISC without replacing the lemma-column freeze."""
    assert not SUPPLEMENT.exists()
    source = read(SOURCE)
    assert (
        sha(cli) == source["cli_sha256"]
        and sha(dictionary) == source["dictionary_sha256"]
    )
    corpora = []
    for corpus in source["corpora"]:
        path = ROOT / corpus["source"]
        assert sha(path) == corpus["source_sha256"]
        tokens = []
        for block in path.read_text().split("\n\n"):
            for line in block.splitlines():
                row = line.split("\t")
                if len(row) != 10 or not row[0].isdigit():
                    continue
                if "ㄹ지" in row[2] or "을지" in row[2]:
                    continue
                if not ("ㄹ지" in row[9] or "을지" in row[9]):
                    continue
                if not any(re.fullmatch(r"[가-힣]+지" + p, row[1]) for p in PARTICLES):
                    continue
                sent = next(
                    l.removeprefix("# sent_id = ")
                    for l in block.splitlines()
                    if l.startswith("# sent_id = ")
                )
                tokens.append(
                    {
                        "id": "future-question-origlemma-"
                        + digest([corpus["source"], sent, row[0]])[:24],
                        "source_row": row,
                        "complete_sentence": block,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        corpora.append(
            {
                "source": corpus["source"],
                "source_sha256": corpus["source_sha256"],
                "tokens": tokens,
            }
        )
    assert sum(len(c["tokens"]) for c in corpora) == 8
    words = sorted({t["source_row"][1] for c in corpora for t in c["tokens"]})
    stream = list(
        map(
            json.loads,
            subprocess.check_output(
                [
                    str(cli.resolve()),
                    "text",
                    "-",
                    "--dictionary",
                    str(dictionary.resolve()),
                    "--suggest-spacing",
                ],
                input=" ".join(words).encode(),
            ).splitlines(),
        )
    )
    value = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "cli_before_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "scope": "Append-only original OrigLemma discoveries missed by the initial lemma-column scan; the initial source freeze and 42-token selection remain immutable.",
        "corpora": corpora,
        "before_words": {
            r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
            for r in stream
            if r["kind"] == "word"
        },
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    with SUPPLEMENT.open("x") as file:
        file.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def before_words(source):
    # CLI text records serialize WordAnalysis under `analysis`; breakdowns
    # are derived from each Analysis in the library, not a CLI record field.
    return {
        r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }


def finish_fixture():
    """Complete a failed fixture projection without rewriting frozen evidence."""
    assert not FIXTURE.exists()
    source = read(SOURCE)
    verify_native_lmf(read(LMF), source["complete_native_entries"])
    projected = copy.deepcopy(list(source["complete_native_entries"].values()))
    for e in projected:
        for s in e["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(LMF),
                "source_entries": projected,
                "corpora": source["corpora"],
                "license": read(ROOT / "docs/lexical-nada-listed-preflight.json.gz")[
                    "license"
                ],
                "cases": cases(),
                "before_words": before_words(source),
                "independent_cores": sorted(
                    {
                        c["surface"][: -len(c["morphemes"][-1])]
                        for c in cases()
                        if c["verdict"] == "required"
                    }
                ),
                "tracked_dependency": "lexical-nada-discovery-ef9a33c60226f6c9ba4fe452",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify():
    s, f = read(SOURCE), read(FIXTURE)
    assert f["source_sha256"] == sha(SOURCE) and f["lmf_sha256"] == sha(LMF)
    assert f["cases"] == cases()
    assert f["corpora"] == s["corpora"]
    assert s["primary_guidance"] == GUIDANCE and s["native_pattern"] == PATTERN
    assert s["discoveries"] == discover(s["complete_native_entries"])
    assert len(s["discoveries"]) == 589
    assert f["before_words"] == before_words(s)
    verify_native_lmf(read(LMF), s["complete_native_entries"])
    for h in s["discoveries"]:
        entry = s["complete_native_entries"][h["entry"]]
        sense = next(x for x in entry["senses"] if x["id"] == h["sense"])
        assert sense["examples"][h["group"] - 1] == h["complete_group"]
        a, b = h["span"]["start"], h["span"]["end"]
        assert h["text"].encode()[a:b].decode() == h["surface"]
    for corpus in s["corpora"]:
        for sentence in corpus["sentences"]:
            rows = [
                line.split("\t")
                for line in sentence["complete_sentence"].splitlines()
                if len(line.split("\t")) == 10 and line.split("\t")[0].isdigit()
            ]
            assert sentence["matched_tokens"] == [
                r
                for r in rows
                if ("ㄹ지" in r[2] or "을지" in r[2])
                and any(re.fullmatch(r"[가-힣]+지" + p, r[1]) for p in PARTICLES)
            ]
            assert sentence["contextual_verdict"] == "unjudged"
            assert sentence["independent_review"] == "pending"
    supplement = read(SUPPLEMENT)
    assert supplement["source_sha256"] == sha(SOURCE)
    assert supplement["cli_before_sha256"] == s["cli_sha256"]
    assert supplement["dictionary_sha256"] == s["dictionary_sha256"]
    assert len(supplement["before_words"]) == 6
    assert len(supplement["corpora"]) == 6
    count = 0
    for corpus, original in zip(supplement["corpora"], s["corpora"], strict=True):
        assert corpus["source"] == original["source"]
        assert corpus["source_sha256"] == original["source_sha256"]
        for token in corpus["tokens"]:
            row, sentence = token["source_row"], token["complete_sentence"]
            assert "\t".join(row) in sentence.splitlines()
            assert not ("ㄹ지" in row[2] or "을지" in row[2])
            assert "ㄹ지" in row[9] or "을지" in row[9]
            assert any(re.fullmatch(r"[가-힣]+지" + p, row[1]) for p in PARTICLES)
            sent = next(
                line.removeprefix("# sent_id = ")
                for line in sentence.splitlines()
                if line.startswith("# sent_id = ")
            )
            assert (
                token["id"]
                == "future-question-origlemma-"
                + digest([corpus["source"], sent, row[0]])[:24]
            )
            assert (
                token["contextual_verdict"] == "unjudged"
                and token["independent_review"] == "pending"
            )
            count += 1
    assert count == 8
    print("Verified eight append-only OrigLemma tokens and six prior words.")
    print(
        f"Verified {len(f['cases'])} future-question cases, 589 native spelling observations, {len(f['before_words'])} prior words and {sum(len(h['matched_tokens']) for c in s['corpora'] for h in c['sentences'])} original annotated tokens; contextual review remains pending."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--finish-fixture", action="store_true")
    p.add_argument("--freeze-corpus-supplement", action="store_true")
    p.add_argument("--cli-before", type=Path)
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    if a.freeze_corpus_supplement:
        if not a.cli_before or not a.dictionary:
            p.error("supplement freeze requires --cli-before and --dictionary")
        freeze_corpus_supplement(a.cli_before, a.dictionary)
        verify()
    elif a.finish_fixture:
        finish_fixture()
        verify()
    elif a.verify:
        verify()
    elif a.cli_before and a.dictionary:
        freeze(a.cli_before, a.dictionary)
        verify()
    else:
        p.error("freeze requires --cli-before and --dictionary")
