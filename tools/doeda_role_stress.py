"""Track role additions while retaining every original stress snapshot hash."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from doeda_role_audit import SOURCE
from doeda_role_diagnostics import RULE
from doeda_role_historical import inspect
from lexical_nada_audit import ROOT, digest, read, sha

ORIGINAL = ROOT / "tests/fixtures/optimization.json"
FIXTURE = ROOT / "tests/fixtures/doeda-role-stress.json"


def freeze(before_cli, cli):
    assert not FIXTURE.exists()
    assert sha(before_cli) == read(SOURCE)["cli_sha256"]
    changes = []
    for snapshot in read(ORIGINAL):
        # The scope is only an existing 되다 link. Avoid rerunning unrelated
        # expensive thousand-syllable snapshots as a new capture operation.
        if not any(
            form in snapshot["word"]
            for form in ("게되", "게돼", "게됐", "게끔되", "게끔돼", "게끔됐")
        ):
            continue
        payloads = [
            subprocess.check_output([str(c), "word", snapshot["word"]])
            for c in (before_cli, cli)
        ]
        before, after = [json.loads(p) for p in payloads]
        assert hashlib.sha256(payloads[0]).hexdigest() == snapshot["sha256"]
        if before == after:
            continue
        row = {
            "surface": snapshot["word"],
            "original_snapshot": snapshot,
            "before": before,
            "after": after,
            "before_jsonl_sha256": hashlib.sha256(payloads[0]).hexdigest(),
            "after_jsonl_sha256": hashlib.sha256(payloads[1]).hexdigest(),
            "added": [
                {
                    "id": "doeda-role-historical-" + digest([snapshot["word"], a])[:24],
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
    FIXTURE.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "checklist": "COV-019ag",
                "source_sha256": sha(SOURCE),
                "original_sha256": sha(ORIGINAL),
                "before_cli_sha256": sha(before_cli),
                "cli_sha256": sha(cli),
                "engine_sha256": sha(ROOT / "src/engine.rs"),
                "scope": "Exact stress role-addition overlay. The complete original snapshot records and all older grammar/spelling hashes remain unchanged; the new role candidates have original structural parents.",
                "changes": changes,
                "contextual_verdict": "unjudged",
                "independent_review": "pending",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
    verify()


def verify():
    fixture = read(FIXTURE)
    assert fixture["schema_version"] == 1 and fixture["checklist"] == "COV-019ag"
    assert fixture["source_sha256"] == sha(SOURCE) and fixture[
        "original_sha256"
    ] == sha(ORIGINAL)
    assert fixture["before_cli_sha256"] == read(SOURCE)["cli_sha256"]
    for row in fixture["changes"]:
        inspect(row)
        assert row["original_snapshot"] == next(
            r for r in read(ORIGINAL) if r["word"] == row["surface"]
        )
        assert row["before_jsonl_sha256"] == row["original_snapshot"]["sha256"]
        for name in ("before", "after"):
            payload = (
                json.dumps(
                    row[name], ensure_ascii=False, separators=(",", ":")
                ).encode()
                + b"\n"
            )
            assert hashlib.sha256(payload).hexdigest() == row[name + "_jsonl_sha256"]
        assert all(RULE in c["analysis"]["rules"] for c in row["added"])
    assert (
        fixture["contextual_verdict"] == "unjudged"
        and fixture["independent_review"] == "pending"
    )
    print(
        f"Verified {len(fixture['changes'])} stress snapshot overlays and {sum(len(c['added']) for c in fixture['changes'])} added role candidates; original optimization hashes preserved."
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
