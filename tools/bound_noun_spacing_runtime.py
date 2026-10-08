"""Capture actual bound-noun CLI/API evidence without replacing the original proposal."""
import argparse,gzip,hashlib,json,subprocess,sys,unicodedata,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from predicate_auxiliary_spacing_runtime import verify_segment
RULE='spacing.modifier_bound_noun'
MODES={'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}
PROFILE_IDS={'것':'krdict:62835','수':'krdict:15615','줄':'krdict:91870','바':'krdict:56324','적':'krdict:71232','지':'krdict:91881','듯':'krdict:49981','뿐':'krdict:66641','대로':'krdict:48415','만큼':'krdict:53008','때문':'krdict:64555','따름':'krdict:49675'}
def read(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def verify_hypothesis(h,record,text,replay):
 assert h['rule']==RULE
 segments=h['records'];assert len(segments)>=2
 assert ''.join(s['surface'] for s in segments)==record['surface']
 assert ' '.join(s['surface'] for s in segments)==h['spaced']
 assert h['inserted_at']==[s['span']['start'] for s in segments[1:]]
 cursor=record['span']['start']
 for s in segments:
  assert s['span']['start']==cursor;verify_segment(s,text,replay);cursor=s['span']['end']
 assert cursor==record['span']['end']
 # Homonyms remain visible, but a reviewed bound-noun entry must license the
 # first lemma of at least one independent right-segment analysis.
 right=segments[-1];backed=False
 for a,r in zip(right['analysis']['analyses'],right['dictionary']['readings'],strict=True):
  lemma=a['lemmas'][0];ident=PROFILE_IDS.get(lemma['text'])
  if ident is None:continue
  member=next(m for m in right['dictionary']['lemmas'] if m['lemma']==lemma)
  backed|=any(e['id']==ident and e['pos']=='의존 명사' for e in member['entries']) and any(e['id']==ident and e['status']!='incompatible' for e in r['lemmas'][0]['entries'])
 assert backed,'source-specific right noun license missing'
 contexts=h.get('joined_contexts',[]);spans=set()
 for c in contexts:
  s=c['span'];assert record['span']['start']<=s['start']<s['end']<right['span']['end']
  assert s['end']==right['span']['start'],'joined auxiliary context includes noun or ends early'
  key=(s['start'],s['end']);assert key not in spans;spans.add(key)
  verify_segment(c,text,replay)
  assert all(any(l['kind']=='auxiliary' for l in a['lemmas']) for a in c['analysis']['analyses'])
def verify(report,fixture,closure):
 assert report['fixture']==fixture and report['closure_sha256']==sha(closure)
 cases=fixture['cases'];assert len(cases)==50 and len({c['id'] for c in cases})==50
 assert fixture['original_proposal']==read(ROOT/'tests/fixtures/predicate-auxiliary-spacing-owner-cases.json')['cases'][9]
 assert report['state']=='verified' and report['inputs_unchanged']
 observations=[];seen=set();spacing={}
 for run in report['runs']:
  key=(run['encoding'],run['mode'],run['cache_bytes']);assert key not in seen;seen.add(key)
  text='前🙂「'+' '.join(unicodedata.normalize(run['encoding'],c['surface']) for c in cases)+'」';assert run['text']==text
  before,after=run['before'],run['after']
  assert before==[{k:v for k,v in r.items() if k!='spacing'} for r in after],'raw word candidates/dictionary changed'
  old=run['baseline_spacing'];assert len(old)==len(after)
  for a,b in zip(old,after,strict=True):
   assert {k:v for k,v in a.items() if k!='spacing'}=={k:v for k,v in b.items() if k!='spacing'}
   if 'spacing' in a:assert [h for h in b['spacing']['alternatives'] if h in a['spacing']['alternatives']]==a['spacing']['alternatives'],'prior option loss/reorder'
  words={r['analysis']['normalized']:r for r in after if r.get('analysis')}
  assert set(words)=={c['surface'] for c in cases}|{'前'}
  this={w:r['spacing'] for w,r in words.items()}
  if run['encoding'] in spacing:assert spacing[run['encoding']]==this,'filter/cache spacing changed'
  else:spacing[run['encoding']]=this
  for c in cases:
   record=words[c['surface']];assert record['spacing']['complete'],'finite search incomplete'
   hypotheses=[h for h in record['spacing']['alternatives'] if h.get('rule')==RULE]
   spaces={unicodedata.normalize('NFC',h['spaced']) for h in hypotheses}
   assert set(c['required_spaces'])<=spaces,(c['id'],'required corrected option missing')
   if not c['required_spaces']:assert not hypotheses,(c['id'],'outside finite template')
   for h in hypotheses:verify_hypothesis(h,record,text,report['independent_replay'])
   observations.append({'case_id':c['id'],'encoding':run['encoding'],'mode':run['mode'],'cache_bytes':run['cache_bytes'],'required':c['required_spaces'],'actual':sorted(spaces)})
  target=words[fixture['original_proposal']['surface']]
  assert fixture['original_proposal']['required_space'] not in {unicodedata.normalize('NFC',h['spaced']) for h in target['spacing']['alternatives']},'original proposal silently certified'
 assert seen=={(e,m,c) for e in ['NFC','NFD'] for m in MODES for c in [0,1,4096]}
 assert report['observations']==observations
 assert report['original_unmet_requirement']==fixture['original_proposal'] and not report['full_coverage_complete']
 if report['api']:
  assert set(report['api'])=={'NFC','NFD'}
  for encoding,api in report['api'].items():
   run=next(r for r in report['runs'] if r['encoding']==encoding and r['mode']=='raw' and r['cache_bytes']==4096)
   assert api['records']==run['after'],'API/CLI parity'
   assert api['rules'][RULE] and api['rules']['auxiliary'],'new rule/context metadata missing'
  assert report['native']==read(closure)['complete_native_entries'] and len(report['native'])==135
 return {'runs':len(seen),'observations':len(observations),'native_entries':len(report['native']),'finite_requirements_passed':True,'full_coverage_complete':False,'original_unmet_requirement':fixture['original_proposal']}
def capture(args):
 fixture=read(args.fixture);frozen={str(p.resolve()):sha(p) for p in [args.cli,args.baseline,args.dictionary,args.fixture,args.closure,Path(__file__)]}
 report={'state':'verified','fixture':fixture,'closure_sha256':sha(args.closure),'runs':[],'api':{},'native':{},'independent_replay':{},'frozen_inputs':frozen,'observations':[],'original_unmet_requirement':fixture['original_proposal'],'full_coverage_complete':False,'scope':'Isolated finite source-profile boundaries, exact prior words/options, CLI/API/Native/Unicode/filter/cache observations. Original malformed two-word proposal retained. Root/Nix, wider profiles, intended spacing, contextual sense and independent language review remain separate.'}
 def cli(binary,cmd,text=None):
  job=subprocess.run([str(binary.resolve()),*cmd,'--dictionary',str(args.dictionary.resolve())],input=None if text is None else text.encode(),capture_output=True,check=True);assert not job.stderr;return [json.loads(l) for l in job.stdout.splitlines()]
 def post(route,data):
  request=urllib.request.Request(args.url.rstrip('/')+'/api/'+route,data=json.dumps(data,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=60) as response:return json.load(response)
 for encoding in ['NFC','NFD']:
  text='前🙂「'+' '.join(unicodedata.normalize(encoding,c['surface']) for c in fixture['cases'])+'」'
  if args.url:report['api'][encoding]=post('analyze',{'text':text,'suggest_spacing':True})
  for mode,flags in MODES.items():
   for cache in [0,1,4096]:
    command=['text','-',*flags,'--cache-bytes',str(cache)]
    before=cli(args.cli,command,text);old=cli(args.baseline,command+['--suggest-spacing'],text);after=cli(args.cli,command+['--suggest-spacing'],text)
    report['runs'].append({'encoding':encoding,'mode':mode,'cache_bytes':cache,'text':text,'command':command,'before':before,'baseline_spacing':old,'after':after})
    words={r['analysis']['normalized']:r for r in after if r.get('analysis')}
    for case in fixture['cases']:
     hypotheses=[h for h in words[case['surface']]['spacing']['alternatives'] if h.get('rule')==RULE]
     report['observations'].append({'case_id':case['id'],'encoding':encoding,'mode':mode,'cache_bytes':cache,'required':case['required_spaces'],'actual':sorted({unicodedata.normalize('NFC',h['spaced']) for h in hypotheses})})
     for h in hypotheses:
      for s in h['records']+h.get('joined_contexts',[]):
       if s['surface'] not in report['independent_replay']:report['independent_replay'][s['surface']]=cli(args.baseline,['word',s['surface'],'--dict-compatible'])[0]
 if args.url:
  for ident in read(args.closure)['complete_native_entries']:report['native'][ident]=post('entry',{'id':ident})['entry']
 report['inputs_unchanged']=all(sha(p)==h for p,h in frozen.items())
 report['producer']={'text':Path(__file__).read_text(),'sha256':sha(__file__)}
 with args.output.open('xb') as f:f.write(gzip.compress((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,default=ROOT)
 for name in ['fixture','closure']:p.add_argument('--'+name,type=Path,required=True)
 for name in ['cli','baseline','dictionary','output','verify']:p.add_argument('--'+name,type=Path)
 p.add_argument('--url');args=p.parse_args();ROOT=args.root.resolve()
 report=read(args.verify) if args.verify else capture(args)
 print(json.dumps(verify(report,read(args.fixture),args.closure),ensure_ascii=False))
