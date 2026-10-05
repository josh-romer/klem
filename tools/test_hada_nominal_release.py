"""Reject incomplete release, cache-parity and timing evidence."""
import copy
import unittest

import hada_nominal_audit as audit
import hada_nominal_performance as performance
import hada_nominal_release as release


class ReleaseGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = audit.read(release.REPORT)

    def test_complete_release(self):
        self.assertEqual(release.inspect(self.report)["rust_passed"], 938)

    def test_missing_release_cache_run(self):
        report = copy.deepcopy(self.report)
        del report["runs"]["compatible"]["NFD-uncached"]
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_incorrect_rust_receipt(self):
        report = copy.deepcopy(self.report)
        report["rust_passed"] = 909
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_missing_api_encoding(self):
        report = copy.deepcopy(self.report)
        report["api_batches"].pop()
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_only_measured_elapsed_time_may_vary(self):
        report = copy.deepcopy(self.report)
        report["api_batches"][0]["response"]["elapsed_ms"] += 1
        release.inspect(report)
        record = next(r for r in report["api_batches"][0]["response"]["records"] if r.get("analysis"))
        record["analysis"]["normalized"] = "rewritten"
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_rewritten_browser_compound(self):
        report = copy.deepcopy(self.report)
        report["browser"]["diagrams"][0]["parts"][1] = "되"
        with self.assertRaises(AssertionError):
            release.inspect(report)


    def test_nominal_hint_cannot_borrow_unrelated_entry(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['word'] == '건강해요')
        diagram['entry'] = 'krdict:14668'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_direct_identity_cannot_borrow_another_index(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['word'] == '건강해요')
        entry = next(e for e in diagram['owner']['entries'] if e['id'] == diagram['entry'])
        entry['derivational_identity']['morpheme_index'] = 1
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_adjective_formation_label_cannot_be_verbal(self):
        report = copy.deepcopy(self.report)
        diagram = next(d for d in report['browser']['diagrams'] if d['word'] == '건강해요')
        diagram['formation_label'] = 'Action / verb formation'
        with self.assertRaises(AssertionError):
            release.inspect(report)

    def test_assets_receipt_cannot_be_replaced(self):
        report = copy.deepcopy(self.report)
        report['assets_nix_log']['text'] = 'unverified output'
        with self.assertRaises(AssertionError):
            release.inspect(report)


class TimingGuards(unittest.TestCase):
    def test_complete_timings(self):
        self.assertEqual(performance.inspect(audit.read(performance.REPORT)), 80)

    def test_missing_paired_sample(self):
        report = audit.read(performance.REPORT)
        report["workloads"][0]["samples"].pop()
        with self.assertRaises(AssertionError):
            performance.inspect(report)

    def test_missing_cache_stream(self):
        from unittest.mock import patch
        original_read = performance.read

        def incomplete_read(path):
            value = original_read(path)
            if path.name == 'hada-nominal-cache-parity.json':
                value['streams'].pop()
            return value

        with patch.object(performance, 'read', side_effect=incomplete_read), self.assertRaises(AssertionError):
            performance.inspect(audit.read(performance.REPORT))


class StreamGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = audit.read(release.REPORT)
        cls.broad = audit.read(release.BROAD)
        cls.corpora = audit.read(release.CORPORA)

    def test_release_streams(self):
        self.assertEqual(release.inspect_streams(self.package, self.broad, self.corpora),
                         (1128312, 66570, 32096))

    def test_wrong_release_executable(self):
        broad = dict(self.broad, cli_sha256='wrong')
        with self.assertRaises(AssertionError):
            release.inspect_streams(self.package, broad, self.corpora)

    def test_missing_corpus_word(self):
        corpora = dict(self.corpora, after_words=dict(self.corpora['after_words']))
        corpora['after_words'].pop(next(iter(corpora['after_words'])))
        with self.assertRaises(AssertionError):
            release.inspect_streams(self.package, self.broad, corpora)


if __name__ == "__main__":
    unittest.main()
