"""Freeze finite continuation-class judgments before changing dictionary policy.

All raw analyses and complete native source objects remain unchanged. English
LMF projections are importer adapters only. The existing eleven-word preflight
is historical evidence and must never be overwritten.
"""
import argparse,copy,hashlib,json,sqlite3,subprocess
from pathlib import Path
from excluded_paradigm_audit import array
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'tests/fixtures/continuation-left-sources.json'
LMF=ROOT/'tests/fixtures/krdict-continuation-left.json'
TARGETS=[('내다','어','내다','다','krdict:60625'),('나다','어','나니','으니','krdict:62134'),('나다','고','나니','으니','krdict:62134'),('나가다','어','나가다','다','krdict:26813'),('버리다','어','버리다','다','krdict:62601'),('치우다','어','치우다','다','krdict:74290')]
def sha(path):
 with Path(path).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def cases():
 result=[]
 def add(tag,surface,heads,kinds,forms,roles,verdict,source):
  result.append(dict(id='continuation-left-'+tag,surface=surface,judgments=[dict(id='path',lemmas=heads,lemma_kinds=kinds,morphemes=forms,morpheme_kinds=roles,verdict=verdict,source=source,reason='Scoped compatible-filter class judgment, not contextual grammaticality: this source requires a verbal immediate owner. Preserve verb homonyms and represented verbal later owners; explicit copulas/adjectival derivations and adjective entries conflict. Negatives inherit lexical classes. Missing classes and other restrictions remain independently unjudged.')]))
 for right,link,tail,ending,ident in TARGETS:
  source='continuation-left-'+ident.split(':')[1];key=right+'-'+link
  for tag,prefix,heads,kinds,verdict in [
   ('verb','먹어'if link=='어'else'먹고',['먹다'],['predicate'],'required'),
   ('adjective','좋아'if link=='어'else'좋고',['좋다'],['predicate'],'forbidden'),
   ('homonyms','커'if link=='어'else'크고',['크다'],['predicate'],'required'),
   ('copula','학생이어'if link=='어'else'학생이고',['학생','이다'],['nominal','copula'],'forbidden'),
   ('verbal-negative','먹지않아'if link=='어'else'먹지않고',['먹다','않다'],['predicate','auxiliary'],'required'),
   ('adjectival-negative','좋지않아'if link=='어'else'좋지않고',['좋다','않다'],['predicate','auxiliary'],'forbidden'),
   ('derived-adjective','학생다워'if link=='어'else'학생답고',['학생'],['nominal'],'forbidden'),
   ('derived-negative','학생답지않아'if link=='어'else'학생답지않고',['학생','않다'],['nominal','auxiliary'],'forbidden')]:
   forms=(['답다']if tag.startswith('derived')else[])+(['지']if'negative'in tag else[])+[link,ending]
   roles=['suffix'if f=='답다'else'ending'for f in forms]
   add(key+'-'+tag,prefix+tail,heads+[right],kinds+['auxiliary'],forms,roles,verdict,source)
 add('question-do-adjective','좋아내느냐도',['좋다','내다'],['predicate','auxiliary'],['어','느냐','도'],['ending','ending','particle'],'forbidden','continuation-left-60625')
 add('independent-pos-adjective','발그스레해내다',['발그스레하다','내다'],['predicate','auxiliary'],['어','다'],['ending','ending'],'forbidden','continuation-left-60625')
 for prefix,head,verdict in [('먹어','먹다','required'),('좋아','좋다','forbidden')]:
  for tail,forms in [('냈다',['어','었','다']),('내겠다',['어','겠','다']),('내시다',['어','시','다'])]:
   add('right-prefinal-'+prefix+tail,prefix+tail,[head,'내다'],['predicate','auxiliary'],forms,['ending','prefinal','ending'],verdict,'continuation-left-60625')
 return result

def match(analysis,j):
 return [l['text']for l in analysis['lemmas']]==j['lemmas']and[l['kind']for l in analysis['lemmas']]==j['lemma_kinds']and[m['form']for m in analysis['morphemes']]==j['morphemes']and[m['kind']for m in analysis['morphemes']]==j['morpheme_kinds']

def verify(r):
 assert r['extractor_sha256']==sha(__file__)and r['lmf_sha256']==sha(LMF)
 assert r['original_preflight_sha256']==sha(ROOT/'docs/continuation-left-source-preflight.json')
 assert r['cases']==cases()
 historical=json.loads((ROOT/'docs/continuation-left-source-preflight.json').read_text())
 assert all(r['before_words'][s]==w for s,w in historical['words'].items())
 ledger=json.loads((ROOT/'tests/fixtures/dictionary-attachments.json').read_text());indexed={c['id']:c for c in ledger['cases']}
 assert all(indexed[c['id']]==c for c in cases())
 assert all(ledger['sources'][k]==v for k,v in r['sources'].items())
 for entry in r['source_entries']:
  original=copy.deepcopy(r['complete_native_entries'][entry['id']])
  for s in original['senses']:s['translations']=[t for t in s['translations']if t['language']=='영어']
  assert original==entry
 for c in cases():assert any(match(a,c['judgments'][0])for a in r['before_words'][c['surface']]['all']['analyses']),c['id']
 print('Continuation-left audit: original preflight, complete sources, raw targets and 56 append-only class judgments verified.')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');p.add_argument('--cli',type=Path);p.add_argument('--dictionary',type=Path);args=p.parse_args()
 if args.verify:verify(json.loads(OUTPUT.read_text()));return
 if not args.cli or not args.dictionary or OUTPUT.exists()or LMF.exists():p.error('Freeze requires CLI/dictionary and refuses overwriting evidence.')
 cli=args.cli.resolve();dbpath=args.dictionary.resolve();previous=json.loads((ROOT/'docs/continuation-left-source-preflight.json').read_text())
 # Keep all source homonyms of every selected head, including lexical and
 # auxiliary entries; the raw LMF adapter selects exact native ID/POS profiles.
 heads={'가다','오다','나가다','나다','내다','버리다','치우다','먹다','좋다','크다','학생','이다','않다','아니하다','못하다','지다','보다','싶다','하다','공부','공부하다','좋아하다','발그스레하다','어둡다','밝다','깊다'}
 entries={}
 with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)as db:
  for ident,head,raw in db.execute('select id,headword,data from entries'):
   if head in heads:entries[ident]=json.loads(raw)
 raw_entries={};raw_hashes={}
 for path in sorted((ROOT/'data/dictionaries/krdict/json').glob('*.json')):
  for raw in array(json.loads(path.read_text())['LexicalResource']['Lexicon']['LexicalEntry']):
   ident='krdict:'+str(raw['val'])
   if ident not in entries:continue
   head=next(f['val']for l in array(raw['Lemma'])for f in array(l['feat'])if f['att']=='writtenForm')
   pos=next((f['val']for f in array(raw.get('feat',[]))if f['att']=='partOfSpeech'),'품사 없음')
   if(head,pos)!=(entries[ident]['headword'],entries[ident]['pos']):continue
   assert ident not in raw_entries
   raw=copy.deepcopy(raw);raw.pop('RelatedForm',None);raw['Sense']=array(raw.get('Sense',[]))
   for s in raw['Sense']:
    if'Equivalent'in s:s['Equivalent']=[e for e in array(s['Equivalent'])if any(f['att']=='language'and f['val']=='영어'for f in array(e.get('feat',[])))]
   raw_entries[ident]=raw;raw_hashes[str(path.relative_to(ROOT))]=sha(path)
 assert set(raw_entries)==set(entries)
 LMF.write_text(json.dumps({'LexicalResource':{'Lexicon':{'LexicalEntry':[raw_entries[i]for i in sorted(entries)]}}},ensure_ascii=False,indent=2)+'\n')
 projected=copy.deepcopy([entries[i]for i in sorted(entries)])
 for e in projected:
  for s in e['senses']:s['translations']=[t for t in s['translations']if t['language']=='영어']
 raw_ledger=json.loads((ROOT/'tests/fixtures/validity.json').read_text())
 native_controls={c['surface']for c in raw_ledger['cases']if c['id'].startswith('continuation-aux-')}
 diagnostics={'좋아해내다','좋아보아내다','좋아지고나니','좋고싶어내다','공부해내다','뮈어내다','내다','내느냐도','어두워가다','깊어가다','밝아오다','먹었어버리다','먹겠어버리다','먹고난다','먹고나셨다'}
 surfaces=sorted({c['surface']for c in cases()}|set(previous['words'])|native_controls|diagnostics)
 before={s:{mode:json.loads(subprocess.check_output([str(cli),'word',s,'--dictionary',str(dbpath),*flags]))for mode,flags in [('all',[]),('headword',['--dict-only']),('compatible',['--dict-compatible'])]}for s in surfaces}
 assert all(before[s]==w for s,w in previous['words'].items())
 for c in cases():assert any(match(a,c['judgments'][0])for a in before[c['surface']]['all']['analyses']),c['id']
 sources={'continuation-left-'+ident.split(':')[1]:entries[ident]['url']for _,_,_,_,ident in TARGETS}
 r=dict(schema_version=1,checklist='COV-019ad',before_revision=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),cli=str(cli),cli_sha256=sha(cli),dictionary_sha256=sha(dbpath),original_preflight_sha256=sha(ROOT/'docs/continuation-left-source-preflight.json'),extractor_sha256=sha(__file__),lmf_sha256=sha(LMF),raw_source_sha256=raw_hashes,complete_native_entries=entries,source_entries=projected,before_words=before,sources=sources,cases=cases(),scope='Finite immediate-left verb-class checks for five exact native auxiliary identities and six connectors. Raw generation and native source fields are unchanged. 가다/오다 adjective examples prevent a family-wide exclusion. Negatives inherit lexical class; other auxiliaries and copulas start their own owners. Context, lexical subsets, source conflicts, tense and right-ending restrictions and independent Korean review remain separate.')
 OUTPUT.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(native_entries=len(entries),surfaces=len(surfaces),class_cases=len(cases()))),flush=True)
if __name__=='__main__':main()
