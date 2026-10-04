"""Freeze contracted reported-retrospective sources before adding candidates.

Complete native groups and original corpus fields are observations. Authored
attachment judgments, contextual selection and independent review stay separate.
"""

import argparse
import copy
import json
import re
import subprocess
from pathlib import Path

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import MODES, ROOT, digest, load_dictionary, read, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/reported-retrospective-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/reported-retrospective-sources.json"
LMF = ROOT / "tests/fixtures/krdict-reported-retrospective.json"
RULE = "ending.reporting_retrospective"
OWNERS = {
    "다던": [82040],
    "다던데": [82094],
    "는다던": [82037, 82038],
    "는다던데": [82092, 82098],
    "라던": [82042],
    "라던데": [82095],
    "으라던": [82042, 89663],
    "으라던데": [82095, 89050],
    "자던": [89664],
    "자던데": [83888],
    "냐던데": [86357],
    "느냐던데": [86359],
    "으냐던데": [86361],
}
PATTERN = r"(?<![가-힣])[가-힣]+(?:다던데|라던데|냐던데|자던데|다던|라던|자던)[가-힣]*(?![가-힣])"


def cases():
    rows = []

    def add(
        surface,
        heads,
        kinds,
        forms,
        verdict="required",
        status="compatible",
        origin="authored_structural_case",
    ):
        row = {
            "id": "reported-retrospective-"
            + digest([surface, heads, kinds, forms])[:24],
            "surface": surface,
            "lemmas": heads,
            "lemma_kinds": kinds,
            "morphemes": forms,
            "verdict": verdict,
            "ending_owner_status": status if verdict == "required" else None,
            "origin": origin,
            "required_rule": RULE,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        if not any(r["id"] == row["id"] for r in rows):
            rows.append(row)

    for tail in ["던", "던데"]:
        plain = "다" + tail
        present = "는다" + tail
        factual = "라" + tail
        command = "으라" + tail
        proposal = "자" + tail
        for stem, head in [
            ("좋", "좋다"),
            ("있", "있다"),
            ("없", "없다"),
            ("춥", "춥다"),
            ("어렵", "어렵다"),
        ]:
            add(stem + plain, [head], ["predicate"], [plain])
        for stem, head in [
            ("간", "가다"),
            ("산", "살다"),
            ("먹는", "먹다"),
            ("만든", "만들다"),
            ("돕는", "돕다"),
            ("붓는", "붓다"),
            ("짓는", "짓다"),
            ("듣는", "듣다"),
        ]:
            add(stem + "다" + tail, [head], ["predicate"], [present])
        for stem, head, prefs in [
            ("났", "나다", ["었"]),
            ("먹었", "먹다", ["었"]),
            ("먹겠", "먹다", ["겠"]),
            ("먹으셨", "먹다", ["시", "었"]),
            ("먹으셨겠", "먹다", ["시", "었", "겠"]),
            ("먹었었", "먹다", ["었", "었"]),
            ("좋으시", "좋다", ["시"]),
        ]:
            add(stem + plain, [head], ["predicate"], prefs + [plain])
        add(
            "먹으시" + plain,
            ["먹다"],
            ["predicate"],
            ["시", plain],
            status="unknown",
            origin="listed_honorific_class_extension_unjudged",
        )
        add(
            "가짜" + plain,
            ["가짜다"],
            ["predicate"],
            [plain],
            status="unknown",
            origin="unknown_lexical_owner",
        )
        for stem, head in [("학생이", "학생"), ("의사", "의사"), ("학교", "학교")]:
            add(stem + factual, [head, "이다"], ["nominal", "copula"], [factual])
        add("아니" + factual, ["아니다"], ["predicate"], [factual])
        add(
            "학생이시" + factual,
            ["학생", "이다"],
            ["nominal", "copula"],
            ["시", factual],
        )
        add(
            "먹으시" + factual,
            ["먹다"],
            ["predicate"],
            ["시", factual],
            status="unknown",
            origin="listed_honorific_class_extension_unjudged",
        )
        for stem, head in [
            ("가", "가다"),
            ("살", "살다"),
            ("먹으", "먹다"),
            ("들으", "듣다"),
            ("도우", "돕다"),
            ("부으", "붓다"),
            ("지으", "짓다"),
        ]:
            add(stem + factual, [head], ["predicate"], [command])
        add("먹으시" + factual, ["먹다"], ["predicate"], ["시", command])
        for stem, head in [("먹", "먹다"), ("가", "가다"), ("살", "살다")]:
            add(stem + proposal, [head], ["predicate"], [proposal])
        for surface, heads, kinds, forms in [
            (
                "먹고싶" + plain,
                ["먹다", "싶다"],
                ["predicate", "auxiliary"],
                ["고", plain],
            ),
            (
                "먹어본다" + tail,
                ["먹다", "보다"],
                ["predicate", "auxiliary"],
                ["어", present],
            ),
            (
                "먹어봤" + plain,
                ["먹다", "보다"],
                ["predicate", "auxiliary"],
                ["어", "었", plain],
            ),
            (
                "먹었어본다" + tail,
                ["먹다", "보다"],
                ["predicate", "auxiliary"],
                ["었", "어", present],
            ),
            (
                "먹지않았" + plain,
                ["먹다", "않다"],
                ["predicate", "auxiliary"],
                ["지", "었", plain],
            ),
            ("학생답" + plain, ["학생"], ["nominal"], ["답다", plain]),
            (
                "학생이었" + plain,
                ["학생", "이다"],
                ["nominal", "copula"],
                ["었", plain],
            ),
            ("학교였" + plain, ["학교", "이다"], ["nominal", "copula"], ["었", plain]),
            (
                "도와달" + factual,
                ["돕다", "달다"],
                ["predicate", "auxiliary"],
                ["어", command],
            ),
            (
                "먹어보" + proposal,
                ["먹다", "보다"],
                ["predicate", "auxiliary"],
                ["어", proposal],
            ),
        ]:
            add(surface, heads, kinds, forms)
        # Ordinary lexical POS conflicts stay raw hypotheses; known fixed
        # auxiliary/derived classes and malformed allomorphs reject only paths.
        add(
            "먹" + plain,
            ["먹다"],
            ["predicate"],
            [plain],
            status="incompatible",
            origin="raw_known_verb_class_conflict",
        )
        add(
            "예쁜다" + tail,
            ["예쁘다"],
            ["predicate"],
            [present],
            status="incompatible",
            origin="raw_known_adjective_class_conflict",
        )
        for surface, head, form in [
            ("가는다" + tail, "가다", present),
            ("살는다" + tail, "살다", present),
            ("먹ㄴ다" + tail, "먹다", present),
            ("먹" + factual, "먹다", command),
            ("갈" + factual, "가다", command),
            ("살으" + factual, "살다", command),
        ]:
            add(surface, [head], ["predicate"], [form], "forbidden")
        for pref in ["었", "겠", "더"]:
            add(
                "먹" + pref + "는다" + tail,
                ["먹다"],
                ["predicate"],
                [pref, present],
                "forbidden",
            )
            add(
                "먹" + pref + "으" + factual,
                ["먹다"],
                ["predicate"],
                [pref, command],
                "forbidden",
            )
            add(
                "먹" + pref + proposal,
                ["먹다"],
                ["predicate"],
                [pref, proposal],
                "forbidden",
            )
        add("먹더" + plain, ["먹다"], ["predicate"], ["더", plain], "forbidden")
        add(
            "학생이" + proposal,
            ["학생", "이다"],
            ["nominal", "copula"],
            [proposal],
            "forbidden",
        )
        add("학생답는다" + tail, ["학생"], ["nominal"], ["답다", present], "forbidden")
        add(
            "먹고싶는다" + tail,
            ["먹다", "싶다"],
            ["predicate", "auxiliary"],
            ["고", present],
            "forbidden",
        )
        add(
            "먹고싶" + proposal,
            ["먹다", "싶다"],
            ["predicate", "auxiliary"],
            ["고", proposal],
            "forbidden",
        )
        add(
            "학생이더" + factual,
            ["학생", "이다"],
            ["nominal", "copula"],
            ["더", factual],
            "required" if tail == "던데" else "forbidden",
        )
        add(
            "학생이리" + factual,
            ["학생", "이다"],
            ["nominal", "copula"],
            ["으리", factual],
            "required" if tail == "던데" else "forbidden",
        )
        add(
            "먹" + plain,
            ["먹다", "하다"],
            ["predicate", "auxiliary"],
            [plain],
            "forbidden",
            origin="no_unwritten_reporter",
        )
    for head, stem, form, status in [
        ("좋다", "좋", "냐던데", "compatible"),
        ("가다", "가", "냐던데", "compatible"),
        ("먹다", "먹", "느냐던데", "compatible"),
        ("있다", "있", "느냐던데", "compatible"),
        ("없다", "없", "느냐던데", "compatible"),
        ("계시다", "계시", "느냐던데", "compatible"),
        ("좋다", "좋으", "으냐던데", "compatible"),
        ("많다", "많으", "으냐던데", "compatible"),
        ("먹다", "먹으", "으냐던데", "incompatible"),
    ]:
        add(
            stem + form.removeprefix("으") if form.startswith("으") else stem + form,
            [head],
            ["predicate"],
            [form],
            status=status,
        )
    for form, ending in [("냐던데", "냐던데"), ("느냐던데", "느냐던데")]:
        for stem, head, pre in [
            ("먹었", "먹다", ["었"]),
            ("먹겠", "먹다", ["겠"]),
            ("먹으시", "먹다", ["시"]),
        ]:
            add(stem + ending, [head], ["predicate"], pre + [form])
        add("먹더" + ending, ["먹다"], ["predicate"], ["더", form], "forbidden")
    add("학생이냐던데", ["학생", "이다"], ["nominal", "copula"], ["냐던데"])
    add("의사냐던데", ["의사", "이다"], ["nominal", "copula"], ["냐던데"])
    add(
        "학생이느냐던데",
        ["학생", "이다"],
        ["nominal", "copula"],
        ["느냐던데"],
        "forbidden",
    )
    add(
        "좋으셨으냐던데", ["좋다"], ["predicate"], ["시", "었", "으냐던데"], "forbidden"
    )
    for surface, heads, kinds, forms in [
        ("한다던데요", ["하다"], ["predicate"], ["는다던데", "요"]),
        ("먹었다던데요", ["먹다"], ["predicate"], ["었", "다던데", "요"]),
        ("학생이라던데요", ["학생", "이다"], ["nominal", "copula"], ["라던데", "요"]),
    ]:
        add(surface, heads, kinds, forms, origin="native_or_inferred_polite_follower")
    assert len(rows) == len({r["id"] for r in rows})
    return rows


def discover(entries):
    found = []
    for entry in entries.values():
        for sense in entry["senses"]:
            for gi, group in enumerate(sense["examples"]):
                for ti, text in enumerate(group):
                    for m in re.finditer(PATTERN, text):
                        key = [entry["id"], sense["id"], gi, ti, m.start(), m.end()]
                        found.append(
                            {
                                "id": "reported-retrospective-native-"
                                + digest(key)[:24],
                                "entry": entry["id"],
                                "sense": sense["id"],
                                "group": gi,
                                "text_index": ti,
                                "surface": m[0],
                                "complete_group": group,
                                "text": text,
                                "char_span": [m.start(), m.end()],
                                "span": {
                                    "start": len(text[: m.start()].encode()),
                                    "end": len(text[: m.end()].encode()),
                                },
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return found


def freeze(cli, dictionary):
    assert not any(p.exists() for p in [SOURCE, FIXTURE, LMF])
    native = load_dictionary(dictionary)
    hits = discover(native)
    corpora = []
    for path in sorted((ROOT / "data/corpora").glob("*/*.conllu")):
        sentences = []
        for block in path.read_text().split("\n\n"):
            matched = [
                row
                for line in block.splitlines()
                for row in [line.split("\t")]
                if len(row) == 10 and row[0].isdigit() and re.fullmatch(PATTERN, row[1])
            ]
            if matched:
                sentences.append(
                    {
                        "complete_sentence": block,
                        "matched_tokens": matched,
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
    rows = cases()
    words = {h["surface"] for h in hits} | {r["surface"] for r in rows}
    words.update(
        r[1] for c in corpora for s in c["sentences"] for r in s["matched_tokens"]
    )
    words.update(["발표났다던데", "학교에서발표났다던데", "날지도", "사고날지도"])
    text = " ".join(sorted(words))
    streams = {
        mode: list(
            map(
                json.loads,
                subprocess.check_output(
                    [
                        str(cli.resolve()),
                        "text",
                        "-",
                        "--dictionary",
                        str(dictionary.resolve()),
                        "--suggest-spacing",
                        *flags,
                    ],
                    input=text.encode(),
                ).splitlines(),
            )
        )
        for mode, flags in MODES.items()
    }
    owners = {f"krdict:{i}" for ids in OWNERS.values() for i in ids} | {
        h["entry"] for h in hits
    }
    heads = {h for row in rows for h in row["lemmas"]} | {"발표", "학교", "나다"}
    owners.update(i for i, e in native.items() if e["headword"] in heads)

    def visit(v):
        if isinstance(v, dict):
            if isinstance(v.get("id"), str) and v["id"].startswith("krdict:"):
                owners.add(v["id"])
            for item in v.values():
                visit(item)
        elif isinstance(v, list):
            for item in v:
                visit(item)

    visit(streams)
    entries = {i: native[i] for i in sorted(owners)}
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
        "checklist": "COV-017 / COV-020r",
        "before_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(dictionary),
        "complete_native_entries": entries,
        "raw_source_sha256": hashes,
        "owners": OWNERS,
        "native_pattern": PATTERN,
        "native_scan_entries": len(native),
        "discoveries": hits,
        "corpora": corpora,
        "before_input": text,
        "before_streams": streams,
        "license": read(ROOT / "docs/lexical-nada-listed-preflight.json.gz")["license"],
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    write(SOURCE, source)
    projected = copy.deepcopy(list(entries.values()))
    for e in projected:
        for s in e["senses"]:
            s["translations"] = [
                t for t in s["translations"] if t["language"] == "영어"
            ]
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_sha256": sha(SOURCE),
                "lmf_sha256": sha(LMF),
                "source_entries": projected,
                "cases": rows,
                "corpora": corpora,
                "before_words": {
                    r["surface"]: {
                        "analysis": r["analysis"],
                        "dictionary": r["dictionary"],
                    }
                    for r in streams["all"]
                    if r["kind"] == "word"
                },
                "tracked_dependency": "lexical-nada-discovery-7b1f871bde65cd5d1aeba52a",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def verify():
    s, f = read(SOURCE), read(FIXTURE)
    assert f["source_sha256"] == sha(SOURCE) and f["lmf_sha256"] == sha(LMF)
    assert f["cases"] == cases() and f["corpora"] == s["corpora"]
    assert s["owners"] == OWNERS and s["native_pattern"] == PATTERN
    assert s["discoveries"] == discover(s["complete_native_entries"])
    assert s["native_scan_entries"] == 56555
    verify_native_lmf(read(LMF), s["complete_native_entries"])
    for hit in s["discoveries"]:
        entry = s["complete_native_entries"][hit["entry"]]
        sense = next(x for x in entry["senses"] if x["id"] == hit["sense"])
        assert sense["examples"][hit["group"]] == hit["complete_group"]
        assert hit["complete_group"][hit["text_index"]] == hit["text"]
        assert (
            hit["text"].encode()[hit["span"]["start"] : hit["span"]["end"]].decode()
            == hit["surface"]
        )
    for corpus in s["corpora"]:
        for sentence in corpus["sentences"]:
            matched = [
                row
                for line in sentence["complete_sentence"].splitlines()
                for row in [line.split("\t")]
                if len(row) == 10 and row[0].isdigit() and re.fullmatch(PATTERN, row[1])
            ]
            assert matched == sentence["matched_tokens"]
    assert f["before_words"] == {
        r["surface"]: {"analysis": r["analysis"], "dictionary": r["dictionary"]}
        for r in s["before_streams"]["all"]
        if r["kind"] == "word"
    }
    followers = read(ROOT / "tests/fixtures/reported-retrospective-followers.json")
    assert followers["core_source_sha256"] == sha(SOURCE)
    originals = {e["id"]: e for e in f["source_entries"]}
    assert all(originals[e["id"]] == e for e in followers["source_entries"])
    assert len(followers["cases"]) == 7
    for row in followers["cases"]:
        assert (
            row["id"]
            == "reported-retrospective-"
            + digest(
                [row["surface"], row["lemmas"], row["lemma_kinds"], row["morphemes"]]
            )[:24]
        )
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
        assert row["morphemes"][-1] == "요"
    wanted = {f"krdict:{i}" for ids in OWNERS.values() for i in ids}
    grammar_raw = read(
        ROOT / "tests/fixtures/krdict-reported-retrospective-labels.json"
    )
    verify_native_lmf(grammar_raw, {i: s["complete_native_entries"][i] for i in wanted})
    labels = read(ROOT / "web/src/grammar-labels.json")
    for form, owners in OWNERS.items():
        expected = [
            {
                "id": i,
                "headword": originals[f"krdict:{i}"]["headword"],
                "pos": originals[f"krdict:{i}"]["pos"],
            }
            for i in owners
        ]
        assert labels["-" + form]["sources"] == expected
        assert labels["-" + form]["kind"] == "ending"
    from reported_retrospective_corrections import effective_cases
    from reported_retrospective_corrections import verify as verify_corrections

    verify_corrections()
    ledger = {c["id"]: c for c in read(ROOT / "tests/fixtures/validity.json")["cases"]}
    boundaries = read(ROOT / "tests/fixtures/reported-retrospective-boundaries.json")
    assert boundaries["source_sha256"] == sha(SOURCE)
    assert boundaries["source_entry"] == originals["krdict:86361"]
    assert len(boundaries["cases"]) == 5
    for row in boundaries["cases"]:
        assert (
            row["id"]
            == "reported-retrospective-boundary-"
            + digest(
                [row["surface"], row["lemmas"], row["lemma_kinds"], row["morphemes"]]
            )[:24]
        )
        assert row["contextual_verdict"] == "unjudged"
        assert row["independent_review"] == "pending"
        if row["verdict"] == "forbidden":
            record = next(
                r
                for r in boundaries["before_records"]
                if r["surface"] == row["surface"]
            )
            assert any(
                [l["text"] for l in a["lemmas"]] == row["lemmas"]
                and [m["form"] for m in a["morphemes"]] == row["morphemes"]
                for a in record["analysis"]["analyses"]
            )
    for row in effective_cases() + boundaries["cases"]:
        judgment = ledger[row["id"]]["judgments"][0]
        assert ledger[row["id"]]["surface"] == row["surface"]
        assert all(
            judgment[k] == row[k]
            for k in ["lemmas", "lemma_kinds", "morphemes", "verdict"]
        )
    print(
        f"Verified {len(f['cases'])} authored cases, {len(s['discoveries'])} native spelling observations, {len(f['before_words'])} prior words, {sum(len(x['matched_tokens']) for c in s['corpora'] for x in c['sentences'])} original annotated tokens and {len(f['source_entries'])} complete native owners; contextual/independent review pending."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli-before", type=Path)
    p.add_argument("--dictionary", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    elif a.cli_before and a.dictionary:
        freeze(a.cli_before, a.dictionary)
        verify()
    else:
        p.error("freeze requires --cli-before and --dictionary")
