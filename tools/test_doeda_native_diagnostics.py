"""Reject native additions that lose prior paths or borrow the wrong source role."""

import unittest
from copy import deepcopy

from doeda_native_diagnostics import REPORT, NativeAudit
from doeda_native_preflight import REPORT as PREFLIGHT
from doeda_native_preflight import words
from lexical_nada_audit import read
from lexical_nada_compare import canon


class NativeDiagnosticGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source, after = read(PREFLIGHT), read(REPORT)
        raw_before, raw_after = (
            words(source["before_streams"]["raw"]),
            words(after["after_streams"]["raw"]),
        )
        cls.surface = source["cases"][0]["surface"]
        cls.before, cls.after = raw_before[cls.surface], raw_after[cls.surface]
        cls.components = {
            canon(a): source["original_parent_components"][canon(a)]
            for a in cls.before["analyses"]
        }
        cls.added = next(
            a for a in cls.after["analyses"] if a not in cls.before["analyses"]
        )
        cls.audit().word(cls.before, cls.after)

    @classmethod
    def audit(cls):
        return NativeAudit(cls.components, {cls.surface: cls.before})

    def test_native_origin_supported_path_has_original_whole_owner(self):
        self.assertIn(self.added, self.audit().word(self.before, self.after))

    def test_added_root_cannot_borrow_a_nominal_source_license(self):
        after = deepcopy(self.after)
        next(a for a in after["analyses"] if a == self.added)["lemmas"][0]["kind"] = (
            "root"
        )
        with self.assertRaises(AssertionError):
            self.audit().word(self.before, after)

    def test_original_candidate_loss_and_assessment_drift_are_rejected(self):
        for change in ("candidate", "assessment"):
            after = deepcopy(self.after)
            if change == "candidate":
                after["analyses"].remove(self.before["analyses"][0])
            else:
                i = after["analyses"].index(self.before["analyses"][0])
                after["dictionary"]["readings"][i]["status"] = "rewritten"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.audit().word(self.before, after)

    def test_owned_suffix_and_spelling_indices_cannot_be_invented(self):
        for change in ("suffix", "spelling"):
            after = deepcopy(self.after)
            added = next(a for a in after["analyses"] if a == self.added)
            if change == "suffix":
                added["morphemes"].reverse()
            else:
                added["spelling_paths"] = [
                    [{"class": "written_vowel_eo", "morpheme_index": 99}]
                ]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                self.audit().word(self.before, after)


if __name__ == "__main__":
    unittest.main()
