"""Bind every original annotated row to the actual current Rust adapter."""
import argparse,gzip,hashlib,json,pathlib,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from friendly_command_corpora import outcome
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--adapter',type=pathlib.Path,required=True);parser.add_argument('--output',type=pathlib.Path,required=True);parser.add_argument('--package',type=pathlib.Path);args=parser.parse_args()
ADAPTER=args.adapter.resolve();CORPUS=ROOT/'docs/literary-question-geona-prototype-corpora.json.gz';OUT=args.output;assert not OUT.exists()
sha=lambda p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest();corpus=json.loads(gzip.decompress(CORPUS.read_bytes()));producer=pathlib.Path(__file__);frozen={str(p):sha(p) for p in [ADAPTER,CORPUS,producer,ROOT/'examples/evaluate.rs',ROOT/'tools/corpus.rs']};runs=[]
package_binding={}
if args.package:
 receipt=json.loads(args.package.read_bytes());snapshot=receipt['snapshot']['files'];package_binding={'package_sha256':sha(args.package),'snapshot_files':snapshot}
 assert receipt['state']=='passed' and receipt['exit_code']==0 and receipt['snapshot_unchanged']
 assert len(snapshot)==969
 assert str(ADAPTER)==next(p for p in receipt['outputs'] if p.endswith('-klem-corpus-adapter-0.1.0'))+'/bin/klem-corpus-adapter'
 assert all(sha(ROOT/name)==record['sha256'] for name,record in snapshot.items())
 frozen[str(args.package)]=sha(args.package)
for partition in corpus['corpora']:
 source=ROOT/partition['source'];frozen[str(source)]=sha(source);assert sha(source)==partition['source_sha256'];command=[str(ADAPTER),partition['corpus'],partition['source']];p=subprocess.run(command,cwd=ROOT,capture_output=True,check=True);rows=list(map(json.loads,p.stdout.splitlines()));assert len(rows)==partition['report_lines'];assert rows[0]['input_sha256']==partition['source_sha256']
 for actual,gold,expected in zip(rows[1:],partition['original_converted_rows'],partition['comparisons'],strict=True):
  for k in ['id','surface','expected']:assert actual[k]==gold[k]==expected[k]
  matched,recovered,sets=outcome(gold['expected'],corpus['after_words'][gold['surface']]['analyses']);assert (actual['matched'],actual['recovered'],actual['recovered_sets'])==(matched,recovered,sets)
 for key in ['converted_rows','grouped_matches','recovered_gold_lemmas','gold_lemmas','mean_candidates','p95_candidates','max_candidates']:assert abs(rows[0][key]-partition['after_summary'][key])<1e-10,key
 runs.append({k:partition[k] for k in ['corpus','partition','source','source_sha256']}|{'command':command,'exit_code':0,'rows':len(rows)-1,'jsonl':p.stdout.decode(),'sha256':hashlib.sha256(p.stdout).hexdigest(),'summary':rows[0],'all_original_rows_and_candidate_summaries_bound':True});print(partition['corpus'],partition['partition'],len(rows)-1,'currentactualRust rows pass.',flush=True)
assert sum(r['rows'] for r in runs)==66570 and all(sha(p)==h for p,h in frozen.items());r={'schema_version':1,'state':'passed','exit_code':0,'adapter':str(ADAPTER),'adapter_sha256':sha(ADAPTER),'corpus_sha256':sha(CORPUS),'runs':runs,'frozen_inputs':frozen,'inputs_unchanged':True,'producer':{'text':producer.read_text(),'sha256':sha(producer)},'scope':'Actual configured production Rust adapter against alloriginal66570rows, each exact gold grouping and unchanged candidate-count summaries. Prototypecapture expected words came from the independently captured isolated CLI; The configured build is recorded separately; actual installed package identity and all969 frozen source inputs are bound; precision/contextual review remains separate.','contextual_verdict':'unjudged','independent_review':'pending'};r.update(package_binding);assert not package_binding or all(sha(ROOT/name)==record['sha256'] for name,record in package_binding['snapshot_files'].items());OUT.write_bytes(gzip.compress((json.dumps(r,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0));print('All66570 currentRust adapter rows bound.',flush=True)
