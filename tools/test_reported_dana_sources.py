"""Corrupt source updates while retaining the immutable tested package anchor."""

import copy
import gzip
import unittest
from copula_expectation_production import ROOT, read
from reported_dana_sources import verify, source_texts, text_sha, nar_contents


class CompleteSourceUpdates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = read("docs/reported-dana-package-sources.json")
        cls.baseline = read("docs/reported-deoni-package-complete-sources.json")
        cls.bundle = read("docs/reported-dana-integration.json.gz")
        cls.texts = source_texts()
        cls.receipt = read("docs/reported-dana-package-nix.json")
        cls.log = gzip.decompress(
            (ROOT / "docs/reported-dana-package-nix.log.gz").read_bytes()
        ).decode()

    def check(self, sources=None, bundle=None, receipt=None):
        return verify(
            self.sources if sources is None else sources,
            self.baseline,
            self.bundle if bundle is None else bundle,
            self.texts,
            self.receipt if receipt is None else receipt,
            self.log,
        )

    def test_complete_tested_source_nar_and_parent_updates(self):
        self.assertEqual(self.check()["source_files"], 859)

    def test_missing_new_source_fixture_is_rejected(self):
        changed = copy.deepcopy(self.sources)
        changed["files"].pop("tests/fixtures/reported-dana-validity.json")
        with self.assertRaises(AssertionError):
            self.check(sources=changed)

    def test_wrong_original_source_parent_is_rejected(self):
        changed = copy.deepcopy(self.bundle)
        changed["files"]["src/engine.rs"]["before_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.check(bundle=changed)

    def test_changed_source_executable_bit_is_rejected(self):
        changed = copy.deepcopy(self.sources)
        changed["files"]["src/engine.rs"]["executable"] = True
        with self.assertRaises(AssertionError):
            self.check(sources=changed)

    def test_missing_directory_is_rejected(self):
        changed = copy.deepcopy(self.sources)
        changed["directories"].remove("tests/reported_dana_support")
        with self.assertRaises(AssertionError):
            self.check(sources=changed)

    def test_changed_source_anchor_is_rejected(self):
        changed = copy.deepcopy(self.sources)
        changed["source"] = "/nix/store/incorrect-source"
        with self.assertRaises(AssertionError):
            self.check(sources=changed)

    def test_changed_package_log_is_rejected(self):
        with self.assertRaises(AssertionError):
            verify(
                self.sources,
                self.baseline,
                self.bundle,
                self.texts,
                self.receipt,
                self.log + "fabricated",
            )

    def test_self_consistent_replacement_text_and_nar_cannot_change_tested_source(self):
        sources = copy.deepcopy(self.sources)
        bundle = copy.deepcopy(self.bundle)
        receipt = copy.deepcopy(self.receipt)
        name = "tests/fixtures/validity.json"
        change = bundle["files"][name]
        old_bytes = len(change["after_text"].encode())
        change["after_text"] = change["after_text"].replace(
            "reported-dana-", "reported-xana-", 1
        )
        self.assertEqual(len(change["after_text"].encode()), old_bytes)
        change["after_sha256"] = text_sha(change["after_text"])
        sources["files"][name]["sha256"] = receipt["snapshot"][name]["sha256"] = change[
            "after_sha256"
        ]
        texts = dict(self.texts)
        texts.update(
            {path: value["after_text"] for path, value in bundle["files"].items()}
        )
        digest, count = nar_contents(sources["files"], sources["directories"], texts)
        self.assertEqual(count, sources["nar_bytes"])
        sources["nar_sha256"] = sources["store_path_command"][4] = digest
        with self.assertRaises(AssertionError):
            self.check(sources, bundle, receipt)


if __name__ == "__main__":
    unittest.main()
