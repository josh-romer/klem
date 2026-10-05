"""Reject altered candidate, identity, Unicode/cache and component evidence."""

import hashlib
import json
import unittest
from copy import deepcopy

from doeda_partial_origin_diagnostics import REPORT, inspect
from lexical_nada_audit import read


def synchronize_raw(report):
    text = "".join(
        json.dumps(r, ensure_ascii=False) + "\n" for r in report["after_streams"]["raw"]
    )
    report["after_jsonl"]["raw"] = text
    report["after_jsonl_sha256"]["raw"] = hashlib.sha256(text.encode()).hexdigest()


class PartialOriginDiagnosticGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(REPORT)

    def test_actual_complete_evidence_passes(self):
        comparisons, changes = inspect(self.report)
        self.assertEqual(changes, 30)
        self.assertEqual(
            [c["unknown_identity_assessments"] for c in comparisons], [30, 30, 30]
        )

    def test_old_candidate_loss_fails(self):
        report = deepcopy(self.report)
        record = next(r for r in report["after_streams"]["raw"] if r["kind"] == "word")
        record["analysis"]["analyses"].pop(0)
        synchronize_raw(report)
        with self.assertRaises(AssertionError):
            inspect(report)

    def test_known_whole_origin_cannot_promote_missing_noun_identity(self):
        report = deepcopy(self.report)
        entry = next(
            e
            for r in report["after_streams"]["raw"]
            if r["kind"] == "word"
            for a in r["dictionary"]["readings"]
            for l in a["lemmas"]
            for e in l["entries"]
            if "derivational_identity" in e
        )
        entry["derivational_identity"]["relation"] = "recorded_match"
        synchronize_raw(report)
        with self.assertRaises(AssertionError):
            inspect(report)

    def test_missing_unicode_cache_or_change_evidence_fails(self):
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
