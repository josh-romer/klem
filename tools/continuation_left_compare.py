"""Compare frozen source diagnostics and complete streams for class-only changes.

Raw paths, native metadata and existing conflicts must be preserved. Compatible
filter removals require an individually recorded continuation conflict. These
observations do not certify contextual correctness or select a native sense.
"""
import argparse
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()
def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

class Audit:
    def __init__(self, cli, dictionary):
        self.cli, self.dictionary = cli, dictionary
        self.raw = {}
        self.changes = {}
        self.removals = {}

    def raw_word(self, surface):
        if surface not in self.raw:
            self.raw[surface] = json.loads(subprocess.check_output([
                str(self.cli), 'word', surface, '--dictionary', str(self.dictionary)]))
        return self.raw[surface]

    def reading(self, surface, analysis, before, after, location):
        assert [s['lemma_index'] for s in before['lemmas']] == [s['lemma_index'] for s in after['lemmas']]
        altered = False
        for old, new in zip(before['lemmas'], after['lemmas']):
            assert [e['id'] for e in old['entries']] == [e['id'] for e in new['entries']]
            for b, a in zip(old['entries'], new['entries']):
                if b == a:
                    continue
                assert b['status'] in ('compatible', 'unknown') and a['status'] == 'incompatible', (surface,b,a)
                assert a['conflicts'][:-1] == b['conflicts']
                conflict = a['conflicts'][-1]
                assert conflict['rule'] == 'continuation_verb'
                assert analysis['morphemes'][conflict['morpheme_index']]['form'] in ('어', '고')
                key = canonical([surface, analysis, old['lemma_index'], b['id']])
                if key not in self.changes:
                    self.changes[key] = dict(id='continuation-left-entry-'+hashlib.sha256(key.encode()).hexdigest()[:24],
                        surface=surface, analysis=analysis, lemma_index=old['lemma_index'], entry_id=b['id'],
                        before=b, after=a, occurrences=[], contextual_verdict='unjudged')
                self.changes[key]['occurrences'].append(location)
                altered = True
        assert before == after or altered, (surface, 'unexplained aggregate change')

    def word(self, before, after, mode, location):
        assert before['normalized'] == after['normalized']
        surface = before['normalized']
        old, new = before['analyses'], after['analyses']
        if 'compatible' in mode:
            assert [a for a in old if a in new] == new, (surface, 'filtered path order')
        else:
            assert old == new, (surface, 'raw/headword candidates changed')
        bd, ad = before['dictionary'], after['dictionary']
        assert (bd['source'],bd['fingerprint']) == (ad['source'],ad['fingerprint'])
        assert all(m in bd['lemmas'] for m in ad['lemmas']), (surface, 'native fields changed')
        if 'compatible' not in mode:
            assert bd['lemmas'] == ad['lemmas']
        for index, analysis in enumerate(old):
            if analysis in new:
                self.reading(surface,analysis,bd['readings'][index],ad['readings'][new.index(analysis)],location)
            else:
                raw = self.raw_word(surface)
                raw_index = raw['analyses'].index(analysis)
                assessment = raw['dictionary']['readings'][raw_index]
                assert assessment['status'] == 'incompatible'
                self.reading(surface,analysis,bd['readings'][index],assessment,location)
                key = canonical([surface,analysis])
                if key not in self.removals:
                    self.removals[key] = dict(id='continuation-left-filter-'+hashlib.sha256(key.encode()).hexdigest()[:24],
                        surface=surface,analysis=analysis,raw_index=raw_index,assessment=assessment,
                        occurrences=[],contextual_verdict='unjudged')
                self.removals[key]['occurrences'].append(location)

    def record(self, before, after, mode, location):
        ignored = ('analysis','dictionary','spacing','breakdowns')
        assert {k:v for k,v in before.items() if k not in ignored} == {k:v for k,v in after.items() if k not in ignored}
        bw, aw = before.get('analysis'), after.get('analysis')
        assert (bw is None) == (aw is None)
        if bw is not None:
            self.word(dict(bw,dictionary=before['dictionary']),dict(aw,dictionary=after['dictionary']),mode,location)
        bs, ns = before.get('spacing'), after.get('spacing')
        assert (bs is None) == (ns is None)
        if bs is not None:
            assert {k:v for k,v in bs.items() if k!='alternatives'} == {k:v for k,v in ns.items() if k!='alternatives'}
            assert len(bs['alternatives']) == len(ns['alternatives'])
            for index,(b,a) in enumerate(zip(bs['alternatives'],ns['alternatives'])):
                assert {k:v for k,v in b.items() if k!='records'} == {k:v for k,v in a.items() if k!='records'}
                assert len(b['records']) == len(a['records'])
                for j,(br,ar) in enumerate(zip(b['records'],a['records'])):
                    self.record(br,ar,mode,[*location,'spacing',index,j])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before-cli',type=Path,required=True)
    p.add_argument('--cli',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assert not args.output.exists()
    args.cli=args.cli.resolve();args.before_cli=args.before_cli.resolve()
    db=ROOT/'data/dictionaries/krdict/krdict.db'
    source=json.loads((ROOT/'tests/fixtures/continuation-left-sources.json').read_text())
    assert sha(db)==source['dictionary_sha256'] and sha(args.before_cli)==source['cli_sha256']
    overlay=json.loads((ROOT/'tests/fixtures/continuation-left-written-vowel-judgments.json').read_text())
    assert overlay['before_cli_sha256']==source['cli_sha256']
    frozen=dict(source['before_words'])
    for c in overlay['cases']:
        assert c['surface']not in frozen
        frozen[c['surface']]=c['before_words']
    vowel_compat=json.loads((ROOT/'tests/fixtures/continuation-left-vowel-compat-judgments.json').read_text())
    assert vowel_compat['before_cli_sha256']==source['cli_sha256']
    for u in vowel_compat['cases']:
        surface=u['original_case']['surface']
        if surface in frozen:assert frozen[surface]==u['before_words']
        else:frozen[surface]=u['before_words']
    audit=Audit(args.cli,db);diagnostics=[]
    for surface,modes in frozen.items():
        changed=[]
        for mode,flags in [('all',[]),('headword',['--dict-only']),('compatible',['--dict-compatible'])]:
            after=json.loads(subprocess.check_output([str(args.cli),'word',surface,'--dictionary',str(db),*flags]))
            audit.word(modes[mode],after,mode,['diagnostic',surface,mode])
            if modes[mode]!=after:changed.append(mode)
        diagnostics.append(dict(surface=surface,changed_modes=changed))
    print('Source diagnostics:',len(diagnostics),'surfaces verified',flush=True)
    prior=json.loads((ROOT/'docs/question-additive-observations.json').read_text())
    comparisons=[]
    for previous in prior['comparisons']:
        mode,path=previous['mode'],Path(previous['source'])
        assert sha(path)==previous['source_sha256']
        flags=['--dict-compatible']if'compatible'in mode else['--dict-only']if'headword'in mode else[]
        command=['text',str(path),'--dictionary',str(db),*flags]
        if'spacing'in mode:command.append('--suggest-spacing')
        processes=[subprocess.Popen([str(cli),*command],stdout=subprocess.PIPE)for cli in(args.before_cli,args.cli)]
        hashes=[hashlib.sha256(),hashlib.sha256()];count=changed=0
        try:
            for b,a in itertools.zip_longest(*(p.stdout for p in processes)):
                assert b is not None and a is not None
                count+=1;hashes[0].update(b);hashes[1].update(a)
                if b!=a:
                    audit.record(json.loads(b),json.loads(a),mode,[mode,count-1]);changed+=1
            assert all(p.wait()==0 for p in processes)
        finally:
            for process in processes:
                if process.poll()is None:process.terminate()
                process.wait()
        assert count==previous['records'] and hashes[0].hexdigest()==previous['after_jsonl_sha256']
        comparisons.append(dict(mode=mode,source=str(path),source_sha256=sha(path),records=count,
            before_jsonl_sha256=hashes[0].hexdigest(),after_jsonl_sha256=hashes[1].hexdigest(),changed_records=changed))
        print(mode,count,'records;',changed,'changed',flush=True)
    report=dict(schema_version=1,checklist='COV-019ad',before_revision=source['before_revision'],
        before_cli=str(args.before_cli),before_cli_sha256=sha(args.before_cli),cli=str(args.cli),cli_sha256=sha(args.cli),
        dictionary_sha256=sha(db),diagnostics=diagnostics,comparisons=comparisons,
        changed_entries=list(audit.changes.values()),removed_paths=list(audit.removals.values()),
        raw_candidates_order_and_native_fields_preserved=True,existing_conflicts_preserved=True,
        all_baseline_stream_hashes_verified=True,contextual_verdict='unjudged')
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('Individual changes:',len(audit.changes),'entries;',len(audit.removals),'filtered paths',flush=True)
if __name__=='__main__':main()
