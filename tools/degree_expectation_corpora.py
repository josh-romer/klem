"""Replay production corpus preservation and original gold outcomes offline."""
import copy, hashlib, json, sys
from pathlib import Path
sys.path.insert(0,'/home/josh/projects/klem/tools')
from lexical_nada_audit import ROOT, read, sha
from doeda_native_corpora import contexts_text, gold_changes
from friendly_command_corpora import outcome
from degree_expectation_parent import inverse

p=ROOT/'docs/degree-expectation-main-corpora.json.gz'
r=read(p);prior=read(ROOT/'docs/friendly-command-packaged-corpora.json.gz')
assert r['production_worktree'] is True
assert r['previous_report_sha256']==sha(ROOT/'docs/friendly-command-packaged-corpora.json.gz')
assert r['source_sha256']==sha(ROOT/'docs/degree-rimankeum-source-preparation.json.gz')
assert r['before_cli_sha256']==prior['cli_sha256']
assert hashlib.sha256(r['producer']['text'].encode()).hexdigest()==r['producer']['sha256']
before,after=prior['after_words'],r['after_words']
assert before.keys()==after.keys() and len(after)==32096
for field,words in [('before_word_stream_sha256',before),('after_word_stream_sha256',after)]:
 assert r[field]==hashlib.sha256(json.dumps(words,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
texts=read(ROOT/'docs/doeda-originless-corpora.json.gz')
locations={};total=0;changedgold=0
for old,new in zip(prior['corpora'],r['corpora'],strict=True):
 for field in ['corpus','partition','source','source_sha256','converted_rows','report_lines']:assert old[field]==new[field]
 original=texts['original_corpus_texts'][new['source']]
 assert hashlib.sha256(original.encode()).hexdigest()==new['source_sha256']
 context=contexts_text(original)
 b=[json.loads(l) for l in old['after_jsonl'].splitlines()];a=[json.loads(l) for l in new['after_jsonl'].splitlines()]
 assert new['after_report_sha256']==hashlib.sha256(new['after_jsonl'].encode()).hexdigest()
 assert new['changed_gold_outcomes']==gold_changes(b[1:],a[1:],context)
 changedgold+=len(new['changed_gold_outcomes'])
 assert len(a)==new['converted_rows']+1==new['report_lines']
 counts=[len(after[row['surface']]['analyses']) for row in a[1:]]
 assert counts==new['after_candidate_counts']
 assert a[0]['mean_candidates']==sum(counts)/len(counts)
 assert a[0]['p95_candidates']==sorted(counts)[len(counts)*95//100]
 assert a[0]['max_candidates']==max(counts)
 assert a[0]['grouped_matches']==sum(row['matched'] for row in a[1:])
 assert a[0]['recovered_gold_lemmas']==sum(row['recovered'] for row in a[1:])
 for oldrow,row in zip(b[1:],a[1:],strict=True):
  assert {k:oldrow[k] for k in ['id','surface','expected']}=={k:row[k] for k in ['id','surface','expected']}
  assert (row['matched'],row['recovered'],row['recovered_sets'])==outcome(row['expected'],after[row['surface']]['analyses'])
  locations.setdefault(row['surface'],[]).append(dict(source=new['source'],source_sha256=new['source_sha256'],id=row['id'],**context[row['id']]))
 total+=len(a)-1
changed={};observations=[]
for word in sorted(before):
 b,a=before[word],after[word]
 if b==a:continue
 assert {k:v for k,v in b.items() if k!='analyses'}=={k:v for k,v in a.items() if k!='analyses'}
 assert [x for x in a['analyses'] if x in b['analyses']]==b['analyses']
 changed[word]=dict(before=b,after=a,occurrences=locations[word])
 for path in a['analyses']:
  if path in b['analyses']:continue
  companion,parent,source_ids=inverse(word,path)
  assert parent in r['companion_analyses'][companion]['analyses']
  digest=hashlib.sha256(json.dumps([word,path],ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:24]
  observations.append(dict(id='degree-expectation-corpus-'+digest,surface=word,analysis=path,parent=dict(surface=companion,analysis=parent),source_entries=source_ids,source_sense_ids=['1'],occurrences=locations[word],contextual_verdict='unjudged',independent_review='pending'))
assert total==66570==r['converted_rows']
assert changed==r['changed_words'] and observations==r['candidate_changes']
print('Verified',total,'original gold rows;',len(after),'raw word orders;',len(changed),'changed words;',len(observations),'exact companion-parent additions;',changedgold,'changed gold outcomes.')
