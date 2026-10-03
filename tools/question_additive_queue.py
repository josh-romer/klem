"""Verify individual alternatives from the frozen question/additive runtime audit."""
import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def report():
    fixture = ROOT / "tests/fixtures/question-additive-sources.json"
    runtime = ROOT / "docs/question-additive-runtime.json.gz"
    source = json.loads(fixture.read_text())
    with gzip.open(runtime, "rt") as file:
        evidence = json.load(file)
    assert evidence["source_sha256"] == sha(fixture)
    paths = evidence["new_paths"]
    assert len({p["id"] for p in paths}) == len(paths)
    assert paths and sum(bool(p["judgments"]) for p in paths) == 13
    for item in paths:
        word = evidence["words"][item["surface"]]
        assert word["all"]["analyses"][item["raw_index"]] == item["analysis"]
        assert word["all"]["dictionary"]["readings"][item["raw_index"]] == item["assessment"]
        assert word["api"]["breakdowns"][0][item["raw_index"]] == item["breakdown"]
        assert item["analysis"] not in source["before_words"][item["surface"]]["all"]["analyses"]
        assert item["headword_retained"] == (item["analysis"] in word["headword"]["analyses"])
        assert item["compatible_retained"] == (item["analysis"] in word["compatible"]["analyses"])
    compositions = Counter()
    for item in paths:
        if item["surface"].endswith("도"):
            compositions["literal_question_additive"] += 1
        else:
            assert item["surface"].endswith("도요")
            rules = item["analysis"]["rules"]
            outer = [r for r in ("particle.polite", "ending.enumerative_yo") if r in rules]
            assert len(outer) == 1
            compositions[outer[0]] += 1
    return dict(
        schema_version=1, checklist="COV-018ad", generator="tools/question_additive_queue.py",
        generator_sha256=sha(Path(__file__)), fixture_sha256=sha(fixture), runtime_sha256=sha(runtime),
        counts=evidence["counts"], composition_counts=dict(compositions), items=paths,
        limitation="Frozen newly emitted diagnostic paths. Thirteen named structures are required; every contextual interpretation remains unjudged. This does not enumerate or certify all Korean sentences. The complete broader stream comparison is retained separately in question-additive-observations.json.",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    current = report()
    if args.verify:
        assert current == json.loads((ROOT / "docs/question-additive-review-queue.json").read_text())
        print(f"{len(current['items'])} individual additive alternatives verified; 13 required structures; every contextual interpretation remains unjudged.")
    else:
        print(json.dumps(current, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
