"""Verify every changed full-stream frame against original records and remaining-hada parents."""
import argparse
import hashlib
from pathlib import Path

from hada_remaining_audit import FIXTURE, SOURCE, inspect_source, parent_for
from well_doeda_audit import ROOT, digest, read, sha

PRIOR=ROOT/'docs/hada-nominal-packaged-observations.json.gz'
REPORT=ROOT/'docs/hada-remaining-observations.json.gz'


def inspect(report):
    prior,source=read(PRIOR),read(SOURCE);owners=inspect_source(source)
    assert report['schema_version']==1 and report['checklist']=='COV-022t'
    assert report['prior_sha256']==sha(PRIOR) and report['source_sha256']==sha(SOURCE)
    assert report['fixture_sha256']==sha(FIXTURE)
    assert report['before_cli_sha256']==prior['cli_sha256']==source['before_cli_sha256']
    assert report['dictionary_sha256']==prior['dictionary_sha256']==source['dictionary_sha256']
    assert len(report['comparisons'])==len(prior['comparisons'])==8
    assert hashlib.sha256(report['producer']['text'].encode()).hexdigest()==report['producer']['sha256']
    changes=[];metadata=[];native=source['complete_native_entries']
    for old,new in zip(prior['comparisons'],report['comparisons'],strict=True):
        assert {k:v for k,v in old.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}=={k:v for k,v in new.items() if k not in ['before_jsonl_sha256','after_jsonl_sha256','changed_records']}
        assert new['before_jsonl_sha256']==old['after_jsonl_sha256']
        pairs=[p for p in report['changed_record_pairs'] if p['mode']==new['mode']]
        assert len(pairs)==new['changed_records']
        assert len({p['location']['record'] for p in pairs})==len(pairs)
        path=Path(new['source']);text=None
        if path.exists():
            assert sha(path)==new['source_sha256'];text=path.read_bytes()
        for pair in pairs:
            b,a=pair['before'],pair['after'];location=pair['location']
            assert location['mode']==new['mode'] and 0<=location['record']<new['records']
            assert {k:v for k,v in b.items() if k not in ['analysis','dictionary']}=={k:v for k,v in a.items() if k not in ['analysis','dictionary']}
            assert location['span']==a['span']
            if text is not None:
                span=a['span'];assert text[span['start']:span['end']].decode()==a['surface']
                assert location['context']==text[max(0,span['start']-120):min(len(text),span['end']+120)].decode(errors='replace')
            word=a['analysis']['normalized'];old_paths=b['analysis']['analyses'];new_paths=a['analysis']['analyses']
            assert {k:v for k,v in b['analysis'].items() if k!='analyses'}=={k:v for k,v in a['analysis'].items() if k!='analyses'}
            assert [p for p in new_paths if p in old_paths]==old_paths
            assert {k:v for k,v in b['dictionary'].items() if k not in ['lemmas','readings']}=={k:v for k,v in a['dictionary'].items() if k not in ['lemmas','readings']}
            old_lemmas=b['dictionary']['lemmas'];old_keys=[l['lemma'] for l in old_lemmas]
            retained=[l for l in a['dictionary']['lemmas'] if l['lemma'] in old_keys]
            assert [l['lemma'] for l in retained]==old_keys
            for old_entry,new_entry in zip(old_lemmas,retained,strict=True):
                assert len(old_entry['entries'])==len(new_entry['entries'])
                for oe,ne in zip(old_entry['entries'],new_entry['entries'],strict=True):
                    if oe==ne:continue
                    assert (old_entry['lemma']['text'], old_entry['lemma']['kind']) in owners
                    assert 'origins' not in oe and {k:v for k,v in ne.items() if k!='origins'}==oe
                    assert ne['origins']==native[ne['id']]['origins']
                    metadata.append({'id':'hada-remaining-origin-field-'+digest([new['mode'],location['record'],old_entry['lemma'],oe,ne]),'mode':new['mode'],'location':location,'lemma':old_entry['lemma'],'before':oe,'after':ne,'source_entry':native[ne['id']],'scope':'Previously omitted origins field now populated from the complete native entry; existing path assessments remain unchanged.'})
            for entry in a['dictionary']['lemmas']:
                if entry['lemma'] in old_keys:continue
                assert (entry['lemma']['text'], entry['lemma']['kind']) in owners
                for e in entry['entries']:
                    original=native[e['id']]
                    for key in ['id','headword','homonym','pos']:assert e[key]==original[key]
                    if 'origins' in e:assert e['origins']==original['origins']
            for index,analysis in enumerate(new_paths):
                reading=a['dictionary']['readings'][index]
                if analysis in old_paths:
                    assert reading==b['dictionary']['readings'][old_paths.index(analysis)];continue
                parent,components=parent_for(owners,word,analysis,old_paths)
                for component in components:
                    owner = component['source_owner']
                    assessment = next(l for l in reading['lemmas'] if l['lemma_index'] == component['lemma_index'])
                    for entry in assessment['entries']:
                        original=native[entry['id']];identity=entry.get('derivational_identity')
                        eligible = original['pos']=='명사' or (owner['base_role']=='bound_noun' and original['pos']=='의존 명사') or (owner['base_role']=='adverbial' and original['pos']=='부사')
                        if owner['base_role']=='bound_noun' and original['pos']!='의존 명사':
                            assert entry['status'] != 'compatible'
                        if not eligible:
                            assert identity is None
                            continue
                        expected=owner['whole_expected_base_origins']
                        complete=all(native[i]['origins'] for i in owner['whole_entries'])
                        relation='recorded_match' if set(expected)&set(original['origins']) else 'recorded_difference' if complete and original['origins'] else 'unknown'
                        assert identity=={'relation':relation,'morpheme_index':component['morpheme_index'],'expected_origins':expected,'whole_entries':owner['whole_entries'],'whole_origins_complete':complete}
                changes.append({'id':'hada-remaining-stream-'+digest([new['mode'],location['record'],word,analysis]),'mode':new['mode'],'location':location,'surface':word,'analysis':analysis,'parent':parent,'inserted_components':components,'reading':reading,'contextual_verdict':'unjudged','independent_review':'pending'})
        assert (new['before_jsonl_sha256']==new['after_jsonl_sha256'])==(not pairs)
    assert sum(c['records'] for c in report['comparisons'])==1128312
    if 'candidate_changes' in report:assert report['candidate_changes']==changes
    if 'origin_field_changes' in report:assert report['origin_field_changes']==metadata
    if metadata:print('Verified explicitly sourced origin-field enrichments:',len(metadata))
    return changes,metadata


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true',required=True);p.add_argument('--report',type=Path,default=REPORT);a=p.parse_args()
    print('Verified 1128312 original frames;',len(inspect(read(a.report))[0]),'individually parent-attributed additions')
