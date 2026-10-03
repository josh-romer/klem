"""Compare eight complete streams without storing duplicate novel output."""
import argparse
from collections import Counter
import hashlib
import itertools
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, required=True)
parser.add_argument('--before-cli', type=Path, required=True)
parser.add_argument('--cli', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
args.before_cli = args.before_cli.resolve()
args.cli = args.cli.resolve()
assert not args.output.exists()
root = args.root.resolve()
db = root / 'data/dictionaries/krdict/krdict.db'
prior = json.loads((root / 'docs/question-topic-observations.json').read_text())

def sha(path):
    with Path(path).open('rb') as file:
        return hashlib.file_digest(file, 'sha256').hexdigest()

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

new_paths = {}
comparisons = []
changes = []
def audit(before, after, mode, location):
    assert {k:v for k,v in before.items() if k not in ('analysis','dictionary','spacing','breakdowns')} == {k:v for k,v in after.items() if k not in ('analysis','dictionary','spacing','breakdowns')}, (mode,location,'token metadata')
    bw, aw = before.get('analysis'), after.get('analysis')
    assert bool(bw) == bool(aw)
    if bw:
        assert bw['normalized'] == aw['normalized']
        retained = [a for a in aw['analyses'] if a in bw['analyses']]
        assert retained == bw['analyses'], (mode,location,'removed/modified/reordered path')
        bd, ad = before.get('dictionary'), after.get('dictionary')
        assert bool(bd) == bool(ad)
        if bd:
            assert (bd['source'],bd['fingerprint']) == (ad['source'],ad['fingerprint'])
            for slot in bd['lemmas']:
                assert slot in ad['lemmas'], (mode,location,'native entry metadata changed')
            for index, old in enumerate(bw['analyses']):
                current = aw['analyses'].index(old)
                assert bd['readings'][index] == ad['readings'][current], (mode,location,'old assessment')
        for index, a in enumerate(aw['analyses']):
            if a in bw['analyses']:
                continue
            assert 'particle.quoted_question' in a['rules'], (mode,location,'unexplained rule',a)
            assert any(m == dict(form='도',kind='particle') for m in a['morphemes']), (mode,location,'additive missing')
            key = canonical([aw['normalized'],a])
            if key not in new_paths:
                new_paths[key] = dict(id='question-additive-broad-'+hashlib.sha256(key.encode()).hexdigest()[:24], surface=aw['normalized'], analysis=a,
                    assessment=ad['readings'][index] if ad else None, occurrences=[], contextual_verdict='unjudged')
            new_paths[key]['occurrences'].append(dict(mode=mode, location=location, raw_or_filtered_index=index))
        if 'breakdowns' in before:
            for index, a in enumerate(bw['analyses']):
                assert before['breakdowns'][index] == after['breakdowns'][aw['analyses'].index(a)]
    bs, ns = before.get('spacing'), after.get('spacing')
    assert bool(bs) == bool(ns)
    if bs:
        assert {k:v for k,v in bs.items() if k!='alternatives'} == {k:v for k,v in ns.items() if k!='alternatives'}
        assert len(bs['alternatives']) == len(ns['alternatives'])
        for index, (b,a) in enumerate(zip(bs['alternatives'], ns['alternatives'])):
            assert {k:v for k,v in b.items() if k!='records'} == {k:v for k,v in a.items() if k!='records'}
            assert len(b['records']) == len(a['records'])
            for j,(br,ar) in enumerate(zip(b['records'],a['records'])):
                audit(br,ar,mode,[*location,'spacing',index,j])

for previous in prior['comparisons']:
    mode, source = previous['mode'], Path(previous['source'])
    assert sha(source) == previous['source_sha256']
    flags = ['--dict-compatible'] if 'compatible' in mode else ['--dict-only'] if 'headword' in mode else []
    command = ['text',str(source),'--dictionary',str(db),*flags]
    if 'spacing' in mode: command.append('--suggest-spacing')
    processes = [subprocess.Popen([str(cli),*command],stdout=subprocess.PIPE) for cli in (args.before_cli,args.cli)]
    hashes = [hashlib.sha256(),hashlib.sha256()]
    count = changed = 0
    try:
        for b,a in itertools.zip_longest(*(p.stdout for p in processes)):
            assert b is not None and a is not None
            count += 1
            hashes[0].update(b);hashes[1].update(a)
            if b != a:
                before,after = json.loads(b),json.loads(a)
                audit(before,after,mode,[count-1])
                changes.append(dict(mode=mode,record_index=count-1,before=before,after=after))
                changed += 1
        assert all(p.wait()==0 for p in processes)
    finally:
        for p in processes:
            if p.poll() is None: p.terminate();p.wait()
    assert count == previous['records']
    assert hashes[0].hexdigest() == previous['after_jsonl_sha256'], (mode,'old baseline differs')
    comparisons.append(dict(mode=mode,source=str(source),source_sha256=sha(source),records=count,before_jsonl_sha256=hashes[0].hexdigest(),after_jsonl_sha256=hashes[1].hexdigest(),changed_records=changed))
    print(mode,count,'records;',changed,'changed',flush=True)

shape_counts = Counter()
for item in new_paths.values():
    surface, analysis = item['surface'], item['analysis']
    if surface.endswith('도'):
        shape_counts['literal_question_additive'] += 1
    else:
        # Do not assume that every nonliteral surface represents the same
        # contraction. Keep the actual components/rules in the individual queue.
        outer=[r for r in analysis['rules'] if r in ('particle.polite','particle.contraction.n','ending.enumerative_yo')]
        assert outer,(surface,analysis)
        shape_counts['+'.join(outer)] += 1

report = dict(schema_version=1,checklist='COV-018ad',before_revision='5419e9c',
    before_cli=str(args.before_cli),before_cli_sha256=sha(args.before_cli),cli=str(args.cli),cli_sha256=sha(args.cli),
    dictionary_sha256=sha(db),comparisons=comparisons,complete_changed_records=changes,new_paths=list(new_paths.values()),
    all_original_baseline_hashes_verified=True,all_prior_candidates_order_assessments_components_and_native_fields_preserved=True,
    additive_shape_counts=dict(shape_counts),
    composition_scope='Every additional boundary comes from the reviewed literal question/do composition, possibly followed by existing outer particle rules. All contextual interpretations and registers remain individually unjudged.',
    interpretation='Complete stream comparison; new alternatives are individually tracked and contextually unjudged. No precision, contextual grammaticality or performance claim.')
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('Completed',sum(c['records'] for c in comparisons),'records;',len(new_paths),'individual new paths',flush=True)
