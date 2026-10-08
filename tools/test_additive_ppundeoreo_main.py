import copy,unittest
import additive_ppundeoreo_main as a
B,R,F=a.main_inputs()
class Controls(unittest.TestCase):
 def test_actual_complete_main_capture(self):self.assertEqual(a.inspect(B,R,F)['source_observations'],60)
 def reject(self,index,fn):
  reports=[B,R,F];reports[index]=copy.deepcopy(reports[index]);fn(reports[index])
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):a.inspect(*reports)
 def test_actual_main_cli_identity(self):self.reject(1,lambda r:r.__setitem__('cli_sha256','0'*64))
 def test_main_source_snapshot_required(self):self.reject(0,lambda r:r['snapshot_files'].pop(next(iter(r['snapshot_files']))))
 def test_isolated_capture_cannot_replace_main(self):self.reject(1,lambda r:r.__setitem__('producer',a.inputs()[2]['producer']))
 def test_every_unicode_filter_run_required(self):self.reject(1,lambda r:r['runs'].pop())
 def test_conditional_native_outcome_stays_separate(self):self.reject(2,lambda r:r['observations'][0].__setitem__('present',not r['observations'][0]['present']))
if __name__=='__main__':unittest.main()
