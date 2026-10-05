"""Reject omissions and rewrites in the supplemental release evidence."""

import json
import unittest
from copy import deepcopy

from doeda_partial_origin_corpora import REPORT as CORPORA
from doeda_partial_origin_corpora import inspect as inspect_corpora
from doeda_partial_origin_observations import REPORT as BROAD
from doeda_partial_origin_observations import inspect as inspect_broad
from doeda_partial_origin_package import REPORT as PACKAGE
from doeda_partial_origin_package import inspect as inspect_package
from doeda_partial_origin_performance import REPORT as PERFORMANCE
from doeda_partial_origin_performance import inspect as inspect_performance
from lexical_nada_audit import read


class PartialOriginReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package, cls.broad = read(PACKAGE), read(BROAD)
        cls.corpora, cls.performance = read(CORPORA), read(PERFORMANCE)

    def test_complete_actual_evidence_passes(self):
        self.assertEqual(inspect_package(self.package)["api_words"], 88)
        self.assertEqual(inspect_broad(self.broad), (0, 0))
        self.assertEqual(inspect_corpora(self.corpora), (66570, 32096))
        self.assertEqual(inspect_performance(self.performance), 80)

    def test_missing_api_encoding_entry_or_plain_noun_control_fails(self):
        for field in ("encoding", "entry", "noun"):
            report = deepcopy(self.package)
            if field == "encoding":
                report["runtime"]["batches"].pop()
            elif field == "entry":
                report["runtime"]["native_entries"].popitem()
            else:
                report["runtime"]["ordinary_noun_controls"].pop()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_identity_promotion_or_lost_whole_browser_alternative_fails(self):
        for field in ("identity", "whole"):
            report = deepcopy(self.package)
            diagram = report["browser"]["diagrams"][0]
            if field == "identity":
                diagram["identity"]["relation"] = "recorded_match"
            else:
                diagram["whole_selected"] = diagram["selected"]
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_changed_cli_bytes_or_borrowed_source_gloss_fails(self):
        for field in ("bytes", "gloss"):
            report = deepcopy(self.package)
            if field == "bytes":
                report["runtime"]["batches"][0]["cli_jsonl"] += " "
            else:
                report["browser"]["diagrams"][0]["label"] = "borrowed definition"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_missing_broad_stream_or_false_unchanged_digest_fails(self):
        for field in ("stream", "digest"):
            report = deepcopy(self.broad)
            if field == "stream":
                report["comparisons"].pop()
            else:
                report["comparisons"][0]["after_jsonl_sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_broad(report)

    def test_original_gold_word_or_word_digest_rewrite_fails(self):
        for field in ("gold", "word", "digest"):
            report = deepcopy(self.corpora)
            if field == "gold":
                corpus = report["corpora"][0]
                lines = corpus["after_jsonl"].splitlines()
                row = json.loads(lines[1])
                row["expected"] = ["rewritten gold"]
                lines[1] = json.dumps(row, ensure_ascii=False)
                corpus["after_jsonl"] = "\n".join(lines) + "\n"
            elif field == "word":
                report["after_words"].pop(next(iter(report["after_words"])))
            else:
                report["after_word_stream_sha256"] = "0" * 64
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_corpora(report)

    def test_timing_source_pair_command_or_summary_rewrite_fails(self):
        for field in ("source", "pair", "command", "summary"):
            report = deepcopy(self.performance)
            workload = report["workloads"][0]
            if field == "source":
                report["cli_sha256"] = "0" * 64
            elif field == "pair":
                workload["samples"].pop()
            elif field == "command":
                workload["samples"][0]["command"].append("--dict-only")
            else:
                workload["summary"]["after"]["median_seconds"] = 0
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_performance(report)


if __name__ == "__main__":
    unittest.main()
