"""Regression controls for multiple paths and exact explicit-parent provenance."""
import copy
import unittest
from copula_expectation_audit import read, verify_added_source_paths

class SourceParents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = read('docs/copula-expectation-full-source.json.gz')
        word = next(w for w, after in source['after_analyses'].items()
                    if len([p for p in after['analyses'] if p not in source['before_analyses'][w]['analyses']]) > 1)
        rows = [r for r in source['individual_additions'] if r['surface'] == word]
        cls.fixture = {'before_analyses': {word: source['before_analyses'][word]},
                       'after_analyses': {word: source['after_analyses'][word]},
                       'individual_additions': rows,
                       'explicit_parents': {p: source['explicit_parents'][p] for r in rows for p in r['explicit_parents']}}

    def test_every_path_for_one_surface_keeps_its_exact_parent(self):
        self.assertEqual(verify_added_source_paths(self.fixture), 2)

    def test_missing_individual_observation_is_rejected(self):
        fixture = copy.deepcopy(self.fixture)
        fixture['individual_additions'].pop()
        with self.assertRaises(AssertionError):
            verify_added_source_paths(fixture)

    def test_a_parent_with_changed_lexical_identity_is_rejected(self):
        fixture = copy.deepcopy(self.fixture)
        for parent in fixture['explicit_parents'].values():
            parent['analyses'].clear()
        with self.assertRaises(AssertionError):
            verify_added_source_paths(fixture)

if __name__ == '__main__':
    unittest.main()
