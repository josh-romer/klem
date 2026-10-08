"""Reject mismatched release/runtime/launcher bindings using complete captured reports."""
import copy
import unittest

import literary_future_kko_package as audit


class PackageGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = audit.inputs()

    def reject(self, report_index, change):
        reports = list(self.reports)
        reports[report_index] = copy.deepcopy(reports[report_index])
        change(reports[report_index])
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,StopIteration)):
            audit.inspect(*reports)

    def test_actual_package_bindings(self):
        result = audit.inspect(*self.reports)
        self.assertEqual(result['release_tests']['passed'],1055)
        self.assertEqual(result['browser']['complete_native_entries'],153)

    def test_release_failure(self):
        self.reject(0,lambda r:r.__setitem__('exit_code',1))

    def test_release_log_binding(self):
        self.reject(0,lambda r:r.__setitem__('log_sha256','0'*64))

    def test_frozen_compile_input(self):
        self.reject(0,lambda r:r['snapshot']['files'].pop('src/engine.rs'))

    def test_wrong_cli_package(self):
        self.reject(1,lambda r:r.__setitem__('cli','/tmp/unverified-cli'))

    def test_adapter_cannot_use_main_cli(self):
        self.reject(2,lambda r:r.__setitem__('adapter',self.reports[1]['cli']))

    def test_launcher_assets(self):
        self.reject(3,lambda r:r.__setitem__('assets','/tmp/unverified-assets'))

    def test_served_javascript_binding(self):
        self.reject(3,lambda r:r['asset_checks'][0].__setitem__('sha256','0'*64))

    def test_launcher_help(self):
        self.reject(3,lambda r:r.__setitem__('help_exit_code',1))

    def test_launcher_cannot_swap_server(self):
        self.reject(3,lambda r:r.__setitem__('launcher_text',r['launcher_text'].replace('exec ','exec /tmp/other ')))

    def test_launcher_command_is_bound(self):
        self.reject(3,lambda r:r['command'].__setitem__(0,'/tmp/other-launcher'))

    def test_server_must_stop(self):
        self.reject(3,lambda r:r.__setitem__('server_stopped',False))


if __name__=='__main__':
    unittest.main()
