"""Bind only the exact tested Gena-parent update to the original Sena profiles.

Prepared independently while the full Rust run freezes the worktree. Historical
profile projection is allowed only after complete actual parent validation.
"""
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent / 'friendly-hortative-sena' if HERE.name == 'friendly-hortative-sena-prepared' else HERE.parent
if HERE.name == 'friendly-hortative-sena-prepared':
    sys.path.insert(0, str(ROOT / 'tools'))
sha = lambda b: hashlib.sha256(b).hexdigest()
CAPTURE_HEAD = '9e0753a4e753d3b9a392927cba24d64a782b138b'
PARENT_SHA = '605f5a1540fec9680143b5112a6dae2b57d52ccd03cba58167bcd10de1046d66'
PARENT_TEST_SHA = '4e673e033432b0c1053af7699719f34d206bcb4e97ca936516c7ee52f55990af'
PARENT_MANIFEST_SHA = '98723fc49b17a554e688c1ddc38042aa8cbac537f155367cc05798165c05329c'
MANIFEST_SHA = '487937cb12d6b9146e22ecfaf4cfb89de8e7c945a50f7b86ff98e9b9eef6d1ff'


def inputs(prepared=None):
    files = {}
    manifest = ROOT / 'docs/friendly-hortative-sena-gena-parent-validation-proof-archive.json'
    archived = prepared is None and manifest.exists()
    if archived:
        raw = manifest.read_bytes()
        assert MANIFEST_SHA is not None and sha(raw) == MANIFEST_SHA, 'immutable tested Gena-parent proof'
        for name, row in json.loads(raw)['files'].items():
            packed = (ROOT / 'docs' / row['path']).read_bytes()
            assert sha(packed) == row['archive_sha256'], 'whole packed parent proof artifact'
            payload = gzip.decompress(packed)
            assert sha(payload) == row['source_sha256'] and len(payload) == row['bytes'], 'whole original parent proof artifact'
            files[name] = payload
    else:
        prepared = Path(prepared) if prepared is not None else HERE
    def raw(name):
        return files[name] if archived else (prepared / name).read_bytes()
    rraw = raw('friendly-hortative-sena-gena-parent-full-rust.json')
    values = dict(rust=json.loads(rraw), rust_raw=rraw,
                rust_log=raw('friendly-hortative-sena-gena-parent-full-rust.log'),
                rust_producer=raw('run_sena_gena_parent_full_rust.py'),
                parent_raw=(ROOT / 'tests/fixtures/validity.json').read_bytes(),
                parent_test_raw=(ROOT / 'tests/validity.rs').read_bytes(),
                parent_manifest_raw=(ROOT / 'docs/friendly-hortative-sena-gena-parent-preservation-proof-archive.json').read_bytes())
    if sha(values['parent_raw']) != PARENT_SHA or sha(values['parent_test_raw']) != PARENT_TEST_SHA:
        import friendly_hortative_sena_promotion_audit as promotion
        child = promotion.inputs()
        promotion.inspect(child)
        assert child['ledger']['current_raw'] == values['parent_raw'], 'whole actual promoted parent ledger'
        assert child['actual_test_raw'] == values['parent_test_raw'], 'whole actual promoted validity regression'
        values.update(actual_parent_raw=values['parent_raw'], actual_parent_test_raw=values['parent_test_raw'],
                      verified_promotion=child,
                      parent_raw=child['authored']['original/tests/fixtures/validity.json'],
                      parent_test_raw=child['authored']['original/tests/validity.rs'])
    return values


def inspect(v, current_profiles, original_profiles, production):
    r = v['rust']
    assert r['state'] == 'passed', 'actual complete parent Rust validation must pass'
    assert all(r[k] for k in ['inputs_unchanged', 'head_unchanged', 'index_unchanged', 'protected_binaries_unchanged']), 'all actual parent Rust inputs frozen'
    assert r['head'] == CAPTURE_HEAD and r['isolated_new_parent_target'], 'exact independently built parent checkpoint'
    assert r['production_inputs'] == production and len(production) == 44, 'all44 unchanged tested Sena production inputs'
    assert r['producer'] == dict(text=v['rust_producer'].decode(), sha256=sha(v['rust_producer'])), 'whole actual parent Rust producer'
    assert r['log_sha256'] == sha(v['rust_log']), 'whole actual parent Rust log'
    assert r['rust_totals'] == dict(passed=1212, failed=0, ignored=1) and r['rust_batches'] == 263, 'every1212 parent Rust test and original doctest'
    rows = r['results']; targets = r['all_targets']
    assert len(targets) == 262 and len(rows) == 267 and all(row['exit_code'] == 0 for row in rows), 'every262 parent Cargo target and all trailing checks'
    assert [row['target'] for row in rows if row['target'] is not None] == targets, 'complete original parent Cargo target order'
    package, = [p for p in r['cargo_metadata']['packages'] if p['manifest_path'] == '/home/josh/projects/klem/.direnv/friendly-hortative-sena/Cargo.toml']
    assert package['targets'] == targets, 'whole actual parent Cargo metadata target inventory'
    assert sha(json.dumps(r['cargo_metadata'], ensure_ascii=False, separators=(',', ':')).encode() + b'\n') == r['cargo_metadata_sha256'], 'whole actual parent Cargo metadata bytes'
    assert rows[0]['command'] == ['cargo','fmt','--all','--','--check'], 'actual parent formatting check'
    assert [row['command'] for row in rows[-4:]] == [
        ['cargo','test','--locked','--offline','--features','web','--doc'],
        ['cargo','clippy','--locked','--offline','--all-targets','--features','web','--','-D','warnings'],
        ['python3','tools/review_inventory.py','--verify'],['git','diff','--check']], 'actual parent doctest Clippy inventory and diff checks'
    plain_log = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', v['rust_log'])
    batches = re.findall(rb'^test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', plain_log, flags=re.M)
    assert len(batches) == 263 and all(row[0] == b'ok' for row in batches) and [sum(int(row[i]) for row in batches) for i in [1,2,3]] == [1212,0,1], 'all original parent Rust log totals'
    assert b'Doc-tests klem' in plain_log and b'test src/lib.rs - (line 3) ... ok' in plain_log, 'actual original parent doctest preserved'
    assert sha(v['parent_raw']) == PARENT_SHA and sha(v['parent_test_raw']) == PARENT_TEST_SHA, 'exact tested35764 parent ledger and test bytes'
    assert sha(v['parent_manifest_raw']) == PARENT_MANIFEST_SHA, 'whole original parent merge preservation proof'
    preservation = json.loads(v['parent_manifest_raw'])
    assert preservation['gena_main_parent'] == '65b8eff7cdb6b29844d7d08f46d4d3993ea22b56' and preservation['all44_Sena_production_inputs_unchanged'] and preservation['original25_Sena_cases_not_promoted'], 'exact declared Gena parent and private Sena scope'
    import friendly_command_gena_ledger_audit as gena
    parent = gena.inputs()
    assert parent['current_raw'] == v['parent_raw'], 'entire current parent ledger is independently audited'
    checked = gena.inspect(parent)
    assert checked['current_cases'] == 35764 and checked['current_reviews'] == 520, 'complete actual35764-case520-review parent'
    verified_current = None
    if sha((ROOT / 'tests/fixtures/validity.json').read_bytes()) != PARENT_SHA or sha((ROOT / 'tests/validity.rs').read_bytes()) != PARENT_TEST_SHA:
        import friendly_hortative_sena_promotion_audit as promotion
        child = v['verified_promotion']
        verified_current = promotion.inspect(child)
        assert v['actual_parent_raw'] == child['ledger']['current_raw'] == (ROOT / 'tests/fixtures/validity.json').read_bytes(), 'mandatory complete actual promoted ledger'
        assert v['actual_parent_test_raw'] == child['actual_test_raw'] == (ROOT / 'tests/validity.rs').read_bytes(), 'mandatory complete actual promoted test bytes'
        assert set(current_profiles) == set(original_profiles) == {'klem','corpus-adapter','web-assets'}, 'all three whole parent profiles'
        for name, original in original_profiles.items():
            current = current_profiles[name]
            assert set(current) == set(original) and len(current) == (18 if name == 'web-assets' else 1158), 'every original1158/1158/18 profile member retained'
            changed = {path for path in current if current[path] != original[path]}
            assert changed == (set() if name == 'web-assets' else {'tests/fixtures/validity.json','tests/validity.rs'}), 'only exact two tested Gena-parent input changes'
        current_profiles = promotion.parent_profiles(child, current_profiles)
    assert set(current_profiles) == set(original_profiles) == {'klem','corpus-adapter','web-assets'}, 'all three whole parent profiles'
    for name, original in original_profiles.items():
        current = current_profiles[name]
        assert set(current) == set(original) and len(current) == (18 if name == 'web-assets' else 1158), 'every original1158/1158/18 profile member retained'
        changed = {path for path in current if current[path] != original[path]}
        assert changed == (set() if name == 'web-assets' else {'tests/fixtures/validity.json','tests/validity.rs'}), 'only exact two tested Gena-parent input changes'
        prefix = 'web/' if name == 'web-assets' else ''
        assert all(r['frozen_inputs'][prefix + path] == digest for path, digest in current.items()), 'every current profile byte belongs to actual passed parent Rust source'
    for name in ['klem','corpus-adapter']:
        assert current_profiles[name]['tests/fixtures/validity.json'] == PARENT_SHA and current_profiles[name]['tests/validity.rs'] == PARENT_TEST_SHA, 'both Rust owners have exact tested parent changes'
    result = dict(parent_cases=35764, parent_reviews=520, unchanged_production_inputs=44,
                exact_changed_test_inputs=2, full_rust_tests=1212, original25_Sena_cases_promoted=False,
                full_coverage_complete=False)
    if verified_current is not None:
        result.update(verified_current_shared_cases=verified_current['current_cases'],
                      verified_current_shared_reviews=verified_current['current_reviews'],
                      verified_current_full_rust_tests=verified_current['full_rust_tests'],
                      actual_current25_Sena_cases_promoted=True,
                      legacy_checkpoint_fields='Original35764/520/1212-test unpromoted parent; current complete promotion is verified_current_*')
    return result


def historical_profiles(v, current_profiles, original_profiles, production):
    inspect(v, current_profiles, original_profiles, production)
    return {name: dict(files) for name, files in original_profiles.items()}
