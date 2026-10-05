"""Verify captured API orders, complete native entries and inspected browser output."""
import argparse
import base64
import hashlib
import unicodedata
from pathlib import Path

from nominal_si_audit import FIXTURE, RULE, SOURCE
from nominal_si_audit import REPORT as DIAGNOSTICS
from well_doeda_audit import MODES, ROOT, read, sha, word_records

REPORT=ROOT/'docs/nominal-si-runtime-checks.json.gz'


def inspect(report):
    source,diagnostic=read(SOURCE),read(DIAGNOSTICS)
    api,browser=report['api'],report['browser']
    assert report['source_sha256']==api['source_sha256']==sha(SOURCE)
    assert report['diagnostics_sha256']==sha(DIAGNOSTICS)
    assert api['cli_sha256']==browser['cli_sha256']==diagnostic['cli_sha256']
    assert browser['fixture_sha256']==sha(FIXTURE)
    assert browser['dictionary_sha256']==diagnostic['dictionary_sha256']
    assert api['before']['cli_sha256']==source['before_cli_sha256']
    assert api['before']['derived_orders']==0 and len(api['before']['batches'])==4
    before={}
    for batch in api['before']['batches']:
        assert batch['encoding']=='NFC'
        records,_=word_records(batch['cli_jsonl'])
        assert batch['response']['records']==records
        for record,orders in zip(records,batch['response']['breakdowns'],strict=True):
            if record.get('analysis'):
                before[record['analysis']['normalized']]=(record,orders)
    assert set(before)==set(source['words'])
    _,original=word_records(source['before']['raw']['jsonl'])
    for word,(record,_) in before.items():
        assert (record['analysis'],record['dictionary'])==(original[word]['analysis'],original[word]['dictionary'])
    assert len(api['batches'])==8
    assert [b['encoding'] for b in api['batches']]==['NFC']*4+['NFD']*4
    _,expected=word_records(diagnostic['runs']['raw']['NFC-cached']['jsonl'])
    total=derived=0;encodings={'NFC':[],'NFD':[]}
    for batch_index,batch in enumerate(api['batches']):
        start=(batch_index % 4)*63
        assert batch['request']['text']==unicodedata.normalize(batch['encoding'],' '.join(source['words'][start:start+63]))
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
    assert all(words==source['words'] for words in encodings.values())
    assert total==504 and derived==api['derived_orders']==282
    assert api['complete_native_entries']==api['before']['complete_native_entries']==source['complete_native_entries']
    assert browser['browser_errors']==[]
    assert [r['encoding'] for r in browser['responses']]==['NFC','NFD']
    for batch in browser['responses']:
        response=batch['response']
        assert batch['request']['text']==unicodedata.normalize(batch['encoding'],'문제시됐어요 의문시되는 중요시됨은 중요시되시다')
        assert ''.join(r['surface'] for r in response['records'])==batch['request']['text']
        assert any((e['id'],e['headword'],e['pos'])==('krdict:71567','-시','접사') for e in response['grammar']['-시'])
        assert all(e['id']!='krdict:71567' for e in response['grammar']['-시-'])
        for record in response['records']:
            if record.get('analysis'):
                want=expected[record['analysis']['normalized']]
                assert (record['analysis'],record['dictionary'])==(want['analysis'],want['dictionary'])
    assert len(browser['checks'])==6 and len(browser['diagrams'])==8
    assert {(c['encoding'],c['mode']) for c in browser['checks']}=={(e,m) for e in ['NFC','NFD'] for m in MODES}
    for check in browser['checks']:
        assert check['cli_records']==check['exported_records']
        _,words=word_records(diagnostic['runs'][check['mode']]['NFC-cached']['jsonl'])
        for record in check['exported_records']:
            if record.get('analysis'):
                want=words[record['analysis']['normalized']]
                assert (record['analysis'],record['dictionary'])==(want['analysis'],want['dictionary'])
    assert {(d['encoding'],d['word']) for d in browser['diagrams']}=={(e,w) for e in ['NFC','NFD'] for w in ['문제시됐어요','의문시되는','중요시됨은','중요시되시다']}
    for diagram in browser['diagrams']:
        assert diagram['parts'][:3]==[diagram['base'],'시','되']
        assert diagram['selected']!=diagram['whole_selected']
        assert diagram['entry'] in source['complete_native_entries']
        assert source['complete_native_entries'][diagram['entry']]['headword']==diagram['base']
        assert next(e for e in diagram['owner']['entries'] if e['id']==diagram['entry'])['derivational_identity']['morpheme_index']==1
    assert set(report['screenshots'])=={'desktop','mobile'}
    for screenshot in report['screenshots'].values():
        raw=base64.b64decode(screenshot['base64'],validate=True)
        assert raw.startswith(b'\x89PNG\r\n\x1a\n')
        assert hashlib.sha256(raw).hexdigest()==screenshot['sha256']
    return total,derived,44,8,6


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true',required=True)
    parser.add_argument('--report',type=Path,default=REPORT)
    args=parser.parse_args();print('Verified API/owned orders/native/diagrams/exports:',inspect(read(args.report)))
