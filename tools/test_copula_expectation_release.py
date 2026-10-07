"""Release checks must reject incomplete streams and altered source/build evidence."""
import copy
import gzip
import unittest

from copula_expectation_production import ROOT, read
from copula_expectation_release import verify_build, verify_streams


class CopulaReleaseBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = read('docs/copula-expectation-package-nix.json')
        cls.archive = read('docs/copula-expectation-main-sources.json.gz')
        cls.sources = read('docs/copula-expectation-package-sources.json')
        cls.log = gzip.decompress((ROOT / 'docs/copula-expectation-package-nix.log.gz').read_bytes()).decode()

    def test_preserved_build_matches_independent_source_archive(self):
        verify_build(self.receipt, self.archive, self.log, self.sources)

    def test_changed_source_or_build_log_is_rejected(self):
        archive = copy.deepcopy(self.archive)
        archive['files']['src/grammar.rs']['text'] += '\n// altered\n'
        with self.assertRaises(AssertionError):
            verify_build(self.receipt, archive, self.log, self.sources)
        with self.assertRaises(AssertionError):
            verify_build(self.receipt, self.archive, self.log + '\nchanged\n', self.sources)

    def test_missing_nix_source_or_changed_derivation_is_rejected(self):
        sources = copy.deepcopy(self.sources)
        del sources['files']['src/engine.rs']
        with self.assertRaises(AssertionError):
            verify_build(self.receipt, self.archive, self.log, sources)
        sources = copy.deepcopy(self.sources)
        sources['derivation_json'][sources['derivation']]['env']['src'] += '-other'
        with self.assertRaises(AssertionError):
            verify_build(self.receipt, self.archive, self.log, sources)


class CopulaReleaseStreams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = read('docs/copula-expectation-packaged-production.json')
        cls.source = read('docs/copula-expectation-source-streams.json.gz')
        cls.broad = read('docs/copula-expectation-broad.json.gz')
        cls.corpus = read('docs/copula-expectation-corpora.json.gz')
        cls.cli = read('docs/copula-expectation-packaged-checks.json')['nix_outputs']['klem'] + '/bin/klem'

    def verify(self, report):
        verify_streams(report, self.source, self.broad, self.corpus, self.cli)

    def test_missing_or_duplicate_source_stream_is_rejected(self):
        report = copy.deepcopy(self.report)
        report['source_runs'].pop()
        with self.assertRaises(AssertionError):
            self.verify(report)
        report['source_runs'].append(report['source_runs'][0])
        with self.assertRaises(AssertionError):
            self.verify(report)

    def test_changed_packaged_command_or_broad_hash_is_rejected(self):
        report = copy.deepcopy(self.report)
        report['source_runs'][0]['command'][0] = '/tmp/another-klem'
        with self.assertRaises(AssertionError):
            self.verify(report)
        report = copy.deepcopy(self.report)
        report['broad_runs'][0]['sha256'] = '0' * 64
        with self.assertRaises(AssertionError):
            self.verify(report)

    def test_evaluator_execution_claim_and_incomplete_gold_are_rejected(self):
        report = copy.deepcopy(self.report)
        report['corpus_runs'] = report['corpus_reference_runs']
        with self.assertRaises(AssertionError):
            self.verify(report)
        report = copy.deepcopy(self.report)
        report['corpus_validation']['verified_gold_rows'] -= 1
        with self.assertRaises(AssertionError):
            self.verify(report)


if __name__ == '__main__':
    unittest.main()
