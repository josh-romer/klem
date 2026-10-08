import copy
import unittest
from pathlib import Path
import declarative_contrast_sources as a

class HistoricalSourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proof=a.read(a.ROOT/'docs/declarative-contrast-historical-sources.json.gz')
        cls.receipt=a.read(a.ROOT/'docs/declarative-contrast-package-nix.json')
        cls.auxiliary=a.read(a.ROOT/'docs/declarative-contrast-auxiliary-nix.json')
        cls.texts=a.baseline_texts()

    def reject(self,change):
        proof=copy.deepcopy(self.proof);change(proof)
        with self.assertRaises((AssertionError,KeyError,ValueError)):
            a.verify(proof,self.receipt,self.auxiliary,self.texts)

    def test_complete_all_three_profiles(self):
        self.assertEqual(len(a.inspect(a.ROOT/'docs/declarative-contrast-historical-sources.json.gz')),915)

    def test_current_engine_cannot_replace_historical_engine(self):
        self.reject(lambda p:p['updates']['src/engine.rs'].__setitem__('after_text','different engine'))

    def test_wrong_parent_sha(self):
        self.reject(lambda p:p['updates']['src/engine.rs'].__setitem__('before_sha256','0'*64))

    def test_missing_frozen_catalog(self):
        self.reject(lambda p:p['snapshot_files'].pop('web/src/grammar-labels.json'))

    def test_changed_source_derivation(self):
        self.reject(lambda p:p['profiles']['klem'].__setitem__('source','/nix/store/other-source'))

    def test_changed_frontend_relative_path(self):
        self.reject(lambda p:p['profiles']['web-assets']['files']['src/model.ts'].__setitem__('snapshot_path','src/model.ts'))

    def test_changed_executable_mode(self):
        self.reject(lambda p:p['profiles']['klem']['files']['src/engine.rs'].__setitem__('executable',True))

    def test_missing_directory(self):
        self.reject(lambda p:p['profiles']['klem']['directories'].pop())

    def test_core_binary_cannot_masquerade_as_adapter(self):
        self.reject(lambda p:p['profiles']['corpus-adapter'].__setitem__('package',p['profiles']['klem']['package']))

    def test_adapter_cannot_borrow_frontend_source(self):
        self.reject(lambda p:p['profiles']['corpus-adapter'].__setitem__('source',p['profiles']['web-assets']['source']))

    def test_missing_adapter_profile(self):
        self.reject(lambda p:p['profiles'].pop('corpus-adapter'))

    def test_unverified_dump(self):
        self.reject(lambda p:p['profiles']['corpus-adapter'].__setitem__('actual_dump_verified',False))

if __name__=='__main__':unittest.main()
