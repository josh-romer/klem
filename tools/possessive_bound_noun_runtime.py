"""Capture nominal possession/cause hypotheses and unchanged independent readings."""
import argparse,gzip,hashlib,json,os,subprocess,sys,unicodedata,urllib.request
from pathlib import Path
ROOT=Path(os.environ.get('KLEM_ROOT',Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(ROOT/'tools'))
from predicate_auxiliary_spacing_runtime import verify_segment
RULE='spacing.nominal_bound_noun'
MODES={'raw':[],'headword':['--dict-only'],'compatible':['--dict-compatible']}
PROFILE_IDS={'것':'krdict:62835','때문':'krdict:64555'}
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
 assert not h.get('joined_contexts'), 'nominal template cannot invent auxiliary context'
 def licensed(segment,a,ids=None,poses=('명사','대명사')):
  lemma=a['lemmas'][0];member=next(m for m in segment['dictionary']['lemmas'] if m['lemma']==lemma)
  reading=segment['dictionary']['readings'][segment['analysis']['analyses'].index(a)]
  statuses={e['id']:e['status'] for e in reading['lemmas'][0]['entries']}
  return any(e['headword']==lemma['text'] and e['pos'] in poses and (ids is None or e['id'] in ids) and statuses.get(e['id'],'incompatible')!='incompatible' for e in member['entries'])
 def genitive(a):return bool(a['morphemes']) and a['morphemes'][-1]=={'form':'의','kind':'particle'}
 def bare(a):return len(a['lemmas'])==1 and all(m['kind']=='suffix' and m['form']=='들' for m in a['morphemes']) and a['lemmas'][0]['kind'] in {'nominal','unclassified'}
 last=segments[-2]
 if right['analysis']['analyses'][0]['lemmas'][0]['text']=='것':
  ids={'krdict:17182':'대명사','krdict:62078':'대명사','krdict:31971':'명사','krdict:29742':'명사','krdict:70748':'명사','krdict:27375':'명사','krdict:62818':'명사'}
  assert all((genitive(a) and licensed(last,a,poses=('명사','대명사','동사','형용사'))) or (bare(a) and any(licensed(last,a,{ident},(pos,)) for ident,pos in ids.items())) for a in last['analysis']['analyses']), 'possession owner license'
 else:
  assert all((genitive(a) and licensed(last,a,poses=('명사','대명사','동사','형용사'))) or (bare(a) and licensed(last,a)) for a in last['analysis']['analyses']), 'cause owner license'


def verify(report,fixture,closure):
 assert report['fixture']==fixture and report['closure_sha256']==sha(closure)
 cases=fixture['cases'];assert len(cases)==42 and len({c['id'] for c in cases})==42
 gap=next(c for c in cases if c['id']=='surname-teacher')
 assert gap['required_spaces']==['박 선생님 것'] and gap['known_unmet'] and gap['source_entry']=='krdict:62835' and gap['source_sense']=='3', 'original surname proposal erased or redefined'
 native=read(closure)['complete_native_entries'];source=next(s for s in native['krdict:62835']['senses'] if s['id']=='3')
 assert any('박 선생님 것' in example for group in source['examples'] for example in group), 'complete original source proposal missing'
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
   missing=sorted(set(c['required_spaces'])-spaces)
   if missing:assert c['id']=='surname-teacher' and c.get('known_unmet'),(c['id'],'unexpected unmet requirement')
   if c.get('known_unmet'):assert missing==c['required_spaces'], 'unrelated gourd/night dictionary entries borrowed for surname'
   if not c['required_spaces'] and not c.get('allow_other_spacing_hypotheses'):assert not hypotheses,(c['id'],'outside finite template')
   assert not (set(c.get('forbidden_spaces',[])) & spaces),(c['id'],'forbidden direct nominal interpretation')
   for h in hypotheses:verify_hypothesis(h,record,text,report['independent_replay'])
   observations.append({'case_id':c['id'],'encoding':run['encoding'],'mode':run['mode'],'cache_bytes':run['cache_bytes'],'required':c['required_spaces'],'actual':sorted(spaces),'missing':missing})
 assert seen=={(e,m,c) for e in ['NFC','NFD'] for m in MODES for c in [0,1,4096]}
 assert report['observations']==observations
 assert report['unmet_requirements']==sorted({o['case_id'] for o in observations if o['missing']})
 assert not report['full_coverage_complete']
 if report['api']:
  assert set(report['api'])=={'NFC','NFD'}
  for encoding,api in report['api'].items():
   run=next(r for r in report['runs'] if r['encoding']==encoding and r['mode']=='raw' and r['cache_bytes']==4096)
   assert api['records']==run['after'],'API/CLI parity'
   assert api['rules'][RULE],'new rule metadata missing'
  assert report['native']==read(closure)['complete_native_entries'] and len(report['native'])==len(read(closure)['complete_native_entries'])
 return {'runs':len(seen),'observations':len(observations),'native_entries':len(report['native']),'observations_verified':True,'finite_requirements_passed':not report['unmet_requirements'],'unmet_requirements':report['unmet_requirements'],'full_coverage_complete':False}
def capture(args):
 fixture=read(args.fixture);frozen={str(p.resolve()):sha(p) for p in [args.cli,args.baseline,args.dictionary,args.fixture,args.closure,Path(__file__)]}
 report={'state':'verified','fixture':fixture,'closure_sha256':sha(args.closure),'runs':[],'api':{},'native':{},'independent_replay':{},'frozen_inputs':frozen,'observations':[],'unmet_requirements':[],'full_coverage_complete':False,'scope':'Complete nominal/possessive finite requirements, all original source groups retained; contextual sense and independent review pending.'}
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
     spaces={unicodedata.normalize('NFC',h['spaced']) for h in hypotheses};missing=sorted(set(case['required_spaces'])-spaces)
     report['observations'].append({'case_id':case['id'],'encoding':encoding,'mode':mode,'cache_bytes':cache,'required':case['required_spaces'],'actual':sorted(spaces),'missing':missing})
     for h in hypotheses:
      for s in h['records']+h.get('joined_contexts',[]):
       if s['surface'] not in report['independent_replay']:report['independent_replay'][s['surface']]=cli(args.baseline,['word',s['surface'],'--dict-compatible'])[0]
 if args.url:
  for ident in read(args.closure)['complete_native_entries']:report['native'][ident]=post('entry',{'id':ident})['entry']
 report['unmet_requirements']=sorted({o['case_id'] for o in report['observations'] if o['missing']})
 report['inputs_unchanged']=all(sha(p)==h for p,h in frozen.items())
 report['producer']={'text':Path(__file__).read_text(),'sha256':sha(__file__)}
 with args.output.open('xb') as f:f.write(gzip.compress((json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
 return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['fixture','closure']:p.add_argument('--'+name,type=Path,required=True)
 for name in ['cli','baseline','dictionary','output','verify']:p.add_argument('--'+name,type=Path)
 p.add_argument('--url');p.add_argument('--require-complete',action='store_true');args=p.parse_args()
 report=read(args.verify) if args.verify else capture(args)
 print(json.dumps(verify(report,read(args.fixture),args.closure),ensure_ascii=False))

 if args.require_complete and report['unmet_requirements']:raise SystemExit(1)
