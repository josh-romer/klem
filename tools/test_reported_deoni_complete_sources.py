"""Corrupt source closure data while retaining the original tested source NAR."""

import copy, gzip, hashlib, json, unittest
from pathlib import Path
from reported_deoni_complete_sources import source_store_path, verify_complete_sources

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    path = Path(path)
    return json.loads(
        gzip.decompress(path.read_bytes())
        if path.suffix == ".gz"
        else path.read_bytes()
    )


class CompleteInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.complete = read(ROOT / "docs/reported-deoni-package-complete-sources.json")
        cls.supplement = read(
            ROOT / "docs/reported-deoni-package-source-supplement.json.gz"
        )
        cls.sources = read(ROOT / "docs/reported-deoni-package-sources.json")
        cls.archive = read(ROOT / "docs/reported-deoni-main-rust-sources.json.gz")
        cls.formatting = read(ROOT / "docs/reported-deoni-main-formatting.json")
        cls.receipt = read(ROOT / "docs/reported-deoni-package-nix.json")

    def verify(self, complete=None, supplement=None):
        return verify_complete_sources(
            self.complete if complete is None else complete,
            self.supplement if supplement is None else supplement,
            self.sources,
            self.archive,
            self.formatting,
            self.receipt,
        )

    def test_full_nar_matches_official_immutable_source(self):
        self.assertEqual(self.verify()["files"], 850)

    def test_missing_annotated_fixture_is_rejected(self):
        changed = copy.deepcopy(self.supplement)
        changed["files"].pop("tests/fixtures/kaist-noun-base.conllu")
        with self.assertRaises(AssertionError):
            self.verify(supplement=changed)

    def test_self_consistent_changed_gold_text_still_fails_nar(self):
        complete = copy.deepcopy(self.complete)
        supplement = copy.deepcopy(self.supplement)
        name = "tests/fixtures/kaist-noun-base.conllu"
        record = supplement["files"][name]
        before_bytes = len(record["text"].encode())
        assert "까막눈" in record["text"]
        record["text"] = record["text"].replace("까막눈", "가짜눈", 1)
        assert len(record["text"].encode()) == before_bytes
        record["sha256"] = record["preceding_commit_sha256"] = hashlib.sha256(
            record["text"].encode()
        ).hexdigest()
        record["bytes"] = len(record["text"].encode())
        complete["files"][name]["sha256"] = record["sha256"]
        complete["files"][name]["bytes"] = record["bytes"]
        with self.assertRaises(AssertionError):
            self.verify(complete, supplement)

    def test_changed_source_executable_flag_is_rejected(self):
        changed = copy.deepcopy(self.complete)
        changed["files"]["tests/fixtures/kaist-noun-base.conllu"]["executable"] = True
        with self.assertRaises(AssertionError):
            self.verify(complete=changed)

    def test_wrong_source_anchor_is_rejected(self):
        changed = copy.deepcopy(self.complete)
        changed["source"] = "/nix/store/incorrect-source"
        with self.assertRaises(AssertionError):
            self.verify(complete=changed)

    def test_official_recursive_store_path_is_reproduced_offline(self):
        self.assertEqual(
            source_store_path(self.complete["nar_sha256"]), self.sources["source"]
        )

    def test_replaced_nar_hash_and_command_cannot_change_tested_source(self):
        changed = copy.deepcopy(self.complete)
        changed["nar_sha256"] = "0" * 64
        changed["store_path_command"][4] = changed["nar_sha256"]
        self.assertEqual(changed["store_path_command"][-1], "source")
        with self.assertRaises(AssertionError):
            self.verify(complete=changed)

    def test_missing_source_directory_is_rejected(self):
        changed = copy.deepcopy(self.complete)
        changed["directories"].remove("tests/fixtures")
        with self.assertRaises(AssertionError):
            self.verify(complete=changed)


if __name__ == "__main__":
    unittest.main()
