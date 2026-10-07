"""Audit captured full-stream parity; byte-span checks belong to the saved producer."""

import copy
from reported_dana_corpora import read, sha, reject


def verify(report):
    previous = read("docs/reported-deoni-prototype-broad.json.gz")
    inputs = read("docs/reported-deoni-broad-inputs.json.gz")["sources"]
    source = read("docs/reported-dana-prototype-source-streams.json.gz")
    assert report["prototype"] and report["inputs_unchanged"]
    assert report["prior_capture_sha256"] == sha(
        "docs/reported-deoni-prototype-broad.json.gz"
    )
    import hashlib

    assert (
        hashlib.sha256(report["producer"]["text"].encode()).hexdigest()
        == report["producer"]["sha256"]
    )
    assert (
        report["individual_additions"] == [] and report["actual_prior_companions"] == {}
    )
    before_cli = "/nix/store/p0xh9pk9m2nm8373vzicgdpx5w1yz6z7-klem-0.1.0/bin/klem"
    after_cli = "/home/josh/projects/klem/web/test-results/reported-dana-prototype-cargo/debug/klem"
    assert (
        source["frozen_inputs"][before_cli]
        == report["before_cli_sha256"]
        == report["frozen_inputs"][before_cli]
    )
    assert (
        source["frozen_inputs"][after_cli]
        == report["cli_sha256"]
        == report["frozen_inputs"][after_cli]
    )
    dictionary = "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"
    assert source["frozen_inputs"][dictionary] == report["frozen_inputs"][dictionary]
    assert len(report["comparisons"]) == len(previous["comparisons"]) == 8
    identities = set()
    for run, old in zip(report["comparisons"], previous["comparisons"], strict=True):
        assert all(
            run[key] == old[key]
            for key in ["source", "source_sha256", "mode", "records"]
        )
        identity = (run["source"], run["mode"])
        assert identity not in identities
        identities.add(identity)
        original = inputs[run["source"]]
        assert (
            hashlib.sha256(original["text"].encode()).hexdigest()
            == original["sha256"]
            == run["source_sha256"]
            == report["frozen_inputs"][run["source"]]
        )
        assert (
            run["before_jsonl_sha256"]
            == run["after_jsonl_sha256"]
            == old["after_jsonl_sha256"]
        )
        assert run["exit_codes"] == [0, 0] and run["original_bytes_conserved"]
        assert run["changed_frames"] == []
        mode = run["mode"]
        flags = (
            ["--dict-compatible"]
            if "compatible" in mode
            else ["--dict-only"]
            if "headword" in mode
            else []
        )
        commands = [
            [
                cli,
                "text",
                run["source"],
                "--dictionary",
                dictionary,
                *flags,
                *(["--suggest-spacing"] if "spacing" in mode else []),
            ]
            for cli in [before_cli, after_cli]
        ]
        assert run["commands"] == commands
    assert sum(run["records"] for run in report["comparisons"]) == 1128312
    return 1128312


if __name__ == "__main__":
    report = read("docs/reported-dana-prototype-broad.json.gz")
    print("Verified all eight captured unchanged streams:", verify(report), flush=True)
    changed = copy.deepcopy(report)
    changed["comparisons"][0]["after_jsonl_sha256"] = "0" * 64
    reject(lambda: verify(changed), "changed full-stream fingerprint")
    changed = copy.deepcopy(report)
    changed["comparisons"][1] = copy.deepcopy(changed["comparisons"][0])
    reject(lambda: verify(changed), "duplicate comparison")
    changed = copy.deepcopy(report)
    changed["comparisons"][0]["commands"][1][0] = "invented-cli"
    reject(lambda: verify(changed), "wrong candidate CLI")
    changed = copy.deepcopy(report)
    changed["comparisons"][0]["original_bytes_conserved"] = False
    reject(lambda: verify(changed), "unverified byte conservation")
