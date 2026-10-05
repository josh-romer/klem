"""Reject gaps and rewritten ownership in the packaged native evidence."""

import copy
import unittest

import doeda_native_package as package
from lexical_nada_audit import read


class NativePackagedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(package.REPORT)
        package.verify_data(cls.report)

    def altered_batch(self, index=0):
        report = dict(self.report, api=dict(self.report["api"]))
        report["api"]["batches"] = list(self.report["api"]["batches"])
        batch = copy.deepcopy(report["api"]["batches"][index])
        report["api"]["batches"][index] = batch
        return report, batch

    def test_missing_encoded_case_is_rejected(self):
        index = next(
            i
            for i, b in enumerate(self.report["api"]["batches"])
            if b["encoding"] == "NFD"
        )
        report, batch = self.altered_batch(index)
        batch["cases"].pop()
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_changed_candidate_or_native_reading_is_rejected(self):
        for field in ("analysis", "dictionary"):
            report, batch = self.altered_batch()
            row = next(r for r in batch["api"]["records"] if r["kind"] == "word")
            if field == "analysis":
                row[field]["analyses"].pop()
            else:
                row[field]["readings"][0]["status"] = "unknown"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                package.verify_data(report)

    def test_wrong_order_on_a_required_owned_path_is_rejected(self):
        report, batch = self.altered_batch()
        batch["api"]["breakdowns"][0][0].reverse()
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_native_entry_or_browser_diagram_rewrite_is_rejected(self):
        report = dict(self.report, api=dict(self.report["api"]))
        native = dict(report["api"]["native_endpoint_entries"])
        entry = copy.deepcopy(native["krdict:74902"])
        entry["senses"][0]["definition"] = "rewritten"
        native["krdict:74902"] = entry
        report["api"]["native_endpoint_entries"] = native
        with self.assertRaises(AssertionError):
            package.verify_data(report)
        report = dict(self.report, browser=copy.deepcopy(self.report["browser"]))
        report["browser"]["diagrams"][0]["forms"].reverse()
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_missing_filter_export_or_fixture_drift_is_rejected(self):
        report = dict(self.report, browser=copy.deepcopy(self.report["browser"]))
        report["browser"]["checks"].pop()
        with self.assertRaises(AssertionError):
            package.verify_data(report)
        report = dict(self.report, browser=dict(self.report["browser"]))
        report["browser"]["fixture_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            package.verify_data(report)


if __name__ == "__main__":
    unittest.main()
