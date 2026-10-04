"""Reject altered baseline hashes, incomplete workloads, and misleading summaries."""

import unittest
from copy import deepcopy

from doeda_suffix_performance import REPORT, verify_data
from lexical_nada_audit import read


class NovelPerformanceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(REPORT)
        verify_data(cls.report)

    def test_complete_samples_and_summaries_are_verified(self):
        verify_data(self.report)

    def test_uncached_output_must_match_independent_cached_stream(self):
        report = deepcopy(self.report)
        report["cache_parity"][0]["jsonl_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            verify_data(report)

    def test_spacing_and_filter_workloads_cannot_be_omitted(self):
        report = deepcopy(self.report)
        report["workloads"].pop()
        with self.assertRaises(AssertionError):
            verify_data(report)

    def test_summary_cannot_hide_a_slow_sample(self):
        report = deepcopy(self.report)
        report["workloads"][0]["summary"]["after"]["median_seconds"] /= 2
        with self.assertRaises(AssertionError):
            verify_data(report)

    def test_raw_annotations_cannot_be_reported_as_unannotated_speed(self):
        report = deepcopy(self.report)
        report["workloads"][0]["samples"][0]["command"] += [
            "--dictionary",
            "/data/dictionaries/krdict/krdict.db",
        ]
        with self.assertRaises(AssertionError):
            verify_data(report)


if __name__ == "__main__":
    unittest.main()
