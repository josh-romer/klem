"""Require the full Sena ledger behind the older command-family reader."""
import copy
import json
import unittest
from unittest.mock import patch

import friendly_command_audit as legacy
import friendly_command_gena_ledger_audit as gena


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values=gena.inputs()
        cls.raw=(legacy.ROOT/'tests/fixtures/validity.json').read_bytes()
        assert cls.raw==cls.values['actual_current_raw']

    def reject(self,values,reason=None):
        with patch.object(gena,'inputs',return_value=values):
            with self.assertRaisesRegex(AssertionError,reason) if reason else self.assertRaises((AssertionError,KeyError)):
                legacy.command_ledger(self.raw)

    def child_case(self,change):
        values=dict(self.values);values['sena_append']=dict(values['sena_append'])
        ledger=json.loads(values['sena_append']['current_raw']);change(ledger)
        values['sena_append']['current_raw']=(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode()
        return values

    def test_complete_current_reader_and_exact_old_owner_view(self):
        with patch.object(gena,'inspect',wraps=gena.inspect) as guard:
            old=legacy.command_ledger()
        guard.assert_called_once()
        self.assertEqual(guard.call_args.args[0]['actual_current_raw'],self.raw)
        self.assertEqual(old,json.loads(self.values['parent_raw']))
        self.assertEqual(len(old['cases']),35740)

    def test_complete_legacy_audit_remains_valid(self):
        self.assertEqual(legacy.inspect(),(60,1874,4794,7))

    def test_actual_binding_cannot_be_removed(self):
        values=dict(self.values);values.pop('actual_current_raw');self.reject(values)

    def test_entire_sena_child_cannot_be_removed(self):
        values=dict(self.values);values.pop('sena_append');self.reject(values)

    def test_actual_binding_cannot_be_replaced_by_checkpoint(self):
        values=dict(self.values,actual_current_raw=self.values['current_raw'])
        self.reject(values,'complete current command ledger matches guarded Gena source')

    def test_missing_required_sena_case(self):
        self.reject(self.child_case(lambda r:r['cases'].pop(35764)),'complete35764')

    def test_missing_forbidden_sena_case(self):
        def change(r):
            index=next(i for i in range(35764,35789) if r['cases'][i]['judgments'][0]['verdict']=='forbidden');r['cases'].pop(index)
        self.reject(self.child_case(change),'complete35764')

    def test_changed_sena_candidate(self):
        self.reject(self.child_case(lambda r:r['cases'][-1]['judgments'][0].update(lemmas=['invented'])),'only exact25')

    def test_changed_original_gena_case(self):
        self.reject(self.child_case(lambda r:r['cases'][35740]['judgments'][0].update(reason='invented')),'all35764 parent')

    def test_unknown_sena_tail(self):
        self.reject(self.child_case(lambda r:r['cases'].append(dict(id='unjudged-tail',surface='중세나',judgments=[]))),'complete35764')

    def test_changed_current_review(self):
        values=dict(self.values);values['sena_append']=dict(values['sena_append'])
        reviews=copy.deepcopy(values['sena_append']['current_reviews']);reviews['entries'][-1]['scope']='invented';values['sena_append']['current_reviews']=reviews
        self.reject(values)

    def test_foreign_current_raw_cannot_be_borrowed(self):
        ledger=json.loads(self.raw);ledger['cases'][-1]['surface']='invented'
        raw=(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n').encode()
        with self.assertRaisesRegex(AssertionError,'complete current command ledger matches guarded Gena source'):
            legacy.command_ledger(raw)


if __name__=='__main__':unittest.main()
