"""Bind the actual packaged browser run to its script and runtime evidence."""

import argparse
import json
from pathlib import Path

from adjectival_allomorph_runtime import REPORT as RUNTIME
from lexical_nada_audit import ROOT, read, sha

SCRIPT = ROOT / "web/tests/adjectival-allomorph.mjs"
REPORT = ROOT / "docs/adjectival-allomorph-packaged-browser.json"
DIAGRAMS = {
    "예쁘냐고": (["예쁘", "냐고"], "냐고", {"76243", "87442"}),
    "기냐고": (["길", "냐고"], "냐고", {"76243", "87442"}),
    "좋으냐고": (["좋", "으냐고"], "으냐고", {"79258", "87444"}),
    "어떠냐": (["어떻", "으냐"], "으냐", {"76235"}),
    "아이다우냐": (["아이", "답", "으냐"], "으냐", {"76235"}),
    "학생이냐": (["학생", "이", "냐"], "냐", {"76230"}),
    "먹고계시냐면": (["먹", "고", "계시", "냐면"], "냐면", {"80177"}),
    "기냐는구나": (["길", "냐는구나"], "냐는구나", {"88945"}),
    "좋으냐는구나": (["좋", "으냐는구나"], "으냐는구나", {"88947"}),
}


def inspect(browser, runtime):
    assert browser["schema_version"] == 1
    assert browser["words"] == len(runtime["words"]) == 2050
    assert browser["errors"] == [] and browser["allExportsMatchCli"]
    assert browser["mobileNoHorizontalOverflow"]
    assert len(browser["checks"]) == 60
    for encoding in ("NFC", "NFD"):
        for mode in ("all", "headword", "compatible"):
            rows = [
                r
                for r in browser["checks"]
                if r["encoding"] == encoding and r["mode"] == mode
            ]
            end = 0
            for row in rows:
                assert row["start"] == end and row["passed"]
                assert 0 < row["words"] <= 250 and row["records"] >= row["words"]
                end += row["words"]
            assert end == len(runtime["words"])
    rendered = browser["rendered"]
    assert len(rendered) == len(DIAGRAMS)
    assert {r["word"] for r in rendered} == DIAGRAMS.keys()
    for row in rendered:
        forms, ending, entries = DIAGRAMS[row["word"]]
        assert row["forms"] == forms and row["ending"] == ending
        assert row["entry"] in entries and row["passed"]


def freeze(result, cli, output):
    assert not output.exists()
    browser, runtime = read(result), read(RUNTIME)
    inspect(browser, runtime)
    assert sha(cli) == runtime["cli_sha256"]
    report = {
        "schema_version": 1,
        "checklist": "COV-017bu",
        "runtime_sha256": sha(RUNTIME),
        "cli_sha256": sha(cli),
        "script_sha256": sha(SCRIPT),
        "original_browser_report_sha256": sha(result),
        "browser": browser,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        "Bound all 60 browser exports and nine source-linked diagrams to the tested package/script."
    )


def verify():
    report, runtime = read(REPORT), read(RUNTIME)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-017bu"
    assert report["runtime_sha256"] == sha(RUNTIME)
    assert report["script_sha256"] == sha(SCRIPT)
    assert report["cli_sha256"] == runtime["cli_sha256"]
    assert (
        report["contextual_verdict"] == "unjudged"
        and report["independent_review"] == "pending"
    )
    inspect(report["browser"], runtime)
    print(
        "Verified packaged browser evidence: all 2,050 words in both encodings/three filters and nine ordered source-linked diagrams."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--result", type=Path)
    parser.add_argument("--cli", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.verify:
        verify()
    else:
        assert args.result and args.cli and args.output
        freeze(args.result, args.cli, args.output)


if __name__ == "__main__":
    main()
