import copy
import unittest
import gentle_command_history_audit as audit


class HistoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.actual = audit.inputs()

    def reject(self, change, message):
        history = copy.deepcopy(self.actual[0])
        change(history)
        with self.assertRaisesRegex(AssertionError, message):
            audit.inspect(history, *self.actual[1:])

    def test_complete_actual_capture(self):
        self.assertEqual(audit.inspect(*self.actual)['individual_unjudged_additions'], 18)

    def test_missing_path(self):
        self.reject(lambda h: h['individual_additions'].pop(), 'every exact individual addition')

    def test_changed_raw_head(self):
        self.reject(lambda h: h['individual_additions'][0]['analysis']['lemmas'][0].update(text='invented다'), 'every exact individual addition')

    def test_missing_original_witness(self):
        self.reject(lambda h: h['individual_additions'][0]['original_occurrences'].pop(), 'every exact individual addition')

    def test_original_record_cannot_be_rewritten(self):
        self.reject(lambda h: h['individual_additions'][0]['original_occurrences'][0]['complete_original_record'].update(normalized='invented'), 'every exact individual addition')

    def test_context_cannot_be_abbreviated(self):
        def change(h):
            row = next(r for r in h['individual_additions'] if r['original_contexts'])
            row['original_contexts'][0]['complete_original_record']['original_group'].clear()
        self.reject(change, 'every exact individual addition')

    def test_source_digest_cannot_be_refreshed(self):
        self.reject(lambda h: h['source_files_sha256'].update({next(iter(h['source_files_sha256'])): '0'*64}), 'unchanged original fixture bytes')

    def test_prior_candidate_order_cannot_be_changed(self):
        def change(h):
            row = next(iter(h['changed_words'].values()))
            row['before']['analyses'].reverse()
        self.reject(change, 'exact eight captured histories')

    def test_new_path_cannot_be_declared_contextually_correct(self):
        self.reject(lambda h: h['individual_additions'][0].update(contextual_verdict='required'), 'every exact individual addition')

    def test_review_cannot_be_inferred_from_dictionary_match(self):
        self.reject(lambda h: h['individual_additions'][0].update(independent_review='complete'), 'every exact individual addition')

    def test_exact_prior_parent_cannot_be_replaced(self):
        self.reject(lambda h: h['individual_additions'][0]['exact_parent']['rules'].append('invented'), 'every exact individual addition')

    def test_missing_actual_prior_counterpart(self):
        def change(h):
            parent = h['individual_additions'][0]['parent_surface']
            h['actual_prior_companions'][parent]['analyses'].clear()
        self.reject(change, 'every complete actual prior counterpart preserved')

    def test_unrelated_parent_word_cannot_be_added(self):
        self.reject(lambda h: h['actual_prior_companions'].update(invented={}), 'every complete actual prior counterpart preserved')

    def test_extra_fabricated_prior_path_is_rejected(self):
        def change(h):
            parent = next(iter(h['actual_prior_companions'].values()))
            extra = copy.deepcopy(parent['analyses'][0])
            extra['lemmas'][0]['text'] = 'invented다'
            parent['analyses'].append(extra)
        self.reject(change, 'every complete actual prior counterpart preserved')

    def test_archived_prior_capture_cannot_be_refreshed(self):
        with self.assertRaisesRegex(AssertionError, 'original immutable prior-parent capture bytes'):
            audit.inspect(*self.actual[:4], b'{}')

    def test_prior_executable_cannot_be_replaced(self):
        self.reject(lambda h: h.update(prior_cli_sha256='0'*64), 'exact prior executable bytes')


if __name__ == '__main__':
    unittest.main()
