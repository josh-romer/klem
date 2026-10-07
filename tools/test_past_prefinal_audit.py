"""Meaningful omissions and self-consistent capture corruption must be rejected."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from past_prefinal_audit import read, sha, verify, verify_sources, verify_targets, verify_streams, verify_browser


class SourceGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.capture = read('docs/past-prefinal-source-discovery.json.gz')
        cls.primary = read('docs/past-prefinal-native-preparation.json.gz')
        cls.owners = read('docs/past-prefinal-owner-preparation.json.gz')
        cls.draft = read('docs/past-prefinal-judgments.json')
        cls.inventory = read('docs/past-prefinal-literal-inventory.json')
        cls.suite = read('tests/fixtures/past-prefinal-validity.json')
        cls.boundary = read('docs/past-prefinal-boundary-capture.json.gz')

    def targets(self, draft=None, inventory=None, suite=None):
        verify_targets(self.capture,draft or self.draft,inventory or self.inventory,suite or self.suite)

    def test_browser_missing_allomorph_alias_is_rejected(self):
        browser = read('docs/past-prefinal-main-browser.json.gz')
        browser['responses'][0]['response']['grammar']['-었-'].pop()
        with self.assertRaises(AssertionError):
            verify_browser(browser,self.owners,self.suite)

    def test_browser_missing_second_polite_analysis_is_rejected(self):
        browser = read('docs/past-prefinal-main-browser.json.gz')
        browser['diagrams'] = [r for r in browser['diagrams'] if not r['judgment_id'].endswith('whole-polite')]
        with self.assertRaises(AssertionError):
            verify_browser(browser,self.owners,self.suite)

    def test_browser_changed_full_native_sense_is_rejected(self):
        browser = read('docs/past-prefinal-main-browser.json.gz')
        next(r for r in browser['native'] if r['id']=='krdict:66954')['response']['entry']['senses'].pop()
        with self.assertRaises(AssertionError):
            verify_browser(browser,self.owners,self.suite)

    def test_offline_audit_never_reads_original_runtime_inputs(self):
        original = Path.read_bytes
        forbidden = set(self.capture['frozen_inputs'])
        forbidden.update('/home/josh/projects/klem/'+p for p in self.owners['source_hashes'])
        def archived(path):
            self.assertNotIn(str(path),forbidden)
            return original(path)
        with patch.object(Path,'read_bytes',archived):
            self.assertEqual(verify()['primary_occurrences'],44)

    def test_dialogue_reply_cannot_be_omitted(self):
        draft = copy.deepcopy(self.draft)
        draft['cases'] = [c for c in draft['cases'] if c['surface']!='괜찮았어']
        with self.assertRaises(AssertionError):
            self.targets(draft=draft)

    def test_future_certainty_original_group_cannot_be_reassigned(self):
        draft = copy.deepcopy(self.draft)
        case = next(c for c in draft['cases'] if c['surface']=='혼났다')
        case['source_occurrence']['sense']='1'
        with self.assertRaises(AssertionError):
            self.targets(draft=draft)

    def test_incidental_lexical_ss_coda_cannot_disappear(self):
        inventory = copy.deepcopy(self.inventory)
        inventory['literal_observations'] = [r for r in inventory['literal_observations'] if r['surface']!='있어']
        with self.assertRaises(AssertionError):
            self.targets(inventory=inventory)

    def test_incidental_lexical_ss_coda_cannot_be_claimed_as_past(self):
        inventory = copy.deepcopy(self.inventory)
        row = next(r for r in inventory['literal_observations'] if r['surface']=='있던')
        row['role']='primary_structural_proposal'
        with self.assertRaises(AssertionError):
            self.targets(inventory=inventory)

    def test_source_owned_eu_exception_cannot_be_erased(self):
        draft,suite = copy.deepcopy(self.draft),copy.deepcopy(self.suite)
        for data in (draft,suite):
            next(c for c in data['cases'] if c['surface']=='잠갔니')['judgments'][0]['lemmas']=['잠갔다']
        with self.assertRaises(AssertionError):
            self.targets(draft=draft,suite=suite)

    def test_specific_boundary_cannot_be_broadened(self):
        draft,suite = copy.deepcopy(self.draft),copy.deepcopy(self.suite)
        for data in (draft,suite):
            data['cases'][-1]['judgments'][0].pop('morphemes')
        with self.assertRaises((AssertionError,KeyError)):
            self.targets(draft=draft,suite=suite)

    def test_self_consistent_changed_byte_span_is_rejected(self):
        capture = copy.deepcopy(self.capture)
        run = capture['runs'][0]
        frames = [json.loads(line) for line in run['jsonl'].splitlines()]
        frames[0]['span']['end']-=1
        run['jsonl']='\n'.join(json.dumps(f,ensure_ascii=False) for f in frames)+'\n'
        run['sha256']=sha(run['jsonl'].encode())
        with self.assertRaises(AssertionError):
            verify_streams(capture,self.boundary)

    def test_self_consistent_new_malformed_past_reading_is_rejected(self):
        boundary = copy.deepcopy(self.boundary)
        run = boundary['runs'][0]
        response = json.loads(run['json'])
        response['analyses'].append({'lemmas':[{'text':'가다','kind':'predicate'}],
                                    'morphemes':[{'form':'었','kind':'prefinal'},{'form':'다','kind':'ending'}],
                                    'rules':['prefinal.past'],'unchanged':False})
        run['json']=json.dumps(response,ensure_ascii=False)+'\n'
        run['sha256']=sha(run['json'].encode())
        with self.assertRaises(AssertionError):
            verify_streams(self.capture,boundary)

    def test_contextual_certification_cannot_be_inferred(self):
        inventory = copy.deepcopy(self.inventory)
        inventory['literal_observations'][0]['contextual_verdict']='reviewed'
        with self.assertRaises(AssertionError):
            self.targets(inventory=inventory)


if __name__=='__main__':
    unittest.main()
