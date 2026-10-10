"""Bind the eight original expression judgments to the exact unchanged parent ledger."""
import hashlib
import json
from pathlib import Path

import formal_volitional_expression_audit as source
from native_lmf import entry

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def inspect(packet, suite, ledger, native, entries, projection):
    summary = source.inspect(packet, suite)
    assert projection['state'] == 'exact-expression-ledger-prefix-passed', 'independent exact parent projection'
    assert (projection['parent_cases'], projection['appended_cases'], projection['complete_cases']) == (35587, 8, 35595), 'complete original ledger scopes'
    original_suite = ROOT / 'tests/fixtures/formal-volitional-expression-validity.json'
    assert sha(original_suite.read_bytes()) == projection['suite_sha256'], 'unchanged independent expression fixture'
    assert len(ledger['cases']) == 35595 and ledger['cases'][35587:] == suite['cases'], 'exact eight appended judgments'
    assert len({case['id'] for case in ledger['cases']}) == 35595, 'stable complete case identities'
    assert all(ledger['sources'][key] == value for key, value in suite['sources'].items()), 'separate expression source links'
    previous = {**ledger, 'cases': ledger['cases'][:35587],
                'sources': {key: value for key, value in ledger['sources'].items() if key not in suite['sources']}}
    original = (json.dumps(previous, ensure_ascii=False, indent=2) + '\n').encode()
    assert sha(original) == projection['parent_ledger_sha256'], 'exact complete parent ledger bytes'
    counts = {verdict: sum(j['verdict'] == verdict for case in ledger['cases'] for j in case['judgments'])
              for verdict in ['required', 'forbidden']}
    assert counts == projection['counts'] == {'required': 31345, 'forbidden': 4266}, 'complete independent ledger counts'
    owners = native['LexicalResource']['Lexicon']['LexicalEntry']
    assert owners == list(packet['original_native_entries'].values()), 'all exact original Native fixture fields'
    assert {value['id']: value for value in map(entry, owners)} == entries == packet['complete_imported_entries'], 'exact complete Rust importer expectations'
    from literary_question_geona_runtime import read, verify_ledger
    verify_ledger(ledger, read(ROOT / 'docs/literary-question-geona-proposed-ledger.json.gz'))
    return {**summary, 'preserved_parent_cases': 35587, 'appended_cases': 8, 'ledger_cases': 35595, 'counts': counts}


def inputs():
    return (*source.inputs(),
            source.read(ROOT / 'tests/fixtures/validity.json'),
            source.read(ROOT / 'tests/fixtures/formal-volitional-expression-native.json'),
            source.read(ROOT / 'tests/fixtures/formal-volitional-expression-native-entries.json'),
            source.read(ROOT / 'docs/formal-volitional-expression-ledger-projection.json.gz'))


if __name__ == '__main__':
    print(inspect(*inputs()))
