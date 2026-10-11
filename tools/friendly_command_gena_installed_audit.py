"""Audit current installed Gena results against every original source capture."""
import gzip
import json
import re
import signal
from pathlib import Path

import friendly_command_gena_revision as revision
import friendly_command_gena_runtime_audit as runtime

ROOT = revision.ROOT
sha = revision.sha
CAPTURE_HEAD = '6cf27565c7891005de12651abcb7f18911495adf'
MANIFEST_SHA = '545fbd3cc756746e5afadf12f5c5008e96fe4fc70de63452b441b51252764c8e'


def inputs(prepared=None):
    manifest = ROOT/'docs/friendly-command-gena-installed-proof-archive.json'
    archived = prepared is None and manifest.exists()
    originals = {}
    if archived:
        raw = manifest.read_bytes()
        assert MANIFEST_SHA is not None and sha(raw)==MANIFEST_SHA, 'immutable installed Gena manifest'
        for name,item in json.loads(raw)['files'].items():
            packed=(ROOT/'docs'/item['path']).read_bytes()
            assert sha(packed)==item['archive_sha256'], 'immutable installed Gena archive bytes'
            original=gzip.decompress(packed)
            assert sha(original)==item['source_sha256'], 'complete original installed Gena payload'
            originals[name]=original
    else:
        prepared = Path(prepared) if prepared is not None else Path(__file__).resolve().parent
    def raw(name):
        return originals[name] if archived else (prepared/name).read_bytes()
    def read(name):
        payload=raw(name)
        return json.loads(gzip.decompress(payload) if name.endswith('.gz') else payload)
    return dict(reference=runtime.inputs(),
                package=read('friendly-command-gena-nix-packages.json'),
                selected=read('friendly-command-gena-selected-source.json'),
                installed=read('friendly-command-gena-installed-runtime.json.gz'),
                browser=read('friendly-command-gena-installed-browser.json'),
                browser_runtime=read('friendly-command-gena-installed-browser-runtime.json'),
                package_producer=raw('build_friendly_command_gena_nix_packages.py'),
                package_log=raw('friendly-command-gena-nix-packages.log'),
                selected_producer=raw('preflight_friendly_command_gena_selected_source.py'),
                selected_log=raw('friendly-command-gena-selected-source.log'),
                installed_producer=raw('capture_friendly_command_gena_installed_runtime.py'),
                browser_producer=raw('run_friendly_command_gena_installed_browser.py'),
                browser_driver=raw('friendly-command-gena-browser.mjs'),
                browser_log=raw('friendly-command-gena-installed-browser-runtime.log'),
                browser_raw=raw('friendly-command-gena-installed-browser.json'))


def inspect_packages(v):
    package, installed, selected = v['package'],v['installed'],v['selected']
    for report in [package,installed,selected]:
        revision.terminal(report,'passed')
        assert report['head_unchanged'] and report['index_unchanged'], 'actual installed source/HEAD/index freeze'
    assert installed['source_unchanged'], 'complete installed source freeze'
    assert package['head'] == selected['head'] == installed['captured_head'] == CAPTURE_HEAD, 'same named installed checkpoint'
    assert selected['controls'] == 224 and len(selected['results']) == 8 and all(r['exit_code']==0 for r in selected['results']), 'all224 actual selected controls'
    assert len(package['frozen_inputs']) == len(selected['frozen_inputs']) == 6985 and len(package['inventory_source_files']) == len(selected['selected_files']) == 6943, 'complete6985/6943 selected source snapshots'
    assert package['frozen_inputs'] == selected['frozen_inputs'] and package['inventory_source_files'] == selected['selected_files'], 'exact complete selected/package source identity'
    assert package['exit_code'] == 0 and len(package['outputs']) == 4 and set(package['outputs']) == set(installed['packages'].values()), 'all four actual installed outputs'
    for report,producer,log in [(package,v['package_producer'],v['package_log']),(selected,v['selected_producer'],v['selected_log'])]:
        assert report['producer']['text'].encode()==producer and sha(producer)==report['producer']['sha256'], 'actual retained package/selection producers'
        assert report['log_sha256']==sha(log), 'complete actual package/selection logs'
    assert installed['producer']['text'].encode()==v['installed_producer'], 'actual installed collector producer'
    batches=re.findall(rb'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;',v['package_log'])
    assert len(batches)==255 and all(b[0]==b'ok' for b in batches) and [sum(int(b[i]) for b in batches) for i in [1,2,3]] == [1200,0,1], 'actual1200 release Rust/255 suites'
    assert installed['release_rust']==dict(totals=dict(passed=1200,failed=0,ignored=1),batches=255), 'release totals match full package log'
    production = revision.inspect(v['reference']['revision'])
    for name,profile in installed['profiles'].items():
        assert profile['package']==installed['packages'][name], 'installed package/profile identity'
        prefix='web/' if name=='klem-web-assets' else ''
        assert all(package['frozen_inputs'][prefix+p]==d for p,d in profile['files'].items()), 'every installed source profile byte'
        selected_name={'klem':'klem','klem-corpus-adapter':'corpus-adapter','klem-web-assets':'web-assets'}[name]
        assert profile['files']==selected['profiles'][selected_name]['files'], 'complete selected/installed source profile equality'
        assert len(profile['files'])==(18 if prefix else 1146), 'complete1146/1146/18 profiles'
        if not prefix: assert all(profile['files'][p]==d for p,d in production.items()), 'all44 current compiled production bytes'
    for name,owner,binary in [('klem','klem','klem'),('adapter','klem-corpus-adapter','klem-corpus-adapter'),('server','klem','klem-web'),('launcher','klem-web','klem-web')]:
        value=installed['binaries'][name]
        assert value['path']==installed['packages'][owner]+'/bin/'+binary and installed['frozen_inputs'][value['path']]==value['sha256'], 'exact actual installed executable'


def inspect_runtime(v):
    report=v['installed']; reference=v['reference']; cli=report['binaries']['klem']['path']
    captures=reference['captures']['captures']
    assert len(report['source_runs'])==len(captures)==36, 'all36 complete installed policies'
    for row,original in zip(report['source_runs'],captures,strict=True):
        assert row['original_capture']==original, 'every complete original current CLI capture'
        assert row['command']==[cli,*original['command'][1:]] and row['exit_code']==0, 'actual installed CLI policy command'
        assert row['stdout']==original['stdout'] and row['stderr']==original['stderr'] and row['stdout_sha256']==sha(row['stdout'].encode()), 'every original installed CLI byte'
    native=dict(reference['captures']['native_entries'])
    for ident,row in reference['native']['actual_complete_entry_responses'].items():
        assert ident not in native or native[ident]['stdout']==row['stdout'], 'duplicate complete Native owner equality'
        native[ident]=row
    assert len(native)==len(report['native_records'])==44 and [r['id'] for r in report['native_records']]==list(native), 'all44 complete installed Native owners'
    for row in report['native_records']:
        original=native[row['id']]
        assert row['original_capture']==original and row['stdout']==original['stdout'] and row['stderr']==original['stderr'], 'every complete original installed Native response'
        assert row['command']==[cli,*original['command'][1:]] and row['exit_code']==0 and row['stdout_sha256']==sha(row['stdout'].encode()), 'actual complete installed Native command'
    queries=reference['native']['actual_headword_queries']
    assert len(report['lookup_records'])==len(queries)==69 and [r['headword'] for r in report['lookup_records']]==list(queries), 'all69 installed new lemma lookups'
    for row in report['lookup_records']:
        original=queries[row['headword']]
        assert row['original_capture']==original and row['stdout']==original['stdout'] and row['stderr']==original['stderr'], 'every complete installed headword response'
        assert row['command']==[cli,*original['command'][1:]] and row['exit_code']==0 and row['stdout_sha256']==sha(row['stdout'].encode()), 'actual installed headword query command'
    assert [(r['family'],r['surfaces']) for r in report['cohort_runs']]==[('corpus',32096),('history',21406)], 'all53502 installed cohort words'
    for row,original in zip(report['cohort_runs'],reference['cohorts']['runs'],strict=True):
        assert row['words']==original['captures'][1]['words'], 'every original ordered installed WordAnalysis'
    assert len(report['corpus_runs'])==4, 'all four installed gold partitions'
    for row,original in zip(report['corpus_runs'],reference['gold']['runs'],strict=True):
        assert row['original_capture']==original and row['stdout']==original['jsonl'] and row['stdout_sha256']==sha(row['stdout'].encode()), 'every complete installed gold row/outcome/summary'
        assert row['command']==[report['binaries']['adapter']['path'],*original['command'][1:]] and row['exit_code']==0, 'actual installed gold adapter command'
    assert len(report['broad_runs'])==8 and sum(r['records'] for r in report['broad_runs'])==1128312, 'all eight installed broad streams'
    for row,original in zip(report['broad_runs'],reference['broad']['runs'],strict=True):
        assert row['mode']==original['mode'] and row['command']==[cli,*original['commands'][1][1:]] and row['exit_code']==0, 'actual installed broad filter/spacing command'
        assert row['records']==original['records'] and row['stdout_sha256']==original['after_jsonl_sha256'] and row['source_sha256']==original['source_sha256'], 'complete installed broad input/output bytes'
        assert row['changed_frames']==original['changed_frames'], 'all18 full original unjudged broad contexts and paths'


def inspect_browser(v):
    installed,report,browser=v['installed'],v['browser_runtime'],v['browser']
    revision.terminal(report,'passed')
    assert report['source_unchanged'] and report['server_stopped'] and report['server_exit_code'] in (0,-signal.SIGINT), 'owned installed browser source freeze/shutdown'
    assert report['head']==CAPTURE_HEAD and report['source_inputs']==v['package']['frozen_inputs'], 'same complete installed browser checkpoint'
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


def inspect(v):
    runtime.inspect(v['reference']);inspect_packages(v);inspect_runtime(v);inspect_browser(v)
    return dict(release_rust_tests=1200,current_selected_controls=224,installed_cli_policies=36,
                complete_native_owners=44,new_lemma_lookups=69,cohort_words=53502,
                annotated_gold_rows=66570,broad_frames=1128312,browser_decisions=144,
                required_diagrams=102,exact_exports=6,complete_browser_native_entries=31,
                main_quiet_context_register_independent_review_and_shared24promotion='pending',full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
