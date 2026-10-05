"""Guard source ownership, retained alternatives, API order and filtered exports."""
import copy
import unittest

import hada_remaining_context as context
import hada_remaining_runtime as runtime


class RuntimeGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = runtime.audit.read(runtime.REPORT)

    def rejects(self, report):
        with self.assertRaises(AssertionError):
            runtime.inspect(report)

    def test_complete_runtime(self):
        self.assertEqual(runtime.inspect(self.report), (1298, 752, 138, 34, 6))

    def test_root_cannot_invent_standalone_entry(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['source_owner']['base_role'] == 'root')
        diagram['formation_title'] = diagram['formation_title'].replace('Root status does not assert a standalone dictionary entry.', '')
        self.rejects(report)

    def test_bound_noun_cannot_borrow_lexical_label(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['source_owner']['base_role'] == 'bound_noun')
        diagram['formation_label'] = 'Action / verb formation'
        self.rejects(report)

    def test_original_whole_reading_must_remain_selectable(self):
        report = copy.deepcopy(self.report)
        diagram = report['browser']['diagrams'][0]
        diagram['whole_selected'] = diagram['selected']
        self.rejects(report)

    def test_export_cannot_omit_reading(self):
        report = copy.deepcopy(self.report)
        record = next(r for r in report['browser']['checks'][0]['exported_records'] if r.get('analysis'))
        record['analysis']['analyses'].pop()
        self.rejects(report)


class ContextGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = context.audit.read(context.REPORT)

    def test_complete_contexts(self):
        self.assertEqual(len(context.inspect(self.report)), 78)

    def test_filtered_baseline_cannot_change_old_reading(self):
        report = copy.deepcopy(self.report)
        report['before']['compatible']['jsonl'] = report['before']['raw']['jsonl']
        report['before']['compatible']['sha256'] = report['before']['raw']['sha256']
        with self.assertRaises(AssertionError):
            context.inspect(report)

    def test_missing_context_stream(self):
        report = copy.deepcopy(self.report)
        del report['runs']['raw']['NFD-cached']
        with self.assertRaises(AssertionError):
            context.inspect(report)


if __name__ == '__main__':
    unittest.main()
