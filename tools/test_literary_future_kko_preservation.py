"""Reject lost candidates, fabricated provenance and changed annotated corpus gold."""
import copy
import unittest
import literary_future_kko_preservation as a

B=a.read(a.ROOT/'docs/literary-future-kko-prototype-broad.json.gz')
C=a.read(a.ROOT/'docs/literary-future-kko-prototype-corpora.json.gz')
RUN=next(i for i,r in enumerate(B['comparisons']) if r['changed_frames'])

def replace_at(obj,path,fn):
    if not path:return fn(copy.deepcopy(obj))
    result=obj.copy();result[path[0]]=replace_at(obj[path[0]],path[1:],fn);return result

class Controls(unittest.TestCase):
    def reject_broad(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):
            a.inspect(replace_at(B,path,fn),C)
    def reject_corpus(self,path,fn):
        with self.assertRaises((AssertionError,KeyError,ValueError,TypeError)):
            a.inspect(B,replace_at(C,path,fn))
    def test_complete_actual_capture_passes(self):
        r=a.inspect(B,C)
        self.assertEqual(r['broad_frames'],1128312)
        self.assertEqual(r['individually_unjudged_broad_additions'],9)
        self.assertEqual(r['changed_corpus_words'],0)
    def test_missing_new_path_observation(self):
        self.reject_broad(['individual_additions'],lambda rows:rows[:-1])
    def test_individual_id_is_rederived(self):
        self.reject_broad(['individual_additions',0,'id'],lambda text:text+'invented')
    def test_original_line_is_bound(self):
        self.reject_broad(['individual_additions',0,'complete_original_line'],lambda text:text+' invented')
    def test_structural_proposal_is_not_context_certification(self):
        self.reject_broad(['individual_additions',0,'contextual_verdict'],lambda _: 'correct')
    def test_previous_reading_assessment_is_preserved(self):
        self.reject_broad(['comparisons',RUN,'changed_frames',0,'before','dictionary','readings',0,'status'],lambda _: 'fabricated')
    def test_original_utf8_span_is_checked(self):
        self.reject_broad(['comparisons',RUN,'changed_frames',0,'after','span','start'],lambda n:n+1)
    def test_missing_complete_mode_is_rejected(self):
        self.reject_broad(['comparisons'],lambda rows:rows[:-1])
    def test_baseline_is_not_the_new_binary(self):
        self.reject_broad(['before_cli_sha256'],lambda _:B['cli_sha256'])
    def test_equal_frames_have_equal_stream_hash(self):
        self.reject_broad(['comparisons',0,'after_jsonl_sha256'],lambda _: '0'*64)
    def test_original_gold_row_is_immutable(self):
        self.reject_corpus(['corpora',0,'original_converted_rows',0,'surface'],lambda text:text+'꼬')
    def test_gold_recovery_is_recomputed(self):
        self.reject_corpus(['corpora',0,'comparisons',0,'after','recovered'],lambda n:n+1)
    def test_candidate_summary_is_recomputed(self):
        self.reject_corpus(['corpora',0,'after_summary','candidate_count_sum'],lambda n:n+1)
    def test_original_context_is_immutable(self):
        self.reject_corpus(['corpora',0,'original_source_text'],lambda text:text+' invented')
    def test_missing_corpus_partition_is_rejected(self):
        self.reject_corpus(['corpora'],lambda rows:rows[:-1])

if __name__=='__main__':unittest.main()
