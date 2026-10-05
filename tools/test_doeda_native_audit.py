"""Reject borrowed noun origins and rewritten native formation evidence."""

import unittest
from copy import deepcopy

from doeda_native_audit import FIXTURE, REPORT, verify_data
from lexical_nada_audit import read


class NativeReviewGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report, cls.fixture = read(REPORT), read(FIXTURE)
        verify_data(cls.report, cls.fixture)

    def test_complete_native_dispositions_and_case_ids_are_verified(self):
        verify_data(self.report, self.fixture)

    def test_matching_noun_cannot_be_replaced_by_spelling_homonym(self):
        report = deepcopy(self.report)
        row = next(r for r in report["native_reviews"] if r["head"] == "결정되다")
        self.assertEqual(row["matching_noun_entries"], ["krdict:83174"])
        row["matching_noun_entries"] = ["krdict:32131"]
        with self.assertRaises(AssertionError):
            verify_data(report, self.fixture)

    def test_missing_or_changed_native_lead_fails(self):
        for change in ("missing", "class"):
            report = deepcopy(self.report)
            if change == "missing":
                report["native_reviews"].pop()
            else:
                report["native_reviews"][0]["predicate_class"] = "adjective"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_data(report, self.fixture)

    def test_unresolved_base_cannot_be_promoted_to_a_licensed_noun(self):
        report = deepcopy(self.report)
        row = next(r for r in report["native_reviews"] if r["head"] == "경주되다")
        self.assertEqual(row["disposition"], "unresolved-native-base")
        self.assertFalse(row["matching_noun_entries"])
        row["disposition"] = "nominal-origin-supported"
        row["matching_noun_entries"] = ["krdict:25919"]
        with self.assertRaises(AssertionError):
            verify_data(report, self.fixture)

    def test_fixture_cannot_change_proposed_roles_or_owned_inflections(self):
        for change in ("role", "suffix", "case"):
            fixture = deepcopy(self.fixture)
            if change == "role":
                fixture["formations"][0]["base_kind"] = "root"
            elif change == "suffix":
                fixture["variants"][0]["morphemes"] = ["는다"]
            else:
                fixture["formations"][0]["id"] = "rewritten"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                verify_data(self.report, fixture)


if __name__ == "__main__":
    unittest.main()
