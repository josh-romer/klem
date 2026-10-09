"""Audit complete workload receipts and every individual novel addition."""

import gzip
import hashlib
import json
from pathlib import Path

from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith(".gz") else raw)


def inspect(report, prior, sources, native, entries):
    assert report["state"] == "draft-complete-broad-preservation-passed"
    assert report["inputs_unchanged"] and not report["full_coverage_complete"]
    projected = {}
    for raw in native["LexicalResource"]["Lexicon"]["LexicalEntry"]:
        value = entry(raw)
        assert value["id"] not in projected, "Native identity collision"
        projected[value["id"]] = value
    assert projected == entries and len(projected) == 4, "complete original Native owners"
    assert len(report["comparisons"]) == len(prior["comparisons"]) == 8, "all original workloads"
    assert sum(r["records"] for r in report["comparisons"]) == 1128312, "complete original frames"
    assert report["individual_spacing_additions"] == [] and report["independent_spacing_replay"] == {}, "no new spacing boundaries"
    observations = []
    for run, previous in zip(report["comparisons"], prior["comparisons"], strict=True):
        assert (run["source"], run["source_sha256"], run["mode"], run["records"], run["before_jsonl_sha256"]) == (previous["source"], previous["source_sha256"], previous["mode"], previous["records"], previous["after_jsonl_sha256"]), "actual complete previous stream"
        assert run["exit_codes"] == [0, 0] and run["original_bytes_conserved"], "complete stream execution"
        original = sources["sources"][run["source"]]["text"].encode()
        assert hashlib.sha256(original).hexdigest() == run["source_sha256"], "complete original source text"
        previous_record = 0
        for changed in run["changed_frames"]:
            record = changed["record"]
            assert previous_record < record <= run["records"], "original frame ordering"
            previous_record = record
            before, after = changed["before"], changed["after"]
            assert {k: v for k, v in before.items() if k not in ["analysis", "dictionary", "breakdowns"]} == {k: v for k, v in after.items() if k not in ["analysis", "dictionary", "breakdowns"]}, "original frame fields and spacing"
            old, new = before["analysis"], after["analysis"]
            assert {k: v for k, v in old.items() if k != "analyses"} == {k: v for k, v in new.items() if k != "analyses"}, "original analysis fields"
            assert [p for p in new["analyses"] if p in old["analyses"]] == old["analyses"], "old candidate preservation and order"
            bd, ad = before["dictionary"], after["dictionary"]
            assert {k: v for k, v in bd.items() if k not in ["lemmas", "readings"]} == {k: v for k, v in ad.items() if k not in ["lemmas", "readings"]}, "dictionary identity"
            assert all(owner in ad["lemmas"] for owner in bd["lemmas"]), "original dictionary owners"
            for index, path in enumerate(old["analyses"]):
                next_index = new["analyses"].index(path)
                assert bd["readings"][index] == ad["readings"][next_index], "old dictionary assessments"
                if "breakdowns" in before:
                    assert before["breakdowns"][index] == after["breakdowns"][next_index], "old diagrams"
            span = after["span"]
            assert original[span["start"]:span["end"]].decode() == after["surface"], "original source span"
            left = original.rfind(b"\n", 0, span["start"]) + 1
            right = original.find(b"\n", span["end"])
            line = original[left:right if right >= 0 else len(original)].decode()
            assert changed["complete_original_line"] == line, "complete original context"
            additions = []
            for index, path in enumerate(new["analyses"]):
                if path in old["analyses"]:
                    continue
                assert "ending.question_dapnikka" in path["rules"], "new rule attribution"
                owners = [next(owner for owner in ad["lemmas"] if owner["lemma"] == lemma) for lemma in path["lemmas"]]
                for owner in owners:
                    for summary in owner["entries"]:
                        full = entries[summary["id"]]
                        assert all(summary[k] == full[k] for k in ["id", "headword", "homonym", "pos"]), "exact Native owner summary"
                addition = {"location": "word", "surface": after["surface"], "span": span, "analysis": path, "dictionary_assessment": ad["readings"][index], "dictionary_owners": owners, "contextual_verdict": "unjudged", "independent_review": "pending"}
                ident = hashlib.sha256(json.dumps([run["source_sha256"], run["mode"], record, addition], ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:24]
                additions.append({"id": "dapnikka-broad-" + ident, "source": run["source"], "source_sha256": run["source_sha256"], "mode": run["mode"], "record": record, "complete_original_line": line, **addition})
            assert len(additions) == changed["added_paths"] and changed["added_spacing_options"] == 0, "exact individual change counts"
            observations.extend(additions)
    assert observations == report["individual_additions"], "complete individual additions and evidence"
    assert len(observations) == len({o["id"] for o in observations}), "stable unique addition identities"
    owners = {e["id"] for o in observations for owner in o["dictionary_owners"] for e in owner["entries"]}
    assert owners == set(entries), "complete Native owner closure"
    return {"frames": 1128312, "individual_paths": len(observations), "native_entries": len(entries), "contextual_and_independent_review": "pending"}


def inputs():
    return [read(ROOT / name) for name in [
        "docs/dapnikka-broad-retry1.json.gz",
        "docs/self-question-broad-retry2.json.gz",
        "docs/reported-deoni-broad-inputs.json.gz",
        "tests/fixtures/dapnikka-novel-native.json",
        "tests/fixtures/dapnikka-novel-entries.json",
    ]]


if __name__ == "__main__":
    print(inspect(*inputs()))
