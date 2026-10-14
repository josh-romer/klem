"""Independently rederive every actual Sena browser reading and corpus choice."""
import json
import signal
import unicodedata

import friendly_hortative_sena_runtime_audit as runtime
from formal_volitional_browser_audit import filtered, kept_indices

ROOT = runtime.ROOT
sha = runtime.sha
MANIFEST_SHA = '9eece5cad10db1354a6874a10577929ace60ecb6b5f304fc137d0910b025e583'
CORPUS_SHA = '7e996be5cdd1f4f560f1ebedd8c9454c17d17d40c6bf76fe8870a2f5aea7c245'


def inputs():
    assert MANIFEST_SHA is not None, 'pinned actual browser manifest'
    proof, hashes, originals = runtime.archive('friendly-hortative-sena-browser-proof-archive.json', MANIFEST_SHA)
    corpus, corpus_hashes, corpus_originals = runtime.archive('friendly-hortative-sena-corpus-regression-proof-archive.json', CORPUS_SHA)
    v = runtime.inputs()
    return dict(runtime=v, proof=proof, hashes=hashes, originals=originals,
                corpus=corpus['friendly-hortative-sena-corpus-regression-retry.json.gz'],
                labels=json.loads((ROOT/'web/src/grammar-labels.json').read_bytes()))


def word_records(records):
    return [{k:r[k] for k in ['surface','kind','analysis','dictionary']} for r in records if r['kind']=='word']


def spans(records, text):
    raw = text.encode(); cursor = 0
    for record in records:
        assert record['span']['start'] == cursor and raw[cursor:record['span']['end']].decode() == record['surface'], 'complete original browser byte spans'
        cursor = record['span']['end']
    assert cursor == len(raw), 'whole browser input covered'


def forms(judgment):
    stems = [head[:-1] if kind in ['predicate','auxiliary','copula'] and head.endswith('다') else head
             for head,kind in zip(judgment['lemmas'],judgment['lemma_kinds'],strict=True)]
    morphs = [form[:-1] if kind=='suffix' and form in ['답다','되다','하다'] else form
              for form,kind in zip(judgment['morphemes'],judgment['morpheme_kinds'],strict=True)]
    if len(stems)==1:
        result = [stems[0],*morphs]
        if judgment['lemmas'][0].endswith('하다'):
            if result[1].startswith('었'): result[1] = '였'+result[1][1:]
            elif result[1].startswith('어'): result[1] = '여'+result[1][1:]
        return result
    if judgment['lemma_kinds'][1]=='auxiliary': return [stems[0],morphs[0],stems[1],*morphs[1:]]
    return [*stems,*morphs]


def inspect(v):
    bound = v['runtime']; runtime.inspect_binding(bound)
    proof = v['proof']; browser = proof['friendly-hortative-sena-browser.json']
    report = proof['friendly-hortative-sena-browser-runtime-retry1.json']
    frontend = proof['friendly-hortative-sena-frontend-build.json']
    for receipt in [report,frontend]: runtime.terminal(receipt)
    assert report['exit_code']==0 and report['source_unchanged'] and report['server_stopped'] and report['server_exit_code'] in [0,-signal.SIGINT], 'owned browser server stopped'
    assert browser['state']=='source-bound-friendly-hortative-sena-browser-passed' and not browser['errors'], 'actual passed browser capture'
    assert report['source_inputs']==frontend['frozen_inputs'] and len(report['source_inputs'])==7179, 'same complete7179 source snapshot'
    assert report['head']==frontend['head']=='3b3d9246da3b7833a5ac0f2cd7c92b343cd73b2a' and report['index_sha256']==frontend['index_sha256'], 'actual captured source revision'
    assert report['production_inputs']==bound['current'] and all(report['source_inputs'][p]==d for p,d in bound['current'].items()), 'all44 current browser production inputs'
    assert {'web/'+p:d for p,d in frontend['frontend_inputs'].items()}==bound['frontend']=={'web/'+p:d for p,d in report['frontend_inputs'].items()}, 'all18 current browser frontend inputs'
    assert frontend['exit_code']==0 and frontend['log_sha256']==v['hashes']['friendly-hortative-sena-frontend-build.log'], 'actual frontend build log'
    assert report['log_sha256']==v['hashes']['friendly-hortative-sena-browser-runtime-retry1.log'] and report['result_sha256']==v['hashes']['friendly-hortative-sena-browser.json'], 'actual browser result log binding'
    for receipt,name,key in [(report,'run_friendly_hortative_sena_browser_retry1.py','producer'),(report,'friendly-hortative-sena-browser.mjs','driver'),(frontend,'build_friendly_hortative_sena_frontend.py','producer')]:
        assert receipt[key]==dict(text=v['originals'][name].decode(),sha256=v['hashes'][name]), 'actual original browser producers'
    assert browser['producer_sha256']==v['hashes']['friendly-hortative-sena-browser.mjs'], 'actual browser driver binding'
    assert 'job.send_signal(signal.SIGINT)' in report['producer']['text'] and 'job.wait(timeout=20)' in report['producer']['text'], 'explicit bounded owned shutdown'
    binding = bound['binding']
    paths = {b['path']:b['sha256'] for b in binding['binaries'].values()} | binding['protected_parent_binaries']
    assert len(paths)==6 and all(report['frozen_inputs'][p]==d for p,d in paths.items()), 'all six frozen executable fingerprints'
    assert report['command'][0]==binding['binaries']['server']['path'] and report['command'][1:3]==['--port','0'] and '--assets' in report['command'] and '--dictionary' in report['command'], 'bound actual browser server command'
    assert report['assets']==frontend['assets'] and len(report['served_assets'])==2, 'complete production browser assets'
    for asset in report['served_assets']:
        assert frontend['assets'][asset['path'].lstrip('/')]==asset['sha256'], 'actual served asset bytes'
    assert [r['encoding'] for r in browser['responses']]==['NFC','NFD'], 'both original browser Unicode responses'
    policies = [(encoding,mode) for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in browser['exports']]==policies+policies and all(r.get('family')=='original-corpus' for r in browser['exports'][6:]), 'all twelve original browser exports'
    cases = [dict(c,id=c['id']+'/'+c['judgments'][0].get('id','path')) for c in bound['source']['suite']['cases']]
    decisions=[]; diagrams=[]
    owner = bound['source']['entries']['krdict:78469']
    for response in browser['responses']:
        encoding,api = response['encoding'],response['api']
        capture = next(c for c in bound['captures']['captures'] if c['family']=='preauthored-25-proposals' and c['normalization']==encoding and c['mode']=='all' and c['cache_bytes']==0)
        assert word_records(api['records'])==word_records(capture['frames']), 'every complete browser word equals original bound CLI'
        spans(api['records'],unicodedata.normalize(encoding,' '.join(c['surface'] for c in cases)))
        assert api['grammar']['-세나']==[{k:owner[k] for k in ['headword','homonym','id','pos']}] and runtime.RULE in api['rules'], 'own attributed Sena browser grammar'
        words = [(i,r) for i,r in enumerate(api['records']) if r['kind']=='word']
        assert len(words)==25 and len(api['breakdowns'])==len(api['records']), 'all original browser case records'
        for mode in ['raw','headword','compatible']:
            exported = next(r for r in browser['exports'][:6] if (r['encoding'],r['mode'])==(encoding,mode))
            assert exported['records']==[filtered(r,mode) for r in api['records']], 'independently filtered entire browser export'
            for case,(record_index,record) in zip(cases,words,strict=True):
                assert record['surface']==unicodedata.normalize(encoding,case['surface']), 'original browser surface identity'
                judgment=case['judgments'][0]; paths=record['analysis']['analyses']
                indices=[i for i,path in enumerate(paths) if runtime.source.typed_match(path,judgment)]
                assert bool(indices)==(judgment['verdict']=='required'), 'independent preauthored required and forbidden path'
                index=indices[0] if indices else -1; kept=kept_indices(record,mode)
                decision=dict(case_id=case['id'],encoding=encoding,mode=mode,record_index=record_index,
                              raw_analysis_index=index,allowed=index in kept,offered_indices=[str(i) for i in kept] if kept else [''])
                if judgment['verdict']=='forbidden':
                    decision.update(verdict='forbidden',judgment=judgment);decisions.append(decision);continue
                decision['analysis']=paths[index]
                assert runtime.RULE in paths[index]['rules'], 'own Sena reading attribution'
                if not kept: decision['empty_message']='No matching reading'
                decisions.append(decision)
                if index not in kept: continue
                shown=forms(judgment)
                assert len(api['breakdowns'][record_index][index])==len(shown), 'complete ordered browser components'
                diagrams.append(dict(case_id=case['id'],encoding=encoding,mode=mode,analysis=paths[index],forms=shown,references=[]))
    assert browser['policyDecisions']==decisions and len(decisions)==report['decisions']==150, 'all150 independently rederived browser decisions'
    assert sum(d.get('verdict')=='forbidden' for d in decisions)==report['forbidden']==36, 'all36 browser forbidden exclusions'
    assert len(browser['diagrams'])==len(diagrams)==report['diagrams']==114, 'all114 required browser diagrams'
    for actual,expected in zip(browser['diagrams'],diagrams,strict=True):
        assert {k:actual[k] for k in expected}==expected, 'every independent displayed form and order'
        assert '78469' in actual['source_hint'] and '-세나' in actual['source_hint'], 'own displayed Sena label sources'
    corpus=v['corpus'];item=corpus['original_observation']['items'][0]
    assert corpus['state']=='original-KAIST-noun-reading-preserved-and-unmatched-Sena-hypothesis-filtered' and item['id']=='friendly-hortative-sena-kaist-MH2_0180-s63-5' and item['contextual_verdict']=='unjudged', 'original unjudged corpus occurrence'
    assert [(r['encoding'],r['mode']) for r in browser['corpusDecisions']]==policies and report['corpus_decisions']==6, 'all six original-corpus policies'
    for ordinal,decision in enumerate(browser['corpusDecisions']):
        encoding,mode=decision['encoding'],decision['mode'];api=decision['api']
        raw=next(c for c in corpus['captures'] if (c['normalization'],c['mode'],c['cache_bytes'])==(encoding,'raw',0))
        selected=next(c for c in corpus['captures'] if (c['normalization'],c['mode'],c['cache_bytes'])==(encoding,mode,0))
        assert api['records']==raw['after']['frames'], 'every complete original-corpus browser record equals bound CLI'
        spans(api['records'],raw['input'])
        assert browser['exports'][ordinal+6]['records']==selected['after']['frames']==[filtered(r,mode) for r in api['records']], 'whole original-corpus filtered export'
        index=next(i for i,r in enumerate(api['records']) if r['kind']=='word' and unicodedata.normalize('NFC',r['surface'])=='중세나')
        record=api['records'][index];paths=record['analysis']['analyses']
        noun=next(i for i,p in enumerate(paths) if p['lemmas']==[dict(text='중세',kind='nominal')] and p['morphemes']==[dict(form='나',kind='particle')])
        hypothesis=next(i for i,p in enumerate(paths) if runtime.RULE in p['rules'])
        assert paths[hypothesis]==item['new_unjudged_paths'][0] and record['dictionary']['readings'][hypothesis]['status']=='unknown' and record['dictionary']['readings'][noun]['status']=='compatible', 'original noun and unjudged unknown hypothesis'
        kept=kept_indices(record,mode)
        assert decision==dict(case_id=item['id'],encoding=encoding,mode=mode,record_index=index,api=api,
            original_gold_row=item['original_gold_row'],nominal_analysis_index=noun,hypothetical_analysis_index=hypothesis,
            offered_indices=[str(i) for i in kept],forms=['중세','나'],hypothesis_contextual_verdict='unjudged'), 'every independent original-corpus dropdown and gold observation'
        assert noun in kept and (hypothesis in kept)==(mode=='raw'), 'corpus unmatched hypothesis filter exclusion'
    native=bound['source']['entries']|corpus['complete_native_entries']
    assert len(native)==37 and len(browser['nativeEntries'])==report['native_entries']==37 and {r['id']:r['entry'] for r in browser['nativeEntries']}==native, 'all37 complete original browser Native entries'
    failure=proof['friendly-hortative-sena-browser-runtime.json']
    assert failure['state']=='failed' and 'Operation not permitted' in failure['error'] and failure['server_stopped'] and failure['server_exit_code']==1 and failure['log_sha256'] is None, 'original port-denied failure preserved'
    assert failure['producer']==dict(text=v['originals']['run_friendly_hortative_sena_browser.py'].decode(),sha256=v['hashes']['run_friendly_hortative_sena_browser.py']), 'original failed browser producer'
    for path,digest in report['screenshots'].items():
        assert v['hashes'][path.rsplit('/',1)[-1]]==digest, 'complete original screenshot bytes'
    assert proof['friendly-hortative-sena-browser-visual-observation.json']['screenshots']==report['screenshots'], 'actual bounded screenshot inspection'
    assert not browser['spacingDiagrams'] and report['exports']==12, 'explicit bounded browser scope'
    return dict(browser_choices=150,required_diagrams=114,forbidden_exclusions=36,original_corpus_choices=6,
                exact_exports=12,complete_native_entries=37,binary_evidence=bound['binary_evidence'],
                context_register_independent_review='pending',full_coverage_complete=False)


if __name__=='__main__':
    print(inspect(inputs()))
