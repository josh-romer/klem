"""Verify the stable review queue for every observed sourced-ending addition."""
import hashlib

from degree_expectation_broad import REPORT, inspect
from lexical_nada_audit import ROOT, read, sha


def verify():
    path = ROOT / 'docs/degree-expectation-individual-observations.json.gz'
    report = read(path)
    assert report['schema_version'] == 1
    assert report['checklist'] == ['COV-017by', 'COV-017bz']
    assert report['capture_sha256'] == sha(REPORT)
    assert report['companions_sha256'] == sha(ROOT / 'docs/degree-expectation-main-companions.json.gz')
    assert report['native_closure_sha256'] == sha(ROOT / 'docs/degree-expectation-main-broad-native-closure.json.gz')
    candidates, spacing = inspect(read(REPORT))
    assert report['candidate_changes'] == candidates and len(candidates) == 146
    assert report['spacing_component_changes'] == spacing == []
    assert len({row['id'] for row in candidates}) == len(candidates)
    assert all(row['contextual_verdict'] == 'unjudged' and row['independent_review'] == 'pending'
               for row in candidates)
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest() == report['producer']['sha256']
    return len(candidates)


if __name__ == '__main__':
    print('Verified individually tracked candidate additions:', verify())
