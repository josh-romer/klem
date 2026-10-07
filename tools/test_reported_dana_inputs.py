"""Verify portable input identity and reject incomplete or changed archived bytes."""

import copy
import unittest
from pathlib import Path
from unittest.mock import patch

from copula_expectation_production import read
from reported_dana_inputs import source_snapshots, verify_frozen_inputs


class ArchivedInputGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = read("docs/reported-dana-packaged-production.json")[
            "frozen_inputs"
        ]
        cls.snapshots = source_snapshots()

    def test_all_inputs_verify_without_access_to_original_runtime_files(self):
        original_read = Path.read_bytes
        forbidden = {name for name in self.frozen if name.startswith("/")}

        def read_only_archive(path):
            if str(path) in forbidden:
                self.fail("Attempted to read original runtime input: " + str(path))
            return original_read(path)

        with patch.object(Path, "read_bytes", read_only_archive):
            verify_frozen_inputs(self.frozen)

    def test_missing_temporary_source_snapshot_is_rejected(self):
        snapshots = copy.deepcopy(self.snapshots)
        snapshots.pop("/tmp/klem-written-vowel-candidate-input.txt")
        with self.assertRaises(AssertionError):
            verify_frozen_inputs(self.frozen, snapshots)

    def test_changed_corpus_bytes_are_rejected(self):
        snapshots = copy.deepcopy(self.snapshots)
        name = next(name for name in snapshots if "/data/corpora/" in name)
        snapshots[name]["text"] += "changed"
        with self.assertRaises(AssertionError):
            verify_frozen_inputs(self.frozen, snapshots)

    def test_unknown_absolute_input_is_rejected(self):
        frozen = dict(self.frozen)
        frozen["/tmp/unarchived-input.txt"] = "0" * 64
        with self.assertRaises(AssertionError):
            verify_frozen_inputs(frozen, self.snapshots)

    def test_self_consistent_changed_snapshot_cannot_change_captured_digest(self):
        import hashlib

        snapshots = copy.deepcopy(self.snapshots)
        name = "/tmp/klem-written-vowel-candidate-input.txt"
        snapshots[name]["text"] += "changed"
        snapshots[name]["sha256"] = hashlib.sha256(
            snapshots[name]["text"].encode()
        ).hexdigest()
        with self.assertRaises(AssertionError):
            verify_frozen_inputs(self.frozen, snapshots)


if __name__ == "__main__":
    unittest.main()
