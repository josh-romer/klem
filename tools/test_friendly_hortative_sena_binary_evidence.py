"""Verify that portable evidence replay cannot claim live executable verification."""
import copy
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import friendly_hortative_sena_runtime_audit as audit


class BinaryEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = audit.inputs(binary_evidence='captured')

    def test_live_is_the_explicit_default(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(audit.binary_mode(), 'live')

    def test_unknown_mode_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, 'explicit live or captured'):
            audit.inputs(binary_evidence='unchecked')

    def test_captured_mode_never_reads_current_or_parent_executable_files(self):
        paths = {b['path'] for b in self.original['binding']['binaries'].values()}
        paths.update(self.original['binding']['protected_parent_binaries'])
        original = Path.read_bytes
        def read(path):
            self.assertNotIn(str(path), paths, 'captured mode must not read host executables')
            return original(path)
        with patch.object(Path, 'read_bytes', read):
            value = audit.inputs(binary_evidence='captured')
            audit.inspect_binding(value)
        self.assertFalse(value['binary_evidence']['live_executable_files_verified'])

    def test_captured_mode_cannot_claim_live_files_verified(self):
        value = self.original.copy()
        value['binary_evidence'] = dict(self.original['binary_evidence'], live_executable_files_verified=True)
        with self.assertRaisesRegex(AssertionError, 'honest immutable binary evidence scope'):
            audit.inspect_binding(value)

    def test_captured_parent_fingerprint_cannot_change(self):
        value = self.original.copy()
        value['parent_binaries'] = self.original['parent_binaries'].copy()
        value['parent_binaries'][next(iter(value['parent_binaries']))] = 'changed'
        with self.assertRaisesRegex(AssertionError, 'all original parent binaries retained'):
            audit.inspect_binding(value)

    def test_binding_receipt_cannot_be_borrowed(self):
        value = self.original.copy()
        value['binary_evidence'] = dict(self.original['binary_evidence'], binding_receipt_sha256='changed')
        with self.assertRaisesRegex(AssertionError, 'honest immutable binary evidence scope'):
            audit.inspect_binding(value)

    def test_captured_output_explicitly_reports_its_scope(self):
        result = audit.inspect(self.original)
        self.assertEqual(result['binary_evidence']['mode'], 'captured')
        self.assertFalse(result['binary_evidence']['live_executable_files_verified'])
        self.assertFalse(result['full_coverage_complete'])


if __name__ == '__main__':
    unittest.main()
