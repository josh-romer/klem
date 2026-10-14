"""Verify a bounded Sena append without granting any active promotion claim."""
import gzip
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'friendly-hortative-sena' if HERE.name == 'friendly-hortative-sena-prepared' else HERE.parent
MANIFEST_SHA = '234d0168c0433cb35339b30e39884f1f0d3423bd25fd9c06b6cfd470099f6476'
DRAFT_SHA = 'a9a623efb161030f2f369914a2e75c29e817bd460668b0a5f84088bf79e72f67'
PARENT_SHA = '605f5a1540fec9680143b5112a6dae2b57d52ccd03cba58167bcd10de1046d66'
PARENT_REVIEWS_SHA = '8bb5af182bf1670575d6a665aeb15def4fd167067abb7f76102933de1a5f16f0'
SUITE_SHA = 'd85973f2aa29dc5f82b3710f23b46f7dad8e67785cbf4b04d8edfc81056f91be'
SOURCE_SHA = '7a9f33eb603ac7313086069a566372f0a848a69da1e1bf2aa38952dde12870e3'
SCOPED_SHA = '241f9756a327f947f82f1ecee5f65baa5bf18de55b751c6657a6e91970c33082'
sha = lambda raw: hashlib.sha256(raw).hexdigest()
if HERE.name == 'friendly-hortative-sena-prepared':
    sys.path.insert(0, str(ROOT / 'tools'))
from native_lmf import entry
from review_inventory import digest, source_entry


def inputs():
    manifest = (ROOT / 'docs/friendly-hortative-sena-ledger-draft-proof-archive.json').read_bytes()
    assert sha(manifest) == MANIFEST_SHA, 'complete immutable original draft archive'
    originals = {}
    for name, row in json.loads(manifest)['files'].items():
        packed = (ROOT / 'docs' / row['path']).read_bytes()
        assert sha(packed) == row['archive_sha256'], 'whole packed original draft artifact'
        payload = gzip.decompress(packed)
        assert sha(payload) == row['source_sha256'] and len(payload) == row['source_bytes'], 'whole original draft artifact'
        originals[name] = payload
    raw = originals['draft-draft.json']
    assert sha(raw) == DRAFT_SHA, 'immutable honest draft metadata'
    metadata = json.loads(raw)
    values = {}
    for name, item in metadata['files'].items():
        label = 'draft-' + name + ('.gz' if 'archive_sha256' in item else '')
        payload = originals[label]
        if 'archive_sha256' in item:
            assert sha(payload) == item['archive_sha256'], 'whole original compressed draft input'
            payload = gzip.decompress(payload)
        assert sha(payload) == item['source_sha256'], 'whole original draft input'
        values[name] = payload
    return dict(metadata=metadata, parent_raw=values['parent-validity.json'],
                parent_reviews_raw=values['parent-inventory-reviews.json'],
                parent_queue_raw=values['parent-inventory-review-queue.json'],
                suite_raw=values['sena-original-validity.json'], author_raw=values['sena-reviewed-source.json'],
                scoped_raw=values['proposed-scoped-reviews.json'], proposed_raw=values['proposed-cases.json'],
                current_raw=values['proposed-validity.json'],
                current_reviews=json.loads(values['proposed-inventory-reviews.json']))


def inspect(v):
    assert sha(v['parent_raw']) == PARENT_SHA, 'complete immutable35764 parent'
    assert sha(v['parent_reviews_raw']) == PARENT_REVIEWS_SHA, 'complete immutable520 reviews'
    assert sha(v['suite_raw']) == SUITE_SHA and sha(v['author_raw']) == SOURCE_SHA, 'original preauthored suite and corrected metadata'
    assert sha(v['scoped_raw']) == SCOPED_SHA, 'exact bounded review draft'
    parent, current, suite, author = [json.loads(v[k]) for k in ['parent_raw', 'current_raw', 'suite_raw', 'author_raw']]
    assert len(parent['cases']) == 35764 and len(current['cases']) == 35789, 'whole35764 parent plus25'
    assert current['cases'][:35764] == parent['cases'], 'all old judgments and case fields in order'
    assert current['cases'][35764:] == suite['cases'], 'only exact25 original Sena cases'
    case_body = lambda raw: raw.split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert case_body(v['current_raw']).startswith(case_body(v['parent_raw'])), 'all old serialized case bytes'
    assert len({c['id'] for c in current['cases']}) == 35789, 'stable unique case IDs'
    assert {k: val for k, val in current.items() if k not in ('cases', 'sources')} == {k: val for k, val in parent.items() if k not in ('cases', 'sources')}, 'all old ledger metadata'
    expected_sources = dict(parent['sources'])
    for key, url in suite['sources'].items():
        assert key not in expected_sources or expected_sources[key] == url, 'old source declarations'
        expected_sources[key] = url
    assert current['sources'] == expected_sources, 'only exact Sena source declaration'
    assert json.loads(v['proposed_raw']) == dict(sources=suite['sources'], cases=suite['cases']), 'exact original proposal'
    counts = {kind: sum(j['verdict'] == kind for c in current['cases'] for j in c['judgments']) for kind in ['required', 'forbidden']}
    assert counts == dict(required=31488, forbidden=4318), 'all complete candidate judgments'
    assert len(suite['cases']) == 25 and sum(j['verdict'] == 'required' for c in suite['cases'] for j in c['judgments']) == 19
    assert all(len(c['judgments']) == 1 and not c['judgments'][0].get('required_rules') for c in suite['cases']), 'preserve original rule-independent targets'
    assert not author['candidate_runtime_observed'] and author['suite_sha256'] == SUITE_SHA
    assert author['metadata_label_correction']['case_and_judgment_bytes_unchanged'], 'original metadata correction preserves targets'
    owner = author['owners']['krdict:78469']
    assert entry(author['original_lmf'][owner['id']]) == owner, 'all original Native fields'
    assert len(owner['senses'][0]['examples']) == len(author['items']) == 5
    for item, case in zip(author['items'], suite['cases'][:5], strict=True):
        assert item['id'] == case['id'] and item['surface'] == case['surface']
        assert item['typed_target'] == case['judgments'][0]
        assert item['complete_original_group'] == owner['senses'][0]['examples'][item['example_group'] - 1]
        assert item['contextual_verdict'] == 'unjudged' and item['independent_korean_review'] == 'pending'
    old_reviews = json.loads(v['parent_reviews_raw'])
    reviews = v['current_reviews']
    scoped, = json.loads(v['scoped_raw'])['entries']
    assert len(old_reviews['entries']) == 520 and len(reviews['entries']) == 521, 'all520 reviews plus one'
    assert reviews['entries'][:520] == old_reviews['entries'], 'all old review fields and order'
    assert reviews['entries'][520:] == [scoped], 'only exact bounded Sena review'
    assert {k: val for k, val in reviews.items() if k != 'entries'} == {k: val for k, val in old_reviews.items() if k != 'entries'}, 'all old review metadata'
    assert scoped['id'] == owner['id'] and scoped['checklist'] == ['COV-017dc'] and scoped['status'] == 'scoped'
    assert scoped['source_sha256'] == digest(source_entry(owner)) and scoped['remaining']
    assert scoped['judgments'] == [dict(case=c['id'], judgment=j['id']) for c in suite['cases'][:5] for j in c['judgments']], 'five original source groups only'
    queue = json.loads(v['parent_queue_raw'])
    assert len(queue['entries']) == 715
    queued = next(row for row in queue['entries'] if row['source']['id'] == owner['id'])
    assert queued['source'] == source_entry(owner) and queued['source_sha256'] == scoped['source_sha256']
    assert queued['review']['status'] == 'unreviewed'
    draft = v['metadata']
    assert draft['state'] == 'prepared-not-promoted' and not draft['shared_ledger_changed']
    assert draft['original_authoring_precedes_runtime'] and draft['review_draft_authored_after_runtime']
    assert not draft['original_unjudged_corpus_hypothesis_promoted'] and not draft['full_coverage_complete']
    assert len(draft['prerequisites']) == 4 and draft['reference_queue_may_receive_later_evidence_updates']
    return dict(parent_cases=35764, proposed_cases=35789, added_cases=25, required=31488, forbidden=4318,
                parent_reviews=520, proposed_reviews=521, source_groups=5,
                actual_shared_promotion=False, corpus_hypothesis_promoted=False, full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
