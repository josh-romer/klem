"""Rederive current installed package, corpus, private-case and browser evidence."""
import gzip
import json
import re
import unicodedata
from pathlib import Path

import gentle_command_long_runtime_audit as runtime
import gentle_command_long_revision as revision
from formal_volitional_browser_audit import filtered, kept_indices
from gentle_command_runtime_audit import matches, terminal

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_SHA = 'd296070193fea273282763e53abfe7510671b06f61a4455e343992093dc1747d'
HEAD = '3648c0d3502c162819c18f380befa9ace243550d'
SUITES = ['gentle-command-long-validity.json', 'gentle-command-long-novel-validity.json',
          'gentle-command-class-interaction-validity.json', 'gentle-command-validity.json',
          'willingness-question-interaction-validity.json']
NATIVE = ['gentle-command-long-native-entries.json', 'gentle-command-long-boundary-native-entries.json',
          'gentle-command-long-novel-native-entries.json', 'gentle-command-native-entries.json',
          'gentle-command-boundary-native-entries.json']
sha = revision.sha


def inputs():
    raw = (ROOT/'docs/gentle-command-long-installed-proof-archive.json').read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'immutable current installed manifest'
    proof = {}; hashes = {}
    for name, item in json.loads(raw)['files'].items():
        packed = (ROOT/'docs'/item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'immutable installed archive bytes'
        original = packed if name.endswith(('.gz', '.png')) else gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'immutable original installed payload'
        hashes[name] = sha(original)
        proof[name] = json.loads(gzip.decompress(original) if name.endswith('.gz') else original) if name.endswith(('.json', '.json.gz')) else original
    report = proof['gentle-command-long-installed-runtime.json.gz']
    return dict(reference=runtime.inputs(), proof=proof, hashes=hashes,
                package=proof['gentle-command-long-nix-packages-retry2.json'],
                installed=report, browser=proof['gentle-command-long-installed-browser.json'],
                browser_runtime=proof['gentle-command-long-installed-browser-runtime.json'],
                failures=[proof['gentle-command-long-nix-packages.json'], proof['gentle-command-long-nix-packages-retry1.json']],
                suites=[proof[n] for n in SUITES], native=[proof[n] for n in NATIVE],
                labels=proof['grammar-labels.json'],
                current_frontend={name:sha((ROOT/'web'/name).read_bytes()) for name in report['profiles']['klem-web-assets']['files']})


def inspect_packages(v):
    package, installed, browser = v['package'], v['installed'], v['browser_runtime']
    for capture in [package, installed, browser]:
        terminal(capture, 'passed')
        assert capture['head_unchanged'] and capture['index_unchanged'], 'complete actual installed HEAD/index freeze'
    assert installed['source_unchanged'] and browser['source_unchanged'], 'complete actual installed source freeze'
    assert package['head'] == installed['captured_head'] == browser['captured_head'] == HEAD, 'one exact current installed checkpoint'
    assert package['exit_code'] == 0 and len(package['outputs']) == 4 and set(package['outputs']) == set(installed['packages'].values()), 'all four actual current packages'
    assert len(package['frozen_inputs']) == 6674 and len(package['inventory_source_files']) == 6632, 'complete current build and inventory source snapshots'
    assert all(package['frozen_inputs'].get(n) == digest for n,digest in package['inventory_source_files'].items()), 'every selected inventory source byte'
    for suffix, capture in [('', v['failures'][0]), ('-retry1', v['failures'][1]), ('-retry2', package)]:
        producer = v['proof']['build_gentle_command_long_nix_packages'+suffix.replace('-', '_')+'.py']
        assert capture['producer']['text'].encode() == producer and sha(producer) == capture['producer']['sha256'], 'all original build producers retained'
        assert capture['log_sha256'] == v['hashes']['gentle-command-long-nix-packages'+suffix+'.log'], 'all original build logs retained'
        assert capture['head'] == HEAD and capture['head_unchanged'] and capture['index_unchanged'] and capture['inputs_unchanged'], 'all build attempts preserve original source'
    assert all(c['state'] == 'failed' and c['exit_code'] != 0 for c in v['failures']), 'both actual failed build attempts retained'
    assert installed['release_rust'] == {'totals':{'passed':1191,'failed':0,'ignored':1},'batches':254}, 'complete current release Rust suite'
    batches = re.findall(r'test result: (\w+)\. (\d+) passed; (\d+) failed; (\d+) ignored;', v['proof']['gentle-command-long-nix-packages-retry2.log'].decode())
    assert len(batches) == 254 and all(b[0] == 'ok' for b in batches) and [sum(int(b[i]) for b in batches) for i in [1,2,3]] == [1191,0,1], 'actual full release log totals'
    assert [len(installed['profiles'][n]['files']) for n in ['klem','klem-corpus-adapter','klem-web-assets']] == [1137,1137,18], 'complete current package source profiles'
    production = v['reference']['revision']['binding']['production_inputs']
    for name, profile in installed['profiles'].items():
        assert profile['package'] == installed['packages'][name], 'actual source/package identity'
        prefix = 'web/' if name == 'klem-web-assets' else ''
        assert all(package['frozen_inputs'].get(prefix+n) == digest for n,digest in profile['files'].items()), 'every original Nix package source byte'
        if name != 'klem-web-assets':
            assert all(profile['files'].get(n) == digest for n,digest in production.items()), 'all44actual compiled production inputs'
    historical_frontend = installed['profiles']['klem-web-assets']['files']
    current_matches = v['current_frontend'] == historical_frontend
    if not current_matches:
        import friendly_command_gena_revision as gena
        current_matches = gena.accepts_frontend(v['current_frontend'], historical_frontend)
    assert current_matches, 'all18current frontend sources'
    for name, owner, binary in [('klem','klem','klem'),('adapter','klem-corpus-adapter','klem-corpus-adapter'),('server','klem','klem-web'),('launcher','klem-web','klem-web')]:
        value = installed['binaries'][name]
        assert value['path'] == installed['packages'][owner]+'/bin/'+binary and installed['frozen_inputs'][value['path']] == value['sha256'], 'exact immutable installed executables'
    assert installed['producer']['text'].encode() == v['proof']['capture_gentle_command_long_installed_runtime.py'] and sha(installed['producer']['text'].encode()) == installed['producer']['sha256'], 'actual frozen installed producer'


def inspect_installed(v):
    report, reference = v['installed'], v['reference']
    native = {}
    for source in [reference['native'], reference['novel_native']]:
        for row in source['records']:
            if row['id'] in native:
                assert native[row['id']]['complete_original_entry'] == row['complete_original_entry'], 'original complete duplicate Native owner'
            else:
                native[row['id']] = row
    for field, originals in [('source_runs',reference['streams']['runs']), ('native_records',list(native.values())), ('corpus_runs',reference['gold']['runs'])]:
        rows = report[field]
        assert len(rows) == len(originals) == {'source_runs':36,'native_records':48,'corpus_runs':4}[field], 'all current installed original comparison policies'
        for row, original in zip(rows, originals, strict=True):
            assert row['original_capture'] == original, 'every complete unchanged original capture'
            command = original['captures'][1]['command'] if field == 'native_records' else original['command']
            binary = report['binaries']['adapter' if field == 'corpus_runs' else 'klem']['path']
            assert row['command'] == [binary,*command[1:]], 'actual installed original policy command'
            output = original['captures'][1]['json'] if field == 'native_records' else original['jsonl']
            assert row['exit_code'] == 0 and row['stdout'] == output and sha(output.encode()) == row['stdout_sha256'], 'every installed source Native and gold output byte'
    assert len(report['broad_runs']) == len(reference['broad']['runs']) == 8, 'all eight current installed broad policies'
    for row, original in zip(report['broad_runs'], reference['broad']['runs'], strict=True):
        assert row['mode'] == original['mode'] and row['command'] == [report['binaries']['klem']['path'],*original['commands'][1][1:]], 'every actual installed broad policy command'
        assert row['exit_code'] == 0 and row['records'] == original['records'] and row['original_bytes_conserved'], 'every installed broad frame and span'
        assert row['stdout_sha256'] == original['after_jsonl_sha256'] and row['source_sha256'] == original['source_sha256'], 'whole original installed broad input and output'
        assert row['changed_frames'] == original['changed_frames'], 'every original novel occurrence candidate owner and context'
    assert sum(r['records'] for r in report['broad_runs']) == 1128312, 'all1128312installed broad frames'


def frames_from_bytes(text, stdout):
    raw = text.encode(); frames = [json.loads(line) for line in stdout.splitlines()]; cursor = 0
    for frame in frames:
        assert frame['span']['start'] == cursor and raw[cursor:frame['span']['end']].decode() == frame['surface'], 'complete contiguous original UTF8 spans'
        cursor = frame['span']['end']
    assert cursor == len(raw), 'complete original source bytes conserved'
    return frames


def inspect_extra(v):
    report = v['installed']; cases = v['suites'][1]['cases'] + v['suites'][2]['cases']
    assert len(cases) == 11, 'all eight novel and three derived-class cases'
    keys = [(encoding,mode,cache) for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible'] for cache in [0,4096]]
    assert [(r['encoding'],r['mode'],r['cache_bytes']) for r in report['extra_runs']] == keys, 'all12additional Unicode filter cache policies'
    cached = {}; raw_outputs = {}
    for run in report['extra_runs']:
        text = unicodedata.normalize(run['encoding'], ' '.join(c['surface'] for c in cases))
        assert run['input_text'] == text and run['input_sha256'] == sha(text.encode()), 'every original additional case input byte'
        flags = {'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}[run['mode']]
        assert run['command'][:4] == [report['binaries']['klem']['path'],'text','-','--dictionary'] and run['command'][4] in report['frozen_inputs'] and run['command'][5:] == flags+['--cache-bytes',str(run['cache_bytes'])], 'actual additional Unicode filter cache command'
        debug = v['reference']['revision']['binding']['binaries']['klem']['path']
        assert run['reference_command'] == [debug,*run['command'][1:]], 'actual additional compiled reference command'
        assert run['exit_code'] == 0 and sha(run['stdout'].encode()) == run['stdout_sha256'], 'whole actual additional case output'
        frames = frames_from_bytes(text,run['stdout'])
        assert run['records'] == len(frames) and run['original_bytes_conserved'], 'all additional frames conserved'
        key = (run['encoding'],run['mode'])
        assert key not in cached or cached[key] == run['stdout'], 'exact additional cache output parity'
        cached[key] = run['stdout']
        if run['mode'] == 'raw': raw_outputs[run['encoding']] = frames
        assert frames == [filtered(frame,run['mode']) for frame in raw_outputs[run['encoding']]], 'independently filtered complete additional outputs'
        checks = []; offset = 0
        for ordinal, case in enumerate(cases):
            located = [(i,f) for i,f in enumerate(frames) if f['span']['start'] == offset]
            assert len(located) == 1 and located[0][1]['surface'] == unicodedata.normalize(run['encoding'],case['surface']), 'each stable additional judgment occurrence'
            index, frame = located[0]; offset += len(frame['surface'].encode())+1
            for judgment in case['judgments']:
                indices = [i for i,p in enumerate((frame.get('analysis') or {}).get('analyses',[])) if matches(p,judgment)]
                if judgment['verdict'] == 'forbidden': assert not indices, 'both forbidden derived-class paths absent'
                elif run['mode'] == 'raw' or ordinal < 8: assert indices, 'all required additional supported paths'
                checks.append(dict(case_id=case['id'],judgment_id=judgment['id'],verdict=judgment['verdict'],record_index=index,analysis_indices=indices))
        assert checks == run['observations'], 'every independently rederived additional judgment index'


def inspect_browser(v):
    browser, capture, installed = v['browser'], v['browser_runtime'], v['installed']
    assert browser['state'] == 'source-bound-gentle-command-long-installed-browser-passed' and not browser['errors'], 'actual error-free current installed browser'
    assert capture['exit_code'] == 0 and capture['server_stopped'] and capture['server_exit_code'] in [0,-2], 'actual owned browser server stopped cleanly'
    assert capture['command'] == [installed['binaries']['launcher']['path'],'--port','0','--dictionary',next(p for p in capture['frozen_inputs'] if p.endswith('/krdict.db'))], 'actual bound installed browser launcher'
    for field, name in [('driver','gentle-command-long-installed-browser.mjs'),('producer','run_gentle_command_long_installed_browser.py')]:
        assert capture[field]['text'].encode() == v['proof'][name] and sha(v['proof'][name]) == capture[field]['sha256'], 'complete actual browser producers'
    assert browser['producer_sha256'] == capture['driver']['sha256'], 'browser output producer binding'
    assert capture['log_sha256'] == v['hashes']['gentle-command-long-installed-browser-runtime.log'] and capture['result_sha256'] == v['hashes']['gentle-command-long-installed-browser.json'], 'whole actual browser receipt log and output'
    assert capture['served_assets'] and all(installed['assets'][r['path'].removeprefix('/')] == r['sha256'] for r in capture['served_assets']), 'actual immutable served SolidJS assets'
    cases = [{**case,'judgments':[judgment]} for suite in v['suites'] for case in suite['cases'] for judgment in case['judgments']]
    assert len(cases) == 67 and sum(c['judgments'][0]['verdict']=='forbidden' for c in cases) == 23, 'all original67browser judgments'
    assert [r['encoding'] for r in browser['responses']] == ['NFC','NFD'], 'both complete original browser encodings'
    decisions = []; diagrams = []; exports = []
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        text = unicodedata.normalize(encoding,' '.join(c['surface'] for c in cases))
        frames = frames_from_bytes(text, '\n'.join(json.dumps(f,ensure_ascii=False) for f in api['records']))
        words = [i for i,f in enumerate(frames) if f['kind'] == 'word']
        assert len(words) == len(cases), 'every original browser token'
        assert all(name in api['rules'] for name in ['ending.gentle_command_long','ending.gentle_command','ending.willingness_question']), 'all separate current browser grammar rules'
        for mode in ['raw','headword','compatible']:
            exports.append(dict(encoding=encoding,mode=mode,records=[filtered(f,mode) for f in frames]))
            for case,index in zip(cases,words,strict=True):
                frame = frames[index]; judgment = case['judgments'][0]
                assert frame['surface'] == unicodedata.normalize(encoding,case['surface']), 'every original browser case occurrence'
                paths = frame['analysis']['analyses']; found = [i for i,p in enumerate(paths) if matches(p,judgment)]
                assert bool(found) == (judgment['verdict']=='required'), 'every original browser required and forbidden judgment'
                decision = browser['policyDecisions'][len(decisions)]; key = case['id']+'/'+judgment['id']
                assert (decision['case_id'],decision['encoding'],decision['mode'],decision['record_index']) == (key,encoding,mode,index), 'every browser policy identity and order'
                offered = [str(i) for i in kept_indices(frame,mode)]
                assert [i for i in decision['offered_indices'] if i.isdigit()] == offered, 'every independently filtered browser option'
                if judgment['verdict'] == 'forbidden':
                    assert decision['verdict']=='forbidden' and decision['judgment']==judgment and decision['raw_analysis_index']==-1 and not decision['allowed'], 'all138forbidden browser choices absent'
                else:
                    selected = found[0]; path = paths[selected]
                    assert decision['raw_analysis_index']==selected and decision['analysis']==path and decision['allowed']==(str(selected) in offered), 'every required current browser policy'
                    if decision['allowed']:
                        diagram = browser['diagrams'][len(diagrams)]
                        assert (diagram['case_id'],diagram['encoding'],diagram['mode'],diagram['analysis']) == (key,encoding,mode,path), 'every actual current rendered path'
                        stems = [head[:-1] if kind in ['predicate','auxiliary','copula'] else head for head,kind in zip(judgment['lemmas'],judgment['lemma_kinds'],strict=True)]
                        parts = [form[:-1] if kind=='suffix' and form in ['답다','되다','하다'] else form for form,kind in zip(judgment['morphemes'],judgment['morpheme_kinds'],strict=True)]
                        forms = [stems[0],*parts] if len(stems)==1 else [stems[0],parts[0],stems[1],*parts[1:]] if judgment['lemma_kinds'][1]=='auxiliary' else [*stems,*parts]
                        if len(stems)==1 and judgment['lemmas'][0].endswith('하다'): forms[1]=re.sub('^어','여',re.sub('^었','였',forms[1]))
                        assert diagram['forms']==forms, 'independently ordered canonical browser components'
                        last = path['morphemes'][-1]; label = v['labels'][last['form'] if last['kind']=='particle' else '-'+last['form']]
                        assert not diagram['references'] and all(str(s['id']) in diagram['source_hint'] for s in label['sources']), 'all individual original browser grammar attributions'
                        diagrams.append(diagram)
                decisions.append(decision)
    assert browser['exports']==exports and len(exports)==6, 'six independently filtered complete browser exports'
    assert len(decisions)==len(browser['policyDecisions'])==402 and len(diagrams)==len(browser['diagrams'])==264, 'all402decisions264diagrams accounted'
    native = {}
    for entries in v['native']: native.update(entries)
    assert browser['nativeEntries']==[dict(id=i,entry=e) for i,e in native.items()] and len(native)==62, 'all62complete original Native browser owners'
    assert not browser['spacingDiagrams'], 'no invented browser spacing verification'


def inspect(v):
    runtime.inspect(v['reference'])
    inspect_packages(v); inspect_installed(v); inspect_extra(v); inspect_browser(v)
    return dict(state='current-long-installed-and-browser-audit-passed',release_rust=1191,
                source_policies=36,native_cli_owners=48,annotated_rows=66570,broad_frames=1128312,
                extra_cases=11,extra_policies=12,browser_cases=67,policy_decisions=402,
                diagrams=264,exports=6,native_browser_owners=62,
                novel_proposals_precede_runtime=False,other_raw_novel_hypotheses_unjudged=11,
                shared_judgments_changed=False,full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
