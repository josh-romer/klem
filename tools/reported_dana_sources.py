"""Bind all 859 tested source inputs to the previous complete source and exact updates."""

import gzip
import hashlib
import json
import struct
from pathlib import PurePosixPath
from copula_expectation_production import ROOT, read, sha
from reported_deoni_complete_sources import (
    inspect as verify_baseline,
    source_store_path,
)


def text_sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def source_texts():
    archive = read("docs/reported-deoni-main-rust-sources.json.gz")["files"]
    formatting = read("docs/reported-deoni-main-formatting.json")["files"]
    old = '#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;\n#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;'
    new = '#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;\n#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;'
    texts = {}
    for name, record in archive.items():
        value = record["text"]
        if name in formatting:
            assert value.count(old) == 1
            value = value.replace(old, new)
        texts[name] = value
    for name, record in read("docs/reported-deoni-package-source-supplement.json.gz")[
        "files"
    ].items():
        assert name not in texts
        texts[name] = record["text"]
    return texts


def nar_contents(files, directories, texts):
    children = {"": {}}
    assert directories == sorted(set(directories))
    for name in directories:
        path = PurePosixPath(name)
        assert str(path) == name and not path.is_absolute() and ".." not in path.parts
        assert name not in texts
        children[name] = {}
    for name in directories + sorted(texts):
        path = PurePosixPath(name)
        parent = "" if str(path.parent) == "." else str(path.parent)
        assert parent in children and path.name not in children[parent]
        children[parent][path.name] = name
    digest = hashlib.sha256()
    count = 0

    def write(raw):
        nonlocal count
        digest.update(raw)
        count += len(raw)

    def string(value):
        raw = value.encode() if isinstance(value, str) else value
        write(struct.pack("<Q", len(raw)))
        write(raw)
        write(b"\0" * ((-len(raw)) % 8))

    def node(name):
        string("(")
        string("type")
        if name in children:
            string("directory")
            for child in sorted(children[name], key=lambda value: value.encode()):
                string("entry")
                string("(")
                string("name")
                string(child)
                string("node")
                node(children[name][child])
                string(")")
        else:
            string("regular")
            if files[name]["executable"]:
                string("executable")
                string("")
            string("contents")
            string(texts[name])
        string(")")

    string("nix-archive-1")
    node("")
    return digest.hexdigest(), count


def verify(sources, baseline, bundle, texts, receipt, log):
    assert sources["state"] == receipt["state"] == "passed"
    assert receipt["exit_code"] == 0 and receipt["snapshot_unchanged"]
    assert sources["package"] in receipt["outputs"]
    assert text_sha(log) == receipt["log_sha256"]
    for key in ["producer"]:
        assert text_sha(sources[key]["text"]) == sources[key]["sha256"]
    assert (
        text_sha(sources["derivation_json_text"]) == sources["derivation_json_sha256"]
    )
    drv = json.loads(sources["derivation_json_text"])
    assert set(drv) == {sources["derivation"]}
    assert drv[sources["derivation"]]["env"]["src"] == sources["source"]
    assert drv[sources["derivation"]]["outputs"]["out"]["path"] == sources["package"]
    assert set(texts) == set(baseline["files"]) and len(texts) == 850
    updates = bundle["files"]
    assert len(updates) == 19
    current = dict(texts)
    for name, change in updates.items():
        assert change["before_sha256"] == (
            text_sha(texts[name]) if name in texts else None
        )
        assert text_sha(change["after_text"]) == change["after_sha256"]
        current[name] = change["after_text"]
    assert set(current) == set(sources["files"]) and len(current) == 859
    for name, text in current.items():
        record = sources["files"][name]
        assert record["sha256"] == text_sha(text) == receipt["snapshot"][name]["sha256"]
        assert (
            record["bytes"] == len(text.encode()) == receipt["snapshot"][name]["bytes"]
        )
        assert isinstance(record["executable"], bool)
    digest, count = nar_contents(sources["files"], sources["directories"], current)
    assert (
        digest == sources["nar_sha256"] and count == sources["nar_bytes"] == 704297464
    )
    assert source_store_path(digest) == sources["source"]
    assert sources["nar_command"] == ["nix-store", "--dump", sources["source"]]
    assert sources["store_path_command"] == [
        "nix-store",
        "--print-fixed-path",
        "--recursive",
        "sha256",
        digest,
        "source",
    ]
    return {
        "source_files": len(current),
        "updated_files": len(updates),
        "nar_bytes": count,
        "nar_sha256": digest,
    }


def inspect():
    verify_baseline()
    sources = read("docs/reported-dana-package-sources.json")
    for key, name in [
        ("package_receipt_sha256", "docs/reported-dana-package-nix.json"),
        (
            "baseline_complete_source_sha256",
            "docs/reported-deoni-package-complete-sources.json",
        ),
        ("integration_bundle_sha256", "docs/reported-dana-integration.json.gz"),
    ]:
        assert sources[key] == sha(ROOT / name)
    return verify(
        sources,
        read("docs/reported-deoni-package-complete-sources.json"),
        read("docs/reported-dana-integration.json.gz"),
        source_texts(),
        read("docs/reported-dana-package-nix.json"),
        gzip.decompress(
            (ROOT / "docs/reported-dana-package-nix.log.gz").read_bytes()
        ).decode(),
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print(
        "Verified complete tested source updates and independent canonical NAR:",
        inspect(),
    )
