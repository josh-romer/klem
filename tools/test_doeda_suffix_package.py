"""Detect incomplete encoded/filter coverage and rewritten packaged evidence."""

import copy
import unittest

import doeda_suffix_package as package
from lexical_nada_audit import read


class PackagedEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(package.REPORT)

    def test_missing_encoded_case_is_rejected(self):
        report = dict(self.report, api=dict(self.report["api"]))
        report["api"]["batches"] = list(report["api"]["batches"])
        batch = dict(report["api"]["batches"][0])
        batch["cases"] = batch["cases"][:-1]
        report["api"]["batches"][0] = batch
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_filtered_candidate_loss_is_rejected(self):
        report = dict(self.report, api=dict(self.report["api"]))
        report["api"]["batches"] = list(report["api"]["batches"])
        batch = dict(report["api"]["batches"][0])
        streams = dict(batch["cli_streams"])
        streams["headword"] = list(streams["headword"])
        i = next(
            i
            for i, r in enumerate(streams["headword"])
            if r.get("analysis", {}).get("analyses")
        )
        row = copy.deepcopy(streams["headword"][i])
        row["analysis"]["analyses"].pop()
        streams["headword"][i] = row
        batch["cli_streams"] = streams
        report["api"]["batches"][0] = batch
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_rewritten_complete_native_entry_is_rejected(self):
        report = dict(self.report, api=dict(self.report["api"]))
        native = dict(report["api"]["native_endpoint_entries"])
        entry = copy.deepcopy(native["krdict:74902"])
        entry["senses"][0]["definition"] = "changed"
        native["krdict:74902"] = entry
        report["api"]["native_endpoint_entries"] = native
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_wrong_rendered_owner_order_is_rejected(self):
        report = dict(self.report, browser=copy.deepcopy(self.report["browser"]))
        report["browser"]["diagrams"][0]["forms"].reverse()
        with self.assertRaises(AssertionError):
            package.verify_data(report)

    def test_changed_original_fixture_anchor_is_rejected(self):
        report = dict(self.report, api=dict(self.report["api"]))
        report["api"]["fixture_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            package.verify_data(report)


if __name__ == "__main__":
    unittest.main()
