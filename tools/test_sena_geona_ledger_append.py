"""Verify the complete promoted ledger independently of historical controls."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import literary_question_geona_runtime as audit


class PromotedLedger(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = audit.read(audit.ROOT/'tests/fixtures/validity.json')
        cls.proposal = audit.read(audit.ROOT/'docs/literary-question-geona-proposed-ledger.json.gz')
        assert len(cls.current['cases']) == 35789

    def rejected(self, change):
        ledger = copy.deepcopy(self.current)
        change(ledger)
        with self.assertRaisesRegex(AssertionError, 'append-only ledger'):
            audit.verify_ledger(ledger, self.proposal)

    def test_whole_actual_promoted_ledger_passes(self):
        self.assertEqual(audit.verify_ledger(self.current, self.proposal)['preserved_cases'], 34920)

    def test_changed_sena_judgment_rejected(self):
        self.rejected(lambda c: c['cases'][-1]['judgments'][0].update(reason='changed source rationale'))

    def test_reordered_sena_cases_rejected(self):
        self.rejected(lambda c: c['cases'].__setitem__(slice(35764, None), c['cases'][35764:][::-1]))

    def test_missing_sena_case_rejected(self):
        self.rejected(lambda c: c['cases'].pop())

    def test_unreviewed_tail_rejected(self):
        def change(c):
            extra = copy.deepcopy(c['cases'][-1])
            extra['id'] = 'unreviewed-extra'
            c['cases'].append(extra)
        self.rejected(change)

    def test_changed_source_identity_rejected(self):
        self.rejected(lambda c: c['sources'].__setitem__('friendly-hortative-sena-78469', 'https://invalid.example/'))

    def test_unused_source_alias_rejected(self):
        self.rejected(lambda c: c['sources'].__setitem__('unreviewed-extra', 'https://invalid.example/'))

    def test_changed_metadata_rejected(self):
        self.rejected(lambda c: c.update(invented_metadata='changed'))

    def test_coordinated_fixture_rewrite_rejected(self):
        original = Path.read_bytes
        def changed(path):
            raw = original(path)
            if path.name == 'friendly-hortative-sena-validity.json':
                suite = json.loads(raw)
                suite['cases'][0]['judgments'][0]['reason'] = 'changed original rationale'
                return json.dumps(suite).encode()
            return raw
        with patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(AssertionError, 'reviewed friendly-hortative Sena preauthored fixture bytes'):
                audit.verify_ledger(self.current, self.proposal)


if __name__ == '__main__':
    unittest.main()
