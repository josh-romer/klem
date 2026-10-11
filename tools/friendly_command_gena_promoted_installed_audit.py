"""Audit complete current promoted captures; historical executables are archived evidence."""
import gzip
import json
import re
import signal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if HERE.name == 'willingness-question-prepared':
    sys.path.insert(0, str(HERE.parent / 'friendly-command-gena' / 'tools'))
import friendly_command_gena_installed_audit as original
import friendly_command_gena_promoted_streams as streams

ROOT = original.ROOT
revision = original.revision
sha = original.sha
CAPTURE_HEAD = '2e366b9fbe80ab299e1540792fe3f409802900f0'
MANIFEST_SHA = '52a98a9ddb14f576ec179e9bacb31a61c15f807bb40f40de1313b8c3fd4a1a08'
PREFIX = 'friendly-command-gena-promoted-'
PROMOTION_MANIFEST_SHA = 'ed5f3e113bd9d1555aa4079689260b4d01dc0e754f8866112de1f80bfd2e66af'


def inputs(prepared=None):
    originals = {}
    manifest = ROOT / 'docs/friendly-command-gena-promoted-installed-proof-archive.json'
    archived = prepared is None and manifest.exists()
    if archived:
        payload = manifest.read_bytes()
        assert MANIFEST_SHA is not None and sha(payload) == MANIFEST_SHA, 'pinned promoted installed proof manifest'
        for name, row in json.loads(payload)['files'].items():
            packed = (ROOT / 'docs' / row['path']).read_bytes()
            assert sha(packed) == row['archive_sha256'], 'complete packed promoted installed artifact'
            raw = gzip.decompress(packed)
            assert sha(raw) == row['source_sha256'], 'complete original promoted installed artifact'
            originals[name] = raw
    else:
        prepared = Path(prepared) if prepared is not None else HERE
    def raw(name):
        return originals[name] if archived else (prepared / name).read_bytes()
    def read(name):
        payload = raw(name)
        return json.loads(gzip.decompress(payload) if name.endswith('.gz') else payload)
    prior = original.inputs()
    promotion_raw = (ROOT / 'docs/friendly-command-gena-promotion-proof-archive.json').read_bytes()
    assert sha(promotion_raw) == PROMOTION_MANIFEST_SHA, 'pinned complete actual promotion proof'
    promotion = json.loads(promotion_raw)
    promoted_sources = {}
    for path in ['tests/fixtures/validity.json', 'tests/validity.rs', 'docs/inventory-reviews.json']:
        row = promotion['files']['promoted-' + path.replace('/', '-')]
        packed = (ROOT / 'docs' / row['path']).read_bytes()
        assert sha(packed) == row['archive_sha256']
        payload = gzip.decompress(packed)
        assert sha(payload) == row['source_sha256']
        promoted_sources[path] = payload
    installed = read(PREFIX + 'installed-runtime-retry1.json.gz')
    failure_raw = raw('gena-installed-cohort-recorder-failure-originals.json')
    failure = json.loads(failure_raw)
    return dict(reference=prior['reference'], historical_installed=prior,
                promoted_sources=promoted_sources,
                gate=read(PREFIX + 'completed-nix-output-audit.json'), gate_raw=raw(PREFIX + 'completed-nix-output-audit.json'),
                gate_log=raw(PREFIX + 'completed-nix-output-audit.log'), gate_producer=raw('verify_gena_completed_nix_outputs.py'),
                original_failed_gate_raw=raw(PREFIX + 'complete-nix-gate-retry2.json'),
                original_failed_gate_log=raw(PREFIX + 'complete-nix-gate-retry2.log'),
                package=read(PREFIX + 'nix-packages.json'), package_log=raw(PREFIX + 'nix-packages.log'),
                package_producer=raw('build_friendly_command_gena_promoted_nix_packages_retry3.py'), release_log=raw(PREFIX + 'release-rust.log'),
                installed=installed, installed_producer=raw('capture_friendly_command_gena_promoted_installed_runtime_retry4.py'),
                browser=read(PREFIX + 'installed-browser.json'), browser_raw=raw(PREFIX + 'installed-browser.json'),
                browser_runtime=read(PREFIX + 'installed-browser-runtime.json'), browser_log=raw(PREFIX + 'installed-browser-runtime.log'),
                browser_producer=raw('run_friendly_command_gena_promoted_installed_browser_retry4.py'), browser_driver=raw('friendly-command-gena-browser.mjs'),
                failed_prefix_manifest_raw=failure_raw,
                failed_prefix_originals={name: raw(Path(row['path']).name) for name, row in failure['files'].items()},
                cohort_command_streams={stream['path']: raw(Path(stream['path']).name)
                                        for attempt in installed['cohort_command_attempts']
                                        for stream in attempt['streams'].values()},
                command_streams={stream['path']: raw(Path(stream['path']).name)
                                 for attempt in installed['command_attempts']
                                 for stream in attempt['streams'].values()})


def inspect_packages(v):
    gate, package, installed = v['gate'], v['package'], v['installed']
    for report in [gate, package, installed]:
        original.revision.terminal(report, 'passed')
        assert report['head_unchanged'] and report['index_unchanged'], 'full promoted source HEAD/index freeze'
    assert gate['inputs_unchanged'] and package['inputs_unchanged'] and installed['inputs_unchanged'] and installed['source_unchanged'], 'full promoted source/input freeze'
    assert gate['protected_binaries_unchanged'] and package['protected_binaries_unchanged'], 'all promoted protected binaries unchanged'
    assert gate['head'] == package['head'] == installed['captured_head'] == CAPTURE_HEAD, 'same actual promoted checkpoint'
    assert gate['index_sha256'] == package['index_sha256'] == installed['index_sha256'], 'same complete promoted source index'
    frozen = package['frozen_inputs']
    assert len(frozen) == 7157 and frozen == gate['frozen_inputs'], 'complete7139 promoted source snapshot'
    assert all(frozen[name] == digest for name, digest in gate['inventory_source_files'].items()), 'every selected promoted inventory source byte'
    assert gate['promoted_cases'] == 35764 and gate['scoped_reviews'] == 520, 'actual full promoted ledger and review scope'
    assert all(frozen[path] == sha(payload) for path, payload in v['promoted_sources'].items()), 'every original complete promoted fixture judgment and review byte'
    assert len(json.loads(v['promoted_sources']['tests/fixtures/validity.json'])['cases']) == 35764
    assert len(json.loads(v['promoted_sources']['docs/inventory-reviews.json'])['entries']) == 520
    flake = 'git+file:///home/josh/projects/klem/.direnv/friendly-command-gena'
    assert gate['phase'] == 'complete' and gate['original_wrapper_state']=='failed' and gate['original_wrapper_failure_preserved'] and gate['Nix_build_replays']==0 and len(gate['outputs']) == 4 and len(set(gate['outputs'])) == 4, 'complete promoted four-check success'
    assert gate['command'][-4:] == [flake + '#checks.x86_64-linux.' + name for name in ['klem', 'web-assets', 'corpus-adapter', 'inventory-review']], 'all four actual promoted checks'
    assert gate['selected_controls'] == 214 and len(gate['results']) == 13 and all(row['exit_code'] == 0 for row in gate['results']), 'all selected102 and complete Nix commands'
    assert gate['results'][-1]['command'] == gate['command'] and gate['results'][-1]['stdout'].splitlines() == gate['outputs'], 'terminal four actual Nix outputs'
    failed = json.loads(v['original_failed_gate_raw'])
    assert failed['state']=='failed' and failed['exit_code']==1 and failed['error']=='AssertionError()', 'actual original output-type wrapper remains failed'
    assert sha(v['original_failed_gate_raw'])==gate['original_wrapper_receipt_sha256'], 'complete original output-type wrapper binding'
    assert sha(v['original_failed_gate_log'])==failed['log_sha256']==gate['original_build_log_sha256'], 'complete actual original four-check build log'
    assert gate['results']==failed['results'] and gate['frozen_inputs']==failed['frozen_inputs'] and gate['compiled_source_profiles']==failed['compiled_source_profiles'], 'all actual already completed Nix commands and exact selected profiles retained'
    assert gate['expected_output_types']==['directory','directory','directory','empty-file'] and len(gate['independent_audit_results'])==4, 'exact expected four output contracts'
    for row,name,output in zip(gate['independent_audit_results'],['klem','web-assets','corpus-adapter','inventory-review'],gate['outputs'],strict=True):
        assert row['exit_code']==0 and row['stdout'].strip()==output and row['command']==['nix','eval','--offline','--raw',flake+'#checks.x86_64-linux.'+name+'.outPath'], 'actual independent attribute/output verification'
    assert package['complete_gate_sha256'] == sha(v['gate_raw']), 'complete original promoted gate prerequisite'
    assert package['exit_code'] == 0 and len(package['outputs']) == 4 and set(package['outputs']) == set(installed['packages'].values()), 'all actual promoted package outputs'
    assert package['command'][-4:] == [flake + '#packages.x86_64-linux.' + name for name in ['klem', 'web-assets', 'corpus-adapter', 'web']], 'actual promoted packaged launcher build'
    for report, producer, log in [(gate, v['gate_producer'], v['gate_log']), (package, v['package_producer'], v['package_log'])]:
        assert report['producer'] == dict(text=producer.decode(), sha256=sha(producer)), 'complete actual promoted producer'
        assert report['log_sha256'] == sha(log), 'complete actual promoted log'
    assert installed['producer'] == dict(text=v['installed_producer'].decode(), sha256=sha(v['installed_producer'])), 'complete promoted installed collector'
    assert package['release_log_exit_code'] == 0 and package['release_log_sha256'] == sha(v['release_log']), 'complete actual promoted release log'
    plain_release = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', v['release_log'])
    batches = re.findall(rb'^test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', plain_release, flags=re.M)
    assert len(batches) == 255 and all(batch[0] == b'ok' for batch in batches) and [sum(int(batch[i]) for batch in batches) for i in [1, 2, 3]] == [1200, 0, 1], 'complete actual1200 release Rust255 suites'
    assert b'Doc-tests klem' in plain_release and b'test src/lib.rs - (line 3) ... ok' in plain_release, 'original release documentation test retained'
    assert package['release_rust'] == installed['release_rust'] == dict(totals=dict(passed=1200, failed=0, ignored=1), batches=255), 'promoted release totals match original log'
    prior = v['historical_installed']['installed']
    production = original.revision.inspect(v['reference']['revision'])
    assert set(installed['profiles']) == set(package['profiles']) == {'klem', 'klem-corpus-adapter', 'klem-web-assets'}, 'all complete promoted compile profiles'
    assert package['profiles'] == gate['compiled_source_profiles'], 'all selected promoted source profiles'
    for name, profile in installed['profiles'].items():
        files = profile['files']; prefix = 'web/' if name == 'klem-web-assets' else ''
        assert files == package['profiles'][name]['files'] and profile['package'] == installed['packages'][name], 'complete selected installed promoted profile equality'
        assert len(files) == (18 if prefix else 1146) and all(frozen[prefix + path] == digest for path, digest in files.items()), 'every1146/1146/18 promoted source byte'
        before = prior['profiles'][name]['files']
        changes = {path for path in set(before) | set(files) if before.get(path) != files.get(path)}
        assert changes == (set() if prefix else {'tests/fixtures/validity.json', 'tests/validity.rs'}), 'exact two independently tested promotion changes'
        assert set(files) == set(before), 'no original compiled input omitted'
        if not prefix:
            assert len(production) == 44 and all(files[path] == digest for path, digest in production.items()), 'all44 original Gena production bytes'
    assert set(installed['binaries']) == set(package['binaries']) == {'klem', 'adapter', 'server', 'launcher'}, 'all four promoted executables'
    for name, owner, binary in [('klem', 'klem', 'klem'), ('adapter', 'klem-corpus-adapter', 'klem-corpus-adapter'), ('server', 'klem', 'klem-web'), ('launcher', 'klem-web', 'klem-web')]:
        row = installed['binaries'][name]
        assert row['path'] == installed['packages'][owner] + '/bin/' + binary and installed['frozen_inputs'][row['path']] == row['sha256'], 'exact actual promoted executable'
        assert package['binaries'][name]['path'] == row['path'] and package['binaries'][name]['sha256'] == row['sha256'], 'actual built and replayed executable identity'
    assert len(gate['protected_binaries']) == 6 and gate['protected_binaries'] == package['protected_binaries'] and all(installed['frozen_inputs'][path] == digest for path, digest in gate['protected_binaries'].items()), 'all six original protected executables'
    assert package['assets'] == installed['assets'] == prior['assets'] and package['frontend_byte_identity'], 'complete original installed frontend assets'


def inspect_runtime(v):
    original.inspect_runtime(v)
    report = v['installed']
    assert len(report['command_attempts']) == 36 + 44 + 69 + 4 + 8, 'all161 explicit policy Native gold and broad commands retained'
    expected = [(row['command'], row['original_capture']['input']) for row in report['source_runs']]
    expected += [(row['command'], None) for group in ['native_records', 'lookup_records', 'corpus_runs', 'broad_runs'] for row in report[group]]
    rows = report['source_runs'] + [row for group in ['native_records', 'lookup_records', 'corpus_runs', 'broad_runs'] for row in report[group]]
    assert [(row['command'], row['input']) for row in report['command_attempts']] == expected, 'complete explicit capture command and original input order'
    assert len(v['command_streams']) == 322, 'complete322 retained command streams'
    for attempt, row in zip(report['command_attempts'], rows, strict=True):
        assert attempt['exit_code'] == 0 and set(attempt['streams']) == {'stdout', 'stderr'}, 'all actual replay command streams retained'
        for name, stream in attempt['streams'].items():
            assert report['frozen_inputs'][stream['path']] == stream['archive_sha256'], 'all retained actual stream bindings'
            assert len(stream['source_sha256']) == len(stream['archive_sha256']) == 64 and stream['bytes'] >= 0, 'complete actual stream digest and length'
            packed = v['command_streams'][stream['path']]
            assert sha(packed) == stream['archive_sha256'], 'actual retained packed stream bytes'
            payload = gzip.decompress(packed)
            assert sha(payload) == stream['source_sha256'] and len(payload) == stream['bytes'], 'actual complete stream content'
            if name == 'stdout':
                assert sha(payload) == row['stdout_sha256'], 'actual complete output bound to independently verified record'
                if 'stdout' in row:
                    assert payload == row['stdout'].encode(), 'actual complete output equals independently verified bytes'
            else:
                assert payload == row['stderr'].encode(), 'actual complete stderr equals retained record'


def inspect_browser(v):
    installed,report,browser=v['installed'],v['browser_runtime'],v['browser']
    revision.terminal(report,'passed')
    assert report['source_unchanged'] and report['server_stopped'] and report['server_exit_code'] in (0,-signal.SIGINT), 'owned installed browser source freeze/shutdown'
    assert report['head']==CAPTURE_HEAD and report['source_inputs']==v['package']['frozen_inputs'] and report['index_sha256']==v['package']['index_sha256'], 'same complete installed browser checkpoint'
    assert report['command']==[installed['binaries']['launcher']['path'],'--port','0','--dictionary','/home/josh/projects/klem/.direnv/dictionary-restoration/krdict.db'], 'actual packaged launcher browser command'
    for name in ['klem','server','launcher']:
        binary=installed['binaries'][name]
        assert report['frozen_inputs'][binary['path']]==binary['sha256'], 'exact installed browser executable binding'
    assert report['producer']['text'].encode()==v['browser_producer'] and 'job.send_signal(signal.SIGINT)' in v['browser_producer'].decode(), 'actual bounded installed server supervisor'
    assert report['driver']['text'].encode()==v['browser_driver'] and browser['producer_sha256']==sha(v['browser_driver']), 'actual unchanged installed browser driver'
    assert report['result_sha256']==sha(v['browser_raw']) and report['log_sha256']==sha(v['browser_log']), 'complete installed browser result/log'
    assert browser['state']=='source-bound-friendly-command-gena-browser-passed' and not browser['errors'], 'actual installed browser success'
    before=v['reference']['proof']['friendly-command-gena-browser.json']
    for key in ['exports','diagrams','spacingDiagrams','nativeEntries','policyDecisions']:
        assert browser[key]==before[key], 'every independently audited original installed browser choice/form/Native/export'
    assert len(browser['responses'])==2, 'both original installed Unicode API responses'
    for response,previous in zip(browser['responses'],before['responses'],strict=True):
        assert response['encoding']==previous['encoding'] and {k:x for k,x in response['api'].items() if k!='elapsed_ms'}=={k:x for k,x in previous['api'].items() if k!='elapsed_ms'}, 'every complete original installed API field'
    assert (report['decisions'],report['diagrams'],report['exports'],report['native_entries'])==(144,102,6,31), 'all144 installed decisions/102 diagrams/6 exports/31 Native'
    for asset in report['served_assets']:
        assert installed['assets'][asset['path'].lstrip('/')]==asset['sha256'], 'actual installed served assets'
    assert len(report['served_assets'])==2, 'actual installed JS and CSS served'
    assert len(report['screenshots']) == 2 and set(report['screenshots']) == {'desktop', 'mobile'}, 'both actual promoted screenshots retained'
    assert all(len(row['sha256']) == 64 for row in report['screenshots'].values()), 'complete actual promoted screenshot digests'
    assert all(report['frozen_inputs'][path] == digest for path, digest in v['package']['protected_binaries'].items()), 'all six original browser-protected executables'


def inspect(v):
    original.inspect(v['historical_installed'])
    inspect_packages(v)
    inspect_runtime(v)
    inspect_browser(v)
    streams.inspect_prefix(v)
    streams.inspect_cohorts(v)
    return dict(reused_commands=149, prefix_command_replays=0, retained_command_streams=472, actual_cohort_commands=75,
                shared_cases=35764, scoped_reviews=520, release_rust_tests=1200,
                installed_cli_policies=36, complete_native_owners=44, new_lemma_lookups=69,
                cohort_words=53502, annotated_gold_rows=66570, broad_frames=1128312,
                browser_decisions=144, required_diagrams=102, exact_exports=6, complete_browser_native_entries=31,
                main_context_register_independent_review='pending', full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
