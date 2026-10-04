"""Verify finite policy observations offline without rejudging source contexts."""

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from continuation_inflection_compare import Audit

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "docs/continuation-inflection-candidate-review.json.gz"
ARTIFACTS = [
    "docs/continuation-inflection-observations.json",
    "docs/continuation-inflection-novel-views.json",
    "docs/continuation-inflection-runtime.json.gz",
    "docs/continuation-inflection-packaged-runtime.json.gz",
]


def read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt") as file:
            return json.load(file)
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_observations():
    source = read(ROOT / "tests/fixtures/continuation-inflection-sources.json")
    extra = read(ROOT / "tests/fixtures/continuation-inflection-additional.json")
    frozen = dict(source["before_words"])
    frozen.update(extra["before_words"])
    observations = read(ROOT / ARTIFACTS[0])
    novel = read(ROOT / ARTIFACTS[1])
    runtime = read(ROOT / ARTIFACTS[2])
    package = read(ROOT / ARTIFACTS[3])
    assert len(frozen) == len(runtime["words"]) == len(package["words"]) == 367

    def without_elapsed(words):
        words = copy.deepcopy(words)
        for word in words.values():
            elapsed = word["api"].pop("elapsed_ms")
            assert isinstance(elapsed, (int, float)) and elapsed >= 0
        return words

    assert without_elapsed(runtime["words"]) == without_elapsed(package["words"])
    assert runtime["streams"] == package["streams"]
    assert len(runtime["streams"]) == 18
    assert (
        runtime["complete_native_api_entries"]
        == package["complete_native_api_entries"]
        == 328
    )
    assert observations["before_cli_sha256"] == source["cli_sha256"]
    assert observations["cli_sha256"] == runtime["cli_sha256"]
    assert novel["observations_sha256"] == sha(ROOT / ARTIFACTS[0])
    assert (
        runtime["dictionary_sha256"]
        == package["dictionary_sha256"]
        == source["dictionary_sha256"]
    )
    audit = Audit(
        Path("unused-before"), Path("unused-after"), Path("unused-db"), frozen
    )
    audit.after = {s: w["all"] for s, w in package["words"].items()}
    for item in novel["cases"]:
        assert (
            item["contextual_verdict"] == "unjudged"
            and item["independent_review"] == "pending"
        )
        audit.before[item["surface"]] = item["words"]["before"]["all"]
        audit.after[item["surface"]] = item["words"]["after"]["all"]
        raw = item["complete_original_paragraph"].encode()
        span, paragraph = item["span"], item["paragraph_span"]
        assert (
            raw[
                span["start"] - paragraph["start"] : span["end"] - paragraph["start"]
            ].decode()
            == item["surface"]
        )
        for mode in ["all", "headword", "compatible"]:
            audit.word(
                item["words"]["before"][mode],
                item["words"]["after"][mode],
                mode,
                {"cohort": "novel-view", "surface": item["surface"], "mode": mode},
            )
    for surface, modes in frozen.items():
        changed = []
        for mode in ["all", "headword", "compatible"]:
            current = package["words"][surface][mode]
            audit.word(
                modes[mode],
                current,
                mode,
                {"cohort": "diagnostic", "surface": surface, "mode": mode},
            )
            if modes[mode] != current:
                changed.append(mode)
        saved = next(d for d in observations["diagnostics"] if d["surface"] == surface)
        assert saved["changed_modes"] == changed
    for name, generated in [
        ("entry_changes", audit.entries),
        ("filter_changes", audit.memberships),
    ]:
        expected = {
            c["id"]: {k: v for k, v in c.items() if k != "occurrences"}
            for c in generated.values()
        }
        saved = {
            c["id"]: {k: v for k, v in c.items() if k != "occurrences"}
            for c in observations[name]
        }
        assert expected == saved, name
    assert len(observations["entry_changes"]) == 619
    assert len(observations["filter_changes"]) == 113
    assert observations["spacing_changes"] == []
    assert sum(c["records"] for c in observations["comparisons"]) == 1128312
    assert len(observations["comparisons"]) == 8
    for c in observations["comparisons"]:
        assert c["changed_records"] == (0 if c["mode"].startswith("candidate") else 1)
        if c["changed_records"] == 0:
            assert c["before_jsonl_sha256"] == c["after_jsonl_sha256"]
    assert observations["raw_candidates_and_native_fields_preserved"]
    assert observations["all_baseline_stream_hashes_verified"]
    cases = observations["entry_changes"] + observations["filter_changes"]
    assert len(cases) == len({c["id"] for c in cases}) == 732
    assert all(
        c["contextual_verdict"] == "unjudged" and c["independent_review"] == "pending"
        for c in cases
    )
    return {
        "schema_version": 1,
        "checklist": "COV-019ae",
        "artifact_sha256": {p: sha(ROOT / p) for p in ARTIFACTS},
        "cases": cases,
        "scope": "Finite per-entry and filter observations, preserving original source/corpus context. Stable IDs do not imply contextual correctness or independent review.",
        "contextual_verdict": "unjudged",
        "independent_review": "pending",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    actual = verify_observations()
    if args.verify:
        assert read(QUEUE) == actual
    else:
        assert not QUEUE.exists(), "Refusing to overwrite individual observations"
        QUEUE.write_bytes(
            gzip.compress(
                json.dumps(actual, ensure_ascii=False, indent=2).encode(), mtime=0
            )
        )
    print(
        "732 individual candidate/filter observations verified; contextual and independent reviews remain pending"
    )


if __name__ == "__main__":
    main()
