"""Keep current Gena validation mandatory behind historical ledger views."""
import copy
import json
import unittest

import gentle_command_ledger_audit as gentle
import gentle_command_long_ledger_audit as long
import friendly_command_gena_ledger_audit as gena


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = long.inputs()

    def reject(self,path,change,reason=None):
        value = self.values.copy();node = value
        if path:
            for key in path[:-1]:
                node[key] = copy.copy(node[key]);node = node[key]
            node[path[-1]] = copy.deepcopy(node[path[-1]]);change(node[path[-1]])
        else:
            change(value)
        if reason is None:
            with self.assertRaises(KeyError): long.inspect(value)
        else:
            with self.assertRaisesRegex(AssertionError,reason): long.inspect(value)

    def test_current_append_remains_mandatory(self):
        result = long.inspect(self.values)
        self.assertEqual((result['active_cases'],result['active_reviews']),(35740,519))
        self.assertEqual((result['complete_current_cases'],result['complete_current_reviews']),(35764,520))
        self.assertEqual((result['complete_current_required'],result['complete_current_forbidden']),(31469,4312))
        self.assertEqual(result['gena_added_cases'],24)
        self.assertFalse(result['full_coverage_complete'])

    def test_gentle_defaults_check_entire_current_ledger(self):
        result = gentle.inspect(gentle.inputs())
        self.assertEqual((result['complete_current_cases'],result['complete_current_reviews']),(35764,520))
        self.assertEqual((result['verified_active_shared_cases'],result['verified_active_shared_reviews']),(35764,520))

    def test_actual_own_gena_promotion(self):
        result = gena.inspect(gena.inputs())
        self.assertTrue(result['actual_shared_promotion'])
        self.assertFalse(result['historical_and_broad_hypotheses_promoted'])

    def test_missing_descendant_guard(self):
        self.reject((),lambda r:r.pop('gena_append'))

    def test_actual_raw_tail_cannot_be_hidden(self):
        value = self.values.copy();value['actual_current_raw']=value['current_raw']
        with self.assertRaisesRegex(AssertionError,'mandatory complete current Gena ledger bytes'):long.inspect(value)

    def test_actual_review_tail_cannot_be_hidden(self):
        self.reject(('actual_current_reviews','entries'),lambda r:r.pop(),'mandatory complete current Gena review fields')

    def test_current_review_scope_cannot_be_rewritten(self):
        self.reject(('gena_append','current_reviews','entries',519),lambda r:r.update(scope='all Korean'),'mandatory complete current Gena review fields')

    def test_parent_ledger_cannot_be_borrowed(self):
        self.reject(('gena_append',),lambda r:r.update(parent_raw=b'{}'),'historical long matches exact Gena parent')

    def test_parent_reviews_cannot_be_borrowed(self):
        self.reject(('gena_append',),lambda r:r.update(parent_reviews_raw=b'{}'),'historical long reviews match exact Gena parent')

    def test_unknown_new_tail_rejected(self):
        value = copy.copy(self.values);complete = copy.copy(value['gena_append'])
        ledger = json.loads(complete['current_raw'])
        ledger['cases'].append(dict(id='unjudged-tail',surface='보게나',judgments=[]))
        raw=(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode()
        complete['current_raw']=value['actual_current_raw']=raw;value['gena_append']=complete
        with self.assertRaisesRegex(AssertionError,'complete35740 parent plus24 cases'):long.inspect(value)

    def test_unknown_review_tail_rejected(self):
        value=copy.copy(self.values);complete=copy.copy(value['gena_append'])
        reviews=copy.deepcopy(complete['current_reviews']);reviews['entries'].append(dict(id='unjudged-owner'))
        complete['current_reviews']=value['actual_current_reviews']=reviews;value['gena_append']=complete
        with self.assertRaisesRegex(AssertionError,'complete519 reviews plus one bounded owner'):long.inspect(value)

    def test_changed_gena_candidate_rejected_even_when_bindings_agree(self):
        value=copy.copy(self.values);complete=copy.copy(value['gena_append'])
        ledger=json.loads(complete['current_raw']);ledger['cases'][-1]['judgments'][0]['lemmas']=['invented']
        raw=(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode()
        complete['current_raw']=value['actual_current_raw']=raw;value['gena_append']=complete
        with self.assertRaisesRegex(AssertionError,'only exact24 preauthored cases appended'):long.inspect(value)


if __name__ == '__main__':
    unittest.main()
