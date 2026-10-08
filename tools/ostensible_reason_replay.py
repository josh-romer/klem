"""Replay actual main/release CLI outputs against the frozen complete prototype.

Full stream hashes, all held-out WordAnalysis objects and individual judgments
must match. This is build parity, not a candidate precision estimate.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
import unicodedata
from pathlib import Path

from ostensible_reason_audit import ROOT, matches, read, sha
from doeda_native_corpora import words_from_cli


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cli', type=Path, required=True)
    parser.add_argument('--dictionary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    source_path = ROOT/'docs/ostensible-reason-source-discovery.json.gz'
    expected_path = ROOT/'docs/ostensible-reason-prototype-source-replay.json.gz'
    broad_path = ROOT/'docs/ostensible-reason-prototype-broad.json.gz'
    corpus_path = ROOT/'docs/ostensible-reason-prototype-corpora.json.gz'
    suite_path = ROOT/'tests/fixtures/ostensible-reason-validity.json'
    producer_path = Path(__file__)
    conditional_path=ROOT/'tests/fixtures/ostensible-reason-mode-scope.json'
    paths = [args.cli, args.dictionary, source_path, expected_path, broad_path, corpus_path, suite_path, conditional_path, producer_path]
    frozen = {str(p):sha(p.read_bytes()) for p in paths}
    source, expected, broad, corpus, suite = map(read, [source_path, expected_path, broad_path, corpus_path, suite_path])
    runs, judgments, broad_runs, conditional_runs, conditional_observations = [], [], [], [], []
    conditional=read(conditional_path)
    for run in expected['runs']:
        text = unicodedata.normalize(run['encoding'], source['input'])
        flags = {'raw':[], 'headword':['--dict-only'], 'compatible':['--dict-compatible']}[run['mode']]
        command = [str(args.cli),'text','-','--dictionary',str(args.dictionary),*flags]
        result = subprocess.run(command, input=text.encode(), capture_output=True, check=True)
        assert sha(result.stdout) == run['after_sha256'] and result.stdout.decode() == run['jsonl']
        runs.append({'encoding':run['encoding'], 'mode':run['mode'], 'command':command, 'exit_code':0,
                     'sha256':sha(result.stdout), 'records':len(result.stdout.splitlines()), 'exact_prototype_output':True})
        words = ' '.join(dict.fromkeys(c['surface'] for c in suite['cases']))
        result = subprocess.run(command,input=unicodedata.normalize(run['encoding'],words).encode(),capture_output=True,check=True)
        records = {r['analysis']['normalized']:r for r in map(json.loads,result.stdout.splitlines()) if r.get('analysis')}
        for case in suite['cases']:
            for judgment in case['judgments']:
                present = any(matches(p,judgment) for p in records.get(case['surface'],{}).get('analysis',{}).get('analyses',[]))
                assert present == (judgment['verdict']=='required'), (case['id'],run['encoding'],run['mode'])
                judgments.append({'case':case['id'], 'judgment':judgment['id'], 'encoding':run['encoding'],
                                  'mode':run['mode'], 'verdict':judgment['verdict'], 'present':present})
    for original in expected['runs']:
        encoding,mode=original['encoding'],original['mode']
        text=unicodedata.normalize(encoding,' '.join(c['surface'] for c in conditional['cases']))
        flags={'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}[mode]
        command=[str(args.cli),'text','-','--dictionary',str(args.dictionary),*flags]
        result=subprocess.run(command,input=text.encode(),capture_output=True,check=True)
        records=list(map(json.loads,result.stdout.splitlines()))
        for case in conditional['cases']:
            row=next(r for r in records if r.get('analysis') and r['analysis']['normalized']==case['surface'])
            targets=[{'analysis':a,'assessment':row['dictionary']['readings'][index]}
                     for index,a in enumerate(row['analysis']['analyses']) if matches(a,case['expected'])]
            assert bool(targets)==case['expected_presence'][mode],(case['id'],encoding,mode)
            for target in targets:
                for native in case['expected_entry_statuses']:
                    entry=next(e for e in target['assessment']['lemmas'][native['lemma']]['entries'] if e['id']==native['id'])
                    assert entry['status']==native['status'],(case['id'],native)
            conditional_observations.append({'case':case['id'],'judgment':case['judgment_id'],'encoding':encoding,'mode':mode,
                                             'present':bool(targets),'expected_presence':case['expected_presence'][mode],
                                             'targets':targets,'contextual_verdict':'unjudged','independent_review':'pending'})
        conditional_runs.append({'encoding':encoding,'mode':mode,'command':command,'exit_code':0,'input':text,
                                 'input_sha256':sha(text.encode()),'sha256':sha(result.stdout),'jsonl':result.stdout.decode(),'records':len(records)})
    assert len(conditional_observations)==72 and len(conditional_runs)==6
    for previous in broad['comparisons']:
        path = Path(previous['source'])
        assert sha(path.read_bytes()) == previous['source_sha256']
        frozen[str(path)] = sha(path.read_bytes())
        mode = previous['mode']
        flags = ['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
        command = [str(args.cli),'text',str(path),'--dictionary',str(args.dictionary),*flags,*(['--suggest-spacing'] if 'spacing' in mode else [])]
        digest, records = hashlib.sha256(), 0
        job = subprocess.Popen(command,stdout=subprocess.PIPE)
        try:
            for line in job.stdout:
                digest.update(line)
                records += 1
            assert job.wait() == 0
        finally:
            if job.poll() is None:
                job.terminate()
                job.wait()
        assert digest.hexdigest() == previous['after_jsonl_sha256'] and records == previous['records']
        broad_runs.append({k:previous[k] for k in ['source','source_sha256','mode','records']} |
                          {'command':command,'exit_code':0,'sha256':digest.hexdigest(),'exact_prototype_output':True})
        print(mode,records,'actual frames match',flush=True)
    words = words_from_cli(args.cli, sorted(corpus['after_words']))
    assert words == corpus['after_words'] and len(words) == 32096
    assert len(runs)==6 and len(judgments)==156 and sum(r['records'] for r in broad_runs)==1128312
    assert all(sha(Path(path).read_bytes())==digest for path,digest in frozen.items())
    report = {'schema_version':1,'state':'passed','exit_code':0,'cli':str(args.cli),'cli_sha256':frozen[str(args.cli)],
              'runs':runs,'judgments':judgments,'broad':broad_runs,'conditional_runs':conditional_runs,'conditional_observations':conditional_observations,
              'corpora':{'unique_surfaces':32096,'original_gold_rows':66570,'exact_prototype_word_analyses':True,
                         'word_analyses_sha256':sha(json.dumps(words,ensure_ascii=False,sort_keys=True).encode())},
              'frozen_inputs':frozen,'inputs_unchanged':True,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'producer':{'text':producer_path.read_text(),'sha256':frozen[str(producer_path)]},
              'scope':'Actual configured CLI parity with all frozen original-source and finite-suite mode judgments, full broad streams and every original held-out word. Twelve further Native owner/mode cases retain individual conditional assertions; their Unknown extensions and raw hypotheses do not certify structural precision or context.',
              'contextual_verdict':'unjudged','independent_review':'pending'}
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Passed actual full CLI parity:',1398,'source frames;',156,'judgments;',1128312,'broad frames;',32096,'corpus words.',flush=True)


if __name__ == '__main__':
    main()
