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
  if current!=complete and len(current['cases'])>len(complete['cases']):
   # Only exact reviewed suites, in integration order, may extend this
   # historical ledger. Full fixture bytes, source identities, case order
   # and every judgment are bound; arbitrary appended tails are rejected.
   reviewed_appends=[
    ('declarative-dao-validity.json',36,'f847dfe655657f54a0a10870251d6b831c2462d8b8ddf8b7c1bb30218efaa9b7','DAO'),
    ('self-question-validity.json',29,'882d5671aa228e25ede6809e03da1d11ac097dd484315e59d1b2f6ce02fa566a','self-question'),
    ('dapnikka-validity.json',62,'ebba195627702a1ccbe768f559983143e51094f3dd671a7b20c05ac00f0487f0','dapnikka'),
    ('dapnikka-novel-validity.json',1,'162bde7235fccb0091eacf4e1370cc2aad58c67a298303a2182483e176b4137f','dapnikka novel'),
    ('formal-b-validity.json',99,'e64d2f15524b6bd8d8cc199b6f46c17a3073d2791d16677cdfdf17721125d94f','formal-b'),
    ('formal-b-novel-validity.json',9,'d42e0df2c6f0f3573e85545acd02494148c492acd815c9ae8a3fb62001b0a9b2','formal-b novel'),
    ('reported-experience-validity.json',97,'93e5294ec23e651c3cb85c7f131c3a91fa025f31a23d170bc49a6141c69e2d7a','reported-experience'),
    ('giroseo-validity.json',48,'da93852e351d2bc6fe0464bae93a6a6d4b3694fd4a42f9b01d7226cc4f959889','giroseo'),
    ('explanatory-se-validity.json',46,'3d13d48a6814c40b9a7328f0c2fc748f20590974a57f197a38b375c3a397cad8','explanatory-se'),
    ('explanatory-se-gold-validity.json',2,'2682e3b37b8d1782b1a9d86d8e4d1d3db3b46ec31323aa9303ab7f18ffea4582','explanatory-se-gold'),
    ('explanatory-se-novel-validity.json',14,'41ca6b4a824266128de576190bc4389066375bb4e0c1550ebb478caef83bf02c','explanatory-se-novel'),
    ('familiar-geurae-validity.json',27,'e2b927b7691731277b429a7322639d26562b9946741d1bcd029943d87d61f9f5','familiar-geurae'),
    ('fear-lsera-validity.json',46,'2ccc67014adcae61861ee24774ddd2eae92bf82c7a9f3d138179460851390f25','fear-lsera'),
    ('formal-volitional-raw-validity.json',53,'23346ec33a887be1eb10c925ef9cfe2777b901df3d6e600e5bea053d7a968124','formal-volitional raw'),
    ('formal-volitional-novel-validity.json',4,'db0853ac54c5ca0ab8995511e6d40f4c20b1a9b1020b9358a31d9ee19efaea41','formal-volitional novel'),
   ]
   accepted={**complete,'cases':list(complete['cases']),'sources':dict(complete['sources'])}
   for filename,count,digest,label in reviewed_appends:
    if len(current['cases'])==len(accepted['cases']):break
    path=ROOT/'tests/fixtures'/filename
    assert sha(path.read_bytes())==digest,f'reviewed {label} fixture bytes'
    suite=read(path)
    assert len(suite['cases'])==count,'complete append-only ledger'
    assert not set(accepted['sources'])&set(suite['sources']),'separate reviewed source identities'
    accepted['cases'].extend(suite['cases']);accepted['sources'].update(suite['sources'])
   assert current==accepted,'complete append-only ledger'
   assert len({c['id'] for c in accepted['cases']})==len(accepted['cases']),'complete case IDs'
   current=complete
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
