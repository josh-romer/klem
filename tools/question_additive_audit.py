"""Freeze the modern question-clause/do attestation and authored diagnostics.

The original PDF layout and source preflight remain unchanged. A diagnostic
joins one printed word split across a layout line break; production input is
never repaired. Verification runs offline in the Nix flake.
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
PREFLIGHT = ROOT / "docs/question-clause-additive-preflight.json"
OUTPUT = ROOT / "tests/fixtures/question-additive-sources.json"
LMF = ROOT / "tests/fixtures/krdict-question-additive.json"


def sha(path):
    with Path(path).open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def cases():
    result = []
    for surface, heads, kinds, forms, roles in [
        ("내느냐도", ["내다"], ["predicate"], ["느냐", "도"], ["ending", "particle"]),
        ("내냐도", ["내다"], ["predicate"], ["냐", "도"], ["ending", "particle"]),
        ("먹느냐도", ["먹다"], ["predicate"], ["느냐", "도"], ["ending", "particle"]),
        ("먹냐도", ["먹다"], ["predicate"], ["냐", "도"], ["ending", "particle"]),
        ("크냐도", ["크다"], ["predicate"], ["냐", "도"], ["ending", "particle"]),
        ("좋냐도", ["좋다"], ["predicate"], ["냐", "도"], ["ending", "particle"]),
        ("좋으냐도", ["좋다"], ["predicate"], ["으냐", "도"], ["ending", "particle"]),
        ("학생이냐도", ["학생", "이다"], ["nominal", "copula"], ["냐", "도"], ["ending", "particle"]),
        ("냈느냐도", ["내다"], ["predicate"], ["었", "느냐", "도"], ["prefinal", "ending", "particle"]),
        ("내겠느냐도", ["내다"], ["predicate"], ["겠", "느냐", "도"], ["prefinal", "ending", "particle"]),
        ("내시느냐도", ["내다"], ["predicate"], ["시", "느냐", "도"], ["prefinal", "ending", "particle"]),
        ("먹어내느냐도", ["먹다", "내다"], ["predicate", "auxiliary"], ["어", "느냐", "도"], ["ending", "ending", "particle"]),
        ("없지않느냐도", ["없다", "않다"], ["predicate", "auxiliary"], ["지", "느냐", "도"], ["ending", "ending", "particle"]),
    ]:
        literal = surface == "내느냐도"
        result.append(dict(id="question-additive-" + surface, surface=surface, judgments=[dict(
            id="path", lemmas=heads, lemma_kinds=kinds, morphemes=forms, morpheme_kinds=roles,
            required_rules=["particle.quoted_question"], verdict="required",
            source="question-additive-attestation" if literal else "question-additive-absence-exception" if surface == "없지않느냐도" else "question-additive-inference",
            reason="Agent morphological decomposition of the modern attested question/do word; the original printed layout remains unchanged."
            if literal else "Agent extension of the attested question/do boundary and functional noun-clause explanation to the existing question/prefinal/auxiliary licenses. Own lexical classes, the exact 없다-negative exception and contextual register remain separate. This is not direct attestation of every matrix cell.",
        )]))
    result.append(dict(id="question-additive-no-invented-nominalizer", surface="내느냐도", judgments=[dict(
        id="path", lemmas=["내다"], lemma_kinds=["predicate"], morphemes=["느냐", "기", "도"],
        morpheme_kinds=["ending", "ending", "particle"], verdict="forbidden", source="question-additive-inference",
        reason="Agent representation constraint: the attested closed question functions as a noun clause without a written 기. Do not invent that overt morpheme in this named analysis; no alternative head or contextual nominal reading is banned.",
    )]))
    return result


def verify(report):
    assert report["preflight_sha256"] == sha(PREFLIGHT)
    assert report["extractor_sha256"] == sha(__file__)
    assert report["lmf_sha256"] == sha(LMF)
    assert report["cases"] == cases()
    preflight = json.loads(PREFLIGHT.read_text())
    assert preflight["target_path"] == report["attested_target"]
    assert preflight["before_word"] == report["before_words"]["내느냐도"]["all"]
    assert not preflight["target_path_present_before"]
    assert report["native_scan"]["all_native_entries_scanned"] and report["native_scan"]["hits"] == []
    assert report["layout_diagnostic"]["joined_fragment"] == "내느냐도"
    assert preflight["complete_attested_sentence"].count(report["layout_diagnostic"]["source_fragment"]) == 1
    ledger = json.loads((ROOT / "tests/fixtures/validity.json").read_text())
    indexed = {c["id"]: c for c in ledger["cases"]}
    assert all(indexed[c["id"]] == c for c in cases())
    assert all(ledger["sources"][key] == val for key, val in report["sources"].items())
    for projected in report["source_entries"]:
        original = copy.deepcopy(report["complete_native_entries"][projected["id"]])
        for sense in original["senses"]:
            sense["translations"] = [t for t in sense["translations"] if t["language"] == "영어"]
        assert original == projected
    print("Question/do audit: original attestation/layout and zero-hit native scan retained; 13 required and one representation exclusion verified.")


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
        parser.error("Freeze requires CLI/dictionary and refuses overwriting evidence.")
    cli, database = args.cli.resolve(), args.dictionary.resolve()
    preflight = json.loads(PREFLIGHT.read_text())
    ids = {"krdict:" + str(i) for i in [89906, 60625, 15983, 58272, 66584, 66586, 79033, 31670, 86232, 86118, 89917, 71581, 71583, 76230, 76231, 76235, 86258, 86031, 88990]}
    pattern = re.compile(r"[가-힣]+(?:느냐|으냐|냐)도[가-힣]*")
    entries, hits, scanned = {}, [], 0
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        for ident, raw in db.execute("select id,data from entries"):
            entry = json.loads(raw)
            scanned += 1
            if ident in ids:
                entries[ident] = entry
            for sense in entry["senses"]:
                for gi, group in enumerate(sense["examples"]):
                    for li, line in enumerate(group):
                        for match in pattern.finditer(line):
                            hits.append(dict(entry=ident, sense=sense["id"], group=gi, line=li, span=list(match.span()), surface=match.group(), examples=group))
    assert set(entries) == ids and not hits
    from excluded_paradigm_audit import array
    raw_entries, raw_hashes = {}, {}
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
            raw = copy.deepcopy(raw); raw.pop("RelatedForm", None); raw["Sense"] = array(raw.get("Sense", []))
            for sense in raw["Sense"]:
                if "Equivalent" in sense:
                    sense["Equivalent"] = [e for e in array(sense["Equivalent"]) if any(f["att"] == "language" and f["val"] == "영어" for f in array(e.get("feat", [])))]
            raw_entries[ident] = raw; raw_hashes[str(path.relative_to(ROOT))] = sha(path)
    assert set(raw_entries) == ids
    LMF.write_text(json.dumps({"LexicalResource": {"Lexicon": {"LexicalEntry": [raw_entries[i] for i in sorted(ids)]}}}, ensure_ascii=False, indent=2) + "\n")
    projected = copy.deepcopy([entries[i] for i in sorted(ids)])
    for entry in projected:
        for sense in entry["senses"]:
            sense["translations"] = [t for t in sense["translations"] if t["language"] == "영어"]
    diagnostics = sorted({c["surface"] for c in cases()} | {"크느냐도", "좋느냐도", "학생이느냐도", "뮈느냐도", "좋지않느냐도", "좋아내느냐도", "먹느냐는데도", "먹느냐는도", "내느냐도요", "내느냐도는", "내느냐부터", "내느냐조차", "내느냐마저"})
    before = {s: {mode: json.loads(subprocess.check_output([str(cli), "word", s, "--dictionary", str(database), *flags])) for mode, flags in [("all", []), ("headword", ["--dict-only"]), ("compatible", ["--dict-compatible"])]} for s in diagnostics}
    report = dict(schema_version=1, checklist="COV-018ad", before_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        preflight_sha256=sha(PREFLIGHT), extractor_sha256=sha(__file__), lmf_sha256=sha(LMF),
        cli=str(cli), cli_sha256=sha(cli), dictionary_sha256=sha(database), raw_source_sha256=raw_hashes,
        attested_target=preflight["target_path"], layout_diagnostic=dict(source_fragment="내\n느냐도", joined_fragment="내느냐도", interpretation="Author diagnostic removes one printed internal-word layout break. No production whitespace repair or cross-token joining."),
        native_scan=dict(regex=pattern.pattern, entries_scanned=scanned, all_native_entries_scanned=True, hits=hits, limitation="No direct attestation in this snapshot is not evidence of impossibility."),
        complete_native_entries=entries, source_entries=projected, before_words=before,
        inference="Uniform question/do composition and existing prefinal/auxiliary combinations are agent structural inferences from the modern attestation and functional noun-clause explanation. Context, sense and register remain unjudged; no further particle license follows automatically.",
        sources={"question-additive-attestation": preflight["source_url"], "question-additive-inference": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=73&qna_seq=336008", "question-additive-absence-exception": "https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=8390&mn_id=62&pageIndex=80"}, cases=cases())
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(entries=len(entries), diagnostics=len(diagnostics), native_entries_scanned=scanned, native_hits=len(hits), required=13, forbidden=1)))


if __name__ == "__main__":
    main()
