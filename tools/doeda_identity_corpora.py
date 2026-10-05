"""Verify all unchanged original gold rows and the complete raw corpus-word digest."""

import argparse

from doeda_identity_package import REPORT as PACKAGE
from doeda_identity_package import digest
from doeda_native_corpora import REPORT as PREVIOUS
from lexical_nada_audit import ROOT, read, sha

REPORT = ROOT / "docs/doeda-identity-corpora.json.gz"


def inspect(report):
    previous = read(PREVIOUS)
    assert report["schema_version"] == 1 and report["checklist"] == "COV-022m"
    assert report["previous_sha256"] == sha(PREVIOUS)
    assert report["cli_sha256"] == read(PACKAGE)["cli_sha256"]
    assert report["engine_sha256"] == previous["engine_sha256"]
    assert report["adapter_sha256"] == previous["adapter_sha256"]
    assert report["unique_surfaces"] == previous["unique_surfaces"] == 32096
    assert report["word_stream_sha256"] == previous["after_word_stream_sha256"]
    assert digest(report["producer"]["text"]) == report["producer"]["sha256"]
    assert len(report["corpora"]) == len(previous["corpora"]) == 4
    total = 0
    for old, new in zip(previous["corpora"], report["corpora"], strict=True):
        for key in ("corpus", "partition", "source", "source_sha256"):
            assert new[key] == old[key]
        assert new["after_jsonl"] == old["after_jsonl"]
        assert (
            new["jsonl_sha256"]
            == digest(new["after_jsonl"])
            == old["after_report_sha256"]
        )
        assert new["gold_rows"] == old["converted_rows"]
        total += new["gold_rows"]
    assert total == 66570
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", required=True)
    parser.parse_args()
    print(
        inspect(read(REPORT)), "original gold rows and all raw corpus words unchanged"
    )
