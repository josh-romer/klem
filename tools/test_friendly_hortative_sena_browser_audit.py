"""Reject corrupted actual browser choices, exports, source bindings, and corpus hypotheses."""
import copy
import unittest
import friendly_hortative_sena_browser_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.values=audit.inputs()

    def reject(self,path,change,reason):
        values=self.values.copy();node=values
        for key in path[:-1]:
            node[key]=copy.copy(node[key]);node=node[key]
        node[path[-1]]=copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError,reason): audit.inspect(values)

    def browser(self,path,change,reason):
        self.reject(('proof','friendly-hortative-sena-browser.json',*path),change,reason)

    def report(self,path,change,reason):
        self.reject(('proof','friendly-hortative-sena-browser-runtime-retry1.json',*path),change,reason)

    def test_complete_original_browser(self):
        result=audit.inspect(self.values)
        self.assertEqual((result['browser_choices'],result['required_diagrams'],result['original_corpus_choices'],result['exact_exports'],result['complete_native_entries']),(150,114,6,12,37))
        self.assertFalse(result['full_coverage_complete'])

    def test_owned_server_not_stopped(self):
        self.report((),lambda r:r.update(server_stopped=False),'owned browser server stopped')

    def test_unexpected_server_exit(self):
        self.report((),lambda r:r.update(server_exit_code=1),'owned browser server stopped')

    def test_incomplete_source_snapshot(self):
        self.report(('source_inputs',),lambda r:r.pop(next(iter(r))),'same complete7179 source snapshot')

    def test_borrowed_source_head(self):
        self.report((),lambda r:r.update(head='6cf27565c7891005de12651abcb7f18911495adf'),'actual captured source revision')

    def test_current_production_changed(self):
        self.reject(('runtime','current'),lambda r:r.update({'src/engine.rs':'changed'}),'complete44 current production inputs')

    def test_browser_production_changed(self):
        self.report(('production_inputs',),lambda r:r.update({'src/engine.rs':'changed'}),'all44 current browser production inputs')

    def test_frontend_source_omitted(self):
        self.report(('frontend_inputs',),lambda r:r.pop(next(iter(r))),'all18 current browser frontend inputs')

    def test_served_asset_changed(self):
        self.report(('served_assets',0),lambda r:r.update(sha256='changed'),'actual served asset bytes')

    def test_parent_binary_fingerprint_changed(self):
        parent=next(iter(self.values['runtime']['binding']['protected_parent_binaries']))
        self.report(('frozen_inputs',),lambda r:r.update({parent:'changed'}),'all six frozen executable fingerprints')

    def test_borrowed_server_command(self):
        self.report(('command',),lambda r:r.__setitem__(0,'/tmp/borrowed-klem-web'),'bound actual browser server command')

    def test_driver_hash_changed(self):
        self.browser((),lambda r:r.update(producer_sha256='changed'),'actual browser driver binding')

    def test_unicode_policy_omitted(self):
        self.browser(('responses',),lambda r:r.pop(),'both original browser Unicode responses')

    def test_export_omitted(self):
        self.browser(('exports',),lambda r:r.pop(),'all twelve original browser exports')

    def test_api_old_candidate_lost(self):
        self.browser(('responses',0,'api','records',0,'analysis','analyses'),lambda r:r.pop(0),'every complete browser word equals original bound CLI')

    def test_api_old_assessment_changed(self):
        self.browser(('responses',0,'api','records',0,'dictionary','readings',0),lambda r:r.update(status='invented'),'every complete browser word equals original bound CLI')

    def test_original_byte_span_changed(self):
        self.browser(('responses',0,'api','records',0,'span'),lambda r:r.update(start=1),'complete original browser byte spans')

    def test_label_owner_borrowed(self):
        self.browser(('responses',0,'api','grammar','-세나',0),lambda r:r.update(id='krdict:66968'),'own attributed Sena browser grammar')

    def test_whole_export_candidate_lost(self):
        self.browser(('exports',0,'records',0,'analysis','analyses'),lambda r:r.pop(0),'independently filtered entire browser export')

    def test_selector_option_missing(self):
        self.browser(('policyDecisions',0,'offered_indices'),lambda r:r.pop(),'all150 independently rederived browser decisions')

    def test_forbidden_path_claimed_allowed(self):
        i=next(i for i,r in enumerate(self.values['proof']['friendly-hortative-sena-browser.json']['policyDecisions']) if r.get('verdict')=='forbidden')
        self.browser(('policyDecisions',i),lambda r:r.update(allowed=True),'all150 independently rederived browser decisions')

    def test_displayed_component_order_changed(self):
        self.browser(('diagrams',0,'forms'),lambda r:r.reverse(),'every independent displayed form and order')

    def test_own_source_hint_missing(self):
        self.browser(('diagrams',0),lambda r:r.update(source_hint='Friendly invitation'),'own displayed Sena label sources')

    def test_corpus_policy_omitted(self):
        self.browser(('corpusDecisions',),lambda r:r.pop(),'all six original-corpus policies')

    def test_corpus_old_candidate_lost(self):
        index=self.values['proof']['friendly-hortative-sena-browser.json']['corpusDecisions'][0]['record_index']
        self.browser(('corpusDecisions',0,'api','records',index,'analysis','analyses'),lambda r:r.pop(0),'every complete original-corpus browser record equals bound CLI')

    def test_corpus_filtered_export_changed(self):
        self.browser(('exports',6,'records'),lambda r:r.pop(),'whole original-corpus filtered export')

    def test_corpus_gold_rewritten(self):
        self.browser(('corpusDecisions',0,'original_gold_row'),lambda r:r.update(expected=['중다']),'every independent original-corpus dropdown and gold observation')

    def test_corpus_hypothesis_falsely_reviewed(self):
        self.browser(('corpusDecisions',0),lambda r:r.update(hypothesis_contextual_verdict='required'),'every independent original-corpus dropdown and gold observation')

    def test_corpus_dropdown_loses_noun(self):
        i=2;d=self.values['proof']['friendly-hortative-sena-browser.json']['corpusDecisions'][i]
        self.browser(('corpusDecisions',i,'offered_indices'),lambda r:r.remove(str(d['nominal_analysis_index'])),'every independent original-corpus dropdown and gold observation')

    def test_complete_native_field_changed(self):
        self.browser(('nativeEntries',0,'entry'),lambda r:r.update(notes=['invented']),'all37 complete original browser Native entries')

    def test_original_port_failure_rewritten(self):
        self.reject(('proof','friendly-hortative-sena-browser-runtime.json'),lambda r:r.update(state='passed'),'original port-denied failure preserved')

    def test_screenshot_hash_changed(self):
        self.report(('screenshots',),lambda r:r.update({next(iter(r)):'changed'}),'complete original screenshot bytes')

if __name__=='__main__': unittest.main()
