import copy, unittest
import declarative_dao_audit as audit

class Evidence(unittest.TestCase):
    def rejected(self, change):
        values = copy.deepcopy([audit.prepared, audit.closure, audit.runtime, audit.suite])
        change(*values)
        with self.assertRaises((AssertionError, KeyError, StopIteration, ValueError)):
            audit.inspect(*values)

    def test_complete_evidence(self):
        self.assertEqual(audit.inspect(audit.prepared, audit.closure, audit.runtime, audit.suite)['frames'], 2502)

    def test_missing_original_group(self):
        self.rejected(lambda p, c, r, s: p['complete_groups'].pop())

    def test_clipped_dialogue(self):
        def change(p, c, r, s):
            next(g for g in p['complete_groups'] if len(g['complete_original_examples']) > 1)['complete_original_examples'].pop()
        self.rejected(change)

    def test_missing_expression_identity(self):
        self.rejected(lambda p, c, r, s: c['complete_native_entries'].pop('krdict:88937'))

    def test_wrong_native_pos(self):
        self.rejected(lambda p, c, r, s: c['complete_native_entries']['krdict:88937'].update(pos='어미'))

    def test_missing_cache_run(self):
        self.rejected(lambda p, c, r, s: r['runs'].pop())

    def test_changed_stream_digest(self):
        self.rejected(lambda p, c, r, s: r['runs'][0].update(stdout_sha256='0' * 64))

    def test_missing_frame(self):
        self.rejected(lambda p, c, r, s: r['runs'][0]['records'].pop())

    def test_lost_added_observation(self):
        self.rejected(lambda p, c, r, s: r['changes'].pop())

    def test_changed_source_lemma(self):
        self.rejected(lambda p, c, r, s: s['cases'][0]['judgments'][0].update(lemmas=['invented']))

    def test_wrong_source_allomorph(self):
        self.rejected(lambda p, c, r, s: s['cases'][0]['judgments'][0].update(morphemes=['다오']))

if __name__ == '__main__':
    unittest.main()
