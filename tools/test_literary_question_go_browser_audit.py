import copy,importlib.util,unittest
import literary_question_go_browser_audit as a
R=a.read(a.ROOT/'docs/literary-question-go-main-browser-runtime.json');B=a.read(a.ROOT/'docs/literary-question-go-main-browser.json');N=a.read(a.ROOT/'docs/literary-question-go-boundary-matched-owner-preparation.json.gz')
class Controls(unittest.TestCase):
 def reject(self,part,fn):
  r,b=R,B
  if part=='runtime':r=copy.deepcopy(r);fn(r)
  else:b=copy.deepcopy(b);fn(b)
  with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):a.inspect(r,b,N)
 def test_partial_compiled_source_snapshot_rejected(self):self.reject('runtime',lambda r:r['source_snapshot'].pop('src/engine.rs'))
 def test_owned_server_must_be_stopped(self):self.reject('runtime',lambda r:r.__setitem__('server_stopped',False))
 def test_serve_actual_frontend_assets(self):self.reject('runtime',lambda r:r['asset_checks'][0].__setitem__('sha256','0'*64))
 def test_original_source_frames_cannot_disappear(self):self.reject('browser',lambda r:r['responses'][0]['after']['records'].pop())
 def test_all_boundary_modes_are_checked(self):self.reject('browser',lambda r:r['modeJudgments'].pop())
 def test_diagram_type_is_bound(self):self.reject('browser',lambda r:r['diagrams'][0]['pieces'][0].__setitem__('label','Particle'))
 def test_diagram_order_cannot_drop_components(self):self.reject('browser',lambda r:r['diagrams'][0]['order'].pop())
 def test_conditional_unknown_cannot_be_promoted(self):
  def mutate(r):
   export=r['conditionalExports'][0];row=next(x for x in export['records'] if x.get('analysis') and x['analysis']['normalized']=='학생이던고')
   for status in row['dictionary']['readings']:
    if status['status']=='unknown':status['status']='compatible'
  self.reject('browser',mutate)
 def test_primary_source_panes_cannot_disappear(self):self.reject('browser',lambda r:r['opened'].pop())
 def test_all_native_senses_are_bound(self):self.reject('browser',lambda r:r['native'][0]['response']['entry']['senses'].pop())
 def test_errors_cannot_be_ignored(self):self.reject('browser',lambda r:r['errors'].append('uncaught page error'))
if __name__=='__main__':unittest.main()
