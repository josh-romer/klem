"""Detect source omissions and misleading conversion of observations into judgments."""
import copy
import unittest

import conjectural_additive_source_audit as audit


class Controls(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = audit.inputs()

    def reject(self, mutate, reason):
        values = copy.deepcopy(self.evidence)
        mutate(values)
        with self.assertRaisesRegex(AssertionError, reason):
            audit.inspect(*values)

    def test_complete_sources_and_unjudged_baseline(self):
        result = audit.inspect(*self.evidence)
        self.assertEqual((result['groups'], result['frames'], result['proposed_lemma_groups_found']), (16, 4080, 0))

    def test_source_owner_missing(self):
        self.reject(lambda v: v[0]['source_entries'].pop('krdict:86084'), 'original separate ending identities')

    def test_original_note_rewritten(self):
        self.reject(lambda v: v[0]['source_entries']['krdict:86084']['notes'].clear(), 'all original dictionary fields')

    def test_group_omitted(self):
        self.reject(lambda v: v[0]['complete_groups'].pop(), 'all complete original groups')

    def test_proposal_claimed_required(self):
        self.reject(lambda v: v[0]['independent_proposals'][0].update(verdict='required'), 'proposals are not reviewed path judgments')

    def test_proposal_source_borrowed(self):
        self.reject(lambda v: v[0]['independent_proposals'][8].update(source_entry_id='krdict:86083'), 'original occurrence identity and context')

    def test_cache_stream_missing(self):
        self.reject(lambda v: v[1]['runs'].pop(), 'complete original Unicode filter cache workloads')

    def test_original_bytes_changed(self):
        self.reject(lambda v: v[1]['runs'][0].update(input_sha256='0' * 64), 'complete original baseline input')

    def test_filter_flag_removed(self):
        self.reject(lambda v: v[1]['runs'][2]['command'].remove('--dict-only'), 'actual baseline filter and cache command')

    def test_observation_fabricated(self):
        self.reject(lambda v: v[1]['runs'][0]['observed_proposals'][0].update(proposed_lemma_indices=[0]), 'independently rederived unjudged observations')

    def test_native_owner_missing(self):
        self.reject(lambda v: v[2]['original_native_entries'].pop('krdict:86084'), 'all original Native identities')

    def test_native_fields_rewritten(self):
        self.reject(lambda v: v[2]['original_native_entries']['krdict:86084'].update(val='86083'), 'every exact Native projection field')

    def test_original_export_missing(self):
        self.reject(lambda v: v[2]['original_exports'].pop(next(iter(v[2]['original_exports']))), 'all original Native exports')


if __name__ == '__main__':
    unittest.main()
