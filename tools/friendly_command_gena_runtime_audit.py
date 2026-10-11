"""Rederive -게나 captures, preserving each original hypothesis and gold row."""
import gzip
import json
import unicodedata

import friendly_command_gena_revision as revision
import friendly_command_gena_source_audit as source_audit
import gentle_command_long_revision as parent_revision
import gentle_command_runtime_audit as prior_audit
from native_lmf import entry

ROOT = revision.ROOT
sha = revision.sha
RULE = 'ending.friendly_command.gena'


def inputs():
    proof, hashes = revision.archive()
    parents, _ = parent_revision.archive('gentle-command-long-runtime-proof-archive.json',
        parent_revision.MANIFEST_SHA, {'gentle-command-long-cohorts-retry1.json.gz',
                                     'gentle-command-long-broad.json.gz',
                                     'gentle-command-long-corpora.json.gz'})
    source = source_audit.inputs()
    originals = {}
    for key in ['broad_inputs', 'annotations']:
        name, digest = prior_audit.PARENTS[key]
        raw = (ROOT / 'docs' / name).read_bytes()
        assert sha(raw) == digest, 'immutable original broad/gold inputs'
        originals[key] = json.loads(gzip.decompress(raw))
    return dict(proof=proof, hashes=hashes, revision=revision.inputs(proof, hashes), source=source,
                captures=proof['friendly-command-gena-runtime-records.json.gz'],
                streams=proof['friendly-command-gena-runtime.json'],
                cohorts=proof['friendly-command-gena-cohorts.json.gz'],
                history=proof['friendly-command-gena-history.json'],
                history_fixture=json.loads((ROOT / 'tests/fixtures/friendly-command-gena-history.json').read_bytes()),
                history_sources={p:(ROOT / p).read_bytes() for p in proof['friendly-command-gena-history.json']['source_files_sha256']},
                broad=proof['friendly-command-gena-broad.json.gz'],
                gold=proof['friendly-command-gena-corpora.json.gz'],
                native=proof['friendly-command-gena-extra-native.json.gz'], parents=parents, originals=originals)


def bound(v, report, state, binaries=('klem',), production=True):
    revision.terminal(report, state)
    frozen = report.get('external_inputs', report['frozen_inputs'])
    for name in binaries:
        binary = v['revision']['binding']['binaries'][name]
        assert frozen[binary['path']] == binary['sha256'], 'exact compiled Gena executable'
    # Capture producers use both absolute and worktree-relative source keys.
    for p, digest in v['revision']['binding']['production_inputs'].items():
        absolute = revision.CAPTURE_ROOT + '/' + p
        if production:
            assert absolute in report['frozen_inputs'] or p in report['frozen_inputs'], 'complete capture production closure'
            assert report['frozen_inputs'].get(absolute, report['frozen_inputs'].get(p)) == digest, 'capture belongs to exact Gena production'


def word_additions(old, new):
    assert {k:v for k,v in old.items() if k != 'analyses'} == {k:v for k,v in new.items() if k != 'analyses'}, 'original WordAnalysis fields'
    before, after = old['analyses'], new['analyses']
    assert [p for p in after if p in before] == before, 'every original candidate and order'
    assert len(after) == len({json.dumps(p, sort_keys=True) for p in after}), 'unique captured candidates'
    added = [p for p in after if p not in before]
    assert all(RULE in p['rules'] and {'form':'게나','kind':'ending'} in p['morphemes'] for p in added), 'only canonical Gena additions'
    return added


def additions(old, new):
    assert {k:v for k,v in old.items() if k not in ['analysis','dictionary']} == {k:v for k,v in new.items() if k not in ['analysis','dictionary']}, 'original token ownership and spans'
    if old['kind'] != 'word':
        assert old == new, 'complete nonword records'
        return []
    added = word_additions(old['analysis'], new['analysis'])
    assert len(new['dictionary']['readings']) == len(new['analysis']['analyses']), 'one Native assessment per candidate'
    for ordinal, path in enumerate(old['analysis']['analyses']):
        assert old['dictionary']['readings'][ordinal] == new['dictionary']['readings'][new['analysis']['analyses'].index(path)], 'every original Native assessment'
    assert all(owner in new['dictionary']['lemmas'] for owner in old['dictionary']['lemmas']), 'every original Native owner'
    return added


def inspect_streams(v):
    report, captures, baseline = v['streams'], v['captures'], v['source']['captures']
    bound(v, report, 'passed')
    assert report['capture_sha256'] == v['hashes']['friendly-command-gena-runtime-records.json.gz'] and report['log_sha256'] == v['hashes']['friendly-command-gena-runtime.log'], 'full original CLI capture/log binding'
    assert len(captures['captures']) == len(baseline['captures']) == report['runs'] == 36, 'all36 current policies'
    cases = v['source']['suite']['cases']; totals = dict(frames=0, old_paths=0, added=0, required=0, forbidden=0)
    cli = v['revision']['binding']['binaries']['klem']['path']
    for run, previous in zip(captures['captures'], baseline['captures'], strict=True):
        assert all(run[k] == previous[k] for k in ['family','normalization','mode','cache_bytes','input']), 'every full original input/policy'
        assert run['command'] == [cli, *previous['command'][1:]] and run['exit_code'] == 0 and run['stderr'] == '', 'actual bound CLI filter/cache command'
        assert [json.loads(line) for line in run['stdout'].splitlines()] == run['frames'], 'complete current stdout/frame order'
        assert len(run['frames']) == len(previous['frames']), 'every original CLI frame'
        cursor = 0; observations = []; new_paths = []
        for old, current in zip(previous['frames'], run['frames'], strict=True):
            raw = run['input'].encode(); span = current['span']
            assert span['start'] == cursor and raw[cursor:span['end']].decode() == current['surface'], 'contiguous original UTF-8/NFD spans'
            cursor = span['end']; added = additions(old, current)
            totals['frames'] += 1; totals['added'] += len(added)
            if current['kind'] != 'word': continue
            paths = current['analysis']['analyses']; totals['old_paths'] += len(old['analysis']['analyses'])
            new_paths.extend(dict(surface=current['surface'], span=span, analysis=p,
                                  assessment=current['dictionary']['readings'][paths.index(p)]) for p in added)
            for case in cases:
                if unicodedata.normalize('NFC', current['surface']) != case['surface']: continue
                judgment = case['judgments'][0]
                present = any(prior_audit.matches(p, judgment) for p in paths)
                assert present == (judgment['verdict'] == 'required'), 'every independent required/forbidden path'
                totals[judgment['verdict']] += 1
                observations.append(dict(case_id=case['id'],span=span,verdict=judgment['verdict'],present=present))
        assert cursor == len(run['input'].encode()), 'complete original input covered'
        assert run['new_paths'] == new_paths and run['observations'] == observations, 'all independently rederived CLI observations'
        for other in captures['captures']:
            if all(run[k] == other[k] for k in ['family','normalization','mode']):
                assert run['stdout'] == other['stdout'], 'exact cache parity'
            if all(run[k] == other[k] for k in ['family','mode','cache_bytes']):
                project = lambda c:[(f['kind'],unicodedata.normalize('NFC',f['surface']),f['analysis'],f['dictionary']) for f in c['frames']]
                assert project(run) == project(other), 'NFC/NFD candidate and dictionary parity'
    assert totals == dict(frames=1488,old_paths=3644,added=524,required=264,forbidden=108), 'complete independently derived CLI totals'
    assert (report['frames'],report['old_paths_preserved'],report['new_unjudged_paths'],report['required_checks'],report['forbidden_checks']) == tuple(totals.values()), 'reported CLI totals equal full captures'
    assert set(captures['native_entries']) == set(baseline['native_entries']) == set(v['source']['entries']) and len(captures['native_entries']) == 31, 'all31 complete primary Native owners'
    for ident, row in captures['native_entries'].items():
        old = baseline['native_entries'][ident]
        assert row['command'] == [cli,*old['command'][1:]] and row['exit_code'] == 0, 'actual bound primary Native command'
        assert row['stdout'] == old['stdout'] and row['stderr'] == old['stderr'] and json.loads(row['stdout']) == row['response'] and row['response']['entry'] == v['source']['entries'][ident], 'every full original primary Native response'


def inspect_cohorts(v):
    report = v['cohorts']; bound(v, report, 'complete-original-corpus-history-comparison-passed')
    parent = v['parents']['gentle-command-long-cohorts-retry1.json.gz']
    assert [(r['family'],r['surfaces']) for r in report['runs']] == [('corpus',32096),('history',21406)], 'all53502 original cohort words'
    cli = v['revision']['binding']['binaries']['klem']['path']; derived = []
    for run, old in zip(report['runs'],parent['runs'],strict=True):
        assert len(run['captures']) == 2 and run['captures'][1]['binary'] == cli, 'both bound cohort versions'
        before, after = [c['words'] for c in run['captures']]
        assert before == old['captures'][1]['words'] and len(before) == run['surfaces'] and list(after) == list(before), 'complete ordered original cohort baseline'
        changed = []
        for surface in before:
            added = word_additions(before[surface],after[surface])
            if not added: continue
            changed.append(surface)
            derived.append(dict(id=f"friendly-command-gena-cohort-{run['family']}-{len(changed)}", family=run['family'],surface=surface,before=before[surface],after=after[surface],new_paths=added,contextual_verdict='unjudged',independent_review='pending'))
        assert run['changed_words'] == changed, 'all and only changed cohort words'
    assert report['individual_changed_words'] == derived, 'every exact unjudged cohort addition'
    assert {r['surface'] for r in derived} == {'누구에게나','머슴에게나','보게나','알려주시게나','아무에게나'} and sum(len(r['new_paths']) for r in derived) == 11, 'exact five words/eleven new hypotheses'


def pointer(value, path):
    for part in path.split('/')[1:]:
        key = part.replace('~1','/').replace('~0','~')
        value = value[int(key)] if isinstance(value,list) else value[key]
    return value


def inspect_history(v):
    history = v['history']
    revision.terminal(history, 'complete-gena-history-and-unchanged-parent-fixture-capture-passed')
    assert history == v['history_fixture'], 'exact captured finite history fixture'
    assert history['cohort_sha256'] == v['hashes']['friendly-command-gena-cohorts.json.gz'] and not history['observations_precede_runtime'], 'honest post-runtime history scope'
    changed = {}
    for row in v['cohorts']['individual_changed_words']:
        item = dict(before=row['before'],after=row['after'])
        assert row['surface'] not in changed or changed[row['surface']] == item, 'same word across cohort families'
        changed[row['surface']] = item
    assert history['changed_words'] == changed and len(history['individual_additions']) == 11, 'complete finite history scope'
    sources = v['history_sources']
    assert set(sources) == set(history['source_files_sha256']) and all(sha(raw) == history['source_files_sha256'][p] for p,raw in sources.items()), 'all44 unchanged original history sources'
    derived = []; seen_witnesses = {}
    def walk(value,path,name,digest):
        escape = lambda s:s.replace('~','~0').replace('/','~1')
        if isinstance(value,dict):
            if value.get('normalized') in changed and isinstance(value.get('analyses'),list):
                seen_witnesses[value['normalized']].append(dict(source=name,source_sha256=digest,pointer=path,complete_original_record=value,kind='original-word-analysis'))
            for key,item in value.items():
                child = path + '/' + escape(key)
                if key in changed and not (isinstance(item,dict) and item.get('normalized') == key and isinstance(item.get('analyses'),list)):
                    seen_witnesses[key].append(dict(source=name,source_sha256=digest,pointer=child,complete_original_record=item,kind='original-surface-key'))
                walk(item,child,name,digest)
        elif isinstance(value,list):
            for index,item in enumerate(value): walk(item,path+'/'+str(index),name,digest)
    seen_witnesses = {s:[] for s in changed}
    for name,raw in sources.items(): walk(json.loads(raw),'',name,sha(raw))
    for surface in sorted(changed):
        item = changed[surface]
        for analysis in word_additions(item['before'],item['after']):
            derived.append(dict(id='friendly-command-gena-history-'+str(len(derived)+1),surface=surface,analysis=analysis,original_occurrences=seen_witnesses[surface],contextual_verdict='unjudged',independent_review='pending'))
    assert history['individual_additions'] == derived, 'every finite path and full original pointer witness'
    witnesses = [w for r in derived if r['surface'] == '아무에게나' for w in r['original_occurrences'] if w['source'] == 'tests/fixtures/deoniman-sources.json' and w['kind'] == 'original-word-analysis']
    assert len(witnesses) == 1 and pointer(json.loads(sources[witnesses[0]['source']]),witnesses[0]['pointer']) == witnesses[0]['complete_original_record'], 'original deoniman WordAnalysis witness'


def inspect_gold(v):
    report = v['gold']; bound(v,report,'complete-friendly-command-gena-annotated-comparison-passed',('adapter',))
    parent = v['parents']['gentle-command-long-corpora.json.gz']; annotations = v['originals']['annotations']['corpora']
    assert len(report['runs']) == len(parent['runs']) == len(annotations) == 4, 'all four original annotated partitions'
    assert report['individual_changed_rows'] == [], 'no relabeled annotated rows'
    for run,old,annotation in zip(report['runs'],parent['runs'],annotations,strict=True):
        assert all(run[k] == old[k] for k in ['corpus','partition','source','source_sha256','rows']), 'original gold partition identity'
        assert run['exit_code'] == 0 and sha(run['jsonl'].encode()) == run['stdout_sha256'] and sha(old['jsonl'].encode()) == run['before_stdout_sha256'], 'complete actual annotated output binding'
        assert run['command'] == [v['revision']['binding']['binaries']['adapter']['path'],run['corpus'],run['source']], 'actual compiled adapter command'
        assert report['frozen_inputs']['/home/josh/projects/klem/'+run['source']] == run['source_sha256'], 'original annotated input bytes'
        rows = [json.loads(line) for line in run['jsonl'].splitlines()]; previous = [json.loads(line) for line in old['jsonl'].splitlines()]
        assert rows[1:] == previous[1:] and len(rows)-1 == run['rows'], 'every full original annotated row/outcome'
        assert [{k:r[k] for k in ['id','surface','expected']} for r in rows[1:]] == [{k:r[k] for k in ['id','surface','expected']} for r in annotation['original_converted_rows']], 'every independent original gold annotation'
        before, after = previous[0], rows[0]
        diff = {k:dict(before=before[k],after=after[k]) for k in before if before[k] != after[k]}
        assert set(before) == set(after) and run['summary_changes'] == diff and set(diff) <= {'mean_candidates'}, 'only derived mean-candidate summary differences'
        assert not diff or diff['mean_candidates']['after'] >= diff['mean_candidates']['before'], 'candidate counts cannot shrink'
    assert sum(r['rows'] for r in report['runs']) == 66570 and sum(bool(r['summary_changes']) for r in report['runs']) == 3, 'all66570 unchanged gold outcomes'


def inspect_broad(v):
    report = v['broad']; bound(v,report,'complete-friendly-command-gena-broad-comparison-passed')
    parent = v['parents']['gentle-command-long-broad.json.gz']
    modes = ['candidate-raw','candidate-headword','candidate-compatible','novel-raw','novel-headword','novel-compatible','novel-headword-spacing','novel-compatible-spacing']
    assert [r['mode'] for r in report['runs']] == modes and sum(r['records'] for r in report['runs']) == 1128312, 'all eight complete broad streams'
    expected = [0,0,0,10,4,0,4,0]
    for run,old,count in zip(report['runs'],parent['runs'],expected,strict=True):
        raw = v['originals']['broad_inputs']['sources'][run['source']]['text'].encode()
        assert run['source_sha256'] == old['source_sha256'] == sha(raw) and run['records'] == old['records'], 'complete original broad input identity'
        assert run['before_jsonl_sha256'] == old['after_jsonl_sha256'], 'complete original broad baseline digest'
        assert run['exit_codes'] == [0,0] and run['original_bytes_conserved'] and run['original_paths_preserved'], 'both complete original broad executions'
        flags = ['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
        assert len(run['commands']) == 2 and run['commands'][1][0] == v['revision']['binding']['binaries']['klem']['path'], 'both actual broad executables'
        for command in run['commands']:
            assert command[1:4] == ['text',run['actual_source'],'--dictionary'] and command[4] in report['frozen_inputs'] and command[5:] == flags + (['--suggest-spacing'] if 'spacing' in run['mode'] else []), 'exact broad filter/spacing command'
        assert len(run['changed_frames']) == count and run['new_family_paths'] == count, 'all exact per-policy broad additions'
        total = 0; spans = []
        for change in run['changed_frames']:
            added = additions(change['before'],change['after']); total += len(added)
            start,end = (change['after']['span'][k] for k in ['start','end']); spans.append((start,end))
            assert raw[start:end].decode() == change['after']['surface'], 'original broad occurrence span'
            begin = raw.rfind(b'\n',0,start)+1; finish = raw.find(b'\n',end); finish = len(raw) if finish < 0 else finish
            assert change['line_byte_start'] == begin and change['complete_original_line'] == raw[begin:finish].decode(), 'complete original broad context line'
            assert change['new_paths'] == added and change['contextual_verdict'] == 'unjudged', 'all new broad hypotheses remain unjudged'
            assert change['id'] == f"friendly-command-gena-broad-{run['mode']}-{start}-{end}", 'stable individual broad occurrence identity'
        assert total == count and spans == sorted(set(spans)), 'all and only ordered changed broad occurrences'
        if not count: assert run['before_jsonl_sha256'] == run['after_jsonl_sha256'], 'unchanged complete broad output bytes'


def inspect_native(v):
    report = v['native']; bound(v,report,'complete-original-native-closure-for-every-new-runtime-history-broad-lemma-passed',production=False)
    paths = [p['analysis'] for c in v['captures']['captures'] for p in c['new_paths']] + [p['analysis'] for p in v['history']['individual_additions']] + [a for r in v['broad']['runs'] for c in r['changed_frames'] for a in c['new_paths']]
    heads = sorted({l['text'] for a in paths for l in a['lemmas']})
    assert report['selected_heads'] == heads and len(heads) == 69, 'every newly observed lemma head'
    entries = report['complete_native_entries']
    assert {ident:entry(raw) for ident,raw in report['original_lmf'].items()} == entries and len(entries) == 42, 'all42 complete original Native import projections'
    closure = json.loads(gzip.decompress(v['source']['originals']['friendly-command-gena-original-native-closure.json.gz']))
    assert report['source_exports'] == closure['source_exports'], 'all11 original dictionary exports unchanged'
    assert report['additional_native_entries'] == {i:e for i,e in entries.items() if i not in v['source']['entries']} and len(report['additional_native_entries']) == 13, 'all13 additional original Native owners'
    assert set(report['actual_complete_entry_responses']) == set(entries) and set(report['actual_headword_queries']) == set(heads), 'all actual Native lookups and responses'
    cli = v['revision']['binding']['binaries']['klem']['path']
    db = '/home/josh/projects/klem/.direnv/dictionary-restoration/krdict.db'
    for ident,row in report['actual_complete_entry_responses'].items():
        assert row['command'] == [cli,'dict','entry',db,ident] and row['exit_code'] == 0 and row['stderr'] == '', 'exact actual complete Native command'
        assert json.loads(row['stdout']) == row['response'] and row['response']['entry'] == entries[ident], 'every complete original Native response'
    unmatched = 0
    for head,row in report['actual_headword_queries'].items():
        assert row['command'] == [cli,'dict','lookup',db,head] and row['exit_code'] == 0 and row['stderr'] == '', 'exact actual headword lookup command'
        expected = [dict(id=i,headword=e['headword'],pos=e['pos'],homonym=e['homonym']) for i,e in entries.items() if e['headword'] == head]
        actual = json.loads(row['stdout'])['entries']
        assert sorted(actual,key=lambda e:e['id']) == sorted(expected,key=lambda e:e['id']), 'every same-head Native homonym'
        unmatched += not expected
    assert unmatched == 45 and report['contextual_verdict'] == 'unjudged' and report['independent_review'] == 'pending', 'unmatched hypotheses and independent review remain unjudged'


def inspect(v):
    revision.inspect(v['revision']); source_audit.inspect(v['source'])
    inspect_streams(v); inspect_cohorts(v); inspect_history(v)
    inspect_gold(v); inspect_broad(v); inspect_native(v)
    return dict(rust_tests=1200,source_controls=22,cli_runs=36,cli_frames=1488,
                old_cli_paths=3644,new_unjudged_cli_paths=524,required_checks=264,forbidden_checks=108,
                cohort_words=53502,changed_words=5,new_unjudged_history_paths=11,
                annotated_rows=66570,changed_gold_rows=0,broad_frames=1128312,new_unjudged_broad_paths=18,
                observed_heads=69,complete_native_owners=42,unmatched_hypothetical_heads=45,
                installed_nix_main_performance_context_register_independent_review='pending',
                full_coverage_complete=False)


if __name__ == '__main__':
    print(inspect(inputs()))
