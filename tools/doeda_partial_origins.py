"""Verify two semantic noun links without supplying absent noun origins."""

import argparse
import hashlib
import json

from continuation_inflection_audit import project_lmf
from doeda_native_preflight import expected, words
from doeda_originless_audit import REPORT as PREVIOUS
from doeda_originless_audit import cases, corpus_rows
from doeda_originless_package import REPORT as PACKAGE
from doeda_suffix_audit import SOURCE, referenced
from lexical_nada_audit import ROOT, digest, read, sha
from native_lmf import verify_native_lmf

REPORT = ROOT / "docs/doeda-partial-origin-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-partial-origin-sources.json"
LMF = ROOT / "tests/fixtures/krdict-doeda-partial-origin.json"
PROVENANCE = ROOT / "tests/fixtures/doeda-partial-origin-import.json"
LINKS = [
    (
        "대칭",
        "83732",
        "46854",
        "89865",
        "對稱",
        "The noun denotes a matching pair of identical size/shape; the whole verb denotes becoming such a pair.",
    ),
    (
        "첨삭",
        "77496",
        "77493",
        "77498",
        "添削",
        "The noun denotes editing by adding/removing content; the whole verb denotes being edited by those operations.",
    ),
]
CONTROLS = [
    {
        "head": "개비되다",
        "base": "개비",
        "whole_entries": ["krdict:23532"],
        "noun_entries": ["krdict:23528"],
        "reason": "The thin stick/counting-unit noun does not denote the replacement action in whole-head 改備되다; missing noun origins cannot license that semantic substitution.",
    },
    {
        "head": "상치되다",
        "base": "상치",
        "whole_entries": ["krdict:62991"],
        "noun_entries": ["krdict:92261"],
        "reason": "The noun redirects to lettuce, whereas 相馳되다 denotes conflicting events/intentions; absent noun origins do not supply a predicative link.",
    },
]


def formations(native, previous):
    result = []
    for base, wid, nid, hid, origin, reason in LINKS:
        ids = ["krdict:" + i for i in (wid, nid, hid)]
        whole, noun, hada = [native[i] for i in ids]
        assert (whole["headword"], noun["headword"], hada["headword"]) == (
            base + "되다",
            base,
            base + "하다",
        )
        assert (whole["pos"], noun["pos"], hada["pos"]) == ("동사", "명사", "동사")
        assert whole["origins"] == [origin + "되다"]
        assert noun["origins"] == [] and hada["origins"] == [origin + "하다"]
        prior = next(
            r
            for r in previous["original_unresolved_reviews"]
            if r["native_entry_id"] == ids[0]
        )
        assert prior["disposition"] == "unresolved-native-base"
        result.append(
            {
                "id": "doeda-partial-origin-formation-" + wid,
                "head": whole["headword"],
                "base": base,
                "base_kind": "nominal",
                "predicate_class": "verb",
                "whole_entries": [ids[0]],
                "noun_entries": [ids[1]],
                "paired_hada_entries": [ids[2]],
                "review_ids": [prior["id"]],
                "expected_origins": [origin],
                "whole_origins_complete": True,
                "origin_relation": "unknown",
                "semantic_evidence": [
                    {
                        "entry": e["id"],
                        "sense": "1",
                        "definition": e["senses"][0]["definition"],
                        "entry_sha256": digest(e),
                    }
                    for e in (noun, whole, hada)
                ],
                "reason": reason,
                "suffix_source": "krdict:74902",
                "suffix_sense": "1",
                "reviewer": "agent",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return result


def inspect(report):
    previous, source, package = read(PREVIOUS), read(SOURCE), read(PACKAGE)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["previous_source_sha256"] == sha(PREVIOUS)
    assert report["previous_package_sha256"] == sha(PACKAGE)
    assert report["cli_sha256"] == package["cli_sha256"]
    assert report["dictionary_sha256"] == previous["dictionary_sha256"]
    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    native = report["complete_native_entries"]
    for ident, entry in native.items():
        assert ident == entry["id"] and entry["senses"]
        if ident in source["complete_native_entries"]:
            assert entry == source["complete_native_entries"][ident]
    forms = formations(native, previous)
    assert report["formations"] == forms and report["controls"] == CONTROLS
    variants = read(ROOT / "tests/fixtures/doeda-originless-formations.json")[
        "variants"
    ]
    assert report["variants"] == variants
    assert report["cases"] == cases(forms, variants) and len(report["cases"]) == 20
    corpus = corpus_rows(
        {f["head"] for f in forms} | {c["head"] for c in CONTROLS}, source["corpora"]
    )
    assert report["corpus_occurrences"] == corpus == []
    surfaces = {c["surface"] for c in report["cases"]}
    surfaces |= {c["base"] + v["tail"] for c in CONTROLS for v in variants}
    surfaces |= {r["original_row"][1] for r in corpus}
    surfaces |= {c["base"] for c in [*forms, *CONTROLS]}
    assert report["before_input"] == "\n".join(sorted(surfaces)) + "\n"
    assert (
        set(report["before_streams"])
        == set(report["before_jsonl"])
        == set(report["before_jsonl_sha256"])
        == {"raw", "headword", "compatible"}
    )
    for mode, stream in report["before_streams"].items():
        encoded = report["before_jsonl"][mode]
        assert (
            hashlib.sha256(encoded.encode()).hexdigest()
            == report["before_jsonl_sha256"][mode]
        )
        assert [json.loads(line) for line in encoded.splitlines()] == stream
        assert "".join(r["surface"] for r in stream) == report["before_input"]
        assert len(stream) == 2 * len(surfaces) == 88
    raw = words(report["before_streams"]["raw"])
    for case in report["cases"]:
        assert not any(expected(a, case) for a in raw[case["surface"]]["analyses"])
        assert any(
            a["lemmas"] == case["original_whole_lemmas"]
            and a["morphemes"] == case["morphemes"][1:]
            for a in raw[case["surface"]]["analyses"]
        )
    ids = referenced(report["before_streams"]) | {"krdict:74902"}
    ids |= {
        i
        for f in forms
        for k in ("whole_entries", "noun_entries", "paired_hada_entries")
        for i in f[k]
    }
    ids |= {
        i for c in CONTROLS for k in ("whole_entries", "noun_entries") for i in c[k]
    }
    assert set(native) == ids and len(ids) == 15
    return len(forms), len(report["cases"]), len(surfaces)


def fixture(report):
    controls = []
    for control in report["controls"]:
        for variant in report["variants"]:
            controls.append(
                {
                    "id": "doeda-partial-origin-control-"
                    + control["whole_entries"][0].split(":")[1]
                    + "-"
                    + variant["id"],
                    "surface": control["base"] + variant["tail"],
                    "base": control["base"],
                    "forbidden_rule": "suffix.verb.doeda",
                    "forbidden_base_kind": "nominal",
                    "reason": control["reason"],
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    return {
        "schema_version": 1,
        "checklist": "COV-022m",
        "preflight_sha256": sha(REPORT),
        "formations": report["formations"],
        "cases": report["cases"],
        "controls": controls,
        "before_words": words(report["before_streams"]["raw"]),
        "corpus_occurrences": report["corpus_occurrences"],
    }


def generate():
    report = read(REPORT)
    inspect(report)
    assert not any(p.exists() for p in (FIXTURE, LMF, PROVENANCE))
    FIXTURE.write_text(json.dumps(fixture(report), ensure_ascii=False, indent=2) + "\n")
    native = report["complete_native_entries"]
    projected, hashes = project_lmf(native)
    lmf = {"LexicalResource": {"Lexicon": {"LexicalEntry": list(projected.values())}}}
    verify_native_lmf(lmf, native)
    LMF.write_text(json.dumps(lmf, ensure_ascii=False, separators=(",", ":")) + "\n")
    PROVENANCE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "preflight_sha256": sha(REPORT),
                "fixture_sha256": sha(FIXTURE),
                "lmf_sha256": sha(LMF),
                "source_files_sha256": hashes,
                "native_entries": len(native),
                "projection": "Complete native entries with English translations; all languages preserved in source checkpoint. NIKL Korean Basic Dictionary CC BY-SA 2.0 KR.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    verify()


def verify():
    report = read(REPORT)
    counts = inspect(report)
    assert read(FIXTURE) == fixture(report)
    provenance = read(PROVENANCE)
    assert provenance["schema_version"] == 1
    for key, path in (
        ("preflight_sha256", REPORT),
        ("fixture_sha256", FIXTURE),
        ("lmf_sha256", LMF),
    ):
        assert provenance[key] == sha(path)
    assert provenance["native_entries"] == len(report["complete_native_entries"])
    verify_native_lmf(read(LMF), report["complete_native_entries"])
    for path, digest_value in provenance["source_files_sha256"].items():
        if (ROOT / path).exists():
            assert sha(ROOT / path) == digest_value
    print("Verified supplemental noun links, stable cases and original words:", counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate", action="store_true")
    group.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    generate() if args.generate else verify()
