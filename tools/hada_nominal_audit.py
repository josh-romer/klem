"""Independently verify original noun-hada source licenses and captured path additions."""
import argparse
import copy
import hashlib
import json
import unicodedata
from pathlib import Path

from native_lmf import verify_native_lmf
from well_doeda_audit import ROOT, digest, read, sha, word_records

SOURCE=ROOT/'docs/hada-nominal-preflight.json.gz'
FIXTURE=ROOT/'tests/fixtures/hada-nominal-sources.json'
LMF=ROOT/'tests/fixtures/krdict-hada-six-sense.json'
REPORT=ROOT/'docs/hada-nominal-diagnostics.json.gz'
RULES={'1':'suffix.verb.hada','2':'suffix.adjective.hada'}


def inspect_source(source):
    assert source['schema_version']==1 and source['checklist']=='COV-022s'
    assert source['contextual_verdict']=='unjudged' and source['independent_review']=='pending'
    assert source['before_cli_sha256']==read(ROOT/'docs/nominal-si-hada-packaged-checks.json.gz')['cli_sha256']
    assert source['current_package_sha256']==sha(ROOT/'docs/nominal-si-hada-packaged-checks.json.gz')
    native=source['complete_native_entries'];assert len(native)==138
    assert source['lmf_sha256']==sha(LMF);verify_native_lmf(read(LMF),native)
    suffix=native[source['primary_suffix']]
    assert (suffix['headword'],suffix['pos'])==('-하다','접사')
    assert len(suffix['senses'])==6
    groups=[(s['id'],i,g,s['notes']) for s in suffix['senses'] for i,g in enumerate(s['examples'])]
    assert len(groups)==28 and len(source['all_sense_groups'])==28 and len(source['owners'])==28
    owners={o['whole_head']:o for o in source['owners'] if o['sense_id'] in RULES}
    assert len(owners)==11 and list(owners)==source['implemented_owner_heads']
    assert [sum(o['sense_id']==s for o in owners.values()) for s in RULES]==[6,5]
    for o,(sense,index,group,notes) in zip(source['owners'],groups,strict=True):
        assert (o['sense_id'],o['example_index'],o['original_group'],o['attachment_notes'])==(sense,index,group,notes)
        assert o['whole_head'] in group and o['whole_head']==o['base']+'하다'
        assert o['runtime_implemented'] is False # historical preflight, not a live status
        if sense not in RULES:continue
        assert o['base_role']=='nominal' and notes==['일부 명사 뒤에 붙는다.']
        pos='동사' if sense=='1' else '형용사'
        assert o['supported_predicate_classes']==[pos]
        whole=[native[i] for i in o['whole_entries']]
        assert whole and all(e['headword']==o['whole_head'] and e['pos']==pos for e in whole)
        expected=sorted({v.removesuffix('하다') for e in whole for v in e['origins']})
        assert expected==o['whole_expected_base_origins']
        for b in o['base_entries']:
            e=native[b['id']];assert (e['headword'],e['pos'],e['origins'])==(o['base'],'명사',b['origins'])
            relation='unknown' if not expected or not e['origins'] else 'recorded_match' if set(expected)&set(e['origins']) else 'recorded_difference'
            assert b['relation']==relation
    fixture=read(FIXTURE);assert fixture['source_sha256']==sha(SOURCE)
    for field in ['complete_native_entries','corpora']:assert fixture[field]==source[field]
    assert fixture['owners']==list(owners.values())
    assert len(source['words'])==len(set(source['words']))==649 and source['input']==' '.join(source['words'])
    for mode,run in source['before'].items():
        assert run['exit_code']==0 and hashlib.sha256(run['jsonl'].encode()).hexdigest()==run['sha256']
        records,words=word_records(run['jsonl']);assert set(words)==set(source['words'])
        assert ''.join(r['surface'] for r in records)==source['input']
        if mode=='raw':assert fixture['before_analyses']=={w:r['analysis'] for w,r in words.items()}
    cases=fixture['cases'];assert len(cases)==len({c['id'] for c in cases})==114
    assert sum(c['judgments'][0]['verdict']=='required' for c in cases)==88
    ledger=read(ROOT/'tests/fixtures/validity.json')
    assert [c for c in ledger['cases'] if c['id'].startswith('hada-noun-')]==cases
    assert ledger['sources']['hada-nominal-krdict']==suffix['url']
    parents={p['case_id']:p for p in fixture['required_parents']};assert len(parents)==88
    for c in cases:
        j=c['judgments'][0];value={k:v for k,v in j.items() if k != 'id'}
        ident='hada-noun-'+hashlib.sha256(json.dumps([c['surface'],value],sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
        assert c['id']==ident and j['id']==ident+'-structure' and j['source']=='hada-nominal-krdict'
        if j['verdict']!='required':continue
        p=parents[ident];parent=p['before_parent'];assert p['surface']==c['surface']
        assert parent in fixture['before_analyses'][c['surface']]['analyses']
        owner=owners[parent['lemmas'][0]['text']]
        assert j['lemmas']==[owner['base']]+[l['text'] for l in parent['lemmas'][1:]]
        assert j['lemma_kinds']==['nominal']+[l['kind'] for l in parent['lemmas'][1:]]
        assert j['morphemes']==['하다']+[m['form'] for m in parent['morphemes']]
        assert RULES[owner['sense_id']] in j['required_rules']
    rows=0
    for corpus in source['corpora']:
        path=ROOT/corpus['source'];text=path.read_text() if path.exists() else None
        if text is not None:assert sha(path)==corpus['sha256']
        for row in corpus['rows']:
            assert len(row['original_row'])==10
            assert '\t'.join(row['original_row']) in row['complete_sentence'].splitlines()
            if text is not None:assert row['complete_sentence'] in text
            rows+=1
    assert rows==1048
    for field in ['producer','baseline_producer']:
        assert hashlib.sha256(source[field]['text'].encode()).hexdigest()==source[field]['sha256']
    return owners


def parent_for(owners,word,analysis,before):
    # Inverse insertions at arbitrary component offsets; flags alone never establish ownership.
    restored=copy.deepcopy(analysis);insertions=[];added=set()
    for li,l in enumerate(analysis['lemmas']):
        if l['kind']!='nominal':continue
        owner=owners.get(l['text']+'하다')
        if owner is None:continue
        candidates=[mi for mi,m in enumerate(analysis['morphemes']) if m=={'form':'하다','kind':'suffix'}]
        # Frozen source cohort's noun owners occupy the initial lexical position.
        assert li==0 and candidates and candidates[0]==0,(word,analysis)
        rule=RULES[owner['sense_id']];assert rule in analysis['rules']
        insertions.append((li,0,owner));added.add(rule)
    assert len(insertions)==1,(word,analysis)
    li,mi,owner=insertions[0]
    restored['lemmas'][li]={'text':owner['whole_head'],'kind':'predicate'}
    restored['morphemes'].pop(mi)
    for path in restored.get('spelling_paths',[]):
        for recovery in path:
            assert recovery['morpheme_index']!=mi
            if recovery['morpheme_index']>mi:recovery['morpheme_index']-=1
    matches=[]
    for parent in before[word]['analysis']['analyses']:
        if sorted(set(parent['rules'])|added)!=analysis['rules']:continue
        restored['rules']=parent['rules']
        if restored==parent:matches.append(parent)
    assert matches,(word,analysis)
    return owner,matches[0]


def inspect_comparison(source,report):
    owners=inspect_source(source);native=source['complete_native_entries']
    assert report['source_sha256']==sha(SOURCE) and report['fixture_sha256']==sha(FIXTURE)
    assert report['dictionary_sha256']==source['dictionary_sha256']
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    _,raw_before=word_records(source['before']['raw']['jsonl']);changes=[]
    assert set(report['runs'])=={'raw','headword','compatible'}
    for mode,runs in report['runs'].items():
        _,before=word_records(source['before'][mode]['jsonl']);parity=None
        assert set(runs)=={'NFC-cached','NFC-uncached','NFD-cached','NFD-uncached'}
        for name,run in runs.items():
            assert run['exit_code']==0 and hashlib.sha256(run['jsonl'].encode()).hexdigest()==run['sha256']
            records,after=word_records(run['jsonl']);assert set(after)==set(before)
            assert ''.join(r['surface'] for r in records)==unicodedata.normalize(name.split('-')[0],source['input'])
            semantic={w:(r['analysis'],r['dictionary']) for w,r in after.items()}
            if parity is None:parity=semantic
            else:assert semantic==parity
        count=0;surfaces=[]
        for word,r in after.items():
            old=before[word]['analysis']['analyses'];new=r['analysis']['analyses']
            assert [a for a in new if a in old]==old,word
            extras=[a for a in new if a not in old]
            if extras:surfaces.append(word)
            count+=len(extras)
            for i,a in enumerate(new):
                reading=r['dictionary']['readings'][i]
                if a in old:
                    assert reading==before[word]['dictionary']['readings'][old.index(a)],word
                    continue
                owner,parent=parent_for(owners,word,a,raw_before)
                for entry in reading['lemmas'][0]['entries']:
                    e=native[entry['id']];identity=entry.get('derivational_identity')
                    if e['pos']!='명사':assert identity is None;continue
                    expected=owner['whole_expected_base_origins']
                    complete=all(native[i]['origins'] for i in owner['whole_entries']) # missing recorded origins cannot prove a difference
                    relation='unknown' if not expected or not e['origins'] else 'recorded_match' if set(expected)&set(e['origins']) else 'recorded_difference'
                    assert identity=={'relation':relation,'morpheme_index':0,'expected_origins':expected,'whole_entries':owner['whole_entries'],'whole_origins_complete':complete},(word,entry)
                changes.append({'id':'hada-noun-change-'+digest([mode,word,a]),'mode':mode,'surface':word,'analysis':a,'parent':parent,'reading':reading,'contextual_verdict':'unjudged','independent_review':'pending'})
        assert count==report['addition_counts'][mode] and surfaces==report['changed_surfaces'][mode]
    if 'changes' in report:assert report['changes']==changes
    return changes


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');p.add_argument('--comparison',type=Path,default=REPORT);p.add_argument('--changes',type=Path);a=p.parse_args()
    source=read(SOURCE);changes=inspect_comparison(source,read(a.comparison))
    if a.changes:
        assert not a.changes.exists();a.changes.write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
    print('Verified 11 owners / all 28 source groups / 138 complete native entries / 1048 original corpus rows / 114 stable cases / 12 streams /',len(changes),'parent-attributed additions')
