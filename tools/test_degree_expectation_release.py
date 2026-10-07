"""Historical package evidence must remain complete and tamper evident."""
import copy
import unittest
from degree_expectation_audit import read
from degree_expectation_release import verify_release_sources

class HistoricalReleaseSources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = read('docs/degree-expectation-release-sources.json.gz')
        receipt = read('docs/degree-expectation-final-nix.json')
        cls.snapshot = {p: v['sha256'] for p, v in receipt['snapshot']['files'].items()}
        cls.package = receipt['outputs'][0]

    def test_exact_preserved_sources_match_the_independent_final_gate(self):
        verify_release_sources(self.snapshot, self.package, self.sources)

    def test_modified_text_cannot_keep_the_recorded_hash(self):
        sources = copy.deepcopy(self.sources)
        sources['files']['src/grammar.rs']['text'] += '\n// changed after packaging\n'
        with self.assertRaises(AssertionError):
            verify_release_sources(self.snapshot, self.package, sources)

    def test_missing_source_or_another_package_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        del sources['files']['src/grammar.rs']
        with self.assertRaises(AssertionError):
            verify_release_sources(self.snapshot, self.package, sources)
        with self.assertRaises(AssertionError):
            verify_release_sources(self.snapshot, self.package + '-other', self.sources)

    def test_altered_independent_receipt_is_rejected(self):
        snapshot = dict(self.snapshot)
        snapshot['tests/fixtures/validity.json'] = '0' * 64
        with self.assertRaises(AssertionError):
            verify_release_sources(snapshot, self.package, self.sources)

if __name__ == '__main__':
    unittest.main()
