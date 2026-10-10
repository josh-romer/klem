"""Verify full broad receipts and every changed path, context and spacing segment."""
import gzip,hashlib,json
from pathlib import Path
from native_lmf import entry
from predicate_auxiliary_spacing_runtime import verify_segment
ROOT=Path(__file__).resolve().parents[1]
sha=lambda value:hashlib.sha256(value).hexdigest()
def read(path):
 raw=Path(path).read_bytes();return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)
def inspect(report,prior,sources,native,entries,history):
 assert report['state']=='draft-complete-broad-preservation-passed' and report['inputs_unchanged'] and not report['full_coverage_complete'],'actual terminal broad receipt'
 assert sha(report['producer']['text'].encode())==report['producer']['sha256'],'actual producer bytes'
 projected={entry(raw)['id']:entry(raw) for raw in native['LexicalResource']['Lexicon']['LexicalEntry']}
 assert projected==entries and len(projected)==len(native['LexicalResource']['Lexicon']['LexicalEntry']),'complete original Native owners'
 assert all(entries[k]==v for k,v in report['complete_native_entries'].items()),'complete path Native entries'
 observations=[];spacing=[];owners=set()
 def summaries(values):
  for owner in values:
   for summary in owner['entries']:
    owners.add(summary['id']);full=entries[summary['id']]
    assert all(summary[k]==full[k] for k in ['id','headword','homonym','pos']),'exact Native owner summary'
 def inspect_record(old,new,location,added,options):
  assert {k:v for k,v in old.items() if k not in ['analysis','dictionary','spacing','breakdowns']}=={k:v for k,v in new.items() if k not in ['analysis','dictionary','spacing','breakdowns']},'original frame fields'
  if old.get('analysis') is None:
   assert old==new,'unaltered nonword';return
  a,b=old['analysis'],new['analysis']
  assert {k:v for k,v in a.items() if k!='analyses'}=={k:v for k,v in b.items() if k!='analyses'},'original analysis fields'
  assert [p for p in b['analyses'] if p in a['analyses']]==a['analyses'],'old candidate preservation and order'
  od,nd=old['dictionary'],new['dictionary']
  assert {k:v for k,v in od.items() if k not in ['lemmas','readings']}=={k:v for k,v in nd.items() if k not in ['lemmas','readings']},'original dictionary identity'
  assert all(o in nd['lemmas'] for o in od['lemmas']),'old dictionary owners'
  assert len(nd['readings'])==len(b['analyses']),'one assessment per path'
  for i,path in enumerate(a['analyses']):
   j=b['analyses'].index(path)
   assert od['readings'][i]==nd['readings'][j],'old dictionary assessments'
   if 'breakdowns' in old:assert old['breakdowns'][i]==new['breakdowns'][j],'old diagram preservation'
  for i,path in enumerate(b['analyses']):
   if path in a['analyses']:continue
   assert 'ending.reported_experience' in path['rules'],'new rule attribution'
   matches=[next(o for o in nd['lemmas'] if o['lemma']==lemma) for lemma in path['lemmas']]
   summaries(matches)
   added.append({'location':location,'surface':new['surface'],'span':new['span'],'analysis':path,'dictionary_assessment':nd['readings'][i],'dictionary_owners':matches,'contextual_verdict':'unjudged','independent_review':'pending'})
  if 'spacing' not in old:return
  os,ns=old['spacing'],new['spacing']
  assert os['rule']==ns['rule'] and os['limits']==ns['limits'],'spacing limits and rule'
  key=lambda h:(h.get('rule'),h['spaced'],tuple(h['inserted_at']))
  oldkeys=[key(h) for h in os['alternatives']]
  assert [key(h) for h in ns['alternatives'] if key(h) in oldkeys]==oldkeys,'old spacing boundary preservation'
  for h in os['alternatives']:
   nh=next(t for t in ns['alternatives'] if key(t)==key(h))
   assert {k:v for k,v in h.items() if k not in ['records','joined_contexts']}=={k:v for k,v in nh.items() if k not in ['records','joined_contexts']},'old spacing hypothesis'
   for field in ['records','joined_contexts']:
    assert len(h.get(field,[]))==len(nh.get(field,[])),'old spacing segment count'
    for i,(s,t) in enumerate(zip(h.get(field,[]),nh.get(field,[]),strict=True)):inspect_record(s,t,location+'/'+field+'/'+str(i),added,options)
  for h in ns['alternatives']:
   if key(h) in oldkeys:continue
   pieces=h['records']+h.get('joined_contexts',[])
   assert any('ending.reported_experience' in p['rules'] for r in pieces for p in r['analysis']['analyses']),'new boundary reported experience witness'
   assert ''.join(r['surface'] for r in h['records'])==new['surface'] and h['spaced']==' '.join(r['surface'] for r in h['records']),'new spacing exact original surface'
   assert h['inserted_at']==[r['span']['start'] for r in h['records'][1:]],'new spacing byte boundaries'
   for piece in pieces:
    summaries(piece['dictionary']['lemmas'])
    verify_segment(piece,current_text,report['independent_spacing_replay'])
   options.append({'location':location,'hypothesis':h,'original_surface':new['surface'],'original_span':new['span']})
 assert len(report['comparisons'])==len(prior['comparisons'])==8,'all original workloads'
 assert sum(r['records'] for r in report['comparisons'])==1128312,'complete original frames'
 for run,previous in zip(report['comparisons'],prior['comparisons'],strict=True):
  assert (run['source'],run['source_sha256'],run['mode'],run['records'],run['before_jsonl_sha256'])==(previous['source'],previous['source_sha256'],previous['mode'],previous['records'],previous['after_jsonl_sha256']),'actual complete previous stream'
  assert run['exit_codes']==[0,0] and run['original_bytes_conserved'],'complete stream execution'
  current_text=sources['sources'][run['source']]['text'];original=current_text.encode()
  assert sha(original)==run['source_sha256'],'complete original source text'
  flags=['--dict-compatible'] if 'compatible' in run['mode'] else ['--dict-only'] if 'headword' in run['mode'] else []
  if 'spacing' in run['mode']:flags.append('--suggest-spacing')
  assert all(c[1]=='text' and c[3]=='--dictionary' and c[5:]==flags for c in run['commands']),'actual workload flags'
  if not run['changed_frames']:assert run['after_jsonl_sha256']==run['before_jsonl_sha256'],'unchanged full stream hash'
  previous_record=0
  for frame in run['changed_frames']:
   record=frame['record'];assert previous_record<record<=run['records'],'original frame ordering';previous_record=record
   before,after=frame['before'],frame['after'];span=after['span']
   assert original[span['start']:span['end']].decode()==after['surface'],'original source span'
   left=original.rfind(b'\n',0,span['start'])+1;right=original.find(b'\n',span['end']);line=original[left:right if right>=0 else len(original)].decode()
   assert frame['complete_original_line']==line,'complete original context'
   added=[];options=[];inspect_record(before,after,'word',added,options)
   assert len(added)==frame['added_paths'] and len(options)==frame['added_spacing_options'],'individual change counts'
   for addition in added:
    ident=sha(json.dumps([run['source_sha256'],run['mode'],record,addition],ensure_ascii=False,sort_keys=True).encode())[:24]
    observations.append({'id':'reported-experience-broad-'+ident,'source':run['source'],'source_sha256':run['source_sha256'],'mode':run['mode'],'record':record,'complete_original_line':line,**addition})
   for option in options:
    ident=sha(json.dumps([run['source_sha256'],run['mode'],record,option],ensure_ascii=False,sort_keys=True).encode())[:24]
    spacing.append({'id':'reported-experience-broad-spacing-'+ident,'source':run['source'],'source_sha256':run['source_sha256'],'mode':run['mode'],'record':record,'complete_original_line':line,'contextual_verdict':'unjudged','independent_review':'pending',**option})
 assert observations==report['individual_additions'] and len(observations)==len({o['id'] for o in observations})==16,'complete individual additions and evidence'
 assert spacing==report['individual_spacing_additions'] and len(spacing)==len({o['id'] for o in spacing})==0,'complete individual spacing observations'
 assert owners==set(entries),'complete Native owner closure'
 assert history['individual_additions']==observations and history['individual_spacing_additions']==spacing and history['complete_native_entries']==report['complete_native_entries'] and history['independent_spacing_replay']==report['independent_spacing_replay'],'exact individual regression fixture'
 raw=next(r for r in report['comparisons'] if r['mode']=='novel-raw')
 assert history['raw_changed_frames']==raw['changed_frames'] and history['source_sha256']==raw['source_sha256'],'exact novel frame regression fixture'
 return {'frames':1128312,'individual_paths':16,'spacing_observations':0,'native_entries':len(entries),'contextual_and_independent_review':'pending'}
def inputs():
 return [read(ROOT/p) for p in ['docs/reported-experience-broad.json.gz','docs/formal-b-broad.json.gz','docs/reported-deoni-broad-inputs.json.gz','tests/fixtures/reported-experience-novel-native.json','tests/fixtures/reported-experience-novel-entries.json','tests/fixtures/reported-experience-novel-history.json']]
if __name__=='__main__':print(inspect(*inputs()))
