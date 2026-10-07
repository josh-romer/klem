"""Match every actual packaged legacy stream to the independently audited capture."""

import argparse
import hashlib
import json
from pathlib import Path
from reported_dana_corpora import ROOT, read, sha
from reported_dana_legacy import specifications
from reported_dana_production import file_sha, replay


def capture(cli, output):
    cli = Path(cli).resolve()
    output = Path(output)
    assert not output.exists()
    previous_path = "docs/reported-dana-prototype-legacy.json.gz"
    previous = read(previous_path)
    frozen = {previous_path: sha(previous_path)}
    specs, paths = specifications()
    frozen.update({name: sha(name) for name in paths})
    cli_sha = file_sha(cli)
    dictionary = ROOT / "data/dictionaries/krdict/krdict.db"
    dictionary_sha = file_sha(dictionary)
    runs = []
    for spec, old in zip(specs, previous["comparisons"], strict=True):
        assert all(
            spec[key] == old[key] for key in ["family", "encoding", "mode", "records"]
        )
        result = replay(
            [str(cli), *spec["arguments"]],
            old["after_sha256"],
            old["records"],
            spec["input"],
        )
        runs.append(
            {key: old[key] for key in ["family", "encoding", "mode", "input_sha256"]}
            | result
        )
        print(
            "packaged legacy",
            old["family"],
            old["encoding"],
            old["mode"],
            result["records"],
            flush=True,
        )
    assert len(runs) == 18 and sum(run["records"] for run in runs) == 688434
    assert file_sha(cli) == cli_sha and file_sha(dictionary) == dictionary_sha
    assert all(sha(name) == value for name, value in frozen.items())
    producer = Path(__file__)
    report = {
        "schema_version": 1,
        "state": "passed",
        "inputs_unchanged": True,
        "runs": runs,
        "cli": str(cli),
        "cli_sha256": cli_sha,
        "dictionary_sha256": dictionary_sha,
        "frozen_inputs": frozen,
        "producer": {
            "text": producer.read_text(),
            "sha256": hashlib.sha256(producer.read_bytes()).hexdigest(),
        },
        "scope": "Actual packaged CLI equality for all18 independently reconstructed earlier source streams,688434frames. Existing paths/order/readings/byte spans and20 individual additions transfer by exact full-stream equality; contextual and independent review remain unjudged.",
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    capture(args.cli, args.output)
