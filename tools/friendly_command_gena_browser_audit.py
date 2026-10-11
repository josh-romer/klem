"""Rederive every recorded Gena browser choice against complete CLI records."""
import gzip
import json
import signal
import unicodedata

import friendly_command_gena_revision as revision
import friendly_command_gena_runtime_audit as runtime_audit
from formal_volitional_browser_audit import filtered, kept_indices
from gentle_command_runtime_audit import matches

ROOT = revision.ROOT
sha = revision.sha


def inputs():
    v = runtime_audit.inputs()
    proof = v['proof']
    captured = proof['friendly-command-gena-browser-runtime-retry1.json']['source_inputs']
    v['current_frontend'] = {p:sha((ROOT / p).read_bytes()) for p in captured if p.startswith('web/') and not p.startswith('web/tests/')}
    v['labels'] = json.loads((ROOT / 'web/src/grammar-labels.json').read_bytes())
    return v


def inspect(v):
    proof = v['proof']; browser = proof['friendly-command-gena-browser.json']
    report = proof['friendly-command-gena-browser-runtime-retry1.json']
    frontend = proof['friendly-command-gena-frontend-build.json']
    revision.inspect(v['revision'])
    runtime_audit.bound(v,report,'passed',production=False)
    assert all(report['source_inputs'][p] == d for p,d in v['revision']['binding']['production_inputs'].items()), 'complete browser production closure'
    revision.terminal(frontend,'passed')
    assert browser['state'] == 'source-bound-friendly-command-gena-browser-passed' and not browser['errors'], 'actual successful browser capture'
    assert report['exit_code'] == 0 and report['server_stopped'] and report['server_exit_code'] in (0,-signal.SIGINT) and report['source_unchanged'], 'owned browser server stopped with inputs unchanged'
    driver = proof['friendly-command-gena-browser.mjs']
    supervisor = proof['run_friendly_command_gena_browser_retry1.py']
    assert sha(driver) == browser['producer_sha256'] == report['driver']['sha256'] and report['driver']['text'].encode() == driver, 'actual browser driver binding'
    assert report['producer']['text'].encode() == supervisor and 'job.send_signal(signal.SIGINT)' in supervisor.decode(), 'actual explicit owned server shutdown producer'
    assert report['log_sha256'] == v['hashes']['friendly-command-gena-browser-runtime-retry1.log'] and report['result_sha256'] == v['hashes']['friendly-command-gena-browser.json'], 'complete original browser result/log binding'
    server = v['revision']['binding']['binaries']['klem-web']
    assert report['command'][0] == server['path'] and report['frozen_inputs'][server['path']] == server['sha256'], 'actual compiled browser server'
    assert frontend['exit_code'] == 0 and frontend['log_sha256'] == v['hashes']['friendly-command-gena-frontend-build.log'], 'actual SolidJS production build/log'
    prefix = revision.CAPTURE_ROOT + '/web/'
    original = {p.removeprefix(revision.CAPTURE_ROOT+'/'):d for p,d in frontend['frozen_inputs'].items() if p.startswith(prefix)}
    captured = {p:d for p,d in report['source_inputs'].items() if p.startswith('web/') and not p.startswith('web/tests/')}
    assert len(original) == 14 and all(captured[p] == d for p,d in original.items()), 'all14 declared frontend build inputs'
    assert len(captured) == 18 and v['current_frontend'] == captured, 'all18 current SolidJS source inputs'
    for asset in report['served_assets']:
        assert frontend['assets'][asset['path'].lstrip('/')] == asset['sha256'], 'exact served production asset bytes'
    assert [r['encoding'] for r in browser['responses']] == ['NFC','NFD'], 'both original browser Unicode policies'
    assert [(r['encoding'],r['mode']) for r in browser['exports']] == [(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']], 'all six browser exports'
    cases = [dict(c,id=c['id']+'/'+c['judgments'][0]['id']) for c in v['source']['suite']['cases']]
    decisions = []; diagrams = []
    for response in browser['responses']:
        encoding, api = response['encoding'], response['api']
        capture = next(c for c in v['captures']['captures'] if c['family'] == 'preauthored-24-proposals' and c['normalization'] == encoding and c['mode'] == 'all' and c['cache_bytes'] == 0)
        project = lambda records:[{k:f[k] for k in ['surface','kind','analysis','dictionary']} for f in records if f['kind']=='word']
        # The source-policy CLI input contains newlines; the UI joins the same
        # cases with spaces. Compare complete word records, then independently
        # verify every API byte span against the actual browser input.
        assert project(api['records']) == project(capture['frames']), 'every complete browser record equals actual CLI'
        raw = unicodedata.normalize(encoding,' '.join(c['surface'] for c in cases)).encode(); cursor = 0
        for frame in api['records']:
            assert frame['span']['start'] == cursor and raw[cursor:frame['span']['end']].decode() == frame['surface'], 'complete original browser byte spans'
            cursor = frame['span']['end']
        assert cursor == len(raw), 'whole original browser input covered'
        owner = v['source']['entries']['krdict:66968']
        assert api['grammar']['-게나'] == [{k:owner[k] for k in ['headword','homonym','id','pos']}] and runtime_audit.RULE in api['rules'], 'own attributed browser label and rule'
        words = [(i,r) for i,r in enumerate(api['records']) if r['kind'] == 'word']
        assert len(words) == len(cases) == 24 and len(api['breakdowns']) == len(api['records']), 'all24 browser cases and ordered breakdown records'
        for mode in ['raw','headword','compatible']:
            exported = next(r for r in browser['exports'] if r['encoding'] == encoding and r['mode'] == mode)
            assert exported['records'] == [filtered(r,mode) for r in api['records']], 'every independently filtered browser export'
            for case,(record_index,record) in zip(cases,words,strict=True):
                assert record['surface'] == unicodedata.normalize(encoding,case['surface']), 'original browser case occurrence'
                judgment = case['judgments'][0]; paths = record['analysis']['analyses']
                indices = [i for i,p in enumerate(paths) if matches(p,judgment)]
                assert bool(indices) == (judgment['verdict'] == 'required'), 'every independent browser required/forbidden path'
                index = indices[0] if indices else -1; kept = kept_indices(record,mode)
                offered = [str(i) for i in kept] if kept else ['']
                decision = dict(case_id=case['id'],encoding=encoding,mode=mode,record_index=record_index,raw_analysis_index=index,allowed=index in kept,offered_indices=offered)
                if judgment['verdict'] == 'forbidden':
                    decision.update(verdict='forbidden',judgment=judgment); decisions.append(decision); continue
                decision['analysis'] = paths[index]
                if not decision['allowed'] and not kept: decision['empty_message'] = 'No matching reading'
                decisions.append(decision)
                if not decision['allowed']: continue
                stems = [head[:-1] if role in ['predicate','auxiliary','copula'] and head.endswith('다') else head for head,role in zip(judgment['lemmas'],judgment['lemma_kinds'],strict=True)]
                morphs = [form[:-1] if kind == 'suffix' and form in ['답다','되다','하다'] else form for form,kind in zip(judgment['morphemes'],judgment['morpheme_kinds'],strict=True)]
                forms = [stems[0],*morphs] if len(stems)==1 else [stems[0],morphs[0],stems[1],*morphs[1:]]
                order = api['breakdowns'][record_index][index]
                assert len(order) == len(forms), 'complete original ordered browser components'
                diagrams.append(dict(case_id=case['id'],encoding=encoding,mode=mode,analysis=paths[index],forms=forms,references=[]))
    assert browser['policyDecisions'] == decisions and len(decisions) == report['decisions'] == 144, 'all144 independently rederived browser choices'
    assert len(browser['diagrams']) == len(diagrams) == report['diagrams'] == 102, 'all102 independently required browser diagrams'
    for actual,expected in zip(browser['diagrams'],diagrams,strict=True):
        assert {k:actual[k] for k in expected} == expected, 'every independent displayed form/order/reference'
        assert '-게나' in actual['source_hint'] and '66968' in actual['source_hint'], 'own ending source attribution'
    assert not browser['spacingDiagrams'] and report['exports'] == 6, 'bounded browser export and spacing scope'
    native = browser['nativeEntries']
    assert len(native) == report['native_entries'] == 31 and {r['id']:r['entry'] for r in native} == v['source']['entries'], 'all31 complete original browser Native entries'
    failure = proof['friendly-command-gena-browser-launch-failure-friendly-command-gena-browser-runtime.json.gz']
    revision.terminal(failure,'failed')
    failed_log = gzip.decompress(proof['friendly-command-gena-browser-launch-failure-friendly-command-gena-browser-runtime.log.gz'])
    assert failure['exit_code'] != 0 and failure['server_stopped'] and sha(failed_log) == failure['log_sha256'] and b'Socket path too long:' in failed_log, 'original browser launch failure retained'
    return dict(browser_choices=144,required_diagrams=102,forbidden_exclusions=42,
                exact_exports=6,complete_native_entries=31,owned_server_stopped=True,
                context_register_independent_review='pending',full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
