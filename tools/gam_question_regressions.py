"""Track exact -감 candidate judgments without reformatting historical ledgers."""

import argparse
import json

from gam_question_audit import FIXTURE, LMF, ROOT
from lexical_nada_audit import read

RAW = ROOT / "tests/fixtures/validity.json"
POLICY = ROOT / "tests/fixtures/dictionary-attachments.json"


def records():
    raw = []
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
                "Source-backed structural candidate; contextual sense and independent review pending."
                if row["verdict"] == "required"
                else "Exact written-boundary exclusion; other lemma and morpheme paths remain unjudged."
            ),
        )
        raw.append(
            {"id": row["id"], "surface": row["surface"], "judgments": [judgment]}
        )
    policy = []
    for word, head, form, verdict, source in [
        ("먹은감", "먹다", "은감", "forbidden", 73888),
        ("좋는감", "좋다", "는감", "forbidden", 73879),
        ("좋은감", "좋다", "은감", "required", 73888),
        ("가는감", "가다", "는감", "required", 73879),
        ("있는감", "있다", "는감", "required", 73879),
        ("없는감", "없다", "는감", "required", 73879),
    ]:
        cid = "gam-question-policy-" + word
        policy.append(
            {
                "id": cid,
                "surface": word,
                "judgments": [
                    {
                        "id": cid + "-path",
                        "lemmas": [head],
                        "lemma_kinds": ["predicate"],
                        "morphemes": [form],
                        "morpheme_kinds": ["ending"],
                        "required_rules": ["ending.refuting_question"],
                        "verdict": verdict,
                        "source": f"gam-question-{source}",
                        "reason": "Native bare-owner attachment class; contextual interpretation remains pending.",
                    }
                ],
            }
        )
    return raw, policy


def update(path, rows):
    original_text = path.read_text()
    original = json.loads(original_text)
    sources = {
        f"gam-question-{i}": f"https://krdict.korean.go.kr/kor/dicSearch/SearchView?ParaWordNo={i}"
        for i in (73878, 73879, 73880, 73888)
    }
    assert not any(c["id"].startswith("gam-question-") for c in original["cases"])
    source_start = original_text.index('"sources": {') + len('"sources": {')
    text = (
        original_text[:source_start]
        + "\n"
        + "\n".join(
            "    " + json.dumps(k) + ": " + json.dumps(v) + ","
            for k, v in sources.items()
        )
        + original_text[source_start:]
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
    expected = dict(
        original, sources=original["sources"] | sources, cases=original["cases"] + rows
    )
    assert json.loads(text) == expected
    path.write_text(text)


def verify():
    original = read(LMF)
    labels = read(ROOT / "tests/fixtures/krdict-gam-question-labels.json")
    expected = [
        e
        for e in original["LexicalResource"]["Lexicon"]["LexicalEntry"]
        if e["val"] in {"73878", "73879", "73880", "73888"}
    ]
    assert len(expected) == 4
    assert labels["LexicalResource"]["Lexicon"]["LexicalEntry"] == expected
    for path, expected in zip((RAW, POLICY), records()):
        suite = read(path)
        actual = [c for c in suite["cases"] if c["id"].startswith("gam-question-")]
        assert actual == expected
        for c in actual:
            for j in c["judgments"]:
                assert suite["sources"][j["source"]].endswith(
                    j["source"].split("-")[-1]
                )
    print(
        "Verified -감 central regressions: 57 required / 12 forbidden raw; 4 required / 2 forbidden dictionary paths."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if not args.verify:
        for path, rows in zip((RAW, POLICY), records()):
            update(path, rows)
    verify()
