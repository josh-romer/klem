"""Mutate real source captures and rebind bytes to exercise semantic guards."""
import copy,importlib.util,json,unittest
from pathlib import Path
import additive_ppundeoreo_audit as a
class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.reports=a.inputs()
    def reject(self,index,change):
        reports=list(self.reports);reports[index]=copy.deepcopy(reports[index]);change(reports[index])
        with self.assertRaises((AssertionError,KeyError,ValueError,StopIteration,TypeError)):
            a.inspect(*reports)
    def change_rows(self,report,fn):
        run=report['runs'][0];rows=list(map(json.loads,run['jsonl'].splitlines()));fn(rows)
        run['jsonl']=''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows)
        run['sha256']=a.sha(run['jsonl'].encode())
    def test_actual_complete_source_and_boundary_capture(self):
        self.assertEqual(a.inspect(*self.reports)['authored_observations'],216)
    def test_original_dialogue_group_cannot_disappear(self):self.reject(0,lambda r:r['all_original_groups'].pop())
    def test_original_native_annotation_cannot_change(self):
        self.reject(1,lambda r:r['complete_native_entries']['krdict:74341']['senses'][0]['notes'].append('invented'))
    def test_source_sense_cannot_disappear(self):self.reject(0,lambda r:r['sqlite_entries']['krdict:74021']['senses'].clear())
    def test_native_same_head_closure_cannot_shrink(self):self.reject(1,lambda r:r['complete_native_entries'].pop('krdict:74021'))
    def test_a_unicode_mode_cannot_disappear(self):self.reject(2,lambda r:r['runs'].pop())
    def test_original_utf8_span_cannot_shift(self):
        self.reject(2,lambda r:self.change_rows(r,lambda rows:rows[0]['span'].__setitem__('start',1)))
    def test_original_whole_ending_cannot_disappear(self):
        def change(rows):
            for row in rows:
                if row.get('analysis'):
                    row['analysis']['analyses']=[p for p in row['analysis']['analyses'] if 'ending.additive_ppundeoreo' not in p['rules']]
        self.reject(2,lambda r:self.change_rows(r,change))
    def test_a_prior_raw_path_cannot_disappear(self):
        self.reject(2,lambda r:self.change_rows(r,lambda rows:rows[0]['analysis']['analyses'].clear()))
    def test_one_boundary_observation_cannot_disappear(self):self.reject(3,lambda r:r['observations'].pop())
    def test_scoped_marker_status_cannot_change(self):
        self.reject(3,lambda r:r['observations'][0]['statuses'].append('incompatible'))
    def test_source_occurrence_cannot_be_reassigned(self):self.reject(5,lambda r:r[0]['source_occurrence'].__setitem__('group_index',99))
    def test_independent_review_cannot_be_claimed(self):self.reject(5,lambda r:r[0].__setitem__('independent_review','complete'))
    def test_matched_owner_identity_cannot_change(self):self.reject(1,lambda r:r['matched_owner_ids'].__setitem__(0,'krdict:invented'))
if __name__=='__main__':unittest.main()
