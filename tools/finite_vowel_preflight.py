import argparse,copy,hashlib,json,re,sqlite3,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Freeze complete source entries and before outputs for finite vowel paradigms; refuses to overwrite fixtures.')
parser.add_argument('--cli',type=Path,required=True)
parser.add_argument('--dictionary',type=Path,default=R/'data/dictionaries/krdict/krdict.db')
args=parser.parse_args();CLI=args.cli.resolve();DB=args.dictionary.resolve()
outputs=['krdict-finite-vowel.json','finite-vowel-sources.json','kaist-finite-vowel.conllu']
existing=[name for name in outputs if (R/'tests/fixtures'/name).exists()]
if existing:parser.error('Refusing to overwrite frozen fixtures: '+', '.join(existing))
prior=json.load(open(R/'docs/written-paradigm-remaining-preflight.json'));pairs=prior['review_next']['native_pairs']
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def arr(v):return v if isinstance(v,list)else[v]
def dump(p,v):
 with Path(p).open('x')as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
entries={};primary=[]
with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)as db:
 for form,head in pairs:
  e=next(e for e in prior['complete_native_entries']if e['headword']==head and e['pos']in ['동사','형용사']);entries[e['id']]=e;primary.append(e)
cases=[];controls=[]
def add(name,s,heads,forms,entry,verdict='required',kinds=None,reason=None):
 c=dict(id='finite-vowel-'+name,surface=s,lemmas=[dict(text=h,kind=k)for h,k in zip(heads,kinds or ['predicate']*len(heads))],morphemes=[dict(form=f,kind='prefinal'if f in ['었','겠']else'ending')for f in forms],source_id=entry['id'],source=entry['url'],verdict=verdict,reason=reason or 'Source-listed whole-stem vowel boundary under an existing productive suffix template. Sense/register/contextual grammaticality remain unjudged; no arbitrary prefix or suffix-wide contraction is licensed.');cases.append(c);return c
for (form,head),entry in zip(pairs,primary):
 name=entry['id'].split(':')[1];past=form[:-1]+('랬'if form[-1]=='래'else'쨌')
 patterns=[('bare',form,['어']),('polite',form+'요',['어요']),('concessive',form+'도',['어도']),('reason',form+'서',['어서']),('condition',form+'야',['어야']),('past',past+'다',['었','다']),('past-polite',past+'어요',['었','어요']),('past-if',past+'으면',['었','으면']),('past-modal',past+'겠지',['었','겠','지']),('past-quote',past+'다고',['었','다고'])]
 if entry['pos']=='동사':patterns.append(('command',form+'라',['어라']))
 for name2,s,ms in patterns:add(name+'-'+name2,s,[head],ms,entry)
 if entry['pos']=='동사':
  for tail,aux in [('버렸다','버리다'),('봤다','보다')]:add(name+'-aux-'+tail,form+tail,[head,aux],['어','었','다'],entry,kinds=['predicate','auxiliary'])
 add(name+'-prefix','마'+form,['마'+head],['어'],entry,verdict='forbidden',reason='The exact source-listed stem does not license a fabricated lexical prefix; this forbids only the stated hypothesis.')
 controls.extend('마'+s for s in [form,form+'도',past+'다'])
 controls.extend([f['written'].strip()for f in entry['forms']if f['kind']=='활용'and f['written'].strip()])
 # Authored composition controls preserve structural alternatives without
 # promoting an unreviewed adjective/auxiliary or mood combination to gold.
 if entry['pos']=='형용사':controls.extend([form+'라',form+'버렸다',form+'봤다'])
corpus_rows=[];sentences={}
p=R/'data/corpora/kaist/ko_kaist-ud-train.conllu'
for block in p.read_text().split('\n\n'):
 for line in block.splitlines():
  row=line.split('\t')
  if len(row)!=10 or row[1]!='아무래도'or row[2]!='아무렇+어도':continue
  sid=next(l.split(' = ',1)[1]for l in block.splitlines()if l.startswith('# sent_id = '));e=next(e for e in primary if e['headword']=='아무렇다');c=add('kaist-'+sid+'-'+row[0],row[1],['아무렇다'],['어도'],e,reason='Unchanged original annotated 아무렇 + 어도 group, complete original sentence and token row preserved.');c['source']='https://github.com/UniversalDependencies/UD_Korean-Kaist/tree/r2.15';sentences[sid]=block;corpus_rows.append(dict(case_id=c['id'],path=str(p.relative_to(R)),source_sha256=sha(p),sentence_id=sid,token_id=row[0],surface=row[1],original_row=line,original_sentence=block))
assert len(corpus_rows)==4
# Retain existing adverb, noun and other whole-word alternatives as controls.
controls+=['그래','그랬다','이래','저래','그리했다','어쩐다','어쩌니','어쩌면','어쨌든','아무래도','고래들','요래다','조래다','먹고요래']
surfaces=sorted({c['surface']for c in cases}|set(controls));words={s:json.loads(subprocess.check_output([str(CLI),'word',s,'--dictionary',str(DB)]))for s in surfaces}
with sqlite3.connect(DB.resolve().as_uri()+'?mode=ro',uri=True)as db:
 for word in words.values():
  for a in word['analyses']:
   for lemma in a['lemmas']:
    for raw,in db.execute('select data from entries where headword=?',(lemma['text'],)):
     e=json.loads(raw);entries[e['id']]=e
for c in cases:c['before_candidate_indices']=[i for i,a in enumerate(words[c['surface']]['analyses'])if a['lemmas']==c['lemmas']and a['morphemes']==c['morphemes']]
raw={};hashes={}
for file in sorted((R/'data/dictionaries/krdict/json').glob('*.json')):
 for e in arr(json.load(file.open())['LexicalResource']['Lexicon']['LexicalEntry']):
  ident='krdict:'+str(e['val'])
  if ident not in entries:continue
  head=next(x['val']for lm in arr(e['Lemma'])for x in arr(lm['feat'])if x['att']=='writtenForm');pos=next((x['val']for x in arr(e.get('feat',[]))if x['att']=='partOfSpeech'),'품사 없음')
  if(head,pos)!=(entries[ident]['headword'],entries[ident]['pos']):continue
  assert ident not in raw
  v=copy.deepcopy(e);v.pop('RelatedForm',None);v['Sense']=arr(v.get('Sense',[]))
  for sense in v['Sense']:
   if'Equivalent'in sense:sense['Equivalent']=[t for t in arr(sense['Equivalent'])if any(x['att']=='language'and x['val']=='영어'for x in arr(t.get('feat',[])))]
  raw[ident]=v;hashes[str(file.relative_to(R))]=sha(file)
assert set(raw)==set(entries)
full=copy.deepcopy(list(entries.values()))
for e in full:
 for sense in e['senses']:sense['translations']=[t for t in sense['translations']if t['language']=='영어']
report=dict(schema_version=1,checklist=['COV-021n'],before_revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),before_cli=str(CLI),before_cli_sha256=sha(CLI),dictionary_sha256=sha(DB),original_preflight='docs/written-paradigm-remaining-preflight.json',original_preflight_sha256=sha(R/'docs/written-paradigm-remaining-preflight.json'),primary_entry_ids=[e['id']for e in primary],native_pairs=pairs,source_entries=full,source_hashes=hashes,cases=cases,corpus_rows=corpus_rows,unjudged_controls=sorted(set(controls)),before_words=words,attribution='National Institute of Korean Language Korean Basic Dictionary; UD Korean-Kaist r2.15',license='KRDict CC BY-SA 2.0 KR; UD CC BY-SA 4.0',policy='Exact finite whole stems only. Keep every prior candidate, metadata, assessment and relative order. Verbal 고러/요러/조러 do not inherit homonymous adjective ㅎ spelling requirements. All authored extended mood/auxiliary controls and contextual senses remain unjudged.')
dump(R/'tests/fixtures/krdict-finite-vowel.json',dict(LexicalResource=dict(Lexicon=dict(LexicalEntry=[raw[i]for i in sorted(raw)]))));dump(R/'tests/fixtures/finite-vowel-sources.json',report)
with(R/'tests/fixtures/kaist-finite-vowel.conllu').open('x')as out:out.write('\n\n'.join(sentences.values())+'\n\n')
print(json.dumps(dict(sources=len(full),cases=len(cases),required=sum(c['verdict']=='required'for c in cases),forbidden=sum(c['verdict']=='forbidden'for c in cases),surfaces=len(words),corpus_rows=len(corpus_rows)),ensure_ascii=False),flush=True)
