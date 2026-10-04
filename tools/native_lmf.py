"""Validate committed English LMF adapters against preserved native entries.

This check needs no local dictionary export. The frozen LMF hash also preserves
export fields outside the importer model (example types and sense relations).
Original full-export hashes remain provenance, rather than an offline replay.
Rust integration tests separately verify the production importer's projection.
"""

import copy
import hashlib
import re


def array(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def decode(text):
    def entity(match):
        name = match[1]
        known = {
            "amp": "&",
            "lt": "<",
            "gt": ">",
            "quot": '"',
            "apos": "'",
            "nbsp": "\xa0",
        }
        if name in known:
            return known[name]
        try:
            number = (
                int(name[2:], 16)  # noqa: FURB166 - XML uses #x, not Python's 0x.
                if name.startswith("#x")
                else int(name[1:])
                if name.startswith("#")
                else -1
            )
            if 0 <= number <= 0x10FFFF and not 0xD800 <= number <= 0xDFFF:
                return chr(number)
        except ValueError:
            pass
        return match[0]

    return re.sub(r"&([^&;]{1,11});", entity, text)


def features(raw, name):
    return [
        decode(f["val"])
        for f in array(raw.get("feat"))
        if f["att"] == name and isinstance(f.get("val"), str)
    ]


def feature(raw, name):
    return next(iter(features(raw, name)), "")


def entry(raw):
    source_id = raw["val"]
    assert raw["att"] == "id" and source_id.isascii() and source_id.isdecimal()
    heads = [h for lemma in array(raw["Lemma"]) for h in features(lemma, "writtenForm")]
    assert len(heads) == 1
    unit = feature(raw, "lexicalUnit")
    ident = "krdict:" + source_id
    if unit in {"관용구", "속담"}:
        ident += ":" + hashlib.sha256((unit + "\0" + heads[0]).encode()).hexdigest()
    senses = []
    for sense in array(raw.get("Sense")):
        assert sense["att"] == "id"
        senses.append(
            {
                "id": sense["val"],
                "definition": feature(sense, "definition"),
                "translations": [
                    {k: feature(t, k) for k in ("language", "lemma", "definition")}
                    for t in array(sense.get("Equivalent"))
                ],
                "examples": [
                    features(g, "example") for g in array(sense.get("SenseExample"))
                ],
                "notes": features(sense, "annotation")
                + features(sense, "syntacticAnnotation"),
                "patterns": features(sense, "syntacticPattern"),
            }
        )
    assert senses and len(senses) == len({s["id"] for s in senses})
    return {
        "id": ident,
        "headword": heads[0],
        "homonym": feature(raw, "homonym_number"),
        "pos": feature(raw, "partOfSpeech"),
        "url": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo="
        + source_id,
        "level": feature(raw, "vocabularyLevel"),
        "lexical_unit": unit,
        "origins": features(raw, "origin"),
        "notes": features(raw, "annotation"),
        "forms": [
            {
                "kind": feature(f, "type"),
                "written": feature(f, "writtenForm"),
                "pronunciations": features(f, "pronunciation"),
            }
            for f in array(raw.get("WordForm"))
        ],
        "senses": senses,
    }


def verify_native_lmf(lmf, native):
    projected = {}
    for raw in array(lmf["LexicalResource"]["Lexicon"]["LexicalEntry"]):
        value = entry(raw)
        assert value["id"] not in projected, value["id"]
        projected[value["id"]] = value
    expected = copy.deepcopy(native)
    for value in expected.values():
        for sense in value["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    assert projected.keys() == expected.keys(), projected.keys() ^ expected.keys()
    for ident in expected:
        assert projected[ident] == expected[ident], ident
