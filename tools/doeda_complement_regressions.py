"""Append attributed 되다 paths with explicit corrections to frozen proposals."""

import argparse
import copy
import json
from collections import Counter

from doeda_complement_audit import FIXTURE, NIKL, ROOT
from lexical_nada_audit import read, sha

CORRECTIONS = ROOT / "tests/fixtures/doeda-complement-corrections.json"
BOUNDARIES = ROOT / "tests/fixtures/doeda-complement-bridge-boundaries.json"
RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
SOURCES = {
    "doeda-complement-krdict": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89858",
    "doeda-complement-nikl": NIKL,
    "doeda-complement-negative-adverb": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=71372",
}


def effective_cases():
    original = read(FIXTURE)
    amendments = read(CORRECTIONS)
    assert amendments["source_fixture_sha256"] == sha(FIXTURE)
    assert len(amendments["corrections"]) == 2
    cases = copy.deepcopy(original["cases"])
    for correction in amendments["corrections"]:
        old = correction["original"]
        assert old["surface"] == "빨가도된다" and old["lemmas"] == ["빨갛다", "되다"]
        index = cases.index(old)
        control = correction["replacement_control"]
        positive = correction["replacement_positive"]
        assert control == dict(
            old,
            id=old["id"] + "-corrected-control",
            verdict="forbidden",
            family="hieut-vowel-control",
            scope="scoped_construction_control",
        )
        assert positive == dict(
            old, id=old["id"] + "-corrected-vowel", surface="빨개도된다"
        )
        cases[index] = control
        cases.append(positive)
    native = next(e for e in original["source_entries"] if e["id"] == "krdict:71070")
    assert any(form["written"] == "빨개" for form in native["forms"])
    assert Counter(c["verdict"] for c in cases) == {"required": 404, "forbidden": 10}
    cases.extend(read(BOUNDARIES)["cases"])
    assert Counter(c["verdict"] for c in cases) == {"required": 404, "forbidden": 11}
    return cases


def records(policy=False):
    rows = []
    for case in effective_cases():
        auxiliary = any(
            kind == "auxiliary" and head == "되다"
            for kind, head in zip(case["lemma_kinds"], case["lemmas"], strict=True)
        )
        ident = case["id"] + ("-policy" if policy else "")
        judgment = {
            k: case[k]
            for k in (
                "lemmas",
                "lemma_kinds",
                "morphemes",
                "morpheme_kinds",
                "required_rules",
                "verdict",
            )
        }
        if policy and auxiliary:
            judgment["verdict"] = "forbidden"
        judgment.update(
            id=ident + "-path",
            source="doeda-complement-negative-adverb"
            if case["source"] == "krdict:71372"
            else "doeda-complement-nikl"
            if auxiliary
            else "doeda-complement-krdict",
            reason=(
                "Native KRDict classifies these 되다 senses as lexical verbs. Its role conflict with the separately attributed NIKL auxiliary representation remains explicit; this policy exclusion is not a grammatical ban."
                if policy and auxiliary
                else "Source-listed complement with independent predicate, particle and negative-adverb owners. Preserve all original candidates and native POS. Contextual sense/register and independent review remain pending."
                if case["verdict"] == "required"
                else "Scoped connector/allomorph control on this exact attributed path; unrelated lexical hypotheses and sentence contexts remain unjudged."
            ),
        )
        rows.append({"id": ident, "surface": case["surface"], "judgments": [judgment]})
    return rows


def append(path, policy):
    original = path.read_text()
    suite = json.loads(original)
    rows = records(policy)
    assert not {r["id"] for r in rows} & {r["id"] for r in suite["cases"]}
    assert not set(SOURCES) & set(suite["sources"])
    start = original.index('"sources": {') + len('"sources": {')
    additions = "".join(
        "\n    " + json.dumps(key) + ": " + json.dumps(url) + ","
        for key, url in SOURCES.items()
    )
    updated = original[:start] + additions + original[start:]
    end = updated.rindex("\n  ]")
    updated = (
        updated[:end]
        + ",\n"
        + ",\n".join(
            "    "
            + json.dumps(row, ensure_ascii=False, indent=2).replace("\n", "\n    ")
            for row in rows
        )
        + updated[end:]
    )
    assert json.loads(updated) == dict(
        suite, sources=suite["sources"] | SOURCES, cases=suite["cases"] + rows
    )
    path.write_text(updated)


def verify():
    for path, policy in ((RAW, False), (POLICY, True)):
        suite = read(path)
        expected = records(policy)
        ids = {row["id"] for row in expected}
        assert [row for row in suite["cases"] if row["id"] in ids] == expected
        assert all(suite["sources"][key] == url for key, url in SOURCES.items())
        print(
            path.name, dict(Counter(row["judgments"][0]["verdict"] for row in expected))
        )
    print(
        "Verified explicit proposal corrections and attributed 되다 raw/policy judgments; original source freeze retained."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify:
        for path, policy in ((RAW, False), (POLICY, True)):
            ids = {row["id"] for row in records(policy)}
            existing = {row["id"] for row in read(path)["cases"]}
            if ids & existing:
                assert ids <= existing
            else:
                append(path, policy)
    verify()
