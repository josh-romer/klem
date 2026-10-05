"""Reject gaps or rewrites in complete packaged, broad and corpus evidence."""

import unittest
from copy import deepcopy

from doeda_identity_corpora import REPORT as CORPUS
from doeda_identity_corpora import inspect as inspect_corpus
from doeda_identity_observations import REPORT as BROAD
from doeda_identity_observations import inspect as inspect_broad
from doeda_identity_package import REPORT as PACKAGE
from doeda_identity_package import inspect as inspect_package
from doeda_identity_performance import FOCUSED, verify_focused_data
from doeda_identity_performance import REPORT as TIMING
from lexical_nada_audit import read


class IdentityReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package, cls.broad, cls.corpus = read(PACKAGE), read(BROAD), read(CORPUS)

    def test_complete_actual_checkpoints_pass(self):
        self.assertEqual(inspect_package(self.package)["api_words"], 4608)
        self.assertEqual(inspect_broad(self.broad), 355)
        self.assertEqual(inspect_corpus(self.corpus), 66570)

    def test_missing_unicode_cohort_and_native_endpoint_fail(self):
        for field in ("unicode", "entry"):
            report = deepcopy(self.package)
            if field == "unicode":
                report["runtime"]["batches"].pop()
            else:
                report["runtime"]["native_entries"].popitem()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_changed_cli_bytes_and_borrowed_browser_gloss_fail(self):
        for field in ("cli", "gloss"):
            report = deepcopy(self.package)
            if field == "cli":
                report["runtime"]["batches"][0]["cli_jsonl"] += " "
            else:
                report["browser"]["diagrams"][0]["label"] = "antipathy"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_original_broad_candidate_and_assessment_loss_fail(self):
        for field in ("candidate", "assessment"):
            report = deepcopy(self.broad)
            word = next(
                p["after"]
                for p in report["changed_record_pairs"]
                if p["after"]["kind"] == "word"
            )
            if field == "candidate":
                word["analysis"]["analyses"].pop()
            else:
                word["dictionary"]["readings"][0]["status"] = "rewritten"
            with (
                self.subTest(field=field),
                self.assertRaises((AssertionError, IndexError)),
            ):
                inspect_broad(report)

    def test_missing_broad_record_and_wrong_owned_order_fail(self):
        for field in ("record", "order"):
            report = deepcopy(self.broad)
            if field == "record":
                report["changed_record_pairs"].pop()
            else:
                key = next(iter(report["owned_components"]))
                report["owned_components"][key].reverse()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_broad(report)

    def test_original_gold_and_complete_word_digest_cannot_be_rewritten(self):
        for field in ("gold", "words"):
            report = deepcopy(self.corpus)
            if field == "gold":
                report["corpora"][0]["after_jsonl"] += "\n"
            else:
                report["word_stream_sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_corpus(report)

    def test_focused_timing_requires_pairs_source_and_actual_summary(self):
        original, timing = read(FOCUSED), read(TIMING)
        verify_focused_data(original, timing)
        for field in ("pair", "source", "summary", "cpu"):
            report = deepcopy(original)
            if field == "pair":
                report["workloads"][0]["samples"].pop()
            elif field == "source":
                report["cli_sha256"] = "0" * 64
            elif field == "summary":
                report["workloads"][0]["summary"]["after"]["median_seconds"] = 0.1
            else:
                report["cpu_affinity"] = [max(report["allowed_cpus"]) + 1]
            with self.subTest(field=field), self.assertRaises(AssertionError):
                verify_focused_data(report, timing)


if __name__ == "__main__":
    unittest.main()
