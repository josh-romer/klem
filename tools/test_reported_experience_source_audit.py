"""Reject rewritten classes, incomplete contexts and hidden scope changes."""
import copy,unittest
import reported_experience_source_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,change,reason):
  v=copy.deepcopy(self.evidence);change(v)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*v)
 def test_actual_original_scope(self):self.assertEqual(audit.inspect(*self.evidence)['complete_original_groups'],51)
 def test_expression_reclassified_as_ending(self):self.reject(lambda v:v[0]['complete_imported_entries']['krdict:86687'].update(pos='어미'),'original expression POS')
 def test_missing_group(self):self.reject(lambda v:v[0]['complete_groups'].pop(),'complete original groups')
 def test_text_rewritten(self):self.reject(lambda v:v[0].update(complete_source_text='fabricated'),'original text')
 def test_native_homonym_removed(self):self.reject(lambda v:v[1]['entries'].pop('krdict:30194'),'Native closure')
 def test_source_context_shortened(self):self.reject(lambda v:v[3][0]['complete_original_group'].__setitem__(0,'참으랍디까'),'authored context')
 def test_source_case_changed(self):self.reject(lambda v:v[4]['cases'][0]['judgments'][0].update(morphemes=['습디까']),'structural reading')
 def test_conditional_case_discarded(self):self.reject(lambda v:v[5]['cases'].pop(),'retained dictionary-dependent')
 def test_original_failed_case_changed(self):self.reject(lambda v:v[6]['cases'][-3]['judgments'][0].update(reason='hidden change'),'original judgments')
 def test_tension_silently_smoothed(self):
  def change(v):next(p for p in v[3] if p['surface']=='했답디까')['source_tension']=None
  self.reject(change,'cross-source past')
 def test_label_pos_rewritten(self):self.reject(lambda v:v[7]['-답디까']['sources'][0].update(pos='어미'),'label owner role')
 def test_label_identity_rewritten(self):self.reject(lambda v:v[7]['-는답디까']['sources'][0].update(id=86678),'label owner role')
if __name__=='__main__':unittest.main()
