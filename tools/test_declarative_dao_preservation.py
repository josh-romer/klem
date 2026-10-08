import copy,unittest
import declarative_dao_preservation as audit

class Preservation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.values=audit.values()
    def rejected(self,change):
        values=copy.deepcopy(self.values);change(*values)
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration)):audit.verify(*values)
    def test_complete_capture(self):self.assertEqual(audit.verify(*self.values)['frames'],1128312)
    def test_lost_observation(self):self.rejected(lambda r,b,i,n:r['individual_additions'].pop())
    def test_changed_original_context(self):self.rejected(lambda r,b,i,n:r['comparisons'][0]['changed_frames'][0].update(complete_original_line='invented'))
    def test_lost_prior_parent(self):self.rejected(lambda r,b,i,n:r['actual_prior_companions'].clear())
    def test_lost_native_owner(self):
        def change(r,b,i,n):
            ident=next(e['id'] for row in r['individual_additions'] for member in row['dictionary_owners'] for e in member['entries']);n.pop(ident)
        self.rejected(change)
    def test_changed_spacing(self):self.rejected(lambda r,b,i,n:r['individual_spacing_additions'][0]['hypothesis'].update(spaced='arbitrary'))
    def test_changed_before_stream(self):self.rejected(lambda r,b,i,n:r['comparisons'][0].update(before_jsonl_sha256='0'*64))
    def test_missing_prior_candidate(self):
        def change(r,b,i,n):r['comparisons'][0]['changed_frames'][0]['after']['analysis']['analyses'].pop(0)
        self.rejected(change)
if __name__=='__main__':unittest.main()
