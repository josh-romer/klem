"""Capture complete earlier source streams and attribute every new path to a real parent."""

import argparse
import gzip
import hashlib
import itertools
import json
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from reported_dana_corpora import ROOT, read, sha
from reported_dana_parent import actual_parent, frame
from reported_dana_production import file_sha

BASELINE = Path("/nix/store/p0xh9pk9m2nm8373vzicgdpx5w1yz6z7-klem-0.1.0/bin/klem")


def specifications():
    paths = [
        "docs/reported-deoni-prototype-source-streams.json.gz",
        "docs/reported-deoni-main-production.json",
        "docs/degree-rimankeum-cohort.json.gz",
        "docs/counterfactual-ryeon-cohort.json.gz",
    ]
    old = read(paths[0])
    specs = []
    for encoding, modes in old["runs"].items():
        request = unicodedata.normalize(encoding, old["input"])
        for mode, stages in modes.items():
            previous = stages["after"]
            specs.append(
                {
                    "family": "reported-deoni",
                    "encoding": encoding,
                    "mode": mode,
                    "input": request,
                    "expected_before_sha256": previous["sha256"],
                    "records": len(previous["jsonl"].splitlines()),
                    "arguments": previous["command"][1:],
                }
            )
    previous_production = json.loads((ROOT / paths[1]).read_bytes())
    for previous in previous_production["legacy_source_runs"]:
        original = read(f"docs/{previous['family']}-cohort.json.gz")
        request = unicodedata.normalize(previous["encoding"], original["input"])
        assert hashlib.sha256(request.encode()).hexdigest() == previous["input_sha256"]
        specs.append(
            {key: previous[key] for key in ["family", "encoding", "mode", "records"]}
            | {
                "input": request,
                "expected_before_sha256": previous["sha256"],
                "arguments": previous["command"][1:],
            }
        )
    assert len(specs) == 18 and sum(row["records"] for row in specs) == 688434
    assert len({(s["family"], s["encoding"], s["mode"]) for s in specs}) == 18
    return specs, paths


def parent_for(word, path, parents):
    candidates = {
        word[:at] + "다고" + word[at + len("다나") :]
        for at in range(len(word))
        if word.startswith("다나", at)
    }
    for candidate in sorted(candidates):
        if candidate not in parents:
            parents[candidate] = json.loads(
                subprocess.check_output([str(BASELINE), "word", candidate], cwd=ROOT)
            )
    return actual_parent(word, path, parents)


def capture(cli, output):
    cli = Path(cli).resolve()
    output = Path(output)
    assert not output.exists()
    specs, paths = specifications()
    source = read("docs/reported-dana-prototype-source-streams.json.gz")
    assert file_sha(BASELINE) == source["frozen_inputs"][str(BASELINE)]
    frozen = {name: sha(name) for name in paths}
    frozen["docs/reported-dana-prototype-source-streams.json.gz"] = sha(
        "docs/reported-dana-prototype-source-streams.json.gz"
    )
    binaries = {
        str(path): file_sha(path)
        for path in [BASELINE, cli, ROOT / "data/dictionaries/krdict/krdict.db"]
    }
    parents = {}
    comparisons = []
    observations = []
    native_ids = set()
    for spec in specs:
        raw = spec["input"].encode()
        commands = [[str(binary), *spec["arguments"]] for binary in [BASELINE, cli]]
        files = []
        jobs = []
        hashes = [hashlib.sha256(), hashlib.sha256()]
        changed = []
        offset = count = 0
        try:
            for command in commands:
                request = tempfile.TemporaryFile()
                files.append(request)
                request.write(raw)
                request.seek(0)
                jobs.append(
                    subprocess.Popen(
                        command, cwd=ROOT, stdin=request, stdout=subprocess.PIPE
                    )
                )
            for pair in itertools.zip_longest(*(job.stdout for job in jobs)):
                assert all(line is not None for line in pair), "unequal frame counts"
                count += 1
                for digest, line in zip(hashes, pair, strict=True):
                    digest.update(line)
                after = json.loads(pair[1])
                span = after["span"]
                assert (
                    span["start"] == offset
                    and raw[span["start"] : span["end"]].decode() == after["surface"]
                )
                offset = span["end"]
                if pair[0] == pair[1]:
                    continue
                before = json.loads(pair[0])
                assert after["kind"] == "word"
                word = after["analysis"]["normalized"]
                for path in after["analysis"]["analyses"]:
                    if path not in before["analysis"]["analyses"]:
                        parent_for(word, path, parents)
                additions = frame(before, after, parents)
                assert additions, "changed old frame without an attributed addition"
                changed.append({"record": count, "before": before, "after": after})
                for path in additions:
                    parent_surface, parent = actual_parent(word, path, parents)
                    assessment = after["dictionary"]["readings"][
                        after["analysis"]["analyses"].index(path)
                    ]
                    owners = sorted(
                        {
                            owner["id"]
                            for lemma in assessment["lemmas"]
                            for owner in lemma["entries"]
                        }
                    )
                    native_ids.update(owners)
                    identity = [
                        spec["family"],
                        spec["encoding"],
                        spec["mode"],
                        count,
                        path,
                    ]
                    ident = hashlib.sha256(
                        json.dumps(
                            identity, ensure_ascii=False, sort_keys=True
                        ).encode()
                    ).hexdigest()[:24]
                    observations.append(
                        {
                            "id": "reported-dana-legacy-" + ident,
                            "family": spec["family"],
                            "encoding": spec["encoding"],
                            "mode": spec["mode"],
                            "record": count,
                            "surface": after["surface"],
                            "normalized": word,
                            "span": span,
                            "analysis": path,
                            "dictionary_assessment": assessment,
                            "native_entry_ids": owners,
                            "parent_surface": parent_surface,
                            "exact_parent": parent,
                            "contextual_verdict": "unjudged",
                            "independent_review": "pending",
                        }
                    )
            codes = [job.wait() for job in jobs]
            assert codes == [0, 0] and count == spec["records"] and offset == len(raw)
            assert hashes[0].hexdigest() == spec["expected_before_sha256"]
        finally:
            for job in jobs:
                if job.poll() is None:
                    job.terminate()
                job.wait()
            for request in files:
                request.close()
        comparisons.append(
            {key: spec[key] for key in ["family", "encoding", "mode"]}
            | {
                "commands": commands,
                "exit_codes": codes,
                "records": count,
                "input_sha256": hashlib.sha256(raw).hexdigest(),
                "before_sha256": hashes[0].hexdigest(),
                "after_sha256": hashes[1].hexdigest(),
                "changed_frames": changed,
                "original_bytes_conserved": True,
            }
        )
        print(
            "legacy",
            spec["family"],
            spec["encoding"],
            spec["mode"],
            count,
            "frames;",
            len(changed),
            "changed",
            flush=True,
        )
    assert len(observations) == len({row["id"] for row in observations})
    assert all(sha(name) == value for name, value in frozen.items())
    assert all(file_sha(name) == value for name, value in binaries.items())
    producer = Path(__file__)
    report = {
        "schema_version": 1,
        "state": "passed",
        "inputs_unchanged": True,
        "comparisons": comparisons,
        "individual_additions": observations,
        "actual_prior_companions": parents,
        "observed_native_ids": sorted(native_ids),
        "frozen_inputs": frozen,
        "binaries": binaries,
        "producer": {"text": producer.read_text(), "sha256": file_sha(producer)},
        "scope": "Actual complete earlier source streams against validated previous package. All old candidates, order, dictionary readings and byte spans survive; every new path has an exact actual old companion. Matched Native owners are listed for separate complete-entry validation; contextual and independent review remain unjudged.",
    }
    output.write_bytes(
        gzip.compress(
            (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode(), mtime=0
        )
    )
    print(
        "Actual legacy parity:",
        sum(row["records"] for row in comparisons),
        "frames;",
        len(observations),
        "individually tracked additions;",
        len(native_ids),
        "owners",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    capture(args.cli, args.output)
