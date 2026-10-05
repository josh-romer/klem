"""Protect original evidence and finite semantic candidate additions."""

import unittest
from copy import deepcopy

from doeda_originless_audit import FIXTURE
from doeda_originless_audit import REPORT as SOURCE
from doeda_originless_audit import inspect as inspect_source
from doeda_originless_diagnostics import REPORT, inspect
from lexical_nada_audit import read


class OriginlessGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source, cls.fixture, cls.report = read(SOURCE), read(FIXTURE), read(REPORT)

    def test_actual_complete_evidence_passes(self):
        self.assertEqual(inspect_source(self.source, self.fixture), (170, 52, 165))
        comparisons, changes, _ = inspect(self.report)
        self.assertEqual(len(comparisons), 3)
        self.assertEqual(len(changes), 289)

    def test_missing_original_context_or_native_owner_fails(self):
        for field in ("context", "entry"):
            source = deepcopy(self.source)
            if field == "context":
                source["corpus_occurrences"].pop()
            else:
                source["complete_native_entries"].pop("krdict:74902")
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_source(source, self.fixture)

    def test_borrowed_noun_and_inferred_origin_fail(self):
        for field in ("noun", "origin"):
            fixture = deepcopy(self.fixture)
            if field == "noun":
                fixture["formations"][0]["noun_entries"] = ["krdict:31674"]
            else:
                fixture["formations"][0]["origin_relation"] = "recorded_match"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_source(self.source, fixture)

    def test_missing_original_candidate_fails(self):
        report = deepcopy(self.report)
        record = next(r for r in report["after_streams"]["raw"] if r["kind"] == "word")
        record["analysis"]["analyses"].pop(0)
        with self.assertRaises(AssertionError):
            inspect(report)

    def test_unknown_identity_cannot_be_omitted_or_promoted(self):
        for field in ("missing", "promoted"):
            report = deepcopy(self.report)
            entries = (
                e
                for r in report["after_streams"]["raw"]
                if r["kind"] == "word"
                for a in r["dictionary"]["readings"]
                for l in a["lemmas"]
                for e in l["entries"]
            )
            entry = next(e for e in entries if "derivational_identity" in e)
            if field == "missing":
                del entry["derivational_identity"]
            else:
                entry["derivational_identity"]["relation"] = "recorded_match"
            with (
                self.subTest(field=field),
                self.assertRaises((AssertionError, KeyError)),
            ):
                inspect(report)

    def test_unicode_cache_and_individual_change_coverage_are_required(self):
        for field in ("unicode", "cache", "change"):
            report = deepcopy(self.report)
            if field == "unicode":
                report["nfd_streams"]["compatible"].pop()
            elif field == "cache":
                report["uncached_streams"]["headword"].pop()
            else:
                report["changes"].pop()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect(report)


if __name__ == "__main__":
    unittest.main()
