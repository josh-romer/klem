"""Freeze and verify the question-clause/topic review before grammar changes.

The original 165 bundle observations remain intact. Only two complete native
contexts are selected as topic attestations; other senses stay unjudged.
"""

import argparse
import copy
import hashlib
import json
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs/question-case-source-preflight.json"
OUTPUT = ROOT / "tests/fixtures/question-topic-sources.json"
LMF = ROOT / "tests/fixtures/krdict-question-topic.json"


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def cases():
    result = []
    for surface, heads, kinds, forms, roles in [
        ("넣느냐는", ["넣다"], ["predicate"], ["느냐", "는"], ["ending", "particle"]),
        ("붙느냐는", ["붙다"], ["predicate"], ["느냐", "는"], ["ending", "particle"]),
        ("먹느냐는", ["먹다"], ["predicate"], ["느냐", "는"], ["ending", "particle"]),
        ("먹냐는", ["먹다"], ["predicate"], ["냐", "는"], ["ending", "particle"]),
        ("크냐는", ["크다"], ["predicate"], ["냐", "는"], ["ending", "particle"]),
        ("좋냐는", ["좋다"], ["predicate"], ["냐", "는"], ["ending", "particle"]),
        ("좋으냐는", ["좋다"], ["predicate"], ["으냐", "는"], ["ending", "particle"]),
        ("학생이냐는", ["학생", "이다"], ["nominal", "copula"], ["냐", "는"], ["ending", "particle"]),
        ("넣었느냐는", ["넣다"], ["predicate"], ["었", "느냐", "는"], ["prefinal", "ending", "particle"]),
        ("넣겠느냐는", ["넣다"], ["predicate"], ["겠", "느냐", "는"], ["prefinal", "ending", "particle"]),
        ("넣으시느냐는", ["넣다"], ["predicate"], ["시", "느냐", "는"], ["prefinal", "ending", "particle"]),
    ]:
        native = surface in ("넣느냐는", "붙느냐는")
        source = "question-topic-" + ("16110" if surface == "넣느냐는" else "38833" if native else "inference")
        result.append(dict(
            id="question-topic-" + surface, surface=surface, judgments=[dict(
                id="topic", lemmas=heads, lemma_kinds=kinds, morphemes=forms,
                morpheme_kinds=roles, required_rules=["particle.quoted_question"],
                verdict="required", source=source,
                reason="Agent decomposition of the complete native question/topic example."
                if native else "Agent structural extension of the two native question/topic contexts and NIKL's functional noun-clause explanation. Existing question/prefinal and lexical-owner licenses remain separate; no contextual sense or register is selected.",
            )],
        ))
    for surface, head, ending in [("넣느냐은", "넣다", "느냐"), ("좋으냐은", "좋다", "으냐")]:
        result.append(dict(id="question-topic-" + surface, surface=surface, judgments=[dict(
            id="wrong-allomorph", lemmas=[head], lemma_kinds=["predicate"],
            morphemes=[ending, "은"], morpheme_kinds=["ending", "particle"],
            verdict="forbidden", source="question-topic-particle",
            reason="The topic particle uses 는 after a vowel; the question clause ends in 냐. This forbids only the named path, never the surface or hypothetical heads.",
        )]))
    return result


def verify(report):
    assert sha(SOURCE) == report["original_preflight_sha256"]
    original = json.loads(SOURCE.read_text())
    observations = [h for h in original["hits"] if h["discovery_classification"] == "bundled-quoted-question-expression"]
    assert observations == report["original_bundle_observations"] and len(observations) == 165
    assert cases() == report["cases"]
    assert sha(LMF) == report["lmf_sha256"]
    assert sha(__file__) == report["extractor_sha256"]
    for selected in report["topic_attestations"]:
        assert selected in observations
        entry = report["complete_native_entries"][selected["entry_id"]]
        sense = next(s for s in entry["senses"] if s["id"] == selected["sense"])
        assert sense["examples"][selected["example_group"]] == selected["complete_example_group"]
        line = selected["complete_example_group"][selected["line_index"]]
        start, end = selected["character_span"]
        assert line[start:end] == selected["surface"]
    ledger = json.loads((ROOT / "tests/fixtures/validity.json").read_text())
    indexed = {c["id"]: c for c in ledger["cases"]}
    assert all(indexed[c["id"]] == c for c in cases())
    assert all(ledger["sources"][k] == v for k, v in report["sources"].items())
    for projected in report["source_entries"]:
        native = copy.deepcopy(report["complete_native_entries"][projected["id"]])
        for sense in native["senses"]:
            sense["translations"] = [t for t in sense["translations"] if t["language"] == "영어"]
        assert native == projected
    print("Question/topic audit: 165 original observations, two selected native contexts, 11 required and two forbidden paths verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--dictionary", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify(json.loads(OUTPUT.read_text()))
        return
    if not args.cli or not args.dictionary or OUTPUT.exists() or LMF.exists():
        parser.error("Freeze requires CLI/dictionary and refuses overwriting existing evidence.")
    original = json.loads(SOURCE.read_text())
    observations = [h for h in original["hits"] if h["discovery_classification"] == "bundled-quoted-question-expression"]
    selected = [h for h in observations if h["surface"] in ("넣느냐는", "붙느냐는")]
    assert len(selected) == 2
    ids = {"krdict:" + str(i) for i in [16110, 38833, 64509, 74181, 66584, 66586, 79033, 15983, 58272, 31670, 86232, 85851, 76230, 76231, 76235]}
    with sqlite3.connect(args.dictionary.resolve().as_uri() + "?mode=ro", uri=True) as db:
        entries = {i: json.loads(db.execute("select data from entries where id=?", (i,)).fetchone()[0]) for i in sorted(ids)}
    from excluded_paradigm_audit import array
    raw_entries, hashes = {}, {}
    for path in sorted((ROOT / "data/dictionaries/krdict/json").glob("*.json")):
        for raw in array(json.loads(path.read_text())["LexicalResource"]["Lexicon"]["LexicalEntry"]):
            ident = "krdict:" + str(raw["val"])
            if ident not in ids:
                continue
            head = next(f["val"] for lemma in array(raw["Lemma"]) for f in array(lemma["feat"]) if f["att"] == "writtenForm")
            pos = next((f["val"] for f in array(raw.get("feat", [])) if f["att"] == "partOfSpeech"), "품사 없음")
            if (head, pos) != (entries[ident]["headword"], entries[ident]["pos"]):
                continue
            assert ident not in raw_entries
            raw = copy.deepcopy(raw)
            raw.pop("RelatedForm", None)
            raw["Sense"] = array(raw.get("Sense", []))
            for sense in raw["Sense"]:
                if "Equivalent" in sense:
                    sense["Equivalent"] = [e for e in array(sense["Equivalent"]) if any(f["att"] == "language" and f["val"] == "영어" for f in array(e.get("feat", [])))]
            raw_entries[ident] = raw
            hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == ids
    LMF.write_text(json.dumps({"LexicalResource": {"Lexicon": {"LexicalEntry": [raw_entries[i] for i in sorted(ids)]}}}, ensure_ascii=False, indent=2) + "\n")
    projected = copy.deepcopy(list(entries.values()))
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [t for t in sense["translations"] if t["language"] == "영어"]
    diagnostics = sorted({h["surface"] for h in observations} | {c["surface"] for c in cases()} | {"크느냐는", "좋느냐는", "학생이느냐는", "뮈느냐는", "넣느냐도", "넣느냐부터"})
    before = {s: {mode: json.loads(subprocess.check_output([str(args.cli.resolve()), "word", s, "--dictionary", str(args.dictionary.resolve()), *flags])) for mode, flags in [("all", []), ("headword", ["--dict-only"]), ("compatible", ["--dict-compatible"])]} for s in diagnostics}
    report = dict(schema_version=1, checklist="COV-018ab", reviewed="2026-10-03",
        before_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        original_preflight_sha256=sha(SOURCE), original_bundle_observations=observations,
        topic_attestations=selected, complete_native_entries=entries, source_entries=projected,
        raw_source_sha256=hashes, lmf_sha256=sha(LMF), extractor_sha256=sha(__file__),
        cli=str(args.cli.resolve()), cli_sha256=sha(args.cli.resolve()), dictionary_sha256=sha(args.dictionary),
        selection="Source/context review before production changes; only two named examples receive contextual topic judgments. All 165 former bundle observations remain available as potentially ambiguous contexts.",
        inference="Uniform question/topic composition is an agent inference from the two modern native contexts and the functional noun-clause explanation, not a direct NIKL ruling about every particle or prefinal.",
        primary_review=dict(url="https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=73&qna_seq=336008", answer_date="2026-09-21", html_sha256="5a7a1bec951ccc5ee17bd9d38c7ff2705ae8cc091df72fb0508cb7a4fc1d8867", finding="The actual answer treats the entire question clause as functioning as a noun clause followed by subject 가. Earlier conflicting answers are quoted in the question; the final answer is separate. This supports the structural inference, not a topic-specific direct ruling."),
        historical_review=dict(url="https://www.korean.go.kr/nkview/nklife/1995_3/5_2.html", finding="The article reviews 1948/1957 grammar and lists 느냐는/느냐도/느냐부터. Its historical classification is not imported and does not license additional modern particle rules in this patch."),
        sources={"question-topic-16110": entries["krdict:16110"]["url"], "question-topic-38833": entries["krdict:38833"]["url"], "question-topic-inference": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=73&qna_seq=336008", "question-topic-particle": entries["krdict:85851"]["url"]},
        cases=cases(), before_words=before)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(observations=len(observations), selected=len(selected), diagnostics=len(diagnostics), entries=len(entries))))


if __name__ == "__main__":
    main()
