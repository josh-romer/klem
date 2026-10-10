"""Bind preserved installed giroseo packages to all complete recorded runtime outputs."""
import gzip,hashlib,json,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def raw(p):
 data=Path(p).read_bytes();return gzip.decompress(data) if str(p).endswith('.gz') else data
def read(p):return json.loads(raw(p))
def inspect(binding,broad,cohorts,corpora,finite,browser,runtime,expected_broad,expected_cohorts,expected_corpora,source,cases,native,labels):
 assert binding['state']=='passed' and binding['exit_code']==0 and binding['inputs_unchanged'] and binding['head_unchanged'] and binding['index_unchanged'],'actual committed source binding'
 assert set(binding['profiles'])=={'klem','web-assets','corpus-adapter'},'complete source profiles'
 assert {k:len(v['files']) for k,v in binding['profiles'].items()}=={'klem':1024,'web-assets':18,'corpus-adapter':1024},'complete source files'
 assert binding['profiles']['klem']['files']==binding['profiles']['corpus-adapter']['files'],'same Rust source files'
 for profile in binding['profiles'].values():
  assert sha(profile['derivation_json'].encode())==profile['derivation_json_sha256'],'actual derivation bytes'
  drv=json.loads(profile['derivation_json'])[profile['derivation']]
  assert drv['env']['src']==profile['source'] and drv['outputs']['out']['path']==profile['package'],'actual package source identity'
  assert profile['package'] in binding['outputs'] and all(v['bytes']>0 and len(v['sha256'])==64 for v in profile['files'].values()),'complete source identities'
 cli=binding['profiles']['klem']['package']+'/bin/klem';adapter=binding['profiles']['corpus-adapter']['package']+'/bin/klem-corpus-adapter'
 assert sha(binding['launcher']['text'].encode())==binding['launcher']['sha256'] and cli[:-4]+'klem-web' in binding['launcher']['text'],'actual launcher'
 assert binding['profiles']['web-assets']['package']+'/share/klem-web' in binding['launcher']['text'],'actual launcher assets'
 for report in [broad,cohorts,corpora,finite]:
  assert 'passed' in report['state'] and report['inputs_unchanged'],'terminal installed runtime'
  assert sha(report['producer']['text'].encode())==report['producer']['sha256'],'actual runtime producer'
 assert len(broad['runs'])==len(expected_broad['comparisons'])==8,'complete broad workloads'
 for run,expected in zip(broad['runs'],expected_broad['comparisons'],strict=True):
  assert run['mode']==expected['mode'] and run['source_sha256']==expected['source_sha256'] and run['records']==expected['records'],'complete original broad input'
  assert run['actual_jsonl_sha256']==expected['after_jsonl_sha256'] and run['exact_preserved_capture'] and run['original_bytes_conserved'] and run['exit_code']==0,'complete installed broad output'
  mode=run['mode'];flags=['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
  assert run['command'][0:3]==[cli,'text',run['source']] and run['command'][3]=='--dictionary' and run['command'][5:]==flags+(['--suggest-spacing'] if 'spacing' in mode else []),'installed broad flags'
 assert sum(r['records'] for r in broad['runs'])==1128312,'complete broad frames'
 assert len(cohorts['runs'])==len(expected_cohorts['runs'])==2,'complete word cohorts'
 for run,expected in zip(cohorts['runs'],expected_cohorts['runs'],strict=True):
  assert run['family']==expected['family'] and run['surfaces']==expected['surfaces'],'complete cohort identity'
  assert run['captures'][-1]['binary']==cli and not run['changed_words'],'actual installed cohort executable'
  for capture in run['captures']:
   assert capture['words']==expected['captures'][1]['words'],'every complete original word'
   assert sha(json.dumps(capture['words'],ensure_ascii=False,sort_keys=True).encode())==capture['word_sha256'],'complete word capture digest'
 assert sum(r['surfaces'] for r in cohorts['runs'])==53502,'complete cohort surfaces'
 assert corpora['adapter']==adapter and len(corpora['runs'])==len(expected_corpora['runs'])==4 and not corpora['individual_changed_rows'],'actual installed adapter'
 for run,expected in zip(corpora['runs'],expected_corpora['runs'],strict=True):
  assert all(run[k]==expected[k] for k in ['corpus','partition','source','source_sha256','rows','jsonl','stdout_sha256']),'all complete original annotated outputs'
  assert sha(run['jsonl'].encode())==run['stdout_sha256'] and run['command']==[adapter,run['corpus'],run['source']] and run['exit_code']==0 and not run['summary_changes'],'actual full adapter execution'
 assert sum(r['rows'] for r in corpora['runs'])==66570,'complete annotated rows'
 expected_keys=[(family,encoding,mode,cache) for family in ['complete-original-source','all-individual-cases'] for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible'] for cache in [0,4096]]
 assert [(r['family'],r['encoding'],r['mode'],r['cache_bytes']) for r in finite['runs']]==expected_keys,'complete Unicode/filter/cache streams'
 inputs={'complete-original-source':source['complete_source_text'],'all-individual-cases':' '.join(c['surface'] for suite in cases for c in suite['cases'])};streams={}
 for run in finite['runs']:
  original=unicodedata.normalize(run['encoding'],inputs[run['family']]).encode();assert sha(original)==run['input_sha256'],'complete finite source input'
  assert sha(run['jsonl'].encode())==run['jsonl_sha256'] and run['exit_codes']==[0,0] and run['exact_previous_and_installed'] and run['original_bytes_conserved'],'complete finite capture'
  rows=[json.loads(line) for line in run['jsonl'].splitlines()];assert len(rows)==run['records'];cursor=0
  for row in rows:
   assert row['span']['start']==cursor;cursor=row['span']['end'];assert original[row['span']['start']:cursor].decode()==row['surface'],'original finite byte span'
  assert cursor==len(original),'all finite source bytes'
  key=(run['family'],run['encoding'],run['mode'])
  if key in streams:assert streams[key]==run['jsonl'],'cache parity'
  streams[key]=run['jsonl'];assert run['commands'][1][0]==cli,'actual installed finite executable'
  flags={'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}[run['mode']]
  assert len(run['commands'])==2 and all(c[0] in finite['frozen_inputs'] and c[1:4]==['text','-','--dictionary'] and c[4] in finite['frozen_inputs'] and c[5:]==[*flags,'--cache-bytes',str(run['cache_bytes'])] for c in run['commands']),'actual finite filter/cache commands'
 assert sum(r['records'] for r in finite['runs'])==3144,'complete finite frames'
 assert runtime['state']=='passed' and runtime['exit_code']==0 and runtime['inputs_unchanged'] and runtime['server_stopped'] and runtime['command'][0]==binding['launcher']['package']+'/bin/klem-web','actual installed browser runtime'
 assert len(browser['diagrams'])==204 and len(browser['exports'])==6 and len(browser['nativeEntries'])==34 and not browser['errors'],'complete installed browser captures'
 assert not browser['spacingDiagrams'],'finite browser scope'
 assert {r['id']:r['entry'] for r in browser['nativeEntries']}==native,'complete installed Native fields'
 required=[c for suite in cases for c in suite['cases'] if any(j['verdict']=='required' for j in c['judgments'])]
 expected_diagrams=[(c['id'],encoding,mode) for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible'] for c in required]
 assert [(r['case_id'],r['encoding'],r['mode']) for r in browser['diagrams']]==expected_diagrams,'complete individual browser scope'
 assert [(r['encoding'],r['mode']) for r in browser['exports']]==[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']],'complete individual export scope'
 assert [r['encoding'] for r in browser['responses']]==['NFC','NFD'],'complete browser Unicode responses'
 targets={c['id']:c for c in required}
 for row in browser['diagrams']:
  target=targets[row['case_id']];judgment=next(j for j in target['judgments'] if j['verdict']=='required');path=row['analysis']
  assert [l['text'] for l in path['lemmas']]==judgment['lemmas'] and [m['form'] for m in path['morphemes']]==judgment['morphemes'],'independent authored browser path'
  assert all(r in path['rules'] for r in judgment['required_rules']),'independent authored browser provenance'
  assert row['forms'][-1]==path['morphemes'][-1]['form'],'actual browser ending component'
  label=labels['-'+path['morphemes'][-1]['form']]
  assert all(str(s['id']) in row['source_hint'] for s in label['sources']),'original browser label sources'
 for capture in browser['exports']:
  text=' '.join(unicodedata.normalize(capture['encoding'],c['surface']) for c in required).encode();cursor=0
  for row in capture['records']:
   assert row['span']['start']==cursor;cursor=row['span']['end'];assert text[row['span']['start']:cursor].decode()==row['surface'],'export original byte spans'
  assert cursor==len(text),'complete export source'

 return {'broad_frames':sum(r['records'] for r in broad['runs']),'cohort_words':sum(r['surfaces'] for r in cohorts['runs']),'annotated_rows':sum(r['rows'] for r in corpora['runs']),'finite_frames':sum(r['records'] for r in finite['runs']),'browser_diagrams':len(browser['diagrams']),'full_coverage_complete':False}
def inputs():
 names=['giroseo-installed-source-binding.json.gz','giroseo-installed-broad.json.gz','giroseo-installed-cohorts.json.gz','giroseo-installed-corpora.json.gz','giroseo-installed-finite.json.gz','giroseo-installed-browser.json.gz','giroseo-installed-browser-runtime.json.gz','giroseo-broad.json.gz','giroseo-cohorts.json.gz','giroseo-corpora.json.gz','giroseo-source-preparation.json.gz']
 return [read(ROOT/'docs'/name) for name in names]+[[read(ROOT/'tests/fixtures'/name) for name in ['giroseo-validity.json']]]+[read(ROOT/'tests/fixtures/giroseo-additional-native-entries.json'),read(ROOT/'web/src/grammar-labels.json')]
if __name__=='__main__':print(inspect(*inputs()))
