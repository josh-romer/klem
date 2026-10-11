"""Negative controls for actual Gena browser captures and source binding."""
import copy
import unittest

import friendly_command_gena_browser_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = audit.inputs()

    def reject(self,path,change,reason):
        values=self.values.copy();node=values
        for key in path[:-1]:
            node[key]=copy.copy(node[key]);node=node[key]
        node[path[-1]]=copy.deepcopy(node[path[-1]])
        change(node[path[-1]])
        with self.assertRaisesRegex(AssertionError,reason):audit.inspect(values)

    def browser_reject(self,path,change,reason):
        self.reject(('proof','friendly-command-gena-browser.json',*path),change,reason)

    def test_complete_original_browser(self):
        self.assertEqual(audit.inspect(self.values)['browser_choices'],144)

    def test_owned_server_remains_running(self):
        self.reject(('proof','friendly-command-gena-browser-runtime-retry1.json'),lambda r:r.update(server_stopped=False),'owned browser server stopped')

    def test_unknown_frontend_source(self):
        self.reject(('current_frontend',),lambda r:r.update({next(iter(r)):'changed'}),'all18 current SolidJS source inputs')

    def test_served_asset_changed(self):
        self.reject(('proof','friendly-command-gena-browser-runtime-retry1.json','served_assets',0),lambda r:r.update(sha256='changed'),'exact served production asset bytes')

    def test_unicode_policy_omitted(self):
        self.browser_reject(('responses',),lambda r:r.pop(),'both original browser Unicode policies')

    def test_export_omitted(self):
        self.browser_reject(('exports',),lambda r:r.pop(),'all six browser exports')

    def test_api_old_candidate_lost(self):
        self.browser_reject(('responses',0,'api','records',0,'analysis','analyses'),lambda r:r.pop(0),'every complete browser record equals actual CLI')

    def test_api_own_entry_assessment_changed(self):
        self.browser_reject(('responses',0,'api','records',0,'dictionary','readings',0),lambda r:r.update(status='invented'),'every complete browser record equals actual CLI')

    def test_api_original_byte_span_changed(self):
        self.browser_reject(('responses',0,'api','records',0,'span'),lambda r:r.update(start=1),'complete original browser byte spans')

    def test_declared_frontend_build_input_omitted(self):
        self.reject(('proof','friendly-command-gena-frontend-build.json','frozen_inputs'),lambda r:r.pop(next(iter(r))),'all14 declared frontend build inputs')

    def test_label_source_borrowed(self):
        self.browser_reject(('responses',0,'api','grammar','-게나',0),lambda r:r.update(id='krdict:79266'),'own attributed browser label and rule')

    def test_filtered_export_loses_original_path(self):
        self.browser_reject(('exports',0,'records',0,'analysis','analyses'),lambda r:r.pop(0),'every independently filtered browser export')

    def test_selector_option_missing(self):
        self.browser_reject(('policyDecisions',0,'offered_indices'),lambda r:r.pop(),'all144 independently rederived browser choices')

    def test_forbidden_case_claimed_allowed(self):
        browser=self.values['proof']['friendly-command-gena-browser.json']
        index=next(i for i,r in enumerate(browser['policyDecisions']) if r.get('verdict')=='forbidden')
        self.browser_reject(('policyDecisions',index),lambda r:r.update(allowed=True),'all144 independently rederived browser choices')

    def test_component_order_changed(self):
        self.browser_reject(('diagrams',0,'forms'),lambda r:r.reverse(),'every independent displayed form/order/reference')

    def test_diagram_source_hint_missing(self):
        self.browser_reject(('diagrams',0),lambda r:r.update(source_hint='Friendly command'),'own ending source attribution')

    def test_native_full_entry_note_changed(self):
        self.browser_reject(('nativeEntries',0,'entry'),lambda r:r.update(notes=['invented']),'all31 complete original browser Native entries')

    def test_original_launch_failure_rewritten(self):
        self.reject(('proof','friendly-command-gena-browser-launch-failure-friendly-command-gena-browser-runtime.json.gz'),lambda r:r.update(state='passed'),'actual terminal Gena scope')


if __name__=='__main__':
    unittest.main()
