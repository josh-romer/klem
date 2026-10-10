"""Corruption controls for complete source streams and Native closure."""
import copy, unittest
import familiar_geurae_streams_audit as audit
class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.evidence = audit.inputs()
    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence); mutate(values)
        with self.assertRaisesRegex(AssertionError, reason): audit.inspect(*values)
    def test_complete_actual_capture(self): self.assertEqual(audit.inspect(*self.evidence)['frames'],516)
    def test_missing_mode(self): self.reject(lambda v:v[1]['runs'].pop(),'all twelve')
    def test_original_group(self): self.reject(lambda v:v[1]['complete_original_groups'].pop(),'original source groups')
    def test_input_text(self): self.reject(lambda v:v[1]['runs'][0].update(input_text='changed'),'Unicode source')
    def test_capture_digest(self): self.reject(lambda v:v[1]['runs'][0]['captures'][0].update(stdout_sha256='0'*64),'capture digest')
    def test_missing_frame(self): self.reject(lambda v:v[1]['runs'][0]['captures'][0]['records'].pop(),'actual source frames')
    def test_command(self): self.reject(lambda v:v[1]['runs'][0]['captures'][0]['command'].append('--invented'),'command identity')
    def test_missing_addition(self): self.reject(lambda v:v[1]['runs'][0]['individual_additions'].pop(),'derived individual additions')
    def test_context_promoted(self): self.reject(lambda v:v[1]['runs'][0]['individual_additions'][0].update(contextual_verdict='correct'),'derived individual additions')
    def test_stable_id(self): self.reject(lambda v:v[1]['individual_additions'][0].update(id='invented'),'individual source accounting')
    def test_missing_owner_observation(self): self.reject(lambda v:v[2]['individual_owner_observations'].pop(),'individual Native ownership')
    def test_altered_original_field(self): self.reject(lambda v:v[3]['LexicalResource']['Lexicon']['LexicalEntry'][0].update(invented=True),'Native originals')
    def test_altered_projection(self): self.reject(lambda v:v[4]['krdict:65194'].update(pos='동사'),'Native projection')
    def test_missing_export(self): self.reject(lambda v:v[2]['additional_exports'].clear(),'homonym exports')
    def test_closure_binding(self): self.reject(lambda v:v[2].update(source_streams_sha256='0'*64),'closure source binding')
    def rewrite_capture(self, values, mutate):
        capture=values[1]['runs'][0]['captures'][1]; mutate(capture['records'])
        capture['jsonl']=''.join(audit.json.dumps(r,ensure_ascii=False)+'\n' for r in capture['records'])
        capture['stdout_sha256']=audit.sha(capture['jsonl'].encode())
    def test_rehashed_byte_gap(self):
        self.reject(lambda v:self.rewrite_capture(v,lambda rows:rows[0]['span'].update(start=1)), 'byte conservation')
    def test_rehashed_prior_path_loss(self):
        def mutate(rows):
            row=next(r for r in rows if r.get('analysis') and len(r['analysis']['analyses'])>1)
            row['analysis']['analyses'].pop(0)
        self.reject(lambda v:self.rewrite_capture(v,mutate), 'prior paths and order')
    def test_coordinated_native_rewrite(self):
        def mutate(v):
            lexical=v[3]['LexicalResource']['Lexicon']['LexicalEntry'][0]
            lexical['invented']='coordinated'
            v[2]['original_native_entries'][audit.entry(lexical)['id']]=copy.deepcopy(lexical)
        self.reject(mutate,'pinned original Native fields')
if __name__ == '__main__': unittest.main()
