"""Freeze native -랴 sources, concessive followers and original candidate evidence.

Every source occurrence keeps its complete group and identity. The finite ledger
records structural source judgments, not sentence meanings or independent review.
"""

import argparse
import json
import re
import subprocess

from continuation_inflection_audit import project_lmf
from lexical_nada_audit import ROOT, load_dictionary, read, run, sha, write
from native_lmf import verify_native_lmf

SOURCE = ROOT / "docs/rya-boundary-source-preflight.json.gz"
FIXTURE = ROOT / "tests/fixtures/rya-boundary-sources.json"
LMF = ROOT / "tests/fixtures/krdict-rya-boundary.json"
CORE = [
    "krdict:79260",
    "krdict:79261",
    "krdict:80306",
    "krdict:80308",
    "krdict:85785",
    "krdict:86543",
    "krdict:86552",
    "krdict:86555",
    "krdict:86116",
]
PATTERN = r"(?<![가-힣])([가-힣]+(?:으랴마는|랴마는|으랴만|랴만|으랴|랴))(?![가-힣])"
GUIDANCE = "https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=296131"

# Exact native final targets: repeated connective sequences retain separate words.
TARGETS = {
    "배부르랴": (["배부르다"], ["predicate"], []),
    "아니랴": (["아니다"], ["predicate"], []),
    "지키랴": (["지키다"], ["predicate"], []),
    "지랴": (["지다"], ["predicate"], []),
    "나랴": (["나다"], ["predicate"], []),
    "하랴": (["하다"], ["predicate"], []),
    "주랴": (["주다"], ["predicate"], []),
    "챙기랴": (["챙기다"], ["predicate"], []),
    "잊으랴": (["잊다"], ["predicate"], []),
    "막으랴": (["막다"], ["predicate"], []),
    "갚으랴": (["갚다"], ["predicate"], []),
    "잘했으랴": (["잘하다"], ["predicate"], ["었"]),
    "숨었으랴": (["숨다"], ["predicate"], ["었"]),
    "놓으랴": (["놓다"], ["predicate"], []),
    "찾으랴": (["찾다"], ["predicate"], []),
    "먹으랴": (["먹다"], ["predicate"], []),
    "잡으랴": (["잡다"], ["predicate"], []),
    "받으랴": (["받다"], ["predicate"], []),
    "노래하랴": (["노래하다"], ["predicate"], []),
    "마시랴": (["마시다"], ["predicate"], []),
    "들으랴": (["듣다"], ["predicate"], []),
    "적으랴": (["적다"], ["predicate"], []),
    "돌보랴": (["돌보다"], ["predicate"], []),
    "시중들랴": (["시중들다"], ["predicate"], []),
    "일하랴": (["일하다"], ["predicate"], []),
    "공부하랴": (["공부하다"], ["predicate"], []),
    "다니랴": (["다니다"], ["predicate"], []),
    "살림하랴": (["살림하다"], ["predicate"], []),
    "있으랴마는": (["있다"], ["predicate"], []),
    "좋으랴마는": (["좋다"], ["predicate"], []),
    "않으랴마는": (["않다"], ["predicate"], []),
    "알랴마는": (["알다"], ["predicate"], []),
    "몫이랴마는": (["몫", "이다"], ["nominal", "copula"], []),
    "비기랴마는": (["비기다"], ["predicate"], []),
    "되랴마는": (["되다"], ["predicate"], []),
    "움직이랴마는": (["움직이다"], ["predicate"], []),
}
EXTRA = {
    "알랴만": (["알다"], ["predicate"], [], ["으랴", "만"]),
    "있으랴만": (["있다"], ["predicate"], [], ["으랴", "만"]),
    "학생이랴마는": (["학생", "이다"], ["nominal", "copula"], [], ["으랴", "마는"]),
    "의사이랴마는": (["의사", "이다"], ["nominal", "copula"], [], ["으랴", "마는"]),
    "들으랴마는": (["듣다"], ["predicate"], [], ["으랴", "마는"]),
    "도우랴마는": (["돕다"], ["predicate"], [], ["으랴", "마는"]),
    "지으랴마는": (["짓다"], ["predicate"], [], ["으랴", "마는"]),
    "살랴마는": (["살다"], ["predicate"], [], ["으랴", "마는"]),
    "나셨으랴마는": (["나다"], ["predicate"], ["시", "었"], ["으랴", "마는"]),
    "나겠으랴만": (["나다"], ["predicate"], ["겠"], ["으랴", "만"]),
    "먹어보랴마는": (
        ["먹다", "보다"],
        ["predicate", "auxiliary"],
        [],
        ["어", "으랴", "마는"],
    ),
    "먹고싶으랴마는": (
        ["먹다", "싶다"],
        ["predicate", "auxiliary"],
        [],
        ["고", "으랴", "마는"],
    ),
    "먹지않으랴마는": (
        ["먹다", "않다"],
        ["predicate", "auxiliary"],
        [],
        ["지", "으랴", "마는"],
    ),
}
UNKNOWN = {
    "먹더랴": "먹다",
    "먹사오랴": "먹다",
    "먹으오랴": "먹다",
    "먹고있더랴": "있다",
    "먹지않더랴": "않다",
    "학생이더랴": "이다",
}
NEGATIVE = {
    "먹랴마는": "먹다",
    "나으랴마는": "나다",
    "살으랴마는": "살다",
    "좋랴마는": "좋다",
    "학생랴마는": "이다",
    "먹으랴요": "먹다",
    "학생마는": "학생",
    "먹음마는": "먹다",
}


def discoveries(entries):
    rows = []
    for ident, entry in sorted(entries.items()):
        for sense in entry["senses"]:
            for group_index, group in enumerate(sense["examples"], 1):
                for text_index, text in enumerate(group):
                    for match in re.finditer(PATTERN, text):
                        start, end = match.span(1)
                        rows.append(
                            {
                                "id": f"rya-source-{ident}-{sense['id']}-{group_index}-{text_index}-{start}-{end}",
                                "entry": ident,
                                "sense": sense["id"],
                                "group": group_index,
                                "text_index": text_index,
                                "span": {
                                    "start": len(text[:start].encode()),
                                    "end": len(text[:end].encode()),
                                },
                                "surface": match[1],
                                "complete_group": group,
                                "contextual_verdict": "unjudged",
                                "independent_review": "pending",
                            }
                        )
    return rows


def cases():
    rows = []
    for surface, (heads, kinds, prefinals) in TARGETS.items():
        forms = prefinals + ["으랴"] + (["마는"] if surface.endswith("마는") else [])
        rows.append(
            {
                "id": "rya-native-" + surface,
                "surface": surface,
                "verdict": "required",
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": forms,
            }
        )
    for surface, (heads, kinds, prefinals, forms) in EXTRA.items():
        rows.append(
            {
                "id": "rya-composition-" + surface,
                "surface": surface,
                "verdict": "required",
                "lemmas": heads,
                "lemma_kinds": kinds,
                "morphemes": prefinals + forms,
            }
        )
    for surface, head in NEGATIVE.items():
        rows.append(
            {
                "id": "rya-boundary-" + surface,
                "surface": surface,
                "verdict": "forbidden",
                "lemma": head,
            }
        )
    for surface, head in UNKNOWN.items():
        rows.append(
            {
                "id": "rya-unreviewed-" + surface,
                "surface": surface,
                "verdict": "unknown_entry",
                "lemma": head,
            }
        )
    return rows


def freeze(args):
    assert not any(p.exists() for p in [SOURCE, FIXTURE, LMF]), (
        "Refusing to replace source/before evidence"
    )
    dictionary = load_dictionary(args.dictionary)
    assert len(dictionary) == 56555
    prior = read(ROOT / "docs/lexical-nada-observations.json.gz")
    assert (
        sha(args.cli_before) == prior["cli_sha256"]
        and sha(args.dictionary) == prior["dictionary_sha256"]
    )
    hits = discoveries(dictionary)
    surfaces = set(TARGETS) | set(EXTRA) | set(UNKNOWN) | set(NEGATIVE)
    surfaces.update(h["surface"] for h in hits if h["entry"] in CORE)
    surfaces.update(s[:-2] for s in surfaces.copy() if s.endswith("마는"))
    surfaces.update(s[:-1] for s in surfaces.copy() if s.endswith("만"))
    text, before = run(args.cli_before, args.dictionary, sorted(surfaces))
    used = set(CORE) | {h["entry"] for h in hits}
    used.update(
        e["id"]
        for record in before["all"]
        if record["kind"] == "word"
        for slot in record["dictionary"]["lemmas"]
        for e in slot["entries"]
    )
    native = {ident: dictionary[ident] for ident in sorted(used)}
    # Full sources for discovery contexts are separate from the smaller LMF test adapter.
    required = set(CORE)
    required.update(
        e["id"]
        for record in before["all"]
        if record["kind"] == "word"
        for slot in record["dictionary"]["lemmas"]
        for e in slot["entries"]
    )
    for heads, *_ in list(TARGETS.values()) + list(EXTRA.values()):
        required.update(e["id"] for e in dictionary.values() if e["headword"] in heads)
    native.update({ident: dictionary[ident] for ident in sorted(required)})
    selected = {ident: dictionary[ident] for ident in sorted(required)}
    raw, hashes = project_lmf(selected)
    LMF.write_text(
        json.dumps(
            {"LexicalResource": {"Lexicon": {"LexicalEntry": list(raw.values())}}},
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    write(
        SOURCE,
        {
            "schema_version": 1,
            "checklist": "COV-017br",
            "before_revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "cli_sha256": sha(args.cli_before),
            "dictionary_sha256": sha(args.dictionary),
            "previous_observations_sha256": sha(
                ROOT / "docs/lexical-nada-observations.json.gz"
            ),
            "pattern": PATTERN,
            "entries_scanned": len(dictionary),
            "complete_native_entries": native,
            "discoveries": hits,
            "before_input": text,
            "before_streams": before,
            "core_entries": CORE,
            "primary_guidance": {
                "url": GUIDANCE,
                "answered": "2024-05-07",
                "finding": "NIKL lists final -랴 among the endings preceding concessive 마는; 만은 in the separately questioned contexts requires whole-context review.",
            },
            "license": "National Institute of Korean Language, Korean Basic Dictionary; CC BY-SA 2.0 KR. Full native groups, notes and all translation languages retained.",
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        },
    )
    fixture = {
        "schema_version": 1,
        "checklist": "COV-017br",
        "source_sha256": sha(SOURCE),
        "lmf_sha256": sha(LMF),
        "raw_source_sha256": hashes,
        "native_entry_ids": sorted(required),
        "cases": cases(),
        "scope": "Exact native rhetorical/offer/enumerative targets; source-listed concessive 마는 and short 만, scoped composition and exclusions. Other prefinals remain hypotheses with unreviewed attachment, never globally banned. All contextual meanings and independent review remain pending.",
    }
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")


def verify():
    source, fixture = read(SOURCE), read(FIXTURE)
    assert fixture["source_sha256"] == sha(SOURCE) and fixture["lmf_sha256"] == sha(LMF)
    assert fixture["cases"] == cases()
    assert source["core_entries"] == CORE and source["pattern"] == PATTERN
    assert source["previous_observations_sha256"] == sha(
        ROOT / "docs/lexical-nada-observations.json.gz"
    )
    assert source["discoveries"] == discoveries(source["complete_native_entries"])
    assert len({h["id"] for h in source["discoveries"]}) == len(source["discoveries"])
    for h in source["discoveries"]:
        e = source["complete_native_entries"][h["entry"]]
        sense = next(s for s in e["senses"] if s["id"] == h["sense"])
        assert sense["examples"][h["group"] - 1] == h["complete_group"]
        text = h["complete_group"][h["text_index"]]
        assert (
            text.encode()[h["span"]["start"] : h["span"]["end"]].decode()
            == h["surface"]
        )
    selected = {
        ident: source["complete_native_entries"][ident]
        for ident in fixture["native_entry_ids"]
    }
    verify_native_lmf(read(LMF), selected)
    for record in source["before_streams"]["all"]:
        if record["kind"] == "word":
            for slot in record["dictionary"]["lemmas"]:
                for e in slot["entries"]:
                    native = source["complete_native_entries"][e["id"]]
                    assert all(
                        e[k] == native[k] for k in ["id", "headword", "homonym", "pos"]
                    )
    print(
        f"{len(source['discoveries'])} full native discoveries, {len(selected)} LMF owners, {len(cases())} finite cases and {len([r for r in source['before_streams']['all'] if r['kind'] == 'word'])} original words preserved; contextual verdicts unjudged"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--cli-before", type=type(ROOT))
    parser.add_argument("--dictionary", type=type(ROOT))
    args = parser.parse_args()
    if args.verify:
        verify()
    elif args.cli_before and args.dictionary:
        freeze(args)
        verify()
    else:
        parser.error("freeze requires --cli-before and --dictionary")
