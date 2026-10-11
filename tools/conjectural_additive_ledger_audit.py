"""Verify the exact existing ledger prefix and every independent new judgment."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def inputs():
    return {'before_raw': gzip.decompress((ROOT / 'docs/conjectural-additive-integration-parent-validity.json.gz').read_bytes()),
            'after_raw': gzip.decompress((ROOT / 'docs/conjectural-additive-novel-parent-validity.json.gz').read_bytes()),
            'current_raw': gzip.decompress((ROOT / 'docs/conjectural-additive-validated-private-validity.json.gz').read_bytes()),
            'novel_raw': (ROOT / 'tests/fixtures/conjectural-additive-novel-validity.json').read_bytes(),
            'novel_append': json.loads(gzip.decompress((ROOT / 'docs/conjectural-additive-novel-ledger-append.json.gz').read_bytes())),
            'source_raw': (ROOT / 'tests/fixtures/conjectural-additive-validity.json').read_bytes(),
            'copula_raw': (ROOT / 'tests/fixtures/conjectural-additive-copula-validity.json').read_bytes(),
            'append': json.loads(gzip.decompress((ROOT / 'docs/conjectural-additive-integration-ledger-append.json.gz').read_bytes()))}

def inspect(v):
    assert sha(v['before_raw']) == '51c4a125bdb20ea4776b3289d5608d1709c2cfc553c3a46f0e40c9e0f2830da7', 'exact independently retained parent ledger'
    assert sha(v['source_raw']) == '669e3f979cbb6156dfa2444e67272b4cdd24151a276976b6c5cbe9b137acbb06', 'original35authoredjudgments unchanged'
    assert sha(v['copula_raw']) == '5c585034c57c61fb665a68a6acf949477cca054d1fb219c587f2f67ac7cada15', 'originalsixcopulajudgments unchanged'
    before, after = json.loads(v['before_raw']), json.loads(v['after_raw'])
    original = json.loads(v['source_raw'])['cases'] + json.loads(v['copula_raw'])['cases']
    assert len(before['cases']) == 35587 and len(after['cases']) == 35628, 'exact complete ledger sizes'
    assert after['cases'][:35587] == before['cases'], 'every old case/role/morpheme/rule/verdict/reason retained'
    assert after['cases'][35587:] == original and len(original) == 41, 'only41exactindependentlyauthoredcases appended'
    assert len({case['id'] for case in after['cases']}) == 35628, 'every stable case identity unique'
    assert all(key in after['sources'] and after['sources'][key] == value for key, value in before['sources'].items()), 'every old source citation retained'
    old_prefix = v['before_raw'].split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert v['after_raw'].split(b'"cases": [', 1)[1].startswith(old_prefix), 'every original serialized case byte retained'
    counts = {kind: sum(j['verdict'] == kind for case in after['cases'] for j in case['judgments']) for kind in ['required', 'forbidden']}
    assert counts == {'required': 31369, 'forbidden': 4275}, 'exact new required/forbidden totals'
    append = v['append']
    assert append['before_ledger_sha256'] == sha(v['before_raw']) and append['after_ledger_sha256'] == sha(v['after_raw']), 'actual append source hashes'
    assert append['independent_appended_case_ids'] == [case['id'] for case in original], 'exact independent append IDs'
    assert sha(v['novel_raw']) == 'b0b3a87c59895f1a056ccb3525ae9a3e4b9e0536edb6729af8c8574f67341732', 'independent16novelrequirements unchanged'
    current, novel = json.loads(v['current_raw']), json.loads(v['novel_raw'])
    assert len(current['cases']) == 35643, 'complete current ledger size'
    assert current['cases'][:35628] == after['cases'], 'every35628previouscase retained'
    assert current['cases'][35628:] == novel['cases'], 'only15independentnovelcases appended'
    assert current['sources'] == after['sources'], 'all existing source citations retained'
    previous_prefix = v['after_raw'].split(b'"cases": [', 1)[1].rsplit(b'\n  ]\n}', 1)[0]
    assert v['current_raw'].split(b'"cases": [', 1)[1].startswith(previous_prefix), 'every35628serializedcase byte retained'
    assert len({case['id'] for case in current['cases']}) == 35643, 'every current stable case identity unique'
    current_counts = {kind: sum(j['verdict'] == kind for case in current['cases'] for j in case['judgments']) for kind in ['required', 'forbidden']}
    assert current_counts == {'required': 31385, 'forbidden': 4275}, 'exact current required/forbidden totals'
    novel_append = v['novel_append']
    assert novel_append['before_ledger_sha256'] == sha(v['after_raw']) and novel_append['after_ledger_sha256'] == sha(v['current_raw']), 'actual novel append source hashes'
    assert novel_append['independent_fixture_sha256'] == sha(v['novel_raw']) and novel_append['independent_appended_case_ids'] == [case['id'] for case in novel['cases']], 'exact independent novel append identities'
    from expression_conjectural_ledger_audit import inputs as active_inputs, inspect as inspect_active
    active = inspect_active(active_inputs())
    return {'active_cases': active['active_cases'], 'historical_private_scope': True, 'state': 'exact-parent41source-and15novelcases-ledger-audit-passed', 'old_cases': 35587, 'new_source_cases': 41, 'new_novel_cases': 15, 'cases': 35643, **current_counts, 'unjudged_alternatives_promoted': False}

if __name__ == '__main__':
    print(inspect(inputs()))
