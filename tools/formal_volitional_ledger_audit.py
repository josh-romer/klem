"""Bind the raw ledger projection to unchanged independently authored judgments."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(name):
    return json.loads((ROOT / 'tests/fixtures' / name).read_bytes())


def inspect(full, policy, raw, novel, ledger):
    complete_ledger = ledger
    complete_ledger_cases = len(ledger['cases'])
    # The historical assertions below concern exactly the original raw53 and
    # novel4 append. The complete ledger is independently checked below against
    # every byte-pinned reviewed suite, including later additions in order.
    # A prefix projection alone never authorizes a new tail or source identity.
    ledger = {**ledger, 'cases': ledger['cases'][:35587]}
    assert hashlib.sha256((ROOT / 'tests/fixtures/formal-volitional-validity.json').read_bytes()).hexdigest() == '4baa4c4bc9da65a9a9c493b7aadd537afd82ff3464daf586dc3e59823d9cd181', 'unchanged original59 fixture'
    assert hashlib.sha256((ROOT / 'tests/fixtures/formal-volitional-novel-validity.json').read_bytes()).hexdigest() == 'db0853ac54c5ca0ab8995511e6d40f4c20b1a9b1020b9358a31d9ee19efaea41', 'unchanged manual novel4 fixture'
    original = read('formal-volitional-validity.json')
    assert full == original and len(full['cases']) == 59, 'unchanged original judgments'
    conditional = {
        'formal-volitional-question-forbidden-negative-copula',
        'formal-volitional-question-forbidden-adjective',
        'formal-volitional-question-forbidden-honorific-adjective',
        'formal-volitional-statement-forbidden-negative-copula',
        'formal-volitional-statement-forbidden-adjective',
        'formal-volitional-statement-forbidden-honorific-adjective',
    }
    assert set(policy['dictionary_required_case_ids']) == conditional and len(policy['dictionary_required_case_ids']) == 6, 'original six dictionary-POS cases'
    assert (policy['raw_cases'], policy['dictionary_cases']) == (53, 59), 'complete raw and dictionary scopes'
    expected = [c for c in full['cases'] if c['id'] not in conditional]
    assert raw['cases'] == expected and len(expected) == 53, 'exact raw53 original case projection'
    assert {k:v for k,v in raw.items() if k != 'review_status'} == {**{k:v for k,v in full.items() if k not in ['review_status','cases']}, 'cases':expected}, 'original raw metadata and source identities'
    assert novel == read('formal-volitional-novel-validity.json') and len(novel['cases']) == 4, 'unchanged manual novel judgments'
    assert len(ledger['cases']) == 35587 and ledger['cases'][35530:] == expected + novel['cases'], 'exact appended case identity and order'
    assert not conditional & {c['id'] for c in ledger['cases']}, 'dictionary-only judgments are not raw gold'
    assert all(ledger['sources'][key] == value for key,value in {**full['sources'], **novel['sources']}.items()), 'original appended source links'
    from literary_question_geona_runtime import read as archived, verify_ledger
    verify_ledger(complete_ledger, archived(ROOT / 'docs/literary-question-geona-proposed-ledger.json.gz'))
    counts = {v:sum(j['verdict'] == v for c in ledger['cases'] for j in c['judgments']) for v in ['required','forbidden']}
    assert counts == {'required':31337,'forbidden':4266}, 'complete private ledger counts'
    return {'raw_cases':53,'dictionary_cases':59,'novel_cases':4,'ledger_cases':35587,'complete_ledger_cases':complete_ledger_cases,'counts':counts,'contextual_and_independent_review':'pending'}


def inputs():
    return [read(name) for name in ['formal-volitional-validity.json', 'formal-volitional-evaluation-policy.json', 'formal-volitional-raw-validity.json', 'formal-volitional-novel-validity.json', 'validity.json']]


if __name__ == '__main__':
    print(inspect(*inputs()))
