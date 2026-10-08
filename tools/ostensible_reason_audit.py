"""Derive source, span, ownership and individual addition judgments independently."""
import argparse
import gzip
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from native_lmf import entry, verify_native_lmf

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def matches(analysis, judgment):
    return ([l['text'] for l in analysis['lemmas']]==judgment['lemmas']
            and [l['kind'] for l in analysis['lemmas']]==judgment['lemma_kinds']
            and [m['form'] for m in analysis['morphemes']]==judgment['morphemes']
            and [m['kind'] for m in analysis['morphemes']]==judgment['morpheme_kinds']
            and set(judgment['required_rules'])<=set(analysis['rules']))


def producer(report):
    assert sha(report['producer']['text'].encode())==report['producer']['sha256']


def inspect_ledger(before, current, suite):
    """Keep the historical ledger intact and append the finite new judgments."""
    count = len(before['cases'])
    assert current['schema_version'] == before['schema_version'] == suite['schema_version'] == 1
    assert current['cases'][:count] == before['cases']
    assert current['cases'][count:count+len(suite['cases'])] == suite['cases']
    assert all(current['sources'][key] == value for key, value in before['sources'].items())
    assert all(current['sources'][key] == value for key, value in suite['sources'].items())
    assert len({case['id'] for case in current['cases']}) == len(current['cases'])
    return {'historical_cases_preserved':count, 'new_individual_cases':len(suite['cases'])}


def historical_ledger():
    from declarative_contrast_sources import package_source_texts
    sources = package_source_texts(read(ROOT/'docs/declarative-contrast-package-nix.json'))
    return json.loads(sources['tests/fixtures/validity.json'])


def inspect(capture, preparation, replay, originals, suite, catalog):
    for report in [capture,preparation,replay]:
        producer(report)
    assert capture['state']==replay['state']=='passed' and capture['exit_code']==replay['exit_code']==0
    assert capture['inputs_unchanged'] is True and replay['inputs_unchanged'] is True
    native = preparation['complete_native_entries']
    assert len(native)==84 and set(native)==set(preparation['original_lmf'])
    for ident,raw in preparation['original_lmf'].items():
        assert entry(raw)==native[ident]
    verify_native_lmf(preparation['english_projection'],native)
    primary = [f'krdict:{ident}' for ident in [80316,80317,80318]]
    assert preparation['primary_entry_ids']==primary and list(capture['sqlite_entries'])==primary
    assert all(capture['sqlite_entries'][ident]==native[ident] for ident in primary)
    groups = [{'source':ident,'sense':sense['id'],'index':index,'original':group}
              for ident in primary for sense in native[ident]['senses']
              for index,group in enumerate(sense['examples'])]
    assert groups==capture['all_original_groups'] and len(groups)==12
    lines, targets, cursor = [], [], 0
    for group in groups:
        for line_index,text in enumerate(group['original']):
            lines.append(text)
            for match in re.finditer(r'[가-힣]*답시고',text):
                targets.append({'source':group['source'],'sense':group['sense'],'group_index':group['index'],
                                'line_index':line_index,'surface':match.group(),
                                'char_span':{'start':cursor+match.start(),'end':cursor+match.end()}})
            cursor += len(text)+1
    assert '\n'.join(lines)+'\n'==capture['input'] and targets==capture['targets'] and len(targets)==12
    assert len(originals)==12
    assert {c['id'] for c in originals}=={f'ostensible-reason-original-{t["source"].split(":")[1]}-{t["group_index"]}' for t in targets}
    assert len(suite['cases'])==26 and len({c['id'] for c in suite['cases']})==26
    assert set(suite['sources'])=={'80316','80317','80318'}
    cases = {c['id']:c for c in suite['cases']}
    judgments = [j for c in suite['cases'] for j in c['judgments']]
    assert sum(j['verdict']=='required' for j in judgments)==21 and sum(j['verdict']=='forbidden' for j in judgments)==5
    for original,target in zip(originals,targets,strict=True):
        assert original['source_occurrence']==target and original['surface']==target['surface']
        case = cases[original['id']]
        assert case['surface']==original['surface']
        assert len(case['judgments'])==1 and case['judgments'][0]['verdict']=='required'
        assert case['judgments'][0]['source']==target['source'].split(':')[1]
        assert all(case['judgments'][0][k]==v for k,v in original['expected'].items())
    for form,ids in [('답시고',[80318]),('는답시고',[80316,80317])]:
        atom = catalog['-'+form]
        assert atom['kind']=='ending' and atom['label']=='Claimed reason (disapproving)'
        assert [s['id'] for s in atom['sources']]==ids
        assert all(s['headword']==native[f'krdict:{s["id"]}']['headword'] and s['pos']=='어미' for s in atom['sources'])
    keys = [(encoding,mode) for encoding in ['NFC','NFD'] for mode in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in capture['runs']]==keys
    assert [(r['encoding'],r['mode']) for r in replay['runs']]==keys
    additions, observations, owners, derived = [], [], set(), []
    for before,after in zip(capture['runs'],replay['runs'],strict=True):
        encoding,mode = before['encoding'],before['mode']
        text = unicodedata.normalize(encoding,capture['input'])
        assert before['input_sha256']==after['input_sha256']==sha(text.encode())
        assert sha(before['jsonl'].encode())==before['sha256']==after['before_sha256']
        assert sha(after['jsonl'].encode())==after['after_sha256'] and after['exit_code']==0
        old = list(map(json.loads,before['jsonl'].splitlines()))
        now = list(map(json.loads,after['jsonl'].splitlines()))
        assert len(old)==len(now)==before['records']==after['records']==233
        target_by_span = {}
        for original in originals:
            target = original['source_occurrence']
            start,end = target['char_span']['start'],target['char_span']['end']
            span = {'start':len(unicodedata.normalize(encoding,capture['input'][:start]).encode()),
                    'end':len(unicodedata.normalize(encoding,capture['input'][:end]).encode())}
            target_by_span[(span['start'],span['end'])] = original
            frame = next(r for r in now if r['span']==span)
            previous = next(r for r in old if r['span']==span)
            if encoding=='NFC' and mode=='raw':
                assert previous['analysis']==original['before']
            found = [i for i,a in enumerate(frame['analysis']['analyses']) if matches(a,original['expected'])]
            assert len(found)==1
            index = found[0]
            assert frame['dictionary']['readings'][index]['status']=='compatible'
            observations.append({'encoding':encoding,'mode':mode,'target':target,'span':span,'expected':original['expected'],
                                 'analysis':frame['analysis']['analyses'][index],'assessment':frame['dictionary']['readings'][index],
                                 'structural_verdict':'required','contextual_verdict':'unjudged','independent_review':'pending'})
        for index,(previous,current) in enumerate(zip(old,now,strict=True)):
            assert {k:v for k,v in previous.items() if k not in ['analysis','dictionary']}=={k:v for k,v in current.items() if k not in ['analysis','dictionary']}
            assert current['surface']==text.encode()[current['span']['start']:current['span']['end']].decode()
            if previous.get('analysis') is None:
                assert previous==current
                continue
            oa,na = previous['analysis']['analyses'],current['analysis']['analyses']
            od,nd = previous['dictionary'],current['dictionary']
            assert [a for a in na if a in oa]==oa
            assert current['analysis']['normalized']==previous['analysis']['normalized']
            assert od['source']==nd['source'] and od['fingerprint']==nd['fingerprint']
            assert len(oa)==len(od['readings']) and len(na)==len(nd['readings'])
            for analysis,assessment in zip(oa,od['readings'],strict=True):
                assert nd['readings'][na.index(analysis)]==assessment
            assert all(match in nd['lemmas'] for match in od['lemmas'])
            for n,analysis in enumerate(na):
                if analysis in oa:
                    continue
                assessment = nd['readings'][n]
                owners.update(e['id'] for slot in assessment['lemmas'] for e in slot['entries'])
                addition = {'encoding':encoding,'mode':mode,'frame_index':index,'surface':current['surface'],
                            'span':current['span'],'analysis':analysis,'assessment':assessment,
                            'structural_verdict':'unjudged','contextual_verdict':'unjudged','independent_review':'pending'}
                additions.append(addition)
                original = target_by_span.get((current['span']['start'],current['span']['end']))
                required = original is not None and matches(analysis,original['expected'])
                derived.append(dict(addition,structural_verdict='required' if required else 'unjudged',
                                    judgment_refs=[{'case':original['id'],'judgment':'whole-source-connective'}] if required else []))
    assert additions==replay['individual_additions'] and len(additions)==158
    assert observations==replay['original_targets'] and len(observations)==72
    assert sorted(owners)==replay['matched_native_owner_ids'] and len(owners)==29 and owners<=native.keys()
    assert sum(a['structural_verdict']=='required' for a in derived)==72
    return {'source_entries':3,'original_groups':12,'source_frames':1398,'target_mode_observations':72,
            'matched_native_owners':29,'complete_native_entries':84,'addition_observations':158,
            'source_required_additions':72,'unjudged_additions':86,'individual_judgments':derived}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preparation',type=Path,required=True)
    parser.add_argument('--replay',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    result = inspect(read(ROOT/'docs/ostensible-reason-source-discovery.json.gz'),read(args.preparation),read(args.replay),
                     read(ROOT/'tests/fixtures/ostensible-reason-original-cases.json'),
                     read(ROOT/'tests/fixtures/ostensible-reason-validity.json'),read(ROOT/'web/src/grammar-labels.json'))
    result['ledger'] = inspect_ledger(historical_ledger(), read(ROOT/'tests/fixtures/validity.json'),
                                      read(ROOT/'tests/fixtures/ostensible-reason-validity.json'))
    args.output.write_bytes(gzip.compress((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode(),mtime=0))
    print({k:v for k,v in result.items() if k!='individual_judgments'})


if __name__=='__main__':
    main()
