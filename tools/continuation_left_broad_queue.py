"""Freeze complete native evidence and raw indices for broad class changes."""
import argparse
import gzip
import json
import sqlite3
import subprocess
import urllib.request
from pathlib import Path
from continuation_left_compare import Audit, sha

ROOT=Path(__file__).resolve().parents[1]
OBS=ROOT/'docs/continuation-left-observations.json'
RUNTIME=ROOT/'docs/continuation-left-broad-runtime.json.gz'
QUEUE=ROOT/'docs/continuation-left-broad-review-queue.json'
TARGETS={'내다':'krdict:60625','나다':'krdict:62134','나가다':'krdict:26813','버리다':'krdict:62601','치우다':'krdict:74290'}
def build_queue(data):
    observed=json.loads(OBS.read_text())
    assert data['observations_sha256']==sha(OBS)
    audit=Audit(None,None);items=[]
    for surface,word in data['words'].items():
        audit.word(word['before'],word['after'],'all',['broad-queue',surface])
    for change in observed['changed_entries']:
        word=data['words'][change['surface']];a=change['analysis'];index=word['after']['analyses'].index(a)
        assert word['before']['analyses'][index]==a
        left=change['lemma_index']
        def selected(w):
            slot=next(s for s in w['dictionary']['readings'][index]['lemmas']if s['lemma_index']==left)
            return next(e for e in slot['entries']if e['id']==change['entry_id'])
        assert selected(word['before'])==change['before']and selected(word['after'])==change['after']
        order=word['breakdowns'][index];connector=change['after']['conflicts'][-1]['morpheme_index']
        position=order.index(dict(morpheme=connector))
        owner_position=order.index(dict(lemma=left))
        assert owner_position<position
        # The source dependency can cross only represented 지-negatives.
        previous=owner_position
        for p in range(owner_position+1,position):
            if'lemma'not in order[p]:continue
            lemma=a['lemmas'][order[p]['lemma']]
            assert lemma['kind']=='auxiliary'and lemma['text']in ['않다','아니하다','못하다']
            endings=[a['morphemes'][c['morpheme']]for c in order[previous+1:p]if'morpheme'in c and a['morphemes'][c['morpheme']]['kind']=='ending']
            assert endings and endings[0]['form']=='지'
            previous=p
        right=next(c['lemma']for c in order[position+1:]if'lemma'in c)
        assert a['lemmas'][right]['kind']=='auxiliary'
        ident=TARGETS[a['lemmas'][right]['text']];source=data['entries'][ident]
        assert source['pos']=='보조 동사'and source['homonym']=='2'
        assert a['morphemes'][connector]['form']in(['어','고']if ident=='krdict:62134'else['어'])
        owner=next(m for m in word['after']['dictionary']['lemmas']if m['lemma']==a['lemmas'][left])
        native=next(e for e in owner['entries']if e['id']==change['entry_id'])
        assert all(native[k]==data['entries'][change['entry_id']][k]for k in ['id','headword','homonym','pos'])
        own_end=next((p for p in range(owner_position+1,len(order))if'lemma'in order[p]),len(order))
        own_morphemes=[a['morphemes'][c['morpheme']]for c in order[owner_position+1:own_end]if'morpheme'in c]
        pos=native.get('independent_pos',{}).get('reviewed_pos',native['pos'])
        assert (pos in ['형용사','보조 형용사']or a['lemmas'][left]['kind']=='copula'
            or dict(form='답다',kind='suffix')in own_morphemes), (change['surface'],native)
        items.append(dict(change,raw_index=index,breakdown=order,left_source=change['entry_id'],right_source=ident,
            right_source_url=source['url'],compatible_retained=word['after']['dictionary']['readings'][index]['status']!='incompatible'))
    # The audit checks every raw reading, including unnamed alternatives.
    assert {c['id']for c in audit.changes.values()}=={c['id']for c in items}
    for removed in observed['removed_paths']:
        word=data['words'][removed['surface']]['after'];index=word['analyses'].index(removed['analysis'])
        assert index==removed['raw_index']and word['dictionary']['readings'][index]==removed['assessment']
        assert removed['assessment']['status']=='incompatible'
    return dict(schema_version=1,checklist='COV-019ad',generator_sha256=sha(Path(__file__)),runtime_sha256=sha(RUNTIME),
        observations_sha256=sha(OBS),dictionary_sha256=data['dictionary_sha256'],items=items,
        counts=dict(surfaces=len(data['words']),native_entries=len(data['entries']),changed_entries=len(items),filtered_paths=len(observed['removed_paths'])),
        limitation='Complete broad-stream and diagnostic changes, with actual raw indices and full native entries. This records finite dictionary class conflicts; every contextual reading remains unjudged. Repeated novel occurrences retain their original stream positions.')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true')
    p.add_argument('--cli',type=Path);p.add_argument('--before-cli',type=Path);p.add_argument('--url');args=p.parse_args()
    if args.verify:
        with gzip.open(RUNTIME,'rt')as f:data=json.load(f)
        current=build_queue(data);assert current==json.loads(QUEUE.read_text())
        print(json.dumps(current['counts']),flush=True);return
    if not args.cli or not args.before_cli or not args.url or RUNTIME.exists()or QUEUE.exists():p.error('Freeze requires CLI/baseline/local URL and refuses overwriting evidence.')
    observed=json.loads(OBS.read_text());db=ROOT/'data/dictionaries/krdict/krdict.db'
    assert sha(db)==observed['dictionary_sha256']
    assert sha(args.cli)==observed['cli_sha256']and sha(args.before_cli)==observed['before_cli_sha256']
    def post(endpoint,body):
        request=urllib.request.Request(args.url+'/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=30)as response:return json.load(response)
    words={}
    for surface in sorted({e['surface']for e in observed['changed_entries']}):
        b,a=[json.loads(subprocess.check_output([str(cli.resolve()),'word',surface,'--dictionary',str(db)]))for cli in [args.before_cli,args.cli]]
        api=post('analyze',dict(text=surface,suggest_spacing=False));assert len(api['records'])==1
        record=api['records'][0];assert record['analysis']=={k:v for k,v in a.items()if k!='dictionary'}
        assert record['dictionary']==a['dictionary']
        words[surface]=dict(before=b,after=a,breakdowns=api['breakdowns'][0])
    ids={e['entry_id']for e in observed['changed_entries']}|set(TARGETS.values());entries={}
    with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)as connection:
        for ident in sorted(ids):
            entry=json.loads(connection.execute('select data from entries where id=?',(ident,)).fetchone()[0])
            assert post('entry',dict(id=ident))['entry']==entry;entries[ident]=entry
    data=dict(schema_version=1,observations_sha256=sha(OBS),cli_sha256=sha(args.cli),before_cli_sha256=sha(args.before_cli),
        dictionary_sha256=sha(db),words=words,entries=entries)
    with RUNTIME.open('xb')as sink,gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0)as archive:archive.write(json.dumps(data,ensure_ascii=False,separators=(',',':')).encode())
    queue=build_queue(data);QUEUE.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(queue['counts']),flush=True)
if __name__=='__main__':main()
