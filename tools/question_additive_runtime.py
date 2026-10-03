"""Verify every frozen diagnostic and individual new path through CLI/API."""
import argparse
import gzip
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--cli',type=Path,required=True)
parser.add_argument('--server',type=Path,required=True)
parser.add_argument('--assets',type=Path,required=True)
parser.add_argument('--url')
parser.add_argument('--expected',type=Path)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
assert not args.output.exists()
root=args.root.resolve();source=json.loads((root/'tests/fixtures/question-additive-sources.json').read_text());db=root/'data/dictionaries/krdict/krdict.db'
def sha(path):
    with Path(path).open('rb') as file:return hashlib.file_digest(file,'sha256').hexdigest()
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))
assert sha(db)==source['dictionary_sha256']
owned=None
try:
    if args.url:base=args.url
    else:
        owned=subprocess.Popen([str(args.server),'--port','0','--assets',str(args.assets),'--dictionary',str(db)],stderr=subprocess.PIPE,text=True)
        line=owned.stderr.readline().strip();assert 'http://127.0.0.1:' in line,line
        base='http://'+line.split('http://',1)[1].split()[0]
    def post(endpoint,body):
        req=urllib.request.Request(base+'/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30)as response:return json.load(response)
    def cli_word(surface,flags):return json.loads(subprocess.check_output([str(args.cli),'word',surface,'--dictionary',str(db),*flags]))
    words={};new_paths=[]
    for surface,modes in source['before_words'].items():
        actual={mode:cli_word(surface,flags)for mode,flags in [('all',[]),('headword',['--dict-only']),('compatible',['--dict-compatible'])]}
        for mode,current in actual.items():
            frozen=modes[mode]
            assert current['normalized']==frozen['normalized']
            assert [a for a in current['analyses']if a in frozen['analyses']]==frozen['analyses'],(surface,mode,'prior order/paths')
            before,after=frozen['dictionary'],current['dictionary']
            assert (before['source'],before['fingerprint'])==(after['source'],after['fingerprint'])
            assert all(s in after['lemmas']for s in before['lemmas'])
            for i,a in enumerate(frozen['analyses']):assert before['readings'][i]==after['readings'][current['analyses'].index(a)],(surface,mode,'prior assessment')
        api=post('analyze',dict(text=surface,suggest_spacing=False))
        records=[json.loads(line)for line in subprocess.check_output([str(args.cli),'text','--dictionary',str(db)],input=surface.encode()).splitlines()]
        assert api['records']==records
        assert len(api['breakdowns'][0])==len(actual['all']['analyses'])
        for i,a in enumerate(actual['all']['analyses']):
            if a in modes['all']['analyses']:continue
            assert 'particle.quoted_question'in a['rules']
            assert any(m==dict(form='도',kind='particle')for m in a['morphemes'])
            assert len(api['breakdowns'][0][i])==len(a['lemmas'])+len(a['morphemes'])
            key=canonical([surface,a])
            judged=[]
            for c in source['cases']:
                j=c['judgments'][0]
                if c['surface']==surface and [l['text']for l in a['lemmas']]==j['lemmas'] and [l['kind']for l in a['lemmas']]==j['lemma_kinds'] and [m['form']for m in a['morphemes']]==j['morphemes'] and [m['kind']for m in a['morphemes']]==j['morpheme_kinds']:
                    assert j['verdict']=='required';judged.append(c['id'])
            new_paths.append(dict(id='question-additive-diagnostic-'+hashlib.sha256(key.encode()).hexdigest()[:24],surface=surface,raw_index=i,analysis=a,assessment=actual['all']['dictionary']['readings'][i],breakdown=api['breakdowns'][0][i],headword_retained=a in actual['headword']['analyses'],compatible_retained=a in actual['compatible']['analyses'],judgments=judged,contextual_verdict='unjudged',structural_verdict='required'if judged else'unjudged'))
        api.pop('elapsed_ms');actual['api']=api;words[surface]=actual
    checks=[]
    for c in source['cases']:
        j=c['judgments'][0];present=[]
        for i,a in enumerate(words[c['surface']]['all']['analyses']):
            if [l['text']for l in a['lemmas']]==j['lemmas'] and [l['kind']for l in a['lemmas']]==j['lemma_kinds'] and [m['form']for m in a['morphemes']]==j['morphemes'] and [m['kind']for m in a['morphemes']]==j['morpheme_kinds']:present.append(i)
        assert bool(present)==(j['verdict']=='required'),c['id']
        checks.append(dict(case=c['id'],verdict=j['verdict'],raw_indices=present))
    entries={i:post('entry',dict(id=i))['entry']for i in source['complete_native_entries']}
    assert entries==source['complete_native_entries']
    contexts=[]
    preflight=json.loads((root/'docs/question-clause-additive-preflight.json').read_text())
    original=preflight['complete_attested_sentence']
    joined=original.replace(source['layout_diagnostic']['source_fragment'],source['layout_diagnostic']['joined_fragment']).replace('\n',' ')
    for label,text in [('original_pdf_layout',original),('author_joined_diagnostic',joined)]:
        for normalized in [text,__import__('unicodedata').normalize('NFD',text)]:
            api=post('analyze',dict(text=normalized,suggest_spacing=False))
            records=[json.loads(line)for line in subprocess.check_output([str(args.cli),'text','--dictionary',str(db)],input=normalized.encode()).splitlines()]
            assert api['records']==records
            assert ''.join(r['surface']for r in records)==normalized
            target_words=[r for r in records if (r.get('analysis') or {}).get('normalized')=='내느냐도']
            assert bool(target_words)==(label=='author_joined_diagnostic'),label
            if target_words:
                assert any([l['text']for l in a['lemmas']]==['내다'] and [m['form']for m in a['morphemes']]==['느냐','도'] for a in target_words[0]['analysis']['analyses'])
            api.pop('elapsed_ms');contexts.append(dict(observation=label,text=normalized,api=api))
    with urllib.request.urlopen(base,timeout=30)as response:html=response.read()
    report=dict(schema_version=1,checklist='COV-018ad',source_sha256=sha(root/'tests/fixtures/question-additive-sources.json'),cli=str(args.cli),cli_sha256=sha(args.cli),server=str(args.server),server_sha256=sha(args.server),assets=str(args.assets),dictionary_sha256=sha(db),words=words,new_paths=new_paths,checks=checks,entries=entries,contexts=contexts,index_sha256=hashlib.sha256(html).hexdigest(),counts=dict(diagnostic_surfaces=len(words),cli_word_responses=len(words)*3,word_api_responses=len(words),source_context_responses=len(contexts),full_native_entries=len(entries),new_raw_paths=len(new_paths),judged_new_paths=sum(bool(p['judgments'])for p in new_paths),unjudged_new_paths=sum(not p['judgments']for p in new_paths)))
    if args.expected:
        with gzip.open(args.expected,'rt')as file:expected=json.load(file)
        for k in ['words','new_paths','checks','entries','contexts','index_sha256']:assert report[k]==expected[k],('runtime differs',k)
    with args.output.open('xb')as sink,gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0)as archive:archive.write(json.dumps(report,ensure_ascii=False,separators=(',',':')).encode())
    print(json.dumps(report['counts']),flush=True)
finally:
    if owned is not None:
        if owned.poll()is None:owned.terminate()
        owned.wait()
