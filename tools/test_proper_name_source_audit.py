import copy
import gzip
import json
import unittest
from proper_name_source_audit import ROOT, inspect


class OriginalEvidenceControls(unittest.TestCase):
    def setUp(self):
        self.lexicon = json.loads((ROOT / 'src/dictionary/proper_names.json').read_text())
        self.prepared = json.loads(gzip.decompress((ROOT / 'docs/surname-corpus-preparation.json.gz').read_bytes()))

    def test_original_evidence(self):
        self.assertEqual(inspect(self.lexicon, self.prepared)['training_rows'], 5)

    def test_rejects_missing_or_rewritten_contexts(self):
        for field, value in [('complete_original_sentence', '박 선생님 것'), ('original_row', ['박']), ('source_partition', 'test')]:
            corrupted = copy.deepcopy(self.lexicon)
            corrupted['names'][0]['observations'][0][field] = value
            with self.assertRaises(AssertionError):
                inspect(corrupted, self.prepared)

    def test_rejects_borrowed_dictionary_identity(self):
        corrupted = copy.deepcopy(self.lexicon)
        corrupted['names'][0]['id'] = 'krdict:57518'
        with self.assertRaises(AssertionError):
            inspect(corrupted, self.prepared)

    def test_rejects_held_out_data_or_changed_source(self):
        for field, value in [('partition', 'test'), ('license', 'MIT'), ('source_files', {})]:
            corrupted = copy.deepcopy(self.lexicon)
            corrupted[field] = value
            with self.assertRaises(AssertionError):
                inspect(corrupted, self.prepared)


if __name__ == '__main__':
    unittest.main()
