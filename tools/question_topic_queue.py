"""Verify individual alternatives from the frozen question/topic runtime audit."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def report():
    fixture = ROOT / "tests/fixtures/question-topic-sources.json"
    runtime = ROOT / "docs/question-topic-runtime.json.gz"
    source = json.loads(fixture.read_text())
    with gzip.open(runtime, "rt") as file:
        evidence = json.load(file)
    assert evidence["source_sha256"] == sha(fixture)
    paths = evidence["new_paths"]
    assert len({p["id"] for p in paths}) == len(paths)
    assert len(paths) == 421 and sum(bool(p["judgments"]) for p in paths) == 11
    for item in paths:
        word = evidence["words"][item["surface"]]
        assert word["all"]["analyses"][item["raw_index"]] == item["analysis"]
        assert word["all"]["dictionary"]["readings"][item["raw_index"]] == item["assessment"]
        assert word["api"]["breakdowns"][0][item["raw_index"]] == item["breakdown"]
        assert item["analysis"] not in source["before_words"][item["surface"]]["all"]["analyses"]
        assert item["headword_retained"] == (item["analysis"] in word["headword"]["analyses"])
        assert item["compatible_retained"] == (item["analysis"] in word["compatible"]["analyses"])
    return dict(
        schema_version=1, checklist="COV-018ab", generator="tools/question_topic_queue.py",
        generator_sha256=sha(Path(__file__)), fixture_sha256=sha(fixture), runtime_sha256=sha(runtime),
        counts=evidence["counts"], items=paths,
        limitation="Frozen newly emitted diagnostic paths. Eleven named structures are required; every contextual interpretation remains unjudged. This does not enumerate or certify all Korean sentences. Additional broad-stream alternatives are retained separately in question-topic-observations.json.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = report()
    if args.verify:
        assert current == json.loads((ROOT / "docs/question-topic-review-queue.json").read_text())
        print("421 individual topic alternatives verified; 11 required structures and 410 structurally unjudged paths, with source/indices/components/assessments/filter memberships intact.")
    else:
        print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
