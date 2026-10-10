"""Verify original expression identities, full contexts and explicit judgment scopes."""
import gzip,hashlib,json
from pathlib import Path
from native_lmf import entry
ROOT=Path(__file__).resolve().parents[1]
OWNERS={86336,86337,86338,86339,86674,86678,86680,86683,86687,86692}
LABELS={'답디까':[86678],'답디다':[86674],'는답디까':[86680,86687],'는답디다':[86683,86692],'랍디까':[86337],'랍디다':[86339],'으랍디까':[86336,86337],'으랍디다':[86338,86339]}
def read(name):
 p=ROOT/name;raw=p.read_bytes();return json.loads(gzip.decompress(raw) if p.suffix=='.gz' else raw)
def inspect(prepared,closure,native,proposals,suite,conditional,original,labels,label_native):
 sources=prepared['complete_imported_entries'];assert set(sources)=={'krdict:'+str(i) for i in OWNERS},'all ten original sources'
 assert all(v['pos']=='품사 없음' for v in sources.values()),'original expression POS retained'
 values=native['LexicalResource']['Lexicon']['LexicalEntry'];projected={entry(v)['id']:entry(v) for v in values}
 assert len(projected)==len(values)==92 and projected==closure['entries'],'complete original Native closure'
 for ident,raw in prepared['original_native_entries'].items():
  assert entry(raw)==sources[ident]==projected[ident],'complete original expression projection'
  assert raw==next(v for v in values if v['val']==raw['val']),'original expression LMF unchanged'
 text='';groups=[]
 for ident,value in sources.items():
  for sense in value['senses']:
   for ordinal,examples in enumerate(sense['examples'],1):
    start=len(text.encode());block='\n'.join(examples);text+=block+'\n'
    groups.append({'id':f"reported-experience-source-{ident.split(':')[1]}-{sense['id']}-{ordinal}",'entry_id':ident,'sense_id':sense['id'],'group':ordinal,'complete_original_examples':examples,'span':{'start':start,'end':start+len(block.encode())},'contextual_verdict':'unjudged','independent_review':'pending'})
 assert prepared['complete_groups']==groups and len(groups)==51,'all complete original groups and ordering'
 assert text==prepared['complete_source_text'] and hashlib.sha256(text.encode()).hexdigest()==prepared['source_text_sha256'],'complete original text and byte hash'
 assert len(proposals)==len({p['id'] for p in proposals})==51,'all authored source proposals'
 assert {p['source_group_id'] for p in proposals}=={g['id'] for g in groups},'one proposal per complete group'
 cases={c['id']:c for c in suite['cases']};assert len(cases)==len(suite['cases'])==97,'unique raw scoped cases'
 assert {v:sum(j['verdict']==v for c in suite['cases'] for j in c['judgments']) for v in ['required','forbidden']}=={'required':79,'forbidden':18},'raw judgment scope'
 for p in proposals:
  group=next(g for g in groups if g['id']==p['source_group_id']);assert p['complete_original_group']==group['complete_original_examples'],'original authored context'
  offset=int(p['id'].rsplit('-',1)[1]);block='\n'.join(p['complete_original_group']).encode();assert block[offset:offset+len(p['surface'].encode())].decode()==p['surface'],'original source target byte offset'
  j=cases[p['id']]['judgments'][0]
  assert cases[p['id']]['surface']==p['surface'] and j['lemmas']==p['proposed_lemmas'] and j['morphemes']==p['proposed_morphemes'] and j['required_rules']==['ending.reported_experience'] and j['verdict']=='required','authored structural reading'
  assert suite['sources'][j['source']]==sources[p['entry_id']]['url'],'original case source identity'
 assert len(conditional['cases'])==2 and all(c['id'].endswith('-adjectival-command') for c in conditional['cases']),'two retained dictionary-dependent cases'
 excluded={c['id']:c for c in conditional['cases']};assert not set(cases)&set(excluded),'conditional scope not raw gold'
 assert len(original['cases'])==99 and [c for c in original['cases'] if c['id'] not in excluded]==suite['cases'] and [c for c in original['cases'] if c['id'] in excluded]==conditional['cases'],'complete original judgments and scope dispositions'
 assert original['sources']==suite['sources'],'original judgment source links'
 tension=next(p for p in proposals if p['surface']=='했답디까');assert tension['entry_id']=='krdict:86687' and tension['proposed_morphemes']==['었','답디까'] and tension['source_tension'],'original cross-source past categorization tension'
 originals={entry(v)['id']:v for v in label_native['LexicalResource']['Lexicon']['LexicalEntry']};assert set(originals)==set(sources),'all label source identities'
 assert all(originals[k]==prepared['original_native_entries'][k] for k in sources),'complete original label LMF'
 for form,ids in LABELS.items():
  label=labels['-'+form];assert label['kind']=='ending' and label['sources']==[{'id':i,'headword':sources['krdict:'+str(i)]['headword'],'pos':'품사 없음'} for i in ids],'exact label owner role and identity'
 return {'sources':10,'complete_original_groups':51,'native_entries':92,'raw_cases':97,'native_conditional_cases':2,'required':79,'forbidden':18,'contextual_and_independent_review':'pending'}
def inputs():
 return [read(p) for p in ['docs/reported-experience-source-preparation.json.gz','docs/reported-experience-native-closure.json.gz','tests/fixtures/reported-experience-native.json','tests/fixtures/reported-experience-proposals.json','tests/fixtures/reported-experience-validity.json','tests/fixtures/reported-experience-native-conditional-cases.json','tests/fixtures/reported-experience-original-authored-cases.json','web/src/grammar-labels.json','tests/fixtures/krdict-reported-experience-labels.json']]
if __name__=='__main__':print(inspect(*inputs()))
