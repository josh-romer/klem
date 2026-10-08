"""Independently bind actual geona CLI output and scoped judgments to preserved evidence."""
import argparse,gzip,hashlib,json,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def verify_ledger(current,proposal,later_proposal=None):
 expected=proposal['proposed_ledger']
 historical=current
 if current!=expected:
  # Bind the only reviewed later append exactly. Do not accept arbitrary tails
  # merely because the older prefix has the expected length or case IDs.
  later=read(ROOT/'docs/additive-ppundeoreo-proposed-ledger.json.gz') if later_proposal is None else later_proposal
  complete=later['proposed_ledger']
  assert current==complete,'complete append-only ledger'
  assert later['before_case_count']==len(expected['cases'])==34981,'historical ledger prefix'
  assert complete['cases'][:34981]==expected['cases'],'historical ledger prefix'
  assert {k:v for k,v in complete.items() if k not in ['cases','sources']}=={k:v for k,v in expected.items() if k not in ['cases','sources']},'historical ledger metadata'
  assert all(complete['sources'].get(k)==v for k,v in expected['sources'].items()),'historical source links'
  assert complete['cases'][34981:]==later['new_cases'] and len(later['new_cases'])==33,'reviewed later append'
  counts={v:sum(j['verdict']==v for c in later['new_cases'] for j in c['judgments']) for v in ['required','forbidden']}
  assert counts==later['new_counts']=={'required':27,'forbidden':6},'reviewed later judgments'
  excluded={c['id'] for c in later['excluded_conditional_cases']}
  assert len(excluded)==13 and not excluded&{c['id'] for c in complete['cases']},'later conditional scope'
  assert not {c['id'] for c in proposal['excluded_conditional_native_cases']}&{c['id'] for c in complete['cases']},'historical conditional scope'
  assert len({c['id'] for c in complete['cases']})==len(complete['cases'])==35014,'complete case IDs'
  historical=expected
 assert historical==expected,'complete append-only ledger'
 assert proposal['before_case_count']==34920 and len(proposal['new_cases'])==61 and len(historical['cases'])==34981,'exact finite scope'
 assert historical['cases'][34920:]==proposal['new_cases'],'appended case identity/order'
 assert len({c['id'] for c in historical['cases']})==34981,'case IDs'
 counts={v:sum(j['verdict']==v for c in proposal['new_cases'] for j in c['judgments']) for v in ['required','forbidden']};assert counts==proposal['new_counts']=={'required':50,'forbidden':11},'finite raw counts'
 excluded={c['id'] for c in proposal['excluded_conditional_native_cases']};assert len(excluded)==21 and not excluded&{c['id'] for c in proposal['new_cases']},'conditional/Native scope'
 return {'preserved_cases':34920,'new_required':50,'new_forbidden':11,'excluded':21}
def inspect(report):
 assert report['state']=='passed' and report['exit_code']==0 and report['inputs_unchanged'] is True,'terminal actual runtime'
 assert sha(report['producer']['text'].encode())==report['producer']['sha256'],'actual producer bytes'
 assert report['cli_sha256']==report['frozen_inputs'][report['cli']],'actual executable'
 sources=read(ROOT/'docs/literary-question-geona-main-binaries.json.gz')
 assert report['snapshot_files']==sources['snapshot_files'] and len(report['snapshot_files'])==957,'complete current source scope'
 if 'package_sha256' in report:
  from literary_question_geona_package_binding import package_paths
  assert report['cli']==package_paths(report)['klem']+'/bin/klem','actual installed CLI'
  assert report['producer']['text']==(ROOT/'tools/literary_question_geona_replay.py').read_text(),'packaged replay producer'
 else:
  assert report['cli_sha256']==sources['binaries']['cli']['sha256'],'actual compiled main executable'
 assert all(len(v['sha256'])==64 and v['bytes']>0 for v in report['snapshot_files'].values()),'source SHA/bytes'
 db=report['finite_runs'][0]['command'];dictionary=db[db.index('--dictionary')+1];original_root=Path(dictionary).parents[3];expected=[]
 for family,name in [('source','prototype-source-replay'),('boundary','boundary-corrected'),('owner','owner-extension-typed'),('spacing','spacing-preflight')]:
  p=ROOT/'docs'/('literary-question-geona-'+name+'.json.gz');capture=read(p);assert report['frozen_inputs'][str(original_root/'docs'/p.name)]==sha(p.read_bytes()),'preserved finite source capture'
  for run in capture['runs']:
   text=run.get('input',unicodedata.normalize(run['encoding'],capture.get('input','')));captured=run.get('after',run);command=list(captured['command']);command[0]=report['cli'];command[command.index('--dictionary')+1]=dictionary;raw=captured['jsonl'].encode()
   expected.append({'family':family,'encoding':run['encoding'],'mode':run['mode'],'command':command,'input_sha256':sha(text.encode()),'jsonl_sha256':sha(raw),'records':len(raw.splitlines()),'expected_capture':str(p.relative_to(ROOT)),'expected_capture_sha256':sha(p.read_bytes()),'exact_captured_output':True,'exit_code':0})
 assert len(expected)==22 and report['finite_runs']==expected,'every exact finite mode/command/input/output'
 p=ROOT/'docs/literary-question-geona-prototype-broad.json.gz';capture=read(p);assert len(report['broad'])==len(capture['comparisons'])==8,'eight complete streams'
 for actual,source in zip(report['broad'],capture['comparisons'],strict=True):
  assert all(actual[k]==source[k] for k in ['source','source_sha256','mode','records']),'complete original broad input'
  assert actual['sha256']==source['after_jsonl_sha256'] and actual['expected_capture_sha256']==sha(p.read_bytes()) and actual['exact_captured_output'] is True and actual['exit_code']==0,'full broad output binding'
  mode=actual['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
  assert actual['command']==[report['cli'],'text',source['source'],'--dictionary',dictionary,*flags,*(['--suggest-spacing'] if 'spacing' in mode else [])],'actual broad flags'
 assert sum(v['records'] for v in report['broad'])==1128312,'all broad frames'
 assert len(report['words'])==2,'complete corpus/history'
 for actual,(family,name,count) in zip(report['words'],[('corpus','prototype-corpora',32096),('historical','prototype-legacy-history',21406)],strict=True):
  p=ROOT/'docs'/('literary-question-geona-'+name+'.json.gz');capture=read(p);assert actual=={'family':family,'surfaces':count,'actual_word_analysis_sha256':capture['after_words_sha256'],'expected_capture_sha256':sha(p.read_bytes()),'exact_captured_output':True},'all original WordAnalysis outputs'
 return {'finite_runs':22,'finite_frames':sum(v['records'] for v in expected),'broad_frames':1128312,'corpus_surfaces':32096,'historical_surfaces':21406,'precision_context_and_independent_review':'pending'}
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True);args=parser.parse_args();print(inspect(read(args.report)));print(verify_ledger(read(ROOT/'tests/fixtures/validity.json'),read(ROOT/'docs/literary-question-geona-proposed-ledger.json.gz')))
