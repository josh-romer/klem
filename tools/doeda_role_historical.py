"""Preserve historical native-POS snapshots and explicitly track role additions."""

import argparse
import copy
import json
import subprocess
from pathlib import Path

from doeda_role_audit import SOURCE
from doeda_role_diagnostics import RULE
from lexical_nada_audit import ROOT, digest, read, sha

FIXTURE = ROOT / "tests/fixtures/doeda-role-historical.json"
ORIGINALS = [
    ROOT / "tests/fixtures/native-pos-sources.json",
    ROOT / "tests/fixtures/native-pos-boundaries.json",
]


def original_parent(analysis):
    result = copy.deepcopy(analysis)
    for index, lemma in enumerate(result["lemmas"]):
        if index > 0 and lemma == {"text": "되다", "kind": "predicate"}:
            lemma["kind"] = "auxiliary"
    result["rules"] = sorted((set(result["rules"]) - {RULE}) | {"auxiliary"})
    return result


def inspect(row):
    before, after = row["before"], row["after"]
    assert before["normalized"] == after["normalized"] == row["surface"]
    assert {k: v for k, v in before.items() if k != "analyses"} == {
        k: v for k, v in after.items() if k != "analyses"
    }
    old, new = before["analyses"], after["analyses"]
    assert [a for a in new if a in old] == old
    added = [a for a in new if a not in old]
    assert added and all(
        RULE in a["rules"] and original_parent(a) in old for a in added
    )
    assert row["added"] == [
        {
            "id": "doeda-role-historical-" + digest([row["surface"], a])[:24],
            "analysis": a,
            "contextual_verdict": "unjudged",
            "independent_review": "pending",
        }
        for a in added
    ]


def freeze(before_cli, cli):
    assert not FIXTURE.exists()
    source = read(SOURCE)
    assert sha(before_cli) == source["cli_sha256"]
    words = {}
    for path in ORIGINALS:
        for surface, frozen in read(path)["before_words"].items():
            if surface in words:
                assert words[surface]["original"] == frozen
            words.setdefault(surface, {"original": frozen, "original_paths": []})[
                "original_paths"
            ].append(str(path.relative_to(ROOT)))
    changes = []
    for surface, origin in sorted(words.items()):
        before, after = [
            json.loads(subprocess.check_output([str(c), "word", surface]))
            for c in (before_cli, cli)
        ]
        if before == after:
            continue
        row = {
            "surface": surface,
            **origin,
            "before": before,
            "after": after,
            "added": [
                {
                    "id": "doeda-role-historical-" + digest([surface, a])[:24],
                    "analysis": a,
                    "contextual_verdict": "unjudged",
                    "independent_review": "pending",
                }
                for a in after["analyses"]
                if a not in before["analyses"]
            ],
        }
        inspect(row)
        changes.append(row)
    fixture = {
        "schema_version": 1,
        "checklist": "COV-019ag",
        "source_sha256": sha(SOURCE),
        "original_fixture_sha256": {
            str(p.relative_to(ROOT)): sha(p) for p in ORIGINALS
        },
        "before_cli_sha256": sha(before_cli),
        "cli_sha256": sha(cli),
        "engine_sha256": sha(ROOT / "src/engine.rs"),
        "scope": "Explicit additions to historical native-POS cohorts. Original snapshots and all class judgments remain unchanged; the source-backed role alternatives have exact original raw parents. Earlier reviewed allomorph removals remain a separate overlay.",
        "changes": changes,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    FIXTURE.write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n")
    verify()


def verify():
    fixture, source = read(FIXTURE), read(SOURCE)
    assert fixture["schema_version"] == 1 and fixture["checklist"] == "COV-019ag"
    assert (
        fixture["source_sha256"] == sha(SOURCE)
        and fixture["before_cli_sha256"] == source["cli_sha256"]
    )
    assert fixture["original_fixture_sha256"] == {
        str(p.relative_to(ROOT)): sha(p) for p in ORIGINALS
    }
    for row in fixture["changes"]:
        inspect(row)
        for path in row["original_paths"]:
            assert read(ROOT / path)["before_words"][row["surface"]] == row["original"]
    assert (
        fixture["contextual_verdict"] == "unjudged"
        and fixture["independent_review"] == "pending"
    )
    print(
        f"Verified {len(fixture['changes'])} explicitly overlaid historical words and {sum(len(c['added']) for c in fixture['changes'])} individual role additions; original native-POS fixtures remain unchanged."
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--cli", type=Path)
    p.add_argument("--before-cli", type=Path)
    a = p.parse_args()
    if a.verify:
        verify()
    else:
        assert a.cli and a.before_cli
        freeze(a.before_cli.resolve(), a.cli.resolve())
