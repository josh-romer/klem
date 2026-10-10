"""Reject false unchanged-stream claims, missing inputs and hidden changes."""
import unittest
from unittest.mock import patch

import fear_lsera_broad_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, obj, changes, reason):
        with patch.dict(obj, changes):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(*self.evidence)

    def test_complete_capture(self):
        self.assertEqual(audit.inspect(*self.evidence)['unchanged_streams'], 8)

    def test_missing_workload(self):
        self.reject(self.evidence[0], {'comparisons': self.evidence[0]['comparisons'][:-1]}, 'eight complete workloads')

    def test_parent_digest(self):
        self.reject(self.evidence[0]['comparisons'][0], {'before_jsonl_sha256': '0' * 64}, 'completed parent stream')

    def test_changed_current_digest(self):
        self.reject(self.evidence[0]['comparisons'][0], {'after_jsonl_sha256': '0' * 64}, 'current stream byte parity')

    def test_missing_original_frame(self):
        self.reject(self.evidence[0]['comparisons'][0], {'records': 0}, 'original frame count')

    def test_failed_producer(self):
        self.reject(self.evidence[0]['comparisons'][0], {'exit_codes': [1, 0]}, 'successful complete')

    def test_unverified_byte_conservation(self):
        self.reject(self.evidence[0]['comparisons'][0], {'original_bytes_conserved': False}, 'byte-conserving')

    def test_missing_spacing_flag(self):
        run = self.evidence[0]['comparisons'][-1]
        self.reject(run, {'commands': [c[:-1] for c in run['commands']]}, 'filter and spacing flags')

    def test_hidden_changed_frame(self):
        self.reject(self.evidence[0]['comparisons'][0], {'changed_frames': [{'invented': True}]}, 'unchanged frames')

    def test_hidden_new_path(self):
        self.reject(self.evidence[0], {'individual_additions': [{'invented': True}]}, 'zero emitted path')

    def test_hidden_new_spacing(self):
        self.reject(self.evidence[0], {'individual_spacing_additions': [{'invented': True}]}, 'zero emitted path')

    def test_hidden_probe_delta(self):
        self.reject(self.evidence[0], {'individual_probe_diagnostics': [{'invented': True}]}, 'zero changed diagnostic')

    def test_falsified_producer(self):
        self.reject(self.evidence[0]['producer'], {'sha256': '0' * 64}, 'producer bytes')

    def test_unverified_input_freeze(self):
        self.reject(self.evidence[0], {'inputs_unchanged': False}, 'frozen broad inputs')

    def test_unsupported_coverage_claim(self):
        self.reject(self.evidence[0], {'full_coverage_complete': True}, 'bounded scope')


if __name__ == '__main__':
    unittest.main()
