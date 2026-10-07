"""Corrupt actual packaged evidence without modifying any archived capture."""

import copy, gzip, unittest
from copula_expectation_production import ROOT, read
from reported_deoni_release import verify_build, verify_cli, verify_browser


class PackagedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = read("docs/reported-deoni-packaged-checks.json")
        cls.receipt = read("docs/reported-deoni-package-nix.json")
        cls.sources = read("docs/reported-deoni-package-sources.json")
        cls.archive = read("docs/reported-deoni-main-rust-sources.json.gz")
        cls.rust = read("docs/reported-deoni-main-rust.json")
        cls.formatting = read("docs/reported-deoni-main-formatting.json")
        cls.log = gzip.decompress(
            (ROOT / "docs/reported-deoni-package-nix.log.gz").read_bytes()
        ).decode()
        cls.production = read("docs/reported-deoni-packaged-production.json")
        cls.main = read("docs/reported-deoni-main-production.json")
        cls.corpus = read("docs/reported-deoni-prototype-corpora.json.gz")
        cls.browser = read("docs/reported-deoni-packaged-browser.json.gz")
        cls.main_browser = read("docs/reported-deoni-main-browser.json.gz")
        cls.native = read("docs/reported-deoni-observation-native.json.gz")

    def build(self, sources=None, archive=None):
        return verify_build(
            self.receipt,
            archive or self.archive,
            self.rust,
            self.formatting,
            sources or self.sources,
            self.log,
        )

    def check_cli(self, production):
        return verify_cli(
            production,
            self.main,
            self.corpus,
            self.package["nix_outputs"]["klem"] + "/bin/klem",
        )

    def test_actual_build_cli_and_browser(self):
        self.build()
        self.check_cli(self.production)
        verify_browser(self.browser, self.main_browser, self.native)

    def test_incomplete_source_closure_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        sources["files"].pop("src/engine.rs")
        with self.assertRaises(AssertionError):
            self.build(sources=sources)

    def test_changed_source_fingerprint_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        sources["files"]["src/grammar.rs"]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            self.build(sources=sources)

    def test_unrecorded_formatting_change_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        sources["files"]["tests/degree_rimankeum.rs"]["formatting_only"] = False
        with self.assertRaises(AssertionError):
            self.build(sources=sources)

    def test_fake_packaged_evaluator_is_rejected(self):
        production = copy.deepcopy(self.production)
        production["corpus_runs"] = self.main["corpus_runs"]
        with self.assertRaises(AssertionError):
            self.check_cli(production)

    def test_duplicate_legacy_stream_is_rejected(self):
        production = copy.deepcopy(self.production)
        production["legacy_source_runs"][1] = production["legacy_source_runs"][0]
        with self.assertRaises(AssertionError):
            self.check_cli(production)

    def test_changed_cli_command_is_rejected(self):
        production = copy.deepcopy(self.production)
        production["source_runs"][0]["command"][0] = "/invalid/bin/klem"
        with self.assertRaises(AssertionError):
            self.check_cli(production)

    def test_changed_native_entry_is_rejected(self):
        browser = copy.deepcopy(self.browser)
        browser["browser"]["native"][0]["response"]["entry"]["headword"] = "invented"
        with self.assertRaises(AssertionError):
            verify_browser(browser, self.main_browser, self.native)


if __name__ == "__main__":
    unittest.main()
