import argparse,copy,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
parser=argparse.ArgumentParser(description='Freeze source examples and before outputs for the direct-command review. Refuses to overwrite any fixture.')
parser.add_argument('--cli',type=Path,required=True,help='Immutable CLI from the revision recorded as the before state')
parser.add_argument('--dictionary',type=Path,default=Path('data/dictionaries/krdict/krdict.db'))
args=parser.parse_args()
R=Path(__file__).resolve().parents[1];CLI=args.cli.resolve();DB=args.dictionary.resolve()
outputs=['kaist-direct-command-review.conllu','gsd-direct-command-review.conllu','krdict-direct-command-review.json','direct-command-review-sources.json']
existing=[name for name in outputs if (R/'tests/fixtures'/name).exists()]
if existing:parser.error('Refusing to overwrite frozen fixtures: '+', '.join(existing))
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def dump(p,v):
 with Path(p).open('x',encoding='utf-8')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def arr(v):return v if isinstance(v,list)else[v]
previous=json.load(open(R/'tests/fixtures/gera-nera-sources.json'));native=json.load(open(R/'docs/gera-nera-source-preflight.json'));entries={e['id']:e for e in native['complete_native_entries']if e['headword']in ['-거라','-너라','-었-']}
with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)as db:
 for h in ['서다','무르다','데리다','살아가다','나오다','나다','거','것']:
  for raw,in db.execute('select data from entries where headword=?',(h,)):
   e=json.loads(raw);entries[e['id']]=e
new_ids=set(entries)-{e['id']for e in previous['source_entries']};cases=[];attestations=[];entry_cases=[]
def case(ident,surface,heads,forms,source,reason,verdict='required',kinds=None,mk=None):
 c=dict(id='direct-command-review-'+ident,surface=surface,lemmas=[dict(text=h,kind=k)for h,k in zip(heads,kinds or ['predicate']*len(heads))],morphemes=[dict(form=f,kind=k)for f,k in zip(forms,mk or ['ending']*len(forms))],source=source,reason=reason,verdict=verdict);cases.append(c);return c
for ident in ['krdict:66953','krdict:68835']:
 e=entries[ident]
 for sense in e['senses']:
  for i,group in enumerate(sense['examples']):
   forms=[m.group()for line in group for m in re.finditer(r'[가-힣]+(?:거라|너라)(?=[^가-힣]|$)',line)]
   assert len(forms)==1,(ident,i,group)
   s=forms[0];ending=s[-2:];head=s[:-2]+'다';c=case(f'native-{ident.split(":")[1]}-{sense["id"]}-{i+1}',s,[head],[ending],e['url'],'Exact token from the complete native ending example; direct whole-head lookup, with context and register not selected.')
   attestations.append(dict(case=c['id'],source_id=ident,sense=sense['id'],example_group_index=i,examples=group,surface=s,headword=head))
train=native['train_rows'];groups={}
for t in train:
 key=Path(t['path']).parts[2];corpus='kaist'if'kaist'in t['path']else'gsd';groups.setdefault(corpus,{})[t['sentence_id']]=t['original_sentence']
 if t['surface']=='거라':heads=['거','이다'];forms=['라'];kinds=['nominal','copula']
 elif t['surface']=='오너라':heads=['오다'];forms=['너라'];kinds=['predicate']
 else:assert t['surface']=='데려오너라';heads=['데리다','오다'];forms=['어','너라'];kinds=['predicate','auxiliary']
 c=case(f'{corpus}-{t["sentence_id"]}-{t["token_id"]}',t['surface'],heads,forms,'https://github.com/UniversalDependencies/UD_Korean-'+('Kaist'if corpus=='kaist'else'GSD')+'/tree/r2.15','Unchanged source row and complete sentence retained. Distinguish nominal 거 + 이다 + 라 from commands; preserve the original 데리다 + auxiliary 오다 segmentation.',kinds=kinds)
 if len(heads)>1 and t['surface']!='거라':case(f'{corpus}-order-{t["sentence_id"]}-{t["token_id"]}',t['surface'],heads,list(reversed(forms)),c['source'],'Specific reversed connector/final hypothesis conflicts with the original annotated component order.',verdict='forbidden',kinds=kinds)
 t['case_id']=c['id'];t['disposition']='required original lemma/morpheme grouping, no gold edits'
url='https://www.korean.go.kr/front/onlineQna/onlineQnaView.do?mn_id=216&pageIndex=1&qna_seq=327283'
for name,s,head in [('stand','섰거라','서다'),('withdraw','물렀거라','무르다')]:
 case('past-'+name,s,[head],['었','거라'],url,'NIKL explicitly analyzes this limited command as lexical stem + past prefinal 었 + final 거라; it does not license arbitrary tense/mood combinations.',mk=['prefinal','ending'])
 case('past-kind-'+name,s,[head],['었','거라'],url,'The named 었 component is a prefinal, not a second terminal ending. This forbids only this exact kind assignment.',verdict='forbidden',mk=['ending','ending'])
# Entry judgments are separate from raw candidate validity.
probes=[('섰거라','서다',['었','거라']),('물렀거라','무르다',['었','거라']),('서거라','서다',['거라']),('무르거라','무르다',['거라']),('서셨거라','서다',['시','었','거라']),('무르셨거라','무르다',['시','었','거라']),('섰겠거라','서다',['었','겠','거라']),('물렀겠거라','무르다',['었','겠','거라']),('섰었거라','서다',['었','었','거라']),('물렀었거라','무르다',['었','었','거라']),('섰더거라','서다',['었','더','거라']),('물렀더거라','무르다',['었','더','거라']),('무렀거라','무르다',['었','거라']),('섰다','서다',['었','다']),('물렀다','무르다',['었','다'])]
for s,head,ms in probes:
 for e in entries.values():
  if e['headword']!=head:continue
  exact=ms==['었','거라']and s in ['섰거라','물렀거라']and e['id']in ['krdict:68756','krdict:55296']
  expected='compatible'if exact else 'incompatible'if s=='무렀거라'else'compatible'if ms in [['거라'],['었','다']]and(ms[-1]=='다'or e['pos']=='동사')else'unknown'
  entry_cases.append(dict(id=f'direct-command-entry-{len(entry_cases)+1:03}',surface=s,lemmas=[dict(text=head,kind='predicate')],morphemes=[dict(form=m,kind='ending'if i==len(ms)-1 else'prefinal')for i,m in enumerate(ms)],lemma_index=0,entry_id=e['id'],expected_status=expected,source=url,reason='Finite single-past license is per reviewed entry and immediate owner; other homonyms/prefinals stay unknown. Existing spelling conflicts and normal past declaratives remain independent.'))
for s,head,aux,connector in [('서버렸거라','서다','버리다','어'),('물러버렸거라','무르다','버리다','어'),('서지말았거라','서다','말다','지')]:
 entry_cases.append(dict(id=f'direct-command-entry-{len(entry_cases)+1:03}',surface=s,lemmas=[dict(text=head,kind='predicate'),dict(text=aux,kind='auxiliary')],morphemes=[dict(form=connector,kind='ending'),dict(form='었',kind='prefinal'),dict(form='거라',kind='ending')],lemma_index=1,entry_id=None,expected_status='unknown',source=url,reason='Past command belongs to the auxiliary, not the earlier reviewed lexical entry. Keep this authored register probe unjudged rather than borrowing a lexical past license.'))
surfaces={c['surface']for c in cases}|{c['surface']for c in entry_cases};words={s:json.loads(subprocess.check_output([str(CLI),'word',s,'--dictionary',str(DB)]))for s in sorted(surfaces)}
for c in cases+entry_cases:
 c['before_candidate_indices']=[i for i,a in enumerate(words[c['surface']]['analyses'])if a['lemmas']==c['lemmas']and a['morphemes']==c['morphemes']]
 if c.get('verdict')=='required':assert c['before_candidate_indices'],c
 if'expected_status'in c:
  assert c['before_candidate_indices'],c
  c['before_assessments']=[words[c['surface']]['dictionary']['readings'][i]['lemmas'][c['lemma_index']]for i in c['before_candidate_indices']]
  if c['entry_id']:
   c['before_entry_statuses']=[next(e['status']for e in x['entries']if e['id']==c['entry_id'])for x in c['before_assessments']]
raw={};hashes={}
for file in sorted((R/'data/dictionaries/krdict/json').glob('*.json')):
 for e in arr(json.load(file.open())['LexicalResource']['Lexicon']['LexicalEntry']):
  ident='krdict:'+str(e['val'])
  if ident not in new_ids:continue
  head=next(x['val']for lm in arr(e['Lemma'])for x in arr(lm['feat'])if x['att']=='writtenForm');pos=next((x['val']for x in arr(e.get('feat',[]))if x['att']=='partOfSpeech'),'품사 없음')
  if(head,pos)!=(entries[ident]['headword'],entries[ident]['pos']):continue
  assert ident not in raw
  v=copy.deepcopy(e);v.pop('RelatedForm',None);v['Sense']=arr(v.get('Sense',[]))
  for sense in v['Sense']:
   if'Equivalent'in sense:sense['Equivalent']=[t for t in arr(sense['Equivalent'])if any(x['att']=='language'and x['val']=='영어'for x in arr(t.get('feat',[])))]
  raw[ident]=v;hashes[str(file.relative_to(R))]=sha(file)
assert set(raw)==new_ids
for corpus,sentences in groups.items():
 p=R/f'tests/fixtures/{corpus}-direct-command-review.conllu';assert not p.exists();p.write_text('\n\n'.join(sentences.values())+'\n\n')
dump(R/'tests/fixtures/krdict-direct-command-review.json',dict(LexicalResource=dict(Lexicon=dict(LexicalEntry=[raw[i]for i in sorted(raw)]))))
full=copy.deepcopy([entries[i]for i in sorted(entries)])
for e in full:
 for sense in e['senses']:sense['translations']=[t for t in sense['translations']if t['language']=='영어']
report=dict(schema_version=1,checklist=['COV-021l'],before_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),before_cli=str(CLI),before_cli_sha256=sha(CLI),dictionary_sha256=sha(DB),source_hashes=hashes,new_source_ids=sorted(new_ids),source_entries=full,cases=cases,attestations=attestations,corpus_rows=train,entry_cases=entry_cases,before_words=words,primary_sources=[dict(url=url,scope='Full answer read: limited single-past commands; withdrawal 무르다 specifically identified. Exact native entry/sense mapping preserved, other verbal/adjectival homonyms and extended prefinals remain unjudged.')],attribution='National Institute of Korean Language Korean Basic Dictionary; Universal Dependencies Korean-Kaist and Korean-GSD r2.15',license='KRDict: CC BY-SA 2.0 KR; UD: CC BY-SA 4.0. Official consultation summarized by URL; no literary passage copied.',policy='Only existing POS-compatible 서다 68756 and retreat 무르다 55296, with exactly own 었 + 거라, escape the generic unreviewed-prefinal downgrade. A compatible entry may contain a reviewed sense without choosing it from context. No incompatible spelling/role is promoted; additional prefinals, other homonyms, auxiliaries and generic providers remain unknown.')
dump(R/'tests/fixtures/direct-command-review-sources.json',report)
print(json.dumps(dict(new_source_ids=len(new_ids),complete_sources=len(full),raw_cases=len(cases),entry_judgments=len(entry_cases),native_groups=len(attestations),corpus_rows=len(train),surfaces=len(words)),ensure_ascii=False),flush=True)
