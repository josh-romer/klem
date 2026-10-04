"""Append source-scoped 되다 role judgments without rewriting prior cases."""

import argparse
import json

from doeda_role_audit import FIXTURE, ROOT
from lexical_nada_audit import read

RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
SOURCE_ID = "doeda-role-89858"
URL = "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89858"


def records(policy=False):
    rows = []
    for case in read(FIXTURE)["cases"]:
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
        judgment.update(
            id=ident + "-path",
            source=SOURCE_ID,
            reason=(
                "Attributed lexical-verb role alternative from the complete KRDict 되다 senses; the -게끔 composition has separately preserved original corpus evidence. Historical auxiliary representations and their known native role conflicts remain intact. Contextual meaning and independent review pending."
                if case["verdict"] == "required"
                else "Only the lexical.doeda.complement projection is excluded on this exact other connector. This does not ban unrelated native complements, other rules or contextual readings."
            ),
        )
        rows.append({"id": ident, "surface": case["surface"], "judgments": [judgment]})
    return rows


def append(path, policy):
    original = path.read_text()
    suite = json.loads(original)
    rows = records(policy)
    assert not {r["id"] for r in rows} & {r["id"] for r in suite["cases"]}
    assert SOURCE_ID not in suite["sources"]
    start = original.index('"sources": {') + len('"sources": {')
    updated = (
        original[:start]
        + "\n    "
        + json.dumps(SOURCE_ID)
        + ": "
        + json.dumps(URL)
        + ","
        + original[start:]
    )
    end = updated.rindex("\n  ]")
    updated = (
        updated[:end]
        + ",\n"
        + ",\n".join(
            "    " + json.dumps(r, ensure_ascii=False, indent=2).replace("\n", "\n    ")
            for r in rows
        )
        + updated[end:]
    )
    assert json.loads(updated) == dict(
        suite, sources=suite["sources"] | {SOURCE_ID: URL}, cases=suite["cases"] + rows
    )
    path.write_text(updated)


def verify():
    for path, policy in ((RAW, False), (POLICY, True)):
        suite = read(path)
        expected = records(policy)
        ids = {r["id"] for r in expected}
        assert [r for r in suite["cases"] if r["id"] in ids] == expected
        assert suite["sources"][SOURCE_ID] == URL
    print(
        "Verified 78 required lexical-role alternatives and three scoped projection controls in both raw and dictionary policy ledgers; prior auxiliary conflicts remain separate."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify:
        for path, policy in ((RAW, False), (POLICY, True)):
            ids = {r["id"] for r in records(policy)}
            existing = {r["id"] for r in read(path)["cases"]}
            if ids & existing:
                assert ids <= existing
            else:
                append(path, policy)
    verify()
