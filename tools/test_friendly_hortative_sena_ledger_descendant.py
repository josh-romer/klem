"""Require the entire Sena append behind every historical ledger view."""
import copy
import json
import unittest

import friendly_command_gena_ledger_audit as gena
import gentle_command_long_ledger_audit as long
import gentle_command_ledger_audit as gentle


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = [(gena, gena.inputs(), ('sena_append',), 'actual_current_raw', 'actual_current_reviews'),
                      (long, long.inputs(), ('gena_append', 'sena_append'), 'actual_entire_current_raw', 'actual_entire_current_reviews'),
                      (gentle, gentle.inputs(), ('long_append', 'gena_append', 'sena_append'), 'actual_entire_current_raw', 'actual_entire_current_reviews')]

    def changed(self, original, path, mutate):
        value = copy.copy(original); node = value
        for key in path[:-1]:
            node[key] = copy.copy(node[key]); node = node[key]
        key = path[-1]; node[key] = copy.deepcopy(node[key]); mutate(node, key)
        return value

    def reject(self, relative, mutate, reason):
        for module, original, child, _, _ in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = self.changed(original, child + relative, mutate)
                with self.assertRaisesRegex(AssertionError, reason): module.inspect(value)

    def reject_case(self, change, reason):
        def mutate(node, key):
            ledger = json.loads(node[key]); change(ledger)
            node[key] = (json.dumps(ledger, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(('current_raw',), mutate, reason)

    def test_complete_entire_current_append(self):
        for module, value, _, _, _ in self.inputs:
            with self.subTest(ancestor=module.__name__):
                result = module.inspect(value)
                self.assertEqual((result['verified_current_shared_cases'], result['verified_current_shared_reviews']), (35789, 521))
                self.assertEqual((result['verified_current_required'], result['verified_current_forbidden']), (31488, 4318))
                self.assertEqual(result['sena_added_cases'], 25)
                self.assertFalse(result['full_coverage_complete'])
                self.assertIn('Original Gena checkpoint', result['legacy_checkpoint_fields'])

    def test_required_child_cannot_be_removed(self):
        for module, original, child, _, _ in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = copy.copy(original); node = value
                for key in child[:-1]:
                    node[key] = copy.copy(node[key]); node = node[key]
                node.pop(child[-1])
                with self.assertRaises(KeyError): module.inspect(value)

    def test_entire_raw_binding_cannot_be_removed(self):
        for module, original, _, raw, _ in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = copy.copy(original); value.pop(raw)
                with self.assertRaises(KeyError): module.inspect(value)

    def test_entire_review_binding_cannot_be_removed(self):
        for module, original, _, _, reviews in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = copy.copy(original); value.pop(reviews)
                with self.assertRaises(KeyError): module.inspect(value)

    def test_historical_parent_cannot_hide_tail(self):
        for module, original, child, raw, _ in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = copy.copy(original); complete = original
                for key in child: complete = complete[key]
                value[raw] = complete['original']['parent_raw']
                with self.assertRaisesRegex(AssertionError, 'mandatory entire'): module.inspect(value)

    def test_historical_reviews_cannot_hide_tail(self):
        for module, original, child, _, reviews in self.inputs:
            with self.subTest(ancestor=module.__name__):
                value = copy.copy(original); complete = original
                for key in child: complete = complete[key]
                value[reviews] = json.loads(complete['original']['parent_reviews_raw'])
                with self.assertRaisesRegex(AssertionError, 'mandatory entire'): module.inspect(value)

    def test_missing_required_tail(self):
        self.reject_case(lambda ledger: ledger['cases'].pop(35764), 'complete35764')

    def test_missing_forbidden_tail(self):
        def change(ledger):
            index = next(i for i in range(35764, 35789) if ledger['cases'][i]['judgments'][0]['verdict'] == 'forbidden')
            ledger['cases'].pop(index)
        self.reject_case(change, 'complete35764')

    def test_unknown_unjudged_tail(self):
        self.reject_case(lambda ledger: ledger['cases'].append(dict(id='unjudged-tail', surface='중세나', judgments=[])), 'complete35764')

    def test_changed_original_gena_candidate(self):
        self.reject_case(lambda ledger: ledger['cases'][35740]['judgments'][0].update(lemmas=['invented']), 'all35764 parent')

    def test_changed_original_sena_candidate(self):
        self.reject_case(lambda ledger: ledger['cases'][35764]['judgments'][0].update(lemmas=['invented']), 'only exact25')

    def test_new_runtime_rule_requirement(self):
        self.reject_case(lambda ledger: ledger['cases'][35764]['judgments'][0].update(required_rules=['invented']), 'only exact25')

    def test_dropped_forbidden_target(self):
        def change(ledger):
            case = next(case for case in ledger['cases'][35764:] if case['judgments'][0]['verdict'] == 'forbidden')
            case['judgments'].clear()
        self.reject_case(change, 'only exact25')

    def test_changed_source_declaration(self):
        self.reject_case(lambda ledger: ledger['sources'].update({next(iter(ledger['sources'])): 'https://example.invalid'}), 'source declaration')

    def test_changed_ledger_metadata(self):
        self.reject_case(lambda ledger: ledger.update(unreviewed_is_correct=True), 'ledger metadata')

    def test_changed_serialized_parent(self):
        self.reject(('current_raw',), lambda node, key: node.update({key: node[key].replace(b'"cases": [\n    {', b'"cases": [\n     {', 1)}), 'serialized parent')

    def test_missing_bounded_review(self):
        self.reject(('current_reviews',), lambda node, key: node[key]['entries'].pop(), 'complete520')

    def test_changed_old_review(self):
        self.reject(('current_reviews',), lambda node, key: node[key]['entries'][0].update(scope='all Korean'), 'all520')

    def test_unbounded_new_review(self):
        self.reject(('current_reviews',), lambda node, key: node[key]['entries'][-1].update(remaining=''), 'exact bounded')

    def test_missing_original_dialogue_judgment(self):
        self.reject(('current_reviews',), lambda node, key: node[key]['entries'][-1]['judgments'].pop(), 'exact bounded')

    def test_changed_original_native_group(self):
        self.reject(('original', 'author_raw'), lambda node, key: node.update({key: node[key].replace('하세나'.encode(), '합세나'.encode(), 1)}), 'original preauthored suite')


    def historical_long_view(self):
        complete = self.inputs[1][1]
        value = gentle.original_inputs()
        value.update(current_raw=complete['parent_raw'],
                     current_reviews=json.loads(complete['parent_reviews_raw']),
                     actual_current_raw=complete['current_raw'],
                     actual_current_reviews=complete['current_reviews'], long_append=complete)
        return value

    def test_explicit_historical_long_view_still_checks_entire_current(self):
        result = gentle.inspect(self.historical_long_view())
        self.assertEqual((result['complete_current_cases'], result['complete_current_reviews']), (35740, 519))
        self.assertEqual((result['verified_current_shared_cases'], result['verified_current_shared_reviews']), (35789, 521))
        self.assertEqual(result['sena_added_cases'], 25)
        self.assertFalse(result['full_coverage_complete'])

    def test_explicit_historical_long_view_cannot_omit_sena_child(self):
        value = self.historical_long_view()
        value['long_append'] = copy.copy(value['long_append'])
        value['long_append']['gena_append'] = copy.copy(value['long_append']['gena_append'])
        value['long_append']['gena_append'].pop('sena_append')
        with self.assertRaises(KeyError): gentle.inspect(value)


if __name__ == '__main__':
    unittest.main()
