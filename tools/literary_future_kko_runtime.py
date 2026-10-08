"""Bind configured CLI replays and append-only judgments to preserved source evidence."""
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def read(path):
    path=Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix=='.gz' else path.read_bytes())

def verify_ledger(current,proposal):
    old=json.loads(proposal['before_text'])
    assert sha(proposal['before_text'].encode())==proposal['before_sha256']
    assert proposal['before_case_count']==len(old['cases'])==34843
    assert proposal['after_case_count']==34920
    assert current['cases'][:34843]==old['cases']
    assert current['cases'][34843:34920]==proposal['added_cases']
    assert len({c['id'] for c in current['cases']})==len(current['cases'])
    assert all(current['sources'][k]==v for k,v in old['sources'].items())
    assert all(current['sources'][k]==v for k,v in proposal['added_sources'].items())
    counts={v:sum(j['verdict']==v for c in proposal['added_cases'] for j in c['judgments']) for v in ['required','forbidden']}
    assert counts==proposal['raw_verdict_counts']=={'required':66,'forbidden':11}
    excluded={c['id'] for c in proposal['excluded_conditional_or_native_cases']}
    assert len(excluded)==9 and not excluded&{c['id'] for c in proposal['added_cases']}
    assert sum(c['id'].startswith('literary-future-kko-original-') for c in proposal['added_cases'])==19
    return {'previous_cases_preserved':34843,'individual_added_cases':77,'raw_judgments':counts,'separate_native_or_conditional_cases':9}

def inspect(report):
    assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True
    assert sha(report['producer']['text'].encode())==report['producer']['sha256']
    assert report['cli_sha256']==report['frozen_inputs'][report['cli']]
    integration=read(ROOT/'docs/literary-future-kko-main-integration.json.gz')
    assert report['snapshot_files']==integration['snapshot_files'] and len(report['snapshot_files'])==947
    original_root=Path(report['finite_runs'][0]['command'][report['finite_runs'][0]['command'].index('--dictionary')+1]).parents[3]
    expected=[]
    discovery=read(ROOT/'docs/literary-future-kko-source-discovery.json.gz')
    for family,name in [('source','prototype-source-replay'),('boundary','boundary-preflight'),('owner','owner-extension-preflight'),('spacing','spacing-preflight-retry1')]:
        p=ROOT/'docs'/('literary-future-kko-'+name+'.json.gz');capture=read(p)
        assert report['frozen_inputs'][str(original_root/'docs'/p.name)]==sha(p.read_bytes())
        for run in capture['runs']:
            mode=run['mode'];flags=['--dict-compatible'] if mode=='compatible' else ['--dict-only'] if mode=='headword' else []
            if family=='spacing':flags.append('--suggest-spacing')
            text=run['input'] if family=='spacing' else unicodedata.normalize(run['encoding'],discovery['input'] if family=='source' else capture['input'])
            jsonl=run['after']['jsonl'] if family=='spacing' else run['jsonl']
            expected.append({'family':family,'encoding':run['encoding'],'mode':mode,'command':[report['cli'],'text','-','--dictionary',str(original_root/'data/dictionaries/krdict/krdict.db'),*flags],'input_sha256':sha(text.encode()),'jsonl_sha256':sha(jsonl.encode()),'records':len(jsonl.splitlines()),'expected_capture':str(p.relative_to(ROOT)),'expected_capture_sha256':sha(p.read_bytes()),'exact_captured_output':True,'exit_code':0})
    assert len(expected)==22 and report['finite_runs']==expected
    broad=read(ROOT/'docs/literary-future-kko-prototype-broad.json.gz')
    assert len(report['broad'])==len(broad['comparisons'])==8
    for actual,original in zip(report['broad'],broad['comparisons'],strict=True):
        assert all(actual[k]==original[k] for k in ['source','source_sha256','mode','records'])
        assert actual['sha256']==original['after_jsonl_sha256'] and actual['exact_captured_output'] is True and actual['exit_code']==0
        assert actual['expected_capture_sha256']==sha((ROOT/'docs/literary-future-kko-prototype-broad.json.gz').read_bytes())
        mode=actual['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
        if 'spacing' in mode:flags.append('--suggest-spacing')
        assert actual['command']==[report['cli'],'text',actual['source'],'--dictionary',str(original_root/'data/dictionaries/krdict/krdict.db'),*flags]
    assert sum(r['records'] for r in report['broad'])==1128312
    assert len(report['words'])==2
    for actual,(family,name,count) in zip(report['words'],[('corpus','prototype-corpora',32096),('historical','prototype-legacy-history-retry1',21388)],strict=True):
        p=ROOT/'docs'/('literary-future-kko-'+name+'.json.gz');capture=read(p)
        assert actual=={'family':family,'surfaces':count,'actual_word_analysis_sha256':capture['after_words_sha256'],'expected_capture_sha256':sha(p.read_bytes()),'exact_captured_output':True}
    return {'finite_mode_runs':22,'finite_frames':sum(r['records'] for r in expected),'broad_frames':1128312,'corpus_surfaces':32096,'historical_surfaces':21388,'all_preserved_outputs_bound':True,'precision_context_and_independent_review':'pending'}

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args()
    print(inspect(read(args.report)))
    print(verify_ledger(read(ROOT/'tests/fixtures/validity.json'),read(ROOT/'docs/literary-future-kko-append-only-ledger-proposal.json.gz')))
