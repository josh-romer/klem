"""Audit installed Sena outputs against full independent source/corpus proofs.

The historical executables are captured evidence. This audit does not claim to
read those executable files inside Nix; live installed execution is proved by
the original frozen collectors, launch commands, and exact original outputs.
"""
import gzip
import json
import math
import re
import signal
from pathlib import Path

import friendly_hortative_sena_revision as revision
import friendly_hortative_sena_runtime_audit as runtime
import friendly_hortative_sena_wide_audit as wide
import friendly_hortative_sena_browser_audit as browser_audit

ROOT = revision.ROOT
sha = revision.sha
CAPTURE_HEAD = 'e4436e38fdbce5d7f27ba4f11277b782ce8f7689'
MANIFEST_SHA = 'd6bd8877e9d5b57dc4229a5597f59a8d468747b8375a1993af2ca571ef66a666'
PREFIX = 'friendly-hortative-sena-'


def inputs(prepared=None):
    assert runtime.binary_mode() == 'captured', 'explicit captured installed evidence scope'
    originals = {}
    manifest = ROOT / 'docs/friendly-hortative-sena-installed-proof-archive.json'
    archived = prepared is None and manifest.exists()
    if archived:
        payload = manifest.read_bytes()
        assert MANIFEST_SHA is not None and sha(payload) == MANIFEST_SHA, 'pinned installed proof manifest'
        for name, item in json.loads(payload)['files'].items():
            packed = (ROOT / 'docs' / item['path']).read_bytes()
            assert sha(packed) == item['archive_sha256'], 'complete packed installed artifact'
            original = gzip.decompress(packed)
            assert sha(original) == item['source_sha256'] and len(original) == item['bytes'], 'complete original installed artifact'
            originals[name] = original
    else:
        prepared = Path(prepared) if prepared is not None else Path(__file__).resolve().parent
    def raw(name):
        return originals[name] if archived else (prepared / name).read_bytes()
    def read(name):
        payload = raw(name)
        return json.loads(gzip.decompress(payload) if name.endswith('.gz') else payload)
    return dict(originals=originals, revision=revision.inputs(), reference=wide.inputs(),
                gate=read(PREFIX+'complete-nix-gate.json'),
                gate_raw=raw(PREFIX+'complete-nix-gate.json'),
                gate_log=raw(PREFIX+'complete-nix-gate.log'),
                gate_producer=raw('run_complete_friendly_hortative_sena_nix_gate.py'),
                package=read(PREFIX+'nix-packages-retry1.json'),
                package_log=raw(PREFIX+'nix-packages-retry1.log'),
                package_producer=raw('build_friendly_hortative_sena_nix_packages_retry1.py'),
                release_log=raw(PREFIX+'release-rust-retry1.log'),
                documentation_scope=read(PREFIX+'documentation-scope.json'), documentation_scope_raw=raw(PREFIX+'documentation-scope.json'),
                documentation_log=raw(PREFIX+'documentation-scope.log'), documentation_producer=raw('run_friendly_hortative_sena_documentation_scope.py'),
                installed=read(PREFIX+'installed-runtime-completion-audit.json.gz'),
                installed_producer=raw('audit_completed_sena_runtime.py'),
                browser=read(PREFIX+'installed-browser.json'),
                browser_raw=raw(PREFIX+'installed-browser.json'),
                browser_runtime=read(PREFIX+'installed-browser-runtime.json'),
                browser_producer=raw('run_friendly_hortative_sena_installed_browser_retry4.py'),
                browser_driver=raw(PREFIX+'browser.mjs'),
                browser_log=raw(PREFIX+'installed-browser-runtime.log'))


def inspect_packages(v):
    gate, package, installed = v['gate'], v['package'], v['installed']
    for report in [gate, package, installed]:
        runtime.terminal(report)
    assert gate['protected_binaries_unchanged'] and package['protected_binaries_unchanged'] and installed['source_unchanged'], 'all protected source and executable freezes'
    assert gate['head'] == package['head'] == installed['captured_head'] == CAPTURE_HEAD, 'same named installed checkpoint'
    assert gate['index_sha256'] == package['index_sha256'] == installed['index_sha256'], 'same full installed source index'
    assert len(gate['frozen_inputs']) == len(package['frozen_inputs']) == 7258 and gate['frozen_inputs'] == package['frozen_inputs'], 'complete7258 selected package source identity'
    assert len(gate['inventory_source_files']) == 7216 and all(package['frozen_inputs'][p] == d for p,d in gate['inventory_source_files'].items()), 'complete7216 inventory source bytes'
    flake = 'git+file:///home/josh/projects/klem/.direnv/friendly-hortative-sena'
    assert gate['phase'] == 'complete' and gate['exit_code'] == 0 and len(gate['outputs']) == 4 and len(set(gate['outputs'])) == 4, 'actual complete four-check terminal success'
    assert all(p.startswith('/nix/store/') for p in gate['outputs']), 'actual Nix check outputs'
    assert gate['command'][-4:] == [flake+'#checks.x86_64-linux.'+n for n in ['klem','web-assets','corpus-adapter','inventory-review']], 'all four actual Nix checks'
    assert gate['selected_preflight_passed'] and len(gate['results']) == 6 and all(r['exit_code'] == 0 for r in gate['results']), 'complete selection preflight and build commands'
    assert gate['results'][-2]['command'] == ['python3','-m','unittest','discover','-s','tools','-p','test_friendly_hortative_sena_revision.py'] and gate['results'][-1]['command'] == gate['command'], 'actual31 selected guard then full Nix gate'
    assert package['complete_gate_sha256'] == sha(v['gate_raw']), 'original complete gate prerequisite'
    assert package['exit_code'] == 0 and len(package['outputs']) == 4 and set(package['outputs']) == set(installed['packages'].values()), 'all four actual installed package outputs'
    assert set(installed['packages']) == {'klem','klem-web-assets','klem-corpus-adapter','klem-web'}, 'all four named installed packages'
    assert package['command'][-4:] == [flake+'#packages.x86_64-linux.'+n for n in ['klem','web-assets','corpus-adapter','web']], 'actual packaged web launcher build'
    for report, producer, log in [(gate,v['gate_producer'],v['gate_log']), (package,v['package_producer'],v['package_log'])]:
        assert report['producer'] == dict(text=producer.decode(),sha256=sha(producer)), 'complete original package/gate producers'
        assert report['log_sha256'] == sha(log), 'complete actual package/gate logs'
    assert installed['producer'] == dict(text=v['installed_producer'].decode(),sha256=sha(v['installed_producer'])), 'complete original installed collector'
    assert package['release_log_exit_code'] == 0 and package['release_log_command'] == ['nix','log',flake+'#packages.x86_64-linux.klem'] and package['release_log_sha256'] == sha(v['release_log']), 'actual complete release build log'
    doc = v['documentation_scope']
    runtime.terminal(doc)
    assert doc['head'] == CAPTURE_HEAD and doc['index_sha256'] == package['index_sha256'], 'same actual documentation scope checkpoint'
    assert package['documentation_scope_sha256'] == sha(v['documentation_scope_raw']), 'complete original documentation scope binding'
    assert doc['producer'] == dict(text=v['documentation_producer'].decode(),sha256=sha(v['documentation_producer'])) and doc['log_sha256'] == sha(v['documentation_log']), 'complete actual documentation producer and log'
    assert doc['exit_code'] == 0 and doc['documentation_totals'] == dict(passed=1,failed=0,ignored=0), 'actual original documentation test passed'
    assert doc['expected_default_release_totals'] == dict(passed=1212,failed=0,ignored=1) and doc['expected_default_release_batches'] == 257, 'complete derived default release scope'
    assert len(doc['excluded_zero_test_example_targets']) == 6 and doc['complete_original_inventory_audit']['targets'] == 262 and doc['complete_original_inventory_audit']['commands'] == 266, 'complete original all-target scope retained'
    assert b'test src/lib.rs - (line 3) ... ok' in v['documentation_log'], 'complete original actual documentation output'
    normalized_release=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',v['release_log'])
    assert b'Doc-tests klem' in normalized_release and b'test src/lib.rs - (line 3) ... ok' in normalized_release, 'original release documentation test retained'
    batches = re.findall(rb'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',v['release_log'])
    assert len(batches) == 257 and all(b[0] == b'ok' for b in batches) and [sum(int(b[i]) for b in batches) for i in [1,2,3]] == [1212,0,1], 'actual1212 release Rust257 suites'
    assert installed['release_rust'] == package['release_rust'] == dict(totals=dict(passed=1212,failed=0,ignored=1),batches=257), 'release totals match original Rust log'
    previous = v['revision']['selected'][PREFIX+'wide-selected-source.json']['profiles']
    assert package['profiles'] == gate['profiles'] and {n:r['files'] for n,r in package['profiles'].items()} == {n:r['files'] for n,r in previous.items()}, 'all previously passed1158/1158/18 profiles'
    assert set(installed['profiles']) == {'klem','klem-corpus-adapter','klem-web-assets'}, 'all three installed compile profiles'
    production = v['revision']['browser']['runtime']['current']
    for name, profile in installed['profiles'].items():
        selected_name = {'klem':'klem','klem-corpus-adapter':'corpus-adapter','klem-web-assets':'web-assets'}[name]
        assert profile['package'] == installed['packages'][name] and profile['files'] == package['profiles'][selected_name]['files'], 'complete selected installed profile equality'
        prefix = 'web/' if name == 'klem-web-assets' else ''
        assert all(package['frozen_inputs'][prefix+p] == d for p,d in profile['files'].items()), 'every installed compile source byte'
        if not prefix:
            assert all(profile['files'][p] == d for p,d in production.items()) and len(production) == 44, 'all44 installed production inputs'
    assert set(installed['binaries']) == {'klem','adapter','server','launcher'}, 'all four installed executables'
    for name, owner, binary in [('klem','klem','klem'),('adapter','klem-corpus-adapter','klem-corpus-adapter'),('server','klem','klem-web'),('launcher','klem-web','klem-web')]:
        row = installed['binaries'][name]
        assert row['path'] == installed['packages'][owner]+'/bin/'+binary and installed['frozen_inputs'][row['path']] == row['sha256'], 'exact actual installed executable'
    assert len(gate['protected_binaries']) == 6 and gate['protected_binaries'] == package['protected_binaries'] and all(installed['frozen_inputs'][p] == d for p,d in gate['protected_binaries'].items()), 'all six protected original debug executables'


def original_output(row, original, cli, message):
    assert row['original_capture'] == original, 'complete original '+message+' capture'
    assert row['command'] == [cli,*original['command'][1:]] and row['exit_code'] == 0, 'actual installed '+message+' command'
    assert row['stdout'] == original['stdout'] and row['stderr'] == original['stderr'] and row['stdout_sha256'] == sha(row['stdout'].encode()), 'every original installed '+message+' byte'


def inspect_runtime(v):
    report, reference = v['installed'],v['reference']
    cli = report['binaries']['klem']['path']
    captures = reference['runtime']['captures']['captures']
    assert len(report['source_runs']) == len(captures) == 36, 'all36 complete installed policies'
    for row, original in zip(report['source_runs'],captures,strict=True):
        original_output(row,original,cli,'CLI')
    corpus = v['revision']['browser']['corpus']
    assert len(report['corpus_sentence_runs']) == len(corpus['captures']) == 12, 'all12 whole original corpus policies'
    for row, original in zip(report['corpus_sentence_runs'],corpus['captures'],strict=True):
        assert row['stable_case_id'] == corpus['stable_case_id'] and row['original_capture'] == original, 'original corpus stable case and full capture'
        copy = dict(row,original_capture=original['after'])
        original_output(copy,original['after'],cli,'corpus sentence')
    native = dict(reference['runtime']['captures']['native_entries'])
    for group in [reference['native']['actual_complete_entry_responses'],corpus['actual_complete_entry_responses']]:
        for ident, row in group.items():
            assert ident not in native or (native[ident]['stdout'] == row['stdout'] and native[ident]['response'] == row['response']), 'duplicate complete Native owner equality'
            if ident not in native: native[ident] = row
    assert len(native) == len(report['native_records']) == 46 and [r['id'] for r in report['native_records']] == list(native), 'all46 complete installed Native owners'
    for row in report['native_records']:
        original_output(row,native[row['id']],cli,'Native')
    queries = dict(reference['native']['actual_headword_queries'])
    for head, row in corpus['actual_headword_queries'].items():
        assert head not in queries or (queries[head]['stdout'] == row['stdout'] and json.loads(queries[head]['stdout']) == json.loads(row['stdout'])), 'duplicate complete headword equality'
        if head not in queries: queries[head] = row
    assert len(queries) == len(report['lookup_records']) == 72 and [r['headword'] for r in report['lookup_records']] == list(queries), 'all72 complete installed headword queries'
    for row in report['lookup_records']:
        original_output(row,queries[row['headword']],cli,'headword')
    assert [(r['family'],r['surfaces']) for r in report['cohort_runs']] == [('corpus',32096),('history',21406)], 'all53502 installed cohort words'
    for row, original in zip(report['cohort_runs'],reference['cohorts']['runs'],strict=True):
        assert row['words'] == original['captures'][1]['words'], 'every original ordered installed WordAnalysis'
    assert len(report['corpus_runs']) == 4, 'all four installed gold partitions'
    for row, original in zip(report['corpus_runs'],reference['gold']['runs'],strict=True):
        assert row['original_capture'] == original and row['stdout'] == original['jsonl'] and row['stdout_sha256'] == sha(row['stdout'].encode()), 'every complete installed gold row outcome and summary'
        assert row['command'] == [report['binaries']['adapter']['path'],*original['command'][1:]] and row['exit_code'] == 0, 'actual installed gold adapter command'
    assert len(report['broad_runs']) == 8 and sum(r['records'] for r in report['broad_runs']) == 1128312, 'all eight installed broad streams'
    for row, original in zip(report['broad_runs'],reference['broad']['runs'],strict=True):
        assert row['mode'] == original['mode'] and row['command'] == [cli,*original['commands'][1][1:]] and row['exit_code'] == 0, 'actual installed broad filter spacing command'
        assert row['records'] == original['records'] and row['stdout_sha256'] == original['after_jsonl_sha256'] and row['source_sha256'] == original['source_sha256'], 'complete installed broad input output bytes'
        assert row['changed_frames'] == original['changed_frames'], 'all full original unjudged broad contexts'


def inspect_browser(v):
    installed, report, browser = v['installed'],v['browser_runtime'],v['browser']
    runtime.terminal(report)
    assert report['source_unchanged'] and report['server_stopped'] and report['server_exit_code'] in [0,-signal.SIGINT], 'owned installed browser source freeze shutdown'
    assert report['head'] == CAPTURE_HEAD and report['source_inputs'] == v['package']['frozen_inputs'] and report['index_sha256'] == v['package']['index_sha256'], 'same complete installed browser checkpoint'
    assert report['command'] == [installed['binaries']['launcher']['path'],'--port','0','--dictionary','/home/josh/projects/klem/.direnv/dictionary-restoration/krdict.db'], 'actual packaged launcher browser command'
    assert report['packages'] == installed['packages'] and report['installed_binaries'] == installed['binaries'], 'complete installed browser package binding'
    for row in installed['binaries'].values():
        if row['path'] in report['frozen_inputs']:
            assert report['frozen_inputs'][row['path']] == row['sha256'], 'exact installed browser executable fingerprint'
    assert all(report['frozen_inputs'][installed['binaries'][n]['path']] == installed['binaries'][n]['sha256'] for n in ['klem','server','launcher']), 'all three installed browser executables'
    assert all(report['frozen_inputs'][p] == d for p,d in v['gate']['protected_binaries'].items()), 'all six protected browser debug executables'
    assert report['producer'] == dict(text=v['browser_producer'].decode(),sha256=sha(v['browser_producer'])) and 'job.send_signal(signal.SIGINT)' in v['browser_producer'].decode() and 'job.wait(timeout=20)' in v['browser_producer'].decode(), 'actual bounded installed browser supervisor'
    assert report['driver'] == dict(text=v['browser_driver'].decode(),sha256=sha(v['browser_driver'])) and browser['producer_sha256'] == sha(v['browser_driver']), 'actual unchanged installed browser driver'
    before = v['revision']['browser']['proof'][PREFIX+'browser.json']
    assert browser['producer_sha256'] == before['producer_sha256'], 'same independently audited browser driver'
    assert report['result_sha256'] == sha(v['browser_raw']) and report['log_sha256'] == sha(v['browser_log']), 'complete installed browser result log'
    assert browser['state'] == 'source-bound-friendly-hortative-sena-browser-passed' and not browser['errors'], 'actual installed browser success'
    for key in ['exports','diagrams','spacingDiagrams','nativeEntries','policyDecisions','corpusDecisions']:
        if key == 'corpusDecisions':
            def semantic_rows(rows):
                projected=[]
                for row in rows:
                    elapsed=row['api']['elapsed_ms']
                    assert isinstance(elapsed,(int,float)) and not isinstance(elapsed,bool) and math.isfinite(elapsed) and elapsed>=0, 'valid captured corpus latency'
                    projected.append({**row,'api':{k:value for k,value in row['api'].items() if k!='elapsed_ms'}})
                return projected
            assert semantic_rows(browser[key]) == semantic_rows(before[key]), 'every independently audited original installed browser choice form Native export; every independently audited original corpus semantic field'
        else:
            assert browser[key] == before[key], 'every independently audited original installed browser choice form Native export'
    assert len(browser['responses']) == len(before['responses']) == 2, 'both original installed Unicode API responses'
    for response, previous in zip(browser['responses'],before['responses'],strict=True):
        assert response['encoding'] == previous['encoding'] and {k:x for k,x in response['api'].items() if k != 'elapsed_ms'} == {k:x for k,x in previous['api'].items() if k != 'elapsed_ms'}, 'every complete original installed API field'
    assert (report['decisions'],report['diagrams'],report['forbidden'],report['corpus_decisions'],report['exports'],report['native_entries']) == (150,114,36,6,12,37), 'all150 decisions114 diagrams36 forbidden6 corpus12 exports37 Native'
    assert report['assets'] == installed['assets'] and report['frontend_inputs'] == installed['profiles']['klem-web-assets']['files'], 'complete installed frontend input and asset binding'
    assert report['production_inputs'] == v['revision']['browser']['runtime']['current'], 'all44 installed browser production inputs'
    assert len(report['served_assets']) == 2 and {p['path'].rsplit('.',1)[-1] for p in report['served_assets']} == {'js','css'}, 'actual installed JS CSS served'
    for asset in report['served_assets']:
        assert installed['assets'][asset['path'].lstrip('/')] == asset['sha256'], 'actual installed served assets: actual installed served asset bytes'
    assert len(report['screenshots']) == 2 and all(len(d) == 64 for d in report['screenshots'].values()), 'both retained installed viewport screenshots'


def inspect_streams(v):
    """Derive every installed result from all original253 commands/506 streams."""
    report, files = v['installed'], v['originals']
    original_raw = files[PREFIX + 'installed-runtime-retry3.json.gz']
    original = json.loads(gzip.decompress(original_raw))
    assert sha(original_raw) == report['original_attempt_sha256'] and original['state'] == 'failed' and original['error'] == 'every actual command stream captured', 'original failed wrapper retained separately'
    assert report['completion_kind'] == 'independent-completed-output-audit' and report['supplementary_audit_executed_cli_commands'] == 0, 'independent completed-output scope'
    assert report['command_attempts'] == original['command_attempts'] and len(report['command_attempts']) == 253, 'all original253 actual command records'
    attempts = iter(report['command_attempts']); streams = set(); count = 0
    def output(row):
        nonlocal count
        count += 1
        assert row['exit_code'] == 0 and set(row['streams']) == {'stdout', 'stderr'}, 'all successful actual commands with both streams'
        text = row['input']
        assert row['input_sha256'] == (None if text is None else sha(text.encode())), 'complete actual command input'
        stdout = None
        for kind, item in row['streams'].items():
            name = Path(item['path']).name
            assert name in files and name not in streams, 'all complete unique original stream archives'
            streams.add(name); packed = files[name]
            assert sha(packed) == item['archive_sha256'], 'original packed installed stream bytes'
            raw = gzip.decompress(packed)
            assert sha(raw) == item['sha256'] and len(raw) == item['bytes'], 'every full original installed stream byte'
            if kind == 'stdout': stdout = raw
            else: assert raw == b'', 'all successful installed stderr streams empty'
        return stdout
    for key in ['source_runs', 'corpus_sentence_runs', 'native_records', 'lookup_records']:
        for result in report[key]:
            attempt = next(attempts)
            assert attempt['command'] == result['command'], 'original finite installed command order'
            raw = output(attempt)
            assert raw.decode() == result['stdout'] and sha(raw) == result['stdout_sha256'], 'every finite whole installed result from actual stdout'
    cli = report['binaries']['klem']['path']
    for result in report['cohort_runs']:
        words = result['words']; surfaces = sorted(words); text = '\n'.join(surfaces) + '\n'; raw_text = text.encode()
        attempt = next(attempts)
        assert attempt['command'] == [cli, 'text', '-'] and attempt['input'] == text, 'whole exact installed cohort command and input'
        frames = [json.loads(line) for line in output(attempt).splitlines() if line]
        assert ''.join(f['surface'] for f in frames) == text, 'complete installed cohort original stream coverage'
        starts = {}; offset = 0; cursor = 0; whole = {}
        for surface in surfaces:
            starts[offset] = surface; offset += len(surface.encode()) + 1
        for frame in frames:
            span = frame['span']
            assert span['start'] == cursor and raw_text[cursor:span['end']].decode() == frame['surface'], 'every installed cohort frame span and order'
            cursor = span['end']
            if frame['kind'] == 'word' and starts.get(span['start']) == frame['surface'] and span['end'] == span['start'] + len(frame['surface'].encode()):
                whole[frame['surface']] = frame['analysis']
        assert cursor == len(raw_text), 'every installed cohort original input byte'
        missing = set(surfaces) - set(whole)
        for _ in range(len(missing)):
            fallback = next(attempts); command = fallback['command']
            assert len(command) == 3 and command[:2] == [cli, 'word'] and command[2] in missing and fallback['input'] is None, 'every original punctuation word once'
            surface = command[2]; missing.remove(surface); whole[surface] = json.loads(output(fallback))
        assert not missing and whole == words, 'all53502 complete installed WordAnalysis fields from actual stdout'
    for result in report['corpus_runs']:
        attempt = next(attempts)
        assert attempt['command'] == result['command'], 'original gold adapter command order'
        raw = output(attempt)
        assert raw.decode() == result['stdout'] and sha(raw) == result['stdout_sha256'], 'all complete original gold rows from actual stdout'
    for result in report['broad_runs']:
        attempt = next(attempts)
        assert attempt['command'] == result['command'], 'original broad stream command order'
        raw = output(attempt)
        assert sha(raw) == result['stdout_sha256'] and len(raw.splitlines()) == result['records'], 'all1128312 full original broad frames from actual stdout'
    assert next(attempts, None) is None and count == 253 and len(streams) == 506, 'all253 actual commands and506 complete streams'
    return dict(actual_commands=count, full_streams=len(streams))


def inspect(v):
    revision.inspect(v['revision'])
    runtime.inspect(v['reference']['runtime'])
    wide.inspect(v['reference'])
    browser_audit.inspect(v['revision']['browser'])
    inspect_packages(v)
    inspect_runtime(v)
    inspect_browser(v)
    inspect_streams(v)
    return dict(release_rust_tests=1212,release_rust_targets=257,installed_cli_policies=48,
                complete_native_owners=46,new_lemma_lookups=72,cohort_words=53502,
                annotated_gold_rows=66570,broad_frames=1128312,browser_decisions=150,
                required_diagrams=114,exact_exports=12,complete_browser_native_entries=37,
                main_quiet_context_register_independent_review_and_shared25promotion='pending',
                full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
