"""Reject incomplete installed evidence, missing recoveries and wrong filter commands."""
import unittest
from unittest.mock import patch

import fear_lsera_installed_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(*self.evidence)

    def test_complete_installed_evidence(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual((result['annotated_rows'], result['policy_decisions'], result['native_entries']), (66570, 222, 74))

    def test_terminal_nix_build(self):
        self.reject(self.evidence[1], {'state': 'running'}, 'terminal actual Nix packages')

    def test_same_commit(self):
        self.reject(self.evidence[0], {'head': 'fabricated'}, 'same built and bound packages')

    def test_missing_source_file(self):
        self.reject(self.evidence[0]['profiles']['klem'], {'files': {}}, 'complete source files')

    def test_actual_derivation_identity(self):
        profile = self.evidence[0]['profiles']['web-assets']
        drv = audit.json.loads(profile['derivation_json'])
        drv[profile['derivation']]['env']['src'] = '/nix/store/fabricated'
        text = audit.json.dumps(drv)
        self.reject(profile, {'derivation_json': text, 'derivation_json_sha256': audit.sha(text.encode())}, 'actual derivation source and output')

    def test_broad_workload_missing(self):
        self.reject(self.evidence[2], {'runs': self.evidence[2]['runs'][:-1]}, 'complete broad workloads')

    def test_broad_output_digest(self):
        self.reject(self.evidence[2]['runs'][0], {'actual_jsonl_sha256': '0' * 64}, 'complete installed broad output')

    def test_broad_spacing_flag(self):
        run = next(r for r in self.evidence[2]['runs'] if 'spacing' in r['mode'])
        self.reject(run, {'command': run['command'][:-1]}, 'actual broad filter and spacing command')

    def test_original_cohort_word(self):
        capture = self.evidence[3]['runs'][0]['captures'][1]
        words = dict(capture['words'])
        words.pop(next(iter(words)))
        digest = audit.sha(audit.json.dumps(words, ensure_ascii=False, sort_keys=True).encode())
        self.reject(capture, {'words': words, 'word_sha256': digest}, 'every complete captured word')

    def test_cohort_individual_changes(self):
        run = self.evidence[3]['runs'][0]
        self.reject(run, {'changed_words': {'invented': {}}}, 'individual original cohort changes')

    def test_invented_original_gold_change(self):
        self.reject(self.evidence[4], {'individual_changed_rows': [{'id': 'invented'}]}, 'individual original gold recoveries')

    def test_annotated_output(self):
        self.reject(self.evidence[4]['runs'][0], {'jsonl': 'fabricated'}, 'all complete original annotated outputs')

    def test_annotated_summary_delta(self):
        run = self.evidence[4]['runs'][0]
        self.reject(run, {'summary_changes': {'grouped_matches': {'before': 0, 'after': 1}}}, 'all complete original annotated outputs')

    def test_missing_unicode_cache_stream(self):
        self.reject(self.evidence[5], {'runs': self.evidence[5]['runs'][:-1]}, 'complete finite Unicode filter cache streams')

    def test_missing_reference_cache_stream(self):
        self.reject(self.evidence[12], {'runs': self.evidence[12]['runs'][:-1]}, 'complete reference Source cache streams')

    def test_reference_cache_output(self):
        capture = self.evidence[12]['runs'][1]['captures'][1]
        self.reject(capture, {'jsonl': 'fabricated'}, 'complete original Source stream parity')

    def test_original_finite_input(self):
        self.reject(self.evidence[5]['runs'][0], {'input_sha256': '0' * 64}, 'complete finite source input')

    def test_installed_finite_executable(self):
        run = self.evidence[5]['runs'][0]
        commands = [list(command) for command in run['commands']]
        commands[1][0] = '/nix/store/fabricated/bin/klem'
        self.reject(run, {'commands': commands}, 'actual installed finite executable')

    def test_finite_filter_flag(self):
        run = next(r for r in self.evidence[5]['runs'] if r['mode'] == 'headword')
        commands = [list(command) for command in run['commands']]
        commands[1].remove('--dict-only')
        self.reject(run, {'commands': commands}, 'actual finite filter cache commands')

    def test_finite_cache_flag(self):
        run = self.evidence[5]['runs'][0]
        commands = [list(command) for command in run['commands']]
        commands[1][-1] = '999'
        self.reject(run, {'commands': commands}, 'actual finite filter cache commands')

    def test_actual_launcher(self):
        self.reject(self.evidence[7], {'command': ['/nix/store/fabricated/bin/klem-web', '--port', '0', '--dictionary', 'db']}, 'actual installed launcher command')

    def test_owned_server_stopped(self):
        self.reject(self.evidence[7], {'server_stopped': False}, 'owned browser runtime stopped')

    def test_unmatched_dictionary_policy(self):
        decision = self.evidence[6]['policyDecisions'][0]
        self.reject(decision, {'allowed': False}, 'all independent policy decisions')

    def test_native_original_fields(self):
        entry = self.evidence[6]['nativeEntries'][0]['entry']
        self.reject(entry, {'headword': 'fabricated'}, 'all complete original Native responses')


if __name__ == '__main__':
    unittest.main()
