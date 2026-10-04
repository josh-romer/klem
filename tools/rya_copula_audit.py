"""Freeze omitted-copula Rya hypotheses before implementation; verify offline.

General vowel-final copula omission and the Rya copula license are separate
sources. Their composition is a hypothesis, not a reviewed modern/register
judgment. Native examples and novel contexts remain immutable observations.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, load_dictionary, read, sha, write
from lexical_nada_fixtures import projection
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/rya-copula-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/rya-copula-regressions.json"
LMF = ROOT / "tests/fixtures/krdict-rya-copula.json"
PRIOR = ROOT / "docs/rya-boundary-source-preflight.json.gz"
OBSERVATIONS = ROOT / "docs/rya-boundary-observations.json.gz"
ADDITIONAL = ROOT / "tests/fixtures/rya-copula-additional-native.json"
ADDITIONAL_LMF = ROOT / "tests/fixtures/krdict-rya-copula-additional.json"
NOVEL = ROOT / "data/books/mujeong.txt"
PATTERN = r"(?<![가-힣])([가-힣]+랴(?:마는|만)?)(?![가-힣])"
GUIDANCE = "https://www.korean.go.kr/common/download.do?c_file_name=5c43a081-403a-47bf-ba5e-3430389c39a4_0.pdf&file_path=etcData&o_file_name=%EA%B5%AD%EB%A6%BD%EA%B5%AD%EC%96%B4%EC%9B%90_%EA%B0%80%EB%82%98%EB%8B%A4%EC%A0%84%ED%99%94%EC%97%90%EB%AC%BC%EC%96%B4%EB%B3%B4%EC%95%98%EC%96%B4%EC%9A%94.pdf"


def cases():
    result = []
    for head in ["지위", "의사", "학교", "나", "거"]:
        for ending, forms in [
            ("랴", ["으랴"]),
            ("랴마는", ["으랴", "마는"]),
            ("랴만", ["으랴", "만"]),
        ]:
            result.append(
                {
                    "id": "rya-copula-hypothesis-" + head + ending,
                    "surface": head + ending,
                    "lemmas": [head, "이다"],
                    "lemma_kinds": ["nominal", "copula"],
                    "morphemes": forms,
                    "verdict": "required_hypothesis",
                    "copula_status": "unknown",
                }
            )
    for surface, heads, kinds, forms in [
        ("지위이랴", ["지위", "이다"], ["nominal", "copula"], ["으랴"]),
        ("학생이랴마는", ["학생", "이다"], ["nominal", "copula"], ["으랴", "마는"]),
        ("먹기랴", ["먹다", "이다"], ["predicate", "copula"], ["기", "으랴"]),
        (
            "먹어보기랴만",
            ["먹다", "보다", "이다"],
            ["predicate", "auxiliary", "copula"],
            ["어", "기", "으랴", "만"],
        ),
        ("먹었기랴", ["먹다", "이다"], ["predicate", "copula"], ["었", "기", "으랴"]),
        ("나랴", ["나다"], ["predicate"], ["으랴"]),
        ("하랴", ["하다"], ["predicate"], ["으랴"]),
        ("들으랴", ["듣다"], ["predicate"], ["으랴"]),
    ]:
        omitted = len(heads) > 1 and "이랴" not in surface
        result.append(
            {
                "id": "rya-copula-composition-" + surface,
                "surface": surface,
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
                "verdict": "required_hypothesis" if omitted else "required_preserved",
                "copula_status": "unknown" if omitted else None,
            }
        )
    for surface, nominal in [
        ("학생랴", "학생"),
        ("물랴", "물"),
        ("몫랴마는", "몫"),
        ("지위으랴", "지위"),
        ("살랴", "살"),
        ("먹음랴", "먹음"),
        ("지위랴요", "지위"),
    ]:
        result.append(
            {
                "id": "rya-copula-boundary-" + surface,
                "surface": surface,
                "lemmas": [nominal, "이다"],
                "lemma_kinds": ["nominal", "copula"],
                "morphemes": ["으랴"]
                + (
                    ["마는"]
                    if surface.endswith("마는")
                    else ["요"]
                    if surface.endswith("요")
                    else []
                ),
                "verdict": "forbidden",
            }
        )
    return result


def novel_discoveries(text):
    return [
        {
            "id": f"rya-copula-novel-{m.start(1)}-{m.end(1)}",
            "surface": m[1],
            "span": {
                "start": len(text[: m.start(1)].encode()),
                "end": len(text[: m.end(1)].encode()),
            },
            "context": text[max(0, m.start(1) - 80) : m.end(1) + 80],
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        for m in re.finditer(PATTERN, text)
    ]


def freeze(cli, dictionary):
    assert not any(p.exists() for p in [SOURCE, FIXTURE, LMF])
    prior = read(PRIOR)
    entries = load_dictionary(dictionary)
    text = NOVEL.read_text()
    hits = novel_discoveries(text)
    words = sorted(
        {r["surface"] for r in prior["before_streams"]["all"] if r["kind"] == "word"}
        | {c["surface"] for c in cases()}
        | {h["surface"] for h in hits}
    )
    original = " ".join(words)
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
                    input=original.encode(),
                ).splitlines(),
            )
        )
        for mode, flags in [
            ("all", []),
            ("headword", ["--dict-only"]),
            ("compatible", ["--dict-compatible"]),
        ]
    }
    required = set(prior["complete_native_entries"])
    heads = {h for c in cases() for h in c["lemmas"]}
    required.update(e["id"] for e in entries.values() if e["headword"] in heads)
    for r in streams["all"]:
        if r["kind"] == "word":
            required.update(
                e["id"] for s in r["dictionary"]["lemmas"] for e in s["entries"]
            )
    native = {i: entries[i] for i in sorted(required)}
    raw, hashes = project_lmf(native)
    lmf = {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}}
    LMF.write_text(json.dumps(lmf, ensure_ascii=False, indent=2) + "\n")
    write(
        SOURCE,
        {
            "schema_version": 1,
            "checklist": "COV-017br",
            "before_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "cli_sha256": sha(cli),
            "dictionary_sha256": sha(dictionary),
            "prior_source_sha256": sha(PRIOR),
            "prior_observations_sha256": sha(OBSERVATIONS),
            "complete_native_entries": native,
            "native_discoveries": prior["discoveries"],
            "novel": {
                "path": str(NOVEL.relative_to(ROOT)),
                "sha256": sha(NOVEL),
                "pattern": PATTERN,
                "discoveries": hits,
            },
            "before_input": original,
            "before_streams": streams,
            "guidance": {
                "url": GUIDANCE,
                "title": "국립국어원 가나다전화에 물어보았어요",
                "printed_page": 40,
                "pdf_page_index": 39,
                "finding": "Vowel-final nominal copula omission is documented generally, with formal-ending examples; it is not a Rya-specific or historical-register judgment.",
            },
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
            "license": prior["license"],
        },
    )
    value = {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "lmf_sha256": sha(LMF),
        "raw_source_sha256": hashes,
        "cases": cases(),
        "source_entries": projection(native),
        "before_words": {
            r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
            for r in streams["all"]
            if r["kind"] == "word"
        },
    }
    FIXTURE.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def verify(dictionary=None):
    source, fixture, prior = read(SOURCE), read(FIXTURE), read(PRIOR)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert fixture["cases"] == cases()
    assert source["prior_source_sha256"] == sha(PRIOR) and source[
        "prior_observations_sha256"
    ] == sha(OBSERVATIONS)
    assert source["native_discoveries"] == prior["discoveries"]
    assert all(
        source["complete_native_entries"][i] == e
        for i, e in prior["complete_native_entries"].items()
    )
    assert fixture["source_entries"] == projection(source["complete_native_entries"])
    assert fixture["before_words"] == {
        r["surface"]: dict(r["analysis"], dictionary=r["dictionary"])
        for r in source["before_streams"]["all"]
        if r["kind"] == "word"
    }
    verify_native_lmf(read(LMF), source["complete_native_entries"])
    if ADDITIONAL.exists():
        additional = read(ADDITIONAL)
        assert additional["source_sha256"] == sha(SOURCE)
        assert additional["lmf_sha256"] == sha(ADDITIONAL_LMF)
        assert not (
            additional["complete_native_entries"].keys()
            & source["complete_native_entries"].keys()
        )
        assert additional["source_entries"] == projection(
            additional["complete_native_entries"]
        )
        verify_native_lmf(read(ADDITIONAL_LMF), additional["complete_native_entries"])
    for row in source["novel"]["discoveries"]:
        assert row["surface"] in fixture["before_words"]
        assert (
            row["contextual_verdict"] == "unjudged"
            and row["independent_review"] == "pending"
        )
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        entries = load_dictionary(dictionary)
        assert all(
            entries[i] == e for i, e in source["complete_native_entries"].items()
        )
        if ADDITIONAL.exists():
            assert all(
                entries[i] == e
                for i, e in read(ADDITIONAL)["complete_native_entries"].items()
            )
        assert sha(NOVEL) == source["novel"]["sha256"]
        assert novel_discoveries(NOVEL.read_text()) == source["novel"]["discoveries"]
    print(
        f"{len(fixture['cases'])} cases, {len(fixture['before_words'])} original words, {len(source['complete_native_entries'])} native owners and {len(source['novel']['discoveries'])} novel occurrences verified"
    )


def freeze_additional(observations, dictionary):
    assert not ADDITIONAL.exists() and not ADDITIONAL_LMF.exists()
    report, source = read(observations), read(SOURCE)
    assert (
        report["source_sha256"] == sha(SOURCE)
        and sha(dictionary) == source["dictionary_sha256"]
    )
    entries = load_dictionary(dictionary)
    selected = {
        i: e
        for i, e in report["complete_native_entries"].items()
        if i not in source["complete_native_entries"]
    }
    assert selected and all(entries[i] == e for i, e in selected.items())
    raw, hashes = project_lmf(selected)
    ADDITIONAL_LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    ADDITIONAL.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(ADDITIONAL_LMF),
                "raw_source_sha256": hashes,
                "complete_native_entries": selected,
                "source_entries": projection(selected),
                "scope": "Additional complete native owners exposed by candidate hypotheses; source identity does not certify contextual attachment.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--dictionary", type=Path)
    p.add_argument("--additional-observations", type=Path)
    a = p.parse_args()
    if a.additional_observations:
        assert a.dictionary
        freeze_additional(a.additional_observations, a.dictionary.resolve())
    elif not a.verify:
        assert a.cli and a.dictionary
        freeze(a.cli.resolve(), a.dictionary.resolve())
    verify(a.dictionary)
