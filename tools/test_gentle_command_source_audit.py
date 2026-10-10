"""Reject rewritten gentle-command source, judgments, homonyms and baseline claims."""
import copy
import unittest
import gentle_command_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.values)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def test_complete_original_source(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['cases'], result['required'], result['native_owners']), (23, 15, 47))
        self.assertFalse(result['full_coverage_complete'])

    def test_original_source_archive_cannot_be_refreshed(self):
        self.reject(lambda v: v['raw'].update({'gentle-command-original-source.json': b'{}'}), 'exact original source Native and installed baseline bytes')

    def test_source_fixture_cannot_change(self):
        self.reject(lambda v: v.update(source_raw=b'{}'), 'exact source fixture retained')

    def test_private_judgments_cannot_change(self):
        self.reject(lambda v: v.update(suite_raw=b'{}'), 'exact independently authored private judgments')

    def test_original_source_context_cannot_be_cropped(self):
        self.reject(lambda v: v['source']['items'][0].update(complete_original_group=['오렴']), 'original source fields retained')

    def test_native_attachment_notes_cannot_expand(self):
        self.reject(lambda v: v['entries'][0]['krdict:79340'].update(notes=['all predicates']), 'every original imported Native field')

    def test_native_homonym_cannot_disappear(self):
        self.reject(lambda v: v['native'][0]['LexicalResource']['Lexicon']['LexicalEntry'].pop(), 'every original Native fixture field and order')

    def test_native_boundary_owner_cannot_change(self):
        self.reject(lambda v: v['entries'][1].pop(next(iter(v['entries'][1]))), 'every original imported Native field')

    def test_ending_catalog_fixture_cannot_omit_an_owner(self):
        self.reject(lambda v: v['ending_native']['LexicalResource']['Lexicon']['LexicalEntry'].pop(), 'offline catalog imports both exact ending owners')

    def test_required_judgment_cannot_be_replaced(self):
        self.reject(lambda v: v['suite']['cases'][0]['judgments'][0].update(lemmas=['invented']), 'original private judgment fields retained')

    def test_forbidden_boundary_cannot_be_promoted(self):
        self.reject(lambda v: v['suite']['cases'][14]['judgments'][0].update(verdict='required'), 'original private judgment fields retained')

    def test_auxiliary_role_cannot_become_predicate(self):
        self.reject(lambda v: v['suite']['cases'][-1]['judgments'][0].update(lemma_kinds=['predicate','predicate']), 'original private judgment fields retained')

    def test_baseline_lexical_recall_cannot_be_invented(self):
        self.reject(lambda v: v['baseline']['runs'][0]['observations'][0].update(lexical_path_indices=[0]), 'every original installed observation retained')

    def test_baseline_cannot_drop_unicode_filter_policy(self):
        self.reject(lambda v: v['baseline']['runs'].pop(), 'every original installed observation retained')

    def test_baseline_output_cannot_be_refreshed(self):
        self.reject(lambda v: v['baseline']['runs'][0].update(jsonl=''), 'every original installed observation retained')

    def test_label_cannot_borrow_willingness_ownership(self):
        self.reject(lambda v: v['label']['sources'][0].update(id=76564), 'label cites its original ending owners')


if __name__ == '__main__':
    unittest.main()
