import copy,unittest
import giroseo_broad_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.values=audit.inputs()
 def reject(self,fn,reason):
  v=copy.deepcopy(self.values);fn(v)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*v)
 def test_all_actual_unchanged_workloads(self):self.assertEqual(audit.inspect(*self.values)['frames'],1128312)
 def test_missing_workload(self):self.reject(lambda v:v[0]['comparisons'].pop(),'complete original workloads')
 def test_previous_stream(self):self.reject(lambda v:v[1]['comparisons'][0].update(after_jsonl_sha256='0'*64),'unchanged stream fingerprint')
 def test_after_stream(self):self.reject(lambda v:v[0]['comparisons'][0].update(after_jsonl_sha256='0'*64),'unchanged stream fingerprint')
 def test_original_source(self):self.reject(lambda v:v[2]['sources'][v[0]['comparisons'][0]['source']].update(text='fabricated'),'original source bytes')
 def test_filter_flags(self):self.reject(lambda v:v[0]['comparisons'][1]['commands'][1].pop(),'filter and spacing flags')
 def test_invented_observation(self):self.reject(lambda v:v[0]['individual_additions'].append({'id':'invented'}),'zero-change accounting')
 def test_suppressed_frame(self):self.reject(lambda v:v[0]['comparisons'][0]['changed_frames'].append({'id':'invented'}),'suppressed changed frames')
 def test_unexecuted_stream(self):self.reject(lambda v:v[0]['comparisons'][0].update(exit_codes=[0,1]),'complete stream execution')
 def test_false_coverage_claim(self):self.reject(lambda v:v[0].update(full_coverage_complete=True),'terminal original broad replay')
if __name__=='__main__':unittest.main()
