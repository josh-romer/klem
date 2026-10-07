"""Verify all package inputs by reconstructing the official NAR byte stream."""

import hashlib
import struct
from pathlib import PurePosixPath


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def source_store_path(nar_sha256):
    """Nix's recursive SHA256 source path: hash, XOR-fold, then Nix base32."""
    fingerprint = f"source:sha256:{nar_sha256}:/nix/store:source"
    raw = hashlib.sha256(fingerprint.encode()).digest()
    folded = bytearray(20)
    for index, byte in enumerate(raw):
        folded[index % 20] ^= byte
    alphabet = "0123456789abcdfghijklmnpqrsvwxyz"
    number = int.from_bytes(folded, "little")
    encoded = "".join(alphabet[(number >> shift) & 31] for shift in range(155, -1, -5))
    return f"/nix/store/{encoded}-source"


def verify_complete_sources(
    complete, supplement, sources, archive, formatting, receipt
):
    for key in ["package", "derivation", "source"]:
        assert complete[key] == supplement[key] == sources[key]
    assert supplement["preceding_commit"] == receipt["snapshot"]["head"]
    for report in [complete, supplement]:
        assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    assert complete["nar_command"] == ["nix-store", "--dump", sources["source"]]
    assert complete["store_path_command"] == [
        "nix-store",
        "--print-fixed-path",
        "--recursive",
        "sha256",
        complete["nar_sha256"],
        "source",
    ]
    assert source_store_path(complete["nar_sha256"]) == sources["source"]
    recorded, extra = sources["files"], supplement["files"]
    assert set(recorded).isdisjoint(extra)
    assert set(complete["files"]) == set(recorded) | set(extra)
    assert len(recorded) == 661 and len(extra) == 189 and len(complete["files"]) == 850
    assert sum(name.endswith(".conllu") for name in extra) == 184
    assert set(archive["files"]) == set(recorded)
    texts = {}
    old = '#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;\n#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;'
    new = '#[path = "copula_expectation_support/parent.rs"]\nmod copula_expectation_parent;\n#[path = "deoniman_support/parent.rs"]\nmod deoniman_parent;'
    for name, value in archive["files"].items():
        text = value["text"]
        assert (
            digest(text) == value["sha256"] == recorded[name]["full_rust_input_sha256"]
        )
        if name in formatting["files"]:
            assert text.count(old) == 1
            text = text.replace(old, new)
            assert digest(text) == formatting["files"][name]["after_sha256"]
        assert digest(text) == recorded[name]["sha256"]
        texts[name] = text
    for name, value in extra.items():
        assert (
            digest(value["text"]) == value["sha256"] == value["preceding_commit_sha256"]
        )
        assert len(value["text"].encode()) == value["bytes"]
        texts[name] = value["text"]
    for name, value in complete["files"].items():
        text = texts[name]
        assert value["sha256"] == digest(text) and value["bytes"] == len(text.encode())
        assert value["recorded_main_rust_input"] == (name in recorded)
        assert isinstance(value["executable"], bool)
    directories = complete["directories"]
    assert directories == sorted(set(directories))
    children = {"": {}}
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
    nar = hashlib.sha256()
    count = 0

    def write(raw):
        nonlocal count
        nar.update(raw)
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
            if complete["files"][name]["executable"]:
                string("executable")
                string("")
            string("contents")
            string(texts[name])
        string(")")

    string("nix-archive-1")
    node("")
    assert count == complete["nar_bytes"] and nar.hexdigest() == complete["nar_sha256"]
    return {
        "files": len(texts),
        "annotated_fixtures": 184,
        "nar_bytes": count,
        "nar_sha256": nar.hexdigest(),
    }


def inspect():
    from copula_expectation_production import ROOT, read, sha

    complete = read("docs/reported-deoni-package-complete-sources.json")
    assert complete["package_source_receipt_sha256"] == sha(
        ROOT / "docs/reported-deoni-package-sources.json"
    )
    assert complete["supplement_sha256"] == sha(
        ROOT / "docs/reported-deoni-package-source-supplement.json.gz"
    )
    assert complete["original_complete_capture_sha256"] == sha(
        ROOT / "docs/reported-deoni-package-complete-sources-original.json"
    )
    return verify_complete_sources(
        complete,
        read("docs/reported-deoni-package-source-supplement.json.gz"),
        read("docs/reported-deoni-package-sources.json"),
        read("docs/reported-deoni-main-rust-sources.json.gz"),
        read("docs/reported-deoni-main-formatting.json"),
        read("docs/reported-deoni-package-nix.json"),
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print("Verified complete immutable package source:", inspect())
