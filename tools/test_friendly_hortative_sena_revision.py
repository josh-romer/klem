"""Keep strict source rejection and every original failure when naming Sena."""
import copy
import unittest
from unittest.mock import patch
import friendly_hortative_sena_revision as audit

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

    def test_exact_current_source_closure(self):
        self.assertEqual(len(audit.inspect(self.values)),44)

    def test_guard_cannot_claim_live_executables(self):
        self.reject(('browser','runtime','binary_evidence'),lambda r:r.update(mode='live',live_executable_files_verified=True),'honest immutable binary evidence scope|explicit captured Sena source guard scope')

    def test_missing_compiled_json(self):
        self.reject(('current_profiles','klem'),lambda r:r.pop('src/dictionary/proper_names.json'),'every current compiled Rust frontend byte')

    def test_changed_compile_test_fixture(self):
        self.reject(('current_profiles','klem'),lambda r:r.update({'tests/fixtures/friendly-hortative-sena-validity.json':'changed'}),'every current compiled Rust frontend byte')

    def test_unknown_compile_input(self):
        self.reject(('current_profiles','klem'),lambda r:r.update({'src/unknown.rs':'changed'}),'every current compiled Rust frontend byte')

    def test_borrowed_rust_production(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','production_inputs'),lambda r:r.update({'src/engine.rs':'changed'}),'complete passing Rust Sena production')

    def test_rust_passed_count_changed(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','rust_totals'),lambda r:r.update(passed=1200),'complete1211 Rust262 targets')

    def test_rust_target_omitted(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','all_targets'),lambda r:r.pop(),'every actual Rust target and final check passed')

    def test_rust_command_failed(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','results',1),lambda r:r.update(exit_code=1),'every actual Rust target and final check passed')

    def test_rust_target_order_changed(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','all_targets'),lambda r:r.reverse(),'every metadata target tested once in order')

    def test_cargo_metadata_changed(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','cargo_metadata','packages',0),lambda r:r.update(name='borrowed'),'original cargo metadata binding')

    def test_rust_original_log_totals_changed(self):
        values=self.values.copy();values['rust_originals']=self.values['rust_originals'].copy()
        raw=values['rust_originals']['friendly-hortative-sena-full-rust-serial-retry.log']
        values['rust_originals']['friendly-hortative-sena-full-rust-serial-retry.log']=raw.replace(b'test result: ok.',b'test result: failed.',1)
        with self.assertRaisesRegex(AssertionError,'complete original Rust log totals'): audit.inspect(values)

    def test_original_compile_failure_rewritten(self):
        self.reject(('rust','friendly-hortative-sena-full-rust.json'),lambda r:r.update(state='passed'),'original compilation and cleanup failures retained')

    def test_original_cleanup_failure_rewritten(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial.json'),lambda r:r.update(state='passed'),'original compilation and cleanup failures retained')

    def test_selected_139_command_failed(self):
        self.reject(('selected','friendly-hortative-sena-wide-selected-source.json','results',0),lambda r:r.update(exit_code=1),'every selected139 command passed')

    def test_selected_compile_input_omitted(self):
        self.reject(('selected','friendly-hortative-sena-wide-selected-source.json','profiles','klem','files'),lambda r:r.pop(next(iter(r))),'all1158/1158/18 actual compile profiles')

    def test_original_rust_source_snapshot_changed(self):
        self.reject(('rust','friendly-hortative-sena-full-rust-serial-retry.json','frozen_inputs'),lambda r:r.update({'src/lib.rs':'changed'}),'same complete passing Rust and selected revision')

    def test_wide_corpus_comparison_failed(self):
        self.reject(('wide','friendly-hortative-sena-wide-comparisons.json','results',0),lambda r:r.update(exit_code=1),'actual whole cohort gold broad comparisons passed')

    def test_wide_production_borrowed(self):
        self.reject(('wide','friendly-hortative-sena-wide-comparisons.json','frozen_inputs'),lambda r:r.update({'src/engine.rs':'changed'}),'complete wide Sena production closure')

    def test_independent_wide_controls_missing(self):
        self.reject(('audited','friendly-hortative-sena-wide-audit-validation.json'),lambda r:r.update(controls=0),'actual independent34 wide controls')

    def test_browser_decision_omitted(self):
        self.reject(('browser','proof','friendly-hortative-sena-browser.json','policyDecisions'),lambda r:r.pop(),'all150 independently rederived browser decisions')

    def test_accept_exact_relative_and_legacy_absolute(self):
        production=self.values['browser']['runtime']['binding']['production_inputs']
        with patch.object(audit,'inputs',return_value=self.values):
            self.assertTrue(audit.accepts_production(production))
            self.assertTrue(audit.accepts_production({'/tmp/klem-gentle-command/'+p:d for p,d in production.items()}))

    def test_reject_missing_json_map(self):
        production=self.values['browser']['runtime']['binding']['production_inputs'].copy();production.pop('src/dictionary/proper_names.json')
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_production(production))

    def test_reject_unknown_production_edit(self):
        production=self.values['browser']['runtime']['binding']['production_inputs'].copy();production['src/lib.rs']='changed'
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_production(production))

    def test_reject_unknown_absolute_root(self):
        production=self.values['browser']['runtime']['binding']['production_inputs']
        self.assertFalse(audit.accepts_production({'/unrelated/'+p:d for p,d in production.items()}))

    def test_reject_duplicate_normalized_path(self):
        production=self.values['browser']['runtime']['binding']['production_inputs'].copy();production['./src/lib.rs']=production['src/lib.rs']
        self.assertFalse(audit.accepts_production(production))

    def frontend(self):
        return {p.removeprefix('web/'):d for p,d in self.values['browser']['runtime']['binding']['frontend_inputs'].items()}

    def test_accept_exact_frontend_with_three_known_parents(self):
        selected=self.frontend();v=self.values['parent'];p=v['parent'];label='src/grammar-labels.json'
        labels=[v['binding']['production_inputs']['web/'+label],p['binding']['production_inputs']['web/'+label],p['binding']['parent_production_inputs']['/tmp/klem-gentle-command/web/'+label]]
        with patch.object(audit,'inputs',return_value=self.values):
            for value in labels:
                historical=selected|{label:value};self.assertTrue(audit.accepts_frontend(selected,historical))

    def test_reject_missing_frontend_public_asset(self):
        selected=self.frontend();historical=selected.copy();selected.pop('public/favicon.svg')
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_frontend(selected,historical))

    def test_reject_changed_frontend_code(self):
        selected=self.frontend();historical=selected.copy();selected['src/App.tsx']='changed'
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_frontend(selected,historical))

    def test_reject_changed_historical_frontend(self):
        selected=self.frontend();historical=selected|{'src/App.tsx':'changed'}
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_frontend(selected,historical))

    def test_reject_unknown_historical_label(self):
        selected=self.frontend();historical=selected|{'src/grammar-labels.json':'unrelated'}
        with patch.object(audit,'inputs',return_value=self.values): self.assertFalse(audit.accepts_frontend(selected,historical))

if __name__=='__main__': unittest.main()
