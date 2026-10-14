"""Bind the captured -게나 revision while retaining the failed queue receipt."""
import gzip
import hashlib
import json
from pathlib import Path

import gentle_command_long_revision as parent_revision

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SHA = '675f69705ab5e175fc4dc72fecd74d5c5cb41538498d526688b88387a1e0e009'
CAPTURE_ROOT = '/home/josh/projects/klem/.direnv/friendly-command-gena'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def archive(selected=None):
    raw = (ROOT / 'docs/friendly-command-gena-initial-runtime-proof-archive.json').read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'immutable Gena runtime manifest'
    values = {}; hashes = {}
    for name, item in json.loads(raw)['files'].items():
        if selected is not None and name not in selected:
            continue
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'immutable packed Gena artifact'
        # Every artifact has exactly one archive wrapper, including .gz inputs.
        original = gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'immutable original Gena artifact'
        hashes[name] = item['source_sha256']
        values[name] = (json.loads(gzip.decompress(original) if name.endswith('.gz') else original)
                        if name.endswith(('.json', '.json.gz')) else original)
    assert selected is None or set(values) == set(selected), 'all requested Gena revision artifacts'
    return values, hashes


def inputs(proof=None, hashes=None):
    if proof is None:
        proof, hashes = archive({'friendly-command-gena-complete-runtime-binding.json',
                                 'friendly-command-gena-initial-validation-retry2.json',
                                 'friendly-command-gena-queue-recovery.json',
                                 'friendly-command-gena-initial-validation-retry2.log',
                                 'friendly-command-gena-queue-recovery.log',
                                 'friendly-command-gena-adapter-build.log'})
    binding = proof['friendly-command-gena-complete-runtime-binding.json']
    return dict(binding=binding, full=proof['friendly-command-gena-initial-validation-retry2.json'],
                recovery=proof['friendly-command-gena-queue-recovery.json'],
                parent=parent_revision.inputs(), hashes=hashes,
                current={p: sha((ROOT / p).read_bytes()) for p in binding['production_inputs']})


def terminal(report, state, producer=None):
    assert report['state'] == state and report['inputs_unchanged'], 'actual terminal Gena scope'
    for name in ['external_inputs_unchanged', 'head_unchanged', 'index_unchanged']:
        assert report.get(name, True), 'unchanged captured Gena inputs/head/index'
    captured = report['producer']
    assert sha(captured['text'].encode()) == captured['sha256'], 'actual Gena producer bytes'
    if producer is not None:
        assert captured['text'].encode() == producer, 'original Gena producer retained'


def inspect(v, check_current=True):
    binding, full, recovery = v['binding'], v['full'], v['recovery']
    parent = parent_revision.inspect(v['parent'], check_current=False)
    terminal(binding, 'passed'); terminal(full, 'failed'); terminal(recovery, 'passed')
    assert binding['exit_code'] == 0 and binding['protected_prior_binaries_unchanged'], 'actual adapter build passed'
    assert full['rust_totals'] == {'passed': 1200, 'failed': 0, 'ignored': 1} and full['rust_batches'] == 255 and full['controls'] == 22, 'complete1200 Rust/22 controls'
    results = full['results']
    assert len(results) == 6 and [r['exit_code'] for r in results] == [0, 0, 0, 0, 0, 1], 'original final queue-only failure retained'
    assert results[-1]['command'] == ['python3', 'tools/review_inventory.py', '--verify'], 'failed original queue command'
    assert len(recovery['results']) == 2 and all(r['exit_code'] == 0 for r in recovery['results']), 'actual queue recovery commands'
    assert recovery['original_full_rust_state'] == 'failed-only-stale-queue-final-stage' and recovery['original_full_rust_receipt_sha256'] == v['hashes']['friendly-command-gena-initial-validation-retry2.json'], 'unchanged failed receipt binding'
    assert recovery['every_prior_source_except_queue_unchanged'] and recovery['all715rows519reviews196unreviewed_and_candidate_judgments_unchanged'], 'queue-only evidence recovery'
    queue = 'docs/inventory-review-queue.json'
    assert all(recovery['frozen_inputs'][p] == digest for p, digest in full['frozen_inputs'].items() if p != queue), 'every passing Rust input retained'
    assert binding['whole_rust_receipt_sha256'] == v['hashes']['friendly-command-gena-initial-validation-retry2.json'] and binding['queue_recovery_receipt_sha256'] == v['hashes']['friendly-command-gena-queue-recovery.json'], 'actual adapter validation bindings'
    production = binding['production_inputs']
    assert set(production) == set(parent) and len(production) == 44, 'complete44 Gena production inputs'
    changes = {p: dict(before=parent[p], after=d) for p, d in production.items() if d != parent[p]}
    assert set(changes) == parent_revision.CHANGED and binding['individual_production_changes'] == changes, 'exact five Gena production changes'
    assert all(binding['frozen_inputs'][CAPTURE_ROOT + '/' + p] == digest for p, digest in production.items()), 'every compiled Gena production byte'
    assert all(full['frozen_inputs'][p] == recovery['frozen_inputs'][p] == digest for p, digest in production.items()), 'passing Rust source equals compiled Gena source'
    assert set(binding['binaries']) == {'klem', 'klem-web', 'adapter'}, 'all three Gena executables'
    suffixes = {'klem': '/debug/klem', 'klem-web': '/debug/klem-web', 'adapter': '/debug/examples/evaluate'}
    for name, binary in binding['binaries'].items():
        assert binary['path'] == '/home/josh/projects/klem/.direnv/friendly-command-gena-target' + suffixes[name] and len(binary['sha256']) == 64, 'actual Gena executable identity'
        if name != 'adapter':
            assert binding['protected_prior_cli_server'][binary['path']] == binary['sha256'], 'original CLI/server protected during adapter build'
    for report, log in [(full, 'friendly-command-gena-initial-validation-retry2.log'),
                        (recovery, 'friendly-command-gena-queue-recovery.log'),
                        (binding, 'friendly-command-gena-adapter-build.log')]:
        assert report['log_sha256'] == v['hashes'][log], 'complete actual Gena validation logs'
    if check_current:
        current_matches = v['current'] == production
        if not current_matches:
            import friendly_hortative_sena_revision as sena
            current_matches = sena.accepts_production(v['current'])
        assert current_matches, 'current complete Gena production closure'
    return production


def accepts_production(current):
    """Accept the complete named Gena revision or its strictly proven Sena child."""
    expected = inspect(inputs())
    relative = {}
    for name, digest in current.items():
        path = Path(name)
        if path.is_absolute():
            try:
                path = path.relative_to('/tmp/klem-gentle-command')
            except ValueError:
                return False
        name = str(path)
        if name in relative:
            return False
        relative[name] = digest
    if relative == expected:
        return True
    import friendly_hortative_sena_revision as sena
    return sena.accepts_production(relative)


def frontend_inputs():
    proof, _ = archive({'friendly-command-gena-frontend-build.json',
                        'friendly-command-gena-browser-runtime-retry1.json'})
    build = proof['friendly-command-gena-frontend-build.json']
    browser = proof['friendly-command-gena-browser-runtime-retry1.json']
    terminal(build, 'passed'); terminal(browser, 'passed')
    assert build['exit_code'] == browser['exit_code'] == 0 and browser['server_stopped'] and browser['source_unchanged'], 'actual Gena frontend/browser capture'
    selected = {p.removeprefix('web/'):d for p,d in browser['source_inputs'].items()
                if p.startswith('web/') and not p.startswith('web/tests/')}
    prefix = CAPTURE_ROOT + '/web/'
    declared = {p.removeprefix(prefix):d for p,d in build['frozen_inputs'].items() if p.startswith(prefix)}
    assert len(selected) == 18 and len(declared) == 14 and all(selected[p] == d for p,d in declared.items()), 'complete18 frontend/14 declared build inputs'
    return selected


def accepts_frontend(current, historical):
    v = inputs(); production = inspect(v); selected = frontend_inputs()
    parent = v['parent']
    known_labels = {parent['binding']['production_inputs']['web/src/grammar-labels.json'],
                    parent['binding']['parent_production_inputs']['/tmp/klem-gentle-command/web/src/grammar-labels.json']}
    label = 'src/grammar-labels.json'
    assert selected[label] == production['web/' + label], 'Gena frontend belongs to bound production'
    if len(historical) != 18 or set(historical) != set(selected) or historical[label] not in known_labels:
        import friendly_hortative_sena_revision as sena
        return sena.accepts_frontend(current, historical)
    if any(d != selected[p] for p,d in historical.items() if p != label):
        return False
    if current == selected:
        return True
    import friendly_hortative_sena_revision as sena
    return sena.accepts_frontend(current, historical)
