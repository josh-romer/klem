"""Independently verify complete self-question source, importer and case evidence."""
import gzip,hashlib,json
from pathlib import Path
from native_lmf import entry
ROOT=Path(__file__).resolve().parents[1]
def read(path):
 p=Path(path);return json.loads(gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes())
def inspect(prepared,closure,native,proposals,suite,labels):
 original=prepared['complete_imported_entries'];endings=['krdict:73881','krdict:73882','krdict:73883','krdict:73891']
 assert set(original)==set(endings)|{'krdict:91482','krdict:88906'},'separate ending/suffix identities'
 assert all(original[i]['pos']=='어미' for i in endings),'ending roles'
 assert all(original[i]['pos']=='접사' for i in ['krdict:91482','krdict:88906']),'suffix roles'
 projected={}
 for raw in native['LexicalResource']['Lexicon']['LexicalEntry']:
  value=entry(raw);assert value['id'] not in projected,'Native identity collision';projected[value['id']]=value
 assert projected==closure['entries'] and len(projected)==51,'complete Native projection'
 assert all(projected[i]==e for i,e in original.items()),'original source entries'
 groups=[];text=''
 for ident in endings:
  for sense in original[ident]['senses']:
   for ordinal,examples in enumerate(sense['examples'],1):
    start=len(text.encode());block='\n'.join(examples);text+=block+'\n'
    groups.append({'id':f"self-question-source-{ident.split(':')[1]}-{sense['id']}-{ordinal}",'entry_id':ident,'sense_id':sense['id'],'group':ordinal,'complete_original_examples':examples,'span':{'start':start,'end':start+len(block.encode())}})
 assert groups==prepared['complete_groups'] and len(groups)==21,'all complete original groups'
 assert text==prepared['complete_source_text'],'complete source text'
 assert proposals==prepared['proposals'] and len(proposals)==21,'original proposals'
 assert {p['source_group_id'] for p in proposals}=={g['id'] for g in groups},'complete proposal coverage'
 assert len(suite['cases'])==29 and len({c['id'] for c in suite['cases']})==29,'stable case identities'
 by_id={c['id']:c for c in suite['cases']}
 for p in proposals:
  c=by_id[p['id']];assert c['surface']==p['surface'],'case source surface'
  j=c['judgments'][0];assert p['proposed_lemma'] in j['lemmas'] and j['verdict']=='required' and j['required_rules']==['ending.self_question'],'authored exact source requirement'
 counts={v:sum(j['verdict']==v for c in suite['cases'] for j in c['judgments']) for v in ['required','forbidden']}
 assert counts=={'required':25,'forbidden':4},'finite judgment counts'
 for form,ids in [('는담',[73881,73882]),('담',[73883]),('남',[73891])]:
  label=labels['-'+form];assert label['kind']=='ending' and label['label']=='Self-question / complaint','display role'
  assert [s['id'] for s in label['sources']]==ids,'display source identities'
  assert all(s['headword']==original['krdict:'+str(s['id'])]['headword'] and s['pos']=='어미' for s in label['sources']),'display source roles'
 assert projected['krdict:63516']['headword']=='웃기다' and projected['krdict:63516']['pos']=='동사','retained source tension owner'
 assert any('웃기담' in line for s in original['krdict:73883']['senses'] for g in s['examples'] for line in g),'independent tension attestation'
 return {'complete_groups':21,'native_entries':51,'required':25,'forbidden':4,'independent_contextual_review_complete':False}
def inputs():
 return [read(ROOT/p) for p in ['docs/self-question-source-preparation-retry1.json.gz','docs/self-question-native-closure-retry2.json.gz','tests/fixtures/self-question-native.json','tests/fixtures/self-question-proposals.json','tests/fixtures/self-question-validity.json','web/src/grammar-labels.json']]
if __name__=='__main__':print(inspect(*inputs()))
