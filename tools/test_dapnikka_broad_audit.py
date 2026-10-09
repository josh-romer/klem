"""Reject missing observations, rewritten contexts and lost original paths."""

import copy
import unittest

import dapnikka_broad_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, change, reason):
        values = copy.deepcopy(self.evidence)
        change(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_actual_workloads(self):
        self.assertEqual(audit.inspect(*self.evidence)["individual_paths"], 5)

    def test_missing_individual_observation(self):
        self.reject(lambda v: v[0]["individual_additions"].pop(), "individual additions")

    def test_changed_context(self):
        self.reject(lambda v: v[0]["comparisons"][3]["changed_frames"][0].update(complete_original_line="fabricated"), "original context")

    def test_prior_path_removed(self):
        def remove_original(values):
            frame = values[0]["comparisons"][3]["changed_frames"][0]
            prior = frame["before"]["analysis"]["analyses"][0]
            frame["after"]["analysis"]["analyses"].remove(prior)

        self.reject(remove_original, "old candidate preservation")

    def test_previous_stream_hash_changed(self):
        self.reject(lambda v: v[0]["comparisons"][0].update(before_jsonl_sha256="0" * 64), "previous stream")

    def test_native_owner_lost(self):
        self.reject(lambda v: v[4].pop(next(iter(v[4]))), "original Native owners")

    def test_reclassified_assessment(self):
        self.reject(lambda v: v[0]["individual_additions"][0]["dictionary_assessment"].update(status="unknown"), "individual additions")


if __name__ == "__main__":
    unittest.main()
