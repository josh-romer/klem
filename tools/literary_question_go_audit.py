"""Independently derive the complete question-go source and addition inventory."""
import argparse
import gzip
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from native_lmf import entry, verify_native_lmf

sha=lambda raw:hashlib.sha256(raw).hexdigest()
def read(path):
    raw=Path(path).read_bytes()
    return json.loads(gzip.decompress(raw) if str(path).endswith('.gz') else raw)
def match(a,e):
    return ([l['text'] for l in a['lemmas']]==e['lemmas'] and [l['kind'] for l in a['lemmas']]==e['lemma_kinds']
            and [m['form'] for m in a['morphemes']]==e['morphemes'] and [m['kind'] for m in a['morphemes']]==e['morpheme_kinds']
            and set(e['required_rules'])<=set(a['rules']))

def inspect(capture,prepared,replay,cases,catalog):
    for report in [capture,prepared,replay]:
        assert sha(report['producer']['text'].encode())==report['producer']['sha256']
    assert capture['state']==replay['state']=='passed' and capture['exit_code']==replay['exit_code']==0
    assert capture['inputs_unchanged'] is replay['inputs_unchanged'] is True
    native=prepared['complete_native_entries'];assert len(native)==106
    assert set(prepared['original_lmf'])==set(native)
    for ident,raw in prepared['original_lmf'].items():assert entry(raw)==native[ident]
    verify_native_lmf(prepared['english_projection'],native)
    primary=['krdict:'+str(i) for i in [73889,73892,73898,73901]]
    assert prepared['primary_entry_ids']==list(capture['sqlite_entries'])==primary
    assert all(capture['sqlite_entries'][i]==native[i] for i in primary)
    groups=[{'source':ident,'sense':sense['id'],'index':i,'original':group}
            for ident in primary for sense in native[ident]['senses'] for i,group in enumerate(sense['examples'])]
    assert capture['all_original_groups']==groups and len(groups)==39
    assert capture['input']=='\n'.join(line for group in groups for line in group['original'])+'\n'
    assert len(cases)==39 and len({c['id'] for c in cases})==39
    assert [c['source_occurrence'] for c in cases]==capture['targets']
    for case in cases:
        t=case['source_occurrence'];assert case['surface']==t['surface']
        assert case['id']==f'literary-question-go-original-{t["source"].split(":")[1]}-{t["sense"]}-{t["group_index"]}'
        assert capture['input'][t['char_span']['start']:t['char_span']['end']]==case['surface']
        assert case['contextual_verdict']=='unjudged' and case['independent_review']=='pending'
    for form,ids in [('은고',[73889,73901]),('는고',[73898]),('던고',[73892])]:
        atom=catalog['-'+form];assert atom['label']=='Literary question' and atom['kind']=='ending'
        assert [s['id'] for s in atom['sources']]==ids
        assert all(s['headword']==native['krdict:'+str(s['id'])]['headword'] and s['pos']=='어미' for s in atom['sources'])
    keys=[(e,m) for e in ['NFC','NFD'] for m in ['raw','headword','compatible']]
    assert [(r['encoding'],r['mode']) for r in capture['runs']]==keys
    assert [(r['encoding'],r['mode']) for r in replay['runs']]==keys
    observations, additions, owners=[],[],set()
    for before,after in zip(capture['runs'],replay['runs'],strict=True):
        encoding,mode=before['encoding'],before['mode'];text=unicodedata.normalize(encoding,capture['input'])
        assert sha(text.encode())==before['input_sha256']==after['input_sha256']
        assert sha(before['jsonl'].encode())==before['sha256']==after['before_sha256']
        assert sha(after['jsonl'].encode())==after['after_sha256'] and after['exit_code']==0
        old=list(map(json.loads,before['jsonl'].splitlines()));now=list(map(json.loads,after['jsonl'].splitlines()))
        assert len(old)==len(now)==after['records']==535
        cursor=0
        for i,(a,b) in enumerate(zip(old,now,strict=True)):
            assert b['span']['start']==cursor and text.encode()[cursor:b['span']['end']].decode()==b['surface']
            cursor=b['span']['end']
            assert {k:v for k,v in a.items() if k not in ['analysis','dictionary']}=={k:v for k,v in b.items() if k not in ['analysis','dictionary']}
            if a.get('analysis') is None:assert a==b;continue
            oa,na=a['analysis']['analyses'],b['analysis']['analyses']
            assert [p for p in na if p in oa]==oa
            assert a['dictionary']['source']==b['dictionary']['source'] and a['dictionary']['fingerprint']==b['dictionary']['fingerprint']
            for p,assessment in zip(oa,a['dictionary']['readings'],strict=True):assert b['dictionary']['readings'][na.index(p)]==assessment
            assert all(e in b['dictionary']['lemmas'] for e in a['dictionary']['lemmas'])
            for n,p in enumerate(na):
                if p in oa:continue
                assert 'ending.literary_question_go' in p['rules']
                assessment=b['dictionary']['readings'][n];owners.update(e['id'] for slot in assessment['lemmas'] for e in slot['entries'])
                ident='literary-question-go-source-addition-'+sha(json.dumps([encoding,mode,i,p],ensure_ascii=False,sort_keys=True).encode())[:24]
                additions.append({'encoding':encoding,'mode':mode,'frame_index':i,'surface':b['surface'],'span':b['span'],
                                  'analysis':p,'assessment':assessment,'id':ident,'structural_verdict':'unjudged','contextual_verdict':'unjudged','independent_review':'pending'})
        assert cursor==len(text.encode())
        for case in cases:
            target=case['source_occurrence'];start,end=target['char_span']['start'],target['char_span']['end']
            span={'start':len(unicodedata.normalize(encoding,capture['input'][:start]).encode()),'end':len(unicodedata.normalize(encoding,capture['input'][:end]).encode())}
            row=next(r for r in now if r['span']==span)
            matches=[i for i,p in enumerate(row['analysis']['analyses']) if match(p,case['expected'])]
            assert len(matches)==1
            n=matches[0];assessment=row['dictionary']['readings'][n]
            if target['source']=='krdict:73892':assert assessment['status']=='unknown'
            observations.append({'encoding':encoding,'mode':mode,'target':target,'span':span,'case_id':case['id'],'expected':case['expected'],
                                 'analysis':row['analysis']['analyses'][n],'assessment':assessment,'structural_verdict':'required','contextual_verdict':'unjudged','independent_review':'pending'})
    assert observations==replay['original_targets'] and len(observations)==234
    assert additions==replay['individual_additions'] and len(additions)==786
    assert len({a['id'] for a in additions})==786
    assert sorted(owners)==replay['matched_native_owner_ids']==prepared['matched_native_owner_ids'] and len(owners)==70
    assert owners<=native.keys()
    required=[];unjudged=[]
    for a in additions:
        refs=[{'case':o['case_id'],'judgment':'original-whole-ending'} for o in observations
              if (o['encoding'],o['mode'],o['span'],o['analysis'])==(a['encoding'],a['mode'],a['span'],a['analysis'])]
        item=dict(a,structural_verdict='required' if refs else 'unjudged',structural_judgment_refs=refs)
        (required if refs else unjudged).append(item)
    assert len(required)==234 and len(unjudged)==552
    return {'source_frames':3210,'original_required_observations':234,'unjudged_additions':552,'matched_native_owners':70,'complete_native_entries':106,
            'required':required,'unjudged':unjudged,'contextual_verdict':'unjudged','independent_review':'pending'}

def verify_ledger(before, current, proposal):
    """Check the immutable old prefix and each individually authored addition."""
    assert proposal['before_case_count'] == len(before['cases']) == 34781
    assert proposal['after_case_count'] == 34843
    assert len(proposal['added_cases']) == 62
    assert current['cases'][:34781] == before['cases']
    assert current['cases'][34781:34843] == proposal['added_cases']
    assert len({case['id'] for case in current['cases']}) == len(current['cases'])
    assert all(current['sources'][key] == value for key, value in before['sources'].items())
    assert all(current['sources'][key] == value for key, value in proposal['after_sources'].items())
    counts = {verdict: sum(judgment['verdict'] == verdict
                          for case in proposal['added_cases']
                          for judgment in case['judgments'])
              for verdict in ['required', 'forbidden']}
    assert counts == proposal['added_judgments'] == {'required': 58, 'forbidden': 4}
    assert sum(case['id'].startswith('literary-question-go-original-')
               for case in proposal['added_cases']) == 39
    return {'historical_cases_preserved': 34781, 'new_individual_cases': 62,
            'new_required': 58, 'new_forbidden': 4}


def audit_current():
    result = inspect(read(ROOT/'docs/literary-question-go-source-discovery.json.gz'),
                     read(ROOT/'docs/literary-question-go-source-owner-preparation.json.gz'),
                     read(ROOT/'docs/literary-question-go-prototype-source-replay.json.gz'),
                     read(ROOT/'tests/fixtures/literary-question-go-original-cases.json'),
                     read(ROOT/'web/src/grammar-labels.json'))
    from ostensible_reason_sources import package_source_texts
    old = json.loads(package_source_texts(read(ROOT/'docs/ostensible-reason-package-nix.json'))[
        'tests/fixtures/validity.json'])
    result['ledger'] = verify_ledger(old, read(ROOT/'tests/fixtures/validity.json'),
                                   read(ROOT/'docs/literary-question-go-append-only-ledger-proposal.json.gz'))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit_current()
    if args.output:
        raw = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode()
        args.output.write_bytes(gzip.compress(raw, mtime=0) if str(args.output).endswith('.gz') else raw)
    print({key: value for key, value in result.items() if key not in ['required', 'unjudged']})
