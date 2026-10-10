"""Reject concealed candidate changes and missing individual spacing diagnostics."""
import copy
import unittest
from unittest.mock import patch

import familiar_geurae_broad_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()
        cls.stream = cls.evidence[0]['comparisons'][-1]
        cls.frame = cls.stream['changed_frames'][0]

    def reject(self, obj, changes, reason):
        with patch.dict(obj, changes):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(*self.evidence)

    def test_complete_actual_capture(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual((result['probe_only_observations'], result['added_candidate_paths']), (398, 0))

    def test_missing_workload(self):
        self.reject(self.evidence[0], {'comparisons': self.evidence[0]['comparisons'][:-1]}, 'all eight complete workloads')

    def test_parent_digest(self):
        self.reject(self.stream, {'before_jsonl_sha256': '0' * 64}, 'exact actual completed parent output')

    def test_missing_spacing_flag(self):
        commands = [c[:-1] for c in self.stream['commands']]
        self.reject(self.stream, {'commands': commands}, 'actual workload executables dictionary and flags')

    def test_changed_nonspacing_hash(self):
        self.reject(self.evidence[0]['comparisons'][0], {'after_jsonl_sha256': '0' * 64}, 'six complete nonspacing streams exact')

    def test_missing_changed_frame(self):
        self.reject(self.stream, {'changed_frames': self.stream['changed_frames'][:-1]}, 'all individually changed spacing frames')

    def test_original_context_removed(self):
        self.reject(self.frame, {'complete_original_line': self.frame['after']['surface']}, 'complete original changed context')

    def test_original_span_changed(self):
        self.reject(self.frame['after']['span'], {'start': 0}, 'original changed source byte ownership')

    def test_concealed_added_path(self):
        paths = self.frame['after']['analysis']['analyses']
        self.reject(self.frame['after']['analysis'], {'analyses': [*paths, copy.deepcopy(paths[0])]}, 'every other candidate assessment display and spacing field exact')

    def test_concealed_assessment_change(self):
        self.reject(self.frame['after']['dictionary'], {'readings': []}, 'every other candidate assessment display and spacing field exact')

    def test_concealed_spacing_alternative(self):
        self.reject(self.frame['after']['spacing'], {'alternatives': [{'invented': True}]}, 'every other candidate assessment display and spacing field exact')

    def test_concealed_probe_delta(self):
        self.reject(self.frame['after']['spacing'], {'segment_probes': 99}, 'exact one additional internal segment probe')

    def test_missing_diagnostic(self):
        self.reject(self.evidence[3], {'observations': self.evidence[3]['observations'][:-1]}, 'every individually derived diagnostic and stable ID')

    def test_rewritten_diagnostic_id(self):
        self.reject(self.evidence[3]['observations'][0], {'id': 'invented'}, 'every individually derived diagnostic and stable ID')

    def test_rewritten_diagnostic_scope(self):
        self.reject(self.evidence[3]['observations'][0], {'candidate_paths_unchanged': False}, 'every individually derived diagnostic and stable ID')

    def test_incomplete_surface_inventory(self):
        self.reject(self.evidence[3], {'surfaces': self.evidence[3]['surfaces'][:-1]}, 'complete original diagnostic surface inventory')

    def test_diagnostic_capture_binding(self):
        self.reject(self.evidence[3], {'complete_broad_report_sha256': '0' * 64}, 'complete broad diagnostic binding')

if __name__ == '__main__':
    unittest.main()
