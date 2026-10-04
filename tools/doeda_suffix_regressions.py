"""Preserve original -되다 proposals and append attributed corrected judgments.

The bound root 속 is lookup material for 俗, not the unrelated interior noun.
This individual lexical identity review does not settle historical root analysis
or select contextual senses for other homonyms. Missing heads remain raw paths
and explicit filter observations rather than attachment-policy successes.
"""

import argparse
import copy
import json
from collections import Counter

from doeda_suffix_audit import FIXTURE
from lexical_nada_audit import ROOT, read, sha

CORRECTIONS = ROOT / "tests/fixtures/doeda-suffix-corrections.json"
RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
SOURCES = {
    "doeda-suffix-krdict": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=74902",
    "doeda-suffix-sok-identity": "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=64223",
}


def amendment():
    original = read(FIXTURE)
    entries = {e["id"]: e for e in original["source_entries"]}
    whole, noun = entries["krdict:64223"], entries["krdict:71278"]
    assert (whole["headword"], whole["pos"], whole["origins"]) == (
        "속되다",
        "형용사",
        ["俗되다"],
    )
    assert (noun["headword"], noun["pos"], len(noun["senses"])) == ("속", "명사", 8)
    originals = [c for c in original["cases"] if c["lemmas"][0] == "속"]
    assert len(originals) == 10
    corrections = []
    for old in originals:
        assert old["lemma_kinds"][0] == "nominal" and old["verdict"] == "required"
        corrections.append(
            {
                "original": old,
                "replacement_control": dict(
                    old,
                    id=old["id"] + "-nominal-control",
                    verdict="forbidden",
                    scope="scoped lexical-identity control; interior noun is not the 俗 base",
                ),
                "replacement_positive": dict(
                    old,
                    id=old["id"] + "-bound-root",
                    lemma_kinds=["root", *old["lemma_kinds"][1:]],
                    scope="bound 俗 lookup material; formal-history and independent review pending",
                ),
            }
        )
    return {
        "schema_version": 1,
        "source_fixture_sha256": sha(FIXTURE),
        "reason": "Original spelling-based proposal borrowed nominal 속 from unrelated interior/content/mind noun 71278. Native adjective 64223 records 俗되다 and suffix 74902 lists 속되다. Preserve all ten original proposals, forbid only their nominal suffix path, and use bound root lookup material for 俗. Absence of an origin is not evidence by itself. This agent review neither establishes a standalone root entry nor settles formal/historical decomposition.",
        "source_entries": [whole, noun],
        "sources": [
            SOURCES["doeda-suffix-krdict"],
            SOURCES["doeda-suffix-sok-identity"],
            noun["url"],
        ],
        "corrections": corrections,
        "native_entry_reviews": [
            {
                "entry_id": noun["id"],
                "lemma": "속",
                "lemma_kind": "root",
                "required_rule": "suffix.adjective.doeda",
                "owned_suffix": "되다",
                "verdict": "incompatible",
                "conflict": "derivational_root",
                "reason": "All eight noun senses concern interior, contents, mind/attitude or related interior properties; none supplies the vulgar/secular 俗 identity of adjective 64223. The full original entry, including every translation, is retained above. No within-entry contextual sense is selected.",
                "reviewer": "agent",
                "independent_review": "pending",
            }
        ],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
        "remaining_review": "Other spelling homonyms, all 1,850 native formation leads, contextual/register judgments and formal/historical root analysis remain open in COV-022m.",
    }


def effective_cases():
    data = read(CORRECTIONS)
    assert data == amendment(), "Correction or original native evidence changed"
    cases = copy.deepcopy(read(FIXTURE)["cases"])
    for correction in data["corrections"]:
        index = cases.index(correction["original"])
        cases[index] = correction["replacement_control"]
        cases.append(correction["replacement_positive"])
    assert Counter(c["verdict"] for c in cases) == {"required": 1580, "forbidden": 20}
    assert len({c["id"] for c in cases}) == 1600
    return cases


def effective_formations():
    effective_cases()
    proposals = copy.deepcopy(read(FIXTURE)["formation_proposals"])
    for p in proposals:
        if p["head"] == "속되다":
            assert p["base_kind"] == "nominal"
            p["base_kind"] = "root"
    return proposals


def records(policy=False):
    source = read(FIXTURE)
    entries = {e["id"]: e for e in source["source_entries"]}
    heads = {}
    for e in entries.values():
        heads.setdefault(e["headword"], []).append(e)
    rows = []
    for case in effective_cases():
        # The policy ledger isolates known compatibility from absent lookups.
        # All missing-head positives remain in the raw ledger and source tests.
        if (
            policy
            and case["verdict"] == "required"
            and any(not heads.get(head) for head in case["lemmas"])
        ):
            continue
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
        identity_conflict = (
            policy and case["lemma_kinds"][0] == "root" and case["lemmas"][0] == "속"
        )
        if identity_conflict:
            assert [e["id"] for e in heads["속"]] == ["krdict:71278"]
            judgment["verdict"] = "forbidden"
        judgment.update(
            id=ident + "-path",
            source="doeda-suffix-sok-identity"
            if case["lemmas"][0] == "속"
            else "doeda-suffix-krdict",
            reason=(
                "Individually reviewed noun 71278 is not the 俗 bound root in 64223; retain raw/headword paths and mark its dictionary attachment conflict. Independent review pending."
                if identity_conflict
                else "Source-listed formation with explicitly owned suffix/inflections. Base lookup roles are attributed agent proposals; homonym sense/context/register and independent review remain unjudged."
                if case["verdict"] == "required"
                else "Scoped suffix class or lexical-identity control; whole lexical candidates and unrelated interpretations remain unjudged."
            ),
        )
        rows.append({"id": ident, "surface": case["surface"], "judgments": [judgment]})
    expected = (
        {"required": 1510, "forbidden": 30}
        if policy
        else {"required": 1580, "forbidden": 20}
    )
    assert Counter(r["judgments"][0]["verdict"] for r in rows) == expected
    return rows


def append(path, policy):
    original = path.read_text()
    suite = json.loads(original)
    rows = records(policy)
    assert not {r["id"] for r in rows} & {r["id"] for r in suite["cases"]}
    assert not set(SOURCES) & set(suite["sources"])
    start = original.index('"sources": {') + len('"sources": {')
    additions = "".join(
        "\n    " + json.dumps(k) + ": " + json.dumps(v) + ","
        for k, v in SOURCES.items()
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
    effective_cases()
    for path, policy in ((RAW, False), (POLICY, True)):
        suite = read(path)
        expected = records(policy)
        ids = {r["id"] for r in expected}
        assert [r for r in suite["cases"] if r["id"] in ids] == expected
        assert all(suite["sources"][k] == v for k, v in SOURCES.items())
        print(path.name, Counter(r["judgments"][0]["verdict"] for r in expected))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-corrections", action="store_true")
    parser.add_argument("--append", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.freeze_corrections:
        with CORRECTIONS.open("x") as file:
            file.write(json.dumps(amendment(), ensure_ascii=False, indent=2) + "\n")
    elif args.append:
        append(RAW, False)
        append(POLICY, True)
        verify()
    elif args.verify:
        verify()
    else:
        parser.error("select --freeze-corrections, --append or --verify")
