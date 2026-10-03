"""Review the original 67 excluded native inflection fields without repairing them.

The evaluator trims surrounding whitespace only to choose a diagnostic token.
Source fields, missing spellings, original exclusions and pronunciation conflicts
stay intact. Judgments select named head/ending paths, not every raw alternative.
Extraction refuses overwrites; verification works offline in the Nix flake.
"""

import argparse
import copy
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "excluded-paradigm-sources.json"
LMF = "krdict-excluded-paradigm.json"
CONFLICT = "krdict:90327"


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def array(value):
    return value if isinstance(value, list) else [value]


def ending(surface):
    # Authored canonical ending selection, independent of the candidate output.
    for suffix, form in [
        ("니다", "습니다"),
        ("니", "으니"),
        ("는", "는"),
        ("지", "지"),
        ("고", "고"),
    ]:
        if surface.endswith(suffix):
            return form
    return "어"


def reviews_and_cases(rows, entries, primary):
    reviews, cases, sources = [], [], {}
    for row in rows:
        ident, index = row["entry_id"], row["form_index"]
        surface = row["written"].strip()
        case_id = f"excluded-paradigm-{ident.split(':')[1]}-{index}"
        review = dict(
            id=case_id,
            original_observation=copy.deepcopy(row),
            diagnostic_surface=surface or None,
            disposition="empty_written_field"
            if not surface
            else "reviewed_written_base_conflict"
            if ident == CONFLICT
            else "reviewed_surrounding_whitespace",
            scope="Only this named head/ending pair. No source repair, "
            "spelling correction, alias, sense choice or global input ban.",
        )
        reviews.append(review)
        if not surface:
            review["basis"] = (
                "No written observation exists; keep the empty field and its sibling forms."
            )
            continue
        assert re.fullmatch("[가-힣]+", surface), row
        assert row["written"] != surface, row
        source = case_id + "-source"
        sources[source] = entries[ident]["url"]
        reason = (
            "The complete native entry explicitly lists this inflection. "
            "Surrounding whitespace is excluded only from the diagnostic token; "
            "the ending decomposition is an agent morphological inference."
        )
        if ident == CONFLICT:
            sources[source] = primary["spelling"]["url"]
            reason = (
                "Agent application of spelling Article 15 to the complete 졸아들다 head: "
                "preserve 졸아들- before 어. The entry's examples also use 졸아들어. "
                "The conflicting 조라들어 field stays unchanged; no alternate head is judged."
            )
        review["basis"] = reason

        def add(label, token, verdict):
            cases.append(
                dict(
                    id=case_id + "-" + label,
                    surface=token,
                    judgments=[
                        dict(
                            id="path",
                            lemmas=[row["headword"]],
                            lemma_kinds=["predicate"],
                            morphemes=[ending(token)],
                            morpheme_kinds=["ending"],
                            verdict=verdict,
                            source=source,
                            reason=reason,
                        )
                    ],
                )
            )

        add("listed", surface, "forbidden" if ident == CONFLICT else "required")
        if ident == CONFLICT:
            add("companion", "졸아들어", "required")
            review["standard_written_companion"] = "졸아들어"
    return reviews, cases, sources


def verify(report):
    original = ROOT / report["original_discovery"]
    assert sha(original) == report["original_discovery_sha256"]
    assert report["extractor_sha256"] == sha(__file__)
    rows = json.loads(original.read_text())["excluded"]
    assert rows == report["original_exclusions"] and len(rows) == 67
    entries = report["complete_native_entries"]
    assert len(entries) == 63
    for row in rows:
        native = entries[row["entry_id"]]
        assert (native["headword"], native["pos"]) == (row["headword"], row["pos"])
        assert native["forms"][row["form_index"]]["written"] == row["written"]
    reviews, cases, sources = reviews_and_cases(rows, entries, report["primary_review"])
    assert reviews == report["reviews"] and cases == report["cases"]
    assert sources == report["sources"]
    assert report["counts"] == dict(
        original_exclusions=67,
        empty_fields=10,
        whitespace_fields=57,
        supported_listed_pairs=56,
        written_conflicts=1,
        required=57,
        forbidden=1,
    )
    ledger = json.loads((ROOT / "tests/fixtures/validity.json").read_text())
    indexed = {case["id"]: case for case in ledger["cases"]}
    assert all(indexed[c["id"]] == c for c in cases)
    assert all(ledger["sources"][key] == val for key, val in sources.items())
    for entry in report["source_entries"]:
        expected = copy.deepcopy(entries[entry["id"]])
        for sense in expected["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
        assert entry == expected
    print(
        "67 original exclusions retained: 56 supported pairs, 1 written conflict, 10 empty fields; 58 ledger cases verified."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument(
        "--dictionary", type=Path, default=ROOT / "data/dictionaries/krdict/krdict.db"
    )
    parser.add_argument("--primary-review", type=Path)
    parser.add_argument(
        "--output-directory", type=Path, default=ROOT / "tests/fixtures"
    )
    args = parser.parse_args()
    output = args.output_directory.resolve()
    if args.verify:
        verify(json.loads((output / NAME).read_text()))
        return
    if not args.cli or not args.primary_review:
        parser.error("Extraction requires --cli and --primary-review.")
    if not output.is_dir() or any((output / name).exists() for name in (NAME, LMF)):
        parser.error(
            "Output directory must exist; frozen evidence will not be overwritten."
        )
    original = ROOT / "docs/written-paradigm-discovery.json"
    discovery = json.loads(original.read_text())
    dictionary, cli = args.dictionary.resolve(), args.cli.resolve()
    assert sha(dictionary) == discovery["dictionary_sha256"]
    rows, entries = discovery["excluded"], {}
    with sqlite3.connect(dictionary.as_uri() + "?mode=ro", uri=True) as db:
        for row in rows:
            ident = row["entry_id"]
            entries[ident] = json.loads(
                db.execute("select data from entries where id=?", (ident,)).fetchone()[
                    0
                ]
            )
    primary = json.loads(args.primary_review.read_text())
    reviews, cases, sources = reviews_and_cases(rows, entries, primary)
    surfaces = {case["surface"] for case in cases}
    surfaces.update(e["headword"] for e in entries.values())
    # Empty fields are not observations. Retain sibling diagnostics separately.
    for row in rows:
        if not row["written"]:
            surfaces.update(
                f["written"].strip()
                for f in entries[row["entry_id"]]["forms"]
                if f["written"] and re.fullmatch("[가-힣]+", f["written"].strip())
            )
    words = {
        s: {
            mode: json.loads(
                subprocess.check_output(
                    [str(cli), "word", s, "--dictionary", str(dictionary), *flags]
                )
            )
            for mode, flags in [
                ("all", []),
                ("headword", ["--dict-only"]),
                ("compatible", ["--dict-compatible"]),
            ]
        }
        for s in sorted(surfaces)
    }
    texts = {
        r["id"]: [
            json.loads(line)
            for line in subprocess.check_output(
                [str(cli), "text", "--dictionary", str(dictionary)],
                input=r["original_observation"]["written"].encode(),
            ).splitlines()
        ]
        for r in reviews
    }
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / "data/dictionaries/krdict/json").glob("*.json")):
        raw_data = json.loads(path.read_text())["LexicalResource"]["Lexicon"][
            "LexicalEntry"
        ]
        for raw in array(raw_data):
            ident = "krdict:" + str(raw["val"])
            if ident not in entries:
                continue
            head = next(
                f["val"]
                for lemma in array(raw["Lemma"])
                for f in array(lemma["feat"])
                if f["att"] == "writtenForm"
            )
            pos = next(
                (
                    f["val"]
                    for f in array(raw.get("feat", []))
                    if f["att"] == "partOfSpeech"
                ),
                "품사 없음",
            )
            if (head, pos) != (entries[ident]["headword"], entries[ident]["pos"]):
                continue
            assert ident not in raw_entries
            raw = copy.deepcopy(raw)
            raw.pop("RelatedForm", None)
            raw["Sense"] = array(raw.get("Sense", []))
            for sense in raw["Sense"]:
                if "Equivalent" in sense:
                    sense["Equivalent"] = [
                        e
                        for e in array(sense["Equivalent"])
                        if any(
                            f["att"] == "language" and f["val"] == "영어"
                            for f in array(e.get("feat", []))
                        )
                    ]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == set(entries)
    projected = copy.deepcopy([entries[i] for i in sorted(entries)])
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [
                t for t in sense["translations"] if t["language"] == "영어"
            ]
    report = dict(
        schema_version=1,
        checklist=["COV-021r"],
        reviewed="2026-10-03",
        before_revision=subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        extractor_source="tools/excluded_paradigm_audit.py",
        extractor_sha256=sha(__file__),
        original_discovery=str(original.relative_to(ROOT)),
        original_discovery_sha256=sha(original),
        cli=str(cli),
        cli_sha256=sha(cli),
        dictionary_sha256=sha(dictionary),
        counts=dict(
            original_exclusions=67,
            empty_fields=10,
            whitespace_fields=57,
            supported_listed_pairs=56,
            written_conflicts=1,
            required=57,
            forbidden=1,
        ),
        original_exclusions=rows,
        complete_native_entries=entries,
        source_entries=projected,
        raw_source_hashes=hashes,
        primary_review=primary,
        reviews=reviews,
        sources=sources,
        cases=cases,
        before_words=words,
        before_text_records=texts,
        attribution=discovery["attribution"],
        license=discovery["license"],
        limitation="Finite written-form review only. All original exclusions and 97 discovery misses remain intact. "
        "Empty forms do not become failures or guessed spellings; surrounding whitespace is retained in text. "
        "Independent Korean review, other lexical paradigms and unresolved complex-coda shortening remain open.",
    )
    (output / NAME).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (output / LMF).write_text(
        json.dumps(
            {
                "LexicalResource": {
                    "Lexicon": {
                        "LexicalEntry": [raw_entries[i] for i in sorted(raw_entries)]
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    print(
        f"Frozen {len(rows)} observations, {len(entries)} entries, {len(words)} diagnostic surfaces."
    )


if __name__ == "__main__":
    main()
