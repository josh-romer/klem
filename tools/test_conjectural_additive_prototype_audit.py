"""Corrupt independent source/typed/browser/queue evidence and require rejection."""
import copy
import json
import unittest
from pathlib import Path

import conjectural_additive_prototype_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs(Path(__file__).resolve().parent)

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(values)

    def change_row(self, values, mutate):
        run = values['after']['runs'][0]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        mutate(rows, run)
        run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows)
        run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())

    def test_complete_real_evidence(self):
        result = audit.inspect(self.evidence)
        self.assertEqual((result['source_frames'], result['browser_diagrams'], result['unjudged_source_alternatives']), (4080, 192, 66))

    def test_authored_target_changed_to_fit_output(self):
        self.reject(lambda v: v['after']['typed_fixture']['cases'][0]['judgments'][0]['lemma_kinds'].__setitem__(0, 'nominal'), 'every independently authored judgment unchanged')

    def test_original_group_omitted(self):
        self.reject(lambda v: v['source']['complete_groups'].pop(), 'all complete original groups')

    def test_source_past_license_erased(self):
        self.reject(lambda v: v['source']['source_entries']['krdict:86084']['notes'].clear(), 'all original dictionary fields')

    def test_unicode_cache_stream_omitted(self):
        self.reject(lambda v: v['after']['runs'].pop(), 'all original24Unicode/filter/cache streams')

    def test_actual_compatible_filter_removed(self):
        self.reject(lambda v: v['after']['runs'][4]['command'].remove('--dict-compatible'), 'actual filter/cache command')

    def test_actual_cache_flag_rewritten(self):
        self.reject(lambda v: v['after']['runs'][1]['command'].__setitem__(-1, '0'), 'actual filter/cache command')

    def test_original_candidate_erased_with_output_hash_repaired(self):
        self.reject(lambda v: self.change_row(v, lambda rows, run: rows[0]['analysis']['analyses'].pop()), 'every original candidate retained')

    def test_target_lemma_role_corrupted_with_output_hash_repaired(self):
        def corrupt(rows, run):
            occurrence = run['observed_typed_paths'][0]
            rows[occurrence['record_index']]['analysis']['analyses'][occurrence['typed_path_indices'][0]]['lemmas'][0]['kind'] = 'nominal'
        self.reject(lambda v: self.change_row(v, corrupt), 'independent typed original path present')

    def test_target_morpheme_type_corrupted_with_output_hash_repaired(self):
        def corrupt(rows, run):
            occurrence = run['observed_typed_paths'][0]
            rows[occurrence['record_index']]['analysis']['analyses'][occurrence['typed_path_indices'][0]]['morphemes'][-1]['kind'] = 'particle'
        self.reject(lambda v: self.change_row(v, corrupt), 'independent typed original path present')

    def test_observed_path_indices_fabricated(self):
        self.reject(lambda v: v['after']['runs'][0]['observed_typed_paths'][0].update(typed_path_indices=[0]), 'independently rederived typed path indices')

    def test_original_source_byte_span_changed(self):
        self.reject(lambda v: self.change_row(v, lambda rows, run: rows[0]['span'].update(end=1)), 'original token identity')

    def test_candidate_queue_entry_omitted(self):
        self.reject(lambda v: v['queue']['items'].pop(), 'every original-context candidate and Native assessment tracked')

    def test_unjudged_alternative_auto_promoted(self):
        def mutate(v):
            next(item for item in v['queue']['items'] if item['coverage'] == 'unjudged-alternative')['coverage'] = 'covered-by-independent-required-path'
        self.reject(mutate, 'every original-context candidate and Native assessment tracked')

    def test_queue_native_assessment_rewritten(self):
        self.reject(lambda v: v['queue']['items'][0]['dictionary_reading'].update(status='compatible'), 'every original-context candidate and Native assessment tracked')

    def test_contextual_sense_claimed_reviewed(self):
        self.reject(lambda v: v['queue']['items'][0].update(contextual_sense_verdict='required'), 'every original-context candidate and Native assessment tracked')

    def test_missing_focused_rust_test(self):
        self.reject(lambda v: v.update(rust_log=v['rust_log'].replace('6 passed;', '5 passed;')), 'all six focused tests completed')

    def test_clippy_warnings_not_denied(self):
        self.reject(lambda v: v['checks']['runs'][1]['command'].__setitem__(-2, '-A'), 'actual warnings-denied Clippy')

    def test_browser_server_still_running(self):
        self.reject(lambda v: v['runtime'].update(server_stopped=False), 'actual browser completion and shutdown')

    def test_browser_error_omitted_from_claim(self):
        self.reject(lambda v: v['browser']['errors'].append('TypeError'), 'no browser errors')

    def test_missing_browser_policy(self):
        self.reject(lambda v: v['browser']['policyDecisions'].pop(), 'all browser source and boundary positives')

    def test_viewer_offers_wrong_candidate_index(self):
        self.reject(lambda v: v['browser']['policyDecisions'][0].update(offered_indices=[]), 'actual authored path available in viewer')

    def test_display_auxiliary_component_order_changed(self):
        self.reject(lambda v: v['browser']['diagrams'][0].update(forms=['어둡', '지', '어', '으려니와']), 'independent displayed component order')

    def test_other_allomorph_source_link_lost(self):
        self.reject(lambda v: v['browser']['diagrams'][0].update(source_hint='KRDict 86083'), 'both original ending source links')

    def test_json_export_loses_selected_analysis(self):
        def mutate(v):
            decision = v['browser']['policyDecisions'][0]
            paths = v['browser']['exports'][0]['records'][decision['record_index']]['analysis']['analyses']
            paths.remove(decision['analysis'])
        self.reject(mutate, 'actual exported selected path')

    def test_original_native_endpoint_owner_missing(self):
        self.reject(lambda v: v['browser']['nativeEntries'].pop(), 'every original Native endpoint field')

    def test_original_native_endpoint_sense_rewritten(self):
        self.reject(lambda v: v['browser']['nativeEntries'][0]['entry']['senses'][0].update(definition='rewritten'), 'every original Native endpoint field')

    def test_supplemental_noun_owner_missing(self):
        self.reject(lambda v: v['copula_native']['complete_imported_entries'].pop('krdict:70089'), 'all eight original supplemental Native identities')

    def test_supplemental_native_sense_rewritten(self):
        self.reject(lambda v: v['copula_native']['complete_imported_entries']['krdict:73276']['senses'][0].update(definition='rewritten'), 'every supplemental Native projection field')

    def test_original_novel_target_reauthored(self):
        self.reject(lambda v: v['copula_author'].update(typed_lemmas=['장래다']), 'unchanged independently authored original novel target')

    def test_forbidden_coda_copula_promoted(self):
        self.reject(lambda v: v['copula_fixture']['cases'][2]['judgments'][0].update(verdict='required'), 'unchanged six independently authored copula judgments')

    def test_original_novel_stream_omitted(self):
        self.reject(lambda v: v['novel']['runs'].pop(), 'all original novel Unicode/filter/cache streams')

    def test_novel_compatible_flag_removed(self):
        self.reject(lambda v: v['novel']['runs'][4]['command'].remove('--dict-compatible'), 'actual novel filter/cache command')

    def test_novel_nominal_copula_rule_removed_with_hash_repaired(self):
        def mutate(v):
            run = v['novel']['runs'][0]
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[run['record_index']]['analysis']['analyses'][run['typed_path_indices'][0]]['rules'].remove('copula.omitted_ending')
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows)
            run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(mutate, 'independently rederived novel copula path indices')

    def test_novel_native_assessment_rewritten_with_hash_repaired(self):
        def mutate(v):
            run = v['novel']['runs'][0]
            rows = [json.loads(line) for line in run['jsonl'].splitlines()]
            rows[run['record_index']]['dictionary']['readings'][run['typed_path_indices'][0]]['status'] = 'unknown'
            run['jsonl'] = ''.join(json.dumps(row, ensure_ascii=False, separators=(',', ':')) + '\n' for row in rows)
            run['jsonl_sha256'] = audit.sha(run['jsonl'].encode())
        self.reject(mutate, 'correct Native novel nominal/copula owners')

    def test_missing_copula_rust_test(self):
        self.reject(lambda v: v.update(rust_log=v['rust_log'].replace('2 passed;', '1 passed;')), 'both copula focused tests completed')

    def test_browser_omitted_copula_component_lost(self):
        self.reject(lambda v: v['browser']['diagrams'][-4].update(forms=['장래', '으려니와']), 'independent displayed component order')

    def test_original_native_and_projection_both_forged(self):
        def mutate(v):
            v['copula_native']['complete_imported_entries']['krdict:73276']['headword'] = '학교'
            v['copula_native']['complete_imported_entries']['krdict:73276']['senses'][0]['definition'] = 'rewritten'
            original = v['copula_native']['original_native_entries']['krdict:73276']
            original['Sense']['feat']['val'] = 'rewritten'
        self.reject(mutate, 'all original supplemental Native fields pinned')

if __name__ == '__main__':
    unittest.main()
