"""Audit actual Nix sources, installed comparisons and bounded browser results."""
import gzip
import hashlib
import json
from pathlib import Path

import gentle_command_runtime_audit as runtime

ROOT = Path(__file__).resolve().parents[1]
sha = lambda raw: hashlib.sha256(raw).hexdigest()
MANIFEST_SHA = '77d29b5a2375ace8256d8bd1194e132bff5bf4056d2f0fe8a935051440f22232'


def inputs():
    docs = ROOT/'docs'; raw = (docs/'gentle-command-installed-proof-archive.json').read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'original installed manifest cannot be refreshed'
    manifest = json.loads(raw);proof = {}
    for name,item in manifest['files'].items():
        raw = (docs/item['path']).read_bytes()
        assert sha(raw) == item['archive_sha256'], 'unchanged installed archive'
        original = raw if name.endswith(('.gz','.png')) else gzip.decompress(raw)
        assert sha(original) == item['source_sha256'], 'unchanged original installed bytes'
        if name.endswith(('.json','.json.gz')):
            proof[name] = json.loads(gzip.decompress(raw))
    installed = proof['gentle-command-installed-runtime.json.gz']
    return dict(reference=runtime.inputs(),installed=installed,
                package=proof['gentle-command-nix-packages-retry2.json'],
                failures=[proof['gentle-command-nix-packages.json'],proof['gentle-command-nix-packages-retry1.json']],
                selected=proof['gentle-command-selected-runtime-audit.json'],
                browser=proof['gentle-command-installed-browser.json'],
                browser_runtime=proof['gentle-command-installed-browser-runtime.json'],
                current_frontend={name:sha((ROOT/'web'/name).read_bytes())
                                  for name in installed['profiles']['klem-web-assets']['files']})


def inspect_packages(v):
    package = v['package'];report = v['installed'];reference = v['reference']
    for capture in [package,report,v['browser_runtime']]:
        runtime.terminal(capture,'passed')
        assert capture['head_unchanged'] and capture['index_unchanged'], 'actual frozen installed HEAD/index'
    assert report['source_unchanged'] and v['browser_runtime']['source_unchanged'], 'actual frozen installed source'
    assert package['exit_code'] == 0 and len(package['outputs']) == 4 and set(package['outputs']) == set(report['packages'].values()), 'four actual built Nix packages'
    assert report['captured_head'] == package['head'] == v['browser_runtime']['captured_head'] == 'c8344446a5403bc29d1a6247c26c8594f61968e5', 'one actual package checkpoint'
    assert len(package['frozen_inputs']) == 6503, 'complete6503-source build snapshot'
    assert report['release_rust'] == {'totals':{'passed':1182,'failed':0,'ignored':1},'batches':253}, 'complete actual release Rust suite'
    assert [len(report['profiles'][name]['files']) for name in ['klem','klem-corpus-adapter','klem-web-assets']] == [1123,1123,18], 'complete actual package source profiles'
    for name in ['klem','klem-corpus-adapter']:
        assert report['profiles'][name]['package'] == report['packages'][name], 'actual package source identity'
        for p,digest in reference['closure']['production_inputs'].items():
            relative = str(Path(p).relative_to('/tmp/klem-gentle-command'))
            assert report['profiles'][name]['files'][relative] == digest, 'all44actual compiled Rust/data inputs'
    assert v['current_frontend'] == report['profiles']['klem-web-assets']['files'], 'actual complete current frontend source'
    for name,package_name,program in [('klem','klem','klem'),('adapter','klem-corpus-adapter','klem-corpus-adapter'),('server','klem','klem-web'),('launcher','klem-web','klem-web')]:
        binary = report['binaries'][name]
        assert binary['path'] == report['packages'][package_name]+'/bin/'+program and report['frozen_inputs'][binary['path']] == binary['sha256'], 'actual bound immutable binaries'
    assert all(f['state'] == 'failed' and f['exit_code'] != 0 and f['inputs_unchanged'] and f['head_unchanged'] and f['index_unchanged'] for f in v['failures']), 'both actual failed attempts retained'
    selected = v['selected'];runtime.terminal(selected,'passed')
    assert selected['controls'] == 35 and selected['source_files'] == package['inventory_source_files'] and len(selected['source_files']) == 6461, 'actual selected-source35control proof'


def inspect_installed(v):
    report = v['installed'];reference = v['reference']
    for field, originals in [('source_runs',reference['streams']['runs']),('native_records',reference['native']['records']),('corpus_runs',reference['gold']['runs'])]:
        rows = report[field]
        assert len(rows) == len(originals) == {'source_runs':36,'native_records':47,'corpus_runs':4}[field], 'all original installed comparison policies'
        for row,original in zip(rows,originals,strict=True):
            assert row['original_capture'] == original, 'complete unchanged audited original capture'
            prior_command = original['captures'][1]['command'] if field == 'native_records' else original['command']
            assert row['command'] == [report['binaries']['adapter' if field == 'corpus_runs' else 'klem']['path'],*prior_command[1:]], 'actual installed comparison command'
            stdout = original['captures'][1]['json'] if field == 'native_records' else original['jsonl']
            assert row['exit_code'] == 0 and row['stdout'] == stdout and sha(stdout.encode()) == row['stdout_sha256'], 'every actual installed output byte'
    assert len(report['broad_runs']) == len(reference['broad']['runs']) == 8, 'all eight installed broad streams'
    for row,original in zip(report['broad_runs'],reference['broad']['runs'],strict=True):
        assert row['mode'] == original['mode'] and row['command'] == [report['binaries']['klem']['path'],*original['commands'][1][1:]], 'actual installed broad policy and command'
        assert row['exit_code'] == 0 and row['records'] == original['records'] and row['original_bytes_conserved'], 'complete installed broad frames and spans'
        assert row['stdout_sha256'] == original['after_jsonl_sha256'] and row['source_sha256'] == original['source_sha256'], 'whole installed broad output and original input bytes'
        assert row['changed_frames'] == original['changed_frames'], 'every unchanged original novel hypothesis/context'
    assert sum(r['records'] for r in report['broad_runs']) == 1128312, 'all1128312installedframes'


def inspect_browser(v):
    report = v['browser'];capture = v['browser_runtime'];installed = v['installed'];reference = v['reference']
    assert report['state'] == 'source-bound-gentle-command-installed-browser-passed' and not report['errors'], 'actual error-free installed browser'
    assert capture['command'] == [installed['binaries']['launcher']['path'],'--port','0','--dictionary',next(p for p in capture['frozen_inputs'] if p.endswith('/krdict.db'))], 'actual installed launcher command'
    assert capture['exit_code'] == 0 and capture['server_stopped'] and capture['server_exit_code'] in [0,-2], 'actual owned server stopped cleanly'
    assert report['producer_sha256'] == capture['driver']['sha256'] == sha(capture['driver']['text'].encode()), 'actual complete browser driver'
    for asset in capture['served_assets']:
        assert installed['assets'][asset['path'].removeprefix('/')] == asset['sha256'], 'actual immutable served frontend assets'
    source = reference['source_evidence'];cases = source['suite']['cases']
    assert len(report['responses']) == 2 and [r['encoding'] for r in report['responses']] == ['NFC','NFD'], 'both complete browser encodings'
    exports = [];decisions = [];diagrams = []
    for response in report['responses']:
        encoding = response['encoding'];api = response['api']
        original = next(r for r in reference['streams']['runs'] if (r['family'],r['encoding'],r['mode'],r['cache_bytes']) == ('individual-validity',encoding,'raw',0))
        assert api['records'] == [json.loads(line) for line in original['jsonl'].splitlines()], 'all original browser API frames/spans/candidates'
        assert {entry['id'] for entry in api['grammar']['-으렴']} == {'krdict:79340','krdict:79343'}, 'both exact original browser ending owners'
        for mode in ['raw','headword','compatible']:
            expected = next(r for r in reference['streams']['runs'] if (r['family'],r['encoding'],r['mode'],r['cache_bytes']) == ('individual-validity',encoding,mode,0))
            frames = [json.loads(line) for line in expected['jsonl'].splitlines()]
            exports.append(dict(encoding=encoding,mode=mode,records=frames))
            words = [i for i,f in enumerate(api['records']) if f['kind'] == 'word'];assert len(words) == 23
            for case,index in zip(cases,words,strict=True):
                judgment = case['judgments'][0];token = api['records'][index]
                paths = token['analysis']['analyses'];filtered = frames[index]['analysis']['analyses']
                found = [i for i,path in enumerate(paths) if runtime.matches(path,judgment)]
                assert bool(found) == (judgment['verdict'] == 'required'), 'every original browser required/forbidden judgment'
                key = case['id']+'/'+judgment['id'];offered = [str(i) for i,p in enumerate(paths) if p in filtered]
                decision = report['policyDecisions'][len(decisions)]
                assert (decision['case_id'],decision['encoding'],decision['mode'],decision['record_index']) == (key,encoding,mode,index), 'all138individual browser policy identities/order'
                assert [i for i in decision['offered_indices'] if i.isdigit()] == offered, 'every original offered reading matches actual CLI policy'
                if judgment['verdict'] == 'forbidden':
                    assert decision['verdict'] == 'forbidden' and decision['judgment'] == judgment and decision['raw_analysis_index'] == -1 and not decision['allowed'], 'every forbidden path remains absent'
                else:
                    selected = found[0]
                    assert decision['raw_analysis_index'] == selected and decision['analysis'] == paths[selected] and decision['allowed'] == (str(selected) in offered), 'every required browser path and policy'
                    if decision['allowed']:
                        diagram = report['diagrams'][len(diagrams)]
                        assert (diagram['case_id'],diagram['encoding'],diagram['mode'],diagram['analysis']) == (key,encoding,mode,paths[selected]), 'every individual rendered decomposition'
                        stems = [head[:-1] if kind in ['predicate','auxiliary','copula'] else head for head,kind in zip(judgment['lemmas'],judgment['lemma_kinds'],strict=True)]
                        forms = [stems[0],*judgment['morphemes']] if len(stems)==1 else [stems[0],judgment['morphemes'][0],stems[1],*judgment['morphemes'][1:]]
                        assert diagram['forms'] == forms, 'independent canonical component order'
                        assert not diagram['references'] and all(str(ident) in diagram['source_hint'] for ident in [79340,79343]), 'original ending label attribution'
                        diagrams.append(diagram)
                decisions.append(decision)
    assert report['exports'] == exports and len(exports) == 6, 'six complete exact browser exports'
    assert len(decisions) == len(report['policyDecisions']) == 138 and len(diagrams) == len(report['diagrams']) == 90, 'all original browser policy and diagram totals'
    expected_native = {k:e for entries in source['entries'] for k,e in entries.items()}
    assert report['nativeEntries'] == [dict(id=k,entry=e) for k,e in expected_native.items()] and len(expected_native) == 47, 'all47completeoriginalbrowserNativefields'
    assert not report['spacingDiagrams'], 'unlisted browser spacing scope not invented'


def inspect(v):
    runtime.inspect(v['reference'])
    inspect_packages(v);inspect_installed(v);inspect_browser(v)
    return dict(state='complete-installed-comparison-and-browser-proof-passed',release_rust=1182,
                source_streams=36,native_entries=47,annotated_rows=66570,broad_frames=1128312,
                browser_cases=23,policy_decisions=138,diagrams=90,exports=6,
                private_judgments_promoted=False,contextual_and_independent_review='pending',full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
