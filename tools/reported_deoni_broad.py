"""Check captured broad additions, stable observations and complete Native evidence offline."""
import copy,gzip,hashlib,json,sys
from pathlib import Path
from native_lmf import entry,verify_native_lmf
from reported_deoni_parent import actual_parent, frame
parents = {}
ROOT=Path(__file__).resolve().parents[1]
read=lambda p:json.loads(gzip.decompress(Path(p).read_bytes()))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def native_closure(native):
 assert native['complete_native_entries'].keys()==native['original_lmf'].keys()
 for ident,raw in native['original_lmf'].items():assert entry(raw)==native['complete_native_entries'][ident]
 verify_native_lmf(native['english_projection'],native['complete_native_entries'])

 for name in ['reported-deoni-native-closure.json.gz','reported-deoni-source-preparation.json.gz','reported-command-deoni-source-preparation.json.gz']:
  assert native['source_hashes']==read(ROOT/'docs'/name)['source_hashes']

def observations(report,native):
 prior=read(ROOT/'docs/copula-expectation-broad.json.gz')
 assert report['prior_capture_sha256']==sha(ROOT/'docs/copula-expectation-broad.json.gz')
 assert len(report['comparisons'])==len(prior['comparisons'])==8
 parents.clear();parents.update(report['actual_prior_companions']);expected=[]
 for run,old in zip(report['comparisons'],prior['comparisons'],strict=True):
  assert (run['source'],run['source_sha256'],run['mode'],run['records'],run['before_jsonl_sha256'])==(old['source'],old['source_sha256'],old['mode'],old['records'],old['after_jsonl_sha256'])
  assert run['exit_codes']==[0,0] and run['original_bytes_conserved']
  inputs=read(ROOT/'docs/reported-deoni-broad-inputs.json.gz')['sources']
  original=inputs[run['source']]['text'].encode();assert hashlib.sha256(original).hexdigest()==run['source_sha256']==inputs[run['source']]['sha256']
  previous_record=0
  for changed in run['changed_frames']:
   record=changed['record'];assert previous_record<record<=run['records'];previous_record=record
   b,a=changed['before'],changed['after'];paths=frame(b,a,parents);assert paths
   span=a['span'];assert original[span['start']:span['end']].decode()==a['surface']
   left=original.rfind(b'\n',0,span['start'])+1;right=original.find(b'\n',span['end']);right=len(original) if right<0 else right
   line=original[left:right].decode()
   for candidate in paths:
    parent_surface,parent=actual_parent(a['analysis']['normalized'],candidate,parents)
    ident=hashlib.sha256(json.dumps([run['source_sha256'],run['mode'],record,candidate],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
    assessment=a['dictionary']['readings'][a['analysis']['analyses'].index(candidate)];owners=[]
    for lemma in candidate['lemmas']:
     matching=next((item for item in a['dictionary']['lemmas'] if item['lemma']==lemma),None)
     ids=[owner['id'] for owner in matching['entries']] if matching else []
     for owner in ids:assert owner in native['complete_native_entries'],owner
     owners.append({'lemma':lemma,'entry_ids':ids})
    expected.append({'id':'reported-deoni-broad-'+ident,'source':run['source'],'source_sha256':run['source_sha256'],'mode':run['mode'],'record':record,'surface':a['surface'],'span':span,'complete_original_line':line,'analysis':candidate,'dictionary_assessment':assessment,'native_owners':owners,'parent_surface':parent_surface,'exact_parent':parent,'contextual_verdict':'unjudged','independent_review':'pending'})
 assert report['individual_additions']==expected
 assert len(expected)==len({r['id'] for r in expected})
 return len(expected)

def rejected(action,label):
 try:action()
 except (AssertionError,KeyError):print('Rejected corruption:',label,flush=True);return
 raise AssertionError('Corruption accepted: '+label)

if __name__=='__main__':
 report=read(ROOT/'docs/reported-deoni-prototype-broad.json.gz');native=read(ROOT/'docs/reported-deoni-observation-native.json.gz')
 assert report['inputs_unchanged'] and native['inputs_unchanged']

 assert report['frozen_inputs']['/home/josh/projects/klem/docs/copula-expectation-broad.json.gz']==sha(ROOT/'docs/copula-expectation-broad.json.gz')
 assert report['frozen_inputs']['/tmp/klem_reported_deoni_validation.py']==sha(ROOT/'docs/reported-deoni-prototype-parent.py.txt')
 source=read(ROOT/'docs/reported-deoni-prototype-source-streams.json.gz')
 assert report['cli_sha256']==source['frozen_inputs']['/home/josh/projects/klem/web/test-results/reported-command-deoni-prototype-cargo/debug/klem']
 assert report['before_cli_sha256']==source['frozen_inputs']['/nix/store/al7vdmyi8h0gsjbnz59qab3vvskkrj0l-klem-0.1.0/bin/klem']
 native_closure(native);count=observations(report,native)
 print('Audited all eight captured comparisons and',count,'exact individual additions;',len(native['complete_native_entries']),'complete Native/LMF/SQL-projected owners.',flush=True)
 changed=copy.deepcopy(report);changed['individual_additions'].pop();rejected(lambda:observations(changed,native),'missing individual novel observation')
 changed=copy.deepcopy(report);changed['individual_additions'][0]['complete_original_line']='fabricated';rejected(lambda:observations(changed,native),'changed original novel context')
 needed=next(i for row in report['individual_additions'] for owner in row['native_owners'] for i in owner['entry_ids']);saved=native['complete_native_entries'].pop(needed)
 try:rejected(lambda:observations(report,native),'missing novel dictionary owner')
 finally:native['complete_native_entries'][needed]=saved
