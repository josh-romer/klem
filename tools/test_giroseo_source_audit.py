import copy,unittest
import giroseo_source_audit as audit
class Controls(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.values=audit.inputs()
 def reject(self,fn,reason):
  v=copy.deepcopy(self.values);fn(v)
  with self.assertRaisesRegex(AssertionError,reason):audit.inspect(*v)
 def test_complete_original_sources(self):self.assertEqual(audit.inspect(*self.values)['complete_groups'],8)
 def test_missing_group(self):self.reject(lambda v:v[0]['complete_groups'].pop(),'every complete original group')
 def test_trailing_source_space(self):self.reject(lambda v:v[0].update(complete_source_text=v[0]['complete_source_text'].replace('해요? \n','해요?\n')),'complete source bytes')
 def test_excluded_marker_note(self):self.reject(lambda v:v[0]['expression_entries']['krdict:83919']['notes'].clear(),'exact source identity')
 def test_native_homonym_removed(self):self.reject(lambda v:v[3].pop(next(iter(v[3]))),'complete Native identities')
 def test_source_proposal_rewritten(self):self.reject(lambda v:v[1]['proposals'][0].update(complete_original_group=['fabricated']),'original proposal group')
 def test_target_location(self):self.reject(lambda v:v[1]['proposals'][0].update(surface_byte_offset=0),'target byte location')
 def test_source_judgment_rewritten(self):self.reject(lambda v:v[4]['cases'][0]['judgments'][0].update(lemmas=['invented']),'independent source judgment')
 def test_missing_baseline_filter(self):self.reject(lambda v:v[1]['proposals'][0]['baseline_records'].pop('compatible'),'pre-change mode records')
 def test_label_kind(self):self.reject(lambda v:v[5]['-기로서'].update(kind='particle'),'label source and kind')
 def test_label_owner_not_truncated(self):self.reject(lambda v:v[6]['LexicalResource']['Lexicon']['LexicalEntry'].pop(),'complete label owners')
 def test_coordinated_native_rewrite(self):
  def change(v):
   ident='krdict:83919';row=next(x for x in v[2]['LexicalResource']['Lexicon']['LexicalEntry'] if 'krdict:'+x['val']==ident)
   from native_lmf import array
   feature=next(f for sense in array(row['Sense']) for f in array(sense['feat']) if f['att']=='definition');feature['val']='fabricated'
   projected=audit.entry(row);v[3][ident]=projected;v[0]['complete_imported_entries'][ident]=projected;v[0]['original_native_entries'][ident]=copy.deepcopy(row)
  self.reject(change,'exact preserved Native fixture bytes')
if __name__=='__main__':unittest.main()
