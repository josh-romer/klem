"""Bind actual main/release corpus adapters to all frozen prototype gold rows."""
import argparse
import gzip
import json
import subprocess
from pathlib import Path

from ostensible_reason_audit import ROOT, read, sha
from friendly_command_corpora import outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    corpus_path = ROOT/'docs/ostensible-reason-prototype-corpora.json.gz'
    # All held-out words are byte-identical to the contrast cohort.
    # Compare the actual old adapter capture, without inventing a new baseline.
    expected_path = ROOT/'docs/declarative-contrast-prototype-adapter.json.gz'
    producer_path = Path(__file__)
    paths = [args.adapter, corpus_path, expected_path, producer_path]
    frozen = {str(p):sha(p.read_bytes()) for p in paths}
    corpus, expected = read(corpus_path), read(expected_path)
    runs = []
    for partition, original in zip(corpus['corpora'],expected['runs'],strict=True):
        source = ROOT/partition['source']
        assert sha(source.read_bytes()) == partition['source_sha256']
        frozen[str(source)] = sha(source.read_bytes())
        command = [str(args.adapter),partition['corpus'],partition['source']]
        result = subprocess.run(command,cwd=ROOT,capture_output=True,check=True)
        wanted = next(s for s in original['streams'] if s['mode']=='after')
        assert result.stdout.decode() == wanted['jsonl'] and sha(result.stdout) == wanted['sha256']
        rows = list(map(json.loads,result.stdout.splitlines()))
        assert len(rows)-1 == wanted['rows'] and rows[0]['input_sha256'] == partition['source_sha256']
        for row, prior in zip(rows[1:],partition['original_converted_rows'],strict=True):
            assert all(row[k]==prior[k] for k in ['id','surface','expected'])
            matched,recovered,sets = outcome(row['expected'],corpus['after_words'][row['surface']]['analyses'])
            assert (row['matched'],row['recovered'],row['recovered_sets']) == (matched,recovered,sets)
        for key in ['converted_rows','grouped_matches','recovered_gold_lemmas','gold_lemmas','mean_candidates','p95_candidates','max_candidates']:
            assert abs(rows[0][key]-partition['after_summary'][key]) < 1e-10
        runs.append({k:partition[k] for k in ['corpus','partition','source','source_sha256']} |
                    {'command':command,'exit_code':0,'rows':len(rows)-1,'sha256':sha(result.stdout),
                     'exact_prior_adapter_output':True,'all_rows_independently_bound_to_word_analyses':True})
        print(partition['corpus'],partition['partition'],len(rows)-1,'actual adapter rows match',flush=True)
    assert len(runs)==4 and sum(r['rows'] for r in runs)==66570
    assert all(sha(Path(path).read_bytes())==digest for path,digest in frozen.items())
    report = {'schema_version':1,'state':'passed','exit_code':0,'adapter':str(args.adapter),
              'adapter_sha256':frozen[str(args.adapter)],'original_adapter_capture_sha256':frozen[str(expected_path)],'runs':runs,'frozen_inputs':frozen,'inputs_unchanged':True,
              'producer':{'text':producer_path.read_text(),'sha256':frozen[str(producer_path)]},
              'scope':'Actual configured Rust adapter parity for all four original held-out partitions; every original gold row and actual candidate summary binds to unchanged source and prototype WordAnalysis outputs. Does not establish candidate precision.',
              'contextual_verdict':'unjudged','independent_review':'pending'}
    raw = (json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode()
    args.output.write_bytes(gzip.compress(raw,mtime=0) if args.output.suffix=='.gz' else raw)
    print('Passed actual adapter parity:',66570,'rows.',flush=True)


if __name__ == '__main__':
    main()
