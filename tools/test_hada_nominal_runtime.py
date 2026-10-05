"""Reject borrowed API orders, changed native sources and incorrect browser labels."""
import copy
import unittest

import hada_nominal_runtime as runtime


class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = runtime.read(runtime.REPORT)

    def test_complete_receipts(self):
        self.assertEqual(runtime.inspect(self.report), (1298, 708, 138, 8, 6))

    def test_changed_retained_order(self):
        report = copy.deepcopy(self.report)
        batch = report['api']['batches'][0]
        row = next(i for i, r in enumerate(batch['response']['records']) if r.get('analysis'))
        batch['response']['breakdowns'][row][0] = []
        with self.assertRaises(AssertionError):
            runtime.inspect(report)

    def test_missing_original_sense(self):
        report = copy.deepcopy(self.report)
        report['api']['complete_native_entries']['krdict:88475']['senses'].pop()
        with self.assertRaises(AssertionError):
            runtime.inspect(report)

    def test_adjective_label_cannot_be_verbal(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['word'] == '건강해요')
        diagram['formation_label'] = 'Action / verb formation'
        with self.assertRaises(AssertionError):
            runtime.inspect(report)

    def test_filtered_export_cannot_lose_candidates(self):
        report = copy.deepcopy(self.report)
        report['browser']['checks'][0]['exported_records'].pop()
        with self.assertRaises(AssertionError):
            runtime.inspect(report)


if __name__ == '__main__':
    unittest.main()
