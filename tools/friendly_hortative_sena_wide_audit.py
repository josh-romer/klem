"""Independently audit all preserved Sena corpus, gold, broad and Native evidence."""
import gzip
import json
from pathlib import Path

import friendly_command_gena_revision as gena
import friendly_hortative_sena_runtime_audit as runtime
from native_lmf import entry

ROOT = runtime.ROOT
sha = runtime.sha
MANIFEST_SHA = 'bb4cb1f2cfa778ba8eab65d02d398e26c89809b578e3c3ff268d74be9a5e4621'
ANNOTATIONS_SHA = '12b9e453369bd11bd4c963bda66eaa69e438aff5c9d47999151445d4a2d220a3'


def inputs():
    path = ROOT / 'docs/friendly-hortative-sena-wide-proof-archive.json'
    raw = path.read_bytes()
    assert sha(raw) == MANIFEST_SHA, 'immutable whole wide evidence manifest'
    manifest = json.loads(raw)
    names = {
        'friendly-hortative-sena-wide-comparisons.json',
        'friendly-hortative-sena-cohorts.json.gz', 'friendly-hortative-sena-corpora.json.gz',
        'friendly-hortative-sena-broad.json.gz', 'friendly-hortative-sena-history.json',
        'friendly-hortative-sena-corpus-observations.json', 'friendly-hortative-sena-extra-native.json.gz',
        'friendly-hortative-sena-extra-native-retry.json',
        'friendly-hortative-sena-extra-native-original-observation.json'}
    values, hashes, producers = {}, {}, {}
    for name, item in manifest['files'].items():
        packed = (ROOT / 'docs' / item['path']).read_bytes()
        assert sha(packed) == item['archive_sha256'], 'packed whole original evidence'
        original = gzip.decompress(packed)
        assert sha(original) == item['source_sha256'], 'whole original evidence bytes'
        hashes[name] = sha(original)
        if name in names:
            values[name] = json.loads(gzip.decompress(original) if name.endswith('.gz') else original)
        elif name.endswith('.py'):
            producers[name] = original
    assert set(values) == names and len(hashes) == 25, 'all25 full original artifacts'
    parents, _ = gena.archive({'friendly-command-gena-broad.json.gz'})
    raw = (ROOT / 'docs/literary-question-geona-prototype-corpora.json.gz').read_bytes()
    assert sha(raw) == ANNOTATIONS_SHA, 'immutable original converted annotations'
    prefix = 'friendly-hortative-sena-'
    return dict(runtime=runtime.inputs(), hashes=hashes, producers=producers, manifest=manifest,
                wide=values[prefix+'wide-comparisons.json'], cohorts=values[prefix+'cohorts.json.gz'],
                gold=values[prefix+'corpora.json.gz'], broad=values[prefix+'broad.json.gz'],
                history=values[prefix+'history.json'], observation=values[prefix+'corpus-observations.json'],
                native=values[prefix+'extra-native.json.gz'], retry=values[prefix+'extra-native-retry.json'],
                stopped=values[prefix+'extra-native-original-observation.json'],
                parent_broad=parents['friendly-command-gena-broad.json.gz'],
                annotations=json.loads(gzip.decompress(raw)))


def producer(v, report, name):
    assert report['producer'] == dict(text=v['producers'][name].decode(), sha256=sha(v['producers'][name])), 'whole original producer binding'


def bound(v, report, state, binaries):
    assert report['state'] == state and report['inputs_unchanged'], 'actual terminal unchanged wide capture'
    binding = v['runtime']['binding']
    frozen = report['frozen_inputs']
    for name in binaries:
        binary = binding['binaries'][name]
        assert frozen[binary['path']] == binary['sha256'], 'exact Source-bound current executable'
    for path, digest in binding['production_inputs'].items():
        assert frozen['/home/josh/projects/klem/.direnv/friendly-hortative-sena/'+path] == digest, 'all44 capture production inputs'
    assert frozen['/home/josh/projects/klem/.direnv/friendly-hortative-sena-prepared/friendly-hortative-sena-complete-runtime-binding.json'] == v['runtime']['hashes']['friendly-hortative-sena-complete-runtime-binding.json'], 'immutable current build receipt'


def inspect_receipts(v):
    runtime.inspect_binding(v['runtime'])
    wide, retry = v['wide'], v['retry']
    for report in [wide, retry]:
        runtime.terminal(report)
        assert report['head'] == '268db8356b8a5ae8a952d86252b5048c6bc95bd6', 'exact wide capture Source revision'
        assert len(report['frozen_inputs']) == 7067, 'whole7067 capture Source snapshot'
        assert all(report['frozen_inputs'][p] == digest for p, digest in v['runtime']['binding']['production_inputs'].items()), 'whole capture production Source'
    assert retry['frozen_inputs'] == wide['frozen_inputs'] and retry['index_sha256'] == wide['index_sha256'], 'same whole Source and index for Native retry'
    assert wide['external_inputs_unchanged'] and wide['protected_current_binaries_unchanged'], 'original producers and protected binaries unchanged'
    expected = ['capture_friendly_hortative_sena_'+n+'.py' for n in ['cohorts','corpora','broad']]
    assert wide['results'] == [dict(command=['python3','/home/josh/projects/klem/.direnv/friendly-hortative-sena-prepared/'+n],exit_code=0) for n in expected], 'all three actual complete comparison commands'
    assert wide['log_sha256'] == v['hashes']['friendly-hortative-sena-wide-comparisons.log'], 'whole original wide log'
    assert retry['log_sha256'] == v['hashes']['friendly-hortative-sena-extra-native-retry.log'], 'whole original Native retry log'
    assert retry['result_sha256'] == v['hashes']['friendly-hortative-sena-extra-native.json.gz'] and retry['exit_code'] == 0 and retry['collector_unchanged'], 'actual completed Native retry'
    assert retry['collector_sha256'] == v['hashes']['capture_friendly_hortative_sena_extra_native_retry.py'], 'corrected collector binding'
    producer(v, wide, 'validate_friendly_hortative_sena_wide_comparisons.py')
    producer(v, retry, 'validate_friendly_hortative_sena_extra_native_retry.py')
    stopped = v['stopped']
    assert stopped['state'] == 'prior-handle-missing-no-terminal-receipt' and stopped['session_id'] == 27297, 'original stopped attempt retained'
    assert stopped['exit_code'] is None and not stopped['terminal_output_available'] and not stopped['expected_output_exists'], 'unknown original outcome cannot become passed'
    assert stopped['producer_sha256'] == v['hashes']['capture_friendly_hortative_sena_extra_native.py'], 'whole original collector retained'


def inspect_cohorts(v):
    report = v['cohorts']
    bound(v, report, 'complete-original-corpus-history-comparison-passed', ['klem'])
    producer(v, report, 'capture_friendly_hortative_sena_cohorts.py')
    parent = v['runtime']['source']['installed']
    assert [(r['family'],r['surfaces']) for r in report['runs']] == [('corpus',32096),('history',21406)], 'every53502 original cohort word'
    changes = []
    for run, old_run in zip(report['runs'], parent['cohort_runs'], strict=True):
        before, after = run['captures']
        assert before['binary'] == parent['binaries']['klem']['path'] and before['words'] == old_run['words'], 'every immutable actual parent word'
        assert after['binary'] == v['runtime']['binding']['binaries']['klem']['path'], 'actual Source-bound cohort binary'
        assert set(after['words']) == set(before['words']) and len(after['words']) == run['surfaces'], 'whole word set and counts'
        changed = []
        for surface, old in before['words'].items():
            new = after['words'][surface]
            additions = runtime.word_additions(old, new)
            if old != new:
                changed.append(surface)
                changes.append(dict(id='friendly-hortative-sena-cohort-'+run['family']+'-'+str(len(changed)),family=run['family'],surface=surface,before=old,after=new,new_paths=additions,contextual_verdict='unjudged',independent_review='pending'))
        assert run['changed_words'] == changed, 'every individual changed word recorded'
    assert changes == report['individual_changed_words'], 'complete individual word records and unjudged status'
    assert len(changes) == 1 and changes[0]['surface'] == '중세나' and changes[0]['family'] == 'corpus' and len(changes[0]['new_paths']) == 1, 'one corpus hypothesis and zero historical changes'


def inspect_gold(v):
    report = v['gold']
    bound(v, report, 'complete-friendly-hortative-sena-annotated-comparison-passed', ['adapter'])
    producer(v, report, 'capture_friendly_hortative_sena_corpora.py')
    old_runs = v['runtime']['source']['installed']['corpus_runs']
    partitions = v['annotations']['corpora']
    assert [(r['corpus'],r['partition'],r['rows']) for r in report['runs']] == [('kaist','dev',22220),('kaist','test',24490),('gsd','dev',9989),('gsd','test',9871)], 'all66570 original annotated rows'
    assert report['individual_changed_rows'] == [], 'zero annotated row changes'
    for run, previous, partition in zip(report['runs'], old_runs, partitions, strict=True):
        old = [json.loads(line) for line in previous['stdout'].splitlines()]
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]
        assert run['exit_code'] == 0 and len(rows) == run['rows']+1, 'complete actual gold command output'
        assert run['before_command'] == previous['command'] and run['command'] == [v['runtime']['binding']['binaries']['adapter']['path'],run['corpus'],run['source']], 'actual bound gold adapter commands'
        assert sha(run['jsonl'].encode()) == run['stdout_sha256'] and run['before_stdout_sha256'] == previous['stdout_sha256'], 'whole gold stdout fingerprints'
        assert run['source'] == partition['source'] and run['source_sha256'] == partition['source_sha256'] == rows[0]['input_sha256'], 'unchanged original annotated input'
        assert rows[1:] == old[1:], 'every full original gold row and recovery'
        assert [{k:r[k] for k in ['id','surface','expected']} for r in rows[1:]] == [{k:r[k] for k in ['id','surface','expected']} for r in partition['original_converted_rows']], 'all independently preserved source annotations'
        delta = {k:dict(before=old[0].get(k),after=value) for k,value in rows[0].items() if old[0].get(k) != value}
        assert delta == run['summary_changes'], 'all gold summary changes independently derived'
        assert set(delta) == ({'mean_candidates'} if run['corpus']=='kaist' and run['partition']=='test' else set()), 'only one mean-candidate delta; all recall/metadata exact'
        if delta:
            assert delta['mean_candidates'] == dict(before=6.009473254389547,after=6.009514087382605), 'exact observed candidate mean delta'


def inspect_broad(v):
    report = v['broad']
    bound(v, report, 'complete-friendly-hortative-sena-broad-comparison-passed', ['klem'])
    producer(v, report, 'capture_friendly_hortative_sena_broad.py')
    parent = v['runtime']['source']['installed']
    assert len(report['runs']) == 8 and sum(r['records'] for r in report['runs']) == 1128312, 'all1128312 frames and eight original modes'
    for run, old, captured in zip(report['runs'],parent['broad_runs'],v['parent_broad']['runs'],strict=True):
        assert (run['mode'],run['records'],run['source_sha256']) == (old['mode'],old['records'],old['source_sha256']), 'every original mode/frame/input'
        assert run['before_jsonl_sha256'] == run['after_jsonl_sha256'] == old['stdout_sha256'], 'every full original output byte unchanged'
        assert run['exit_codes'] == [0,0] and run['original_bytes_conserved'], 'actual complete broad commands and byte conservation'
        expected = [old['command'],[v['runtime']['binding']['binaries']['klem']['path'],*old['command'][1:]]]
        assert run['commands'] == expected, 'actual full filter/spacing commands'
        assert run['original_paths_preserved'] == captured['original_paths_preserved']+captured['new_family_paths'], 'all original candidate occurrences counted'
        assert run['new_family_paths'] == 0 and run['changed_frames'] == [], 'zero broad candidate/assessment/spacing changes'


def inspect_observation(v):
    history, observation = v['history'],v['observation']
    assert history['inputs_unchanged'] and not history['observations_precede_runtime'], 'post-runtime historical observation scope'
    assert history['source_files_sha256'] == {} and history['historical_fixture_words_changed'] == 0 and not history['historical_allowances_assigned'], 'zero historical witnesses and no allowance'
    assert history['cohort_scope']==dict(words=53502,corpus_words=32096,history_words=21406), 'complete unchanged historical cohort scope'
    assert history['cohort_sha256'] == observation['cohort_sha256'] == v['hashes']['friendly-hortative-sena-cohorts.json.gz'], 'same whole actual cohort observation'
    assert observation['gold_sha256'] == v['hashes']['friendly-hortative-sena-corpora.json.gz'], 'same whole actual gold observation'
    assert len(observation['items']) == 1 and not observation['observations_precede_runtime'] and not observation['shared_cases_reviews_changed'], 'sole unjudged post-runtime observation'
    producer(v, history, 'capture_friendly_hortative_sena_history.py')
    producer(v, observation, 'capture_friendly_hortative_sena_corpus_observation.py')
    item = observation['items'][0]
    assert item['id'] == 'friendly-hortative-sena-kaist-MH2_0180-s63-5' and item['contextual_verdict']=='unjudged' and item['independent_korean_review']=='pending', 'stable original case identity and honest judgment'
    change = v['cohorts']['individual_changed_words'][0]
    assert item['complete_original_word_analysis']==change['before'] and item['current_word_analysis']==change['after'] and item['new_unjudged_paths']==change['new_paths'], 'every whole original and current case record'
    fields = item['complete_original_token_fields']
    assert len(fields)==10 and fields[:5]==['5','중세나','중세+나','CCONJ','ncn+jcj'], 'all original token fields and noun annotation'
    assert '\t'.join(fields) in item['complete_original_conllu_block'] and '# sent_id = MH2_0180-s63\n' in item['complete_original_conllu_block'], 'complete original sentence block'
    gold = next(r for r in v['gold']['runs'] if (r['corpus'],r['partition'])==('kaist','test'))
    row = next(r for r in map(json.loads,gold['jsonl'].splitlines()) if r.get('id')=='id:MH2_0180-s63/5')
    assert item['original_gold_row']==row==dict(id='id:MH2_0180-s63/5',surface='중세나',expected=['중세'],matched=True,recovered=1,recovered_sets=[[0]]), 'exact unchanged original gold row'
    assert observation['source']==gold['source'] and observation['source_sha256']==gold['source_sha256'], 'original sentence source provenance'
    assert observation['historical_fixture_words_changed']==0 and not observation['historical_allowances_assigned'], 'corpus observation cannot create historical allowance'


def inspect_native(v):
    report = v['native']
    producer(v, report, 'capture_friendly_hortative_sena_extra_native_retry.py')
    assert all(report[k] for k in ['source_unchanged','head_unchanged','index_unchanged','inputs_unchanged']), 'actual frozen Native closure'
    assert report['captured_head']==v['wide']['head'] and report['source_inputs']==v['wide']['frozen_inputs'], 'Native collection from same whole Source'
    paths = [p['analysis'] for c in v['runtime']['captures']['captures'] for p in c['new_paths']]
    paths += [p for change in v['cohorts']['individual_changed_words'] for p in change['new_paths']]
    heads = sorted({lemma['text'] for p in paths for lemma in p['lemmas']})
    assert heads==report['selected_heads'] and len(heads)==71, 'every actual new candidate head including unmatched hypotheses'
    primary = v['runtime']['source']['entries']
    closure = json.loads(gzip.decompress(v['runtime']['source']['originals']['friendly-hortative-sena-original-native-closure-reviewed.json.gz']))
    assert report['source_exports']==closure['source_exports'] and len(report['source_exports'])==11, 'same11 complete original dictionary exports'
    owners = {n:entry(e) for n,e in report['original_lmf'].items()}
    assert owners==report['complete_native_entries'] and len(owners)==41, 'all41 complete Native owners independently projected'
    assert all(e==primary[n] for n,e in owners.items() if n in primary), 'every original primary same-head owner field'
    assert report['additional_native_entries']=={n:e for n,e in owners.items() if n not in primary} and len(report['additional_native_entries'])==9, 'all nine additional full owners'
    assert set(report['actual_headword_queries'])==set(heads), 'all71 actual headword queries'
    for head, query in report['actual_headword_queries'].items():
        assert query['exit_code']==0 and query['stderr']=='' and query['command']==[v['runtime']['binding']['binaries']['klem']['path'],'dict','lookup','/home/josh/projects/klem/.direnv/dictionary-restoration/krdict.db',head], 'actual current lookup command'
        response = json.loads(query['stdout'])
        expected = [{k:e[k] for k in ['id','headword','homonym','pos']} for n,e in sorted(owners.items()) if e['headword']==head]
        assert response['entries']==expected, 'every same-head Native homonym and unmatched result'
        assert response['source']=='krdict' and response['fingerprint']=='837de0c1deea1a090c9d9687a9a1fee1425f3dedaaf1c93cc0fcc93870bb7234', 'original dictionary identity and fingerprint'
    assert set(report['actual_complete_entry_responses'])==set(owners), 'all actual complete Native entry responses'
    for n, response in report['actual_complete_entry_responses'].items():
        assert response['exit_code']==0 and response['stderr']=='' and response['command']==[v['runtime']['binding']['binaries']['klem']['path'],'dict','entry','/home/josh/projects/klem/.direnv/dictionary-restoration/krdict.db',n], 'actual complete Native command'
        assert json.loads(response['stdout'])==response['response'] and response['response']['entry']==owners[n], 'every actual Native field preserved'
    assert len(heads)-len({e['headword'] for e in owners.values()})==48, 'all48 unmatched hypothetical heads'
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending', 'Native attribution is not contextual certification'


def inspect(v):
    for check in [inspect_receipts,inspect_cohorts,inspect_gold,inspect_broad,inspect_observation,inspect_native]:
        check(v)
    return dict(cohort_words=53502,annotated_rows=66570,broad_frames=1128312,
                unjudged_corpus_additions=1,historical_fixture_changes=0,native_heads=71,
                native_owners=41,unmatched_heads=48,full_coverage_complete=False)


if __name__=='__main__':
    print(inspect(inputs()))
