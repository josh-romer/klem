"""Validate actual current CLI, adapter and browser evidence for ostensible reason."""
import argparse
import gzip
import json
import math
import re
import unicodedata

from ostensible_reason_audit import ROOT, matches, producer, read, sha


def conditional_observations(runs, matrix):
    observations=[]
    assert [(r['encoding'],r['mode']) for r in runs]==[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    for run in runs:
        records=run['records'] if isinstance(run['records'],list) else list(map(json.loads,run['jsonl'].splitlines()))
        by_word={r['analysis']['normalized']:r for r in records if r.get('analysis')}
        for case in matrix['cases']:
            row=by_word[case['surface']]
            targets=[{'analysis':a,'assessment':row['dictionary']['readings'][i]}
                     for i,a in enumerate(row['analysis']['analyses']) if matches(a,case['expected'])]
            assert bool(targets)==case['expected_presence'][run['mode']]
            for target in targets:
                for native in case['expected_entry_statuses']:
                    entry=next(e for e in target['assessment']['lemmas'][native['lemma']]['entries'] if e['id']==native['id'])
                    assert entry['status']==native['status']
            observations.append({'case':case['id'],'judgment':case['judgment_id'],'encoding':run['encoding'],'mode':run['mode'],
                                 'present':bool(targets),'expected_presence':case['expected_presence'][run['mode']],
                                 'targets':targets,'contextual_verdict':'unjudged','independent_review':'pending'})
    assert len(observations)==72
    return observations


def verify_cli(report):
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/ostensible_reason_replay.py').read_text()
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert report['cli_sha256']==report['frozen_inputs'][report['cli']]
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
    expected=read(ROOT/'docs/ostensible-reason-prototype-source-replay.json.gz')
    suite=read(ROOT/'tests/fixtures/ostensible-reason-validity.json')
    assert len(report['runs'])==len(expected['runs'])==6
    judgments=[]
    for actual,old in zip(report['runs'],expected['runs'],strict=True):
        assert (actual['encoding'],actual['mode'])==(old['encoding'],old['mode'])
        assert actual['sha256']==old['after_sha256'] and actual['records']==233
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
        for case in suite['cases']:
            for j in case['judgments']:
                judgments.append({'case':case['id'],'judgment':j['id'],'encoding':actual['encoding'],'mode':actual['mode'],
                                  'verdict':j['verdict'],'present':j['verdict']=='required'})
    assert report['judgments']==judgments and len(judgments)==156
    matrix=read(ROOT/'tests/fixtures/ostensible-reason-mode-scope.json')
    for run in report['conditional_runs']:
        assert run['exit_code']==0 and run['records']==len(run['jsonl'].splitlines())
        assert sha(run['jsonl'].encode())==run['sha256'] and sha(run['input'].encode())==run['input_sha256']
    assert report['conditional_observations']==conditional_observations(report['conditional_runs'],matrix)
    broad=read(ROOT/'docs/ostensible-reason-prototype-broad.json.gz')
    assert len(report['broad'])==len(broad['comparisons'])==8
    for actual,old in zip(report['broad'],broad['comparisons'],strict=True):
        assert all(actual[k]==old[k] for k in ['source','source_sha256','mode','records'])
        assert actual['sha256']==old['after_jsonl_sha256']
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
    corpus=read(ROOT/'docs/ostensible-reason-prototype-corpora.json.gz')
    assert report['corpora']=={'unique_surfaces':32096,'original_gold_rows':66570,'exact_prototype_word_analyses':True,
                              'word_analyses_sha256':corpus['after_words_sha256']}
    return {'source_frames':1398,'individual_mode_judgments':156,'conditional_mode_judgments':72,'broad_frames':1128312,'corpus_words':32096}


def verify_mode_preservation(report, cli):
    producer(report)
    assert report['producer']['text'] == (ROOT/'tools/capture_ostensible_reason_modes.py').read_text()
    assert report['state'] == 'passed' and report['exit_code'] == 0 and report['inputs_unchanged'] is True
    assert report['cli_sha256'] == cli['cli_sha256'] == report['frozen_inputs'][report['cli']]
    assert report['before_cli_sha256'] == report['frozen_inputs'][report['before_cli']]
    prior = read(ROOT/'docs/declarative-contrast-packaged-cli-replay.json')
    assert report['before_cli'] == prior['cli'] and report['before_cli_sha256'] == prior['cli_sha256']
    matrix = read(ROOT/'tests/fixtures/ostensible-reason-mode-scope.json')
    cases = {case['surface']:case for case in matrix['cases']}
    assert len(report['runs']) == len(cli['conditional_runs']) == 6
    additions, owners = [], set()
    for run, current in zip(report['runs'],cli['conditional_runs'],strict=True):
        assert (run['encoding'],run['mode']) == (current['encoding'],current['mode'])
        text = unicodedata.normalize(run['encoding'],' '.join(c['surface'] for c in matrix['cases']))
        assert run['input'] == current['input'] == text
        assert run['input_sha256'] == sha(text.encode())
        assert run['exit_codes'] == [0,0] and run['records'] == 23
        assert run['after_jsonl'] == current['jsonl'] and run['after_sha256'] == current['sha256']
        assert sha(run['before_jsonl'].encode()) == run['before_sha256']
        before = list(map(json.loads,run['before_jsonl'].splitlines()))
        after = list(map(json.loads,run['after_jsonl'].splitlines()))
        assert len(before) == len(after) == 23
        cursor = 0
        for index,(old,new) in enumerate(zip(before,after,strict=True)):
            assert new['span']['start'] == cursor
            assert text.encode()[cursor:new['span']['end']].decode() == new['surface']
            cursor = new['span']['end']
            assert {k:v for k,v in old.items() if k not in ['analysis','dictionary']} == {k:v for k,v in new.items() if k not in ['analysis','dictionary']}
            if old.get('analysis') is None:
                assert old == new
                continue
            old_paths, new_paths = old['analysis']['analyses'], new['analysis']['analyses']
            assert [a for a in new_paths if a in old_paths] == old_paths
            assert old['dictionary']['source'] == new['dictionary']['source'] and old['dictionary']['fingerprint'] == new['dictionary']['fingerprint']
            for analysis, assessment in zip(old_paths,old['dictionary']['readings'],strict=True):
                assert new['dictionary']['readings'][new_paths.index(analysis)] == assessment
            assert all(entry in new['dictionary']['lemmas'] for entry in old['dictionary']['lemmas'])
            case = cases[new['analysis']['normalized']]
            for number,analysis in enumerate(new_paths):
                if analysis in old_paths:
                    continue
                assert 'ending.ostensible_reason' in analysis['rules']
                assessment = new['dictionary']['readings'][number]
                owners.update(e['id'] for slot in assessment['lemmas'] for e in slot['entries'])
                identity = sha(json.dumps([case['id'],run['encoding'],run['mode'],index,analysis],ensure_ascii=False,sort_keys=True).encode())[:24]
                additions.append({'id':'ostensible-reason-mode-addition-'+identity,'case':case['id'],'encoding':run['encoding'],'mode':run['mode'],
                                  'frame_index':index,'surface':new['surface'],'span':new['span'],'analysis':analysis,'assessment':assessment,
                                  'matches_conditional_target':matches(analysis,case['expected']),
                                  'conditional_assertion_refs':[{'case':case['id'],'judgment':case['judgment_id']}],
                                  'structural_verdict':'unjudged','contextual_verdict':'unjudged','independent_review':'pending'})
        assert cursor == len(text.encode())
    assert additions == report['individual_additions'] and len(additions) == 120
    assert len({item['id'] for item in additions}) == 120
    assert sorted(owners) == report['matched_native_owner_ids'] and len(owners) == 19
    prepared = read(ROOT/'docs/ostensible-reason-boundary-owner-preparation.json.gz')['complete_native_entries']
    assert owners <= prepared.keys()
    return {'frames':138,'individually_unjudged_additions':120,'matched_native_owners':19}


def verify_adapter(report):
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/ostensible_reason_adapter_replay.py').read_text()
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert report['adapter_sha256']==report['frozen_inputs'][report['adapter']]
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
    expected_path=ROOT/'docs/declarative-contrast-prototype-adapter.json.gz'
    assert report['original_adapter_capture_sha256']==sha(expected_path.read_bytes())
    expected=read(expected_path)
    assert len(report['runs'])==len(expected['runs'])==4
    for actual,old in zip(report['runs'],expected['runs'],strict=True):
        assert all(actual[k]==old[k] for k in ['corpus','partition','source','source_sha256'])
        stream=next(s for s in old['streams'] if s['mode']=='after')
        assert actual['sha256']==stream['sha256'] and actual['rows']==stream['rows']
        assert actual['exit_code']==0 and actual['exact_prior_adapter_output'] is True
        assert actual['all_rows_independently_bound_to_word_analyses'] is True
    assert sum(r['rows'] for r in report['runs'])==66570
    return 66570


def without_elapsed(response):
    response=dict(response);value=response.pop('elapsed_ms')
    assert type(value) in (int,float) and math.isfinite(value) and value>=0
    return response


def verify_browser(report,cli):
    assert report['cli_sha256']==cli['cli_sha256']
    assert report['producer_sha256']==sha((ROOT/'web/tests/ostensible-reason.mjs').read_bytes())
    assert report['catalog_sha256']==sha((ROOT/'web/src/grammar-labels.json').read_bytes())
    assert report['errors']==[]
    assert len(report['diagrams'])==42 and report['particleDiagrams']==[]
    assert len(report['exports'])==6 and len(report['modeJudgments'])==156
    assert len(report['conditionalExports'])==6 and len(report['conditionalDiagrams'])==22
    assert len(report['conditionalModeJudgments'])==72 and len(report['opened'])==3 and len(report['native'])==91
    source=read(ROOT/'docs/ostensible-reason-prototype-source-replay.json.gz')
    assert [r['encoding'] for r in report['responses']]==['NFC','NFD']
    for response in report['responses']:
        without_elapsed(response['after'])
        run=next(r for r in source['runs'] if r['encoding']==response['encoding'] and r['mode']=='raw')
        assert response['after']['records']==list(map(json.loads,run['jsonl'].splitlines()))
    suite=read(ROOT/'tests/fixtures/ostensible-reason-validity.json')
    keys=[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in report['exports']]==keys
    judgments=[]
    for export in report['exports']:
        records={r['analysis']['normalized']:r for r in export['records'] if r.get('analysis')}
        for case in suite['cases']:
            for j in case['judgments']:
                present=any(matches(p,j) for p in records[case['surface']]['analysis']['analyses'])
                assert present==(j['verdict']=='required')
                judgments.append({'encoding':export['encoding'],'mode':export['mode'],'case_id':case['id'],
                                  'judgment_id':j['id'],'present':present,'verdict':j['verdict']})
    assert report['modeJudgments']==judgments
    matrix=read(ROOT/'tests/fixtures/ostensible-reason-mode-scope.json')
    conditional=conditional_observations(report['conditionalExports'],matrix)
    expected=[{'encoding':r['encoding'],'mode':r['mode'],'case_id':r['case'],'judgment_id':r['judgment'],
               'present':r['present'],'expected_presence':r['expected_presence'],'contextual_verdict':'unjudged'} for r in conditional]
    assert report['conditionalModeJudgments']==expected
    assert conditional==cli['conditional_observations']
    normal={c['id']:c for c in suite['cases']};special={c['id']:c for c in matrix['cases']}
    for kind,cases in [('diagrams',normal),('conditionalDiagrams',special)]:
        for diagram in report[kind]:
            case=cases[diagram['case_id']]
            if kind=='diagrams':
                judgment=next(j for j in case['judgments'] if j['id']==diagram['judgment_id'])
                assert judgment['verdict']=='required'
            else:judgment=case['expected']
            assert matches(diagram['analysis'],judgment)
            assert len(diagram['pieces'])==1 and diagram['pieces'][0]['label']=='Claimed reason (disapproving)'
    owners=read(ROOT/'docs/ostensible-reason-boundary-owner-preparation.json.gz')['complete_native_entries']
    assert {r['id']:r['response']['entry'] for r in report['native']}==owners
    main_path=ROOT/'docs/ostensible-reason-main-browser.json'
    if main_path.exists():
        main=read(main_path)
        assert [dict(r,after=without_elapsed(r['after'])) for r in report['responses']]==[dict(r,after=without_elapsed(r['after'])) for r in main['responses']]
        for key in ['exports','diagrams','conditionalExports','conditionalDiagrams','conditionalModeJudgments','native','opened','modeJudgments','errors']:
            assert report[key]==main[key],key
    return {'source_api_frames':466,'source_diagrams':42,'conditional_diagrams':22,'exports':12,'native_entries':91,'individual_mode_judgments':228}


def verify_package(package,cli,adapter,browser,launcher):
    producer(package)
    assert package['producer']['text']==(ROOT/'tools/capture_ostensible_reason_packages.py').read_text()
    assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
    assert package['command']==['nix','build','--offline','--option','build-dir',
                               '/var/tmp/klem-degree-expectation-nix-build','--cores','4','--max-jobs','2',
                               '--no-link','--print-out-paths','-L',
                               '.#checks.x86_64-linux.klem','.#checks.x86_64-linux.web-assets',
                               '.#checks.x86_64-linux.corpus-adapter']
    log=gzip.decompress((ROOT/'docs/ostensible-reason-package-nix.log.gz').read_bytes())
    assert sha(log)==package['log_sha256']
    batches=re.findall(rb'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored;',log)
    assert len(batches)==219 and [sum(int(row[i]) for row in batches) for i in range(3)]==[1043,0,1]
    assert package['source_profiles']['klem']==package['source_profiles']['corpus-adapter']
    assert set(package['source_profiles'])=={'klem','web-assets','corpus-adapter'}
    assert all(re.fullmatch(r'/nix/store/[a-z0-9]{32}-source',p) for p in package['source_profiles'].values())
    assert len(package['snapshot']['files'])==924
    for path,record in package['snapshot']['files'].items():
        raw=(ROOT/path).read_bytes()
        assert len(raw)==record['bytes'] and sha(raw)==record['sha256'],path
    assert len(package['outputs'])==3 and len(set(package['outputs']))==3
    output=next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    assets=next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0'))+'/share/klem-web'
    adapter_output=next(p for p in package['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))
    assert cli['cli']==output+'/bin/klem' and adapter['adapter']==adapter_output+'/bin/klem-corpus-adapter'
    producer(launcher)
    assert launcher['producer']['text']==(ROOT/'tools/capture_ostensible_reason_web.py').read_text()
    assert launcher['state']=='passed' and launcher['exit_code']==launcher['help_exit_code']==0
    assert launcher['inputs_unchanged'] is True and launcher['server_stopped'] is True
    assert launcher['server_exit_code'] in [-2,130]
    assert launcher['package_sha256']==sha((ROOT/'docs/ostensible-reason-package-nix.json').read_bytes())
    assert launcher['browser_sha256']==sha((ROOT/'docs/ostensible-reason-packaged-browser.json').read_bytes())
    assert launcher['cli']==cli['cli'] and launcher['cli_sha256']==cli['cli_sha256']
    assert launcher['server']==output+'/bin/klem-web' and launcher['assets']==assets
    assert re.fullmatch(r'/nix/store/[a-z0-9]{32}-klem-web/bin/klem-web',launcher['launcher'])
    assert launcher['launcher_sha256']==sha(launcher['launcher_text'].encode())
    assert [line for line in launcher['launcher_text'].splitlines() if line.startswith('exec ')]==[
        f'exec {output}/bin/klem-web --assets {assets} "$@"']
    for key in ['cli','server','launcher']:
        assert launcher[key+'_sha256']==launcher['frozen_inputs'][launcher[key]]
    assert len(launcher['asset_checks'])==2
    assert {r['path'].rsplit('.',1)[-1] for r in launcher['asset_checks']}=={'js','css'}
    assert all(r['bytes']>0 and re.fullmatch(r'[a-f0-9]{64}',r['sha256']) for r in launcher['asset_checks'])
    assert [r['encoding'] for r in launcher['responses']]==['NFC','NFD']
    for actual,baseline in zip(launcher['responses'],browser['responses'],strict=True):
        assert actual['request']==baseline['request']
        assert without_elapsed(actual['after'])==without_elapsed(baseline['after'])
    return {'cli':verify_cli(cli),'adapter_rows':verify_adapter(adapter),'browser':verify_browser(browser,cli),
            'launcher':{'source_api_frames':466,'packaged_assets':2,'owned_server_stopped':True},
            'release_tests':{'passed':1043,'failed':0,'ignored':1,'batches':219}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli-report',type=str,default='docs/ostensible-reason-main-cli-replay-retry1.json')
    parser.add_argument('--adapter-report',type=str,default='docs/ostensible-reason-main-adapter-replay.json.gz')
    parser.add_argument('--browser-report',type=str,default='docs/ostensible-reason-main-browser.json')
    parser.add_argument('--package',action='store_true',help='Also verify the independently executed Nix packages')
    args=parser.parse_args()
    cli=read(ROOT/args.cli_report)
    result={'cli':verify_cli(cli),'adapter_rows':verify_adapter(read(ROOT/args.adapter_report)),
            'browser':verify_browser(read(ROOT/args.browser_report),cli),
            'mode_preservation':verify_mode_preservation(read(ROOT/'docs/ostensible-reason-main-mode-preservation.json.gz'),cli)}
    if args.package:
        result['package']=verify_package(read(ROOT/'docs/ostensible-reason-package-nix.json'),
                                        read(ROOT/'docs/ostensible-reason-packaged-cli-replay.json'),
                                        read(ROOT/'docs/ostensible-reason-packaged-adapter-replay.json.gz'),
                                        read(ROOT/'docs/ostensible-reason-packaged-browser.json'),
                                        read(ROOT/'docs/ostensible-reason-packaged-web-launcher.json'))
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
