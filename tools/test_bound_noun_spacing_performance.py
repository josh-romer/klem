import copy,unittest
from bound_noun_spacing_performance import ROOT,inspect,read
class Evidence(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.report=read(ROOT/'docs/bound-noun-spacing-performance-retry1.json.gz')
 def rejected(self,change):
  report=copy.deepcopy(self.report);change(report)
  with self.assertRaises((AssertionError,KeyError,ValueError)):inspect(report)
 def test_original_complete_capture(self):self.assertEqual(inspect(self.report)['paired_samples'],80)
 def test_missing_workload(self):self.rejected(lambda r:r['workloads'].pop())
 def test_missing_pair(self):self.rejected(lambda r:r['workloads'][0]['samples'].pop())
 def test_wrong_binary(self):self.rejected(lambda r:r['workloads'][0]['samples'][0]['command'].__setitem__(0,'invented'))
 def test_changed_median(self):self.rejected(lambda r:r['workloads'][0]['summary']['before'].update(median_seconds=0))
 def test_lost_cpu_affinity(self):self.rejected(lambda r:r.update(cpu_affinity=[]))
 def test_short_cache_stream(self):self.rejected(lambda r:r['cache_parity'][0]['checks'][0].update(records=1))
 def test_invented_stream_digest(self):self.rejected(lambda r:r['cache_parity'][0]['checks'][0].update(sha256='0'*64))
 def test_lost_cache_budget(self):self.rejected(lambda r:r['cache_parity'][0]['checks'][0].update(cache_bytes=1))
 def test_false_package_identity(self):self.rejected(lambda r:r.update(package_sha256='0'*64))
if __name__=='__main__':unittest.main()
