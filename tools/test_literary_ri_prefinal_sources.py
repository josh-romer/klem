import copy
import unittest
import literary_ri_prefinal_sources as a


class HistoricalSourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof = a.read(a.ROOT / 'docs/literary-ri-prefinal-historical-sources.json.gz')
        cls.receipt = a.read(a.ROOT / 'docs/literary-ri-prefinal-package-nix.json')
        cls.texts = a.baseline_texts()

    def reject(self, change):
        proof = copy.deepcopy(self.proof)
        change(proof)
        with self.assertRaises((AssertionError, KeyError, ValueError)):
            a.verify(proof, self.receipt, self.texts)

    def test_all_exact_historical_package_inputs(self):
        self.assertEqual(len(a.inspect(a.ROOT / 'docs/literary-ri-prefinal-historical-sources.json.gz')), 901)

    def test_current_engine_cannot_replace_historical_engine(self):
        self.reject(lambda p: p['updates']['src/engine.rs'].__setitem__('after_text', 'different engine'))

    def test_previous_source_sha_cannot_be_replaced(self):
        self.reject(lambda p: p['updates']['src/engine.rs'].__setitem__('before_sha256', '0' * 64))

    def test_missing_frozen_model_is_rejected(self):
        self.reject(lambda p: p['snapshot_files'].pop('web/src/model.ts'))

    def test_package_derivation_source_cannot_change(self):
        self.reject(lambda p: p['profiles']['klem'].__setitem__('source', '/nix/store/other-source'))

    def test_frontend_relative_paths_cannot_borrow_rust_paths(self):
        self.reject(lambda p: p['profiles']['web-assets']['files']['src/model.ts'].__setitem__('snapshot_path', 'src/model.ts'))

    def test_nar_executable_flag_is_bound(self):
        self.reject(lambda p: p['profiles']['klem']['files']['src/engine.rs'].__setitem__('executable', True))

    def test_source_directory_cannot_disappear(self):
        self.reject(lambda p: p['profiles']['klem']['directories'].pop())

    def test_derivation_output_cannot_change(self):
        self.reject(lambda p: p['profiles']['web-assets'].__setitem__('package', self.proof['profiles']['klem']['package']))


if __name__ == '__main__':
    unittest.main()
