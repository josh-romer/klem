"""Track every omitted-copula Rya hypothesis and preserve all old assessments.

Preserve every prior path/order/conflict and all native fields. Keep contextual
interpretations unjudged; the report is an engineering/source review queue.
"""

import argparse
import gzip
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

from lexical_nada_audit import read
from lexical_nada_compare import Audit, canon, native_owners, sha

ROOT = Path.cwd()
SOURCE = ROOT / "docs/rya-copula-source-preflight.json.gz"


class CopulaAudit(Audit):
    def remember(self, category, surface, before, after, location):
        super().remember(category, surface, before, after, location)
        row = self.changes[canon([category, surface, before, after])]
        row["id"] = (
            "rya-copula-"
            + category
            + "-"
            + hashlib.sha256(
                canon([category, surface, before, after]).encode()
            ).hexdigest()[:24]
        )

    def word(self, before, after):
        added = super().word(before, after)
        for a in added:
            assert "copula.omitted_rya" in a["rules"]
            assert "copula.omitted_ending" in a["rules"]
            assert any(
                l["kind"] == "copula" and l["text"] == "이다" for l in a["lemmas"]
            )
            index = after["analyses"].index(a)
            slots = after["dictionary"]["readings"][index]["lemmas"]
            for i, lemma in enumerate(a["lemmas"]):
                if lemma["kind"] == "copula":
                    assert all(e["status"] != "compatible" for e in slots[i]["entries"])
        return added

    def record(self, before, after, mode, location):
        self.location = location
        self.outer_surface = after["surface"]
        return super().record(before, after, mode, location)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--before-cli", type=Path, required=True)
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    before, cli = a.before_cli.resolve(), a.cli.resolve()
    db = ROOT / "data/dictionaries/krdict/krdict.db"
    source = read(SOURCE)
    assert (
        sha(before) == source["cli_sha256"] and sha(db) == source["dictionary_sha256"]
    )
    review = read(ROOT / "docs/lexical-nada-source-review.json")
    audit = CopulaAudit(
        cli, db, {p["noun"]: p["noun_entry"] for p in review["finite_pair_proposals"]}
    )
    prior = read(ROOT / "docs/rya-boundary-observations.json.gz")
    comparisons = []
    diagnostics = []
    for mode, flags in [
        ("all", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ]:
        command = ["text", "-", "--dictionary", str(db), "--suggest-spacing", *flags]
        outputs = [
            subprocess.check_output(
                [str(c), *command], input=source["before_input"].encode()
            )
            for c in [before, cli]
        ]
        records = [list(map(json.loads, output.splitlines())) for output in outputs]
        assert records[0] == source["before_streams"][mode]
        changed = 0
        for index, (old, new) in enumerate(zip(*records, strict=True)):
            if old == new:
                continue
            changed += 1
            audit.record(
                old,
                new,
                "diagnostic-" + mode,
                {
                    "mode": "diagnostic-" + mode,
                    "record": index,
                    "span": new["span"],
                    "context": new["surface"],
                    "source_discovery_ids": [
                        h["id"]
                        for h in source["native_discoveries"]
                        + source["novel"]["discoveries"]
                        if h["surface"] == new["surface"]
                    ],
                },
            )
        diagnostics.append(
            {
                "mode": "diagnostic-" + mode,
                "records": len(records[0]),
                "before_jsonl_sha256": hashlib.sha256(outputs[0]).hexdigest(),
                "after_jsonl_sha256": hashlib.sha256(outputs[1]).hexdigest(),
                "changed_records": changed,
            }
        )
        print(
            mode,
            len(records[0]),
            "source diagnostic records;",
            changed,
            "changed",
            flush=True,
        )
    for old in prior["comparisons"]:
        mode, path = old["mode"], Path(old["source"])
        assert sha(path) == old["source_sha256"]
        text = path.read_bytes()
        flags = (
            ["--dict-compatible"]
            if "compatible" in mode
            else ["--dict-only"]
            if "headword" in mode
            else []
        )
        cmd = ["text", str(path), "--dictionary", str(db), *flags] + (
            ["--suggest-spacing"] if "spacing" in mode else []
        )
        procs = [
            subprocess.Popen([str(c), *cmd], stdout=subprocess.PIPE)
            for c in [before, cli]
        ]
        hashes = [hashlib.sha256(), hashlib.sha256()]
        count = changed = 0
        try:
            for b, after in itertools.zip_longest(*(p.stdout for p in procs)):
                assert b is not None and after is not None
                hashes[0].update(b)
                hashes[1].update(after)
                if b != after:
                    br, ar = json.loads(b), json.loads(after)
                    span = ar["span"]
                    context = text[
                        max(0, span["start"] - 120) : min(len(text), span["end"] + 120)
                    ].decode(errors="replace")
                    audit.record(
                        br,
                        ar,
                        mode,
                        {
                            "mode": mode,
                            "record": count,
                            "span": span,
                            "context": context,
                        },
                    )
                    changed += 1
                count += 1
                if count % 25000 == 0:
                    print(mode, count, "records checked", flush=True)
            assert all(proc.wait() == 0 for proc in procs)
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait()
        assert (
            count == old["records"]
            and hashes[0].hexdigest() == old["after_jsonl_sha256"]
        )
        comparisons.append(
            {
                "mode": mode,
                "source": str(path),
                "source_sha256": sha(path),
                "records": count,
                "before_jsonl_sha256": hashes[0].hexdigest(),
                "after_jsonl_sha256": hashes[1].hexdigest(),
                "changed_records": changed,
            }
        )
        print(mode, count, "records;", changed, "changed", flush=True)
    value = {
        "schema_version": 1,
        "checklist": "COV-017br",
        "source_sha256": sha(SOURCE),
        "previous_observations_sha256": sha(
            ROOT / "docs/rya-boundary-observations.json.gz"
        ),
        "before_cli_sha256": sha(before),
        "cli_sha256": sha(cli),
        "dictionary_sha256": sha(db),
        "comparisons": comparisons,
        "diagnostics": diagnostics,
        "changes": list(audit.changes.values()),
        "complete_native_entries": native_owners(audit.changes.values(), db),
        "old_raw_paths_native_fields_and_known_conflicts_preserved": True,
        "old_spacing_options_and_order_preserved": True,
        "all_baseline_stream_hashes_verified": True,
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }
    a.output.write_bytes(
        gzip.compress(
            (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(), mtime=0
        )
    )
    print("Individual changes:", len(audit.changes), flush=True)


if __name__ == "__main__":
    main()
