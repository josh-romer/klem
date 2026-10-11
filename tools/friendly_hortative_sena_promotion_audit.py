"""Verify the full promoted Sena ledger and tested compiled inputs before projection.

Captured proof checks do not read host executables, rerun runtime captures,
assign contextual gold, or imply a successful full Nix/main gate.
"""
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'friendly-hortative-sena-promotion' if HERE.name == 'friendly-hortative-sena-promotion-prepared' else HERE.parent
if HERE.name == 'friendly-hortative-sena-promotion-prepared':
    sys.path.insert(0, str(ROOT / 'tools'))
import friendly_hortative_sena_ledger_audit as ledger

sha = lambda raw: hashlib.sha256(raw).hexdigest()
CAPTURE_ROOT = '/home/josh/projects/klem/.direnv/friendly-hortative-sena-promotion'
CAPTURE_HEAD = '22eaf28f79158398fc1c692f27348e4715efcde1'
LEDGER_MANIFEST_SHA = '1f58551935c10e0b2453365914b6e18e9cc04f77450924e3e63e571903a4caa4'
PARENT_MANIFEST_SHA = '487937cb12d6b9146e22ecfaf4cfb89de8e7c945a50f7b86ff98e9b9eef6d1ff'
MANIFEST_SHA = 'eab1ee93696d5c996513228c82100b4be62c1c5bf816249280712d3a1100b45b'
NAMES = ('sena-promotion-full-rust.json', 'sena-promotion-full-rust.log',
         'run_sena_promotion_full_rust.py', 'sena-promotion-selected-source-retry1.json',
         'sena-promotion-selected-source-retry1.log', 'verify_sena_promotion_compiled_source_retry1.py')


def archive(name, expected, names):
    raw = (ROOT / 'docs' / name).read_bytes()
    assert expected is not None and sha(raw) == expected, 'immutable complete promotion artifact manifest'
    catalog = json.loads(raw)['files']; result = {}
    for name in names:
        row = catalog[name]; packed = (ROOT / 'docs' / row['path']).read_bytes()
        assert sha(packed) == row['archive_sha256'], 'whole packed promotion artifact'
        payload = gzip.decompress(packed)
        assert sha(payload) == row['source_sha256'] and len(payload) == row.get('bytes', len(payload)), 'whole original promotion artifact'
        result[name] = payload
    return result


def inputs(prepared=None):
    files = ({name: (Path(prepared) / name).read_bytes() for name in NAMES} if prepared is not None
             else archive('friendly-hortative-sena-promotion-rust-proof-archive.json', MANIFEST_SHA, NAMES))
    authored = archive('friendly-hortative-sena-promoted-ledger-proof-archive.json', LEDGER_MANIFEST_SHA, (
        'original/tests/fixtures/validity.json', 'original/tests/validity.rs',
        'sena-promotion-ledger-finalization.json', 'sena-promotion-ledger-finalization.log',
        'finalize_sena_promotion_ledgers.py', 'sena-promotion-ledger-controls-retry1.json',
        'sena-promotion-ledger-controls-retry1.log', 'sena-promotion-formatting-adaptation.json'))
    parent = archive('friendly-hortative-sena-gena-parent-validation-proof-archive.json', PARENT_MANIFEST_SHA,
                     ('friendly-hortative-sena-gena-parent-full-rust.json',))
    rust = json.loads(files['sena-promotion-full-rust.json'])
    selected = json.loads(files['sena-promotion-selected-source-retry1.json'])
    profiles = {attr: {name: sha((ROOT / ('web/' if attr == 'web-assets' else '') / name).read_bytes())
                       for name in row['files']} for attr, row in selected['profiles'].items()}
    return dict(files=files, rust=rust, selected=selected, authored=authored, parent=parent,
                ledger=ledger.inputs(), current_profiles=profiles,
                current_production={name: sha((ROOT / name).read_bytes()) for name in rust['production_inputs']},
                actual_test_raw=(ROOT / 'tests/validity.rs').read_bytes())


def inspect(v):
    current = ledger.inspect(v['ledger'])
    assert current['actual_shared_promotion'] and (current['current_cases'], current['current_reviews']) == (35789, 521), 'actual complete promoted Sena ledger'
    files, rust, selected, authored = v['files'], v['rust'], v['selected'], v['authored']
    assert rust == json.loads(files['sena-promotion-full-rust.json']) and selected == json.loads(files['sena-promotion-selected-source-retry1.json']), 'whole original promotion receipts'
    for r in (rust, selected):
        assert r['state'] == 'passed', 'actual complete promotion proof must pass'
        assert all(r[k] for k in ('head_unchanged','index_unchanged','protected_binaries_unchanged')), 'all actual promotion proof inputs frozen'
        assert r['head'] == CAPTURE_HEAD, 'exact tested promotion checkpoint'
    assert rust['inputs_unchanged'] and selected['source_unchanged'], 'complete actual Rust and Nix-selected Source frozen'
    assert rust['frozen_inputs'] == selected['source_inputs'] and rust['index_sha256'] == selected['index_sha256'], 'same entire tested and selected promotion Source'
    for r, program, log in ((rust, 'run_sena_promotion_full_rust.py', 'sena-promotion-full-rust.log'),
                             (selected, 'verify_sena_promotion_compiled_source_retry1.py', 'sena-promotion-selected-source-retry1.log')):
        assert r['producer'] == dict(text=files[program].decode(), sha256=sha(files[program])), 'whole actual promotion producer'
        assert r['log_sha256'] == sha(files[log]), 'whole actual promotion log'
    assert rust['isolated_new_parent_target'] is True, 'independent owned promotion Cargo target'
    assert rust['rust_totals'] == dict(passed=1213, failed=0, ignored=1) and rust['rust_batches'] == 263, 'all1213 promotion Rust tests and original ignored case'
    targets, rows = rust['all_targets'], rust['results']
    assert len(targets) == 262 and len(rows) == 267 and all(row['exit_code'] == 0 for row in rows), 'every262 promotion Cargo target and all trailing checks'
    assert [row['target'] for row in rows if row['target'] is not None] == targets, 'every promotion Cargo target in original order'
    metadata = rust['cargo_metadata']
    assert sha(json.dumps(metadata, ensure_ascii=False, separators=(',', ':')).encode() + b'\n') == rust['cargo_metadata_sha256'], 'whole promotion Cargo metadata'
    package, = [p for p in metadata['packages'] if p['manifest_path'] == CAPTURE_ROOT + '/Cargo.toml']
    assert package['targets'] == targets, 'complete actual promotion target inventory'
    assert rows[0]['command'] == ['cargo','fmt','--all','--','--check']
    assert [row['command'] for row in rows[-4:]] == [
        ['cargo','test','--locked','--offline','--features','web','--doc'],
        ['cargo','clippy','--locked','--offline','--all-targets','--features','web','--','-D','warnings'],
        ['python3','tools/review_inventory.py','--verify'], ['git','diff','--check']], 'all original promotion final checks'
    log = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', files['sena-promotion-full-rust.log'])
    batches = re.findall(rb'^test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', log, flags=re.M)
    assert len(batches) == 263 and all(row[0] == b'ok' for row in batches) and [sum(int(row[i]) for row in batches) for i in (1,2,3)] == [1213,0,1], 'whole actual promotion test log totals'
    assert b'Doc-tests klem' in log and b'test src/lib.rs - (line 3) ... ok' in log, 'original promotion doctest executed'
    parent = json.loads(v['parent']['friendly-hortative-sena-gena-parent-full-rust.json'])
    assert rust['original_passed_rust_receipt_sha256'] == sha(v['parent']['friendly-hortative-sena-gena-parent-full-rust.json']), 'immutable original1212 parent prerequisite'
    assert rust['production_inputs'] == selected['production_inputs'] == parent['production_inputs'] == v['current_production'] and len(v['current_production']) == 44, 'all44 unchanged promotion production bytes'
    assert rust['protected_binaries'] == selected['protected_binaries'] == parent['protected_binaries'], 'all six original protected executable fingerprints'
    assert selected['source_evaluations'] == len(selected['results']) == 4 and all(row['exit_code'] == 0 for row in selected['results']), 'four actual Git-selected promotion source evaluations'
    assert selected['executable_replays'] == selected['full_build_replays'] == 0, 'honest selected-source-only scope'
    fin = json.loads(authored['sena-promotion-ledger-finalization.json'])
    assert fin['state'] == 'passed' and fin['controls'] == 147 and fin['control_replays'] == 0, 'actual147 ledger controls and independent finishing checks'
    assert rust['ledger_controls_sha256'] == selected['ledger_controls_sha256'] == sha(authored['sena-promotion-ledger-finalization.json']), 'same exact147 ledger prerequisite'
    original = json.loads(authored['sena-promotion-ledger-controls-retry1.json'])
    assert original['state'] == 'failed' and len(original['results']) == 12 and all(row['exit_code'] == 0 for row in original['results'][:11]), 'original147 producer remains failed at formatting after all controls/audits passed'
    for row, count in zip(original['results'][:7], (23,24,12,32,26,18,12), strict=True):
        assert re.search(r'Ran ' + str(count) + r' tests in ', row['stdout']) and row['stdout'].rstrip().endswith('OK'), 'all147 actual original and descendant controls'
    assert original['log_sha256'] == sha(authored['sena-promotion-ledger-controls-retry1.log']) and fin['log_sha256'] == sha(authored['sena-promotion-ledger-finalization.log'])
    assert all(record[key] for record in (original, fin) for key in ('source_unchanged','head_unchanged','index_unchanged','protected_binaries_unchanged')), 'all actual147 control and finishing inputs frozen'
    assert original['results'][-1]['command'] == ['cargo','fmt','--all','--','--check'] and original['results'][-1]['exit_code'] != 0, 'original formatting failure never relabelled passed'
    assert fin['original147_receipt_sha256'] == sha(authored['sena-promotion-ledger-controls-retry1.json']), 'whole original147 prerequisite identity'
    assert fin['formatting_adaptation_sha256'] == sha(authored['sena-promotion-formatting-adaptation.json']), 'whole exact whitespace-only adaptation'
    assert fin['producer'] == dict(text=authored['finalize_sena_promotion_ledgers.py'].decode(), sha256=sha(authored['finalize_sena_promotion_ledgers.py']))
    assert all(row['exit_code'] == 0 for row in fin['results']) and len(fin['results']) == 3, 'actual finishing format715queue/diff checks'
    assert rust['promotion_profiles'] == fin['profiles'] == v['current_profiles'] == {name: row['files'] for name,row in selected['profiles'].items()}, 'every actual selected tested promotion profile byte'
    assert set(v['current_profiles']) == {'klem','corpus-adapter','web-assets'}
    for name, profile in v['current_profiles'].items():
        assert len(profile) == (18 if name == 'web-assets' else 1158), 'whole1158/1158/18 promotion profile membership'
        prefix = 'web/' if name == 'web-assets' else ''
        assert all(rust['frozen_inputs'][prefix + path] == digest for path,digest in profile.items()), 'every current compiled byte belongs to passed promotion Rust'
        changes = {path for path,digest in profile.items() if parent['frozen_inputs'][prefix + path] != digest}
        assert changes == (set() if name == 'web-assets' else {'tests/fixtures/validity.json','tests/validity.rs'}), 'only two exact promoted compiled test inputs'
    assert v['ledger']['original']['parent_raw'] == authored['original/tests/fixtures/validity.json'], 'whole original35764 parent before promotion'
    assert sha(authored['original/tests/fixtures/validity.json']) == '605f5a1540fec9680143b5112a6dae2b57d52ccd03cba58167bcd10de1046d66'
    assert sha(authored['original/tests/validity.rs']) == '4e673e033432b0c1053af7699719f34d206bcb4e97ca936516c7ee52f55990af'
    assert sha(v['actual_test_raw']) == v['current_profiles']['klem']['tests/validity.rs'], 'complete actual new validity regression bytes'
    return dict(current_cases=35789, current_reviews=521, original_parent_cases=35764,
                original_parent_reviews=520, full_rust_tests=1213, compiled_inputs=1158,
                production_inputs=44, binary_evidence='captured-no-host-executable-reads',
                full_Nix_main_and_context_review='pending', full_coverage_complete=False)


def parent_profiles(v, actual):
    inspect(v)
    assert actual == v['current_profiles'], 'every current profile byte belongs to actual passed parent Rust source'
    parent = json.loads(v['parent']['friendly-hortative-sena-gena-parent-full-rust.json'])
    return {name: {path: parent['frozen_inputs'][('web/' if name == 'web-assets' else '') + path]
                   for path in profile} for name,profile in actual.items()}


if __name__ == '__main__':
    print(inspect(inputs()))
