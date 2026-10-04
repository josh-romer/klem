"""Freeze the remaining 되다 complements and original negative-adverb contexts.

All native examples and six original corpus files are scanned. Literal matches
are observations, including noun/particle lookalikes, not grammatical licenses.
KRDict lexical and NIKL auxiliary classifications retain separate proposals.
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

SOURCE = ROOT / "docs/doeda-complement-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-complement-sources.json"
LMF = ROOT / "tests/fixtures/krdict-doeda-complement.json"
MAIN = "krdict:89858"
ADJECTIVE = "krdict:48214"
COMPONENT_HEADS = {
    "-도록",
    "-기로",
    "-기",
    "로",
    "-어야",
    "-아야",
    "-여야",
    "-으면",
    "-면",
    "-어도",
    "-아도",
    "-여도",
    "-어서",
    "-아서",
    "-여서",
    "는",
}
# Surface spelling cannot decide whether 야/면/도 is an ending or a noun
# particle. Preserve every literal match; later structural/context review must
# decide the represented construction rather than hiding these lookalikes.
LEFT = re.compile(r"[가-힣]+(?:도록|기로|서는|야|면|도)$")
RIGHT = re.compile(r"(?:되|돼|됐|된|될|됩|됨)[가-힣]*$")
NEG_RIGHT = re.compile(r"(?:안)?(?:되|돼|됐|된|될|됩|됨)[가-힣]*$")
PENDING_PROBES = [
    "좋기로되었다",
    "학생이기로되었다",
    "학생이도록되었다",
    "먹었기로되었다",
    "먹겠으면안된다",
    "먹고싶어도된다",
    "학생이어도되지않는다",
    "먹어서는되지않는다",
    "갔어야되었다",
    "먹고있어야된다",
    "의사면안된다",
    "먹도록도되었다",
    "먹도록은되었다",
    "먹도록까지되었다",
    "안된다",
    "안돼요",
    "안되다",
    "되다",
]

PATTERN = re.compile(
    r"(?<![가-힣])(?P<left>[가-힣]+?(?:도록|기로|서는|야|면|도))"
    r"(?P<gap>\s*)(?:(?P<negative>안)(?P<negative_gap>\s*))?"
    r"(?P<right>(?:되|돼|됐|된|될|됩|됨)[가-힣]*)"
)
NOVEL = ROOT / "data/books/mujeong.txt"
PRIOR = ROOT / "docs/doeda-role-source-preflight.json.gz"
PRIOR_RUNTIME = ROOT / "docs/doeda-role-packaged-runtime.json.gz"
NIKL = "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=318411"
GUIDANCE = {
    "url": NIKL,
    "title": "[재질문] 껀 건",
    "publisher": "국립국어원 온라인가나다",
    "answer_date": "2025-07-18",
    "accessed": "2026-10-04",
    "summary": "The official answer appends the dictionary's 되다 senses. Sense 017 is a verb after 도록/기로. Senses 018/019/021 are auxiliary verbs after necessity, conditional and permission/prohibition complements, explicitly permitting predicate and copula stems. The question's spacing claims are not treated as official grammar evidence.",
    "limits": "The pinned KRDict instead tags all four corresponding senses in verb entry 89858. Preserve both attributed role proposals without rewriting native POS or gold. No scheduled-construction adjective/copula or prefinal license is inferred solely from the unrelated cause/concession ending 기로. Negative-adverb 안 and lexical compound 안되다 remain distinct.",
}
TEACHING_GUIDANCE = {
    "url": "https://www.korean.go.kr/common/download.do?c_file_name=5a2db2bc-a7ad-49f4-84a4-34b20ad33ffc_0.pdf&file_path=reportData&o_file_name=한국어교육%20문법표현%20내용개발%20연구_3단계.pdf",
    "title": "한국어교육 문법 · 표현 내용 개발 연구(3단계)",
    "pdf_sha256": "f6558a802b61115ead3ed20af9ecd7cf7b56f94e4c5a3342bf67f40bf0811268",
    "findings": [
        {
            "printed_pages": [580, 581, 582],
            "pdf_page_indices": [593, 594, 595],
            "summary": "The prohibition expression uses conditional endings with verbs, adjectives and copulas, including colloquial vowel-noun copula omission. It excludes a left modal 겠 in this construction; negative 지 않다 is not a replacement for the particular prohibition unit. Register and prohibition readings differ from ordinary lexical negation.",
        },
        {
            "printed_pages": [583, 584, 585],
            "pdf_page_indices": [596, 597, 598],
            "summary": "Conditional-plus-negative questions can request permission or cooperation. Modal 겠 belongs to right 되다 in an attested polite request. Answers distinguish permission and prohibition; contextual question polarity cannot be selected from a joined word alone.",
        },
    ],
    "disposition": "Source-context/sense/prefinal review required. Do not globally ban a lexical lemma or repair corpus annotation using these particular pedagogical contexts.",
}


def cases():
    rows = []

    def add(
        surface, heads, kinds, forms, morph_kinds, family, role, sense, required=True
    ):
        rule = ("lexical" if role == "predicate" else "auxiliary") + ".doeda.extended"
        rows.append(
            {
                "id": "doeda-complement-"
                + digest([surface, heads, kinds, forms, morph_kinds, rule])[:24],
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "morpheme_kinds": morph_kinds,
                "verdict": "required" if required else "forbidden",
                "source": MAIN if role == "predicate" else "nikl-qna-318411",
                "native_sense": sense,
                "family": family,
                "required_rules": [rule],
                "scope": "source_attributed_construction_proposal"
                if required
                else "scoped_construction_control",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )

    stems = [
        (
            "먹다",
            ["predicate"],
            ["먹도록", "먹기로", "먹어야", "먹으면", "먹어도", "먹어서는안"],
        ),
        (
            "가다",
            ["predicate"],
            ["가도록", "가기로", "가야", "가면", "가도", "가서는안"],
        ),
        (
            "살다",
            ["predicate"],
            ["살도록", "살기로", "살아야", "살면", "살아도", "살아서는안"],
        ),
        (
            "좋다",
            ["predicate"],
            ["좋도록", None, "좋아야", "좋으면", "좋아도", "좋아서는안"],
        ),
        (
            "없다",
            ["predicate"],
            ["없도록", None, "없어야", "없으면", "없어도", "없어서는안"],
        ),
        (
            "행복하다",
            ["predicate"],
            ["행복하도록", None, "행복해야", "행복하면", "행복해도", "행복해서는안"],
        ),
        (
            ["학생", "이다"],
            ["nominal", "copula"],
            [None, None, "학생이어야", "학생이면", "학생이어도", "학생이어서는안"],
        ),
    ]
    families = [
        ("scheduled-dorok", ["도록"], ["ending"], "17", False, ["predicate"]),
        (
            "scheduled-ki-ro",
            ["기", "로"],
            ["ending", "particle"],
            "17",
            False,
            ["predicate"],
        ),
        ("necessity", ["어야"], ["ending"], "18", False, ["predicate", "auxiliary"]),
        ("condition", ["으면"], ["ending"], "19", False, ["predicate", "auxiliary"]),
        ("permission", ["어도"], ["ending"], "21", False, ["predicate", "auxiliary"]),
        (
            "prohibition",
            ["어서", "는"],
            ["ending", "particle"],
            "21",
            True,
            ["predicate", "auxiliary"],
        ),
    ]
    rights = [
        ("되다", ["다"], ["ending"]),
        ("된다", ["는다"], ["ending"]),
        ("되었다", ["었", "다"], ["prefinal", "ending"]),
        ("됐다", ["었", "다"], ["prefinal", "ending"]),
        ("됩니다", ["습니다"], ["ending"]),
        ("되는", ["는"], ["ending"]),
    ]
    for head, kinds, surfaces in stems:
        heads = [head] if isinstance(head, str) else head
        for left, (family, forms, mkinds, sense, negative, roles) in zip(
            surfaces, families, strict=True
        ):
            if left is None:
                continue
            for right, final, final_kinds in rights:
                for role in roles:
                    add(
                        left + right,
                        heads + (["안"] if negative else []) + ["되다"],
                        kinds + (["adverbial"] if negative else []) + [role],
                        forms + final,
                        mkinds + final_kinds,
                        family,
                        role,
                        sense,
                    )
    for surface, head, forms, kinds, family, sense in [
        (
            "들어야된다",
            "듣다",
            ["어야", "는다"],
            ["ending", "ending"],
            "necessity",
            "18",
        ),
        (
            "도와도됩니다",
            "돕다",
            ["어도", "습니다"],
            ["ending", "ending"],
            "permission",
            "21",
        ),
        (
            "지으면된다",
            "짓다",
            ["으면", "는다"],
            ["ending", "ending"],
            "condition",
            "19",
        ),
        (
            "빨가도된다",
            "빨갛다",
            ["어도", "는다"],
            ["ending", "ending"],
            "permission",
            "21",
        ),
        (
            "몰라도된다",
            "모르다",
            ["어도", "는다"],
            ["ending", "ending"],
            "permission",
            "21",
        ),
        (
            "커도된다",
            "크다",
            ["어도", "는다"],
            ["ending", "ending"],
            "permission",
            "21",
        ),
        (
            "출발하기로되었다",
            "출발하다",
            ["기", "로", "었", "다"],
            ["ending", "particle", "prefinal", "ending"],
            "scheduled-ki-ro",
            "17",
        ),
        (
            "표시하도록되어있다",
            "표시하다",
            ["도록", "어", "다"],
            ["ending", "ending", "ending"],
            "scheduled-dorok",
            "17",
        ),
    ]:
        for role in ["predicate"] if sense == "17" else ["predicate", "auxiliary"]:
            heads = [head, "되다"] + (["있다"] if surface.endswith("있다") else [])
            lkinds = ["predicate", role] + (
                ["auxiliary"] if surface.endswith("있다") else []
            )
            add(surface, heads, lkinds, forms, kinds, family, role, sense)
    for surface, forms, kinds in [
        ("먹고되었다", ["고", "었", "다"], ["ending", "prefinal", "ending"]),
        ("먹면된다", ["으면", "는다"], ["ending", "ending"]),
        ("가으면된다", ["으면", "는다"], ["ending", "ending"]),
        ("살으면된다", ["으면", "는다"], ["ending", "ending"]),
    ]:
        for role in ["predicate", "auxiliary"]:
            head = (
                "가다"
                if surface.startswith("가")
                else "살다"
                if surface.startswith("살")
                else "먹다"
            )
            add(
                surface,
                [head, "되다"],
                ["predicate", role],
                forms,
                kinds,
                "scope-or-allomorph-control",
                role,
                "19",
                False,
            )
    assert len({r["id"] for r in rows}) == len(rows)
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
                                "id": "doeda-complement-native-"
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
                                "negative": m["negative"] or "",
                                "negative_gap": m["negative_gap"] or "",
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
                if LEFT.fullmatch(a[1]) and NEG_RIGHT.fullmatch(b[1])
            ]
            triples = [
                [a, b, c]
                for a, b, c in zip(rows, rows[1:], rows[2:])
                if LEFT.fullmatch(a[1]) and b[1] == "안" and RIGHT.fullmatch(c[1])
            ]
            if joined or pairs or triples:
                sentences.append(
                    {
                        "complete_sentence": text,
                        "joined_rows": joined,
                        "spaced_pairs": pairs,
                        "spaced_triples": triples,
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
                "id": "doeda-complement-novel-" + digest([fingerprint, m.span()])[:24],
                "surface": m[0],
                "left": m["left"],
                "gap": m["gap"],
                "negative": m["negative"] or "",
                "negative_gap": m["negative_gap"] or "",
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
    words = {c["surface"] for c in cases()} | set(PENDING_PROBES)
    for h in hits + novel["discoveries"]:
        words.update(
            [
                h["left"],
                h["right"],
                h["negative"] + h["right"],
                h["left"] + h["negative"] + h["right"],
            ]
        )
        if h["negative"]:
            words.add(h["negative"])
    for c in corpora:
        for s in c["sentences"]:
            words.update(r[1] for r in s["joined_rows"])
            for left, right in s["spaced_pairs"]:
                words.update([left[1], right[1], left[1] + right[1]])
            for left, negative, right in s["spaced_triples"]:
                words.update(
                    [
                        left[1],
                        negative[1],
                        right[1],
                        negative[1] + right[1],
                        left[1] + negative[1] + right[1],
                    ]
                )
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
        + [before_words[w] for w in PENDING_PROBES]
    )
    case_heads = {h for c in cases() for h in c["lemmas"]}
    component_ids = {i for i, e in native.items() if e["headword"] in COMPONENT_HEADS}
    case_ids |= component_ids
    case_ids |= {i for i, e in native.items() if e["headword"] in case_heads}
    case_entries = {i: native[i] for i in sorted(case_ids)}
    # Expected new heads need full provenance even when their joined before
    # word had no separate dictionary lookup slot. Do not omit those sources.
    full.update(case_entries)
    full = {i: full[i] for i in sorted(full)}
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
        "checklist": "COV-019ah",
        "implementation_status": "preflight_only",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "prior_doeda_source_sha256": sha(PRIOR),
        "prior_doeda_runtime_sha256": sha(PRIOR_RUNTIME),
        "native_scan_entries": len(native),
        "doeda_headword_ids": headword_ids,
        "pattern": PATTERN.pattern,
        "discoveries": hits,
        "corpora": corpora,
        "novel": novel,
        "primary_guidance": GUIDANCE,
        "teaching_guidance": TEACHING_GUIDANCE,
        "complete_native_entries": full,
        "case_native_ids": sorted(case_ids),
        "component_native_ids": sorted(component_ids),
        "raw_adapter_source_sha256": hashes,
        "before_input": text,
        "before_streams": streams,
        "construction_senses": {
            s["id"]: s
            for s in native[MAIN]["senses"]
            if s["id"] in {"17", "18", "19", "21"}
        },
        "negative_adverb_id": "krdict:71372",
        "pending_probes": PENDING_PROBES,
        "limits": "Literal spelling matches (including noun/particle lookalikes) are observations, not grammatical licenses or contextual gold. All native owners/readings and negative bridges are preserved. The importer is an explicit finite subset. Scheduled adjective/copula and own prefinal constraints need context evidence; no universal negative or particle license is inferred. Preserve existing role paths and compound 안되다 independently.",
        "license": read(PRIOR)["license"],
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
    assert source["schema_version"] == 1 and source["checklist"] == "COV-019ah"
    assert (
        source["implementation_status"] == "preflight_only"
        and source["pattern"] == PATTERN.pattern
    )
    assert source["primary_guidance"] == GUIDANCE and fixture["cases"] == cases()
    assert source["prior_doeda_source_sha256"] == sha(PRIOR)
    assert source["prior_doeda_runtime_sha256"] == sha(PRIOR_RUNTIME)
    assert source["teaching_guidance"] == TEACHING_GUIDANCE
    native = source["complete_native_entries"]
    assert native[MAIN]["pos"] == "동사" and native[ADJECTIVE]["pos"] == "형용사"
    assert source["construction_senses"] == {
        s["id"]: s
        for s in native[MAIN]["senses"]
        if s["id"] in {"17", "18", "19", "21"}
    }
    assert source["negative_adverb_id"] == "krdict:71372"
    assert source["pending_probes"] == PENDING_PROBES
    assert source["component_native_ids"] == sorted(
        i for i, e in native.items() if e["headword"] in COMPONENT_HEADS
    )
    assert set(source["component_native_ids"]) <= set(source["case_native_ids"])
    assert native["krdict:71372"]["pos"] == "부사"
    assert source["doeda_headword_ids"] == sorted(
        i for i, e in native.items() if e["headword"] == "되다"
    )
    assert discoveries(native) == source["discoveries"]
    assert len({h["id"] for h in source["discoveries"]}) == len(source["discoveries"])
    for h in source["discoveries"]:
        a, b = h["char_span"]
        assert (
            h["text"][a:b]
            == h["surface"]
            == h["left"] + h["gap"] + h["negative"] + h["negative_gap"] + h["right"]
        )
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
                if LEFT.fullmatch(a[1]) and NEG_RIGHT.fullmatch(b[1])
            ]
            assert s["spaced_triples"] == [
                [a, b, c]
                for a, b, c in zip(rows, rows[1:], rows[2:])
                if LEFT.fullmatch(a[1]) and b[1] == "안" and RIGHT.fullmatch(c[1])
            ]
            for row in s["joined_rows"] + [
                r for group in s["spaced_pairs"] + s["spaced_triples"] for r in group
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
        f"Verified 되다 role preflight: {len(source['discoveries'])} native observations, {len(words)} words, {len(native)} complete native owners, {len(cases())} proposed paths; attributed lexical/auxiliary roles and contextual/independent limits retained."
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
