"""Freeze the COV-017bu source and candidate boundary audit before parser edits.

All native occurrences are observations, including colloquial and conflicting
uses. Proposed corrections are separate from the immutable original ledger.
This verifier checks evidence fidelity, not completion or contextual precision.
"""

import argparse
import copy
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, digest, load_dictionary, read, run, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/adjectival-allomorph-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/adjectival-allomorph-preflight.json"
LMF = ROOT / "tests/fixtures/krdict-adjectival-allomorph.json"
DERIVED = ROOT / "tests/fixtures/adjectival-allomorph-derived-supplement.json"
EVALUATION = ROOT / "docs/adjectival-allomorph-preflight-evaluation.json"
DERIVED_GUIDANCE = {
    "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=90&pageIndex=1&qna_seq=329643",
    "accessed": "2026-10-04",
    "summary": "NIKL explains that the adjective formed with -답다 conjugates with ㅂ irregularity, illustrating 너다운. The suffix's adjective-forming role does not bypass conjugation.",
}
OWNERS = {
    "으냐": [76235],
    "으냐고": [79258, 87444],
    "으냐는": [86032],
    "으냐며": [86921],
    "으냐면서": [86119],
    "으냐니": [87425, 92543],
    "으냔": [85664],
    "으냔다": [85925],
    "으냬": [89683],
    "으냐지만": [85643],
    "으냐니까": [80820],
    "으냐느니": [88987],
    "으냐면": [80180],
    "으냐던데": [86361],
    "으냐는구나": [88947],
    "으냐는군": [89638],
    "으냐더군": [89661],
    "으냐더군요": [89826],
}
# Broad by design: the general 냐 readings, irregular spellings, exceptional
# native uses and unrelated lexical matches must not disappear from this scan.
PATTERN = r"(?<![가-힣])[가-힣]*(?:냐|냔|냬)[가-힣]*(?![가-힣])"
GUIDANCE = [
    {
        "url": "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=&pageIndex=1&qna_seq=310957",
        "accessed": "2026-10-04",
        "summary": "NIKL distinguishes closed-stem adjective 으냐 from colloquial 냐, which can attach to predicates and 이다. Both 많으냐 and 많냐 are possible.",
    },
    {
        "url": "https://www.korean.go.kr/front/mcfaq/mcfaqView.do?mcfaq_seq=5987&mn_id=217&pageIndex=1",
        "accessed": "2026-10-04",
        "summary": "NIKL explicitly analyzes 어떠냐 as 어떻다 with 으냐 and ㅎ irregular conjugation. An open surface before 냐 does not imply an open underlying stem.",
    },
    {
        "url": "https://m.korean.go.kr/nkview/nknews/200107/36_7.html",
        "accessed": "2026-10-04",
        "summary": "NIKL describes 으냐 after non-ㄹ closed adjective stems and 냐 after ㄹ or vowel-final adjective stems. This supports the canonical distinction despite the 주로 qualifier in entry 76235.",
    },
]


def coda(stem):
    last = ord(stem[-1])
    return (last - 0xAC00) % 28 if 0xAC00 <= last <= 0xD7A3 else None


def proposals():
    rows = []

    def add(surface, heads, kinds, forms, morph_kinds, verdict, origin):
        key = [surface, heads, kinds, forms, morph_kinds]
        row = {
            "id": "adjectival-allomorph-" + digest(key)[:24],
            "surface": surface,
            "lemmas": heads,
            "lemma_kinds": kinds,
            "morphemes": forms,
            "morpheme_kinds": morph_kinds,
            "proposed_verdict": verdict,
            "origin": origin,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        assert not any(r["id"] == row["id"] for r in rows)
        rows.append(row)

    for full in OWNERS:
        short = full[1:]
        for surface, head, origin in [
            ("좋" + full, "좋다", "regular_closed_adjective"),
            ("추우" + short, "춥다", "bieup_irregular_closed_adjective"),
            ("파라" + short, "파랗다", "hieut_irregular_closed_adjective"),
            ("어떠" + short, "어떻다", "nikl_attested_hieut_irregular"),
            ("나" + full, "낫다", "siot_irregular_closed_adjective"),
        ]:
            add(surface, [head], ["predicate"], [full], ["ending"], "required", origin)
        for surface, head, origin in [
            ("아프", "아프다", "open_adjective"),
            ("예쁘", "예쁘다", "open_adjective"),
            ("기", "길다", "rieul_adjective"),
        ]:
            for form, verdict in [(short, "required"), (full, "forbidden")]:
                add(
                    surface + short,
                    [head],
                    ["predicate"],
                    [form],
                    ["ending"],
                    verdict,
                    origin,
                )
            add(
                surface + full,
                [head],
                ["predicate"],
                [full],
                ["ending"],
                "forbidden",
                origin + "_full_surface",
            )
        for form, verdict in [(short, "required"), (full, "forbidden")]:
            add(
                "학생이" + short,
                ["학생", "이다"],
                ["nominal", "copula"],
                [form],
                ["ending"],
                verdict,
                "copular_owner",
            )
            add(
                "먹고계시" + short,
                ["먹다", "계시다"],
                ["predicate", "auxiliary"],
                ["고", form],
                ["ending", "ending"],
                verdict,
                "open_auxiliary_owner",
            )
        add(
            "먹고싶" + full,
            ["먹다", "싶다"],
            ["predicate", "auxiliary"],
            ["고", full],
            ["ending", "ending"],
            "required",
            "closed_auxiliary_owner",
        )
        add(
            "아이답" + full,
            ["아이"],
            ["nominal"],
            ["답다", full],
            ["suffix", "ending"],
            "required",
            "closed_derived_owner_after_open_nominal",
        )
        add(
            "좋았" + full,
            ["좋다"],
            ["predicate"],
            ["었", full],
            ["prefinal", "ending"],
            "forbidden",
            "prefinal_boundary",
        )
    return rows


def flagged_originals(ledger):
    rows = []
    for case in ledger["cases"]:
        for judgment in case["judgments"]:
            if judgment["verdict"] != "required" or not any(
                f in OWNERS for f in judgment.get("morphemes", [])
            ):
                continue
            head = judgment["lemmas"][-1]
            stem = head.removesuffix("다")
            if coda(stem) in {0, 8}:
                # This is a review queue, not a removal classifier. In general
                # a derivational suffix can own the ending after an open noun.
                rows.append(
                    {
                        "case_id": case["id"],
                        "surface": case["surface"],
                        "original_judgment": copy.deepcopy(judgment),
                        "original_source_url": ledger["sources"][judgment["source"]],
                        "proposed_verdict": "forbidden",
                        "review_reason": "Canonical 으냐 component requires a non-ㄹ closed underlying owner. Preserve the distinct general 냐 reading. Ordered ownership must be checked before applying this correction.",
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
    return rows


def discover(entries):
    found = []
    for entry in entries.values():
        for sense in entry["senses"]:
            for gi, group in enumerate(sense["examples"]):
                for ti, text in enumerate(group):
                    for match in re.finditer(PATTERN, text):
                        key = [
                            entry["id"],
                            sense["id"],
                            gi,
                            ti,
                            match.start(),
                            match.end(),
                        ]
                        found.append(
                            {
                                "id": "adjectival-allomorph-native-" + digest(key)[:24],
                                "entry": entry["id"],
                                "sense": sense["id"],
                                "group": gi,
                                "text_index": ti,
                                "surface": match[0],
                                "complete_group": group,
                                "text": text,
                                "char_span": [match.start(), match.end()],
                                "span": {
                                    "start": len(text[: match.start()].encode()),
                                    "end": len(text[: match.end()].encode()),
                                },
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return found


def corpus_scan():
    corpora = []
    for path in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for block in path.read_text().split("\n\n"):
            matches = [
                row
                for line in block.splitlines()
                for row in [line.split("\t")]
                if len(row) == 10 and row[0].isdigit() and re.fullmatch(PATTERN, row[1])
            ]
            if matches:
                sentences.append(
                    {
                        "complete_sentence": block,
                        "matched_tokens": matches,
                        "contextual_verdict": "unjudged",
                        "independent_review": "pending",
                    }
                )
        corpora.append(
            {
                "source": str(path.relative_to(ROOT)),
                "source_sha256": sha(path),
                "sentences": sentences,
            }
        )
    return corpora


def grammar_inventory(entries):
    forms = set(OWNERS) | {f[1:] for f in OWNERS}
    return {
        f: sorted(e["id"] for e in entries.values() if e["headword"] == "-" + f)
        for f in sorted(forms)
    }


def freeze(cli, dictionary):
    assert not any(p.exists() for p in [SOURCE, FIXTURE, LMF])
    native = load_dictionary(dictionary)
    ledger = read(ROOT / "tests/fixtures/validity.json")
    flagged = flagged_originals(ledger)
    hits, corpora, rows = discover(native), corpus_scan(), proposals()
    surfaces = sorted(
        {r["surface"] for r in rows + flagged + hits}
        | {r[1] for c in corpora for s in c["sentences"] for r in s["matched_tokens"]}
    )
    print(f"Freezing {len(surfaces)} surfaces in all three filters", flush=True)
    before_input, streams = run(cli, dictionary, surfaces)
    grammar = grammar_inventory(native)
    wanted = {i for ids in grammar.values() for i in ids} | {h["entry"] for h in hits}
    heads = {h for row in rows for h in row["lemmas"]}
    wanted.update(i for i, e in native.items() if e["headword"] in heads)

    def visit(value):
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and value["id"].startswith("krdict:"):
                wanted.add(value["id"])
            for v in value.values():
                visit(v)
        elif isinstance(value, list):
            for v in value:
                visit(v)

    visit(streams)
    entries = {i: native[i] for i in sorted(wanted)}
    print(f"Projecting {len(entries)} complete native owners", flush=True)
    raw, hashes = project_lmf(entries)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    source = {
        "schema_version": 1,
        "checklist": "COV-017bu",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "ledger_sha256": sha(ROOT / "tests/fixtures/validity.json"),
        "original_ledger": ledger,
        "flagged_originals": flagged,
        "canonical_owners": OWNERS,
        "grammar_inventory": grammar,
        "primary_guidance": GUIDANCE,
        "complete_native_entries": entries,
        "raw_source_sha256": hashes,
        "native_pattern": PATTERN,
        "native_scan_entries": len(native),
        "discoveries": hits,
        "corpora": corpora,
        "proposed_cases": rows,
        "before_input": before_input,
        "before_streams": streams,
        "license": read(ROOT / "docs/lexical-nada-listed-preflight.json.gz")["license"],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
        "implementation_status": "preflight_only; corrections not applied",
    }
    write(SOURCE, source)
    selected = sorted({r["surface"] for r in rows + flagged})
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(LMF),
                "canonical_owners": OWNERS,
                "proposed_cases": rows,
                "flagged_originals": flagged,
                "before_words": {
                    r["surface"]: {
                        "analysis": r["analysis"],
                        "dictionary": r["dictionary"],
                    }
                    for r in streams["all"]
                    if r["kind"] == "word" and r["surface"] in selected
                },
                "implementation_status": source["implementation_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def freeze_derived(cli, dictionary):
    """Append a correction to the draft matrix, never rewrite its source freeze."""
    assert not DERIVED.exists()
    source = read(SOURCE)
    assert sha(cli) == source["cli_sha256"]
    assert sha(dictionary) == source["dictionary_sha256"]
    originals = [
        r
        for r in source["proposed_cases"]
        if r["origin"] == "closed_derived_owner_after_open_nominal"
    ]
    changes, rows = [], []
    for original in originals:
        replacement = dict(
            original,
            proposed_verdict="forbidden",
            origin="regular_bieup_derived_surface_rejected",
        )
        changes.append(
            {
                "original": original,
                "replacement": replacement,
                "reason": "The draft used a regular ㅂ surface for fixed ㅂ-irregular -답다. Preserve its original proposal and explicitly reject that component path; add the correctly recovered surface separately.",
            }
        )
        full = original["morphemes"][-1]
        added = dict(
            original,
            surface="아이다우" + full[1:],
            origin="bieup_irregular_closed_derived_owner_after_open_nominal",
        )
        added["id"] = (
            "adjectival-allomorph-"
            + digest(
                [
                    added[k]
                    for k in [
                        "surface",
                        "lemmas",
                        "lemma_kinds",
                        "morphemes",
                        "morpheme_kinds",
                    ]
                ]
            )[:24]
        )
        rows.append(added)
    text, streams = run(cli, dictionary, sorted(r["surface"] for r in rows))
    native = load_dictionary(dictionary)
    entry = native["krdict:92145"]
    adapter_path = ROOT / "tests/fixtures/krdict-derivation.json"
    raw = next(
        e
        for e in read(adapter_path)["LexicalResource"]["Lexicon"]["LexicalEntry"]
        if str(e["val"]) == "92145"
    )
    adapter = {"LexicalResource": {"Lexicon": {"LexicalEntry": [raw]}}}
    verify_native_lmf(adapter, {entry["id"]: entry})
    DERIVED.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "before_cli_sha256": sha(cli),
                "dictionary_sha256": sha(dictionary),
                "superseded": changes,
                "additional_proposals": rows,
                "primary_guidance": DERIVED_GUIDANCE,
                "complete_native_entries": {entry["id"]: entry},
                "native_lmf": adapter,
                "adapter_origin": str(adapter_path.relative_to(ROOT)),
                "adapter_sha256": sha(adapter_path),
                "before_input": text,
                "before_streams": streams,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def effective_proposals():
    rows = proposals()
    supplement = read(DERIVED)
    for change in supplement["superseded"]:
        index = next(
            i for i, r in enumerate(rows) if r["id"] == change["original"]["id"]
        )
        assert rows[index] == change["original"]
        rows[index] = change["replacement"]
    return rows + supplement["additional_proposals"]


def matches(analysis, row):
    return (
        [l["text"] for l in analysis["lemmas"]] == row["lemmas"]
        and (
            row.get("lemma_kinds") is None
            or [l["kind"] for l in analysis["lemmas"]] == row["lemma_kinds"]
        )
        and [m["form"] for m in analysis["morphemes"]] == row["morphemes"]
        and (
            row.get("morpheme_kinds") is None
            or [m["kind"] for m in analysis["morphemes"]] == row["morpheme_kinds"]
        )
        and all(r in analysis["rules"] for r in row.get("required_rules") or [])
    )


def preflight_evaluation():
    """Report the original behavior; this artifact does not follow parser edits."""
    source, supplement = read(SOURCE), read(DERIVED)
    streams = {
        mode: {r["surface"]: r for r in records if r["kind"] == "word"}
        for mode, records in source["before_streams"].items()
    }
    for mode, records in supplement["before_streams"].items():
        for record in records:
            if record["kind"] == "word":
                assert record["surface"] not in streams[mode]
                streams[mode][record["surface"]] = record
    observations = []
    for proposal in effective_proposals():
        observation = {"id": proposal["id"], "proposal": proposal, "before": {}}
        for mode, words in streams.items():
            record = words[proposal["surface"]]
            indexes = [
                i
                for i, a in enumerate(record["analysis"]["analyses"])
                if matches(a, proposal)
            ]
            observation["before"][mode] = {
                "present": bool(indexes),
                "matches": [
                    {
                        "analysis": record["analysis"]["analyses"][i],
                        "dictionary_reading": record["dictionary"]["readings"][i],
                    }
                    for i in indexes
                ],
            }
        observation["structural_violation"] = observation["before"]["all"][
            "present"
        ] != (proposal["proposed_verdict"] == "required")
        observations.append(observation)
    return {
        "schema_version": 1,
        "source_sha256": sha(SOURCE),
        "supplement_sha256": sha(DERIVED),
        "before_cli_sha256": source["cli_sha256"],
        "dictionary_sha256": source["dictionary_sha256"],
        "scope": "Frozen pre-parser structural proposals and observations. Dictionary filters are reported separately, not assigned contextual judgments. This is not a precision benchmark.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
        "counts": {
            "cases": len(observations),
            "required": sum(
                r["proposal"]["proposed_verdict"] == "required" for r in observations
            ),
            "required_present": sum(
                r["proposal"]["proposed_verdict"] == "required"
                and r["before"]["all"]["present"]
                for r in observations
            ),
            "forbidden": sum(
                r["proposal"]["proposed_verdict"] == "forbidden" for r in observations
            ),
            "forbidden_present": sum(
                r["proposal"]["proposed_verdict"] == "forbidden"
                and r["before"]["all"]["present"]
                for r in observations
            ),
        },
        "observations": observations,
    }


def verify_derived(source, dictionary=None, cli=None):
    supplement = read(DERIVED)
    assert supplement["source_sha256"] == sha(SOURCE)
    assert supplement["before_cli_sha256"] == source["cli_sha256"]
    assert supplement["dictionary_sha256"] == source["dictionary_sha256"]
    assert supplement["primary_guidance"] == DERIVED_GUIDANCE
    assert supplement["adapter_sha256"] == sha(ROOT / supplement["adapter_origin"])
    verify_native_lmf(supplement["native_lmf"], supplement["complete_native_entries"])
    assert (
        len(supplement["superseded"]) == len(supplement["additional_proposals"]) == 18
    )
    for change, added in zip(
        supplement["superseded"], supplement["additional_proposals"], strict=True
    ):
        original, replacement = change["original"], change["replacement"]
        assert original in source["proposed_cases"]
        assert original["origin"] == "closed_derived_owner_after_open_nominal"
        assert replacement == dict(
            original,
            proposed_verdict="forbidden",
            origin="regular_bieup_derived_surface_rejected",
        )
        assert added["surface"] == "아이다우" + original["morphemes"][-1][1:]
        assert added["proposed_verdict"] == "required"
        assert (
            added["id"]
            == "adjectival-allomorph-"
            + digest(
                [
                    added[k]
                    for k in [
                        "surface",
                        "lemmas",
                        "lemma_kinds",
                        "morphemes",
                        "morpheme_kinds",
                    ]
                ]
            )[:24]
        )
        for field in ["lemmas", "lemma_kinds", "morphemes", "morpheme_kinds"]:
            assert added[field] == original[field]
        record = next(
            r
            for r in supplement["before_streams"]["all"]
            if r["surface"] == added["surface"]
        )
        assert any(matches(a, added) for a in record["analysis"]["analyses"])
    if dictionary:
        native = load_dictionary(dictionary)
        assert all(
            native[i] == e for i, e in supplement["complete_native_entries"].items()
        )
    if cli:
        text, streams = run(
            cli,
            dictionary,
            sorted(r["surface"] for r in supplement["additional_proposals"]),
        )
        assert (
            text == supplement["before_input"]
            and streams == supplement["before_streams"]
        )


def verify(dictionary=None, cli=None):
    source, fixture = read(SOURCE), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert source["canonical_owners"] == fixture["canonical_owners"] == OWNERS
    assert source["primary_guidance"] == GUIDANCE
    assert source["native_pattern"] == PATTERN
    assert source["native_scan_entries"] == 56555
    assert source["proposed_cases"] == fixture["proposed_cases"] == proposals()
    assert (
        source["flagged_originals"]
        == fixture["flagged_originals"]
        == flagged_originals(source["original_ledger"])
    )
    assert len(source["flagged_originals"]) == 26
    assert len(source["discoveries"]) == 1703
    assert len(source["complete_native_entries"]) == 1700
    assert source["discoveries"] == discover(source["complete_native_entries"])
    assert source["grammar_inventory"] == grammar_inventory(
        source["complete_native_entries"]
    )
    for form, ids in OWNERS.items():
        assert source["grammar_inventory"][form] == [f"krdict:{i}" for i in sorted(ids)]
        for ident in ids:
            entry = source["complete_native_entries"][f"krdict:{ident}"]
            notes = entry["notes"] + [n for s in entry["senses"] for n in s["notes"]]
            assert any("‘ㄹ’을 제외한 받침 있는 형용사" in n for n in notes)
    verify_native_lmf(read(LMF), source["complete_native_entries"])
    for corpus in source["corpora"]:
        for sentence in corpus["sentences"]:
            expected = [
                row
                for line in sentence["complete_sentence"].splitlines()
                for row in [line.split("\t")]
                if len(row) == 10 and row[0].isdigit() and re.fullmatch(PATTERN, row[1])
            ]
            assert expected == sentence["matched_tokens"]
    assert set(source["before_streams"]) == {"all", "headword", "compatible"}
    all_surfaces = [
        r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
    ]
    assert len(all_surfaces) == len(set(all_surfaces)) == 1399
    for mode, records in source["before_streams"].items():
        assert mode in {"all", "headword", "compatible"}
        assert "".join(r["surface"] for r in records) == source["before_input"]
        assert [r["surface"] for r in records if r["kind"] == "word"] == all_surfaces
        for record in records:
            span = record["span"]
            assert (
                source["before_input"].encode()[span["start"] : span["end"]].decode()
                == record["surface"]
            )
    selected = {
        r["surface"] for r in fixture["proposed_cases"] + fixture["flagged_originals"]
    }
    assert fixture["before_words"] == {
        r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
        for r in source["before_streams"]["all"]
        if r["kind"] == "word" and r["surface"] in selected
    }
    for flagged in fixture["flagged_originals"]:
        assert any(
            matches(a, flagged["original_judgment"])
            for a in fixture["before_words"][flagged["surface"]]["analysis"]["analyses"]
        )
    if DERIVED.exists():
        verify_derived(source, dictionary, cli)
        rows = effective_proposals()
        assert len(rows) == len({r["id"] for r in rows}) == 396
        if EVALUATION.exists():
            assert read(EVALUATION) == preflight_evaluation()
    if dictionary:
        assert sha(dictionary) == source["dictionary_sha256"]
        native = load_dictionary(dictionary)
        assert len(native) == source["native_scan_entries"]
        assert all(native[i] == e for i, e in source["complete_native_entries"].items())
        assert discover(native) == source["discoveries"]
        assert grammar_inventory(native) == source["grammar_inventory"]
        assert corpus_scan() == source["corpora"]
        for path, expected in source["raw_source_sha256"].items():
            assert sha(ROOT / path) == expected
    if cli:
        assert dictionary and sha(cli) == source["cli_sha256"]
        surfaces = [
            r["surface"] for r in source["before_streams"]["all"] if r["kind"] == "word"
        ]
        text, streams = run(cli, dictionary, surfaces)
        assert text == source["before_input"] and streams == source["before_streams"]
    print(
        json.dumps(
            {
                "canonical_families": len(OWNERS),
                "canonical_homonyms": sum(map(len, OWNERS.values())),
                "all_grammar_homonyms": sum(
                    map(len, source["grammar_inventory"].values())
                ),
                "proposed_cases": dict(
                    Counter(r["proposed_verdict"] for r in proposals())
                ),
                "effective_proposed_cases": dict(
                    Counter(r["proposed_verdict"] for r in effective_proposals())
                )
                if DERIVED.exists()
                else None,
                "flagged_originals": len(source["flagged_originals"]),
                "native_observations": len(source["discoveries"]),
                "frozen_words": sum(
                    r["kind"] == "word" for r in source["before_streams"]["all"]
                ),
                "corpus_tokens": sum(
                    len(s["matched_tokens"])
                    for c in source["corpora"]
                    for s in c["sentences"]
                ),
                "full_native_entries": len(source["complete_native_entries"]),
                "status": "verified preflight; parser implementation and independent review remain",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dictionary", type=Path)
    parser.add_argument("--cli-before", type=Path)
    parser.add_argument("--freeze-derived-supplement", action="store_true")
    parser.add_argument("--freeze-evaluation", action="store_true")
    args = parser.parse_args()
    if args.freeze_evaluation:
        assert not EVALUATION.exists()
        EVALUATION.write_text(
            json.dumps(preflight_evaluation(), ensure_ascii=False, indent=2) + "\n"
        )
        verify()
    elif args.freeze_derived_supplement:
        if not (args.cli_before and args.dictionary):
            parser.error("the supplement requires --cli-before and --dictionary")
        freeze_derived(args.cli_before, args.dictionary)
        verify(args.dictionary)
    elif args.verify:
        assert DERIVED.exists() and EVALUATION.exists()
        verify(args.dictionary, args.cli_before)
    elif args.cli_before and args.dictionary:
        freeze(args.cli_before, args.dictionary)
        verify(args.dictionary)
    else:
        parser.error("freeze requires --cli-before and --dictionary")
