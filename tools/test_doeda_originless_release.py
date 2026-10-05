"""Reject omissions and rewrites in actual release, broad and corpus evidence."""

import hashlib
import json
import unittest
from copy import deepcopy

from doeda_originless_corpora import REPORT as CORPORA
from doeda_originless_corpora import inspect as inspect_corpora
from doeda_originless_observations import REPORT as BROAD
from doeda_originless_observations import inspect as inspect_broad
from doeda_originless_package import REPORT as PACKAGE
from doeda_originless_package import inspect as inspect_package
from doeda_originless_performance import REPORT as PERFORMANCE
from doeda_originless_performance import inspect as inspect_performance
from lexical_nada_audit import read


class OriginlessReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package, cls.broad, cls.corpora = read(PACKAGE), read(BROAD), read(CORPORA)
        cls.performance = read(PERFORMANCE)

    def test_complete_actual_release_evidence_passes(self):
        self.assertEqual(inspect_package(self.package)["api_words"], 508)
        self.assertEqual(inspect_broad(self.broad), (18, 8))
        self.assertEqual(inspect_corpora(self.corpora), (66570, 6, 8))
        self.assertEqual(inspect_performance(self.performance), 80)

    def test_missing_unicode_or_native_endpoint_fails(self):
        for field in ("unicode", "entry"):
            report = deepcopy(self.package)
            if field == "unicode":
                report["runtime"]["batches"].pop()
            else:
                report["runtime"]["native_entries"].popitem()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_changed_cli_bytes_or_borrowed_browser_gloss_fails(self):
        for field in ("bytes", "gloss"):
            report = deepcopy(self.package)
            if field == "bytes":
                report["runtime"]["batches"][0]["cli_jsonl"] += " "
            else:
                report["browser"]["diagrams"][0]["label"] = "borrowed meaning"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_plain_noun_identity_leak_or_missing_whole_alternative_fails(self):
        for field in ("noun", "whole"):
            report = deepcopy(self.package)
            if field == "noun":
                control = report["runtime"]["ordinary_noun_controls"][0]
                record = next(
                    r for r in control["api"]["records"] if r["kind"] == "word"
                )
                entry = next(
                    e
                    for a in record["dictionary"]["readings"]
                    for l in a["lemmas"]
                    for e in l["entries"]
                )
                entry["derivational_identity"] = {"status": "unknown"}
                control["cli_jsonl"] = "".join(
                    json.dumps(r, ensure_ascii=False) + "\n"
                    for r in control["api"]["records"]
                )
                control["cli_jsonl_sha256"] = hashlib.sha256(
                    control["cli_jsonl"].encode()
                ).hexdigest()
            else:
                d = report["browser"]["diagrams"][0]
                d["whole_selected"] = d["selected"]
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_package(report)

    def test_broad_candidate_loss_or_changed_original_assessment_fails(self):
        for field in ("candidate", "assessment"):
            report = deepcopy(self.broad)
            record = report["changed_record_pairs"][0]["after"]
            if field == "candidate":
                record["analysis"]["analyses"].pop(0)
            else:
                # Mutate the reading of an actual original analysis.
                original = report["changed_record_pairs"][0]["before"]["analysis"][
                    "analyses"
                ][0]
                index = record["analysis"]["analyses"].index(original)
                record["dictionary"]["readings"][index]["status"] = "rewritten"
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_broad(report)

    def test_missing_broad_pair_or_incorrect_owned_order_fails(self):
        for field in ("record", "order"):
            report = deepcopy(self.broad)
            if field == "record":
                report["changed_record_pairs"].pop()
            else:
                key = next(
                    k for k, v in report["owned_components"].items() if v and len(v) > 1
                )
                report["owned_components"][key].reverse()
            with self.subTest(field=field), self.assertRaises(AssertionError):
                inspect_broad(report)

    def test_original_gold_or_word_digest_rewrite_fails(self):
        for field in ("gold", "digest", "word"):
            report = deepcopy(self.corpora)
            if field == "gold":
                corpus = report["corpora"][0]
                lines = corpus["after_jsonl"].splitlines()
                row = json.loads(lines[1])
                row["expected"] = ["rewritten gold"]
                lines[1] = json.dumps(row, ensure_ascii=False)
                corpus["after_jsonl"] = "\n".join(lines) + "\n"
            elif field == "digest":
                report["after_word_stream_sha256"] = "0" * 64
            else:
                report["after_words"].pop(next(iter(report["after_words"])))
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
