"""Reject fabricated mode bindings, lost source cases and changed old ledger judgments."""
import copy
import unittest
import literary_future_kko_runtime as a
R=a.read(a.ROOT/'docs/literary-future-kko-main-cli-replay.json.gz')
L=a.read(a.ROOT/'tests/fixtures/validity.json')
P=a.read(a.ROOT/'docs/literary-future-kko-append-only-ledger-proposal.json.gz')

def replace_at(value,path,fn):
    if not path:return fn(copy.deepcopy(value))
    result=value.copy();result[path[0]]=replace_at(value[path[0]],path[1:],fn);return result

class RuntimeControls(unittest.TestCase):
    def reject(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError,IndexError)):
            a.inspect(replace_at(R,path,fn))
    def test_actual_capture_passes(self):self.assertEqual(a.inspect(R)['broad_frames'],1128312)
    def test_native_filter_cannot_be_relabelled_raw(self):self.reject(['finite_runs',2,'mode'],lambda _: 'raw')
    def test_missing_finite_mode(self):self.reject(['finite_runs'],lambda rows:rows[:-1])
    def test_original_unicode_input_hash(self):self.reject(['finite_runs',3,'input_sha256'],lambda _: '0'*64)
    def test_full_output_is_bound(self):self.reject(['finite_runs',0,'jsonl_sha256'],lambda _: '0'*64)
    def test_native_filter_command_is_bound(self):self.reject(['finite_runs',2,'command'],lambda c:c[:-1])
    def test_source_capture_is_bound(self):self.reject(['finite_runs',0,'expected_capture_sha256'],lambda _: '0'*64)
    def test_actual_binary_is_bound(self):self.reject(['cli_sha256'],lambda _: '0'*64)
    def test_compile_snapshot_is_bound(self):self.reject(['snapshot_files'],lambda files:{k:v for i,(k,v) in enumerate(files.items()) if i})
    def test_missing_broad_mode(self):self.reject(['broad'],lambda rows:rows[:-1])
    def test_broad_stream_hash(self):self.reject(['broad',3,'sha256'],lambda _: '0'*64)
    def test_old_historical_output_is_bound(self):self.reject(['words',1,'actual_word_analysis_sha256'],lambda _: '0'*64)

class LedgerControls(unittest.TestCase):
    def reject(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):
            a.verify_ledger(replace_at(L,path,fn),P)
    def test_append_only_actual_ledger_passes(self):self.assertEqual(a.verify_ledger(L,P)['individual_added_cases'],77)
    def test_old_case_removal(self):self.reject(['cases'],lambda rows:rows[1:])
    def test_old_verdict_change(self):self.reject(['cases',0,'judgments',0,'verdict'],lambda _: 'forbidden')
    def test_missing_source_occurrence(self):self.reject(['cases'],lambda rows:rows[:34843]+rows[34844:])
    def test_new_scope_cannot_change(self):self.reject(['cases',34843,'judgments',0,'morphemes'],lambda _: ['고'])
    def test_conditional_case_is_not_promoted(self):
        q=copy.deepcopy(P);q['excluded_conditional_or_native_cases'][0]['id']=q['added_cases'][0]['id']
        with self.assertRaises(AssertionError):a.verify_ledger(L,q)
    def test_old_source_mapping_survives(self):
        source=next(iter(L['sources']));self.reject(['sources',source],lambda _: 'https://example.invalid/')

if __name__=='__main__':unittest.main()
