"""Reject incomplete or altered proof before authorizing a promoted parent view."""
import copy
import json
import unittest
from pathlib import Path

import friendly_hortative_sena_promotion_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        here = Path(__file__).resolve().parent
        cls.values = audit.inputs(prepared=here if here.name == 'friendly-hortative-sena-promotion-prepared' else None)

    def change(self, path, mutate):
        value = copy.copy(self.values); node = value
        for key in path[:-1]:
            node[key] = copy.copy(node[key]); node = node[key]
        node[path[-1]] = copy.deepcopy(node[path[-1]])
        mutate(node[path[-1]])
        if path[0] in ('rust', 'selected'):
            name = 'sena-promotion-full-rust.json' if path[0] == 'rust' else 'sena-promotion-selected-source-retry1.json'
            value['files'] = dict(value['files'])
            value['files'][name] = (json.dumps(value[path[0]], ensure_ascii=False, indent=2) + '\n').encode()
        return value

    def reject(self, path, mutate, reason):
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(self.change(path, mutate))

    def test_complete_actual_promotion(self):
        result = audit.inspect(self.values)
        self.assertEqual((result['current_cases'], result['current_reviews'], result['full_rust_tests']), (35789, 521, 1213))
        self.assertEqual((result['production_inputs'], result['compiled_inputs']), (44, 1158))
        self.assertEqual(result['binary_evidence'], 'captured-no-host-executable-reads')
        self.assertFalse(result['full_coverage_complete'])

    def test_complete_exact_parent_projection(self):
        projected = audit.parent_profiles(self.values, self.values['current_profiles'])
        parent = json.loads(self.values['parent']['friendly-hortative-sena-gena-parent-full-rust.json'])
        for name, profile in projected.items():
            prefix = 'web/' if name == 'web-assets' else ''
            self.assertTrue(all(parent['frozen_inputs'][prefix + path] == digest for path, digest in profile.items()))
            self.assertEqual(set(profile), set(self.values['current_profiles'][name]))
        self.assertNotEqual(projected['klem']['tests/fixtures/validity.json'], self.values['current_profiles']['klem']['tests/fixtures/validity.json'])

    def test_running_rust_rejected(self):
        self.reject(('rust',), lambda r: r.update(state='running'), 'actual complete promotion proof must pass')

    def test_failed_rust_rejected(self):
        self.reject(('rust',), lambda r: r.update(state='failed'), 'actual complete promotion proof must pass')

    def test_running_selected_source_rejected(self):
        self.reject(('selected',), lambda r: r.update(state='running'), 'actual complete promotion proof must pass')

    def test_borrowed_checkpoint_rejected(self):
        self.reject(('rust',), lambda r: r.update(head='borrowed'), 'exact tested promotion checkpoint')

    def test_false_source_freeze_rejected(self):
        self.reject(('rust',), lambda r: r.update(inputs_unchanged=False), 'complete actual Rust and Nix-selected Source frozen')

    def test_false_protected_freeze_rejected(self):
        self.reject(('rust',), lambda r: r.update(protected_binaries_unchanged=False), 'all actual promotion proof inputs frozen')

    def test_changed_current_production_rejected(self):
        self.reject(('current_production',), lambda r: r.update({'src/engine.rs': 'changed'}), 'all44 unchanged promotion production bytes')

    def test_missing_current_production_rejected(self):
        self.reject(('current_production',), lambda r: r.pop('src/engine.rs'), 'all44 unchanged promotion production bytes')

    def test_unknown_current_production_rejected(self):
        self.reject(('current_production',), lambda r: r.update({'src/unknown.rs': 'changed'}), 'all44 unchanged promotion production bytes')

    def test_wrong_rust_totals_rejected(self):
        self.reject(('rust', 'rust_totals'), lambda r: r.update(passed=1212), 'all1213 promotion Rust tests')

    def test_missing_target_rejected(self):
        self.reject(('rust', 'all_targets'), lambda r: r.pop(), 'every262 promotion Cargo target')

    def test_failed_target_rejected(self):
        self.reject(('rust', 'results', 1), lambda r: r.update(exit_code=1), 'every262 promotion Cargo target')

    def test_reordered_target_rejected(self):
        self.reject(('rust', 'all_targets'), lambda r: r.reverse(), 'every promotion Cargo target in original order')

    def test_missing_doctest_rejected(self):
        self.reject(('rust', 'results', 263, 'command'), lambda r: r.__setitem__(-1, '--lib'), 'all original promotion final checks')

    def test_changed_metadata_rejected(self):
        self.reject(('rust', 'cargo_metadata', 'packages', 0), lambda r: r.update(name='borrowed'), 'whole promotion Cargo metadata')

    def test_changed_raw_log_rejected(self):
        value = copy.copy(self.values); value['files'] = dict(value['files'])
        value['files']['sena-promotion-full-rust.log'] += b'changed'
        with self.assertRaisesRegex(AssertionError, 'whole actual promotion log'): audit.inspect(value)

    def test_failed_selected_command_rejected(self):
        self.reject(('selected', 'results', 0), lambda r: r.update(exit_code=1), 'four actual Git-selected promotion source evaluations')

    def test_false_build_replay_claim_rejected(self):
        self.reject(('selected',), lambda r: r.update(full_build_replays=1), 'honest selected-source-only scope')

    def test_changed_current_compile_fixture_rejected(self):
        self.reject(('current_profiles', 'klem'), lambda r: r.update({'tests/fixtures/validity.json': 'changed'}), 'every actual selected tested promotion profile byte')

    def test_missing_current_compile_member_rejected(self):
        self.reject(('current_profiles', 'corpus-adapter'), lambda r: r.pop('src/engine.rs'), 'every actual selected tested promotion profile byte')

    def test_unknown_current_compile_member_rejected(self):
        self.reject(('current_profiles', 'klem'), lambda r: r.update({'src/unknown.rs': 'changed'}), 'every actual selected tested promotion profile byte')

    def test_changed_current_frontend_rejected(self):
        self.reject(('current_profiles', 'web-assets'), lambda r: r.update({'src/grammar-labels.json': 'changed'}), 'every actual selected tested promotion profile byte')

    def test_omitted_actual_tail_rejected(self):
        def change(r):
            body = json.loads(r['current_raw']); body['cases'].pop()
            r['current_raw'] = (json.dumps(body, ensure_ascii=False, indent=2) + '\n').encode()
        self.reject(('ledger',), change, 'complete35764')

    def test_borrowed_parent_review_rejected(self):
        self.reject(('ledger', 'current_reviews', 'entries'), lambda r: r.pop(), 'complete520')

    def test_changed_actual_validity_test_rejected(self):
        value = dict(self.values, actual_test_raw=self.values['actual_test_raw'] + b'changed')
        with self.assertRaisesRegex(AssertionError, 'complete actual new validity regression bytes'): audit.inspect(value)

    def test_historical_profiles_cannot_be_supplied_as_current(self):
        current = audit.parent_profiles(self.values, self.values['current_profiles'])
        with self.assertRaisesRegex(AssertionError, 'every current profile byte belongs to actual passed parent Rust source'):
            audit.parent_profiles(self.values, current)


if __name__ == '__main__':
    unittest.main()
