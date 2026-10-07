"""Capture exact packaged whole-novel cache parity in three dictionary modes."""

import argparse
import hashlib
import json
from pathlib import Path

from copula_expectation_production import ROOT, read, sha
from reported_dana_production import replay


def capture(output):
    output = Path(output)
    assert not output.exists()
    name = "docs/reported-dana-performance-inputs.json"
    package = read(name)
    cli = Path(package["nix_outputs"]["klem"]) / "bin/klem"
    book = ROOT / "data/books/mujeong.txt"
    dictionary = ROOT / "data/dictionaries/krdict/krdict.db"
    frozen = {str(path): sha(path) for path in [ROOT / name, cli, book, dictionary]}
    assert sha(cli) == package["cli_sha256"]
    assert sha(dictionary) == package["dictionary_sha256"]
    streams = []
    for mode, flags in [
        ("raw", []),
        ("headword", ["--dict-only"]),
        ("compatible", ["--dict-compatible"]),
    ]:
        expected = next(
            row for row in package["comparisons"] if row["mode"] == "novel-" + mode
        )
        assert sha(book) == expected["source_sha256"]
        checks = []
        for cache in [0, 8388608]:
            command = [
                str(cli),
                "text",
                str(book),
                "--dictionary",
                str(dictionary),
                *flags,
                "--cache-bytes",
                str(cache),
            ]
            check = replay(command, expected["after_jsonl_sha256"], expected["records"])
            assert check["records"] == 179112
            checks.append(check)
            print(mode, cache, check["records"], "exact frames", flush=True)
        streams.append({"mode": mode, "checks": checks})
    assert all(sha(path) == value for path, value in frozen.items())
    producer = Path(__file__)
    output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "state": "passed",
                "inputs_unchanged": True,
                "cli_sha256": sha(cli),
                "book_sha256": sha(book),
                "dictionary_sha256": sha(dictionary),
                "package_sha256": sha(ROOT / name),
                "streams": streams,
                "producer": {
                    "text": producer.read_text(),
                    "sha256": hashlib.sha256(producer.read_bytes()).hexdigest(),
                },
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    capture(parser.parse_args().output)
