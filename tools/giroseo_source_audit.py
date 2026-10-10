"""Verify complete original concessive entries, source groups and authored judgments."""
import gzip,hashlib,json
from pathlib import Path
from native_lmf import entry
ROOT=Path(__file__).resolve().parents[1]
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):
 raw=Path(p).read_bytes();return json.loads(gzip.decompress(raw) if str(p).endswith('.gz') else raw)
def inspect(prepared,proposals,native,entries,suite,labels,label_native):
 assert prepared['state']=='complete-original-sources-preserved-no-engine-judgments','complete original preparation'
 assert sha(prepared['producer']['text'].encode())==prepared['producer']['sha256'],'original producer bytes'
 assert {entry(v)['id']:entry(v) for v in native['LexicalResource']['Lexicon']['LexicalEntry']}==entries==prepared['complete_imported_entries'] and len(entries)==32,'complete Native identities'
 assert {entry(v)['id']:v for v in native['LexicalResource']['Lexicon']['LexicalEntry']}==prepared['original_native_entries'],'lossless original LMF fields'
 assert sha(json.dumps(native,ensure_ascii=False,sort_keys=True).encode())=='75650a86160172a96ec45b89500255de69c16f1820b8a2dd2118847d24766921','exact preserved Native fixture bytes'
 assert list(prepared['expression_entries'])==['krdict:83919','krdict:83918'],'two separate source identities'
 expected=[]
 for ident,owner in prepared['expression_entries'].items():
  assert owner==entries[ident] and owner['pos']=='어미','exact source identity and POS'
  assert owner['notes']==['‘이다’, 동사와 형용사 또는 ‘-더-’, ‘-으리-’를 제외한 어미 뒤에 붙여 쓴다.'],'original excluded markers'
  for sense in owner['senses']:
   for ordinal,group in enumerate(sense['examples']):
    expected.append({'id':f'giroseo-{ident.split(":")[1]}-sense-{sense["id"]}-group-{ordinal+1}','source_entry_id':ident,'source_headword':owner['headword'],'sense_id':sense['id'],'group_ordinal':ordinal,'complete_original_group':group,'source_notes':owner['notes'],'sense_notes':sense['notes'],'definition':sense['definition']})
 assert prepared['complete_groups']==expected and len(expected)==8,'every complete original group and order'
 assert prepared['complete_source_text']=='\n'.join(line for g in expected for line in g['complete_original_group']),'complete source bytes and trailing spaces'
 assert proposals['state']=='independent-source-proposals-and-exact-baselines-preserved' and proposals['inputs_unchanged'],'terminal authored proposals'
 assert sha(proposals['producer']['text'].encode())==proposals['producer']['sha256'],'proposal producer bytes'
 rows=proposals['proposals'];assert len(rows)==8 and {p['source_group_id'] for p in rows}=={g['id'] for g in expected},'all source proposals'
 cases={c['id']:c for c in suite['cases']};assert len(cases)==len(suite['cases'])==48,'individual stable case IDs'
 assert {v:sum(j['verdict']==v for c in suite['cases'] for j in c['judgments']) for v in ['required','forbidden']}=={'required':34,'forbidden':14},'finite independent judgment counts'
 for p,g in zip(rows,expected,strict=True):
  assert p['source_group_id']==g['id'] and p['source_entry_id']==g['source_entry_id'] and p['complete_original_group']==g['complete_original_group'],'exact original proposal group'
  original='\n'.join(g['complete_original_group']).encode();start=p['surface_byte_offset'];assert isinstance(start,int) and start>=0 and original[start:start+len(p['surface'].encode())]==p['surface'].encode(),'original target byte location'
  assert set(p['baseline_records'])=={'raw','headword','compatible'},'complete pre-change mode records'
  c=cases[p['id']];j=c['judgments'][0]
  assert c['surface']==p['surface'] and j['lemmas']==p['proposed_lemmas'] and j['morphemes']==p['proposed_morphemes'] and j['required_rules']==['ending.concessive_giroseo'] and j['verdict']=='required','independent source judgment'
  assert suite['sources'][j['source']]==entries[p['source_entry_id']]['url'],'exact source judgment link'
  assert all(r['exit_code']==0 and r['analysis']['normalized']==p['surface'] for r in p['baseline_records'].values()),'actual source baseline'
 for ident in ['krdict:83919','krdict:83918']:
  owner=entries[ident];label=labels[owner['headword']]
  assert label['kind']=='ending' and label['sources']==[{'id':int(ident.split(':')[1]),'headword':owner['headword'],'pos':'어미'}],'exact label source and kind'
 assert {entry(v)['id']:v for v in label_native['LexicalResource']['Lexicon']['LexicalEntry']}=={ident:prepared['original_native_entries'][ident] for ident in ['krdict:83919','krdict:83918']},'two complete label owners without duplicate lexicals'
 return {'complete_groups':8,'native_entries':32,'required':34,'forbidden':14,'contextual_and_independent_review':'pending'}
def inputs():
 return [read(ROOT/p) for p in ['docs/giroseo-source-preparation.json.gz','docs/giroseo-proposals.json.gz','tests/fixtures/giroseo-native.json','tests/fixtures/giroseo-native-entries.json','tests/fixtures/giroseo-validity.json','web/src/grammar-labels.json','tests/fixtures/krdict-giroseo-labels.json']]
if __name__=='__main__':print(inspect(*inputs()))
