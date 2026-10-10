"""Reject lost source context, conflated homonyms and candidate-authored targets."""
import copy
import unittest
from unittest.mock import patch

import familiar_geurae_source_audit as audit

class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, obj, updates, reason):
        with patch.dict(obj, updates):
            with self.assertRaisesRegex(AssertionError, reason):
                audit.inspect(*self.evidence)

    def test_complete_original_evidence(self):
        self.assertEqual(audit.inspect(*self.evidence)['required'], 19)

    def test_original_native_note(self):
        raw = self.evidence[0]['original_native_entries']['krdict:83913']
        self.reject(raw, {'unexpected_field': 'fabricated'}, 'pinned complete original Native fields')

    def test_missing_initial_native(self):
        native = dict(self.evidence[0]['original_native_entries'])
        native.pop(next(iter(native)))
        self.reject(self.evidence[0], {'original_native_entries': native}, 'pinned complete original Native fields')

    def test_complete_authored_native_projection(self):
        self.reject(self.evidence[9]['krdict:83913'], {'level': 'fabricated'}, 'all authored Native owners')

    def test_missing_source_group(self):
        self.reject(self.evidence[0], {'complete_groups': self.evidence[0]['complete_groups'][:-1]}, 'all complete source groups and order')

    def test_complete_two_line_context(self):
        group = self.evidence[2]['complete_groups'][-1]
        self.reject(group, {'lines': group['lines'][1:]}, 'all complete source groups and order')

    def test_original_byte_spacing(self):
        self.reject(self.evidence[1], {'complete_source_text': self.evidence[1]['complete_source_text'] + ' '}, 'complete original source bytes')

    def test_source_target_rewritten_from_candidate(self):
        target = self.evidence[2]['manual_targets'][0]
        self.reject(target, {'lemmas': ['쉬지그다']}, 'independent original lexical and canonical target')

    def test_initial_authorship_coordinated_rewrite(self):
        judgment = self.evidence[5]['cases'][0]['judgments'][0]
        self.reject(judgment, {'lemmas': ['fabricated']}, 'pinned original independent judgments')

    def test_canonical_variant_source(self):
        self.reject(self.evidence[3], {'canonical_morphemes': ['군', '그래']}, 'source-based canonical target')

    def test_missing_primary_variant_source(self):
        self.reject(self.evidence[3], {'sources': self.evidence[3]['sources'][:-1]}, 'separate primary canonical sources')

    def test_correction_retains_lemma(self):
        self.reject(self.evidence[7]['cases'][0]['judgments'][0], {'lemmas': ['fabricated']}, 'only existing rule ownership corrected')

    def test_correction_retains_forbidden_verdict(self):
        judgment = self.evidence[7]['cases'][-1]['judgments'][0]
        self.reject(judgment, {'verdict': 'required'}, 'only existing rule ownership corrected')

    def test_existing_variant_provenance(self):
        self.reject(self.evidence[6], {'actual_existing_marker': 'fabricated'}, 'existing variant rule ownership')

    def test_baseline_unicode_mode_missing(self):
        self.reject(self.evidence[10], {'runs': self.evidence[10]['runs'][:-1]}, 'all original baseline Unicode filters')

    def test_baseline_candidate_is_not_gold(self):
        run = self.evidence[10]['runs'][0]
        analyses = [*run['record']['analyses'], {'lemmas': [{'text': '쉬다'}]}]
        self.reject(run['record'], {'analyses': analyses}, 'independent missing baseline lexical target')

    def test_prechange_path_conservation(self):
        self.reject(self.evidence[11]['그래'], {'normalized': 'fabricated'}, 'pinned pre-change regression fields')

    def test_particle_label_homonym(self):
        self.reject(self.evidence[12]['그래'], {'sources': [{'id': 27656, 'headword': '그래', 'pos': '감탄사'}]}, 'actual particle component key and source')

    def test_particle_ending_catalog_key(self):
        self.reject(self.evidence[12], {'-그래': self.evidence[12]['그래']}, 'particle key separate from endings')

if __name__ == '__main__':
    unittest.main()
