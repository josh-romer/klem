"""Reject omissions, source drift and policy leakage in the finite source audit."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from present_prefinal_audit import read, sha, verify, verify_cases, verify_sources, verify_streams


class PresentPrefinalGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.discovery = read("docs/present-prefinal-source-discovery.json.gz")
        cls.owners = read("docs/present-prefinal-owner-preparation.json.gz")
        cls.draft = read("docs/present-prefinal-judgment-draft.json")
        cls.native = read("tests/fixtures/present-prefinal-native.json")
        cls.english = read("tests/fixtures/krdict-present-prefinal-english.json")
        cls.raw = read("tests/fixtures/present-prefinal-validity.json")
        cls.policy = read("tests/fixtures/present-prefinal-policy.json")
        cls.ledger = read("tests/fixtures/validity.json")

    def sources(self, discovery=None, draft=None, native=None):
        verify_sources(discovery or self.discovery, self.owners,
                       draft or self.draft, native or self.native, self.english)

    def test_offline_audit_never_reads_original_runtime_inputs(self):
        original = Path.read_bytes
        forbidden = set(self.discovery["frozen_inputs"])

        def archived(path):
            self.assertNotIn(str(path), forbidden)
            return original(path)

        with patch.object(Path, "read_bytes", archived):
            self.assertEqual(verify()["source_occurrences"], 10)

    def test_dialogue_reply_cannot_be_omitted(self):
        draft = copy.deepcopy(self.draft)
        draft["cases"] = [c for c in draft["cases"] if c["surface"] != "나간다던데"]
        with self.assertRaises(AssertionError):
            self.sources(draft=draft)

    def test_incidental_adnominal_cannot_replace_owned_prefinal(self):
        draft = copy.deepcopy(self.draft)
        draft["cases"][-6]["surface"] = "다니는"
        with self.assertRaises(AssertionError):
            self.sources(draft=draft)

    def test_original_group_cannot_be_truncated(self):
        discovery = copy.deepcopy(self.discovery)
        discovery["all_original_groups"][3]["original"].pop()
        with self.assertRaises(AssertionError):
            self.sources(discovery=discovery)

    def test_native_attachment_note_drift_is_rejected(self):
        native = copy.deepcopy(self.native)
        native["krdict:85037"]["notes"].append("으시 뒤에도 쓴다")
        with self.assertRaises(AssertionError):
            self.sources(native=native)

    def test_dictionary_policy_cannot_leak_into_raw_ledger(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["cases"].append(copy.deepcopy(self.policy["cases"][-1]))
        with self.assertRaises(AssertionError):
            verify_cases(self.draft, self.raw, self.policy, ledger)

    def altered_capture(self):
        discovery = copy.deepcopy(self.discovery)
        capture = discovery["runs"][0]["stages"]["after"]
        frames = [json.loads(line) for line in capture["jsonl"].splitlines()]
        return discovery, capture, frames

    @staticmethod
    def encode(capture, frames):
        capture["jsonl"] = "\n".join(json.dumps(f, ensure_ascii=False) for f in frames) + "\n"
        capture["sha256"] = sha(capture["jsonl"].encode())

    def test_self_consistent_missing_old_path_is_rejected(self):
        discovery, capture, frames = self.altered_capture()
        target = next(f for f in frames if f["surface"] == "찾는다나")
        target["analysis"]["analyses"][0] = copy.deepcopy(target["analysis"]["analyses"][-1])
        self.encode(capture, frames)
        with self.assertRaises((AssertionError, ValueError)):
            verify_streams(discovery)

    def test_self_consistent_changed_byte_span_is_rejected(self):
        discovery, capture, frames = self.altered_capture()
        frames[0]["span"]["end"] -= 1
        self.encode(capture, frames)
        with self.assertRaises(AssertionError):
            verify_streams(discovery)


if __name__ == "__main__":
    unittest.main()
