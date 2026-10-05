"""Guard source identity, original records and supplemental formation scope."""

import unittest
from copy import deepcopy

from doeda_partial_origins import REPORT, inspect
from lexical_nada_audit import read


class PartialOriginGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(REPORT)

    def test_complete_source_evidence_passes(self):
        self.assertEqual(inspect(self.report), (2, 20, 44))

    def test_missing_native_owner_or_invented_noun_origin_fails(self):
        for field in ("owner", "origin"):
            report = deepcopy(self.report)
            if field == "owner":
                report["complete_native_entries"].pop("krdict:77498")
            else:
                report["complete_native_entries"]["krdict:77493"]["origins"] = ["添削"]
            with (
                self.subTest(field=field),
                self.assertRaises((AssertionError, KeyError)),
            ):
                inspect(report)

    def test_borrowed_noun_or_promoted_identity_fails(self):
        for field in ("noun", "identity", "whole"):
            report = deepcopy(self.report)
            if field == "noun":
                report["formations"][0]["noun_entries"] = ["krdict:23528"]
            elif field == "identity":
                report["formations"][0]["origin_relation"] = "recorded_match"
            else:
                report["formations"][0]["whole_origins_complete"] = False
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect(report)

    def test_missing_original_stream_case_or_control_fails(self):
        for field in ("stream", "case", "control"):
            report = deepcopy(self.report)
            if field == "stream":
                report["before_streams"]["compatible"].pop()
            elif field == "case":
                report["cases"].pop()
            else:
                report["controls"].pop()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect(report)

    def test_corpus_evidence_cannot_be_invented(self):
        report = deepcopy(self.report)
        report["corpus_occurrences"] = [{"head": "첨삭되다"}]
        with self.assertRaises(AssertionError):
            inspect(report)


if __name__ == "__main__":
    unittest.main()
