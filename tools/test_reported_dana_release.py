"""Reject corrupt packaged evidence while preserving original runtime captures."""

import copy
import gzip
import unittest

from copula_expectation_production import ROOT, read
from reported_dana_release import (
    digest,
    verify_binding,
    verify_browser,
    verify_build,
    verify_cli,
    verify_legacy,
)


class PackagedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = read("docs/reported-dana-package-nix.json")
        cls.log = gzip.decompress(
            (ROOT / "docs/reported-dana-package-nix.log.gz").read_bytes()
        ).decode()
        cls.binding = read("docs/reported-dana-main-package-binding.json")
        cls.sources = read("docs/reported-dana-package-sources.json")
        cls.production = read("docs/reported-dana-packaged-production.json")
        cls.source = read("docs/reported-dana-prototype-source-streams.json.gz")
        cls.broad = read("docs/reported-dana-prototype-broad.json.gz")
        cls.corpus = read("docs/reported-dana-prototype-corpora.json.gz")
        cls.browser = read("docs/reported-dana-packaged-browser.json.gz")
        cls.previous_browser = read(
            "docs/reported-dana-prototype-browser-focused.json.gz"
        )
        cls.closure = read("docs/reported-dana-browser-native.json.gz")
        cls.legacy = read("docs/reported-dana-packaged-legacy.json")
        cls.previous_legacy = read("docs/reported-dana-prototype-legacy.json.gz")
        cls.cli = cls.sources["package"] + "/bin/klem"

    def check_cli(self, report):
        verify_cli(report, self.source, self.broad, self.corpus, self.cli)

    def check_browser(self, report):
        verify_browser(report, self.previous_browser, self.closure)

    def check_legacy(self, report):
        verify_legacy(
            report,
            self.previous_legacy,
            self.cli,
            self.production["binaries"][self.cli],
            self.source["frozen_inputs"][
                "/home/josh/projects/klem/data/dictionaries/krdict/krdict.db"
            ],
        )

    def check_changed_log(self, log):
        receipt = copy.deepcopy(self.receipt)
        receipt["log_sha256"] = digest(log)
        with self.assertRaises(AssertionError):
            verify_build(receipt, log)

    def test_actual_package_including_retried_substituter_warnings(self):
        self.assertIn("warning: error: unable to download", self.log)
        verify_build(self.receipt, self.log)
        verify_binding(self.binding, self.sources, self.receipt)
        self.check_cli(self.production)
        self.check_browser(self.browser)
        self.check_legacy(self.legacy)

    def test_compiler_error_with_consistent_log_digest_is_rejected(self):
        self.check_changed_log(self.log + "\nerror: could not compile klem\n")

    def test_failed_test_with_consistent_log_digest_is_rejected(self):
        self.check_changed_log(self.log + "\ntest candidate_regression ... FAILED\n")

    def test_other_warning_error_is_rejected(self):
        self.check_changed_log(
            self.log + "\nwarning: error: unresolved build failure\n"
        )

    def test_missing_test_batch_is_rejected(self):
        lines = self.log.splitlines(keepends=True)
        index = next(i for i, line in enumerate(lines) if "test result: ok." in line)
        lines.pop(index)
        self.check_changed_log("".join(lines))

    def test_incomplete_main_source_binding_is_rejected(self):
        binding = copy.deepcopy(self.binding)
        binding["files"].pop("src/engine.rs")
        with self.assertRaises(AssertionError):
            verify_binding(binding, self.sources, self.receipt)

    def test_changed_source_stream_command_is_rejected(self):
        report = copy.deepcopy(self.production)
        report["source_runs"][0]["command"][0] = "/invalid/bin/klem"
        with self.assertRaises(AssertionError):
            self.check_cli(report)

    def test_claimed_packaged_evaluation_is_rejected(self):
        report = copy.deepcopy(self.production)
        report["evaluator_runs"] = [{"state": "passed"}]
        with self.assertRaises(AssertionError):
            self.check_cli(report)

    def test_missing_browser_export_is_rejected(self):
        report = copy.deepcopy(self.browser)
        report["browser"]["records"].pop()
        with self.assertRaises(AssertionError):
            self.check_browser(report)

    def test_changed_native_entry_is_rejected(self):
        report = copy.deepcopy(self.browser)
        report["browser"]["native"][0]["response"]["entry"]["headword"] = "invented"
        with self.assertRaises(AssertionError):
            self.check_browser(report)

    def test_duplicate_legacy_stream_is_rejected(self):
        report = copy.deepcopy(self.legacy)
        report["runs"][1] = report["runs"][0]
        with self.assertRaises(AssertionError):
            self.check_legacy(report)

    def test_changed_legacy_binary_is_rejected(self):
        report = copy.deepcopy(self.legacy)
        report["cli_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.check_legacy(report)


if __name__ == "__main__":
    unittest.main()
