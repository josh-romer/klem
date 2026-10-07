"""Replay actual CLI source/broad streams and every original annotated word."""

import argparse, hashlib, json, subprocess, tempfile, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from reported_dana_corpora import ROOT, read, sha


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replay(command, expected_hash, expected_records, request=None):
    digest = hashlib.sha256()
    count = 0
    with tempfile.TemporaryFile() as input_file:
        if request is not None:
            input_file.write(request.encode())
            input_file.seek(0)
        process = subprocess.Popen(
            command, cwd=ROOT, stdin=input_file, stdout=subprocess.PIPE
        )
        try:
            for line in process.stdout:
                digest.update(line)
                count += 1
            code = process.wait()
            assert code == 0, (command, code)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()
    assert (digest.hexdigest(), count) == (expected_hash, expected_records), command
    return {
        "command": command,
        "exit_code": code,
        "sha256": digest.hexdigest(),
        "records": count,
    }


def capture(cli, output, evaluator=None):
    cli = Path(cli).resolve()
    output = Path(output)
    assert not output.exists()
    paths = [
        "docs/reported-dana-prototype-source-streams.json.gz",
        "docs/reported-dana-prototype-corpora.json.gz",
        "docs/reported-dana-prototype-broad.json.gz",
    ]
    frozen = {name: sha(name) for name in paths}
    dictionary = ROOT / "data/dictionaries/krdict/krdict.db"
    binaries = {str(path): file_sha(path) for path in [cli, dictionary]}
    source = read(paths[0])
    source_runs = []
    for encoding, modes in source["runs"].items():
        request = unicodedata.normalize(encoding, source["input"])
        for mode, stages in modes.items():
            old = stages["after"]
            result = replay(
                [str(cli), *old["command"][1:]],
                old["sha256"],
                len(old["jsonl"].splitlines()),
                request,
            )
            source_runs.append(
                {
                    "encoding": encoding,
                    "mode": mode,
                    "input_sha256": hashlib.sha256(request.encode()).hexdigest(),
                    **result,
                }
            )
            print("source", encoding, mode, result["records"], flush=True)
    broad_runs = []
    for old in read(paths[2])["comparisons"]:
        assert file_sha(old["source"]) == old["source_sha256"]
        frozen[old["source"]] = old["source_sha256"]
        result = replay(
            [str(cli), *old["commands"][1][1:]],
            old["after_jsonl_sha256"],
            old["records"],
        )
        broad_runs.append(
            {key: old[key] for key in ["source", "source_sha256", "mode"]} | result
        )
        print("broad", old["mode"], result["records"], flush=True)
    corpus = read(paths[1])
    words = words_from_cli(cli, sorted(corpus["after_words"]))
    assert words == corpus["after_words"] and len(words) == 32096
    references = []
    evaluator_runs = []
    if evaluator is not None:
        evaluator = Path(evaluator).resolve()
        assert evaluator.is_file()
        binaries[str(evaluator)] = file_sha(evaluator)
    for old in corpus["corpora"]:
        # Historical paths refer to the original unchanged corpus files.
        corpus_source = Path(old["command"][2])
        if not corpus_source.is_absolute():
            corpus_source = Path("/home/josh/projects/klem") / corpus_source
        assert file_sha(corpus_source) == old["source_sha256"]
        frozen[str(corpus_source)] = old["source_sha256"]
        references.append(
            {
                key: old[key]
                for key in [
                    "corpus",
                    "partition",
                    "source",
                    "source_sha256",
                    "report_lines",
                ]
            }
            | {
                "reference_evaluator_jsonl_sha256": hashlib.sha256(
                    old["after_jsonl"].encode()
                ).hexdigest()
            }
        )
        if evaluator is not None:
            # Preserve the original relative input header; use the original workspace cwd.
            result = subprocess.run(
                [str(evaluator), old["corpus"], old["source"]],
                cwd="/home/josh/projects/klem",
                capture_output=True,
                check=True,
            )
            assert (
                hashlib.sha256(result.stdout).hexdigest()
                == references[-1]["reference_evaluator_jsonl_sha256"]
            )
            assert len(result.stdout.splitlines()) == old["report_lines"]
            evaluator_runs.append(
                {
                    "command": result.args,
                    "exit_code": result.returncode,
                    "sha256": hashlib.sha256(result.stdout).hexdigest(),
                    "records": old["report_lines"],
                }
            )
    assert (
        len(source_runs) == 6 and sum(run["records"] for run in source_runs) == 247698
    )
    assert len(broad_runs) == 8 and sum(run["records"] for run in broad_runs) == 1128312
    assert (
        len(references) == 4
        and sum(run["report_lines"] - 1 for run in references) == 66570
    )
    assert all(sha(name) == value for name, value in frozen.items())
    assert all(file_sha(path) == value for path, value in binaries.items())
    producer = Path(__file__)
    report = {
        "schema_version": 1,
        "state": "passed",
        "inputs_unchanged": True,
        "source_runs": source_runs,
        "broad_runs": broad_runs,
        "corpus_words": len(words),
        "corpus_word_sha256": hashlib.sha256(
            json.dumps(words, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest(),
        "corpus_reference_runs": references,
        "evaluator_runs": evaluator_runs,
        "corpus_validation": {
            "method": "Actual evaluator parity and full WordAnalysis equality."
            if evaluator is not None
            else "Exact CLI WordAnalysis equality for every original gold surface, tied to independently verified captured evaluator results; no evaluator execution claimed.",
            "verified_gold_rows": 66570,
        },
        "frozen_inputs": frozen,
        "binaries": binaries,
        "producer": {"text": producer.read_text(), "sha256": file_sha(producer)},
        "scope": "Actual source/broad stream and complete corpus-word parity. Evaluator executions, when requested, are recorded separately; prior source-cohort retention is a separate gate. Contextual and independent judgments remain open.",
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        "Actual CLI source6/broad8/fullWords32096 parity passed; evaluator runs:",
        len(evaluator_runs),
        flush=True,
    )


def words_from_cli(cli, surfaces):
    text = "\n".join(surfaces) + "\n"
    result = subprocess.run(
        [str(cli), "text", "-"], input=text, text=True, capture_output=True, check=True
    )
    records = [json.loads(line) for line in result.stdout.splitlines() if line]
    assert "".join(r["surface"] for r in records) == text
    starts = {}
    offset = 0
    for surface in surfaces:
        starts[offset] = surface
        offset += len(surface.encode()) + 1
    whole = {
        r["surface"]: r["analysis"]
        for r in records
        if r["kind"] == "word"
        and starts.get(r["span"]["start"]) == r["surface"]
        and r["span"]["end"] == r["span"]["start"] + len(r["surface"].encode())
    }
    missing = [s for s in surfaces if s not in whole]

    # CoNLL-U tokens can contain punctuation. Preserve the exact original
    # word interface for them rather than rewriting gold token boundaries.
    def analyze(surface):
        out = subprocess.run(
            [str(cli), "word", surface], text=True, capture_output=True, check=True
        )
        return surface, json.loads(out.stdout)

    with ThreadPoolExecutor(max_workers=4) as pool:
        whole.update(pool.map(analyze, missing))
    assert set(whole) == set(surfaces)
    print(
        len(surfaces) - len(missing),
        "exact text tokens and",
        len(missing),
        "punctuation-bearing original word calls",
        flush=True,
    )
    return whole


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--evaluator")
    args = parser.parse_args()
    capture(args.cli, args.output, args.evaluator)
