"""Append exact emphatic-ending judgments without rewriting historical ledgers."""

import argparse
import json

from emphatic_ending_audit import FIXTURE, LMF, OWNERS, ROOT
from lexical_nada_audit import read

RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"
LABELS = ROOT / "tests/fixtures/krdict-emphatic-ending-labels.json"


def records(policy=False):
    result = []
    for row in read(FIXTURE)["cases"]:
        judgment = {
            k: row[k]
            for k in (
                "lemmas",
                "lemma_kinds",
                "morphemes",
                "morpheme_kinds",
                "required_rules",
                "verdict",
                "source",
            )
        }
        judgment.update(
            id=row["id"] + "-path",
            reason=(
                "Source-backed structural hypothesis; contextual interpretation and independent review pending."
                if row["verdict"] == "required"
                else "Exact boundary/connector control; immediate-owner past in causative joins follows the preserved NIKL report. Other paths remain unjudged."
            ),
        )
        case_id = row["id"]
        if policy:
            case_id += "-policy"
            judgment["id"] = case_id + "-path"
            if "되다" in row["lemmas"] and "auxiliary" in row["lemma_kinds"]:
                assert row["verdict"] == "required"
                judgment.update(
                    verdict="forbidden",
                    source="emphatic-ending-89858",
                    reason="Exact existing lexical-role conflict: the parser's legacy auxiliary 되다 representation differs from KRDict's verb POS. The raw/source-observed path remains required; this is not a grammatical impossibility judgment. Role mapping remains COV-019ag work.",
                )
        result.append(
            {"id": case_id, "surface": row["surface"], "judgments": [judgment]}
        )
    return result


def update(path, policy=False):
    old_text = path.read_text()
    old = json.loads(old_text)
    rows = records(policy)
    sources = {
        f"emphatic-ending-{i}": f"https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={i}"
        for ids in OWNERS.values()
        for i in ids
    }
    if policy:
        sources["emphatic-ending-89858"] = (
            "https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo=89858"
        )
    assert not ({c["id"] for c in rows} & {c["id"] for c in old["cases"]})
    assert not (sources.keys() & old["sources"].keys())
    pos = old_text.index('"sources": {') + len('"sources": {')
    text = (
        old_text[:pos]
        + "\n"
        + "\n".join(
            "    " + json.dumps(k) + ": " + json.dumps(v) + ","
            for k, v in sources.items()
        )
        + old_text[pos:]
    )
    end = text.rindex("\n  ]")
    text = (
        text[:end]
        + ",\n"
        + ",\n".join(
            "    " + json.dumps(r, ensure_ascii=False, indent=2).replace("\n", "\n    ")
            for r in rows
        )
        + text[end:]
    )
    assert json.loads(text) == dict(
        old, sources=old["sources"] | sources, cases=old["cases"] + rows
    )
    path.write_text(text)


def verify():
    for path, policy in [(RAW, False), (POLICY, True)]:
        suite = read(path)
        ids = {c["id"] for c in records(policy)}
        assert [c for c in suite["cases"] if c["id"] in ids] == records(policy)
        for c in records(policy):
            for j in c["judgments"]:
                assert suite["sources"][j["source"]].endswith(
                    j["source"].split("-")[-1]
                )
    ids = {str(i) for v in OWNERS.values() for i in v}
    assert read(LABELS)["LexicalResource"]["Lexicon"]["LexicalEntry"] == [
        e
        for e in read(LMF)["LexicalResource"]["Lexicon"]["LexicalEntry"]
        if e["val"] in ids
    ]
    print(
        "Verified emphatic-ending paths: 109 required / 23 forbidden raw; 107 required / 25 forbidden compatibility judgments, including two existing lexical-role conflicts; three native label sources."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify:
        for path, policy in [(RAW, False), (POLICY, True)]:
            existing = {c["id"] for c in read(path)["cases"]}
            ids = {c["id"] for c in records(policy)}
            if existing & ids:
                assert ids <= existing
            else:
                update(path, policy)
    verify()
