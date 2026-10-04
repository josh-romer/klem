"""Verify the frozen continuation cohort through the full dictionary CLI/API."""
import argparse
import gzip
import hashlib
import json
import subprocess
import unicodedata
import urllib.request
from pathlib import Path
from continuation_left_compare import Audit, sha

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cli',type=Path,required=True);p.add_argument('--server',type=Path,required=True)
    p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--url');p.add_argument('--expected',type=Path)
    args=p.parse_args();assert not args.output.exists()
    source=json.loads((ROOT/'tests/fixtures/continuation-left-sources.json').read_text())
    overlay=json.loads((ROOT/'tests/fixtures/continuation-left-written-vowel-judgments.json').read_text())
    vowel_compat=json.loads((ROOT/'tests/fixtures/continuation-left-vowel-compat-judgments.json').read_text())
    frozen=dict(source['before_words'])
    for c in overlay['cases']:
        assert c['surface']not in frozen
        frozen[c['surface']]=c['before_words']
    for u in vowel_compat['cases']:
        surface=u['original_case']['surface']
        if surface in frozen:assert frozen[surface]==u['before_words']
        else:frozen[surface]=u['before_words']
    db=ROOT/'data/dictionaries/krdict/krdict.db';assert sha(db)==source['dictionary_sha256']
    audit=Audit(args.cli.resolve(),db);owned=None
    try:
        if args.url:base=args.url
        else:
            owned=subprocess.Popen([str(args.server.resolve()),'--port','0','--assets',str(args.assets.resolve()),'--dictionary',str(db)],stderr=subprocess.PIPE,text=True)
            line=owned.stderr.readline().strip();assert 'http://127.0.0.1:'in line,line
            base='http://'+line.split('http://',1)[1].split()[0]
        def post(endpoint,body):
            request=urllib.request.Request(base+'/api/'+endpoint,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=30)as response:return json.load(response)
        words={}
        for surface,modes in frozen.items():
            actual={}
            for mode,flags in [('all',[]),('headword',['--dict-only']),('compatible',['--dict-compatible'])]:
                current=json.loads(subprocess.check_output([str(args.cli.resolve()),'word',surface,'--dictionary',str(db),*flags]))
                decomposed=json.loads(subprocess.check_output([str(args.cli.resolve()),'word',unicodedata.normalize('NFD',surface),'--dictionary',str(db),*flags]))
                assert current==decomposed,(surface,mode,'NFD')
                audit.word(modes[mode],current,mode,['runtime',surface,mode]);actual[mode]=current
            api=post('analyze',dict(text=surface,suggest_spacing=False))
            records=[json.loads(line)for line in subprocess.check_output([str(args.cli.resolve()),'text','--dictionary',str(db)],input=surface.encode()).splitlines()]
            assert api['records']==records
            assert len(api['breakdowns'][0])==len(actual['all']['analyses'])
            for index,a in enumerate(actual['all']['analyses']):
                assert len(api['breakdowns'][0][index])==len(a['lemmas'])+len(a['morphemes'])
            api.pop('elapsed_ms');actual['api']=api;words[surface]=actual
        checks=[]
        for c in source['cases']:
            j=c['judgments'][0]
            def match(a):return [l['text']for l in a['lemmas']]==j['lemmas']and[l['kind']for l in a['lemmas']]==j['lemma_kinds']and[m['form']for m in a['morphemes']]==j['morphemes']and[m['kind']for m in a['morphemes']]==j['morpheme_kinds']
            word=words[c['surface']];indices=[i for i,a in enumerate(word['all']['analyses'])if match(a)]
            assert indices and any(match(a)for a in word['headword']['analyses'])
            assert any(match(a)for a in word['compatible']['analyses'])==(j['verdict']=='required'),c['id']
            checks.append(dict(case=c['id'],raw_indices=indices,compatible_verdict=j['verdict'],contextual_verdict='unjudged'))
        for c in overlay['cases']:
            word=words[c['surface']]
            indices=[i for i,a in enumerate(word['all']['analyses'])if a['lemmas']==c['lemmas']and a['morphemes']==c['morphemes']]
            assert indices
            for index in indices:
                reading=word['all']['dictionary']['readings'][index]
                entry=next(e for e in reading['lemmas'][0]['entries']if e['id']==c['entry_id'])
                assert entry==c['after']
                assert word['all']['analyses'][index]not in word['compatible']['analyses']
            checks.append(dict(case=c['id'],raw_indices=indices,compatible_verdict='forbidden',contextual_verdict='unjudged'))
        for u in vowel_compat['cases']:
            c=u['original_case'];word=words[c['surface']]
            indices=[i for i,a in enumerate(word['all']['analyses'])if a['lemmas']==c['lemmas']and a['morphemes']==c['morphemes']]
            assert indices==c['before_candidate_indices']
            for index in indices:
                reading=word['all']['dictionary']['readings'][index]
                entry=next(e for e in reading['lemmas'][0]['entries']if e['id']==c['owner_id'])
                assert entry==u['after']
                assert (word['all']['analyses'][index]in word['compatible']['analyses'])==u['compatible_retained']
            checks.append(dict(case=c['id'],raw_indices=indices,compatible_verdict='required'if u['compatible_retained']else'forbidden',contextual_verdict='unjudged'))
        native=dict(source['complete_native_entries'])
        native.update(overlay['complete_native_entries'])
        native.update(vowel_compat['complete_native_entries'])
        entries={i:post('entry',dict(id=i))['entry']for i in native}
        assert entries==native
        with urllib.request.urlopen(base,timeout=30)as response:html=response.read()
        report=dict(schema_version=1,checklist='COV-019ad',source_sha256=sha(ROOT/'tests/fixtures/continuation-left-sources.json'),
            cli=str(args.cli.resolve()),cli_sha256=sha(args.cli),server=str(args.server.resolve()),server_sha256=sha(args.server),
            assets=str(args.assets.resolve()),dictionary_sha256=sha(db),words=words,checks=checks,entries=entries,
            written_vowel_overlay_sha256=sha(ROOT/'tests/fixtures/continuation-left-written-vowel-judgments.json'),
            vowel_compat_overlay_sha256=sha(ROOT/'tests/fixtures/continuation-left-vowel-compat-judgments.json'),
            changed_entries=list(audit.changes.values()),removed_paths=list(audit.removals.values()),
            index_sha256=hashlib.sha256(html).hexdigest(),counts=dict(surfaces=len(words),cli_word_responses=len(words)*6,
                api_word_responses=len(words),native_entries=len(entries),policy_cases=len(checks),dictionary_ledger_cases=len(source['cases']),historical_policy_updates=len(overlay['cases'])+len(vowel_compat['cases']),changed_entries=len(audit.changes),removed_paths=len(audit.removals)))
        if args.expected:
            with gzip.open(args.expected,'rt')as file:expected=json.load(file)
            for k in ['words','checks','entries','changed_entries','removed_paths','index_sha256']:assert report[k]==expected[k],k
        with args.output.open('xb')as sink,gzip.GzipFile(filename='',mode='wb',fileobj=sink,mtime=0)as archive:archive.write(json.dumps(report,ensure_ascii=False,separators=(',',':')).encode())
        print(json.dumps(report['counts']),flush=True)
    finally:
        if owned is not None:
            if owned.poll()is None:owned.terminate()
            owned.wait()
if __name__=='__main__':main()
