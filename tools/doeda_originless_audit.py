"""Review native noun formations without inventing missing origin evidence.

Keep the original eighty unresolved reviews, full definitions, annotated rows
and actual packaged before streams. Semantic links below are finite agent
judgments; they neither choose contextual senses nor certify independent review.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_identity_package import REPORT as PACKAGE
from doeda_native_audit import FIXTURE as NATIVE_FIXTURE
from doeda_native_audit import REPORT as REVIEW
from doeda_native_preflight import expected, words
from doeda_suffix_audit import SOURCE, referenced
from doeda_suffix_diagnostics import components_for, validate_components
from lexical_nada_audit import ROOT, digest, load_dictionary, read, sha, write

REPORT = ROOT / "docs/doeda-originless-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/doeda-originless-formations.json"

# Whole ID, noun ID, supporting noun sense, whole sense, semantic review.
# The full definitions and all other senses stay in the source checkpoint.
LINKS = [
    (
        "28114",
        "28105",
        "1",
        "1",
        "Checking a target or standard becomes being checked.",
    ),
    (
        "14723",
        "14720",
        "1",
        "1",
        "Organizing and storing becomes being organized and stored.",
    ),
    (
        "15866",
        "17232",
        "1",
        "1",
        "The noun denotes fear/anxiety; the verb denotes that feeling arising.",
    ),
    (
        "89567",
        "32191",
        "1",
        "1",
        "The noun denotes fearful anxiety; the verb denotes becoming anxious.",
    ),
    (
        "14935",
        "48236",
        "1",
        "1",
        "Repeating words or events becomes their being repeated.",
    ),
    (
        "67392",
        "67391",
        "1",
        "1",
        "Supporting and helping becomes being supported and helped.",
    ),
    (
        "58007",
        "58006",
        "1",
        "1",
        "The noun's mixed, indistinguishable state corresponds to the registered verbal state; no paired hada entry is inferred.",
    ),
    (
        "90948",
        "54149",
        "1",
        "1",
        "Explaining difficult meanings becomes their being explained.",
    ),
    ("51505", "51504", "1", "1", "Finishing an activity becomes the activity ending."),
    ("53972", "15701", "1", "1", "Bringing work to an end becomes the work ending."),
    (
        "56783",
        "56782",
        "2",
        "1",
        "The figurative supporting foundation corresponds to becoming the foundation of an activity.",
    ),
    (
        "59625",
        "59311",
        "1",
        "1",
        "Helping someone's movement becomes receiving that help.",
    ),
    (
        "63897",
        "15606",
        "1",
        "1",
        "Handling and refining something becomes its being refined.",
    ),
    (
        "67259",
        "74194",
        "1",
        "1",
        "The noun's account of facts/experience corresponds to being put into an account.",
    ),
    (
        "74011",
        "60321",
        "1",
        "1",
        "The noun's spoken/written account corresponds to being put into an account.",
    ),
    (
        "83643",
        "83642",
        "1",
        "1",
        "Explaining difficult material becomes its being explained.",
    ),
    (
        "89929",
        "88447",
        "1",
        "1",
        "Buying and selling goods becomes the goods being traded.",
    ),
]
CONTROLS = {
    "그릇되다": "The vessel/capacity noun is not the wrongness base of this whole verb.",
    "안되다": "Negative adverb 안 must not be replaced by the interior/proposal nouns; the existing adjective suffix role remains separate.",
    "혼자되다": "Being left alone after a spouse's death does not establish a passive predicative-noun suffix formation.",
    "이리되다": "Thus becoming concerns adverb 이리, not the wolf noun.",
    "저리되다": "Thus becoming concerns adverb 저리, not the low-interest noun.",
}


def proposals(source, review):
    native = source["complete_native_entries"]
    original = {r["native_entry_id"]: r for r in review["native_reviews"]}
    result = []
    for whole_id, noun_id, noun_sense, whole_sense, reason in LINKS:
        wid, nid = "krdict:" + whole_id, "krdict:" + noun_id
        whole, noun, prior = native[wid], native[nid], original[wid]
        assert prior["disposition"] == "unresolved-native-base"
        assert whole["pos"] == "동사" and noun["pos"] == "명사"
        assert whole["headword"] == noun["headword"] + "되다"
        assert not whole["origins"] and not noun["origins"]
        evidence = []
        for entry, sense_id in ((noun, noun_sense), (whole, whole_sense)):
            sense = next(s for s in entry["senses"] if s["id"] == sense_id)
            evidence.append(
                {
                    "entry": entry["id"],
                    "sense": sense_id,
                    "definition": sense["definition"],
                    "entry_sha256": digest(entry),
                }
            )
        result.append(
            {
                "id": "doeda-originless-formation-" + whole_id,
                "head": whole["headword"],
                "base": noun["headword"],
                "base_kind": "nominal",
                "predicate_class": "verb",
                "whole_entries": [wid],
                "noun_entries": [nid],
                "review_ids": [prior["id"]],
                "semantic_evidence": evidence,
                "reason": reason,
                "suffix_source": "krdict:74902",
                "suffix_sense": "1",
                "origin_relation": "unknown",
                "reviewer": "agent",
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            }
        )
    return sorted(result, key=lambda f: f["head"])


def cases(formations, variants):
    result = []
    for f in formations:
        for v in variants:
            result.append(
                {
                    "id": f["id"] + "-" + v["id"],
                    "formation_id": f["id"],
                    "surface": f["base"] + v["tail"],
                    "lemmas": [
                        {"text": f["base"], "kind": "nominal"},
                        *v.get("later_lemmas", []),
                    ],
                    "morphemes": [
                        {"form": "되다", "kind": "suffix"},
                        *[
                            {"form": m, "kind": k}
                            for m, k in zip(
                                v["morphemes"], v["morpheme_kinds"], strict=True
                            )
                        ],
                    ],
                    "required_rule": "suffix.verb.doeda",
                    "original_whole_lemmas": [
                        {"text": f["head"], "kind": "predicate"},
                        *v.get("later_lemmas", []),
                    ],
                    "source_reviews": f["review_ids"],
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
            )
    return result


def corpus_rows(heads, archived=None):
    rows = []
    inputs = (
        [
            (c["source"], c["sha256"], [s["complete_sentence"] for s in c["sentences"]])
            for c in archived
        ]
        if archived is not None
        else [
            (str(p.relative_to(ROOT)), sha(p), p.read_text().strip().split("\n\n"))
            for p in sorted((ROOT / "data/corpora").glob("*/*.conllu"))
        ]
    )
    for source, source_sha256, sentences in inputs:
        for sentence in sentences:
            sent_id = next(
                (
                    s.removeprefix("# sent_id = ")
                    for s in sentence.splitlines()
                    if s.startswith("# sent_id = ")
                ),
                "",
            )
            for line in sentence.splitlines():
                fields = line.split("\t")
                if len(fields) != 10 or not fields[0].isdigit():
                    continue
                original = next(
                    (
                        s.removeprefix("OrigLemma=")
                        for s in fields[9].split("|")
                        if s.startswith("OrigLemma=")
                    ),
                    fields[2],
                )
                parts, tags = original.split("+"), fields[4].lower().split("+")
                if (
                    len(parts) != len(tags)
                    or len(parts) < 2
                    or parts[1] != "되"
                    or tags[1] != "xsv"
                ):
                    continue
                head = parts[0] + "되다"
                if head not in heads:
                    continue
                rows.append(
                    {
                        "id": "doeda-originless-token-"
                        + digest([source, sent_id, fields[0]])[:24],
                        "source": source,
                        "source_sha256": source_sha256,
                        "sent_id": sent_id,
                        "head": head,
                        "original_row": fields,
                        "lemma_parts": parts,
                        "xpos_parts": tags,
                        "complete_sentence": sentence,
                        "scope": "Original morphological evidence; whole-predicate evaluation gold remains unchanged.",
                    }
                )
    return rows


def inspect(report, fixture):
    source, review = read(SOURCE), read(REVIEW)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["source_sha256"] == sha(SOURCE) and report["review_sha256"] == sha(
        REVIEW
    )
    assert report["previous_package_sha256"] == sha(PACKAGE)
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["dictionary_sha256"] == source["dictionary_sha256"]
    forms = proposals(source, review)
    assert fixture["formations"] == forms and len(forms) == 17
    assert fixture["variants"] == read(NATIVE_FIXTURE)["variants"]
    assert fixture["controls"] == [
        {
            "head": h,
            "base": h[:-2],
            "reason": r,
            "forbidden_base_kind": "nominal",
            "forbidden_rule": "suffix.verb.doeda",
        }
        for h, r in sorted(CONTROLS.items())
    ]
    original = [
        r
        for r in review["native_reviews"]
        if r["disposition"] == "unresolved-native-base"
    ]
    assert report["original_unresolved_reviews"] == original and len(original) == 80
    assert report["cases"] == cases(forms, fixture["variants"])
    assert report["fixture_sha256"] == sha(FIXTURE)
    native = report["complete_native_entries"]
    required = {"krdict:74902"}
    for r in original:
        required.add(r["native_entry_id"])
        required.update(b["id"] for b in r["base_entry_reviews"])
    required |= referenced(report["before_streams"])
    required |= {i for ids in report["paired_hada_entries"].values() for i in ids}
    assert set(native) == required
    for i, entry in native.items():
        assert i == entry["id"] and entry["senses"]
        if i in source["complete_native_entries"]:
            assert entry == source["complete_native_entries"][i]
    for f in forms:
        for i in report["paired_hada_entries"][f["head"]]:
            assert (
                native[i]["headword"] == f["base"] + "하다"
                and native[i]["pos"] == "동사"
            )
    assert set(report["paired_hada_entries"]) == {f["head"] for f in forms}
    assert report["paired_hada_entries"]["뒤범벅되다"] == []
    for row in report["corpus_occurrences"]:
        assert "\t".join(row["original_row"]) in row["complete_sentence"].splitlines()
        assert row["head"] in {f["head"] for f in forms} | set(CONTROLS)
        assert len(row["lemma_parts"]) == len(row["xpos_parts"])
        path = ROOT / row["source"]
        if path.exists():
            assert sha(path) == row["source_sha256"]
    heads = {f["head"] for f in forms} | set(CONTROLS)
    assert report["corpus_occurrences"] == corpus_rows(heads, source["corpora"])
    assert len(report["corpus_occurrences"]) == 52
    if (ROOT / "data/corpora/kaist/ko_kaist-ud-test.conllu").exists():
        assert report["corpus_occurrences"] == corpus_rows(heads)
    surfaces = {c["surface"] for c in report["cases"]}
    surfaces |= {
        c["base"] + v["tail"] for c in fixture["controls"] for v in fixture["variants"]
    }
    surfaces |= {r["original_row"][1] for r in report["corpus_occurrences"]}
    text = "\n".join(sorted(surfaces)) + "\n"
    assert (
        report["before_input"] == text
        and report["before_input_sha256"] == hashlib.sha256(text.encode()).hexdigest()
    )
    assert set(report["before_streams"]) == {"raw", "headword", "compatible"}
    for mode, stream in report["before_streams"].items():
        assert len(stream) == 2 * len(surfaces)
        assert "".join(r["surface"] for r in stream) == text
        encoded = report["before_jsonl"][mode]
        assert [json.loads(s) for s in encoded.splitlines()] == stream
        assert (
            report["before_jsonl_sha256"][mode]
            == hashlib.sha256(encoded.encode()).hexdigest()
        )
        mapping = words(stream)
        for c in report["cases"]:
            assert not any(expected(a, c) for a in mapping[c["surface"]]["analyses"])
    raw = words(report["before_streams"]["raw"])
    for c in report["cases"]:
        assert any(
            a["lemmas"] == c["original_whole_lemmas"]
            and a["morphemes"] == c["morphemes"][1:]
            for a in raw[c["surface"]]["analyses"]
        ), c["id"]
    validate_components(report["original_parent_components"], list(raw.values()))
    return len(report["cases"]), len(report["corpus_occurrences"]), len(native)


def freeze(args):
    assert not REPORT.exists() and not FIXTURE.exists()
    source, review, package = read(SOURCE), read(REVIEW), read(PACKAGE)
    assert (
        sha(args.cli) == package["cli_sha256"]
        and sha(args.dictionary) == source["dictionary_sha256"]
    )
    native = load_dictionary(args.dictionary)
    forms = proposals(source, review)
    fixture = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "formations": forms,
        "variants": read(NATIVE_FIXTURE)["variants"],
        "controls": [
            {
                "head": h,
                "base": h[:-2],
                "reason": r,
                "forbidden_base_kind": "nominal",
                "forbidden_rule": "suffix.verb.doeda",
            }
            for h, r in sorted(CONTROLS.items())
        ],
    }
    proposed = cases(forms, fixture["variants"])
    corpus = corpus_rows({f["head"] for f in forms} | set(CONTROLS))
    surfaces = (
        {c["surface"] for c in proposed}
        | {
            c["base"] + v["tail"]
            for c in fixture["controls"]
            for v in fixture["variants"]
        }
        | {r["original_row"][1] for r in corpus}
    )
    text = "\n".join(sorted(surfaces)) + "\n"
    streams, encoded = {}, {}
    for mode, flags in (
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ):
        out = subprocess.run(
            [str(args.cli), "text", "-", "--dictionary", str(args.dictionary), *flags],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        encoded[mode] = out.stdout
        streams[mode] = [json.loads(line) for line in out.stdout.splitlines()]
    original = [
        r
        for r in review["native_reviews"]
        if r["disposition"] == "unresolved-native-base"
    ]
    paired = {
        f["head"]: sorted(
            e["id"]
            for e in native.values()
            if e["headword"] == f["base"] + "하다" and e["pos"] == "동사"
        )
        for f in forms
    }
    ids = (
        {"krdict:74902"}
        | referenced(streams)
        | {i for values in paired.values() for i in values}
    )
    for r in original:
        ids.add(r["native_entry_id"])
        ids.update(b["id"] for b in r["base_entry_reviews"])
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    report = {
        "schema_version": 1,
        "checklist": "COV-022m",
        "source_sha256": sha(SOURCE),
        "review_sha256": sha(REVIEW),
        "previous_package_sha256": sha(PACKAGE),
        "fixture_sha256": sha(FIXTURE),
        "cli_sha256": sha(args.cli),
        "dictionary_sha256": sha(args.dictionary),
        "original_unresolved_reviews": original,
        "paired_hada_entries": paired,
        "corpus_occurrences": corpus,
        "complete_native_entries": {i: native[i] for i in sorted(ids)},
        "cases": proposed,
        "before_input": text,
        "before_input_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "before_streams": streams,
        "before_jsonl": encoded,
        "before_jsonl_sha256": {
            m: hashlib.sha256(s.encode()).hexdigest() for m, s in encoded.items()
        },
        "original_parent_components": components_for(
            list(words(streams["raw"]).values()), args.bridge
        ),
        "scope": "Seventeen finite noun/verb semantic links under suffix 74902 sense 1. All eighty original unresolved reviews retained; other formations and base roles remain open. No origin values or contextual/independent verdicts inferred.",
    }
    inspect(report, fixture)
    write(REPORT, report)
    print("Frozen", inspect(report, fixture))


def verify():
    print(
        "Verified originless cases, original corpus tokens, native owners:",
        inspect(read(REPORT), read(FIXTURE)),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    for name in ("cli", "dictionary", "bridge"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.cli and args.dictionary and args.bridge
        freeze(args)
