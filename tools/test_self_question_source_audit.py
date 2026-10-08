"""Reject source loss, identity borrowing and hidden source tensions."""
import copy,unittest
import self_question_source_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.evidence=audit.inputs()
 def reject(self,change,reason):
  values=copy.deepcopy(self.evidence);change(values)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*values)
 def test_actual_sources_pass(self):self.assertEqual(audit.inspect(*self.evidence)['native_entries'],51)
 def test_dialogue_group_loss(self):self.reject(lambda v:v[0]['complete_groups'].pop(),'complete original groups')
 def test_changed_case_lemma(self):self.reject(lambda v:v[4]['cases'][0]['judgments'][0].update(lemmas=['먹다']),'source requirement')
 def test_label_borrows_suffix(self):self.reject(lambda v:v[5]['-담']['sources'][0].update(id=88906),'source identities')
 def test_tension_owner_reclassified(self):self.reject(lambda v:v[1]['entries']['krdict:63516'].update(pos='형용사'),'Native projection')
 def test_duplicated_native_identity(self):self.reject(lambda v:v[2]['LexicalResource']['Lexicon']['LexicalEntry'].append(copy.deepcopy(v[2]['LexicalResource']['Lexicon']['LexicalEntry'][0])),'identity collision')
if __name__=='__main__':unittest.main()
