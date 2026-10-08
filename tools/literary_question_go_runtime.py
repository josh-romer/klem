"""Validate actual current CLI, adapter and browser evidence for literary question endings."""
import argparse
import gzip
import json
import math
import re
import unicodedata

from ostensible_reason_audit import ROOT, matches, producer, read, sha
from pathlib import Path


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
    assert len(observations)==96
    return observations


def verify_cli(report):
    producer(report)
    assert report['producer']['text']==(ROOT/'tools/literary_question_go_replay.py').read_text()
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert report['cli_sha256']==report['frozen_inputs'][report['cli']]
    assert report['contextual_verdict']=='unjudged' and report['independent_review']=='pending'
    expected=read(ROOT/'docs/literary-question-go-prototype-source-replay.json.gz')
    suite=read(ROOT/'tests/fixtures/literary-question-go-validity.json')
    suite['cases'].extend(read(ROOT/'tests/fixtures/literary-question-go-boundaries.json')['cases'])
    assert len(report['runs'])==len(expected['runs'])==6
    judgments=[]
    for actual,old in zip(report['runs'],expected['runs'],strict=True):
        assert (actual['encoding'],actual['mode'])==(old['encoding'],old['mode'])
        assert actual['sha256']==old['after_sha256'] and actual['records']==535
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
        for case in suite['cases']:
            for j in case['judgments']:
                judgments.append({'case':case['id'],'judgment':j['id'],'encoding':actual['encoding'],'mode':actual['mode'],
                                  'verdict':j['verdict'],'present':j['verdict']=='required'})
    assert report['judgments']==judgments and len(judgments)==372
    matrix=read(ROOT/'tests/fixtures/literary-question-go-mode-scope.json')
    modes=read(ROOT/'docs/literary-question-go-prototype-modes.json.gz')
    assert len(report['conditional_runs'])==len(modes['runs'])==6
    for run, original in zip(report['conditional_runs'],modes['runs'],strict=True):
        assert (run['encoding'],run['mode'])==(original['encoding'],original['mode'])
        assert run['input']==original['input'] and run['jsonl']==original['after_jsonl']
        assert run['records']==31
        assert run['exit_code']==0 and run['records']==len(run['jsonl'].splitlines())
        assert sha(run['jsonl'].encode())==run['sha256'] and sha(run['input'].encode())==run['input_sha256']
    assert report['conditional_observations']==conditional_observations(report['conditional_runs'],matrix)
    boundary=read(ROOT/'docs/literary-question-go-boundary-modes-retry2.json.gz')
    assert len(report['boundary_runs'])==len(boundary['runs'])==6
    for run, original in zip(report['boundary_runs'],boundary['runs'],strict=True):
        assert (run['encoding'],run['mode'])==(original['encoding'],original['mode'])
        assert run['sha256']==original['after_sha256'] and run['records']==45
        assert run['exit_code']==0 and run['exact_prototype_output'] is True
    broad=read(ROOT/'docs/literary-question-go-prototype-broad.json.gz')
    assert len(report['broad'])==len(broad['comparisons'])==8
    for actual,old in zip(report['broad'],broad['comparisons'],strict=True):
        assert all(actual[k]==old[k] for k in ['source','source_sha256','mode','records'])
        assert actual['sha256']==old['after_jsonl_sha256']
        assert actual['exit_code']==0 and actual['exact_prototype_output'] is True
    corpus=read(ROOT/'docs/literary-question-go-prototype-corpora.json.gz')
    assert report['corpora']=={'unique_surfaces':32096,'original_gold_rows':66570,'exact_prototype_word_analyses':True,
                              'word_analyses_sha256':corpus['after_words_sha256']}
    return {'source_frames':3210,'boundary_frames':270,'individual_mode_judgments':372,'conditional_mode_judgments':96,'broad_frames':1128312,'corpus_words':32096}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli-report', type=Path, required=True)
    args = parser.parse_args()
    print(verify_cli(read(args.cli_report)))
