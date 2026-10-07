"""Verify actual main and independent packaged contrast-ending replay records."""
import argparse
import json
import math

from declarative_contrast_audit import ROOT, matches, producer, read, sha


def verify_cli(report):
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/declarative_contrast_replay.py').read_text()
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert report['cli_sha256']==report['frozen_inputs'][report['cli']]
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
    expected = read(ROOT/'docs/declarative-contrast-prototype-source-replay.json.gz')
    suite = read(ROOT/'tests/fixtures/declarative-contrast-validity.json')
    assert len(report['runs'])==len(expected['runs'])==6
    judgments=[]
    for actual,old in zip(report['runs'],expected['runs'],strict=True):
        assert (actual['encoding'],actual['mode'])==(old['encoding'],old['mode'])
        assert actual['sha256']==old['after_sha256'] and actual['records']==506
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
        for case in suite['cases']:
            for judgment in case['judgments']:
                judgments.append({'case':case['id'],'judgment':judgment['id'],'encoding':actual['encoding'],
                                  'mode':actual['mode'],'verdict':judgment['verdict'],'present':judgment['verdict']=='required'})
    assert report['judgments']==judgments and len(judgments)==252
    broad=read(ROOT/'docs/declarative-contrast-prototype-broad.json.gz')
    assert len(report['broad'])==len(broad['comparisons'])==8
    for actual,old in zip(report['broad'],broad['comparisons'],strict=True):
        assert all(actual[k]==old[k] for k in ['source','source_sha256','mode','records'])
        assert actual['sha256']==old['after_jsonl_sha256']
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
    corpus=read(ROOT/'docs/declarative-contrast-prototype-corpora.json.gz')
    assert report['corpora']=={'unique_surfaces':32096,'original_gold_rows':66570,
                              'exact_prototype_word_analyses':True,'word_analyses_sha256':corpus['after_words_sha256']}
    return {'source_frames':3036,'individual_mode_judgments':252,'broad_frames':1128312,'corpus_words':32096}


def verify_adapter(report):
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/declarative_contrast_adapter_replay.py').read_text()
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert report['adapter_sha256']==report['frozen_inputs'][report['adapter']]
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
    expected=read(ROOT/'docs/declarative-contrast-prototype-adapter.json.gz')
    assert len(report['runs'])==len(expected['runs'])==4
    for actual,old in zip(report['runs'],expected['runs'],strict=True):
        assert all(actual[k]==old[k] for k in ['corpus','partition','source','source_sha256'])
        stream=next(s for s in old['streams'] if s['mode']=='after')
        assert actual['sha256']==stream['sha256'] and actual['rows']==stream['rows']
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
        assert actual['all_rows_independently_bound_to_word_analyses'] is True
    assert sum(r['rows'] for r in report['runs'])==66570
    return 66570


def without_elapsed(response):
    response=dict(response)
    value=response.pop('elapsed_ms')
    assert type(value) in (int,float) and math.isfinite(value) and value>=0
    return response


def browser_semantics(report):
    return [dict(row,after=without_elapsed(row['after'])) for row in report['responses']]


def verify_browser(report,cli):
    assert report['cli_sha256']==cli['cli_sha256']
    assert report['producer_sha256']==sha((ROOT/'web/tests/declarative-contrast.mjs').read_bytes())
    assert report['catalog_sha256']==sha((ROOT/'web/src/grammar-labels.json').read_bytes())
    assert report['errors']==[]
    assert len(report['diagrams'])==64 and len(report['particleDiagrams'])==48
    assert len(report['exports'])==6 and len(report['modeJudgments'])==252
    assert len(report['opened'])==6 and len(report['native'])==115
    source=read(ROOT/'docs/declarative-contrast-prototype-source-replay.json.gz')
    assert [r['encoding'] for r in report['responses']]==['NFC','NFD']
    for response in report['responses']:
        stream=next(r for r in source['runs'] if r['encoding']==response['encoding'] and r['mode']=='raw')
        assert response['after']['records']==list(map(json.loads,stream['jsonl'].splitlines()))
    suite=read(ROOT/'tests/fixtures/declarative-contrast-validity.json')
    expected_judgments=[]
    assert [(r['encoding'],r['mode']) for r in report['exports']]==[(encoding,mode) for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible']]
    for export in report['exports']:
        records={r['analysis']['normalized']:r for r in export['records'] if r.get('analysis')}
        for case in suite['cases']:
            for judgment in case['judgments']:
                present=any(matches(p,judgment) for p in records.get(case['surface'],{}).get('analysis',{}).get('analyses',[]))
                assert present==(judgment['verdict']=='required')
                expected_judgments.append({'encoding':export['encoding'],'mode':export['mode'],'case_id':case['id'],
                                          'judgment_id':judgment['id'],'present':present,'verdict':judgment['verdict']})
    assert report['modeJudgments']==expected_judgments
    cases={c['id']:c for c in suite['cases']}
    for diagram in report['diagrams']:
        judgment=next(j for j in cases[diagram['case_id']]['judgments'] if j['id']==diagram['judgment_id'])
        assert judgment['verdict']=='required' and matches(diagram['analysis'],judgment)
        assert diagram['pieces'][0]['label']=='Although / but (connective)'
    owners=read(ROOT/'docs/declarative-contrast-broad-owner-preparation.json.gz')['complete_native_entries']
    assert {r['id']:r['response']['entry'] for r in report['native']}==owners
    main=read(ROOT/'docs/declarative-contrast-main-browser.json')
    assert browser_semantics(report)==browser_semantics(main)
    for key in ['exports','diagrams','particleDiagrams','native','opened','modeJudgments','errors']:
        assert report[key]==main[key],key
    return {'whole_diagrams':64,'particle_diagrams':48,'exports':6,'native_entries':115}


def verify_launcher(package,auxiliary,browser,launcher):
    producer(launcher)
    assert launcher['state']=='passed' and launcher['exit_code']==launcher['help_exit_code']==0
    output=next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    assets=next(p for p in package['outputs'] if p.endswith('-klem-web-assets-0.1.0'))+'/share/klem-web'
    wrapper=next(p for p in auxiliary['outputs'] if p.endswith('-klem-web'))+'/bin/klem-web'
    assert launcher['launcher']==wrapper and launcher['cli']==output+'/bin/klem' and launcher['assets']==assets
    assert sha(launcher['launcher_text'].encode())==launcher['launcher_sha256']
    assert [line for line in launcher['launcher_text'].splitlines() if line.startswith('exec ')]==[
        f'exec {output}/bin/klem-web --assets {assets} "$@"']
    assert len(launcher['asset_checks'])==2 and {r['path'].rsplit('.',1)[-1] for r in launcher['asset_checks']}=={'js','css'}
    assert all(r['bytes']>0 and len(r['sha256'])==64 for r in launcher['asset_checks'])
    assert [r['encoding'] for r in launcher['responses']]==['NFC','NFD']
    for actual,baseline in zip(launcher['responses'],browser['responses'],strict=True):
        assert actual['request']==baseline['request']
        assert without_elapsed(actual['after'])==without_elapsed(baseline['after'])
    return {'source_api_frames':1012,'packaged_assets':2,'help_exit_code':0}


def verify_package(package,cli,adapter,browser,auxiliary,launcher):
    assert package['state']=='passed' and package['exit_code']==0 and package['snapshot_unchanged'] is True
    assert len(package['snapshot']['files'])==915
    for path,record in package['snapshot']['files'].items():
        assert sha((ROOT/path).read_bytes())==record['sha256'],path
    output=next(p for p in package['outputs'] if p.endswith('-klem-0.1.0'))
    assert cli['cli']==output+'/bin/klem'
    producer(auxiliary)
    assert auxiliary['state']=='passed' and auxiliary['exit_code']==0 and auxiliary['snapshot_unchanged'] is True
    assert auxiliary['main_package_receipt_sha256']==sha((ROOT/'docs/declarative-contrast-package-nix.json').read_bytes())
    assert auxiliary['source']==package['source_profiles']['klem'] and auxiliary['source_files']==898
    assert auxiliary['snapshot']==package['snapshot']
    adapter_output=next(p for p in auxiliary['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))
    assert adapter['adapter']==adapter_output+'/bin/klem-corpus-adapter'
    return {'cli':verify_cli(cli),'adapter_rows':verify_adapter(adapter),'browser':verify_browser(browser,cli),
            'launcher':verify_launcher(package,auxiliary,browser,launcher)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--main-only',action='store_true')
    args=parser.parse_args()
    cli=read(ROOT/'docs/declarative-contrast-main-cli-replay-retry1.json')
    result={'main_cli':verify_cli(cli),'main_adapter_rows':verify_adapter(read(ROOT/'docs/declarative-contrast-main-adapter-replay.json.gz')),
            'main_browser':verify_browser(read(ROOT/'docs/declarative-contrast-main-browser.json'),cli)}
    if not args.main_only:
        result['package']=verify_package(read(ROOT/'docs/declarative-contrast-package-nix.json'),
                                        read(ROOT/'docs/declarative-contrast-packaged-cli-replay.json'),
                                        read(ROOT/'docs/declarative-contrast-packaged-adapter-replay.json.gz'),
                                        read(ROOT/'docs/declarative-contrast-packaged-browser.json'),
                                        read(ROOT/'docs/declarative-contrast-auxiliary-nix.json'),
                                        read(ROOT/'docs/declarative-contrast-web-launcher.json'))
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
