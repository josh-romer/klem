"""Reject incomplete timing samples, false summaries and corrupted cache outputs."""

import copy
import unittest

from copula_expectation_production import read
from reported_dana_performance import REPORT, inspect


class NovelPerformanceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read(REPORT)
        cls.parity = read("docs/reported-dana-cache-parity.json")

    def test_complete_actual_measurements(self):
        self.assertEqual(inspect(self.report, self.parity), 80)

    def test_uncached_output_mismatch_is_rejected(self):
        parity = copy.deepcopy(self.parity)
        parity["streams"][0]["checks"][0]["sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            inspect(self.report, parity)

    def test_omitted_spacing_workload_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["workloads"].pop()
        with self.assertRaises(AssertionError):
            inspect(report, self.parity)

    def test_false_median_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["workloads"][0]["summary"]["after"]["median_seconds"] /= 2
        with self.assertRaises(AssertionError):
            inspect(report, self.parity)

    def test_missing_sample_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["workloads"][0]["samples"].pop()
        with self.assertRaises(AssertionError):
            inspect(report, self.parity)

    def test_nonfinite_duration_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["workloads"][0]["samples"][0]["seconds"] = float("nan")
        with self.assertRaises(AssertionError):
            inspect(report, self.parity)

    def test_changed_binary_anchor_is_rejected(self):
        report = copy.deepcopy(self.report)
        report["cli_sha256"] = "0" * 64
        with self.assertRaises(AssertionError):
            inspect(report, self.parity)

    def test_changed_filter_is_rejected(self):
        parity = copy.deepcopy(self.parity)
        parity["streams"][1]["checks"][0]["command"][5] = "--dict-compatible"
        with self.assertRaises(AssertionError):
            inspect(self.report, parity)


if __name__ == "__main__":
    unittest.main()
