"""Bind a named production revision without rewriting historical captures."""
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
MANIFEST_SHA = 'a38f4bd748e734ca314d908bc24676e551e6cb815a923fc3075c879726a4da31'
SHORT_MANIFEST_SHA = '5500e8b18cc6a6051d5792c2397c2f429684a24d8f8f1d73cd21e11dfeeaad69'
CAPTURE_ROOT = '/home/josh/projects/klem/.direnv/gentle-command-long'
CHANGED = {'src/grammar.rs', 'src/engine.rs', 'src/dictionary/attachment.rs',
           'src/bin/klem-web/grammar_labels.rs', 'web/src/grammar-labels.json'}


def archive(name, digest, selected=None):
    raw = (ROOT / 'docs' / name).read_bytes()
    assert sha(raw) == digest, 'immutable named-revision manifest'
    manifest = json.loads(raw); values = {}; hashes = {}
    for name, item in manifest['files'].items():
        if selected is not None and name not in selected:
            continue
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'immutable named-revision archive'
        original = packed if name.endswith('.gz') else gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'immutable original revision bytes'
        hashes[name] = item['source_sha256']
        if name.endswith(('.json', '.json.gz')):
            values[name] = json.loads(gzip.decompress(original) if name.endswith('.gz') else original)
        else:
            values[name] = original
    assert selected is None or set(values) == set(selected), 'all requested revision artifacts'
    return values, hashes


def inputs():
    proof, hashes = archive('gentle-command-long-runtime-proof-archive.json', MANIFEST_SHA,
                            {'gentle-command-long-runtime-binding.json',
                             'gentle-command-long-full-rust.json',
                             'gentle-command-long-runtime-build.log',
                             'gentle-command-long-full-rust.log'})
    old, _ = archive('gentle-command-runtime-proof-archive.json', SHORT_MANIFEST_SHA,
                     {'gentle-command-current-production-closure.json'})
    binding = proof['gentle-command-long-runtime-binding.json']
    return dict(binding=binding, full=proof['gentle-command-long-full-rust.json'],
                parent=old['gentle-command-current-production-closure.json'],
                hashes=hashes,
                current={p: sha((ROOT / p).read_bytes()) for p in binding['production_inputs']})


def inspect(v, check_current=True):
    binding, full, parent = v['binding'], v['full'], v['parent']
    assert binding['state'] == full['state'] == parent['state'] == 'passed', 'terminal named production revision'
    assert binding['exit_code'] == full['exit_code'] == 0, 'successful actual revision commands'
    assert all(r['inputs_unchanged'] and r['head_unchanged'] and r['index_unchanged']
               for r in [binding, full]), 'complete revision source freeze'
    assert binding['captured_head'] == full['head'] == '6413c1bb7a01f8da18a7e38cd4fffe443be4b5bd', 'exact captured revision checkpoint'
    assert binding['index_sha256'] == full['index_sha256'], 'same original revision index'
    assert full['totals'] == {'passed': 1189, 'failed': 0, 'ignored': 1} and full['batches'] == 254, 'complete original revision Rust suite'
    assert len(full['frozen_inputs']) == len(binding['frozen_inputs']) == 6597, 'all6597original revision sources'
    # Each command freezes its own producer in addition to the same 6596
    # worktree files. Preserve that distinction instead of rewriting receipts.
    snapshots = []
    for report, name in [(binding, 'build_gentle_command_long_runtime.py'),
                         (full, 'run_gentle_command_long_full_rust.py')]:
        snapshot = dict(report['frozen_inputs'])
        producer_path = '/home/josh/projects/klem/.direnv/willingness-question-prepared/' + name
        assert snapshot.pop(producer_path) == report['producer']['sha256'], 'frozen actual revision producer'
        snapshots.append(snapshot)
    assert snapshots[0] == snapshots[1], 'same complete revision source snapshot'
    for report in [binding, full]:
        assert sha(report['producer']['text'].encode()) == report['producer']['sha256'], 'actual revision producer bytes'
    assert binding['log_sha256'] == v['hashes']['gentle-command-long-runtime-build.log'], 'actual complete revision build log'
    assert full['log_sha256'] == v['hashes']['gentle-command-long-full-rust.log'], 'actual complete revision Rust log'
    original = binding['observed_full_rust_receipt']
    assert binding['observed_full_rust_state'] == original['state'] == 'running', 'historical running receipt preserved'
    assert all(original[key] == full[key] for key in ['head', 'index_sha256', 'frozen_inputs', 'command', 'producer']), 'original in-progress receipt belongs to terminal suite'
    assert binding['command'] == ['cargo', 'build', '--locked', '--offline', '--features', 'web', '--bin', 'klem', '--bin', 'klem-web', '--example', 'evaluate'], 'actual complete revision build command'
    previous = {str(Path(p).relative_to('/tmp/klem-gentle-command')): digest
                for p, digest in parent['production_inputs'].items()}
    production = binding['production_inputs']
    assert len(production) == len(previous) == 44 and set(production) == set(previous), 'complete44-input production closure'
    assert binding['parent_production_inputs'] == parent['production_inputs'], 'every original parent production input'
    changes = {p: dict(before=previous[p], after=digest)
               for p, digest in production.items() if digest != previous[p]}
    assert set(changes) == CHANGED and binding['individual_production_changes'] == changes, 'exact five declared production changes'
    assert all(binding['frozen_inputs'][CAPTURE_ROOT + '/' + p] == digest
               for p, digest in production.items()), 'every compiled revision source/data byte'
    assert set(binding['binaries']) == {'klem', 'klem-web', 'adapter'}, 'all three actual compiled executables'
    suffixes = {'klem': '/debug/klem', 'klem-web': '/debug/klem-web', 'adapter': '/debug/examples/evaluate'}
    for name, binary in binding['binaries'].items():
        assert binary['path'] == '/home/josh/projects/klem/.direnv/gentle-command-long-target' + suffixes[name], 'actual isolated revision executable'
        assert len(binary['sha256']) == 64, 'complete captured executable digest'
    if check_current:
        current_matches = v['current'] == production
        if not current_matches:
            import friendly_command_gena_revision as gena
            current_matches = gena.accepts_production(v['current'])
        assert current_matches, 'current complete named production closure'
    return production


def accepts_production(current):
    """Accept only this captured revision; unknown edits still fail the old gate."""
    v = inputs(); expected = inspect(v)
    relative = {str(Path(p).relative_to('/tmp/klem-gentle-command')): digest
                for p, digest in current.items()}
    if relative == expected:
        return True
    import friendly_command_gena_revision as gena
    return gena.accepts_production(current)


def accepts_frontend(current, historical):
    v = inputs(); production = inspect(v)
    expected = dict(historical)
    assert len(expected) == 18 and 'src/grammar-labels.json' in expected, 'complete historical18 frontend inputs'
    assert expected['src/grammar-labels.json'] == v['binding']['parent_production_inputs']['/tmp/klem-gentle-command/web/src/grammar-labels.json'], 'original frontend belongs to captured parent'
    expected['src/grammar-labels.json'] = production['web/src/grammar-labels.json']
    if current == expected:
        return True
    import friendly_command_gena_revision as gena
    return gena.accepts_frontend(current, historical)
