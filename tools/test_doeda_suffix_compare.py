"""Reject broad stream drift and unattributed or destructive candidate changes."""

import unittest
from copy import deepcopy

from doeda_suffix_compare import PRIOR, REPORT, inspect
from doeda_suffix_diagnostics import SuffixAudit
from lexical_nada_audit import read


class BroadStreamGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.prior, cls.report = read(PRIOR), read(REPORT)

    def check(self, comparisons=None, pairs=None):
        audit = SuffixAudit(
            self.report["original_parent_components"],
            original_words=self.report["independent_before_words"],
        )
        audit.words = self.report["independent_words"].copy()
        inspect(
            self.prior,
            comparisons if comparisons is not None else self.report["comparisons"],
            pairs if pairs is not None else self.report["changed_record_pairs"],
            audit,
        )
        return list(audit.changes.values())

    def test_complete_capture_reconstructs_all_individual_changes(self):
        self.assertEqual(self.check(), self.report["changes"])

    def test_original_stream_and_source_hashes_cannot_drift(self):
        for key in ("source_sha256", "before_jsonl_sha256", "records"):
            comparisons = deepcopy(self.report["comparisons"])
            comparisons[0][key] = 1 if key == "records" else "rewritten"
            with self.subTest(key=key), self.assertRaises(AssertionError):
                self.check(comparisons=comparisons)

    def test_missing_or_reordered_changed_records_are_rejected(self):
        original = self.report["changed_record_pairs"]
        for pairs in (original[1:], [original[1], original[0], *original[2:]]):
            with self.assertRaises(AssertionError):
                self.check(pairs=pairs)

    def test_loss_of_original_candidate_is_rejected(self):
        pairs = deepcopy(self.report["changed_record_pairs"])
        old = pairs[0]["before"]["analysis"]["analyses"][0]
        pairs[0]["after"]["analysis"]["analyses"].remove(old)
        with self.assertRaises(AssertionError):
            self.check(pairs=pairs)

    def test_added_candidate_cannot_borrow_global_suffix_marker(self):
        pairs = deepcopy(self.report["changed_record_pairs"])
        row = pairs[0]
        old = row["before"]["analysis"]["analyses"]
        added = next(a for a in row["after"]["analysis"]["analyses"] if a not in old)
        added["lemmas"][0]["text"] = "unlisted base"
        with self.assertRaises(AssertionError):
            self.check(pairs=pairs)

    def test_prior_spacing_hypothesis_cannot_be_removed(self):
        pairs = deepcopy(self.report["changed_record_pairs"])
        row = next(
            r for r in pairs if r["before"].get("spacing", {}).get("alternatives")
        )
        row["after"]["spacing"]["alternatives"] = []
        with self.assertRaises(AssertionError):
            self.check(pairs=pairs)


if __name__ == "__main__":
    unittest.main()
