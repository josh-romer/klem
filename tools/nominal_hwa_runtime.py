"""Verify captured API orders, complete native entries and inspected browser output."""
import argparse
import base64
import hashlib
import unicodedata
from pathlib import Path

from nominal_hwa_audit import FIXTURE, RULE, SOURCE, before_words
from nominal_hwa_audit import REPORT as DIAGNOSTICS
from well_doeda_audit import MODES, ROOT, read, sha, word_records

REPORT=ROOT/'docs/nominal-hwa-runtime-checks.json.gz'


def inspect(report):
    source,diagnostic=read(SOURCE),read(DIAGNOSTICS)
    words=list(read(FIXTURE)['before_analyses'])
    assert len(words)==959
    api,browser=report['api'],report['browser']
    assert report['source_sha256']==api['source_sha256']==sha(SOURCE)
    assert report['diagnostics_sha256']==sha(DIAGNOSTICS)
    assert api['cli_sha256']==browser['cli_sha256']==diagnostic['cli_sha256']
    assert browser['fixture_sha256']==sha(FIXTURE)
    assert browser['dictionary_sha256']==diagnostic['dictionary_sha256']
    assert api['before']['cli_sha256']==source['before_cli_sha256']
    assert api['before']['derived_orders']==0 and len(api['before']['batches'])==16
    before={}
    for batch in api['before']['batches']:
        assert batch['encoding']=='NFC'
        records,_=word_records(batch['cli_jsonl'])
        assert batch['response']['records']==records
        for record,orders in zip(records,batch['response']['breakdowns'],strict=True):
            if record.get('analysis'):
                before[record['analysis']['normalized']]=(record,orders)
    assert set(before)==set(words)
    original=before_words(source,'raw')
    for word,(record,_) in before.items():
        assert (record['analysis'],record['dictionary'])==(original[word]['analysis'],original[word]['dictionary'])
    assert len(api['batches'])==32
    assert [b['encoding'] for b in api['batches']]==['NFC']*16+['NFD']*16
    _,expected=word_records(diagnostic['runs']['raw']['NFC-cached']['jsonl'])
    total=derived=0;encodings={'NFC':[],'NFD':[]}
    for batch_index,batch in enumerate(api['batches']):
        start=(batch_index % 16)*63
        assert batch['request']['text']==unicodedata.normalize(batch['encoding'],' '.join(words[start:start+63]))
        assert hashlib.sha256(batch['cli_jsonl'].encode()).hexdigest()==batch['cli_jsonl_sha256']
        records,_=word_records(batch['cli_jsonl'])
        assert records==batch['response']['records']
        assert ''.join(r['surface'] for r in records)==batch['request']['text']
        assert len(batch['request']['text'].encode())<=8000
        for record,orders in zip(records,batch['response']['breakdowns'],strict=True):
            if not record.get('analysis'):continue
            word=record['analysis']['normalized'];total+=1;encodings[batch['encoding']].append(word)
            assert (record['analysis'],record['dictionary'])==(expected[word]['analysis'],expected[word]['dictionary'])
            old,old_orders=before[word]
            for analysis,order in zip(record['analysis']['analyses'],orders,strict=True):
                if RULE not in analysis['rules']:
                    assert order==old_orders[old['analysis']['analyses'].index(analysis)]
                    continue
                assert order[:2]==[{'lemma':0},{'morpheme':0}]
                assert [c['morpheme'] for c in order if 'morpheme' in c]==list(range(len(analysis['morphemes'])))
                assert [c['lemma'] for c in order if 'lemma' in c]==list(range(len(analysis['lemmas'])))
                derived+=1
    assert all(values==words for values in encodings.values())
    assert total==1918 and derived==api['derived_orders']==1204
    assert api['complete_native_entries']==api['before']['complete_native_entries']==source['complete_native_entries']
    assert browser['browser_errors']==[]
    assert [r['encoding'] for r in browser['responses']]==['NFC','NFD']
    for batch in browser['responses']:
        response=batch['response']
        assert batch['request']['text']==unicodedata.normalize(batch['encoding'],'가시화됐어요 상품화되는 이상화됨은 제도화되시다 가시화')
        assert ''.join(r['surface'] for r in response['records'])==batch['request']['text']
        assert any((e['id'],e['headword'],e['pos'])==('krdict:88499','-화','접사') for e in response['grammar']['-화'])
        assert all(e['id']!='krdict:88499' for e in response['grammar']['-시-'])
        for record in response['records']:
            if record.get('analysis'):
                want=expected[record['analysis']['normalized']]
                assert (record['analysis'],record['dictionary'])==(want['analysis'],want['dictionary'])
    assert len(browser['checks'])==6 and len(browser['diagrams'])==10
    assert {(c['encoding'],c['mode']) for c in browser['checks']}=={(e,m) for e in ['NFC','NFD'] for m in MODES}
    for check in browser['checks']:
        assert check['cli_records']==check['exported_records']
        _,words=word_records(diagnostic['runs'][check['mode']]['NFC-cached']['jsonl'])
        for record in check['exported_records']:
            if record.get('analysis'):
                want=words[record['analysis']['normalized']]
                assert (record['analysis'],record['dictionary'])==(want['analysis'],want['dictionary'])
    assert {(d['encoding'],d['word']) for d in browser['diagrams']}=={(e,w) for e in ['NFC','NFD'] for w in ['가시화됐어요','상품화되는','이상화됨은','제도화되시다','가시화']}
    for diagram in browser['diagrams']:
        assert diagram['parts'][:(2 if diagram['word']=='가시화' else 3)]==([diagram['base'],'화'] if diagram['word']=='가시화' else [diagram['base'],'화','되'])
        assert diagram['selected']!=diagram['whole_selected']
        assert diagram['entry'] in source['complete_native_entries']
        assert source['complete_native_entries'][diagram['entry']]['headword']==diagram['base']
        assert next(e for e in diagram['owner']['entries'] if e['id']==diagram['entry'])['derivational_identity']['morpheme_index']==(0 if diagram['word']=='가시화' else 1)
        response = next(r['response'] for r in browser['responses'] if r['encoding'] == diagram['encoding'])
        record = next(r for r in response['records'] if (r.get('analysis') or {}).get('normalized') == diagram['word'])
        assert diagram['owner'] == record['dictionary']['readings'][diagram['selected']]['lemmas'][0]
        entry = next(e for e in diagram['owner']['entries'] if e['id'] == diagram['entry'])
        assert entry['derivational_identity']['relation'] == 'recorded_match'
        assert diagram['label'] == response['glosses'][diagram['entry']]
    assert set(report['screenshots'])=={'desktop','mobile'}
    for screenshot in report['screenshots'].values():
        raw=base64.b64decode(screenshot['base64'],validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        assert hashlib.sha256(raw).hexdigest()==screenshot['sha256']
    return total,derived,164,10,6


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args();print('Verified API/owned orders/native/diagrams/exports:',inspect(read(args.report)))
