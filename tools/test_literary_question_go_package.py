"""Reject broken binding among the actual Nix package and runtime captures."""
import copy
import unittest
from functools import lru_cache
from unittest.mock import patch
import literary_question_go_package as audit

cached_read = lru_cache(maxsize=None)(audit.read)

class BindingGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = audit.inputs()

    def setUp(self):
        reader = patch.object(audit, 'read', cached_read)
        reader.start()
        self.addCleanup(reader.stop)

    def reject(self, index, mutate):
        reports = list(self.reports)
        reports[index] = copy.deepcopy(reports[index])
        mutate(reports[index])
        with self.assertRaises((AssertionError, KeyError, ValueError, StopIteration)):
            audit.inspect(*reports)

    def test_complete_actual_package_passes(self):
        self.assertTrue(audit.inspect(*self.reports)['owned_servers_stopped'])

    def test_source_input_cannot_disappear(self):
        self.reject(0, lambda r: r['snapshot']['files'].pop('src/engine.rs'))

    def test_full_release_log_is_bound(self):
        self.reject(0, lambda r: r.__setitem__('log_sha256', '0'*64))

    def test_actual_package_binary_is_bound(self):
        self.reject(1, lambda r: r.__setitem__('cli', '/tmp/unrelated-cli'))

    def test_separate_adapter_output_is_bound(self):
        self.reject(2, lambda r: r.__setitem__('adapter', '/tmp/unrelated-adapter'))

    def test_packaged_assets_are_bound(self):
        self.reject(3, lambda r: r['command'].__setitem__(2, '/tmp/unrelated-assets'))

    def test_copied_server_is_bound(self):
        self.reject(3, lambda r: r['frozen_inputs'].__setitem__(r['command'][0], '0'*64))

    def test_frontend_source_is_bound(self):
        self.reject(3, lambda r: r['frontend_snapshot'].__setitem__('src/grammar-labels.json', '0'*64))

    def test_launcher_must_stop_its_server(self):
        self.reject(5, lambda r: r.__setitem__('server_stopped', False))

    def test_launcher_arguments_cannot_be_rewritten(self):
        def mutate(r):
            r['launcher_text'] = r['launcher_text'].replace('--assets', '--wrong-assets')
            r['launcher_sha256'] = audit.sha(r['launcher_text'].encode())
        self.reject(5, mutate)

    def test_launcher_assets_cannot_disappear(self):
        self.reject(5, lambda r: r['asset_checks'].pop())

    def test_original_launcher_api_cannot_disappear(self):
        self.reject(5, lambda r: r['responses'].pop())

if __name__ == '__main__':
    unittest.main()
